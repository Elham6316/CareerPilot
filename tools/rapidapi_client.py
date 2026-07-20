"""عملاء RapidAPI — مصدر ثانٍ للبحث عن وظائف يُدمَج مع Jooble في
tools/job_search.py، لا يستبدله. يستخدمان نفس مفتاح RapidAPI الواحد
(RAPIDAPI_KEY في .env) لمنتجين مختلفين، كل واحد بـX-RapidAPI-Host خاص
به. **المفتاح يُقرأ من .env فقط — لا يُكتب حرفياً بأي مكان بهذا الملف
ولا يُطبَع كاملاً بأي رسالة تسجيل (rule 0 في CLAUDE.md).**

كلا العميلين يتبعان نفس فلسفة الصمود المعتمدة بالمشروع: أي فشل (مفتاح
ناقص، اشتراك غير مُفعَّل، حد سرعة، شبكة، شكل رد غير متوقَّع) يُرجع قائمة
فارغة مع تسجيل السبب — لا يرفعان استثناءً أبداً، فلا يُسقط فشل مصدر
واحد تدفق البحث الموحَّد كاملاً."""

import html
import os
import re

import requests

INDEED_SCRAPER_API_URL = "https://indeed-scraper-api.p.rapidapi.com/api/job"
INDEED_SCRAPER_API_HOST = "indeed-scraper-api.p.rapidapi.com"

ACTIVE_JOBS_DB_API_URL = "https://active-jobs-db.p.rapidapi.com/active-ats"
ACTIVE_JOBS_DB_API_HOST = "active-jobs-db.p.rapidapi.com"


def _clean_snippet(text: str) -> str:
    """نفس تنظيف _clean_snippet في job_search.py — مكرَّرة هنا محلياً عمداً
    بدل استيراد متبادل بين الوحدتين."""
    cleaned = html.unescape(text or "")
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _first_present(d: dict, *keys, default=""):
    """يرجع أول قيمة غير فاضية من عدة أسماء حقول محتملة — الاستخدام هنا
    عمدي: شكل رد Indeed Scraper API/Active Jobs DB الدقيق غير موثَّق
    رسمياً بثبات، فهذا يحمي التحليل من أسماء حقول بديلة شائعة بدل الفشل
    الصامت (قائمة فارغة) لمجرد اختلاف تسمية حقل واحد غير جوهري."""
    for key in keys:
        val = d.get(key)
        if val:
            return val
    return default


