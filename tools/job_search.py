"""أدوات متعلقة بالبحث عن وظائف: اقتراح المسميات الوظيفية والبحث عبر Jooble."""

import json

from google.genai import types

from tools.gemini_client import MODEL_NAME, get_client

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
