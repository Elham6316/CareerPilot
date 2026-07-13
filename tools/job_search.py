"""أدوات متعلقة بالبحث عن وظائف: اقتراح المسميات الوظيفية والبحث عبر Jooble."""

import html
import json
import os
import re

import requests
from google.genai import types

from tools.gemini_client import MODEL_NAME, get_client

JOOBLE_API_URL = "https://jooble.org/api/{key}"

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


def search_jobs(query: str, location: str | None = None) -> dict:
    """يبحث عن وظائف حقيقية عبر Jooble API بناءً على مسمى وظيفي وموقع اختياري."""
    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        return {"error": "JOOBLE_API_KEY غير موجود في .env"}

    payload = {"keywords": query}
    if location:
        payload["location"] = location

    try:
        response = requests.post(JOOBLE_API_URL.format(key=api_key), json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return {"error": f"فشل الاتصال بـ Jooble API: {exc}"}
    except ValueError as exc:
        return {"error": f"رد Jooble غير قابل للقراءة: {exc}"}

    jobs = data.get("jobs", [])
    if not jobs:
        return {
            "jobs": [],
            "message": (
                f"لا توجد نتائج لـ '{query}'"
                + (f" في '{location}'" if location else "")
                + " — جرّب مسمى وظيفياً أو موقعاً أوسع."
            ),
        }

    results = [
        {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "link": job.get("link", ""),
            "snippet": _clean_snippet(job.get("snippet", "")),
        }
        for job in jobs[:10]
    ]
    return {"jobs": results, "total_count": data.get("totalCount", len(results))}
