"""واجهة Streamlit فوق agent.py — منصة خدمات (service platform)، طبقة عرض
فقط. **لا يوجد هنا أي منطق قرار جديد**: كل زر خدمة يبني طلباً نصياً
بالعربية ويمرره لـ run_agent() نفسها، والوكيل (Gemini) يقرر بنفسه أي أداة
يستدعي وبأي تسلسل — تماماً كما لو كتب المستخدم نفس الطلب في محادثة حرة.
منطق agent.py وحلقة run_agent لم يُمس إطلاقاً."""

import base64
import os
import tempfile
from pathlib import Path

import streamlit as st

from agent import run_agent, wrap_resume_text
from tools.resume_parser import extract_resume_text

REVIEW_TOOLS = {"improve_resume", "draft_cover_letter"}
MAX_REQUESTS_PER_SESSION = 2
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

st.set_page_config(
    page_title="CareerPilot",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
)

# ------------------------------------------------------------------
# الهوية البصرية: الألوان الأساسية عبر .streamlit/config.toml، وهنا كل ما
# لا يغطيه theming الرسمي (تحديد عرض المحتوى، الـ hero المقسوم، الشبكة
# ثلاثية الأعمدة بارتفاع موحّد، تعريب نص رفع الملف، أيقونات SVG بدل
# الإيموجي). كل استهداف عبر key= لكل عنصر.
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

/* ---- عرض المحتوى: أقصى 1200px بالمنتصف، لا عمود ضيق ولا امتداد كامل ---- */
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1200px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 1rem !important;
}

