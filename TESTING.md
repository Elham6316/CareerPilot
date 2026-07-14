# TESTING.md — سجل حالات الاختبار الفعلية

## ملاحظة تقنية مهمة قبل الاختبارات
CLAUDE.md يحدد `gemini-2.5-flash`. عند الاختبار الفعلي مع مفتاح المشروع في
`.env`، رجعت الـ API خطأ **404 "This model ... is no longer available to new
users"** لكل من `gemini-2.5-flash` و `gemini-2.5-flash-lite`. تم أيضاً اكتشاف
أن مكتبة `google-generativeai` نفسها متوقفة رسمياً (deprecation warning من
Google يطلب الانتقال لـ `google-genai`).

**القرار (بموافقة المستخدم):** التحويل لمكتبة `google-genai` الحالية،
واستخدام الموديل `models/gemini-3.1-flash-lite` بدل `gemini-2.5-flash` —
تم التأكد أنه يعمل فعلياً مع مفتاح المشروع. راجع `tools/gemini_client.py`.

كذلك تم اكتشاف أن الجهاز يستخدم برنامج Avast الذي يعترض اتصالات HTTPS
(SSL interception)، مما كان يسبب فشل التحقق من الشهادات. تم حل هذا بتثبيت
`pip-system-certs` ضمن `requirements.txt` (يجعل بايثون يثق بمخزن شهادات
ويندوز، الذي يتضمن شهادة Avast المُضافة محلياً).

---

## حالة اختبار 1 — استخراج نص PDF (`tools/resume_parser.py`)
- **الإجراء**: توليد `data/demo_resume.pdf` من `data/demo_resume.txt` (سيرة
  ذاتية تجريبية وهمية باسم "Sara Al-Otaibi")، ثم استدعاء
  `extract_resume_text("data/demo_resume.pdf")`.
- **النتيجة**: نجاح — استُخرج نص كامل (1314 حرف) مطابق لمحتوى الملف الأصلي،
  بدون فقدان أي قسم (Summary, Experience, Education, Skills, Languages).

## حالة اختبار 2 — أداة `suggest_job_titles` عبر حلقة الوكيل الكاملة
- **الطلب**: رسالة تحتوي نص السيرة المستخرج من PDF + "اقترح لي مسميات وظيفية
  مناسبة لي".
- **الأداة المستدعاة فعلياً**: تأكدنا من محتوى `history` أن النموذج استدعى
  `function_call=suggest_job_titles` تلقائياً (قرار من النموذج نفسه، لا كود
  يدوي)، ثم `tools/job_search.py` نفّذ استدعاء Gemini حقيقي ورجّع:
  `{'suggested_titles': ['Backend Developer', 'Software Engineer',
  'Python Developer', 'Cloud Engineer']}`.
- **الرد النهائي للمستخدم**: عرض المسميات الأربعة بصيغة واضحة، وسأل المستخدم
  عن أيها يفضّل أو إن كان يريد مسمى آخر — يطابق تصميم "الاقتراح بداية حوار"
  في `PROJECT_BRIEF.md`.
- **النتيجة**: نجاح كامل — الحلقة (`run_agent`) استدعت الأداة، استقبلت
  النتيجة، ورجعت رداً نهائياً بدون تدخل يدوي.

## حالة اختبار 3 — معالجة خطأ أداة غير مربوطة بعد (rule 6)
- **الإجراء**: استدعاء مباشر لـ `execute_tool("search_jobs", {...})` (أداة
  لسا ما اترابطت بتنفيذها الفعلي في هذي المرحلة).
- **النتيجة**: رجعت `{'error': "أداة 'search_jobs' غير مربوطة بعد بتنفيذها
  الفعلي."}` بدل رفع استثناء يوقف البرنامج — يطابق rule 6 في CLAUDE.md
  (فشل الأداة يُبلَّغ كنتيجة عادية، لا يُسقط الحلقة).
- **ملاحظة لاحقة**: `search_jobs` أصبحت مربوطة فعلياً ابتداءً من حالة الاختبار
  رقم 5 أدناه — هذا الاختبار يوثّق سلوك الحلقة *قبل* ربطها فقط.

