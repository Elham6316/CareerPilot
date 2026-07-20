"""أدوات متعلقة بالبحث عن وظائف: اقتراح المسميات الوظيفية والبحث عبر Jooble."""

import html
import json
import os
import re

import requests
from google.genai import types

from tools.gemini_client import MODEL_NAME, get_client
from tools.rapidapi_client import search_active_jobs_db, search_indeed_scraper

JOOBLE_API_URL = "https://jooble.org/api/{key}"
MAX_COMBINED_RESULTS = 10

SUGGEST_TITLES_PROMPT = """حلّل نص السيرة الذاتية التالي واقترح 3 إلى 5 مسميات
وظيفية مناسبة لصاحبها بناءً على خبراته ومهاراته الفعلية الظاهرة في النص.

اكتب المسميات بنفس لغة السيرة الذاتية (عربي أو إنجليزي).

أرجع النتيجة بصيغة JSON فقط، كمصفوفة نصوص، بدون أي شرح إضافي. مثال:
["Backend Developer", "Data Analyst"]

نص السيرة الذاتية:
---
{resume_text}
---
"""


def suggest_job_titles(resume_text: str) -> dict:
    """يحلل نص السيرة الذاتية ويقترح 3-5 مسميات وظيفية مناسبة."""
    prompt = SUGGEST_TITLES_PROMPT.format(resume_text=resume_text)

    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    titles = json.loads(response.text)
    return {"suggested_titles": titles}


