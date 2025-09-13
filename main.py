
# import os
# from typing import List, Dict, Optional
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse, JSONResponse
# from pydantic import BaseModel
# from google import genai
# from google.genai import types

# # ==========================
# # إعداد البيئة وAPI
# # ==========================
# API_KEY = os.getenv("GOOGLE_API_KEY")
# if not API_KEY:
#     raise RuntimeError("GOOGLE_API_KEY not set in .env")

# MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")  # غيرت إلى 2.0-flash الأكثر استقراراً
# client = genai.Client(api_key=API_KEY)

# # ==========================
# # إعداد FastAPI
# # ==========================
# app = FastAPI(title="Gemini Chat Advanced Backend")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# if os.path.isdir("static"):
#     app.mount("/static", StaticFiles(directory="static"), name="static")

# # ==========================
# # نماذج البيانات
# # ==========================
# class ChatRequest(BaseModel):
#     message: str
#     history: Optional[List[Dict[str, str]]] = None
#     system_prompt: Optional[str] = None
#     bot_personality: Optional[str] = "مساعد عادي"

# class ChatResponse(BaseModel):
#     response: str
#     history: List[Dict[str, str]]


# # ==========================
# # وظائف مساعدة
# # ==========================
# def build_chat_history(history: Optional[List[Dict[str, str]]]) -> List:
#     chat_history = []
#     if history:
#         for item in history:
#             if user_msg := item.get("user"):
#                 chat_history.append(types.UserContent(parts=[types.Part(text=user_msg)]))
#             if bot_msg := item.get("bot"):
#                 chat_history.append(types.ModelContent(parts=[types.Part(text=bot_msg)]))
#     return chat_history

# def is_within_specialty_local(question: str, system_prompt: str) -> (bool, str):
#     keywords = ["html","css","javascript","python","بايثون","web","تطوير الويب","frontend"]
#     if any(kw in question.lower() for kw in keywords):
#         return True, ""
#     # fallback باستخدام النموذج
#     try:
#         prompt = f"""بناءً على تخصص المساعد: {system_prompt[:500]}...
# هل السؤال التالي يقع ضمن نطاق تخصص هذا المساعد؟
# السؤال: "{question}"
# أجب بنعم أو لا فقط مع شرح موجز جداً."""
#         resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
#         text = (resp.text or "").strip().lower()
#         if "نعم" in text:
#             return True, ""
#         elif "لا" in text:
#             reason = resp.text.replace("لا", "").replace("نعم", "").strip()
#             return False, reason
#         return False, "التحقق غير حاسم"
#     except Exception:
#         return True, ""


# # ==========================
# # Routes
# # ==========================
# @app.get("/")
# def root():
#     index_path = os.path.join("static", "index.html")
#     if os.path.isfile(index_path):
#         return FileResponse(index_path)
#     return JSONResponse({"message": "ضع index.html في ./static"})


# @app.post("/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     system_prompt = req.system_prompt or """أنت مساعد عربي ودود ومتخصص بالويب.
# - تحدث بالعربية الفصحى أو العامية
# - لا تجيب عن المواضيع غير المتعلقة بالويب
# """

#     # فحص التخصص قبل الاستدعاء
#     if req.bot_personality == "مساعد تقني":
#         within, reason = is_within_specialty_local(req.message, system_prompt)
#         if not within:
#             apology = "عذراً، هذا السؤال خارج نطاق تخصصي. اسأل عن تطوير الويب فقط. 😊"
#             updated_history = (req.history or []) + [{"user": req.message, "bot": apology}]
#             return {"response": apology, "history": updated_history}

#     # بناء المحتوى مع التعليمات النظامية والرسالة
#     contents = []
    
#     # إضافة التعليمات النظامية كجزء من المحتوى
#     if system_prompt:
#         contents.append(types.Content(
#             role="user",
#             parts=[types.Part(text=f"system: {system_prompt}")]
#         ))
    
#     # إضافة تاريخ المحادثة
#     if req.history:
#         for item in req.history:
#             if user_msg := item.get("user"):
#                 contents.append(types.Content(
#                     role="user",
#                     parts=[types.Part(text=user_msg)]
#                 ))
#             if bot_msg := item.get("bot"):
#                 contents.append(types.Content(
#                     role="model",
#                     parts=[types.Part(text=bot_msg)]
#                 ))
    
#     # إضافة الرسالة الحالية
#     contents.append(types.Content(
#         role="user",
#         parts=[types.Part(text=req.message)]
#     ))