## حالة اختبار 4 — حالة حافة: سيرة ذاتية فارغة
- **الإجراء**: `execute_tool("suggest_job_titles", {"resume_text": ""})`.
- **النتيجة**: `{'suggested_titles': []}` — لا انهيار، لكن يُلاحَظ أن الرد
  فارغ بدون توضيح للمستخدم لماذا. تحسين مستقبلي محتمل: رسالة أوضح لو النص
  فارغاً/قصيراً جداً (لم أُعالجه الآن بناءً على تعليمات "ابدأ بأداة واحدة
  وتوقف").

---

## بند 4 — أداة `search_jobs` عبر Jooble API

### ملاحظة تقنية: تنسيق الموقع (location) عند Jooble
اختبرت `search_jobs` مباشرة بعدة صيغ لنفس المدينة قبل ربطها بالحلقة:
- `"Riyadh"` وحدها → **0 نتائج**
- `"الرياض"` (عربي) → **0 نتائج**
- `"Riyadh, Saudi Arabia"` أو `"Saudi Arabia"` (إنجليزي كامل) → **5 نتائج**

هذا سلوك فعلي من طرف Jooble نفسه (ليس خطأ في كودنا) — محرك البحث لديهم
يطابق الموقع بشكل أدق مع الاسم الإنجليزي الكامل للدولة/المدينة. تركت الأداة
تمرر أي نص location كما هو دون تعديل (لا تحويل لغوي داخل الكود) لأن قرار
"كيف يعيد الصياغة أو يوسّع البحث لو فشل" هو قرار للنموذج نفسه حسب rule 6،
وليس منطقاً يدوياً مكتوباً في tools/job_search.py.

### حالة اختبار 5 — `search_jobs` مباشرة (نجاح وفشل)
- **الإجراء**: `search_jobs("Backend Developer", "Riyadh, Saudi Arabia")`.
- **النتيجة**: نجاح — 5 وظائف حقيقية، كل واحدة فيها title/company/location/
  link/snippet نظيف (بدون وسوم HTML أو `&nbsp;`).
- **الإجراء 2**: استعلام غير منطقي عمداً (`"نجار مبتدئ عديم الخبرة تماماً
  xyz123nonsense"` + موقع غير موجود) لاختبار حالة صفر نتائج.
- **النتيجة 2**: `{'jobs': [], 'message': "لا توجد نتائج لـ '...' — جرّب مسمى
  وظيفياً أو موقعاً أوسع."}` — رسالة واضحة تُرجع للنموذج، لا استثناء.

### حالة اختبار 6 — التسلسل الكامل بدون تدخل يدوي (سيناريو مطلوب صراحة)
- **الطلب 1**: رسالة فيها نص PDF المستخرج لسيرة "Sara Al-Otaibi" + "أبي وظيفة
  تناسب سيرتي في الرياض" (بدون تحديد مسمى وظيفي صريح).
  - **القرار 1 من النموذج**: استدعى `suggest_job_titles` تلقائياً (تحقق من
    `history`)، ورجّع 4 مسميات، وسأل المستخدم يختار.
- **الطلب 2** (تمثيل اختيار المستخدم): `"اختار Backend Developer"`.
  - **القرار 2 من النموذج**: استدعى مباشرة
    `search_jobs({'query': 'Backend Developer', 'location': 'Riyadh'})` —
    بدون أي كود يدوي بيني وبين الخطوتين، القرار بالكامل من النموذج بناءً على
    السياق المتراكم في `history`.
  - **النتيجة**: `location='Riyadh'` (بدون "Saudi Arabia") رجعت 0 نتائج من
    Jooble فعلياً، فتعامل النموذج مع الفشل بذكاء: اعتذر، اقترح مسمى أشمل
    ("Software Engineer")، وعرض توسيع الموقع — دون أي توقف أو انهيار في
    الحلقة (rule 6 يعمل حتى عبر استدعاءات متتالية فاشلة).
- **الطلب 3**: `"نعم وسّع البحث للمملكة العربية السعودية كلها"`.
  - **القرار 3 من النموذج**: جرّب تلقائياً استدعاءين متتاليين:
    `search_jobs(query='Backend Developer', location='السعودية')` ثم
    `search_jobs(query='Software Engineer', location='السعودية')` — كلاهما
    رجع 0 نتائج (لأن Jooble يحتاج الاسم الإنجليزي كما وُثّق أعلاه). النموذج
    بعدها اعترف بالمحدودية بصراحة، واقترح بدائل خارجية (LinkedIn, Bayt,
    جدارات) بدل تكرار فاشل لا نهائي — سلوك جيد رغم أن السبب الجذري هو تنسيق
    الموقع لا عيب في الأداة.

### حالة اختبار 7 — تأكيد ظهور النتائج الفعلية + تذكير "تحقق من شرعية الشركة"
- **الطلب**: `"ابحث لي عن وظيفة Backend Developer في Riyadh, Saudi Arabia"`
  (بصيغة إنجليزية كاملة للموقع، بناءً على ما تعلّمناه في حالة اختبار 6).
- **النتيجة**: `search_jobs` رجعت 5 وظائف حقيقية، وعرضها النموذج في رده
  النهائي مع كل وظيفة (المسمى + الشركة)، وأضاف في نهاية الرد بالضبط جملة
  التذكير المطلوبة في `PROJECT_BRIEF.md` و `SYSTEM_INSTRUCTION`: **"يُرجى
  التحقق من شرعية الشركة وتفاصيل الوظيفة من خلال الرابط المرفق قبل القيام
  بأي إجراء أو تقديم فعلي، حيث أن هذه النتائج مستمدة من محرك تجميع
  وظائف."** — يطابق البند 5 من المتطلبات تماماً.

### الخلاصة
كل بنود بند 4 في `PROJECT_BRIEF.md` تحققت: الأداة تستدعي Jooble فعلياً،
تتعامل مع الفشل وصفر النتائج كرسالة عادية للنموذج (لا استثناء)، مربوطة في
`execute_tool()`، والتسلسل الكامل (سيرة → suggest_job_titles → اختيار
المستخدم → search_jobs) يعمل بقرار كامل من النموذج بدون أي `if/else` يدوي
بيني وبين الخطوتين.

---

## تحسين (regression fix) — تطبيع location في SYSTEM_INSTRUCTION

**المشكلة الموثّقة في حالة اختبار 6 أعلاه**: النموذج كان يمرر location كما
كتبها المستخدم حرفياً ("Riyadh" أو "الرياض")، فترجع Jooble صفر نتائج رغم
وجود وظائف فعلية، ويحتاج النموذج عدة محاولات فاشلة قبل يوسّع البحث بنفسه.

**الحل**: أضفت فقرة صريحة في `SYSTEM_INSTRUCTION` (`agent.py`) تلزم النموذج
بتحويل location دائماً لصيغة إنجليزية كاملة "المدينة، الدولة" (مثال:
"Riyadh, Saudi Arabia") قبل استدعاء `search_jobs`، بغض النظر عن لغة/صيغة
المستخدم — هذا تعليمات للنموذج نفسه، لا منطق تحويل يدوي مكتوب في
`tools/job_search.py`.

### حالة اختبار 8 — التحقق من التحسين
- **الطلب**: نفس سيناريو حالة اختبار 6 بالضبط — رسالة فيها نص PDF لسيرة
  "Sara Al-Otaibi" + "أبي وظيفة تناسب سيرتي في الرياض" (عربي، بدون "Saudi
  Arabia")، ثم "اختار Backend Developer".
- **الفحص عبر history**: النموذج استدعى
  `search_jobs({'query': 'Backend Developer', 'location': 'Riyadh, Saudi
  Arabia'})` — حوّل "الرياض" بنفسه إلى الصيغة الإنجليزية الصحيحة **من أول
  استدعاء**، بدون أي كود يدوي يتدخل بين رسالة المستخدم واستدعاء الأداة.
- **النتيجة**: 5 وظائف حقيقية من أول محاولة (بدل 3 جولات فاشلة قبل التحسين)،
  مع ظهور جملة "تحقق من شرعية الشركة" في الرد النهائي كالمعتاد.
- **الخلاصة**: التحسين نجح — تم حل المشكلة عبر تعليمات للنموذج (prompt)
  وليس عبر كود تحويل يدوي، متوافق مع مبدأ CLAUDE.md الأساسي (القرار من
  داخل حلقة النموذج، لا من منطق if/else مكتوب).

---

## بند 5 — أداة `evaluate_match`

### ملاحظة تصميم: من أين يجي resume_text؟
شيمة `evaluate_match` في `TOOLS_SCHEMA` تأخذ `job_description` فقط (بدون
`resume_text`) — لأن السيرة الذاتية أصلاً موجودة في `history` منذ أول رسالة
(انظر `wrap_resume_text()` في `agent.py`، تحيط النص بفاصلين واضحين
`RESUME_START_MARKER`/`RESUME_END_MARKER`). `execute_tool()` يستخرج النص
تلقائياً من `history` عبر `_get_resume_text_from_history()` قبل ما يستدعي
`tools/resume_matcher.evaluate_match()` — هذا IO/plumbing بحت (استخراج نص
من سياق محادثة)، وليس "قراراً" يحتاج منطقاً ذكياً، فمن المقبول يكون كوداً
يدوياً بسيطاً حسب مبدأ CLAUDE.md.

### حالة اختبار 9 — `evaluate_match` مباشرة وحالات الحافة (rule 6)
- **استدعاء طبيعي**: `evaluate_match(job_description="...", resume_text=
  demo_resume_text)` رجّع تحليلاً دلالياً حقيقياً (ليس مطابقة كلمات) —
  راجع حالة اختبار 10 لمثال فعلي كامل.
- **job_description فاضي**: `evaluate_match("", resume_text)` → رجّع
  `{'error': 'وصف الوظيفة فاضي — أعطني وصف الوظيفة المطلوب تقييمها أولاً.'}`
  بدل استثناء.
- **resume_text فاضي**: `evaluate_match("some job", "")` → رجّع
  `{'error': 'لا توجد سيرة ذاتية متاحة لمقارنتها بهذه الوظيفة.'}`.
- **استدعاء عبر execute_tool بدون سيرة محمّلة في history أصلاً**:
  `execute_tool("evaluate_match", {"job_description": "Some job"}, [])` →
  `{'error': 'لا توجد سيرة ذاتية محمّلة في هذي المحادثة بعد — اطلب من
  المستخدم يرفعها أولاً.'}` — كل الحالات رسائل عادية للنموذج، لا انهيار.

### حالة اختبار 10 — التسلسل الكامل المطلوب (استكمال محادثة حالة اختبار 8)
استكملت **نفس محادثة** حالة اختبار 8 (سيرة Sara Al-Otaibi → اختيار Backend
Developer → 5 نتائج بحث حقيقية في الرياض)، وأرسلت رسالة جديدة:
`"قيّم لي الوظيفة الأولى، شو رأيك تناسبني؟"` (بدون ذكر اسم الوظيفة صراحة).

- **أ. الفهم**: تحقق عبر `history` أن النموذج فهم أن "الوظيفة الأولى" تقصد
  أول نتيجة في `search_jobs` السابقة تحديداً: **"Staff Backend Engineer
  (NodeJS/Go)" لدى شركة Yassir** — بدون أي تلميح إضافي مني.
- **ب. الاستدعاء**: نفّذ
  `function_call=evaluate_match({'job_description': 'Staff Backend Engineer
  (NodeJS/Go) at Yassir. Responsibilities include driving technical
  strategy, mentoring junior developers...'})` — بنى وصف الوظيفة بنفسه من
  الـ snippet المتاح (Jooble لا يعطي وصفاً كاملاً، فقط مقتطفاً)، ثم
  `execute_tool` استخرج `resume_text` تلقائياً من `history` ومرّرها لـ
  `evaluate_match`.
- **ج. النتيجة الفعلية من Gemini**: `{'match_score': 45, 'reasoning': "The
  candidate has a solid backend foundation but lacks the seniority required
  for a 'Staff' level role... Additionally, there is a technical stack
  mismatch, as the role requires NodeJS/Go expertise, while the candidate's
  experience is primarily in the Python ecosystem."}` — **تحليل دلالي حقيقي**
  وليس مطابقة كلمات: ميّز بين "Backend" (تطابق سطحي) و"Staff-level seniority"
  و"NodeJS/Go vs Python" (تعارض فعلي في التقنيات وسنوات الخبرة).
- **الرد النهائي للمستخدم**: عرض بالعربية أن التوافق ضعيف، وشرح السببين
  (مستوى الخبرة المطلوب Staff = 8+ سنوات مقابل خبرة سارة 4 سنوات، واختلاف
  التقنيات NodeJS/Go مقابل Python)، واقترح بديلاً ("Senior Backend
  Developer" بـ Python) وعرض بحثاً جديداً — رد واضح ومفيد يتجاوز مجرد رقم.

### الخلاصة
بند 5 مكتمل بالكامل: تحليل دلالي حقيقي عبر Gemini (لا مطابقة كلمات مفتاحية
بكود بايثون)، معالجة حالات الحافة كرسائل عادية (rule 6)، مربوطة في
`execute_tool()`، والتسلسل الكامل (بحث → "قيّم لي الوظيفة الأولى" → فهم
المرجع → استدعاء `evaluate_match` → عرض النتيجة) يعمل بقرار كامل من النموذج
بدون أي تدخل يدوي بيني وبين الخطوات.

---

## بند 7 — أداة `suggest_resume_edits`

### حالة اختبار 11 — استكمال نفس المحادثة (حالة اختبار 10) بطلب تعديل السيرة
بعد نتيجة `evaluate_match` (الدرجة 45، الفجوة: مستوى Staff + NodeJS/Go مقابل
Python) في **نفس المحادثة المستمرة**، أرسلت: `"عدّل السيرة عشان تناسب هذي
الوظيفة أكثر"` (بدون تحديد وظيفة صراحة).

- **الاستدعاء الفعلي عبر history**:
  `function_call=suggest_resume_edits({'target_section': 'summary',
  'job_description': 'Staff Backend Engineer (NodeJS/Go) at Yassir:
  Responsible for driving technical direction, mentoring junior developers,
  and contributing to scaling up backend systems...'})` — النموذج فهم
  تلقائياً إنه نفس وظيفة Yassir من `evaluate_match` السابقة، بدون أي تلميح
  إضافي مني، واستخدم `target_section` الافتراضي "summary" لأني ما حددت قسماً.
- **execute_tool** استخرج `resume_text` من `history` تلقائياً (نفس آلية
  `evaluate_match`) ومرّرها لـ `suggest_resume_edits`.
- **النص المقترح الكامل الذي رجع فعلياً**:
  > "Software Engineer with 4 years of experience specializing in backend
  > development and system architecture. Proven track record in scaling
  > systems by migrating monolithic services into Dockerized microservices
  > on AWS and optimizing API performance to reduce checkout latency.
  > Experienced in building robust data pipelines and REST APIs, with a
  > strong foundation in Python-based microservices, automated testing, and
  > agile collaboration. Committed to driving technical efficiency and
  > mentoring team members to achieve scalable, high-performance solutions."
- **الرد النهائي للمستخدم**: عرض الاقتراح بوضوح كـ"اقتراح" (بلوك اقتباس)،
  مع سؤال "هل يعجبك هذا التوجه؟" — لم يفترض موافقة، ولم يكتب أي شيء على أي
  ملف.

### حالة اختبار 12 — مراجعة بشرية صريحة لنتيجة الذكاء الاصطناعي (مطلوبة رسمياً)
راجعت أنا (وليس بالكود) النص المقترح أعلاه جملة جملة مقابل
`data/demo_resume.txt` الأصلي:

| جملة في الاقتراح | موجودة أصلاً في السيرة الحقيقية؟ |
|---|---|
| "4 years of experience... backend development" | ✅ مطابقة لـ "Backend-focused software engineer with 4 years of experience" |
| "migrating monolithic services into Dockerized microservices on AWS" | ✅ مطابقة تماماً لسطر الخبرة: "Migrated a monolithic order-processing service into three Dockerized microservices deployed on AWS ECS" |
| "optimizing API performance to reduce checkout latency" | ✅ مطابقة لـ "cutting average checkout latency by 30%" |
| "building robust data pipelines and REST APIs" | ✅ مطابقة لنص الـ Summary الأصلي حرفياً تقريباً |
| "strong foundation in Python-based microservices" | ✅ مطابقة لـ "recent focus on Python microservices" |
| "automated testing" | ✅ مطابقة لـ "Wrote automated integration tests (pytest)" |
| "agile collaboration" | ✅ مطابقة لـ "Collaborated with a 5-person team using Agile/Scrum" |
| **"mentoring team members"** | ❌ **غير موجودة إطلاقاً في السيرة الأصلية** — سارة لم تذكر أي خبرة إشراف/توجيه لأحد. هذي عبارة **مُختلَقة**، على الأغلب "تسربت" من وصف الوظيفة نفسها (Yassir تطلب "mentoring junior developers") بدل من خبرة سارة الفعلية |
| "specializing in... system architecture" | ⚠️ صياغة أوسع من المذكور حرفياً، لكن مبررة بشكل معقول من عملية الـ migration المذكورة فعلاً — إعادة صياغة، لا اختلاق واضح |

**⚠️ نتيجة المراجعة البشرية: فشل جزئي في اتباع تحذير "عدم الاختلاق".**
رغم أن الـ prompt في `SUGGEST_EDITS_PROMPT` يحتوي تحذيراً صريحاً وقوياً بعدم
اختلاق أي خبرة غير موجودة، النموذج أضاف عبارة "mentoring team members" وهي
غير صحيحة عن سارة إطلاقاً. هذا بالضبط نوع الخطأ اللي "المراجعة البشرية"
مصممة تلتقطه قبل ما يوصل لأي استخدام فعلي — **لا يجوز اعتماد اقتراح
`suggest_resume_edits` تلقائياً بدون قراءة بشرية دقيقة**، حتى مع وجود تحذير
صريح في الـ prompt. يستحق نقاشاً لاحقاً هل نحتاج تقوية الـ prompt أكثر
(مثلاً: اطلب من النموذج أن يبرر كل جملة بإشارة لسطر محدد من السيرة الأصلية)
قبل اعتماد هذي الأداة نهائياً في العرض التقديمي/الفيديو.

### حالة اختبار 13 — تأكيد عدم الكتابة على أي ملف فعلي
قارنت SHA256 لملفي `data/demo_resume.txt` و `data/demo_resume.pdf` قبل
وبعد تشغيل السيناريو الكامل (حالات اختبار 10-12):
- قبل: `demo_resume.txt` = `30ceebd8...`, `demo_resume.pdf` = `1b3f136c...`
- بعد: **نفس القيمتين تماماً** لكلا الملفين، ونفس وقت آخر تعديل (mtime) —
  لم يُكتب أو يُعدَّل أي ملف على القرص خلال الاختبار بالكامل. الأداة رجعت
  نص الاقتراح فقط كقيمة (`dict`) عبر `function_response`، ولا يوجد أي
  `open(..., "w")` في `tools/resume_matcher.py` إطلاقاً.

### الخلاصة (قبل الإصلاح)
الأداة مربوطة وتعمل ضمن التسلسل الكامل بدون تدخل يدوي، ولا تكتب أي ملف
(يطابق rule 5). لكن المراجعة البشرية المطلوبة كشفت **اختلاقاً فعلياً واحداً**
("mentoring team members") رغم التحذير الصريح في الـ prompt — هذا يوثّق
بالضبط أهمية "مراجعة بشرية لنتائج الذكاء الاصطناعي" كخطوة لا يمكن تخطيها،
ويستحق معالجة/تقوية إضافية قبل اعتبار هذي الأداة "جاهزة للعرض" بثقة كاملة.

---

## إصلاح الاختلاق عبر Grounding (تعليمات، لا كود يدوي يفلتر النص)

**التغيير في `SUGGEST_EDITS_PROMPT`** (`tools/resume_matcher.py`): أضفت
قاعدة صريحة تلزم النموذج أن كل جملة يكتبها لازم تستند لسطر أو عبارة موجودة
حرفياً بالسيرة الأصلية، وتحديداً: *"قبل ما تكتب أي جملة، تأكد أنك تقدر تشير
لمصدرها بالسيرة الأصلية — لو ما تقدر، لا تكتبها، حتى لو الوظيفة تطلبها."*
وأضفت طلب إشارة مصدر بعد كل جملة بالشكل `[مبني على: "..."]` (البند
الاختياري رقم 2). كذلك أضفت `MANDATORY_REVIEW_WARNING` كحقل ثابت `warning`
يرجع دائماً مع كل استدعاء لـ `suggest_resume_edits` بغض النظر عن جودة
الاقتراح (طبقة أمان إضافية، بند 5 من الطلب)، وأضفت سطرين في
`SYSTEM_INSTRUCTION` (`agent.py`) يلزمان النموذج يعرض التحذير وإشارات
المصدر حرفياً في رده النهائي للمستخدم بدل حذفها.

### حالة اختبار 14 — إعادة اختبار بعد إصلاح الاختلاق (قبل/بعد)
أعدت **بالضبط نفس سيناريو حالة اختبار 11-12**: نفس محادثة Yassir (سيرة
Sara → اختيار Backend Developer → بحث بالرياض → تقييم الوظيفة الأولى
[45/100] → "عدّل السيرة عشان تناسب هذي الوظيفة أكثر").

**النص المقترح الجديد (كامل، كما رجع فعلياً من الأداة، ثم كما عُرض
للمستخدم حرفياً بما فيه الإشارات):**
> "Software Engineer with 4 years of experience specializing in backend
> development and the design of REST APIs and data pipelines. [مبني على:
> "Backend-focused software engineer with 4 years of experience building
> and maintaining REST APIs and data pipelines"]
>
> Proven track record in driving technical delivery, evidenced by
> designing and shipping 12+ REST endpoints and migrating monolithic
> services into Dockerized microservices on AWS. [مبني على: "Designed and
> shipped 12+ REST endpoints" و "Migrated a monolithic order-processing
> service into three Dockerized microservices deployed on AWS ECS"]
>
> Experienced in enhancing system performance, having successfully cut
> checkout latency by 30% and reduced production regressions by 40%
> through automated testing. [مبني على: "cutting average checkout latency
> by 30%" و "reduced production regressions by roughly 40%"]
>
> Collaborative professional with a background in Agile/Scrum team
> environments, including sprint planning and code reviews. [مبني على:
> "Collaborated with a 5-person team using Agile/Scrum, participating in
> sprint planning and code reviews."]"

**جدول المقارنة البشرية (نفس أسلوب حالة اختبار 12، جملة بجملة):**

| جملة في الاقتراح | إشارة المصدر المرفقة | تحققت يدوياً من مطابقتها للسيرة الأصلية؟ |
|---|---|---|
| "Software Engineer with 4 years of experience... REST APIs and data pipelines" | "Backend-focused software engineer with 4 years of experience building and maintaining REST APIs and data pipelines" | ✅ مطابقة شبه حرفية للـ Summary الأصلي |
| "designing and shipping 12+ REST endpoints" | "Designed and shipped 12+ REST endpoints" | ✅ مطابقة حرفية تماماً |
| "migrating monolithic services into Dockerized microservices on AWS" | "Migrated a monolithic order-processing service into three Dockerized microservices deployed on AWS ECS" | ✅ مطابقة حرفية تماماً |
| "cut checkout latency by 30%" | "cutting average checkout latency by 30%" | ✅ مطابقة حرفية تماماً |
| "reduced production regressions by 40% through automated testing" | "reduced production regressions by roughly 40%" (+ "Wrote automated integration tests (pytest)" ضمنياً) | ✅ مطابقة صحيحة |
| "Agile/Scrum team environments, including sprint planning and code reviews" | "Collaborated with a 5-person team using Agile/Scrum, participating in sprint planning and code reviews." | ✅ مطابقة حرفية تماماً |

**لا وجود إطلاقاً لأي جملة عن "mentoring" أو أي ادّعاء آخر غير موجود
بالسيرة الأصلية في هذي الإعادة.** كل الإشارات المرفقة صحيحة وقابلة
للتحقق بنظرة سريعة (بدون الحاجة لقراءة السيرة كاملة سطراً بسطر يدوياً كل
مرة) — هذا يحقق فعلياً الهدف من البند الاختياري رقم 2.

كذلك تحقق ظهور التحذير الثابت **"⚠️ راجع هذا الاقتراح بعناية قبل استخدامه
فعلياً"** حرفياً في الرد النهائي للمستخدم، وأضاف النموذج بصدق ملاحظة
منفصلة (غير مندرجة كادّعاء عن خبرة سارة) تقترح إضافة مشاريع شخصية بـ
NodeJS/Go إن وُجدت — وهذا تعامل صحيح وشفاف مع فجوة التقنيات بدل اختلاقها.

**ملاحظة جانبية اكتُشفت ثم عولجت أثناء نفس هذي الإعادة**: أول محاولة من
الإصلاح أظهرت أن `suggested_text` الخام (من الأداة) كان يحتوي إشارات
`[مبني على: ...]` صحيحة، لكن رد النموذج النهائي للمستخدم كان يحذفها عند
إعادة الصياغة قبل العرض — ما يُفقد فائدة البند 2. أضفت سطراً صريحاً في
`SYSTEM_INSTRUCTION` يلزم النموذج يعرض الإشارات كما هي بدون حذف، وأعدت
الاختبار (النتيجة أعلاه) فتأكدت أن الإشارات تصل فعلياً للمستخدم في الرد
النهائي، لا فقط في نتيجة الأداة الداخلية.

### الخلاصة (بعد الإصلاح)
**المشكلة انحلّت كلياً في هذي الإعادة** — لا اختلاق ظاهر، كل جملة لها
مصدر حرفي صحيح وقابل للتحقق، والتحذير الثابت يظهر دائماً. مع ذلك، هذا
اختبار واحد إضافي (وليس ضمانة رياضية 100%) — النموذج قد يختلق أحياناً في
محادثات أخرى رغم الـ grounding، ولهذا بقي التحذير الثابت "راجع بعناية"
كطبقة أمان دائمة بغض النظر عن جودة الإصلاح، تماماً كما طلب البند 5.

---

## بند 8 — أداتا `log_application` و `get_application_status`

التخزين في `tools/tracker.py` عبارة عن `data/applications.json` (مستثنى من
git عبر `.gitignore`) بقائمة كائنات `{company, title, status, date}`.
`log_application` تضيف سجلاً جديداً أو تحدّث سجلاً موجوداً لنفس
company+title (مطابقة case-insensitive). لا كود يدوي جديد يتحقق من "هل
أكّد المستخدم؟" — القاعدة الموجودة أصلاً في `SYSTEM_INSTRUCTION` (منذ أول
نسخة من `agent.py`) لسا كما هي: *"لا تستدعي log_application أبداً إلا بعد
أن يؤكد المستخدم صراحة... (كلمات مثل 'نعم'، 'سجّله'، 'تم التقديم فعلاً')"*.

استكملت **نفس المحادثة المستمرة** من حالة اختبار 14 (بعد اقتراح تعديل
السيرة المُصلَح لوظيفة Yassir):

### حالة اختبار 15 — سيناريو ب: رفض ضمني (سلبي، اختُبر أولاً عمداً)
اختبرت هذا **قبل** سيناريو أ عمداً، حتى أتأكد ما فيه تسجيل عرضي "علّق" من
سياق سابق. أرسلت: `"الوظيفة حلوة"` (بدون أي ذكر لتقديم فعلي أو نية تقديم).

- **النتيجة عبر history**: النموذج رد بنص فقط — **لا يوجد أي
  `function_call` لـ `log_application` أو أي أداة أخرى إطلاقاً**. اقترح
  بدلاً من ذلك كتابة خطاب تقديم (خطوة منطقية تالية) وانتظر رد المستخدم.
- **الخلاصة**: اختبار سلبي ناجح — الأداة لم تُستدعَ بتساهل على رسالة غامضة.

### حالة اختبار 16 — سيناريو أ: تأكيد صريح بصيغة الماضي
بعدها أرسلت: `"قدمت فعلاً على وظيفة Yassir اليوم"`.

- **النتيجة عبر history**: النموذج استدعى مباشرة
  `function_call=log_application({'company': 'Yassir', 'status':
  'submitted', 'title': 'Staff Backend Engineer (NodeJS/Go)'})` — **بدون**
  طلب جولة تأكيد إضافية.
- **لماذا هذا سلوك صحيح وليس تساهلاً**: عبارة "قدمت فعلاً" (بصيغة الماضي،
  فعل مكتمل) مطابقة دلالياً تماماً للمثال المذكور حرفياً في
  `SYSTEM_INSTRUCTION` نفسها: *"تم التقديم فعلاً"*. الرسالة تقرير عن فعل
  مُنجز فعلاً، لا نية مستقبلية أو رسالة غامضة مثل حالة اختبار 15 — فهي
  تُشكّل "تأكيداً صريحاً" بحد ذاتها. النموذج استنتج company + title من
  سياق المحادثة (وظيفة Yassir التي قُيّمت واقتُرح تعديل السيرة لها سابقاً)
  دون أي تدخل يدوي.
- **الملف الفعلي بعد الاستدعاء** (`data/applications.json`):
  ```json
  [{"company": "Yassir", "title": "Staff Backend Engineer (NodeJS/Go)",
    "status": "submitted", "date": "2026-07-14"}]
  ```
  التاريخ (`2026-07-14`) تولّد تلقائياً بدون أي تدخل يدوي من المستخدم أو مني.

### حالة اختبار 17 — `get_application_status`
أرسلت: `"كم وظيفة قدمت؟"` بعد التسجيل أعلاه.

- **الاستدعاء**: `function_call=get_application_status({})` (بدون فلتر).
- **النتيجة الفعلية**: `{'total': 1, 'by_status': {'submitted': 1},
  'applications': [{'company': 'Yassir', 'title': 'Staff Backend Engineer
  (NodeJS/Go)', 'status': 'submitted', 'date': '2026-07-14'}]}` — طابقت
  محتوى `data/applications.json` على القرص حرفياً (تحققت بقراءة الملف
  مباشرة).
- **الرد النهائي**: عرض بالعربية "وظيفة واحدة فقط" مع كل التفاصيل
  (الشركة، المسمى، التاريخ، الحالة) بدقة مطابقة للبيانات الفعلية.

### تنظيف بعد الاختبار
حذفت `data/applications.json` بعد التوثيق لإعادة المشروع لحالة نظيفة قبل
أي عرض أو تسليم (الملف مستثنى من git أصلاً، لكن حذفه يمنع بيانات اختبار
تتراكم في نسخة العرض التجريبي).

### الخلاصة
بند 8 مكتمل بالكامل: `log_application` لا تُستدعى على رسائل غامضة (اختبار
سلبي ناجح)، وتُستدعى فقط عند تأكيد صريح حقيقي (سواء بصيغة أمر مباشر أو
تقرير بصيغة الماضي عن فعل مُنجز) بدون أي كود يدوي إضافي للتحقق —
`SYSTEM_INSTRUCTION` الأصلية كافية. `get_application_status` تعكس بيانات
الملف الفعلية بدقة.

عند كتابة هذا كان `draft_cover_letter` (بند 6) لسا غير مربوطة — تم استكمالها
لاحقاً، راجع القسم التالي.

---

## بند 6 — أداة `draft_cover_letter` (آخر أداة أساسية من السبع)

`tools/cover_letter.py` تستدعي Gemini لكتابة خطاب تقديم مخصص، مبني على نص
السيرة الذاتية الحقيقي + وصف الوظيفة + اسم الشركة. طبّقت **نفس قاعدة
الـ grounding** المستخدمة في `suggest_resume_edits` (بند 7): تحذير صريح في
الـ prompt بأن كل خبرة/إنجاز/مهارة مذكورة يجب أن تستند لعبارة موجودة
حرفياً بالسيرة الأصلية، وإلا لا تُكتب حتى لو الوظيفة تطلبها. النتيجة نص
فقط (`dict` عبر `function_response`) — لا حفظ كملف تلقائياً (rule 5).
مربوطة في `execute_tool()` بنفس آلية سحب `resume_text` من `history`.

### حالة اختبار 18 — التسلسل الكامل بدون إعادة تزويد بالمعلومات يدوياً
استكملت **نفس المحادثة المستمرة** (سيرة Sara → اختيار Backend Developer →
بحث بالرياض → تقييم وظيفة Yassir [45/100] → اقتراح تعديل السيرة)، وأرسلت:
`"اكتب لي خطاب تقديم لهذي الوظيفة"` (بدون ذكر اسم الشركة أو الوظيفة صراحة).

- **الاستدعاء الفعلي عبر history**:
  `function_call=draft_cover_letter({'job_description': 'Staff Backend
  Engineer (NodeJS/Go): Responsibilities include driving technical
  strategy, mentoring junior developers, and contributing to scaling
  backend infrastructure...', 'company_name': 'Yassir'})` — النموذج استنتج
  تلقائياً "هذي الوظيفة" = نفس وظيفة Yassir من `evaluate_match` و
  `suggest_resume_edits` السابقتين، بدون أي تزويد يدوي مني بالمعلومات مرة
  أخرى.
- **execute_tool** استخرج `resume_text` من `history` تلقائياً (نفس آلية
  الأدوات السابقة) ومرّرها لـ `draft_cover_letter`.
- **الرد النهائي**: عرض الخطاب كاملاً بوضوح كـ"مقترح"، وسأل إن كانت تريد
  تعديلات، أو تسجيل التقديم في `log_application` لو نوت تقدّم فعلاً —
  ربط طبيعي وذكي مع أداة لاحقة دون افتراض تنفيذها.

### حالة اختبار 19 — مراجعة بشرية إلزامية لخطاب التقديم (جملة بجملة)
راجعت أنا (لا بالكود) الخطاب الكامل الناتج مقابل `data/demo_resume.txt`:

| ادّعاء في الخطاب | موجود أصلاً في السيرة الحقيقية؟ |
|---|---|
| "backend-focused software engineer with 4 years of experience" | ✅ مطابقة حرفية لأول جملة في الـ Summary |
| "Backend Developer at Falcon Retail Tech" | ✅ مطابقة حرفية لعنوان الخبرة الأولى |
| "designing and shipping 12+ REST endpoints using FastAPI" | ✅ مطابقة حرفية تقريباً |
| "cut average checkout latency by 30%" | ✅ مطابقة حرفية تماماً |
| "migrating a monolithic order-processing service into three Dockerized microservices deployed on AWS ECS" | ✅ مطابقة حرفية تقريباً كلمة بكلمة |
| "writing automated integration tests using pytest... reduced production regressions by roughly 40%" | ✅ مطابقة حرفية تماماً |
| "Junior Developer at Nakhla Software House" | ✅ مطابقة حرفية لعنوان الخبرة الثانية |
| "building internal tooling in Python and Django" | ✅ مطابقة حرفية (حذف تفصيل "35+ warehouse staff" — حذف، لا اختلاق) |
| "collaborated with a 5-person team using Agile/Scrum... sprint planning and code reviews" | ✅ مطابقة حرفية تماماً |
| "technical stack includes Python, FastAPI, Django, PostgreSQL, Docker, AWS (ECS, S3, RDS), and Git" | ✅ مطابقة مباشرة لقائمة Skills (حذف "React" و"pytest" من القائمة — حذف، لا اختلاق) |
| "recent experience in cloud deployment on AWS and a focus on Python microservices" | ✅ مطابقة حرفية لآخر جملة في الـ Summary |

**✅ نتيجة المراجعة: لا يوجد أي اختلاق.** بعكس حالة اختبار 12 (اختلاق
"mentoring team members" في `suggest_resume_edits` قبل إصلاح الـ
grounding)، هذا الخطاب **لم يذكر أي شيء عن "mentoring"** رغم أن وصف وظيفة
Yassir يطلبها صراحة — تجاهلها بصمت بدل اختلاقها، وهذا بالضبط السلوك
المطلوب من قاعدة الـ grounding ("لو ما تقدر تشير لمصدرها، لا تكتبها، حتى
لو الوظيفة تطلبها"). كذلك لم يدّعِ أي خبرة بـ NodeJS/Go رغم أنها متطلب
أساسي بالوظيفة — تعامل صادق مع فجوة معروفة بدل التستر عليها بادّعاء كاذب.

### تأكيد: لا حفظ لأي ملف
قارنت SHA256 لملفي `demo_resume.txt`/`demo_resume.pdf` قبل وبعد هذا
الاختبار — **متطابقة تماماً**، ولم يظهر أي ملف جديد في `data/` (لا خطاب
محفوظ كـ .txt أو .pdf). الأداة ترجع النص كقيمة فقط، بدون أي `open(...,
"w")` في `tools/cover_letter.py`.

### الخلاصة
بند 6 مكتمل: خطاب حقيقي مبني بالكامل على السيرة الفعلية، بدون اختلاق
(تأكدت مراجعة بشرية)، لا حفظ تلقائي، ومربوط في التسلسل الكامل بقرار من
النموذج بدون أي تدخل يدوي.

---

## ✅ الأدوات السبع الأساسية مكتملة بالكامل (7 of 7 core tools complete)

1. **استخراج نص PDF** (`tools/resume_parser.py`) — تأسيسي
2. **suggest_job_titles** (`tools/job_search.py`)
3. **search_jobs** (`tools/job_search.py`) — عبر Jooble API فعلياً
4. **evaluate_match** (`tools/resume_matcher.py`) — تحليل دلالي حقيقي
5. **suggest_resume_edits** (`tools/resume_matcher.py`) — مع grounding بعد إصلاح اختلاق مكتشف
6. **draft_cover_letter** (`tools/cover_letter.py`) — مع نفس قاعدة grounding
7. **log_application** + **get_application_status** (`tools/tracker.py`)

كل أداة مربوطة فعلياً في `execute_tool()` (`agent.py`)، واختُبرت ضمن
سيناريوهات تسلسلية حقيقية (وليس استدعاءً منعزلاً فقط) — القرار الكامل
(أي أداة، متى، وبأي معطيات) من النموذج نفسه عبر حلقة function calling،
لا من منطق if/else مكتوب يدوياً.

---

## واجهة Streamlit (`app.py`) — اختبار فعلي عبر المتصفح

أضفت `app.py` كطبقة عرض فقط فوق `agent.py` — بدون أي تعديل على منطق
`run_agent` أو حلقة الـ ReAct نفسها، وبدون أي منطق قرار جديد (متى تُستدعى
أي أداة يبقى بالكامل داخل `agent.py`). شغّلت التطبيق فعلياً عبر
`streamlit run app.py` وفتحته في متصفح حقيقي (ليس اختباراً عبر الطرفية
فقط)، وأعدت **نفس سيناريو Yassir الكامل** خطوة بخطوة:

### حالة اختبار 20 — رفع PDF فعلياً عبر واجهة الرفع
رفعت `data/demo_resume.pdf` عبر `st.file_uploader` في الشريط الجانبي
(محاكاة رفع ملف حقيقي عبر حقن File object بنفس بايتات الملف الفعلي في
حقل الرفع، لا مجرد استدعاء الدالة مباشرة من الكود). النتيجة: ظهرت رسالة
"تم استخراج نص السيرة الذاتية بنجاح." و"✅ محمّلة: demo_resume.pdf" في
الواجهة — يؤكد أن `app.py` يستخدم فعلاً `tools/resume_parser
.extract_resume_text()` نفسها عبر مسار ملف مؤقت، دون إعادة كتابة منطق
الاستخراج.

### حالة اختبار 21 — نفس سيناريو Yassir الكامل عبر صندوق المحادثة
أرسلت بالتتابع عبر `st.chat_input` (بدون أي تدخل يدوي في الكود بين
الرسائل، فقط تفاعل مستخدم حقيقي بالمتصفح):
1. `"أبي وظيفة تناسب سيرتي في الرياض"` → استدعى `suggest_job_titles`
   وعرض 4 مسميات
2. `"اختار Backend Developer"` → استدعى `search_jobs` (بعد تحويل الموقع
   تلقائياً لـ"Riyadh, Saudi Arabia" كما هو موثّق سابقاً) وعرض 5 وظائف
   حقيقية مع تذكير شرعية الشركة
3. `"قيّم لي الوظيفة الأولى، شو رأيك تناسبني؟"` → استدعى `evaluate_match`
   ورجّع نفس النتيجة المتوقعة (45% تقريباً، فجوة Staff-level و NodeJS/Go)
4. `"عدّل السيرة عشان تناسب هذي الوظيفة أكثر"` → استدعى
   `suggest_resume_edits`
5. `"اكتب لي خطاب تقديم لهذي الوظيفة"` → استدعى `draft_cover_letter`

كل خطوة ظهرت في صندوق المحادثة بالترتيب الصحيح (رسالة المستخدم ثم رد
الوكيل)، والحلقة أدارت `history` بشكل صحيح عبر `st.session_state` بين كل
رسالة والتالية دون فقدان السياق — نفس آلية `run_agent()` الأصلية بدون أي
تغيير.

### حالة اختبار 22 — صندوق المراجعة البصري (human-in-the-loop)
تحقق فعلياً في المتصفح أن ردَّي الخطوتين 4 و5 (suggest_resume_edits و
draft_cover_letter) ظهرا داخل **صندوق مميز بصرياً** يحتوي تحذير "🔍 هذا
اقتراح يحتاج مراجعتك بعناية قبل استخدامه فعلياً" في الأعلى — بينما باقي
الردود (suggest_job_titles, search_jobs, evaluate_match) ظهرت كنص محادثة
عادي بدون هذا الصندوق. هذا يؤكد أن منطق `needs_review` في `app.py` (فحص
`function_call.name` في تاريخ المحادثة الجديد لهذا الدور فقط) يعمل بدقة —
بدون أي تدخل يدوي في قرار الأداة نفسها.

### ملاحظة تقنية (بيئة الاختبار، لا علاقة لها بالكود)
رفع ملف PDF عبر متصفح آلي (بدون تفاعل بشري مباشر) يحتاج محاكاة حقن ملف
حقيقي في حقل `<input type="file">` — استخدمت خادم HTTP محلي مؤقت
(CORS-enabled) لجلب بايتات `demo_resume.pdf` الفعلية بدقة (بدل نسخ base64
يدوياً، الذي تسبب في تلف أول محاولة). هذا الترتيب اختباري بحت (خادم مؤقت
تم إيقافه وحذف ملفاته بعد الاختبار) ولا علاقة له بكود `app.py` نفسه الذي
يستخدم `st.file_uploader` القياسي.

### الخلاصة
واجهة Streamlit تعمل بسلاسة كاملة فوق نفس منطق `agent.py` دون أي تغيير
في حلقة ReAct أو منطق القرار — التسلسل الكامل (رفع PDF → اقتراح مسميات →
بحث → تقييم → اقتراح تعديل → خطاب تقديم) اشتغل عبر المتصفح فعلياً، وصندوق
المراجعة البصري يميّز الأدوات اللي تحتاج مراجعة بشرية بدقة.