def search_indeed_scraper(query: str, location: str | None = None) -> list[dict]:
    """المصدر الأساسي الجديد: Indeed Scraper API. يبحث بمسمى وظيفي داخل
    السعودية تحديداً (country='sa' ثابت — هذا التطبيق يستهدف سوق العمل
    السعودي فقط حسب النطاق الحالي)، ويرجع نتائج بشكل داخلي موحَّد."""
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        print("[rapidapi_client] RAPIDAPI_KEY غير موجود في .env — تخطي مصدر Indeed Scraper.")
        return []

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": INDEED_SCRAPER_API_HOST,
        "Content-Type": "application/json",
    }
    payload = {
        "scraper": {
            "maxRows": 10,
            "query": query,
            "location": location or "",
            "country": "sa",
            "sort": "relevance",
            "fromDays": "14",
        }
    }

    try:
        response = requests.post(INDEED_SCRAPER_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"[rapidapi_client] فشل الاتصال بـ Indeed Scraper API: {exc}")
        return []
    except ValueError as exc:
        print(f"[rapidapi_client] رد Indeed Scraper غير قابل للقراءة (JSON): {exc}")
        return []

    # الشكل الفعلي (مؤكَّد باستدعاء حي فعلي، لا توثيق رسمي — هذا المنتج
    # يعمل كطابور مهام: الرد الأعلى هو حالة المهمة نفسها {state, id,
    # progress, ...}، والنتائج الفعلية متداخلة بمستوى إضافي داخل
    # returnvalue.data (قائمة)، لا returnvalue مباشرةً كما افتُرض أولاً).
    jobs = None
    if isinstance(data, dict):
        returnvalue = data.get("returnvalue")
        if isinstance(returnvalue, dict) and isinstance(returnvalue.get("data"), list):
            jobs = returnvalue["data"]
        elif isinstance(returnvalue, list):
            jobs = returnvalue
        elif isinstance(data.get("data"), list):
            jobs = data["data"]
    elif isinstance(data, list):
        jobs = data
    if jobs is None:
        print(f"[rapidapi_client] شكل رد Indeed Scraper غير متوقَّع: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return []

    try:
        results = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = _first_present(job, "title", "positionName", "jobTitle")
            # حقل اسم الشركة غير موجود إطلاقاً بهذا المنتج/المستوى الحالي
            # (تحقّق فعلي: companyCeo.name وcompanyAddresses فاضيان بكل
            # النتائج المُختبَرة) — تُترَك فاضية بدل اختلاق اسم، بدل تعطّل.
            company = _first_present(job, "company", "companyName", "employer")
            raw_location = job.get("location")
            if isinstance(raw_location, dict):
                job_location = _first_present(
                    raw_location, "formattedAddressShort", "formattedAddressLong", "city"
                )
            else:
                job_location = raw_location or ""
            link = _first_present(job, "jobUrl", "url", "link")
            snippet = _clean_snippet(_first_present(job, "descriptionText", "descriptionHtml"))
            if not title:
                continue
            results.append(
                {
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "link": link,
                    "snippet": snippet,
                    "source": "Indeed",
                }
            )
        return results
    except (AttributeError, TypeError) as exc:
        print(f"[rapidapi_client] تعذّر تحليل عناصر رد Indeed Scraper: {exc}")
        return []


def search_active_jobs_db(query: str, location: str | None = None) -> list[dict]:
    """المصدر الثانوي: Active Jobs DB. يُستخدَم فقط لو جودة رده جيدة —
    القرار الفعلي (هل يُدمَج بالنتيجة النهائية) يُتَّخذ داخل job_search.py
    بعد مقارنة عدد/جودة نتائجه، لا هنا. هذه الدالة فقط تُرجع ما استطاعت
    جلبه بصمود، بلا استثناء."""
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        print("[rapidapi_client] RAPIDAPI_KEY غير موجود في .env — تخطي مصدر Active Jobs DB.")
        return []

    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": ACTIVE_JOBS_DB_API_HOST}
    # time_frame مطلوب إلزامياً (تحقّق حي: 400 "Missing or invalid
    # 'time_frame' parameter" بلا هذا الحقل — لم يكن مذكوراً بمواصفة
    # الـAPI الأصلية المُعطاة). "7d" اختيار متوازن (نافذة زمنية حديثة نسبياً
    # بلا تضييق مبالَغ فيه)، من القيم الأربع المسموحة (1h/24h/7d/6m).
    params = {"title": query, "time_frame": "7d"}
    if location:
        params["location"] = location

    try:
        response = requests.get(ACTIVE_JOBS_DB_API_URL, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"[rapidapi_client] فشل الاتصال بـ Active Jobs DB API: {exc}")
        return []
    except ValueError as exc:
        print(f"[rapidapi_client] رد Active Jobs DB غير قابل للقراءة (JSON): {exc}")
        return []

    jobs = None
    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict):
        for key in ("jobs", "data", "results"):
            if isinstance(data.get(key), list):
                jobs = data[key]
                break
    if jobs is None:
        print(f"[rapidapi_client] شكل رد Active Jobs DB غير متوقَّع: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return []

    try:
        results = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = _first_present(job, "title", "positionName")
            company = _first_present(job, "organization", "company", "companyName")
            # الشكل الفعلي (مؤكَّد باستدعاء حي): "locations_derived" قائمة
            # نصوص جاهزة مُنسَّقة بالكامل ("Riyadh, Riyadh Region, Saudi
            # Arabia") — أدق بكثير من "cities_derived" (اسم مدينة مجرَّد
            # فقط)، لذا تُجرَّب أولاً. لا حقل وصف/snippet متاح إطلاقاً بهذا
            # المنتج (بيانات وصفية فقط) — يبقى فاضياً بصمت، لا اختلاق.
            job_location = _first_present(job, "locations_derived", "locations_raw", "cities_derived", "location")
            if isinstance(job_location, list):
                job_location = ", ".join(str(x) for x in job_location if x)
            elif isinstance(job_location, dict):
                job_location = _first_present(job_location, "address_locality", "address_region", "address_country")
            link = _first_present(job, "url", "link")
            snippet = _clean_snippet(_first_present(job, "description", "snippet"))
            if not title:
                continue
            results.append(
                {
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "link": link,
                    "snippet": snippet,
                    "source": "ActiveJobsDB",
                }
            )
        return results
    except (AttributeError, TypeError) as exc:
        print(f"[rapidapi_client] تعذّر تحليل عناصر رد Active Jobs DB: {exc}")
        return []
