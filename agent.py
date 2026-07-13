"""
CareerPilot — حلقة الوكيل الأساسية (ReAct: Reason + Act)
------------------------------------------------------------
الحلقة (while) تُبقي الحوار مع Gemini مفتوحاً عبر عدة استدعاءات أدوات
متتالية، والنموذج نفسه يقرر متى ينتهي — لا كود يدوي يقرر.
"""

from google.genai import types

from tools.gemini_client import MODEL_NAME, get_client
from tools.resume_parser import extract_resume_text

# نص السيرة الذاتية يُرسل مرة واحدة ضمن أول رسالة مستخدم (بين هذين الفاصلين)،
# وأي أداة تحتاجه لاحقاً (evaluate_match مثلاً) تستخرجه من history بدل أن
# يُعيد النموذج كتابته كوسيط في كل استدعاء.
RESUME_START_MARKER = "[بداية نص السيرة الذاتية المستخرجة من PDF]"
RESUME_END_MARKER = "[نهاية نص السيرة الذاتية]"


def wrap_resume_text(resume_text: str) -> str:
    return f"{RESUME_START_MARKER}\n{resume_text}\n{RESUME_END_MARKER}\n\n"


def _get_resume_text_from_history(history: list) -> str | None:
    for content in history:
        if content.role != "user":
            continue
        for part in content.parts:
            if part.text and RESUME_START_MARKER in part.text and RESUME_END_MARKER in part.text:
                start = part.text.index(RESUME_START_MARKER) + len(RESUME_START_MARKER)
                end = part.text.index(RESUME_END_MARKER)
                return part.text[start:end].strip()
    return None


# ------------------------------------------------------------------
# 1. تعريف الأدوات كـ schemas يفهمها Gemini
#    (التنفيذ الفعلي لكل دالة يُستورد من tools/ عبر execute_tool)
# ------------------------------------------------------------------

TOOLS_SCHEMA = [
    {
        "name": "suggest_job_titles",
        "description": (
            "يحلل نص السيرة الذاتية (بعد استخراجها من PDF) ويقترح 3-5 مسميات "
            "وظيفية مناسبة للمستخدم بناءً على خبراته ومهاراته. المستخدم بعدها "
            "يختار أحد المقترحات أو يكتب مسمى مختلف بنفسه."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string", "description": "نص السيرة الذاتية المستخرج من PDF"},
            },
            "required": ["resume_text"],
        },
    },
    {
        "name": "search_jobs",
        "description": "يبحث عن وظائف حقيقية عبر Jooble API بناءً على مسمى وظيفي وموقع",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "المسمى الوظيفي أو الكلمات المفتاحية"},
                "location": {"type": "string", "description": "المدينة أو الدولة"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "evaluate_match",
        "description": "يقيّم مدى توافق وصف وظيفة معينة مع السيرة الذاتية للمستخدم، ويعطي درجة وسبباً",
        "parameters": {
            "type": "object",
            "properties": {
                "job_description": {"type": "string"},
            },
            "required": ["job_description"],
        },
    },
    {
        "name": "suggest_resume_edits",
        "description": (
            "يقترح تعديلاً لقسم الـ Summary (ويمكن أقسام أخرى ذات صلة كالمهارات) "
            "في السيرة الذاتية ليتناسب بشكل أفضل مع وظيفة معينة. يُرجع نص التعديل "
            "المقترح فقط للعرض على المستخدم — لا يكتب فوق أي ملف مباشرة."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "job_description": {"type": "string"},
                "target_section": {
                    "type": "string",
                    "description": "القسم المطلوب تعديله، مثال: 'summary' أو 'skills'. افتراضي: summary",
                },
            },
            "required": ["job_description"],
        },
    },
    {
        "name": "draft_cover_letter",
        "description": "يكتب خطاب تقديم مخصص لوظيفة معينة بناءً على السيرة الذاتية",
        "parameters": {
            "type": "object",
            "properties": {
                "job_description": {"type": "string"},
                "company_name": {"type": "string"},
            },
            "required": ["job_description"],
        },
    },
    {
        "name": "log_application",
        "description": "يسجل تقديماً على وظيفة في السجل المحلي. لا يُستدعى إلا بعد تأكيد صريح من المستخدم.",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "string", "enum": ["submitted", "interview", "rejected", "offer"]},
            },
            "required": ["company", "title", "status"],
        },
    },
    {
        "name": "get_application_status",
        "description": "يرجع ملخصاً أو تفاصيل عن التقديمات المسجّلة سابقاً، مع إمكانية الفلترة",
        "parameters": {
            "type": "object",
            "properties": {
                "filter_status": {"type": "string", "description": "اختياري: فلترة حسب الحالة"},
            },
        },
    },
]

