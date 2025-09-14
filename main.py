import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import google.generativeai as genai

# ------------------ Env & Model ------------------
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env")

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
DB_PATH = os.getenv("DB_PATH", "chat.db")

genai.configure(api_key=API_KEY)


def get_model(system_prompt: Optional[str] = None):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
    )


# ------------------ DB ------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema():
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                personality TEXT,
                system_prompt TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT CHECK(role IN ('user','assistant','system')),
                content TEXT,
                created_at TEXT,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


ensure_schema()


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def create_conversation(title: str = "محادثة جديدة", personality: str = "مساعد عادي", system_prompt: Optional[str] = None) -> Dict:
    conv_id = uuid.uuid4().hex
    ts = now_iso()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO conversations (id, title, personality, system_prompt, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (conv_id, title, personality, system_prompt, ts, ts),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": conv_id, "title": title, "personality": personality, "system_prompt": system_prompt, "created_at": ts, "updated_at": ts}


def list_conversations() -> List[Dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, personality, system_prompt, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation(conv_id: str) -> Optional[Dict]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, title, personality, system_prompt, created_at, updated_at FROM conversations WHERE id=?",
            (conv_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_conversation(conv_id: str, title: Optional[str] = None, personality: Optional[str] = None, system_prompt: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        parts = []
        vals: List = []
        if title is not None:
            parts.append("title=?")
            vals.append(title)
        if personality is not None:
            parts.append("personality=?")
            vals.append(personality)
        if system_prompt is not None:
            parts.append("system_prompt=?")
            vals.append(system_prompt)
        parts.append("updated_at=?")
        vals.append(now_iso())
        vals.append(conv_id)
        conn.execute(f"UPDATE conversations SET {', '.join(parts)} WHERE id=?", vals)
        conn.commit()
    finally:
        conn.close()


def delete_conversation(conv_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        conn.commit()
    finally:
        conn.close()


def add_message(conv_id: str, role: str, content: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
            (conv_id, role, content, now_iso()),
        )
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now_iso(), conv_id))
        conn.commit()
    finally:
        conn.close()


def get_messages(conv_id: str, limit: Optional[int] = None) -> List[Dict]:
    conn = get_conn()
    try:
        q = "SELECT role, content, created_at FROM messages WHERE conversation_id=? ORDER BY id ASC"
        params: List = [conv_id]
        if limit:
            q += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(q, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ------------------ FastAPI ------------------
app = FastAPI(title="Gemini Chat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------ Schemas ------------------
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None
    bot_personality: Optional[str] = "مساعد عادي"


class ChatStreamRequest(BaseModel):
    conversation_id: str
    message: str
    system_prompt: Optional[str] = None
    bot_personality: Optional[str] = "مساعد عادي"


class ChatResponse(BaseModel):
    response: str
    history: List[Dict[str, str]]


class NewConversationRequest(BaseModel):
    title: Optional[str] = "محادثة جديدة"
    personality: Optional[str] = "مساعد عادي"
    system_prompt: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None


# ------------------ Helpers ------------------
DEFAULT_SYSTEM_PROMPT = (
    """أنت مساعد عربي مفيد وودود.
- تحدث باللغة العربية الفصحى أو العامية حسب طلب المستخدم
- كن دقيقًا في إجاباتك ومفصلاً عندما يطلب المستخدم
- تحدث فقط عن المواضيع المتعلقة بالويب إذا طُلب ذلك
- لا تتحدث عن أي شيء ليس متعلقًا بـ CSS أو HTML أو JavaScript
- اجب بإيجاز ما لم يطلب المستخدم التفصيل
- اقترح أسئلة متابعة مرتبطة بسؤال المستخدم عند المناسب
- جاوب بطريقة محترمة
"""
)


def build_pairs_from_history(history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    return history or []


def is_within_specialty_local(question: str, system_prompt: str) -> (bool, str):
    keywords = ["html", "php", "javascript", "بايثون", "python", "web", "تطوير الويب", "frontend", "css"]
    ql = question.lower()
    if any(kw in ql for kw in keywords):
        return True, ""
    try:
        model = get_model(system_prompt)
        resp = model.generate_content(
            f"""بناءً على تخصص المساعد: {system_prompt[:500]}...
هل السؤال التالي يقع ضمن نطاق تخصص هذا المساعد؟
السؤال: \"{question}\"
أجب بنعم أو لا فقط مع شرح موجز جداً."""
        )
        text = (resp.text or "").strip().lower()
        if "نعم" in text:
            return True, ""
        if "لا" in text:
            return False, resp.text.replace("لا", "").replace("نعم", "").strip()
        return False, "التحقق غير حاسم"
    except Exception:
        return True, ""


# ------------------ Routes ------------------
@app.get("/")
def root():
    index_path = os.path.join("static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Server running — open /docs for API documentation or place an index.html into ./static/"})


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


# Conversations REST
@app.get("/conversations")
def conversations_list():
    return list_conversations()


@app.post("/conversations")
def conversations_create(req: NewConversationRequest):
    conv = create_conversation(
        title=req.title or "محادثة جديدة",
        personality=req.personality or "مساعد عادي",
        system_prompt=req.system_prompt or DEFAULT_SYSTEM_PROMPT,
    )
    return conv


@app.get("/conversations/{conv_id}")
def conversations_get(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = get_messages(conv_id)
    conv["messages"] = msgs
    return conv


@app.patch("/conversations/{conv_id}")
def conversations_update(conv_id: str, req: UpdateConversationRequest):
    if not get_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    update_conversation(conv_id, title=req.title, personality=req.personality, system_prompt=req.system_prompt)
    return {"status": "ok"}


@app.delete("/conversations/{conv_id}")
def conversations_delete(conv_id: str):
    if not get_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    delete_conversation(conv_id)
    return {"status": "ok"}


# Legacy non-stream chat (kept for compatibility)
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system_prompt = req.system_prompt or DEFAULT_SYSTEM_PROMPT

    if req.bot_personality == "مساعد تقني":
        within, _ = is_within_specialty_local(req.message, system_prompt)
        if not within:
            apology = "عذراً، هذا السؤال خارج نطاق تخصصي كمساعد تقني. اسألني عن تطوير الويب أو البرمجة. 😊"
            updated_history = (req.history or []) + [{"user": req.message, "bot": apology}]
            return {"response": apology, "history": updated_history}

    pairs = build_pairs_from_history(req.history)

    history = []
    for item in pairs:
        u = item.get("user")
        b = item.get("bot")
        if u:
            history.append({"role": "user", "parts": [u]})
        if b:
            history.append({"role": "model", "parts": [b]})

    model = get_model(system_prompt)
    chat_session = model.start_chat(history=history)
    try:
        resp = chat_session.send_message(req.message)
        bot_response = resp.text or "لم يتم العثور على استجابة من النموذج."
    except Exception as e:
        bot_response = f"حدث خطأ أثناء الاتصال بالنموذج: {str(e)}"

    updated_history = (req.history or []) + [{"user": req.message, "bot": bot_response}]
    return {"response": bot_response, "history": updated_history}


# Streaming chat
@app.post("/chat/stream")
def chat_stream(req: ChatStreamRequest):
    conv = get_conversation(req.conversation_id)
    if not conv:
        # إذا أرسل العميل معرفًا غير موجود، أنشئ واحدًا جديدًا بنفس المعرّف للشفافية
        conv = create_conversation(title="محادثة جديدة", personality=req.bot_personality or "مساعد عادي", system_prompt=req.system_prompt or DEFAULT_SYSTEM_PROMPT)
        # استبدل المعرّف بالمطلوب إذا وُجد (لكن لا يمكن فرضه مع PRIMARY KEY العشوائي)
        req.conversation_id = conv["id"]

    system_prompt = conv.get("system_prompt") or req.system_prompt or DEFAULT_SYSTEM_PROMPT

    add_message(req.conversation_id, "user", req.message)

    past = get_messages(req.conversation_id)
    hist = []
    for m in past:
        role = m["role"]
        content = m["content"]
        if role == "user":
            hist.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            hist.append({"role": "model", "parts": [content]})

    model = get_model(system_prompt)
    chat_session = model.start_chat(history=hist)

    def token_streamer():
        acc: List[str] = []
        try:
            stream = chat_session.send_message(req.message, stream=True)
            for chunk in stream:
                if hasattr(chunk, "text") and chunk.text:
                    acc.append(chunk.text)
                    yield chunk.text
            # Ensure stream completion (older libs need resolve)
            try:
                stream.resolve()
            except Exception:
                pass
        except Exception as e:
            err = f"\n[خطأ]: {str(e)}"
            acc.append(err)
            yield err
        finally:
            full = "".join(acc).strip()
            if full:
                add_message(req.conversation_id, "assistant", full)
                # تحديث العنوان إذا بقي على القيمة الافتراضية
                if conv.get("title") in (None, "", "محادثة جديدة"):
                    new_title = (req.message or "").strip()[:20]
                    if new_title:
                        update_conversation(req.conversation_id, title=new_title + ("..." if len(req.message) > 20 else ""))

    return StreamingResponse(token_streamer(), media_type="text/plain; charset=utf-8")
