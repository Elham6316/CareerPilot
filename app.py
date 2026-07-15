"""واجهة Streamlit فوق agent.py — منصة خدمات (service platform)، طبقة عرض
فقط. **لا يوجد هنا أي منطق قرار جديد**: كل زر خدمة يبني طلباً نصياً
بالعربية ويمرره لـ run_agent() نفسها، والوكيل (Gemini) يقرر بنفسه أي أداة
يستدعي وبأي تسلسل — تماماً كما لو كتب المستخدم نفس الطلب في محادثة حرة.
منطق agent.py وحلقة run_agent لم يُمس إطلاقاً."""

import os
import tempfile
from pathlib import Path

import streamlit as st

from agent import run_agent, wrap_resume_text
from tools.resume_parser import extract_resume_text

REVIEW_TOOLS = {"improve_resume", "draft_cover_letter"}
MAX_REQUESTS_PER_SESSION = 5
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

st.set_page_config(page_title="CareerPilot", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None)

# ------------------------------------------------------------------
# الهوية البصرية: الألوان الأساسية عبر .streamlit/config.toml، وهنا كل ما
# لا يغطيه theming الرسمي (الأشكال العضوية، البطاقات المتقطعة، الشبكة،
# تعطيل الخدمات، أيقونات SVG بدل الإيموجي). كل استهداف عبر key= لكل عنصر.
# ------------------------------------------------------------------
st.html("""
<style>
:root {
    --primary: #D3A0FD;
    --secondary: #E8CFFF;
    --purple-light: #F7F0FD;
    --accent: #ECFF70;
    --background: #FAFAFA;
    --text: #111111;
    --muted: #5F5F5F;
    --border: #ECECEC;
    --success: #8ED081;
}

#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppViewContainer"] { background: var(--background); }

/* ---- الشريط العلوي ---- */
.st-key-topbar {
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.25rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.5rem;
}
.st-key-topbar_brand { align-items: center; gap: 0.5rem; }
.topbar-title { font-weight: 700; color: var(--text); font-size: 1.05rem; }
.counter-pill {
    background: var(--purple-light);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.3rem 0.9rem;
    font-size: 0.85rem;
    font-weight: 600;
}

/* ---- Hero ---- */
.st-key-hero {
    position: relative;
    overflow: hidden;
    background: var(--purple-light);
    border-radius: 28px;
    padding: 3rem 2rem;
    text-align: center;
    margin-bottom: 1.5rem;
}
.st-key-hero::before, .st-key-hero::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    background: var(--secondary);
    opacity: 0.6;
    z-index: 0;
}
.st-key-hero::before { width: 220px; height: 220px; top: -90px; left: -70px; }
.st-key-hero::after { width: 160px; height: 160px; bottom: -70px; right: -50px; }
.st-key-hero > div { position: relative; z-index: 1; }
.hero-title {
    font-weight: 700;
    font-size: 2rem;
    color: var(--text);
    margin: 0.75rem 0 0.25rem 0;
}
.hero-subtitle { color: var(--muted); font-size: 1rem; }

/* ---- منطقة رفع السيرة ---- */
.st-key-upload_card {
    background: #FFFFFF;
    border: 2px dashed var(--primary);
    border-radius: 24px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}
.st-key-confirm_card {
    background: rgba(142, 208, 129, 0.15);
    border: 1px solid var(--success);
    border-radius: 24px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}
.confirm-title { color: var(--text); font-weight: 700; }
.confirm-sub { color: var(--muted); font-size: 0.9rem; }

/* ---- بطاقات الخدمات ---- */
[class*="st-key-service_"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 1.25rem;
    box-shadow: 0 6px 20px rgba(17, 17, 17, 0.04);
    height: 100%;
}
.service-title {
    font-weight: 700;
    color: var(--text);
    font-size: 1.05rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.15rem;
}
.service-desc { color: var(--muted); font-size: 0.85rem; margin-bottom: 0.85rem; }
.disabled-badge {
    display: inline-block;
    background: var(--purple-light);
    color: var(--muted);
    border-radius: 999px;
    padding: 0.15rem 0.7rem;
    font-size: 0.72rem;
    margin-bottom: 0.6rem;
}

/* أزرار الخدمات: حدود وخلفية بيضاء، hover بنفسجي فاتح */
[class*="st-key-service_"] button {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 12px !important;
    font-weight: 600;
    transition: background 0.15s ease;
}
[class*="st-key-service_"] button:hover:not(:disabled) {
    background: var(--purple-light) !important;
    border-color: var(--primary) !important;
}

/* الزر الأهم: تحسين السيرة — خلفية الـ accent */
.st-key-service_improve button {
    background: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    color: var(--text) !important;
}
.st-key-service_improve button:hover:not(:disabled) {
    filter: brightness(0.97);
}

/* ---- منطقة النتائج ---- */
.st-key-results_card {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 1.5rem;
    box-shadow: 0 6px 20px rgba(17, 17, 17, 0.04);
    margin-top: 1.5rem;
}
.st-key-review_box {
    background: rgba(236, 255, 112, 0.18);
    border: 1.5px solid var(--accent);
    border-radius: 18px;
    padding: 1rem 1.25rem;
}
.review-title {
    font-weight: 700;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.5rem;
}
.results-empty { color: var(--muted); text-align: center; padding: 1.5rem 0; }

[data-testid="stDownloadButton"] button {
    background: var(--accent) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-weight: 600;
}

html, body, [class*="css"] { direction: rtl; }
</style>
""")