SYSTEM_INSTRUCTION = """أنت CareerPilot، وكيل ذكاء اصطناعي يساعد المستخدم في
رحلة البحث عن وظيفة: البحث، التقييم، كتابة خطابات التقديم، والمتابعة.

قواعد صارمة:
- افهم نية المستخدم من نص حر (عربي أو إنجليزي)، ولا تنتظر أوامر بصيغة ثابتة.
- لو رفع المستخدم سيرة ذاتية جديدة ولم يحدد مسمى وظيفي، استخدم
  suggest_job_titles أولاً واعرض المقترحات، ثم انتظر اختياره أو مسماه الخاص
  قبل الانتقال لـ search_jobs.
- استخدم الأدوات المتاحة لك حسب الحاجة، وقد تحتاج أكثر من أداة بالتسلسل
  لطلب واحد (مثال: اقترح مسميات ثم ابحث ثم قيّم ثم اكتب خطاب).
- عند عرض نتائج search_jobs، ذكّر المستخدم بجملة قصيرة إنه يتحقق من شرعية
  الشركة قبل التقديم الفعلي (Jooble محرك تجميع من مصادر متعددة).
- عند استدعاء search_jobs، حوّل قيمة location دائماً لصيغة إنجليزية كاملة
  "المدينة، الدولة" (مثال: "Riyadh, Saudi Arabia") بغض النظر عن اللغة أو
  الصيغة اللي كتبها المستخدم — لأن Jooble API لا يرجع نتائج صحيحة بدون
  هذي الصيغة تحديداً (سلوك موثّق فعلياً، راجع TESTING.md).
- لا تستدعي log_application أبداً إلا بعد أن يؤكد المستخدم صراحة أنه يريد
  تسجيل هذا التقديم (كلمات مثل "نعم"، "سجّله"، "تم التقديم فعلاً").
- suggest_resume_edits يُرجع اقتراحاً نصياً فقط للعرض — لا تعتبره تعديلاً
  نهائياً تلقائياً، واعرضه للمستخدم بوضوح كـ "اقتراح" ينتظر رأيه.
- إن فشلت أداة، أخبر المستخدم بوضوح واقترح بديلاً بدل التوقف الكامل.
- كن مختصراً ومباشراً في ردودك النهائية.
"""

_config = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    tools=[types.Tool(function_declarations=TOOLS_SCHEMA)],
)


def execute_tool(name: str, args: dict, history: list) -> dict:
    """يوجّه كل اسم أداة لتنفيذها الفعلي من tools/. أي استثناء يُلتقط هنا
    ويُرجع كرسالة خطأ عادية (rule 6 في CLAUDE.md) بدل تعطيل حلقة الوكيل."""
    try:
        if name == "suggest_job_titles":
            from tools.job_search import suggest_job_titles

            return suggest_job_titles(**args)

        if name == "search_jobs":
            from tools.job_search import search_jobs

            return search_jobs(**args)

        if name == "evaluate_match":
            from tools.resume_matcher import evaluate_match

            resume_text = _get_resume_text_from_history(history)
            if not resume_text:
                return {"error": "لا توجد سيرة ذاتية محمّلة في هذي المحادثة بعد — اطلب من المستخدم يرفعها أولاً."}
            return evaluate_match(resume_text=resume_text, **args)

        if name == "suggest_resume_edits":
            from tools.resume_matcher import suggest_resume_edits

            resume_text = _get_resume_text_from_history(history)
            if not resume_text:
                return {"error": "لا توجد سيرة ذاتية محمّلة في هذي المحادثة بعد — اطلب من المستخدم يرفعها أولاً."}
            return suggest_resume_edits(resume_text=resume_text, **args)

        # باقي الأدوات لسا ما اترابطت بتنفيذها الفعلي (مراحل قادمة)
        return {"error": f"أداة '{name}' غير مربوطة بعد بتنفيذها الفعلي."}

    except Exception as exc:  # noqa: BLE001 — نبلّغ أي خطأ للنموذج بدل إسقاط الحلقة
        return {"error": f"فشلت أداة '{name}': {exc}"}


def run_agent(user_message: str, conversation_history: list = None) -> tuple[str, list]:
    """حلقة الوكيل الأساسية (ReAct). تستقبل رسالة المستخدم وتاريخ المحادثة
    (لدعم حوار متعدد الأدوار)، وترجع الرد النهائي + التاريخ المحدَّث."""
    client = get_client()

    history = conversation_history or []
    history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    max_turns = 8  # حماية من حلقة لا نهائية
    for _ in range(max_turns):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=history,
            config=_config,
        )
        candidate = response.candidates[0]

        function_calls = [
            part.function_call for part in candidate.content.parts
            if part.function_call
        ]

        if not function_calls:
            # النموذج قرر إنه انتهى — عنده رد نهائي للمستخدم
            final_text = response.text
            history.append(candidate.content)
            return final_text, history

        # النموذج طلب أداة (أو أكثر) — ننفذها ونرجّع النتيجة له
        history.append(candidate.content)

        response_parts = []
        for call in function_calls:
            result = execute_tool(call.name, dict(call.args), history)
            response_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": result})
            )

        history.append(types.Content(role="user", parts=response_parts))

    return "عذراً، الطلب معقّد أكثر من اللازم — جرّب صياغة أبسط.", history


if __name__ == "__main__":
    print("CareerPilot — اكتب طلبك (اكتب 'خروج' للإنهاء)\n")

    conv_history = []
    resume_path = input("مسار PDF للسيرة الذاتية (اختياري، اضغط Enter للتخطي): ").strip()
    pending_prefix = ""
    if resume_path:
        try:
            resume_text = extract_resume_text(resume_path)
            pending_prefix = wrap_resume_text(resume_text)
            print("تم استخراج نص السيرة الذاتية بنجاح.\n")
        except Exception as exc:
            print(f"تعذّر استخراج نص PDF: {exc}\n")

    while True:
        user_input = input("أنت: ").strip()
        if user_input in ("خروج", "exit", "quit"):
            break
        message = pending_prefix + user_input if pending_prefix else user_input
        pending_prefix = ""
        reply, conv_history = run_agent(message, conv_history)
        print(f"\nCareerPilot: {reply}\n")
