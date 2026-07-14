"""واجهة Streamlit بسيطة فوق agent.py — طبقة عرض فقط. لا يوجد هنا أي منطق
قرار جديد (متى تُستدعى أي أداة) — هذا يبقى بالكامل داخل agent.py وحلقة
run_agent كما هي، بدون أي تعديل."""

import os
import tempfile

import streamlit as st

from agent import run_agent, wrap_resume_text
from tools.resume_parser import extract_resume_text

REVIEW_TOOLS = {"suggest_resume_edits", "draft_cover_letter"}

st.set_page_config(page_title="CareerPilot", page_icon="🧭")
st.title("🧭 CareerPilot")
st.caption("وكيل ذكاء اصطناعي يساعدك في رحلة البحث عن وظيفة")

if "history" not in st.session_state:
    st.session_state.history = []
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "pending_prefix" not in st.session_state:
    st.session_state.pending_prefix = ""
if "processed_pdf_name" not in st.session_state:
    st.session_state.processed_pdf_name = None

with st.sidebar:
    st.subheader("سيرتك الذاتية")
    uploaded_pdf = st.file_uploader("ارفع ملف PDF لسيرتك الذاتية", type=["pdf"])

    if uploaded_pdf is not None and uploaded_pdf.name != st.session_state.processed_pdf_name:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_pdf.getvalue())
                tmp_path = tmp.name
            resume_text = extract_resume_text(tmp_path)
            st.session_state.pending_prefix = wrap_resume_text(resume_text)
            st.session_state.processed_pdf_name = uploaded_pdf.name
            st.success("تم استخراج نص السيرة الذاتية بنجاح.")
        except Exception as exc:
            st.error(f"تعذّر استخراج نص PDF: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    if st.session_state.processed_pdf_name:
        st.info(f"✅ محمّلة: {st.session_state.processed_pdf_name}")


def render_message(role: str, content: str, needs_review: bool = False) -> None:
    with st.chat_message(role):
        if needs_review:
            with st.container(border=True):
                st.warning("🔍 هذا اقتراح يحتاج مراجعتك بعناية قبل استخدامه فعلياً")
                st.write(content)
        else:
            st.write(content)


for msg in st.session_state.display_messages:
    render_message(msg["role"], msg["content"], msg.get("needs_review", False))

user_input = st.chat_input("اكتب رسالتك هنا...")

if user_input:
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    render_message("user", user_input)

    message_to_send = st.session_state.pending_prefix + user_input
    st.session_state.pending_prefix = ""

    turn_start = len(st.session_state.history)

    with st.spinner("🤔 يفكر وينفّذ الأدوات اللازمة..."):
        reply, updated_history = run_agent(message_to_send, st.session_state.history)

    st.session_state.history = updated_history

    needs_review = any(
        part.function_call and part.function_call.name in REVIEW_TOOLS
        for content in updated_history[turn_start:]
        for part in content.parts
    )

    st.session_state.display_messages.append(
        {"role": "assistant", "content": reply, "needs_review": needs_review}
    )
    render_message("assistant", reply, needs_review)