# ------------------------------------------------------------------
# أيقونات SVG بسيطة inline — بدون أي إيموجي في كل الواجهة
# ------------------------------------------------------------------
def icon(name: str, color: str = "#111111", size: int = 18) -> str:
    paths = {
        "sparkle": '<path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2z"/>',
        "search": '<circle cx="10" cy="10" r="6"/><line x1="21" y1="21" x2="14.5" y2="14.5"/>',
        "check": '<polyline points="4,12 9,17 20,6"/>',
        "arrow-up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
        "letter": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
        "list": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        "star4": '<path d="M12 2c0 4-2 6-2 6s2 2 2 6c0-4 2-6 2-6s-2-2-2-6z"/>',
    }
    body = paths.get(name, "")
    fill = "none" if name != "star4" and name != "sparkle" else color
    stroke = color if fill == "none" else "none"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="{fill}" stroke="{stroke}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


# نص السيرة الذاتية يُرسل مرة واحدة ضمن أول رسالة (wrap_resume_text من
# agent.py)، وباقي الطلبات نصوص عادية يبنيها كل زر خدمة.
if "history" not in st.session_state:
    st.session_state.history = []
if "pending_prefix" not in st.session_state:
    st.session_state.pending_prefix = ""
if "processed_pdf_name" not in st.session_state:
    st.session_state.processed_pdf_name = None
if "request_count" not in st.session_state:
    st.session_state.request_count = 0
if "last_result" not in st.session_state:
    st.session_state.last_result = None


def extract_improved_resume(history_slice: list) -> str | None:
    """يلتقط نص السيرة المحسّنة من نتيجة improve_resume في مقطع history
    الخاص بهذا الدور فقط — عرض ومعاينة فقط، لا كتابة على أي ملف."""
    for content in history_slice:
        for part in content.parts:
            if part.function_response and part.function_response.name == "improve_resume":
                result = (part.function_response.response or {}).get("result", {})
                if isinstance(result, dict) and result.get("improved_resume"):
                    return result["improved_resume"]
    return None


def extract_latest_jobs(history: list) -> list[dict]:
    """يلتقط قائمة الوظائف من آخر نتيجة search_jobs في المحادثة — لتعبئة
    القوائم المنسدلة في بطاقات التقييم/التحسين/الخطاب. عرض فقط، لا قرار."""
    for content in reversed(history):
        for part in content.parts:
            if part.function_response and part.function_response.name == "search_jobs":
                result = (part.function_response.response or {}).get("result", {})
                if isinstance(result, dict) and result.get("jobs"):
                    return result["jobs"]
    return []


def send_to_agent(message: str) -> None:
    """المسار الوحيد لأي طلب في هذي الواجهة: يبني نص الطلب فقط ويسلّمه لـ
    run_agent() — القرار الكامل (أي أداة، متى، وبأي معطيات) يبقى عند
    النموذج نفسه، تماماً كحلقة الوكيل الأصلية في agent.py."""
    if st.session_state.request_count >= MAX_REQUESTS_PER_SESSION:
        return

    message_to_send = st.session_state.pending_prefix + message
    st.session_state.pending_prefix = ""
    turn_start = len(st.session_state.history)

    with st.spinner("جارٍ التفكير وتنفيذ الأدوات اللازمة..."):
        reply, updated_history = run_agent(message_to_send, st.session_state.history)

    st.session_state.history = updated_history
    st.session_state.request_count += 1

    turn_slice = updated_history[turn_start:]
    needs_review = any(
        part.function_call and part.function_call.name in REVIEW_TOOLS
        for content in turn_slice
        for part in content.parts
    )

    st.session_state.last_result = {
        "request": message,
        "reply": reply,
        "needs_review": needs_review,
        "improved_resume": extract_improved_resume(turn_slice),
    }
    st.rerun()


