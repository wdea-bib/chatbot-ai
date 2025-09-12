# # main.py
# import os
# from typing import List, Dict, Optional
# from dotenv import load_dotenv
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse, JSONResponse
# from pydantic import BaseModel
# import google.generativeai as genai

# load_dotenv()

# API_KEY = os.getenv("GOOGLE_API_KEY")
# if not API_KEY:
#     raise RuntimeError("GOOGLE_API_KEY not set in .env")

# genai.configure(api_key=API_KEY)
# MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# app = FastAPI(title="Gemini Chat Backend")

# # CORS (عدّل origins في الإنتاج)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8000", "http://127.0.0.1:8000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Serve static files from ./static
# if os.path.isdir("static"):
#     app.mount("/static", StaticFiles(directory="static"), name="static")


# # ---------- Pydantic models ----------
# class ChatRequest(BaseModel):
#     message: str
#     history: Optional[List[Dict[str, str]]] = None
#     system_prompt: Optional[str] = None
#     bot_personality: Optional[str] = "مساعد عادي"

# class ChatResponse(BaseModel):
#     response: str
#     history: List[Dict[str, str]]


# # ---------- Helpers ----------
# def build_conversation(system_prompt: str, history: Optional[List[Dict[str, str]]], new_message: str) -> str:
#     conversation = (system_prompt.strip() + "\n\n") if system_prompt else ""
#     if history:
#         for item in history:
#             u = item.get("user", "")
#             b = item.get("bot", "")
#             if u:
#                 conversation += f"User: {u}\n\n"
#             if b:
#                 conversation += f"Assistant: {b}\n\n"
#     conversation += f"User: {new_message}\n\nAssistant:"
#     return conversation

# def is_within_specialty_local(question: str, system_prompt: str) -> (bool, str):
#     # فحص بسيط بالكلمات المفتاحية أولًا لتقليل استدعاءات النموذج
#     keywords = ["html","css","javascript","بايثون","python","web","تطوير الويب","frontend"]
#     ql = question.lower()
#     if any(kw in ql for kw in keywords):
#         return True, ""
#     # إن لم نحسم الأمر نستخدم النموذج كخيار ثانٍ (كما في كودك القديم)
#     try:
#         model = genai.GenerativeModel(MODEL_NAME)
#         check_prompt = f"""بناءً على تخصص المساعد: {system_prompt[:500]}...
# هل السؤال التالي يقع ضمن نطاق تخصص هذا المساعد؟
# السؤال: "{question}"
# أجب بنعم أو لا فقط مع شرح موجز جداً."""
#         resp = model.generate_content(check_prompt)
#         text = (resp.text or "").strip().lower()
#         if "نعم" in text:
#             return True, ""
#         elif "لا" in text:
#             reason = resp.text.replace("لا", "").replace("نعم", "").strip()
#             return False, reason
#         else:
#             return False, "التحقق غير حاسم"
#     except Exception:
#         # إذا فشل الاتصال بالموديل، افترض أننا داخل التخصص لتفادي الحجب الزائد
#         return True, ""


# # ---------- Routes ----------
# @app.get("/")
# def root():
#     index_path = os.path.join("static", "index.html")
#     if os.path.isfile(index_path):
#         return FileResponse(index_path)
#     return JSONResponse({"message": "Server running — open /docs for API documentation or place an index.html into ./static/"})


# @app.post("/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     system_prompt = req.system_prompt or """أنت مساعد عربي مفيد وودود.
# - تحدث باللغة العربية الفصحى أو العامية حسب طلب المستخدم
# - كن دقيقًا في إجاباتك ومفصلاً عندما يطلب المستخدم
# - تحدث فقط عن المواضيع المتعلقة بالويب إذا طُلب ذلك
# """

#     if req.bot_personality == "مساعد تقني":
#         within, reason = is_within_specialty_local(req.message, system_prompt)
#         if not within:
#             apology = "عذراً، هذا السؤال خارج نطاق تخصصي كمساعد تقني. اسألني عن تطوير الويب أو البرمجة. 😊"
#             updated_history = (req.history or []) + [{"user": req.message, "bot": apology}]
#             return {"response": apology, "history": updated_history}

#     conversation_content = build_conversation(system_prompt, req.history or [], req.message)

#     try:
#         model = genai.GenerativeModel(MODEL_NAME)
#         response = model.generate_content(conversation_content)
#         bot_response = response.text or "لم يتم العثور على استجابة من النموذج."
#     except Exception as e:
#         bot_response = f"حدث خطأ أثناء الاتصال بالنموذج: {str(e)}"

