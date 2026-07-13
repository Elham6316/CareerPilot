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


SUGGEST_EDITS_PROMPT = """أنت خبير في كتابة السير الذاتية. اقترح صياغة جديدة
لقسم "{target_section}" فقط من السيرة الذاتية التالية، بحيث تبرز نقاط
التوافق الحقيقية مع الوظيفة المستهدفة أدناه.

تحذير صارم وغير قابل للتفاوض: ممنوع اختلاق أي خبرة، مهارة، مسمى وظيفي،
شركة، رقم، أو إنجاز غير موجود أصلاً في نص السيرة الذاتية أدناه. يُسمح فقط
بإعادة الصياغة أو إعادة الترتيب أو التأكيد على ما هو موجود فعلاً فيها —
ممنوع إضافة أي معلومة جديدة مهما بدت منطقية أو محتملة.

أرجع نص القسم المقترح فقط، بدون أي شرح أو مقدمة أو JSON.

نص السيرة الذاتية الكامل (للسياق):
---
{resume_text}
---

القسم المطلوب تعديل صياغته: {target_section}

وصف الوظيفة المستهدفة:
---
{job_description}
---
"""


def suggest_resume_edits(job_description: str, resume_text: str, target_section: str = "summary") -> dict:
    """يقترح صياغة جديدة لقسم من السيرة الذاتية دون اختلاق معلومات. اقتراح
    للعرض فقط — لا يكتب على أي ملف (rule 5 في CLAUDE.md)."""
    if not job_description or not job_description.strip():
        return {"error": "وصف الوظيفة فاضي — أعطني وصف الوظيفة المطلوب التعديل من أجلها أولاً."}

    if not resume_text or not resume_text.strip():
        return {"error": "لا توجد سيرة ذاتية متاحة لتعديلها."}

    prompt = SUGGEST_EDITS_PROMPT.format(
        resume_text=resume_text, job_description=job_description, target_section=target_section
    )

    response = get_client().models.generate_content(model=MODEL_NAME, contents=prompt)

    return {
        "target_section": target_section,
        "suggested_text": response.text.strip(),
        "note": "هذا اقتراح للعرض فقط — لن يُكتب على أي ملف إلا بموافقتك الصريحة.",
    }