# ------------------------------------------------------------------
# الشريط العلوي
# ------------------------------------------------------------------
with st.container(key="topbar", horizontal=True):
    with st.container(key="topbar_brand", horizontal=True):
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=36)
        st.html('<div class="topbar-title">CareerPilot</div>')
    st.html(
        f'<div class="counter-pill">الطلبات: '
        f'{st.session_state.request_count} / {MAX_REQUESTS_PER_SESSION}</div>'
    )

# ------------------------------------------------------------------
# Hero
# ------------------------------------------------------------------
with st.container(key="hero"):
    if LOGO_PATH.exists():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(str(LOGO_PATH), width=160)
    st.html('<div class="hero-title">ابدأ رحلتك المهنية</div>')
    st.html('<div class="hero-subtitle">مرشدك الذكي يبحث ويقيّم ويكتب نيابة عنك — بموافقتك دائماً</div>')

# ------------------------------------------------------------------
# منطقة رفع السيرة
# ------------------------------------------------------------------
resume_ready = bool(st.session_state.processed_pdf_name)

if not resume_ready:
    with st.container(key="upload_card"):
        st.html(
            f'<div class="service-title">{icon("arrow-up", "#D3A0FD")} ارفعي سيرتك الذاتية للبدء</div>'
        )
        st.html('<div class="service-desc">هذي الخطوة الأولى الإلزامية — بعدها تتفعّل كل الخدمات أدناه.</div>')
        uploaded_pdf = st.file_uploader(
            "ملف PDF لسيرتك الذاتية", type=["pdf"], label_visibility="collapsed"
        )
        if uploaded_pdf is not None:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_pdf.getvalue())
                    tmp_path = tmp.name
                resume_text = extract_resume_text(tmp_path)
                st.session_state.pending_prefix = wrap_resume_text(resume_text)
                st.session_state.processed_pdf_name = uploaded_pdf.name
                st.rerun()
            except Exception as exc:
                st.error(f"تعذّر استخراج نص PDF: {exc}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
else:
    with st.container(key="confirm_card", horizontal=True, vertical_alignment="center"):
        st.html(icon("check", "#3F7A34", 28))
        with st.container():
            st.html(f'<div class="confirm-title">تم رفع السيرة الذاتية</div>')
            st.html(f'<div class="confirm-sub">{st.session_state.processed_pdf_name}</div>')

# ------------------------------------------------------------------
# شبكة بطاقات الخدمات
# ------------------------------------------------------------------
limit_reached = st.session_state.request_count >= MAX_REQUESTS_PER_SESSION
disabled = (not resume_ready) or limit_reached
available_jobs = extract_latest_jobs(st.session_state.history)
job_labels = [f"{j.get('title', '')} — {j.get('company', '')}" for j in available_jobs]


def job_service_card(key: str, icon_name: str, title: str, desc: str, message_builder, button_label: str):
    with st.container(key=key, width=380):
        st.html(f'<div class="service-title">{icon(icon_name, "#8B5CF6" if not disabled else "#B9B9B9")} {title}</div>')
        st.html(f'<div class="service-desc">{desc}</div>')
        if not resume_ready:
            st.html('<div class="disabled-badge">ارفعي سيرتك أولاً</div>')
        no_jobs = not job_labels
        if no_jobs and resume_ready:
            st.html('<div class="disabled-badge">ابحثي عن وظائف أولاً</div>')
        selected_index = st.selectbox(
            "الوظيفة",
            options=range(len(job_labels)) if job_labels else [0],
            format_func=lambda i: job_labels[i] if job_labels else "لا توجد نتائج بحث بعد",
            key=f"{key}_select",
            disabled=disabled or no_jobs,
            label_visibility="collapsed",
        )
        if st.button(button_label, key=f"{key}_btn", disabled=disabled or no_jobs, width="stretch"):
            job = available_jobs[selected_index]
            send_to_agent(message_builder(job))


row1 = st.container(horizontal=True)
row2 = st.container(horizontal=True)

with row1:
    with st.container(key="service_titles", width=380):
        st.html(f'<div class="service-title">{icon("sparkle", "#8B5CF6" if not disabled else "#B9B9B9")} اقتراح مسميات وظيفية</div>')
        st.html('<div class="service-desc">تحليل سيرتك واقتراح مسميات تناسب خبراتك.</div>')
        if not resume_ready:
            st.html('<div class="disabled-badge">ارفعي سيرتك أولاً</div>')
        if st.button("اقترح لي مسميات", key="titles_btn", disabled=disabled, width="stretch"):
            send_to_agent("حلل سيرتي واقترح مسميات وظيفية تناسبني")

    with st.container(key="service_search", width=380):
        st.html(f'<div class="service-title">{icon("search", "#8B5CF6" if not disabled else "#B9B9B9")} البحث عن وظائف</div>')
        st.html('<div class="service-desc">ابحثي عن وظائف حقيقية حسب المسمى والمدينة.</div>')
        if not resume_ready:
            st.html('<div class="disabled-badge">ارفعي سيرتك أولاً</div>')
        search_title = st.text_input("المسمى الوظيفي", key="search_title", disabled=disabled, label_visibility="collapsed", placeholder="المسمى الوظيفي")
        search_city = st.text_input("المدينة", key="search_city", disabled=disabled, label_visibility="collapsed", placeholder="المدينة")
        if st.button("ابحث الآن", key="search_btn", disabled=disabled, width="stretch"):
            if not search_title.strip() or not search_city.strip():
                st.warning("أدخلي المسمى الوظيفي والمدينة أولاً.")
            else:
                send_to_agent(f"ابحث لي عن وظائف {search_title.strip()} في {search_city.strip()}")

    with st.container(key="service_applications", width=380):
        st.html(f'<div class="service-title">{icon("list", "#8B5CF6" if not disabled else "#B9B9B9")} تقديماتي</div>')
        st.html('<div class="service-desc">ملخص الوظائف اللي سجّلتِ تقديمك عليها.</div>')
        if not resume_ready:
            st.html('<div class="disabled-badge">ارفعي سيرتك أولاً</div>')
        if st.button("اعرض تقديماتي", key="apps_btn", disabled=disabled, width="stretch"):
            send_to_agent("اعرض ملخص تقديماتي")

with row2:
    job_service_card(
        "service_match", "check", "تقييم التوافق",
        "قيّمي مدى توافق سيرتك مع وظيفة من نتائج بحثك.",
        lambda job: f"قيّم توافق سيرتي مع وظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "قيّم التوافق",
    )
    job_service_card(
        "service_improve", "star4", "تحسين السيرة الذاتية (ATS)",
        "حسّني سيرتك لتتوافق مع وظيفة محددة بصياغة متوافقة مع ATS.",
        lambda job: f"حسّن سيرتي الذاتية لتتوافق مع وظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "حسّن سيرتي",
    )
    job_service_card(
        "service_letter", "letter", "خطاب تقديم",
        "خطاب تقديم مخصص مبني على سيرتك الحقيقية.",
        lambda job: f"اكتب لي خطاب تقديم لوظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "اكتب الخطاب",
    )

if limit_reached:
    st.info(
        f"وصلتِ للحد الأقصى من الطلبات لهذي الجلسة ({MAX_REQUESTS_PER_SESSION} طلبات). "
        "أعيدي تحميل الصفحة لبدء جلسة جديدة — شكراً لتجربتك CareerPilot."
    )

# ------------------------------------------------------------------
# منطقة النتائج
# ------------------------------------------------------------------
with st.container(key="results_card"):
    result = st.session_state.last_result
    if result is None:
        st.html('<div class="results-empty">نتائج الخدمة اللي تختارينها تظهر هنا.</div>')
    else:
        if result["needs_review"]:
            with st.container(key="review_box"):
                st.html(f'<div class="review-title">{icon("sparkle", "#8B7B00")} يحتاج مراجعتك</div>')
                st.write(result["reply"])
        else:
            st.write(result["reply"])

        if result.get("improved_resume"):
            with st.expander("معاينة السيرة المحسّنة"):
                st.text(result["improved_resume"])
            st.download_button(
                "تحميل السيرة المحسّنة (ملف نصي جديد)",
                data=result["improved_resume"],
                file_name="improved_resume.txt",
                mime="text/plain",
                key="download_improved",
            )
