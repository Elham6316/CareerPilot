"""كتابة خطاب تقديم مخصص بناءً على السيرة الذاتية الحقيقية عبر Gemini."""

from tools.gemini_client import MODEL_NAME, get_client

DRAFT_COVER_LETTER_PROMPT = """أنت خبير في كتابة خطابات التقديم (Cover
Letters). اكتب خطاب تقديم احترافي ومخصص للوظيفة والشركة أدناه، بناءً على
نص السيرة الذاتية الحقيقي فقط.

قاعدة صارمة وغير قابلة للتفاوض (grounding): كل خبرة أو إنجاز أو مهارة
تذكرها في الخطاب يجب أن تستند لسطر أو عبارة موجودة فعلياً وحرفياً في نص
السيرة الذاتية أدناه. قبل ما تكتب أي جملة، تأكد أنك تقدر تشير لمصدرها في
السيرة الأصلية — لو ما تقدر، لا تكتبها، حتى لو الوظيفة تطلبها. ممنوع
اختلاق أي خبرة، مهارة، مسمى وظيفي، شركة، رقم، أو إنجاز غير موجود أصلاً في
السيرة.

اكتب الخطاب بنفس لغة السيرة الذاتية (عربي أو إنجليزي)، وخاطب شركة
"{company_name}" تحديداً. أرجع نص الخطاب فقط، بدون أي شرح أو مقدمة أو JSON.

نص السيرة الذاتية الكامل (المصدر الوحيد المسموح الاستناد له):
---
{resume_text}
---

اسم الشركة: {company_name}

وصف الوظيفة المستهدفة:
---
{job_description}
---
"""


def draft_cover_letter(job_description: str, company_name: str, resume_text: str) -> dict:
    """يكتب خطاب تقديم مخصص لوظيفة معينة بناءً على السيرة الذاتية الحقيقية،
    مع الالتزام الصارم بعدم اختلاق أي خبرة (grounding). نص مقترح فقط — لا
    يُحفظ كملف تلقائياً."""
    if not job_description or not job_description.strip():
        return {"error": "وصف الوظيفة فاضي — أعطني وصف الوظيفة المطلوب كتابة خطاب لها أولاً."}

    if not company_name or not company_name.strip():
        return {"error": "اسم الشركة فاضي — أعطني اسم الشركة المطلوب توجيه الخطاب لها."}

    if not resume_text or not resume_text.strip():
        return {"error": "لا توجد سيرة ذاتية متاحة لكتابة خطاب بناءً عليها."}

    prompt = DRAFT_COVER_LETTER_PROMPT.format(
        resume_text=resume_text, job_description=job_description, company_name=company_name
    )

    response = get_client().models.generate_content(model=MODEL_NAME, contents=prompt)

    return {
        "company_name": company_name,
        "cover_letter": response.text.strip(),
        "note": "هذا خطاب مقترح للعرض فقط — لن يُحفظ كملف إلا بموافقتك الصريحة.",
    }
