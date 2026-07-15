"""واجهة Streamlit فوق agent.py — طبقة عرض فقط. لا يوجد هنا أي منطق قرار
جديد (متى تُستدعى أي أداة) — هذا يبقى بالكامل داخل agent.py وحلقة
run_agent كما هي، بدون أي تعديل."""

import os
import tempfile

import streamlit as st

from agent import run_agent, wrap_resume_text
from tools.resume_parser import extract_resume_text

REVIEW_TOOLS = {"improve_resume", "draft_cover_letter"}
MAX_REQUESTS_PER_SESSION = 5

st.set_page_config(page_title="CareerPilot", page_icon="🧭")

# الهوية البصرية: الألوان الأساسية والخط في .streamlit/config.toml،
# وهنا فقط ما لا يغطيه config.toml (إخفاء عناصر Streamlit، الظلال، الـ accent).
st.html("""
<style>
:root {
    --primary: #D3A0FD;
    --secondary: #E8CFFF;
    --purple-light: #F7F0FD;
    --accent: #ECFF70;
    --background: #FAFAFA;
    --text: #111111;
    --border: #ECECEC;
}

/* إخفاء شعار Streamlit الافتراضي والقائمة والفوتر */
#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stHeader"] {
    background: transparent;
}

/* بطاقات المحادثة: زوايا مدوّرة كبيرة وظلال ناعمة */
[data-testid="stChatMessage"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 24px;
    box-shadow: 0 4px 16px rgba(17, 17, 17, 0.05);
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}

/* نص داكن فوق الدرجة البنفسجية الفاتحة للأزرار الأساسية */
button[kind="primary"], button[kind="primaryFormSubmit"] {
    color: var(--text) !important;
}

/* الـ accent للتمييز فقط: زر التحميل */
[data-testid="stDownloadButton"] button {
    background: var(--accent) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(17, 17, 17, 0.08);
    font-weight: 600;
}
</style>
""")

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
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

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

    st.divider()
    st.caption(f"الطلبات المستخدمة: {st.session_state.request_count} / {MAX_REQUESTS_PER_SESSION}")


def render_message(index: int, msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("needs_review"):
            with st.container(border=True):
                st.warning("🔍 هذا اقتراح يحتاج مراجعتك بعناية قبل استخدامه فعلياً")
                st.write(msg["content"])
        else:
            st.write(msg["content"])

        improved = msg.get("improved_resume")
        if improved:
            with st.expander("📄 معاينة السيرة المحسّنة", expanded=False):
                st.text(improved)
            st.download_button(
                "⬇️ تحميل السيرة المحسّنة (ملف جديد)",
                data=improved,
                file_name="improved_resume.txt",
                mime="text/plain",
                key=f"download_improved_{index}",
            )


def extract_improved_resume(history_slice: list) -> str | None:
    """يلتقط نص السيرة المحسّنة من نتيجة improve_resume في مقطع history
    الخاص بهذا الدور فقط — عرض فقط، لا كتابة على أي ملف."""
    for content in history_slice:
        for part in content.parts:
            if part.function_response and part.function_response.name == "improve_resume":
                result = (part.function_response.response or {}).get("result", {})
                if isinstance(result, dict) and result.get("improved_resume"):
                    return result["improved_resume"]
    return None


for i, msg in enumerate(st.session_state.display_messages):
    render_message(i, msg)

limit_reached = st.session_state.request_count >= MAX_REQUESTS_PER_SESSION
if limit_reached:
    st.info(
        "🌙 وصلتَ للحد الأقصى من الطلبات لهذي الجلسة "
        f"({MAX_REQUESTS_PER_SESSION} طلبات). أعد تحميل الصفحة لبدء جلسة "
        "جديدة — شكراً لتجربتك CareerPilot!"
    )

user_input = st.chat_input("اكتب رسالتك هنا...", disabled=limit_reached)

if user_input and not limit_reached:
    user_msg = {"role": "user", "content": user_input}
    st.session_state.display_messages.append(user_msg)
    render_message(len(st.session_state.display_messages) - 1, user_msg)

    message_to_send = st.session_state.pending_prefix + user_input
    st.session_state.pending_prefix = ""

    turn_start = len(st.session_state.history)

    with st.spinner("🤔 يفكر وينفّذ الأدوات اللازمة..."):
        reply, updated_history = run_agent(message_to_send, st.session_state.history)

    st.session_state.history = updated_history
    st.session_state.request_count += 1

    turn_slice = updated_history[turn_start:]
    needs_review = any(
        part.function_call and part.function_call.name in REVIEW_TOOLS
        for content in turn_slice
        for part in content.parts
    )

    assistant_msg = {
        "role": "assistant",
        "content": reply,
        "needs_review": needs_review,
        "improved_resume": extract_improved_resume(turn_slice),
    }
    st.session_state.display_messages.append(assistant_msg)
    st.rerun()  # إعادة تشغيل لعرض الرد وتحديث عدّاد الطلبات معاً من الحالة المخزّنة