#     try:
#         # استخدام generate_content بدلاً من chats.create
#         response = client.models.generate_content(
#             model=MODEL_NAME,
#             contents=contents
#         )
        
#         bot_response = response.text or "لم يتم استقبال رد من النموذج."

#     except Exception as e:
#         bot_response = f"⚠️ حدث خطأ أثناء الاتصال بالنموذج: {str(e)}"
#         # طباعة الخطأ للتصحيح
#         print(f"Error: {str(e)}")

#     updated_history = (req.history or []) + [{"user": req.message, "bot": bot_response}]
#     return {"response": bot_response, "history": updated_history}


# @app.get("/health")
# def health():
#     return {"status": "ok", "model": MODEL_NAME}



import os
from typing import List, Dict, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# ==========================
# إعداد البيئة وAPI
# ==========================
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env")

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")  # غيرت إلى 2.0-flash الأكثر استقراراً
client = genai.Client(api_key=API_KEY)

# ==========================
# إعداد FastAPI
# ==========================
app = FastAPI(title="Gemini Chat Advanced Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================
# نماذج البيانات
# ==========================
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None
    bot_personality: Optional[str] = "مساعد عادي"

class ChatResponse(BaseModel):
    response: str
    history: List[Dict[str, str]]


# ==========================
# وظائف مساعدة
# ==========================
def build_chat_history(history: Optional[List[Dict[str, str]]]) -> List:
    chat_history = []
    if history:
        for item in history:
            if user_msg := item.get("user"):
                chat_history.append(types.UserContent(parts=[types.Part(text=user_msg)]))
            if bot_msg := item.get("bot"):
                chat_history.append(types.ModelContent(parts=[types.Part(text=bot_msg)]))
    return chat_history

def is_within_specialty_local(question: str, system_prompt: str) -> (bool, str):
    keywords = ["html","css","javascript","python","بايثون","web","تطوير الويب","frontend"]
    if any(kw in question.lower() for kw in keywords):
        return True, ""
    # fallback باستخدام النموذج
    try:
        prompt = f"""بناءً على تخصص المساعد: {system_prompt[:500]}...
هل السؤال التالي يقع ضمن نطاق تخصص هذا المساعد؟
السؤال: "{question}"
أجب بنعم أو لا فقط مع شرح موجز جداً."""
        resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        text = (resp.text or "").strip().lower()
        if "نعم" in text:
            return True, ""
        elif "لا" in text:
            reason = resp.text.replace("لا", "").replace("نعم", "").strip()
            return False, reason
        return False, "التحقق غير حاسم"
    except Exception:
        return True, ""


# ==========================
# Routes
# ==========================
@app.get("/")
def root():
    index_path = os.path.join("static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "ضع index.html في ./static"})


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system_prompt = req.system_prompt or """أنت مساعد عربي ودود ومتخصص بالويب.
- تحدث بالعربية الفصحى أو العامية
- لا تجيب عن المواضيع غير المتعلقة بالويب
"""

    # فحص التخصص قبل الاستدعاء
    if req.bot_personality == "مساعد تقني":
        within, reason = is_within_specialty_local(req.message, system_prompt)
        if not within:
            apology = "عذراً، هذا السؤال خارج نطاق تخصصي. اسأل عن تطوير الويب فقط. 😊"
            updated_history = (req.history or []) + [{"user": req.message, "bot": apology}]
            return {"response": apology, "history": updated_history}

    # بناء المحتوى مع التعليمات النظامية والرسالة
    contents = []
    
    # إضافة التعليمات النظامية كجزء من المحتوى
    if system_prompt:
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=f"system: {system_prompt}")]
        ))
    
    # إضافة تاريخ المحادثة
    if req.history:
        for item in req.history:
            if user_msg := item.get("user"):
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=user_msg)]
                ))
            if bot_msg := item.get("bot"):
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=bot_msg)]
                ))
    
    # إضافة الرسالة الحالية
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=req.message)]
    ))

    try:
        # استخدام generate_content بدلاً من chats.create
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents
        )
        
        bot_response = response.text or "لم يتم استقبال رد من النموذج."

    except Exception as e:
        bot_response = f"⚠️ حدث خطأ أثناء الاتصال بالنموذج: {str(e)}"
        # طباعة الخطأ للتصحيح
        print(f"Error: {str(e)}")

    updated_history = (req.history or []) + [{"user": req.message, "bot": bot_response}]
    return {"response": bot_response, "history": updated_history}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}