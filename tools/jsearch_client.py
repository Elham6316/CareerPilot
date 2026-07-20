"""عميل JSearch (عبر RapidAPI) — مصدر ثانٍ للبحث عن وظائف يُدمَج مع Jooble
في tools/job_search.py، لا يستبدله. يُرجع دائماً قائمة (فارغة عند أي فشل)
بدل رفع استثناء — لا يجب أن يُسقط تدفق البحث كاملاً لو JSearch نفسه فشل
(حد سرعة، شبكة، مفتاح غير صالح)."""

import html
import os
import re

import requests

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_API_HOST = "jsearch.p.rapidapi.com"


def _clean_snippet(text: str) -> str:
    """نفس تنظيف _clean_snippet في job_search.py — وسوم HTML/كيانات ومسافات
    زائدة، مكرَّرة هنا محلياً عمداً بدل استيراد متبادل بين الوحدتين."""
    cleaned = html.unescape(text or "")
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _job_location(job: dict) -> str:
    """يبني نص موقع مقروء من حقول JSearch المنفصلة (مدينة/ولاية/دولة) —
    يتخطى الأجزاء الفاضية بدل ترك فواصل يتيمة."""
    parts = [job.get("job_city"), job.get("job_state"), job.get("job_country")]
    return ", ".join(p for p in parts if p)


def search_jsearch(query: str, location: str | None = None) -> list[dict]:
    """يبحث عن وظائف عبر JSearch API، ويرجع نتائج بنفس شكل Jooble الداخلي
    (title, company, location, link, snippet) ليتعامل الكود اللاحق معهما
    كمصدر واحد موحّد. أي فشل (مفتاح ناقص/غير صالح، حد سرعة، شبكة، رد غير
    متوقع) يُرجع قائمة فارغة مع تسجيل السبب — لا يرفع استثناء أبداً."""
    api_key = os.environ.get("JSEARCH_API_KEY")
    if not api_key:
        print("[jsearch_client] JSEARCH_API_KEY غير موجود في .env — تخطي مصدر JSearch.")
        return []

    search_text = f"{query} in {location}" if location else query
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": JSEARCH_API_HOST}
    params = {"query": search_text, "num_pages": "1"}

    try:
        response = requests.get(JSEARCH_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"[jsearch_client] فشل الاتصال بـ JSearch API: {exc}")
        return []
    except ValueError as exc:
        print(f"[jsearch_client] رد JSearch غير قابل للقراءة (JSON): {exc}")
        return []

    jobs = data.get("data") or []
    if not isinstance(jobs, list):
        print(f"[jsearch_client] شكل رد JSearch غير متوقَّع (data ليست قائمة): {type(jobs)}")
        return []

    try:
        return [
            {
                "title": job.get("job_title", ""),
                "company": job.get("employer_name", ""),
                "location": _job_location(job),
                "link": job.get("job_apply_link") or job.get("job_google_link", ""),
                "snippet": _clean_snippet(job.get("job_description", "")),
                "source": "JSearch",
            }
            for job in jobs
        ]
    except (AttributeError, TypeError) as exc:
        # عنصر واحد مشوَّه بالرد لا يجب أن يُسقط كل نتائج JSearch — لكن هذا
        # يعني تركيبة غير متوقعة بالكامل، فالأسلم إرجاع فارغة والتسجيل.
        print(f"[jsearch_client] تعذّر تحليل عناصر رد JSearch: {exc}")
        return []