def _clean_snippet(snippet: str) -> str:
    """يزيل وسوم HTML وكيانات مثل &nbsp; من مقتطف Jooble."""
    text = html.unescape(snippet or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# علة حقيقية اكتُشفت بالجولة السابقة: مطابقة المدينة كانت مقارنة نصية
# صرفة، فتفشل رغم تطابق المدينة فعلياً لو استخدم أحد المصادر (Indeed
# تحديداً) تهجئة نقل حرفي مختلفة عن التي يُطبِّعها Gemini لطلب المستخدم
# (مثال حي مُختبَر: نتائج "Mecca" من Indeed لم تُطابِق طلب "Makkah" رغم
# كونهما نفس المدينة بالضبط). كل مفتاح هنا صيغة بديلة شائعة تُطابَق
# نصياً، وقيمته الصيغة الموحَّدة (canonical) التي تُستبدَل بها قبل أي
# مقارنة — تُطبَّق على طلب المستخدم وموقع كل نتيجة معاً بنفس الدالة، فلا
# يهم أي جهة كتبت أياً من الصيغتين.
CITY_ALIASES = {
    "mecca": "makkah",
    "medina": "madinah",
    "al-madinah": "madinah",
    "al madinah": "madinah",
    "jiddah": "jeddah",
}


def _normalize_city(text: str) -> str:
    """يوحّد تهجئات النقل الحرفي الشائعة لمدن سعودية داخل نص (طلب المستخدم
    أو حقل location لنتيجة) قبل أي مقارنة تطابق مدينة — بحروف صغيرة دائماً
    لضمان مقارنة غير حساسة لحالة الأحرف أيضاً."""
    normalized = (text or "").lower()
    for variant, canonical in CITY_ALIASES.items():
        normalized = normalized.replace(variant, canonical)
    return normalized


def _search_jooble(query: str, location: str | None) -> list[dict]:
    """يبحث عبر Jooble فقط، ويرجع قائمة بنفس الشكل الموحَّد (لا dict كامل
    بعد الآن) — أي فشل (مفتاح ناقص، شبكة، رد غير مقروء) يُرجع قائمة فارغة
    مع تسجيل السبب بدل رفع استثناء، بنفس نمط rapidapi_client، فلا يُسقِط
    مصدر واحد فاشل تدفق البحث الموحَّد كاملاً."""
    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        print("[job_search] JOOBLE_API_KEY غير موجود في .env — تخطي مصدر Jooble.")
        return []

    payload = {"keywords": query}
    if location:
        payload["location"] = location

    try:
        response = requests.post(JOOBLE_API_URL.format(key=api_key), json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"[job_search] فشل الاتصال بـ Jooble API: {exc}")
        return []
    except ValueError as exc:
        print(f"[job_search] رد Jooble غير قابل للقراءة: {exc}")
        return []

    jobs = data.get("jobs", [])
    return [
        {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "link": job.get("link", ""),
            "snippet": _clean_snippet(job.get("snippet", "")),
            "source": "Jooble",
        }
        for job in jobs
    ]


def _dedupe_merge(job_lists: list[list[dict]], requested_city: str) -> list[dict]:
    """يدمج عدة قوائم (بترتيب أولوية: Jooble ثم Indeed Scraper ثم Active
    Jobs DB) ويُزيل التكرار بمفتاح (العنوان، الشركة) بحروف صغيرة. عند
    وجود نفس الوظيفة بأكثر من مصدر: تُفضَّل أي نسخة موقعها الفعلي يحوي
    اسم المدينة المطلوبة حرفياً (أدق جغرافياً — لا يهم أي مصدر بالتحديد،
    المعيار هو التطابق الفعلي لا اسم المصدر)، وإلا تبقى أول نسخة ظهرت
    حسب ترتيب job_lists. requested_city يُتوقَّع أن يصل مُطبَّعاً مسبقاً
    (_normalize_city) من الطرف المستدعي؛ موقع كل نتيجة يُطبَّع هنا وقت
    المقارنة نفسها."""
    merged: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []

    for jobs in job_lists:
        for job in jobs:
            key = (job["title"].strip().lower(), job["company"].strip().lower())
            if key not in merged:
                merged[key] = job
                order.append(key)
                continue

            existing = merged[key]
            new_matches_city = bool(requested_city) and requested_city in _normalize_city(job["location"])
            existing_matches_city = bool(requested_city) and requested_city in _normalize_city(existing["location"])
            if new_matches_city and not existing_matches_city:
                merged[key] = job

    return [merged[k] for k in order]


def search_jobs(query: str, location: str | None = None) -> dict:
    """يبحث عن وظائف حقيقية عبر 3 مصادر مدموجة: Jooble (أساسي أصلي)،
    Indeed Scraper API (أساسي جديد)، وActive Jobs DB (ثانوي — يُستدعى
    دائماً لكن نتائجه لا تُدمَج فعلياً إلا لو أرجع نتائج فعلية صالحة؛
    "جودة الرد" هنا تعني تحديداً: رد ناجح ببنية مفهومة يحوي عنصراً واحداً
    على الأقل بعنوان وظيفي — أي رد فاشل/فارغ/مشوَّه أصلاً يُقصى ذاتياً
    عبر آلية الصمود بـrapidapi_client.py، فلا حاجة لمنطق فحص جودة منفصل
    هنا). فشل أي مصدر واحد لا يُسقط البقية، بنفس فلسفة "أبلِغ الخطأ
    للنموذج كنتيجة أداة عادية" (CLAUDE.md rule 6)."""
    jooble_jobs = _search_jooble(query, location)
    indeed_jobs = search_indeed_scraper(query, location)
    active_jobs = search_active_jobs_db(query, location)

    requested_city = _normalize_city(location.split(",")[0].strip()) if location else ""
    merged = _dedupe_merge([jooble_jobs, indeed_jobs, active_jobs], requested_city)

    if not merged:
        return {
            "jobs": [],
            "message": (
                f"لا توجد نتائج لـ '{query}'"
                + (f" في '{location}'" if location else "")
                + " — جرّب مسمى وظيفياً أو موقعاً أوسع."
            ),
        }

    results = merged[:MAX_COMBINED_RESULTS]
    output = {"jobs": results, "total_count": len(merged)}

    # علة حقيقية اكتُشفت بالقياس (لا افتراض) بجولة سابقة: نفس نتائج Jooble
    # بالضبط تتكرر لأي مدينة سعودية مع مسميات معينة، لأن إعلانات Jooble
    # نفسها مُصنَّفة بمستوى الدولة فقط لا المدينة أحياناً. أُضيف مصدران
    # إضافيان (Indeed Scraper، Active Jobs DB) تحديداً لهذا — فالتوضيح هنا
    # لا يظهر لمجرد فشل مصدر واحد بمطابقة المدينة، بل فقط لو **كل
    # المصادر الثلاثة معاً** لم ترجع أي نتيجة تحوي اسم المدينة المطلوبة
    # صراحةً بحقل location الفعلي.
    if requested_city:
        city_matched = any(requested_city in _normalize_city(r["location"]) for r in results)
        if not city_matched:
            output["note"] = (
                f"نتائج البحث هنا (من كل مصادر البيانات المتاحة) مُصنَّفة على "
                f"مستوى الدولة لا المدينة تحديداً لهذا المسمى — إعلانات '{query}' "
                f"المتاحة فعلياً في '{location}' محدودة جداً بمصادر البيانات "
                "نفسها، لذا قد تظهر نفس النتائج مع مدن أخرى قريبة بنفس الدولة. "
                "جرّب مسمى أوسع لنتائج أكثر تحديداً جغرافياً."
            )

    return output
