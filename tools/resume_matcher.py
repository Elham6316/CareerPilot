"""تقييم توافق وظيفة مع السيرة الذاتية عبر تحليل دلالي حقيقي بـ Gemini."""

import json

from google.genai import types

from tools.gemini_client import MODEL_NAME, get_client

EVALUATE_MATCH_PROMPT = """قارن وصف الوظيفة التالي بنص السيرة الذاتية، وقيّم
مدى توافقهما بتحليل دلالي حقيقي يفهم السياق (الخبرة، المهارات، التخصص) —
وليس مطابقة كلمات مفتاحية سطحية.

أرجع النتيجة بصيغة JSON فقط بالشكل التالي بالضبط:
{{"match_score": <رقم صحيح من 0 إلى 100>, "reasoning": "<سبب مختصر بجملتين
أو ثلاث، يذكر نقاط القوة ونقاط الضعف في التوافق إن وجدت>"}}

نص السيرة الذاتية:
---
{resume_text}
---

وصف الوظيفة:
---
{job_description}
---
"""


def evaluate_match(job_description: str, resume_text: str) -> dict:
    """يقيّم مدى توافق وصف وظيفة مع السيرة الذاتية، ويرجع match_score و reasoning."""
    if not job_description or not job_description.strip():
        return {"error": "وصف الوظيفة فاضي — أعطني وصف الوظيفة المطلوب تقييمها أولاً."}

    if not resume_text or not resume_text.strip():
        return {"error": "لا توجد سيرة ذاتية متاحة لمقارنتها بهذه الوظيفة."}

    prompt = EVALUATE_MATCH_PROMPT.format(resume_text=resume_text, job_description=job_description)

    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    result = json.loads(response.text)
    return {"match_score": result.get("match_score"), "reasoning": result.get("reasoning")}
