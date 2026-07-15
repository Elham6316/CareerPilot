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


IMPROVE_RESUME_PROMPT = """أنت خبير في تحسين السير الذاتية وأنظمة تتبع
المتقدمين (ATS). حسّن السيرة الذاتية التالية تحسيناً شاملاً لتتواءم مع
الوظيفة المستهدفة أدناه: قسم الـ Summary وقسم الـ Skills وأي قسم آخر
يحتاج مواءمة.

متطلبات الصياغة (ATS-friendly):
- عناوين أقسام قياسية واضحة، وجمل إنجاز تبدأ بأفعال قوية.
- ادمج كلمات مفتاحية من إعلان الوظيفة، لكن **فقط** الكلمات التي لها أساس
  فعلي في خبرة المستخدم الموجودة بالسيرة الأصلية.
- حافظ على نفس لغة السيرة الأصلية.

قاعدة صارمة وغير قابلة للتفاوض (grounding): كل جملة أو ادّعاء تكتبه في
السيرة المحسّنة يجب أن يستند لسطر أو عبارة موجودة فعلياً وحرفياً في نص
السيرة الذاتية الأصلية أدناه. قبل ما تكتب أي جملة، تأكد أنك تقدر تشير
لمصدرها بالسيرة الأصلية — لو ما تقدر، لا تكتبها، حتى لو الوظيفة تطلبها.
يُسمح فقط بإعادة الصياغة أو إعادة الترتيب أو التأكيد على ما هو موجود
فعلاً — ممنوع اختلاق أي خبرة، مهارة، مسمى وظيفي، شركة، رقم، أو إنجاز غير
موجود أصلاً.

ممنوع أيضاً ترقية مستوى دور المستخدم في أي إنجاز: لا تحوّل "شارك في" إلى
"قاد"، ولا "كتب" إلى "أشرف على"، ولا تضف "mentoring" أو "leading" أو أي
دور قيادي/إشرافي غير مذكور حرفياً بالسيرة الأصلية — الفعل القوي يجب أن
يبقى بنفس مستوى الدور الأصلي بالضبط، حتى لو الوظيفة المستهدفة تطلب قيادة.

أرجع النتيجة بصيغة JSON فقط بالشكل التالي بالضبط:
{{
  "improved_resume": "<نص السيرة المحسّنة كاملاً بكل أقسامها، نظيفاً وجاهزاً للاستخدام مباشرة، بدون أي إشارات مصادر داخله>",
  "changes": [
    {{
      "section": "<اسم القسم الذي تغيّر>",
      "what_changed": "<وصف مختصر للتغيير>",
      "grounding": "[مبني على: \\"...العبارة الأصلية الحرفية من السيرة...\\"]"
    }}
  ]
}}

نص السيرة الذاتية الكامل (المصدر الوحيد المسموح الاستناد له):
---
{resume_text}
---

وصف الوظيفة المستهدفة:
---
{job_description}
---
"""

MANDATORY_REVIEW_WARNING = "⚠️ راجع هذا الاقتراح بعناية قبل استخدامه فعلياً"


def improve_resume(job_description: str, resume_text: str) -> dict:
    """يحسّن السيرة الذاتية تحسيناً شاملاً (Summary + Skills + أي قسم يحتاج
    مواءمة) بصياغة متوافقة مع ATS، دون اختلاق معلومات (grounding لكل تغيير
    بمصدره في السيرة الأصلية). اقتراح للعرض فقط — لا يكتب على أي ملف
    (rule 5 في CLAUDE.md)."""
    if not job_description or not job_description.strip():
        return {"error": "وصف الوظيفة فاضي — أعطني وصف الوظيفة المطلوب التحسين من أجلها أولاً."}

    if not resume_text or not resume_text.strip():
        return {"error": "لا توجد سيرة ذاتية متاحة لتحسينها."}

    prompt = IMPROVE_RESUME_PROMPT.format(resume_text=resume_text, job_description=job_description)

    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    result = json.loads(response.text)
    improved = (result.get("improved_resume") or "").strip()
    if not improved:
        return {"error": "لم يرجع النموذج نص سيرة محسّنة — جرّب الطلب مرة أخرى."}

    return {
        "improved_resume": improved,
        "changes": result.get("changes", []),
        "note": "هذا اقتراح للعرض فقط — لن يُكتب فوق السيرة الأصلية أبداً؛ التحميل يكون كملف جديد.",
        "warning": MANDATORY_REVIEW_WARNING,
    }