#     updated_history = (req.history or []) + [{"user": req.message, "bot": bot_response}]
#     return {"response": bot_response, "history": updated_history}

# @app.get("/health")
# def health():
#     return {"status": "ok", "model": MODEL_NAME}


# main.py
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env")

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
client = genai.Client(api_key=API_KEY)

app = FastAPI(title="Gemini Chat Backend")

# CORS (عدّل origins في الإنتاج)
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

# Serve static files from ./static
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Pydantic models ----------
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None
    bot_personality: Optional[str] = "مساعد عادي"

class ChatResponse(BaseModel):
    response: str
    history: List[Dict[str, str]]


# ---------- Helpers ----------
def build_chat_history(history: Optional[List[Dict[str, str]]]) -> List:
    """حوّل التاريخ القديم إلى صيغة Gemini Chat"""
    chat_history = []
    if history:
        for item in history:
            user_msg = item.get("user")
            bot_msg = item.get("bot")
            if user_msg:
                chat_history.append(types.UserContent(parts=[types.Part(text=user_msg)]))
            if bot_msg:
                chat_history.append(types.ModelContent(parts=[types.Part(text=bot_msg)]))
    return chat_history

def is_within_specialty_local(question: str, system_prompt: str) -> (bool, str):
    """فحص بسيط إذا السؤال ضمن تخصص المساعد لتقليل استدعاءات API"""
    keywords = ["html","php","javascript","بايثون","python","web","تطوير الويب","frontend"]
    ql = question.lower()
    if any(kw in ql for kw in keywords):
        return True, ""
    # إذا لم نحسم، نستخدم النموذج كخيار ثانٍ
    try:
        prompt = f"""بناءً على تخصص المساعد: {system_prompt[:500]}...
هل السؤال التالي يقع ضمن نطاق تخصص هذا المساعد؟
السؤال: "{question}"
أجب بنعم أو لا فقط مع شرح موجز جداً."""
        resp = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        text = (resp.text or "").strip().lower()
        if "نعم" in text:
            return True, ""
        elif "لا" in text:
            reason = resp.text.replace("لا", "").replace("نعم", "").strip()
            return False, reason
        else:
            return False, "التحقق غير حاسم"
    except Exception:
        return True, ""


# ---------- Routes ----------
@app.get("/")
def root():
    index_path = os.path.join("static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "message": "Server running — open /docs for API documentation or place an index.html into ./static/"
    })


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system_prompt = req.system_prompt or """أنت مساعد عربي مفيد وودود.
    
- تحدث باللغة العربية الفصحى أو العامية حسب طلب المستخدم
- كن دقيقًا في إجاباتك ومفصلاً عندما يطلب المستخدم
- تحدث فقط عن المواضيع المتعلقة بالويب إذا طُلب ذلك
-لاتتحدث عن اي شيء ليس متعلق ب css,html,js
-اجابة مختصرة الا في حال طلب منك ان جيب ب التفصيل 
-اقتراح اسئلة للمساعدة في اشياء منرتبطة ب السؤالالذي وجه اليك
-جاوب بطريقة محترمة
"""

    # فحص شخصية المساعد
    if req.bot_personality == "مساعد تقني":
        within, reason = is_within_specialty_local(req.message, system_prompt)
        if not within:
            apology = "عذراً، هذا السؤال خارج نطاق تخصصي كمساعد تقني. اسألني عن تطوير الويب أو البرمجة. 😊"
            updated_history = (req.history or []) + [{"user": req.message, "bot": apology}]
            return {"response": apology, "history": updated_history}

    # بناء التاريخ
    chat_history = build_chat_history(req.history)

    # إضافة سؤال جديد
    chat_history.append(types.UserContent(parts=[types.Part(text=req.message)]))

    try:
        chat_session = client.chats.create(
            model=MODEL_NAME,
            history=chat_history
        )
        # إرسال رسالة جديدة (يعتمد على التاريخ السابق)
        resp = chat_session.send_message("")
        bot_response = resp.text or "لم يتم العثور على استجابة من النموذج."
    except Exception as e:
        bot_response = f"حدث خطأ أثناء الاتصال بالنموذج: {str(e)}"

    updated_history = (req.history or []) + [{"user": req.message, "bot": bot_response}]
    return {"response": bot_response, "history": updated_history}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}



