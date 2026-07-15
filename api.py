"""FastAPI backend فوق agent.py — طبقة نقل (HTTP) فقط. **لا يوجد هنا أي
منطق قرار جديد**: كل نقطة نهاية تستدعي run_agent() من agent.py كما هي،
بدون أي تعديل عليها أو على الأدوات في tools/. القرار الكامل (أي أداة، متى،
وبأي معطيات) يبقى بالكامل عند Gemini، تماماً كما في CLI وواجهة Streamlit
السابقتين."""

import os
import tempfile

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import run_agent, wrap_resume_text
from tools.resume_parser import extract_resume_text

MAX_REQUESTS_PER_SESSION = 6

app = FastAPI(title="CareerPilot API")

# ------------------------------------------------------------------
# تخزين الجلسات: dict بالذاكرة مفتاحه X-Session-Id — مقبول لخادم تطوير
# بعملية واحدة (single process)، بنفس روح session_state في نسخة Streamlit.
# ------------------------------------------------------------------
SESSIONS: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "history": [],
            "pending_prefix": "",
            "request_count": 0,
            "resume_filename": None,
        }
    return SESSIONS[session_id]


class MessageRequest(BaseModel):
    message: str


@app.post("/api/upload")
async def upload_resume(
    file: UploadFile = File(...),
    x_session_id: str = Header(..., alias="X-Session-Id"),
) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="الملف يجب أن يكون PDF.")

    tmp_path = None
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        resume_text = extract_resume_text(tmp_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    session = get_session(x_session_id)
    session["pending_prefix"] = wrap_resume_text(resume_text)
    session["resume_filename"] = file.filename

    return {"filename": file.filename, "message": "تم استخراج نص السيرة الذاتية بنجاح."}


@app.post("/api/message")
async def send_message(
    body: MessageRequest,
    x_session_id: str = Header(..., alias="X-Session-Id"),
) -> JSONResponse:
    session = get_session(x_session_id)

    if session["request_count"] >= MAX_REQUESTS_PER_SESSION:
        return JSONResponse(
            status_code=429,
            content={
                "error": (
                    f"وصلتِ للحد الأقصى من الطلبات لهذي الجلسة "
                    f"({MAX_REQUESTS_PER_SESSION} طلبات)."
                )
            },
        )

    message_to_send = session["pending_prefix"] + body.message
    session["pending_prefix"] = ""
    turn_start = len(session["history"])

    try:
        reply, updated_history = run_agent(message_to_send, session["history"])
    except Exception as exc:  # noqa: BLE001 — خطأ غير متوقع بمستوى الـ API نفسه (rule 6 يغطي أخطاء الأدوات الداخلية فقط)
        raise HTTPException(status_code=500, detail=f"فشل الطلب: {exc}") from exc

    session["history"] = updated_history
    session["request_count"] += 1

    tool_calls = [
        part.function_call.name
        for content in updated_history[turn_start:]
        for part in content.parts
        if part.function_call
    ]

    return JSONResponse(
        content={
            "reply": reply,
            "tool_calls": tool_calls,
            "request_count": session["request_count"],
            "request_limit": MAX_REQUESTS_PER_SESSION,
        }
    )


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