/* ---- الشريط العلوي ---- */
.st-key-topbar {
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.25rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
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

/* ---- Hero: شريط كامل العرض مقسوم لنصفين ---- */
.st-key-hero {
    position: relative;
    overflow: hidden;
    background: var(--purple-light);
    border-radius: 28px;
    min-height: 280px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
}
.st-key-hero [data-testid="column"] { display: flex; align-items: center; }
.hero-text-col { position: relative; z-index: 2; }
.hero-title {
    font-weight: 700;
    font-size: 2.4rem;
    color: var(--text);
    margin: 1rem 0 0.4rem 0;
    line-height: 1.25;
}
.hero-subtitle { color: var(--muted); font-size: 1.05rem; margin-bottom: 1.25rem; }
.hero-cta {
    display: inline-block;
    background: var(--accent);
    color: var(--text) !important;
    font-weight: 700;
    text-decoration: none !important;
    padding: 0.7rem 1.6rem;
    border-radius: 999px;
    box-shadow: 0 6px 18px rgba(17, 17, 17, 0.10);
    transition: transform 0.15s ease;
}
.hero-cta:hover { transform: translateY(-1px); }

.hero-deco { position: relative; width: 100%; height: 220px; z-index: 1; }
.hero-deco .circle { position: absolute; border-radius: 50%; background: var(--secondary); }
.hero-deco .c1 { width: 180px; height: 180px; top: 0; right: 30px; opacity: 0.9; }
.hero-deco .c2 { width: 100px; height: 100px; bottom: 10px; right: 180px; opacity: 0.75; }
.hero-deco .c3 { width: 60px; height: 60px; top: 40px; right: 220px; opacity: 0.6; background: var(--primary); }
.hero-deco .c4 { width: 40px; height: 40px; bottom: 50px; right: 40px; opacity: 0.5; background: var(--primary); }

/* ---- منطقة رفع السيرة ---- */
#upload-section { position: relative; top: -90px; }
.st-key-upload_card {
    background: #FFFFFF;
    border: 2px dashed var(--primary);
    border-radius: 24px;
    padding: 1.75rem;
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

/* تعريب نص أداة الرفع الافتراضي: Streamlit يضع font-size الفعلي على
   عناصر span و p الداخلية نفسها (لا يرث من الأب)، فنفرض 0 بـ !important
   على كل الأحفاد مباشرة (نصوص وأيقونات الحروف)، ثم نضيف البديل العربي
   عبر before/after على الحاوية الخارجية فقط. */
.st-key-upload_card [data-testid="stFileUploaderDropzoneInstructions"] * {
    font-size: 0 !important;
    line-height: 0 !important;
    color: transparent !important;
}
.st-key-upload_card [data-testid="stFileUploaderDropzoneInstructions"] {
    position: relative;
    min-height: 2.4rem;
}
.st-key-upload_card [data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "اسحبي ملف PDF هنا أو اضغطي لاختياره — الحد الأقصى 200 ميغابايت";
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    font-size: 0.9rem !important;
    line-height: 1.4 !important;
    color: var(--text) !important;
}

.st-key-upload_card [data-testid="stBaseButton-secondary"] {
    position: relative;
    min-width: 110px;
    min-height: 2.2rem;
    background: var(--purple-light) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 10px !important;
}
.st-key-upload_card [data-testid="stBaseButton-secondary"] * {
    font-size: 0 !important;
    color: transparent !important;
}
.st-key-upload_card [data-testid="stBaseButton-secondary"]::after {
    content: "اختيار ملف";
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem !important;
    color: var(--text) !important;
    font-weight: 600;
}

/* ---- شبكة بطاقات الخدمات: st.columns(3) × 2، كل بطاقة بارتفاع موحّد بالضبط.
   300px كافية لأطول محتوى (بطاقة البحث بحقلين + زر)، وoverflow:hidden
   يضمن تطابق الارتفاع فعلياً بين كل البطاقات بغض النظر عن كمية المحتوى. */
[class*="st-key-service_"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 1.25rem;
    box-shadow: 0 6px 20px rgba(17, 17, 17, 0.04);
    min-height: 300px !important;
    height: 300px !important;
    max-height: 300px !important;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
[class*="st-key-service_"] > div:last-child { margin-top: auto; }

.service-title {
    font-weight: 700;
    color: var(--text);
    font-size: 1.02rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.2rem;
}
.service-desc { color: var(--muted); font-size: 0.83rem; margin-bottom: 0.6rem; }
.disabled-badge {
    display: inline-block;
    background: var(--purple-light);
    color: var(--muted);
    border-radius: 999px;
    padding: 0.15rem 0.7rem;
    font-size: 0.7rem;
    margin-bottom: 0.5rem;
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

/* الزر الأهم: تحسين السيرة — إطار وزر بلون الـ accent */
.st-key-service_improve {
    border: 2px solid var(--accent) !important;
}
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
    margin-top: 1rem;
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
# أيقونات SVG بسيطة inline — بدون أي إيموجي في كل الواجهة.
# st.html() يمرر المحتوى عبر DOMPurify اللي يحذف وسم <svg> كاملاً بصمت
# (تحقق فعلياً عبر اختبار معزول) — لذا نُرمّز الـ SVG كـ base64 data URI
# ونضمّنه بوسم <img> عادي بدل ذلك، وهو وسم مسموح دائماً.
def icon(name: str, color: str = "#D3A0FD", size: int = 22) -> str:
    paths = {
        "sparkle": '<path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z"/>',
        "search": '<circle cx="10" cy="10" r="6"/><line x1="21" y1="21" x2="14.5" y2="14.5"/>',
        "check": '<polyline points="4,12 9,17 20,6"/>',
        "arrow-up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
        "document": '<rect x="5" y="3" width="14" height="18" rx="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="12" y2="16"/>',
        "list": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        "star": '<path d="M12 2c0 5-2.5 7.5-7.5 7.5C9.5 9.5 12 12 12 17c0-5 2.5-7.5 7.5-7.5C14.5 9.5 12 7 12 2z"/>',
    }
    body = paths.get(name, "")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" '
        f'style="vertical-align:middle" alt="" />'
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
# Hero: شريط مقسوم لنصفين (نص + شعار | أشكال عضوية زخرفية)
# ------------------------------------------------------------------
with st.container(key="hero"):
    col_text, col_deco = st.columns([3, 2])
    with col_text:
        st.html('<div class="hero-text-col">')
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=110)
        st.html('<div class="hero-title">ابدأ رحلتك المهنية</div>')
        st.html(
            '<div class="hero-subtitle">مرشدك الذكي يبحث ويقيّم ويكتب نيابة عنك — '
            'بموافقتك دائماً</div>'
        )
        st.html('<a href="#upload-section" class="hero-cta">ارفعي سيرتك للبدء</a>')
        st.html('</div>')
    with col_deco:
        st.html(
            '<div class="hero-deco">'
            '<span class="circle c1"></span><span class="circle c2"></span>'
            '<span class="circle c3"></span><span class="circle c4"></span>'
            "</div>"
        )

# ------------------------------------------------------------------
# منطقة رفع السيرة
# ------------------------------------------------------------------
st.html('<div id="upload-section"></div>')
resume_ready = bool(st.session_state.processed_pdf_name)

if not resume_ready:
    with st.container(key="upload_card"):
        st.html(
            f'<div class="service-title">{icon("arrow-up")} ارفعي سيرتك الذاتية للبدء</div>'
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
            st.html('<div class="confirm-title">تم رفع السيرة الذاتية</div>')
            st.html(f'<div class="confirm-sub">{st.session_state.processed_pdf_name}</div>')

# ------------------------------------------------------------------
# شبكة بطاقات الخدمات: st.columns(3) مرتين → 3×2 حقيقية
# ------------------------------------------------------------------
limit_reached = st.session_state.request_count >= MAX_REQUESTS_PER_SESSION
disabled = (not resume_ready) or limit_reached
available_jobs = extract_latest_jobs(st.session_state.history)
job_labels = [f"{j.get('title', '')} — {j.get('company', '')}" for j in available_jobs]
icon_color = "#D3A0FD" if not disabled else "#B9B9B9"


def simple_service_card(key: str, icon_name: str, title: str, desc: str, body_fn) -> None:
    with st.container(key=key):
        st.html(f'<div class="service-title">{icon(icon_name, icon_color)} {title}</div>')
        st.html(f'<div class="service-desc">{desc}</div>')
        if not resume_ready:
            st.html('<div class="disabled-badge">ارفعي سيرتك أولاً</div>')
        with st.container():
            body_fn()


def job_service_card(key: str, icon_name: str, title: str, desc: str, message_builder, button_label: str) -> None:
    # ملاحظة مهمة: مفاتيح العناصر الداخلية يجب ألا تبدأ بنفس بادئة مفتاح
    # البطاقة ("service_") — محدد CSS الخاص بالبطاقات `[class*="st-key-service_"]`
    # مطابقة substring، فلو بدأ مفتاح الحقل الداخلي بنفس البادئة ستتضاعف
    # الأنماط (padding/border/height) على العنصر الداخلي أيضاً. نستخدم بادئة
    # مختلفة "job-" هنا عمداً لتفادي هذا التصادم.
    widget_ns = key.replace("service_", "job-")

    def body() -> None:
        no_jobs = not job_labels
        if no_jobs and resume_ready:
            st.html('<div class="disabled-badge">ابحثي عن وظائف أولاً</div>')
        selected_index = st.selectbox(
            "الوظيفة",
            options=range(len(job_labels)) if job_labels else [0],
            format_func=lambda i: job_labels[i] if job_labels else "لا توجد نتائج بحث بعد",
            key=f"{widget_ns}_select",
            disabled=disabled or no_jobs,
            label_visibility="collapsed",
        )
        if st.button(button_label, key=f"{widget_ns}_btn", disabled=disabled or no_jobs, width="stretch"):
            job = available_jobs[selected_index]
            send_to_agent(message_builder(job))

    simple_service_card(key, icon_name, title, desc, body)


row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    def titles_body() -> None:
        if st.button("اقترح لي مسميات", key="titles_btn", disabled=disabled, width="stretch"):
            send_to_agent("حلل سيرتي واقترح مسميات وظيفية تناسبني")

    simple_service_card(
        "service_titles", "sparkle", "اقتراح مسميات وظيفية",
        "تحليل سيرتك واقتراح مسميات تناسب خبراتك.", titles_body,
    )

with row1_col2:
    def search_body() -> None:
        search_title = st.text_input(
            "المسمى الوظيفي", key="search_title", disabled=disabled,
            label_visibility="collapsed", placeholder="المسمى الوظيفي",
        )
        search_city = st.text_input(
            "المدينة", key="search_city", disabled=disabled,
            label_visibility="collapsed", placeholder="المدينة",
        )
        if st.button("ابحث الآن", key="search_btn", disabled=disabled, width="stretch"):
            if not search_title.strip() or not search_city.strip():
                st.warning("أدخلي المسمى الوظيفي والمدينة أولاً.")
            else:
                send_to_agent(f"ابحث لي عن وظائف {search_title.strip()} في {search_city.strip()}")

    simple_service_card(
        "service_search", "search", "البحث عن وظائف",
        "ابحثي عن وظائف حقيقية حسب المسمى والمدينة.", search_body,
    )

with row1_col3:
    job_service_card(
        "service_match", "check", "تقييم التوافق",
        "قيّمي مدى توافق سيرتك مع وظيفة من نتائج بحثك.",
        lambda job: f"قيّم توافق سيرتي مع وظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "قيّم التوافق",
    )

row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    job_service_card(
        "service_improve", "star", "تحسين السيرة الذاتية (ATS)",
        "حسّني سيرتك لتتوافق مع وظيفة محددة بصياغة متوافقة مع ATS.",
        lambda job: f"حسّن سيرتي الذاتية لتتوافق مع وظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "حسّن سيرتي",
    )

with row2_col2:
    job_service_card(
        "service_letter", "document", "خطاب تقديم",
        "خطاب تقديم مخصص مبني على سيرتك الحقيقية.",
        lambda job: f"اكتب لي خطاب تقديم لوظيفة {job.get('title', '')} في شركة {job.get('company', '')}",
        "اكتب الخطاب",
    )

with row2_col3:
    def apps_body() -> None:
        if st.button("اعرض تقديماتي", key="apps_btn", disabled=disabled, width="stretch"):
            send_to_agent("اعرض ملخص تقديماتي")

    simple_service_card(
        "service_applications", "list", "تقديماتي",
        "ملخص الوظائف اللي سجّلتِ تقديمك عليها.", apps_body,
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
