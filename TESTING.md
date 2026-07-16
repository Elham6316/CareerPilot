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

---

## تطوير suggest_resume_edits إلى improve_resume + الهوية البصرية + عدّاد الطلبات

### التغييرات
1. **`improve_resume`** (بدل `suggest_resume_edits` في `tools/resume_matcher.py`):
   تحسين شامل للسيرة (Summary + Skills + أي قسم يحتاج مواءمة) بصياغة
   متوافقة مع ATS — كلمات مفتاحية من إعلان الوظيفة لكن فقط الموجودة فعلاً
   بخبرة المستخدم. قاعدة الـ grounding بقيت بحذافيرها. الأداة ترجع JSON:
   `improved_resume` (نص كامل نظيف جاهز للتحميل) + `changes` (قائمة
   تغييرات، كل واحد مع إشارة `[مبني على: "..."]`) + حقل `warning` الثابت.
2. **واجهة Streamlit**: معاينة السيرة المحسّنة في `st.expander` + زر
   `st.download_button` لتحميلها كملف `improved_resume.txt` **جديد** —
   الواجهة تلتقط النص من `function_response` في history فقط، لا كتابة على
   القرص إطلاقاً.
3. **الهوية البصرية**: الألوان الأساسية عبر `.streamlit/config.toml`
   (theming رسمي: primary ‎#D3A0FD، خلفية ‎#FAFAFA، نص ‎#111111، حدود
   ‎#ECECEC، شريط جانبي ‎#F7F0FD، خط Cairo من Google Fonts، زوايا 16px)،
   و CSS مخصص في `app.py` فقط لما لا يغطيه config.toml: إخفاء قائمة
   Streamlit والفوتر وزر Deploy، ظلال ناعمة وزوايا 24px لبطاقات المحادثة،
   ولون الـ accent ‎#ECFF70 لزر التحميل. **لا تغيير في منطق `agent.py`**
   (فقط إعادة تسمية الأداة في الـ schema/التعليمات كما طُلب في البند 1).
4. **عدّاد طلبات**: `request_count` في `session_state`، حد أقصى 5 طلبات
   لكل جلسة، مع رسالة لطيفة وتعطيل حقل الإدخال عند البلوغ.

### حالة اختبار 23 — اكتشاف وإصلاح "تضخيم الدور" قبل اعتماد الأداة
أول اختبار مباشر لـ `improve_resume` (قبل الواجهة) كشف مشكلة grounding
من نفس عائلة الاختلاق المكتشف سابقاً (حالة 12): النص المحسّن احتوى
"mentoring team members" (غير موجودة بالسيرة — تسربت من إعلان الوظيفة)
و"Led the migration" (الأصل "Migrated" — ترقية دور). السبب: تعليمة
"المواءمة مع الوظيفة" تدفع النموذج لرفع مستوى الدور.

**الإصلاح** (prompt، لا كود فلترة): أضفت للـ prompt حظراً صريحاً على ترقية
مستوى الدور — لا تحويل "شارك في" إلى "قاد"، ولا إضافة mentoring/leading
غير مذكورة حرفياً، حتى لو الوظيفة المستهدفة تطلب قيادة.

**إعادة الاختبار**: راجعت الناتج الجديد يدوياً سطراً بسطر — لا mentoring،
لا Led، "participating" صارت "contributing" (نفس المستوى)، كل تصنيفات
Skills من القائمة الأصلية فقط، ولا ذكر لـ NodeJS/Go إطلاقاً. نظيف.

### حالة اختبار 24 — سيناريو Yassir الكامل عبر الواجهة الجديدة (شكلاً ووظيفة)
شغّلت التطبيق فعلياً وفتحته في المتصفح، وتحققت أولاً من الهوية البصرية
بقياس القيم المحسوبة (computed styles) مباشرة من الصفحة:
- خلفية التطبيق: `rgb(250, 250, 250)` = ‎#FAFAFA بالضبط ✅
- الخط: `Cairo, "Source Sans", sans-serif` على النصوص والعناوين ✅
- لون النص: `rgb(17, 17, 17)` = ‎#111111 ✅
- الشريط الجانبي: `rgb(247, 240, 253)` = ‎#F7F0FD ✅
- قائمة Streamlit وزر Deploy وشريط الأدوات: `display: none` ✅
- زر التحميل: خلفية `rgb(236, 255, 112)` = ‎#ECFF70 (الـ accent) بالضبط ✅

ثم أعدت سيناريو Yassir الكامل عبر صندوق المحادثة (رفع PDF حقيقي عبر حقل
الرفع + 5 رسائل):
1. "أبي وظيفة تناسب سيرتي في الرياض" → `suggest_job_titles` (عدّاد 1/5)
2. "اختار Backend Developer" → `search_jobs` مع نتائج حقيقية + تنبيه
   الشرعية (عدّاد 2/5)
3. "قيّم لي الوظيفة الأولى" → `evaluate_match` (35%، نفس أسباب الفجوة:
   Staff-level و NodeJS/Go مقابل Python) (عدّاد 3/5)
4. "حسّن سيرتي عشان تناسب هذي الوظيفة أكثر" → `improve_resume` (عدّاد 4/5):
   - صندوق المراجعة "🔍 يحتاج مراجعتك" ظهر ✅
   - قائمة التغييرات بإشارات [مبني على: ...] + التحذير الثابت في الرد ✅
   - النموذج صرّح نصاً: "لم يتم إدراج NodeJS أو Go لأنها غير موجودة في
     خبراتك السابقة، ولا يُنصح بإضافتها" — سلوك grounding مثالي ظاهر
     للمستخدم ✅
   - معاينة السيرة المحسّنة كاملة في expander ✅ (راجعتها يدوياً: كل
     الأقسام مستندة للأصل؛ الملاحظة الوحيدة أن "basic React" صارت
     "React" — تعميم لمهارة موجودة فعلاً، وليس اختلاق مهارة، ويلتقطه
     المستخدم في مراجعته)
   - زر التحميل "⬇️ تحميل السيرة المحسّنة (ملف جديد)" ظهر بلون الـ accent ✅
5. "اكتب لي خطاب تقديم لهذي الوظيفة" → `draft_cover_letter` بصندوق
   مراجعة خاص به (عدّاد 5/5) ✅

### حالة اختبار 25 — حد الطلبات (5/5)
بعد الرسالة الخامسة مباشرة: ظهرت رسالة "🌙 وصلتَ للحد الأقصى من الطلبات
لهذي الجلسة (5 طلبات)..." وحقل الإدخال أصبح `disabled: true` فعلياً
(تحققت من خاصية العنصر مباشرة) — لا يمكن إرسال طلب سادس. الحماية مزدوجة:
تعطيل الحقل بصرياً + حارس `not limit_reached` في الكود لو وصل إدخال بأي
طريقة أخرى.

### تأكيد سلامة الملفات
SHA256 لـ `demo_resume.txt` و `demo_resume.pdf` قبل وبعد كامل الاختبار:
متطابقة تماماً، ولا ظهر أي ملف جديد في `data/` — التحميل يتم من الذاكرة
(session_state) للمتصفح مباشرة، بدون أي كتابة على القرص.

---

## إعادة تصميم `app.py` — من محادثة إلى منصة خدمات (service platform)

### القرار المعماري الأساسي (تحقّق منه صراحة)
كل زر خدمة في التصميم الجديد **لا يستدعي أي أداة مباشرة** — يبني نص طلب
بالعربية فقط ويمرره لنفس `send_to_agent()` → `run_agent()` المستخدمة من
قبل. الدالة `job_service_card()` وكل الأزرار الستة (مسميات، بحث، تقييم،
تحسين، خطاب، تقديماتي) تمر جميعها عبر هذا المسار الوحيد. **لم يتغيّر
حرف واحد في `agent.py`** خلال هذي المرحلة — تحققت عبر `git diff` أن
الملف غير موجود إطلاقاً في التعديلات.

### ملاحظة على أداة الاختبار المستخدمة
أدوات المتصفح (Claude Browser المستخدمة في الجلسات السابقة) لم تكن متاحة
في هذي الجلسة (انقطاع اتصال MCP). بدل التخطي أو الاختبار السطحي، استخدمت
**إطار الاختبار الرسمي لـ Streamlit نفسه**:
`streamlit.testing.v1.AppTest` — يشغّل `app.py` فعلياً (نفس كود الإنتاج
بالضبط، استدعاءات Gemini/Jooble حقيقية غير مموّهة)، ويسمح بمحاكاة نقر
الأزرار وتعبئة الحقول وفحص شجرة العناصر الناتجة برمجياً. هذا أقوى من
لقطة شاشة لأنه يتحقق من **الحالة الفعلية** لكل عنصر (مثل `disabled`)
مباشرة من كائن الواجهة، لا من نص مرئي فقط.

### حالة اختبار 26 — الحالة الأولية: كل الخدمات معطّلة قبل رفع السيرة
شغّلت `AppTest.from_file("app.py").run()` بدون أي `session_state` مسبق.
- **النتيجة**: `at.exception` فارغة (لا أخطاء عند التحميل الأول). فحصت
  حالة `disabled` لكل الأزرار الستة مباشرة من كائنات الواجهة: **الستة
  كلها `disabled=True`** — يطابق تماماً متطلب "قبل رفع الـ PDF: كل بطاقات
  الخدمات تظهر معطّلة".

### حالة اختبار 27 — تفعّل الخدمات بعد محاكاة رفع PDF ناجح
حقنت `processed_pdf_name` و `pending_prefix` (نفس القيمة اللي ينتجها
مسار الرفع الحقيقي عبر `extract_resume_text` + `wrap_resume_text` —
اختُبر مساره الفعلي عبر متصفح حقيقي في جلسات سابقة موثّقة، فركّزت هنا
على منطق الأزرار الجديد تحديداً).
- **النتيجة**: أزرار "اقتراح مسميات"، "بحث"، "تقديماتي" أصبحت
  `disabled=False` فوراً. أزرار "تقييم التوافق"، "تحسين السيرة"، "خطاب
  تقديم" **بقيت `disabled=True`** لأنه لا توجد نتائج بحث بعد — يطابق شرط
  "ابحثي عن وظائف أولاً" قبل تفعيل بطاقات الوظيفة المحددة.

### حالة اختبار 28 — السيناريو الكامل عبر الأزرار (لا محادثة نصية حرة)
نفّذت بالتتابع عبر نقر الأزرار فقط (بدون أي نص حر مكتوب يدوياً):

| # | الزر | الطلب النصي الفعلي المُرسَل لـ run_agent | الأداة اللي استدعاها النموذج فعلياً |
|---|---|---|---|
| 1 | اقترح لي مسميات | `"حلل سيرتي واقترح مسميات وظيفية تناسبني"` | `suggest_job_titles` |
| 2 | ابحث الآن (بعد تعبئة "Backend Developer" + "الرياض") | `"ابحث لي عن وظائف Backend Developer في الرياض"` | `search_jobs({'location': 'Riyadh, Saudi Arabia', ...})` |
| 3 | قيّم التوافق | `"قيّم توافق سيرتي مع وظيفة Staff Backend Engineer (NodeJS/Go) في شركة Yassir"` | `evaluate_match` → 45/100 |
| 4 | حسّن سيرتي | `"حسّن سيرتي الذاتية لتتوافق مع وظيفة Staff Backend Engineer (NodeJS/Go) في شركة Yassir"` | `improve_resume` |
| 5 | اكتب الخطاب | `"اكتب لي خطاب تقديم لوظيفة Staff Backend Engineer (NodeJS/Go) في شركة Yassir"` | `draft_cover_letter` |

**نقاط تحقق حاسمة**:
- **الزر رقم 2** يثبت أن قاعدة "حوّل الموقع لصيغة إنجليزية" الموجودة أصلاً
  في `SYSTEM_INSTRUCTION` (ولم تُلمَس في هذي المرحلة) لا تزال تعمل رغم
  تغيّر مصدر الطلب بالكامل من محادثة حرة إلى زر: النموذج حوّل "الرياض" إلى
  `"Riyadh, Saudi Arabia"` بنفسه في `search_jobs`، بدون أي كود يدوي جديد.
- **الأزرار 3، 4، 5** تثبت أن الوكيل يفهم مرجع "هذي الوظيفة" (`Staff
  Backend Engineer عند Yassir`) من `history` التراكمي، رغم أن كل طلب
  جاء من زر منفصل في بطاقة منفصلة، لا من محادثة متصلة — يؤكد أن القائمة
  المنسدلة (`extract_latest_jobs`) والذاكرة السياقية للنموذج يعملان معاً
  بشكل صحيح.
- **الزر رقم 4** (`improve_resume`): `needs_review=True` تلقائياً (يطابق
  `REVIEW_TOOLS`)، `improved_resume` التُقط بنجاح من نتيجة الأداة، وزر
  `download_button` بمفتاح `download_improved` ظهر فعلياً على الصفحة.
  النص المحسّن كامل خالٍ من أي اختلاق عند مراجعة بشرية سريعة (لا "mentoring"،
  لا ادّعاء NodeJS/Go — نفس سلوك الـ grounding الموثّق سابقاً).
- **الزر رقم 5** (`draft_cover_letter`): `needs_review=True` أيضاً، والخطاب
  الناتج معتمد بالكامل على السيرة الحقيقية (تحقق سريع: كل الأرقام
  والمسميات والشركات مطابقة للسيرة الأصلية، ولا ذكر لـ NodeJS/Go كخبرة
  فعلية — فقط ملاحظة صادقة بالفجوة).

### حالة اختبار 29 — حد الطلبات (5/جلسة) عبر الأزرار
بعد الطلب الخامس (`request_count == 5`)، ضغطت زر "اعرض تقديماتي" (طلب
سادس).
- **النتيجة**: `request_count` بقي `5` (لم يتغيّر — `send_to_agent()`
  رجعت فوراً من الحارس `if request_count >= MAX: return` **قبل** أي
  استدعاء لـ `run_agent`، فلم يُستهلك أي طلب Gemini إضافي). ظهرت رسالة
  الحد الأقصى، **وكل الأزرار الستة أصبحت `disabled=True`** تلقائياً
  (الحارس `disabled = (not resume_ready) or limit_reached` يشمل كل
  البطاقات معاً).

### تأكيد سلامة الملفات (بعد التصميم الجديد)
قارنت SHA256 لـ `demo_resume.txt` و `demo_resume.pdf` قبل وبعد كامل
اختبار الأزرار الستة — **متطابقة تماماً**، ولا ظهر أي ملف جديد في
`data/`. `improved_resume` معروض من `session_state` مباشرة عبر
`st.download_button`، بدون أي `open(..., "w")` في `app.py` أو
`tools/resume_matcher.py`.

### الخلاصة
منصة الخدمات الجديدة تعمل بالكامل فوق نفس `agent.py` دون أي تعديل فيه —
تحقق ذلك عبر `git diff` (لا سطر واحد تغيّر في `agent.py`) وعبر تتبّع
مسار كل زر حتى `run_agent()` بلا استثناء. كل قرار (أي أداة، متى، وبأي
معطيات — بما فيها تطبيع الموقع الإنجليزي وفهم مرجع "هذي الوظيفة" عبر
عدة بطاقات منفصلة) بقي بالكامل عند Gemini، كما يقتضي المبدأ الأهم في
`CLAUDE.md`.

---

## إصلاح شامل لتخطيط `app.py` (Grid حقيقي + Hero + تعريب الرفع)

المستخدم قدّم لقطة شاشة فعلية أظهرت مشاكل حقيقية: البطاقات الست متكدّسة
عمودياً بعمود ضيق ~50%، الـ hero مسطّح، ونص رفع الملف يظهر بالإنجليزية.
هذي المرة **التزمت بأخذ لقطة شاشة فعلية والتحقق منها بندًا بندًا** كما
طلب المستخدم صراحة، بدل الاكتفاء بمراجعة الكود.

### عائق تقني: أداة لقطة الشاشة فشلت طوال هذي الجلسة
حاولت `computer{action:"screenshot"}` و`zoom` عدة مرات (تبويبات مختلفة،
بعد انتظار كافٍ) — فشلت جميعها بـ timeout بعد 30 ثانية، وهي مشكلة على
مستوى البنية التحتية لهذي الجلسة (كل أدوات المتصفح الأخرى — `javascript_tool`،
`get_page_text`، `read_page`، `computer{action:"wait"}` — تعمل بشكل طبيعي).
**بدل التنازل عن التحقق البصري أو الاكتفاء بمراجعة الكود**، استخدمت
`javascript_tool` لقياس **الهندسة الفعلية المرسومة** (bounding rects،
computed styles) لكل عنصر حرج مباشرة من DOM الحي — وهو أدق من لقطة شاشة
لإثبات ادعاءات مثل "نفس الارتفاع بالضبط" أو "شبكة حقيقية"، لأنه يعطي أرقام
بكسل دقيقة بدل الاعتماد على تقدير بصري لمكان الحواف والاصطفاف.

### حالة اختبار 30 — اكتشاف السبب الجذري لتعطّل CSS بالكامل (خطأ حرج)
أول فحص هندسي بعد إعادة الكتابة أظهر أن **كل** الـ CSS المخصص (المتغيرات،
عرض 1200px، إخفاء Deploy، تعريب الرفع) غير مطبّق إطلاقاً — `--primary`
فارغة، `max-width` = "none"، زر Deploy ظاهر. لم يكن هذا خطأ تخطيط بسيط،
بل تعطّل كامل لعنصر `<style>` نفسه.

**التشخيص بالتقسيم الثنائي (bisection)**: عزلت الـ CSS الفعلي في سكربت
Streamlit منفصل، وقصصته للنصف تكراراً حتى حدّدت نقطة العطل بدقة بين
الحرف 3433 و3891 — بالضبط عند تعليق عربي كتبته يشرح سبب استخدام CSS
override، وفيه بالخطأ ذكرت أسماء وسوم HTML حرفياً بين قوسين زاويين:
`عناصر <span>/<p> الداخلية`. تأكيد قاطع: أعدت اختبار مقتطف صغير معزول
يحتوي فقط `/* comment with <span>/<p> tags inside */` فوق قاعدة CSS بسيطة
(`--test-var: 42px`) — فشل تماماً؛ وبدون تلك الوسوم نجح. **السبب**:
`st.html()` يُمرّر المحتوى عبر DOMPurify (منقّي HTML) *قبل* أن يصل لمحرك
CSS في المتصفح — أي نص يشبه وسم HTML (`<span>`, `<p>`) **حتى داخل تعليق
CSS** يُفسَّر كوسم حقيقي من طرف DOMPurify، فيُفسِد بنية عنصر `<style>`
بالكامل ويُسقطه بصمت (بدون أي رسالة خطأ ظاهرة في السجلات).

**الإصلاح**: أعدت صياغة التعليق لتجنّب أي رمز `<`/`>` حرفي (كتبت "عناصر
span و p" بدل "<span>/<p>")، وفحصت بقية الـ CSS بحثاً عن أي نمط مشابه
(`grep '<[a-zA-Z]'`) فلم أجد شيئاً آخر. أعدت تشغيل التطبيق — `--primary`
أصبحت `#D3A0FD`، `max-width` أصبحت `1200px`، Deploy مخفي، ونص الرفع
العربي (`::before` content) ظهر بشكل صحيح — تأكدت الثلاثة عبر
`getComputedStyle` مباشرة.

**عِبرة تستحق التوثيق**: أي تعليق داخل `<style>` يمرّ عبر `st.html()`
يجب ألا يحتوي رموز `<`/`>` حرفية عند وصف عناصر HTML — استخدام أسماء بدون
أقواس (span بدل `<span>`) هو الحل الآمن دائماً.

### حالة اختبار 31 — شبكة 3×2 حقيقية (قياس هندسي مباشر، لا افتراض)
بعد الإصلاح أعلاه، قسته `st.columns(3)` مرتين مباشرة (`row1_col1/2/3`
و`row2_col1/2/3`، لا `st.container(horizontal=True)` القديمة):
- **8 عناصر `[data-testid="stColumn"]`** بالضبط (2 لتقسيم الـ hero + 3 + 3
  للشبكة) — مطابق للمتوقع تماماً.
- الصف الأول: ثلاث بطاقات بنفس إحداثي y (820) وثلاثة إحداثيات x مختلفة
  (829، 477، 125) — **جنباً إلى جنب فعلياً، لا متكدّسة عمودياً**.
- الصف الثاني: نفس النمط بـ y=1136 مختلف عن الصف الأول — تأكيد أنها صفان
  حقيقيان لا صف واحد ممتد.

### حالة اختبار 32 — اكتشاف وإصلاح تصادم مفاتيح CSS (بطاقات بارتفاع 720px بدل 260px)
القياس الأول للارتفاعات كشف بطاقات `تقييم التوافق`/`تحسين السيرة`/`خطاب
تقديم` بارتفاع **720-722px** بدل 260px المطلوب، بينما `اقتراح مسميات`/
`تقديماتي` كانتا 260px بالضبط. **السبب**: محدد CSS `[class*="st-key-service_"]`
يطابق أي *جزء* من اسم الـ class — ومفاتيح القائمة المنسدلة والزر داخل
`job_service_card()` كانت مبنية كـ `f"{key}_select"`/`f"{key}_btn"` حيث
`key="service_match"` مثلاً، فينتج `st-key-service_match_select` —
والذي **يحتوي** السلسلة `"st-key-service_"` كسلسلة فرعية، فيُطبَّق عليه
نفس نمط البطاقة (padding + حدود + `min-height`) **مرة إضافية متداخلة**
داخل البطاقة الأصلية، فيتضاعف الارتفاع الكلي.

**الإصلاح**: غيّرت مفاتيح العناصر الداخلية في `job_service_card()` لتستخدم
بادئة مختلفة تماماً (`"job-"` بدل `"service_"`) عبر
`widget_ns = key.replace("service_", "job-")`، فأصبحت المفاتيح
`job-match_select`/`job-match_btn` ولا تتقاطع مع محدد CSS الخاص بالبطاقات
إطلاقاً. أعدت القياس: **الآن 6 بطاقات فقط تطابق المحدد** (بدل 12 قبل
الإصلاح)، بارتفاع صحيح.

### حالة اختبار 33 — إصلاح "الارتفاع الموحّد فعلياً" (300px بدل 260px + !important)
حتى بعد إصلاح تصادم المفاتيح، بطاقة "البحث عن وظائف" (حقلا إدخال + زر)
قاست 335px رغم `height: 260px` — لأن محتواها الطبيعي أطول من 260px،
و`height` بدون `!important` خسر أمام تخصيص Streamlit الداخلي لنفس العنصر
(`.stVerticalBlock`). رفعت الارتفاع لـ 300px (يتّسع لأطول بطاقة فعلياً)،
وأضفت `!important` على `min-height`/`height`/`max-height` معاً مع
`overflow: hidden` كضمان صارم. **القياس النهائي**: كل البطاقات الست
= **300px بالضبط** (`Set` من القيم = `{300}` فقط)، `isAllIdentical: true`.

### حالة اختبار 34 — اكتشاف وإصلاح إسقاط أيقونات SVG بالكامل
فحص محتوى كل بطاقة كشف أن عنصر `<svg>` **مفقود تماماً** من كل الأيقونات
الست (`hasSvgInTitle: false` للجميع). اختبار معزول أكّد: `st.html()` مع
`<svg>...</svg>` خام يُسقط الوسم بالكامل عبر DOMPurify (نفس آلية الحماية
اللي أسقطت CSS في حالة اختبار 30، لكن هذي المرة الوسم نفسه غير مسموح، لا
محتواه فقط). **الإصلاح**: غيّرت دالة `icon()` لترمّز الـ SVG كـ
base64 data URI وتُضمّنه عبر وسم `<img src="data:image/svg+xml;base64,...">`
بدل `<svg>` الخام — وسم `<img>` مسموح دائماً من DOMPurify. أعدت الفحص:
كل البطاقات الست الآن تحتوي `<img>` بمصدر `data:image/svg+xml;base64,...`
صحيح.

### حالة اختبار 35 — التحقق النهائي البصري (قياسات هندسية شاملة)
بعد كل الإصلاحات أعلاه:
- **عرض المحتوى**: `max-width: 1200px`، العرض الفعلي المقاس = 1200px
  بالضبط — لا عمود ضيق، ولا امتداد كامل.
- **الـ Hero**: خلفية `rgb(247, 240, 253)` = `#F7F0FD` بالضبط، مقسوم فعلياً
  لعمودين بنفس y (129) وعرضين مختلفين (568 و376) — نص+شعار من جهة،
  أشكال زخرفية من الجهة الأخرى.
- **بطاقة الرفع**: حدود `2px dashed rgb(211, 160, 253)` = `#D3A0FD` بالضبط
  متقطعة كما هو مطلوب.
- **بطاقة "تحسين السيرة"**: حدود `2px solid rgb(236, 255, 112)` = `#ECFF70`
  (أثخن من حدود البطاقات العادية 1px)، وزرها بخلفية `rgb(236, 255, 112)`
  نفس اللون — التمييز البصري المطلوب محقَّق بدقة.
- **عدّاد الطلبات**: "الطلبات: 0 / 2" — يعكس `MAX_REQUESTS_PER_SESSION = 2`
  الجديد بنجاح.
- **لا إيموجي**: فحص `body.innerText` بتعبير نمطي لنطاقات الإيموجي الشائعة
  رجع `false` (لا تطابق) — الأيقونات فعلاً SVG/img، لا إيموجي.

### حالة اختبار 36 — التحقق الوظيفي الكامل بعد كل التعديلات (AppTest)
بما إن الإصلاحات غيّرت مفاتيح عناصر داخلية (بند 32)، أعدت تشغيل سيناريو
كامل عبر `AppTest` للتأكد إن التخطيط الجديد ما كسر أي وظيفة:
- محاكاة رفع PDF ناجح → زر "اقترح لي مسميات" → `suggest_job_titles` نفّذ
  فعلياً (`request_count: 1`، لا استثناءات).
- تعبئة "Backend Developer" + "الرياض" → زر "ابحث الآن" → `search_jobs`
  نفّذ فعلياً (`request_count: 2`)، والمفتاح الجديد `job-match_select`
  موجود في `session_state` (تأكيد إن إعادة تسمية المفاتيح لم تكسر ربط
  القائمة المنسدلة بنتائج البحث).
- ضغط زر ثالث ("اعرض تقديماتي") بعد الوصول للحد الجديد (2) → `request_count`
  بقي **2** (لم يُستهلك طلب Gemini إضافي)، وكل الأزرار الستة أصبحت
  `disabled: True` — حد الطلبات الجديد يعمل بشكل صحيح.

### تأكيد سلامة الملفات
SHA256 لـ `demo_resume.txt`/`demo_resume.pdf` قبل وبعد كل جلسة التصحيح:
متطابقة تماماً، ولا ملفات جديدة في `data/`.

### الخلاصة
أعدت بناء تخطيط `app.py` بالكامل ليطابق المواصفات الست المطلوبة، واكتشفت
وأصلحت **أربع مشاكل حقيقية** كان أول قياس هندسي سيفضحها فوراً لو اكتفيت
بمراجعة الكود فقط: (1) تعليق CSS يحتوي أسماء وسوم HTML أسقط كل التنسيق
بصمت، (2) تصادم substring بين مفاتيح البطاقات والعناصر الداخلية ضاعف
الارتفاعات، (3) `height` بدون `!important` خسر أمام CSS الداخلي لـ
Streamlit، (4) `<svg>` الخام يُسقَط بالكامل من DOMPurify. كل إصلاح تحقق
منه رقمياً عبر `getBoundingClientRect`/`getComputedStyle` من DOM حي فعلي،
لا افتراضاً. أداة لقطة الشاشة نفسها فشلت طوال الجلسة (مشكلة بنية تحتية
غير متعلقة بالكود) — التعويض بقياسات هندسية دقيقة كان أقوى دليل متاح،
وموثّق بصراحة هنا بدل التظاهر بأخذ لقطة شاشة لم تُلتقط فعلياً.

---

## قرار معماري: من Streamlit إلى FastAPI backend + frontend مستقل

### المرحلة 1 — `api.py` (Backend فقط، بدون واجهة فعلية بعد)

`api.py` يستورد `run_agent` و`wrap_resume_text` من `agent.py` مباشرة
**بدون أي تعديل على agent.py أو أي ملف في tools/** — تحققت عبر `git diff`
أن كليهما غير موجودين في تعديلات هذي المرحلة. الجلسات مخزّنة بـ
`dict` بالذاكرة مفتاحه `X-Session-Id` (نفس فكرة `session_state` في
Streamlit لكن على مستوى HTTP)، وحد الطلبات ارتفع لـ 6 لكل جلسة (بدل 2
في نسخة Streamlit) حسب طلب هذي المرحلة تحديداً.

نقطتا النهاية:
- `POST /api/upload`: يستقبل PDF (multipart)، يستخرج النص عبر
  `tools/resume_parser.extract_resume_text` نفسها (دون تعديل)، يخزّن
  `wrap_resume_text(...)` كـ `pending_prefix` للجلسة.
- `POST /api/message`: يستقبل `{"message": "..."}` + هيدر الجلسة، يبني
  الرسالة الكاملة (`pending_prefix + message`)، يستدعي
  `run_agent(message, session["history"])` كما هي بالضبط، يرجّع الرد +
  `tool_calls` (كل أسماء الأدوات المستدعاة بهذا الدور، مش آخر واحدة فقط
  — أكثر فائدة للواجهة القادمة لو استُدعيت أكثر من أداة بدور واحد) +
  عدّاد الطلبات.
- `app.mount("/", StaticFiles(directory="frontend", html=True))`: أنشأت
  `frontend/index.html` مؤقت (صفحة توضّح إن الـ backend شغّال والواجهة
  الفعلية قادمة بالمرحلة التالية) حتى لا يفشل `mount` عند الإقلاع لعدم
  وجود المجلد.

### حالة اختبار 37 — التسلسل الكامل عبر curl مباشرة (بدون واجهة)
شغّلت `uvicorn api:app` فعلياً، ونفّذت **نفس سيناريو Yassir الكامل**
المستخدم في كل الاختبارات السابقة، هذي المرة عبر طلبات HTTP خام
(`curl` مع ملفات JSON مؤقتة لتفادي مشاكل ترميز العربي في القشرة):

| # | الطلب | `tool_calls` المرجعة فعلياً | `request_count` |
|---|---|---|---|
| — | `POST /api/upload` (demo_resume.pdf) | — | — |
| 1 | "أبي وظيفة تناسب سيرتي في الرياض" | `["suggest_job_titles"]` | 1 |
| 2 | "اختار Backend Developer" | `["search_jobs"]` | 2 |
| 3 | "قيّم لي الوظيفة الأولى، شو رأيك تناسبني؟" | `["evaluate_match"]` | 3 |
| 4 | "حسّن سيرتي عشان تناسب هذي الوظيفة أكثر" | `["improve_resume"]` | 4 |
| 5 | "اكتب لي خطاب تقديم لهذي الوظيفة" | `["draft_cover_letter"]` | 5 |
| 6 | "اعرض ملخص تقديماتي" | `["get_application_status"]` | 6 |

نفس نتائج الوظائف الحقيقية من Jooble (Yassir - Staff Backend Engineer
أولاً)، ونفس درجة `evaluate_match` (45%) المطابقة لكل الاختبارات
السابقة عبر CLI وStreamlit — **يؤكد أن `run_agent` يتصرف بالضبط بنفس
الطريقة عبر HTTP كما عبر أي واجهة أخرى**، لأن الكود المستدعى حرفياً هو
نفسه.

### حالة اختبار 38 — حد الطلبات (429) والتحقق من عدم استهلاك طلب Gemini
الطلب السابع بعد الوصول للحد (6): رجع **HTTP 429** فعلياً مع
`{"error": "وصلتِ للحد الأقصى من الطلبات لهذي الجلسة (6 طلبات)."}` —
الحارس في `send_message` يتحقق من العدّاد **قبل** استدعاء `run_agent`
مباشرة، فلا يُستهلك أي طلب Gemini فعلي عند الرفض (نفس نمط الحماية
المزدوجة المستخدم في نسخة Streamlit).

### حالة اختبار 39 — عزل الجلسات (Session Isolation)
أرسلت رسالة لجلسة **جديدة تماماً** (`X-Session-Id: totally-different-session`)
بينما الجلسة الأولى كانت قد وصلت فعلاً لحد الـ6 طلبات — الجلسة الجديدة
بدأت من `request_count: 1` بدون أي تأثر بحد الجلسة السابقة، والرد جاء
نصياً بدون أي `tool_calls` (لأنه لا سيرة ذاتية محمّلة لهذي الجلسة الجديدة
تحديداً، فسأل الوكيل بدل ما يخمّن) — سلوك صحيح، كل جلسة معزولة تماماً
بمفتاح `X-Session-Id` الخاص بها.

### حالة اختبار 40 — معالجة الأخطاء عند حدود الـ API
- **بدون هيدر `X-Session-Id`**: `HTTP 422` من FastAPI نفسه (هيدر مطلوب) —
  رسالة خطأ واضحة تلقائياً، بدون أي كود يدوي إضافي.
- **رفع ملف غير PDF** (`.txt`): `HTTP 400` مع تفصيل `"الملف يجب أن يكون PDF."`
  — تحقق يدوي بسيط عند حدود الـ API (لا علاقة له بمنطق الوكيل الداخلي،
  فلا يخالف مبدأ "لا منطق قرار يدوي" في CLAUDE.md — هذا تحقق مدخلات HTTP
  عادي، لا قرار "أي أداة تُستدعى").

### تأكيد سلامة الملفات وسجل الخادم
راجعت سجل `uvicorn` كاملاً بعد كل الاختبارات أعلاه — **لا أخطاء ولا
tracebacks إطلاقاً**. قارنت SHA256 لـ `demo_resume.txt`/`demo_resume.pdf`
قبل وبعد — متطابقة تماماً، ولا ملفات إضافية ظهرت في `data/`.

### الخلاصة
المرحلة 1 مكتملة وناجحة: `api.py` طبقة نقل HTTP خفيفة فوق `agent.py`
كما هي بدون أي تعديل — كل قرار (أي أداة، متى، تسلسلها، وتطبيع الموقع
تلقائياً) بقي بالكامل عند Gemini، والاختبار عبر curl مباشرة (بدون أي
واجهة) أثبت أن نفس السلوك المُختبر مراراً عبر CLI وStreamlit يتكرر
حرفياً عبر HTTP. جاهزة للمرحلة التالية (الواجهة).

---

## المرحلة 2 — `frontend/` كامل (HTML/CSS/JS مستقل، بلا أي إطار عمل)

### تعديل صغير على `api.py` قبل البدء (بموافقة صريحة)
اكتشفت أن `/api/message` كان يرجع اسم الأداة فقط (`tool_calls`)، لا
قيمتها الخام — فلا يمكن بناء بطاقات وظائف حقيقية (رابط، شركة، موقع) أو
مؤشر درجة توافق رقمي من نص Gemini الحر وحده (تحليل نص حر غير موثوق).
سألت المستخدم صراحة قبل أي تعديل (رغم تعليمات "لا تلمس api.py")، ووافق
على إضافة حقل `tool_results` فقط (اسم الأداة + قيمتها الخام من
`function_response`، كما يرجعها `execute_tool` في `agent.py` دون أي
تعديل عليه). لم يتغيّر أي سطر في `agent.py` أو `tools/`.

### البنية
- `frontend/index.html` — الهيكل الثابت لكل بطاقات الخدمات ومنطقة النتائج.
- `frontend/style.css` — الهوية البصرية كاملة (لا مكتبة CSS خارجية).
- `frontend/app.js` — طبقة عرض فقط: توليد `session_id` بـ
  `crypto.randomUUID()`، استدعاءات `fetch` لـ `/api/upload` و
  `/api/message`، وتنسيق النتائج حسب `tool_results` من الرد. **لا يوجد
  فيه أي استدعاء مباشر لأداة** — كل زر يبني نص طلب عربي فقط ويرسله لـ
  `sendMessage()`، تماماً كمبدأ المرحلة السابقة.

### أداة التحقق البصري: أدوات Claude Browser فشلت مرة أخرى
حاولت `computer{action:"screenshot"}` عدة مرات (تبويبات مختلفة، بعد
انتظار كافٍ) — فشلت جميعها بنفس timeout الذي واجهته في جلسة سابقة (مشكلة
بنية تحتية، لا علاقة لها بالكود). بما إن المستخدم طلب صراحة **لقطات شاشة
فعلية** هذي المرة وشدّد على إنها إلزامية، لم أكتفِ بالبديل الهندسي
(getBoundingClientRect) المستخدم سابقاً — ثبّتت **Playwright** (متصفح
Chromium حقيقي عبر Python) وكتبت سكربت مؤقت يشغّل السيناريو الكامل فعلياً
عبر uvicorn حي، ويلتقط لقطة `full_page=True` حقيقية بعد كل خطوة. هذا
تحقق بصري فعلي 100%، لا قياس هندسي بديل.

### حالة اختبار 41 — الصفحة الأولية (`01_initial.png`)
راجعت اللقطة بنداً بند مقابل المواصفات:
- Hero بعرض كامل، خلفية `#F7F0FD`، الشعار ظاهر بوضوح أعلى يمين النص،
  عنوان "ابدأ رحلتك المهنية" bold كبير، وصف تحته، دوائر عضوية بنفسجية
  فاتحة بأحجام متفاوتة على اليسار، زر CTA ليموني "ارفعي سيرتك للبدء" ✅
- بطاقة الرفع: حدود متقطعة بنفسجية، نص عربي بالكامل (لا إنجليزي) ✅
- الشبكة: 3×2 حقيقية عبر `display:grid`، كل الأزرار مرئية بحدود بنفسجية ✅
- بطاقة "تحسين السيرة" مميزة بحدود ليموني أسمك وزر ليموني ✅
- لا إيموجي إطلاقاً — أيقونات SVG بستايل خط واحد متسق ✅
- عدّاد الطلبات "0 / 6" ✅

**علّة اكتُشفت وأُصلحت فوراً**: أول لقطة أظهرت نص بطاقة الرفع متراكباً
بشكل غير مقروء (كلمات فوق بعضها). السبب: `<label>` عنصر `inline`
افتراضياً، فحدوده وخلفيته تنكسر لأجزاء منفصلة حول عنصر `<p>` (block) بداخله
بدل صندوق واحد متماسك. الإصلاح: أضفت `display:flex; flex-direction:column`
لـ `.upload-dropzone`. أعدت الالتقاط — النص أصبح نظيفاً بدون أي تراكب
(مؤكَّد باللقطة الثانية بعد الإصلاح).

### حالة اختبار 42 — بعد رفع السيرة (`02_after_upload.png`)
- بطاقة تأكيد خضراء فاتحة: "تم رفع السيرة الذاتية" + `demo_resume.pdf` +
  أيقونة صح ✅
- بطاقات "مسميات/بحث/تقديماتي" تفعّلت (حدود بنفسجية نشطة) ✅
- بطاقات "تقييم/تحسين/خطاب" لسا فيها شارة "ابحثي عن وظائف أولاً" لأنه لا
  توجد نتائج بحث بعد — مطابق تماماً لمنطق `updateJobSelects()` ✅

### حالة اختبار 43 — نتيجة `suggest_job_titles` (`03_titles.png`)
- المسميات الأربعة ظهرت كـ pills دائرية بحدود بنفسجية فاتحة، قابلة للنقر
  فعلياً (اختبرت النقر مباشرة عبر `page.click(".title-pill")` وأثبت إنه
  يرسل `"اختار {title}"` بنجاح للخطوة التالية) ✅

**علّة ثانية اكتُشفت وأُصلحت**: النص التلقائي من Gemini كان يظهر بعلامات
Markdown خام (`**Backend Developer**`) بدل نص Bold فعلي، لأن الكود كان
يستخدم `escapeHtml` مباشرة بدون أي تفسير لـ Markdown. أضفت
`formatReplyText()` (يهرب HTML أولاً للأمان، ثم يحوّل `**نص**` إلى
`<strong>`) واستخدمتها في كل مكان يُعرض فيه نص Gemini الحر. أعدت الالتقاط
— النص أصبح Bold فعلياً بدون أي علامات نجمية ظاهرة.

### حالة اختبار 44 — نتيجة `search_jobs` (`04_search_jobs.png`)
- 5 بطاقات منفصلة حقيقية (لا قائمة نصية مرقّمة): عنوان الوظيفة Bold،
  اسم الشركة كـ badge دائري صغير، الموقع بأيقونة دبوس SVG بسيطة، رابط
  "عرض الإعلان الأصلي ←" يفتح تبويباً جديداً، وسطر تنبيه خفيف اللون أسفل
  القائمة: "تحقق من شرعية الشركة قبل التقديم — النتائج مستمدة من محرك
  تجميع (Jooble)." ✅ — نفس نتائج Jooble الحقيقية المألوفة (Yassir أولاً).
- القوائم المنسدلة الثلاث (تقييم/تحسين/خطاب) امتلأت تلقائياً بالوظيفة
  الأولى فور ظهور النتائج ✅

### حالة اختبار 45 — نتيجة `evaluate_match` (`05_evaluate_match.png`)
- Badge دائري ملوّن حسب الدرجة: النتيجة الفعلية كانت **35%** (أقل من 40)
  فظهر باللون الأحمر `#FF6B6B` بالضبط حسب قاعدة الألوان المطلوبة، مع نص
  الـ reasoning بخط عادي بجانبه ✅. (الدرجة اختلفت عن 45% المعتادة في
  اختبارات سابقة — تفاوت طبيعي في مخرجات Gemini غير الحتمية، لا خطأ
  بالكود؛ المنطق اللوني تحقق بشكل صحيح بغض النظر عن الرقم الفعلي).

### حالة اختبار 46 — نتيجة `improve_resume` (`06_improve_resume.png`)
- صندوق بإطار ليموني وعنوان "يحتاج مراجعتك" ✅، النص الكامل بمنطقة قابلة
  للطي (`max-height` + زر "عرض الكل" يبدّل التوسيع) ✅، قائمة `changes` مع
  إشارات "[مبني على: ...]" لكل تغيير ✅، زر "تحميل كملف نصي جديد" (يستخدم
  `Blob` + `URL.createObjectURL` من نص الرد مباشرة، بدون أي كتابة على
  السيرفر) ✅.

**علّة ثالثة اكتُشفت وأُصلحت**: نص التحذير القادم من `tools/resume_matcher.py`
(`MANDATORY_REVIEW_WARNING`) يحتوي إيموجي `⚠️` مضمّن بالباك إند — وهذا
ممنوع لمسه هذي المرحلة (`tools/` محظور). بما إن القاعدة "بلا أي إيموجي
في الواجهة إطلاقاً" مطلقة، أضفت تصفية إيموجي على مستوى العرض فقط: دالة
`stripEmoji()` بتعبير نمطي يغطي نطاقات الإيموجي الشائعة، مطبّقة داخل
`escapeHtml()` نفسها (تُستخدم في كل مكان تقريباً) — فتُزال أي رموز إيموجي
من أي نص قادم من الـ backend دون الحاجة لتعديل `tools/` إطلاقاً. أعدت
الالتقاط وتأكدت أن `⚠️` اختفى تماماً من نص التحذير.

**علّة رابعة اكتُشفت وأُصلحت (ليست من لقطة شاشة، بل من فحص برمجي إضافي)**:
لاحظت أن زر "حسّن سيرتي" (`.btn-accent`) يظهر بلون بنفسجي فاتح بدل الليموني
في حالة الـ hover (وPlaywright يحرّك المؤشر فوق العنصر عند `.click()`، فيبقى
بحالة hover وقت اللقطة). تحققت برمجياً عبر `getComputedStyle` أن الزر **غير
معطّل فعلياً** لكن لونه الفعلي كان `rgb(247, 240, 253)` بدل الليموني —
السبب: محدد `.btn:hover:not(:disabled)` أعلى تخصصاً (specificity) من
`.btn-accent` العادي، فيغلبه على خاصية `background` تحديداً عند الـ hover
(هذي مشكلة حقيقية تظهر لأي مستخدم حقيقي يحرّك الماوس فوق الزر، لا خاصة
بأداة الاختبار). الإصلاح: أضفت `background: var(--accent);` صراحة داخل
`.btn-accent:hover:not(:disabled)` ليفوز بخاصية اللون أيضاً. تحققت برمجياً
بعد الإصلاح: `getComputedStyle` رجعت `rgb(236, 255, 112)` (الليموني الصحيح)
بالضبط.

### تأكيد سلامة الملفات
قارنت SHA256 لـ `demo_resume.txt`/`demo_resume.pdf` قبل وبعد كامل جلسة
الالتقاط (6 طلبات Gemini فعلية عبر السيناريو الكامل) — متطابقة تماماً،
ولا ملفات جديدة في `data/`. ملف `improved_resume.txt` يُنشأ بالكامل في
المتصفح عبر `Blob` — لا أي كتابة على القرص من السيرفر.

### الخلاصة
المرحلة 2 مكتملة: واجهة HTML/CSS/JS مستقلة كاملة، بلا أي منطق قرار جديد
(كل زر يبني نص طلب عربي فقط ويمرره لنفس `sendMessage()` → `/api/message`
→ `run_agent()`)، وتنسيق بصري مختلف فعلياً لكل نوع نتيجة (pills، بطاقات
وظائف، مؤشر توافق ملوّن، صندوق مراجعة قابل للطي مع تحميل). **لقطات شاشة
فعلية حقيقية عبر Playwright** (بديل ناجح لأداة المتصفح المعطّلة) كشفت
**أربع علل حقيقية** ما كانت لتظهر من مراجعة الكود وحدها: تراكب نص بسبب
`<label>` inline، Markdown خام غير مُفسَّر، إيموجي مسرّب من نص backend،
وتضارب specificity في CSS يُفسد لون الزر عند hover — كل واحدة أُصلحت
وتحقق منها الإصلاح فعلياً بلقطة/فحص برمجي جديد.

---

## جولة تلميع بصري (polish pass) — إصلاح 5 مشاكل محدّدة طلبها المستخدم

استخدمت نفس منهجية Playwright (لقطات فعلية بعد كل إصلاح، لا لقطة واحدة
بالنهاية) لأن أدوات Claude Browser فشلت مرة أخرى في هذي الجلسة (نفس
مشكلة البنية التحتية المتكررة).

### حالة اختبار 47 — تشخيص علة الهيدر (بند 1) قبل أي إصلاح
شغّلت السيرفر مباشرة وفحصت الهيدر برمجياً (`naturalWidth`/`complete` لكل
`<img>`) — الصورتان كانتا تُحمَّلان بنجاح فعلياً (لا 404 حقيقي)، فالمشكلة
لم تكن صورة "معطوبة" تقنياً. الفحص البصري كشف السبب الحقيقي: الهيدر نفسه
(شعار + "CareerPilot") كان سليماً فعلاً بعنصر واحد من كل نوع، لكن **قسم
الـ Hero أسفله كان يعرض نفس أيقونة الشعار مرة ثانية بمفردها** (بلا نص)
في زاويته العلوية — عين المستخدم رأت شعارين متقاربين عمودياً كـ"ازدواجية"،
والأيقونة الثانية المعزولة بلا سياق نصي بدت "غير مكتملة/معطوبة". **الحل**:
حذفت شعار الـ Hero تماماً (`<img class="logo">`) — أبقيت مصدر العلامة
التجارية الوحيد في الهيدر العلوي فقط. أضفت أيضاً `width`/`height` صريحين
لصورة الهيدر و`<link rel="icon">` لمنع أي 404 favicon قد يظهر كأيقونة
معطوبة في تبويب المتصفح.

### حالة اختبار 48 — التحقق البصري الكامل بعد كل الإصلاحات دفعة واحدة
طبّقت الإصلاحات الخمسة معاً ثم التقطت لقطات فعلية لكل حالة رئيسية
(الصفحة الأولية، بعد الرفع، hover على بطاقة، ثم السيناريو الكامل: مسميات
→ بحث → تقييم → تحسين)، وراجعت كل واحدة بنداً بند:

**بند 1 (الهيدر)**: لقطة الصفحة الأولية أظهرت شعاراً واحداً بالضبط + نص
"CareerPilot" واحد في الهيدر العلوي — لا تكرار، لا أيقونة يتيمة في الـ Hero. ✅

**بند 2 (النص المكرر)**: بطاقة الرفع أصبحت تعرض "الخطوة الأولى" (eyebrow
صغير بلون بنفسجي) فوق عنوان "ارفعي سيرتك الذاتية" — مختلف تماماً عن نص
زر الـ CTA "ارفعي سيرتك للبدء" في الـ Hero. تحقق عبر قاعدة CSS مخصصة
`.upload-card p.upload-eyebrow` (لاحظت إثناء الكتابة أن `.upload-card p`
العادية كانت ستفوز بالتخصص على `.upload-eyebrow` بمفردها لولا هذا
التخصيص الإضافي — تحققت من الحساب يدوياً قبل الحفظ). ✅

**بند 3 (شارات الأيقونات)**: كل الأيقونات الست + أيقونة بطاقة الرفع +
أيقونة بطاقة التأكيد أصبحت داخل دائرة بخلفية `#F7F0FD` بحجم 48px، والأيقونة
نفسها بلون `#D3A0FD` وحجم 24px بالمنتصف تماماً — تحقق بصري مباشر من اللقطات،
وهذا التغيير فعلاً غيّر طابع الواجهة من "مسطّح" إلى "premium" بشكل ملحوظ. ✅

**بند 4 (التباعد + hover)**: `padding` البطاقات ارتفع من `1.25rem` إلى
`1.6rem` (+28%)، `padding` بطاقة الرفع من `1.75rem` إلى `2.3rem` (+31%)،
الفجوة بين بطاقات الشبكة من `1.25rem` إلى `1.75rem`، و`padding` الـ Hero
العمودي من `2.5rem` إلى `4rem` (+60%). أثر الـ hover (`transform:
scale(1.02)` + ظل أعمق) **لم يكن واضحاً بصرياً في لقطة كاملة الصفحة**
(تغيير 2% طفيف بتصميم)، فتحققت منه **برمجياً** عبر `getComputedStyle`:
`transform` قبل الـ hover = `none`، وبعده =
`matrix(1.02, 0, 0, 1.02, 0, 0)`، و`box-shadow` يتعمّق من
`rgba(...,0.04) 0 6px 20px` إلى `rgba(...,0.1) 0 14px 34px` — ثم أكدت
بصرياً عبر قصّ/تكبير جزء من اللقطة حول البطاقة المُمرَّر عليها، فظهر الظل
الأعمق بوضوح. ✅

**بند 5 (رسم الـ Hero)**: ملف `assets/hero-illustration.svg` كان موجوداً
فعلاً وقت الاختبار (أضافه المستخدم بالتوازي)، فظهر الرسم التوضيحي (شخص
يراجع أوراق سيرة ذاتية بعلامات صح) في الجانب المقابل للنص، بحجم متناسب
(`max-height:260px` داخل عمود `flex:2` من أصل 5 = ~40% من عرض الـ Hero)،
ومتموضع بين الدوائر الزخرفية بانسجام. اختبرت أيضاً عرضاً ضيقاً (500px) —
الرسم والدوائر تختفي تماماً (`display:none` عبر media query)، والنص
يتمركز بشكل نظيف بدلاً منه، مطابقاً لخيار "hidden على الشاشات الضيقة"
المذكور في الطلب. أضفت أيضاً `onerror="this.style.display='none'"` على
عنصر `<img>` كضمان: لو حُذف الملف لاحقاً أو لم يوجد، يختفي بصمت بدل إظهار
أيقونة معطوبة. ✅

### تأكيد عدم كسر أي وظيفة قائمة
أعدت تشغيل السيناريو التسلسلي الكامل (رفع → مسميات → بحث → تقييم →
تحسين) بعد كل التعديلات — نفس نتائج Jooble الحقيقية، نفس درجة التوافق
(45% هذي المرة، ضمن الفئة الكهرمانية المتوقعة لـ 40-69)، صندوق "يحتاج
مراجعتك" وزر التحميل يعملان، القوائم المنسدلة تمتلئ تلقائياً من نتائج
البحث — كل الإصلاحات البصرية من الجولة السابقة (لا Markdown خام، لا
إيموجي، لون الزر الصحيح عند hover) بقيت سليمة.

### تأكيد سلامة الملفات
قارنت SHA256 لـ `demo_resume.txt`/`demo_resume.pdf` قبل وبعد — متطابقة
تماماً.

### الخلاصة
كل البنود الخمسة المطلوبة أُصلحت وتحقق منها بصرياً (لقطات Playwright فعلية
بعد كل تغيير) أو برمجياً حيث كان التغيير طفيفاً جداً ليظهر بوضوح في لقطة
كاملة الصفحة (تأثير hover). العلة الحقيقية وراء بند 1 لم تكن كما افترضتُ
أول وهلة (صورة معطوبة تقنياً) — بل ازدواجية شعار حقيقية بين الهيدر
والـ Hero، اكتُشفت بالفحص البصري المباشر بدل الافتراض.

---

## إصلاح صيغة التذكير/التأنيث النحوية في كل الواجهة

### المنهجية
بحثت عن كل صيغ الأمر/الفعل المؤنّث الموجّهة للمستخدم عبر grep شامل على
`frontend/index.html` و`frontend/app.js` و`frontend/style.css` (أنماط:
لاحقة "ي" على أفعال أمر، ولاحقة "ـتِ" على أفعال ماضٍ بصيغة المخاطبة)،
ميّزت كل نتيجة حسب السياق (فعل موجّه فعلاً للمستخدم مقابل صفة/اسم ينتهي
بنفس الحروف بالمصادفة، أو فعل ضمن رسالة يبنيها الكود لتمثّل كلام المستخدم
موجّهاً للوكيل نفسه — تلك تبقى مذكّرة أصلاً لأنها تخاطب الوكيل لا المستخدمة).

### حالة اختبار 49 — القائمة الكاملة للتصحيحات المطبَّقة

**`frontend/index.html`** (8 مواضع):
| قبل | بعد | الموضع |
|---|---|---|
| ارفعي سيرتك للبدء | ارفع سيرتك للبدء | زر CTA بالـ Hero |
| ارفعي سيرتك الذاتية | ارفع سيرتك الذاتية | عنوان بطاقة الرفع |
| اسحبي ملف PDF هنا أو اضغطي لاختياره | اسحب ملف PDF هنا أو اضغط لاختياره | نص منطقة السحب والإفلات |
| ابحثي عن وظائف حقيقية حسب المسمى والمدينة. | ابحث عن وظائف حقيقية حسب المسمى والمدينة. | وصف بطاقة البحث |
| قيّمي مدى توافق سيرتك... | قيّم مدى توافق سيرتك... | وصف بطاقة التقييم |
| ابحثي عن وظائف أولاً (×3: تقييم/تحسين/خطاب) | ابحث عن وظائف أولاً | شارة تعطيل القوائم المنسدلة |
| حسّني سيرتك لتتوافق... | حسّن سيرتك لتتوافق... | وصف بطاقة التحسين |
| ...اللي سجّلتِ تقديمك عليها. | ...اللي سجّلت تقديمك عليها. | وصف بطاقة التقديمات |

**`frontend/app.js`** (4 مواضع + إصلاح إضافي مصدره الخادم):
- `تأكدي من تشغيل السيرفر` → `تأكد من تشغيل السيرفر` (رسالة فشل رفع الملف)
- `تأكدي...وحاولي مرة أخرى` → `تأكد...وحاول مرة أخرى` (رسالة فشل الشبكة العامة)
- `وصلتِ للحد الأقصى...` → `وصلت للحد الأقصى...` (رسالة حد الطلبات المبنية محلياً)
- `أدخلي المسمى الوظيفي والمدينة أولاً.` → `أدخل المسمى الوظيفي والمدينة أولاً.`

**اكتشاف إضافي مهم**: عند تتبّع مسار رسالة "تجاوز حد الطلبات" وجدت أن حالة
الـ **HTTP 429 الفعلية** (وليس فقط الفحص المسبق بالمتصفح) كانت تعرض
`data.error` **من `api.py` مباشرة** — وهذا النص يحتوي نفس الصيغة المؤنثة
"وصلتِ" **من الخادم نفسه**، وتعديل `api.py` خارج نطاق هذي المهمة (مقصورة
على `frontend/`). طبّقت نفس أسلوب حالة "إيموجي `improve_resume`" من الجولة
السابقة: بدل عرض `data.error` كما هو، بنيت الرسالة محلياً في `app.js`
بنفس النص المذكّر المستخدم أصلاً في الفحص المسبق، فتُعرض دائماً الصيغة
الصحيحة بغض النظر عن مصدر التنبيه (فحص العميل أو رد الخادم الفعلي).

### حالة اختبار 50 — فحص شامل للتأكد من عدم تفويت أي حالة
شغّلت grep نهائي بعد كل التعديلات بحثاً عن الأنماط نفسها
(`تِ|ارفعي|اختاري|ابدئي|جربي|قيّمي|ابحثي|اسحبي|اضغطي|حسّني|سجّلتِ|تأكدي|
حاولي|أدخلي|وصلتِ`) — **النتيجة الوحيدة المتبقية** كانت داخل تعليق برمجي
أضفته أنا بنفسي في `app.js` يشرح سبب الإصلاح (يذكر "وصلتِ" كمثال توثيقي
للمشكلة الأصلية، لا كنص فعلي معروض للمستخدم) — لا حالة حقيقية فائتة.

### حالات مستبعدة عمداً (فحصتها وتأكدت أنها ليست أخطاء)
- `يقيّم` في وصف الـ Hero ("مرشدك الذكي يبحث ويقيّم...") — فعل مضارع بصيغة
  الغائب المذكّر يصف الوكيل نفسه، لا أمراً موجّهاً للمستخدم. **لم يُغيَّر**.
- `نصي` في "تحميل كملف نصي جديد" — صفة ("نصّي" = متعلق بالنص)، لا فعلاً.
  **لم يُغيَّر**.
- `الأصلي` في "عرض الإعلان الأصلي" — صفة ("أصلي" = original)، لا فعلاً.
  **لم يُغيَّر**.
- رسائل الطلب المبنية في JS والمُرسَلة للوكيل (`قيّم توافق سيرتي...`،
  `حسّن سيرتي الذاتية...`، `اكتب لي خطاب تقديم...`) — هذي جمل يقولها
  *المستخدم للوكيل*، فالفعل يخاطب الوكيل (جهة غير معروفة الجنس، الافتراضي
  مذكّر) لا المستخدم — **كانت مذكّرة أصلاً، لم تحتَج تعديلاً**.

### علة غير متوقعة اكتُشفت أثناء التحقق: مسارات ملفات مطلقة معطوبة
أول لقطة شاشة بعد الإصلاحات جاءت **بلا أي تنسيق CSS إطلاقاً** (HTML خام
بخط المتصفح الافتراضي، حقل رفع ملف أصلي ظاهر، عنوان "CareerPilot" مكرر
مرتين). فحصت `frontend/index.html` مباشرة ووجدت أن روابط `<link
rel="stylesheet">`، `<link rel="icon">`، وعنصري `<img>` كانت تشير لمسارات
Windows مطلقة كاملة (`C:\Users\pc\Desktop\CareerPilot\frontend\...`) بدل
المسارات النسبية الصحيحة (`/assets/logo.png`, `style.css`) — تغيير خارجي
حدث على الملف قبل هذي الجلسة. صحّحت المسارات الأربعة كلها للصيغة النسبية
الصحيحة، وأعدت الالتقاط — الصفحة عادت للتنسيق الكامل الصحيح، واختفى ظهور
"CareerPilot" المزدوج (كان في الحقيقة نص `alt="CareerPilot"` الاحتياطي
لصورة معطوبة يظهر بجانب `<span>CareerPilot</span>` المجاور، لا ازدواجية
حقيقية في HTML). هذا **ليس متعلقاً بمهمة صيغة التذكير**، لكن كان لازماً
إصلاحه لأخذ لقطة تحقق فعلية وذات معنى.

### تأكيد سلامة الملفات
قارنت SHA256 لـ `demo_resume.txt`/`demo_resume.pdf` قبل وبعد — متطابقة
تماماً.

### الخلاصة
كل صيغ الأمر/الفعل المؤنّثة الموجّهة للمستخدم في `frontend/` أصبحت
مذكّرة/محايدة افتراضياً — 12 موضعاً في الكود (8 بـ HTML، 4 بـ JS) + معالجة
حالة خاصة لرسالة خادم لا يمكن تعديلها مباشرة (نفس أسلوب `stripEmoji` من
الجولة السابقة: تصفية/استبدال على مستوى العرض لا لمس الملف المحظور).
تحقق grep نهائي شامل لم يجد أي حالة فائتة. لقطة الشاشة النهائية تؤكد
بصرياً نص الزر الرئيسي وعنوان بطاقة الرفع كلاهما بالصيغة المذكّرة الصحيحة.
