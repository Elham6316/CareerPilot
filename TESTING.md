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

---

## إعادة تصميم كاملة لـ frontend/ — نموذج تصميم تحريري/فاخر (Editorial)

### الطلب
إعادة تصميم UI كاملة مستوحاة من بنية redseaglobn.com: هيرو كامل الشاشة
بعنوان ضخم واحد وCTA واحد، إلغاء شبكة البطاقات الست واستبدالها بلوحات
كاملة العرض متبادلة (لون خلفية + محاذاة نص)، نمط "eyebrow" (كلمة صغيرة
بأحرف كبيرة فوق كل عنوان قسم)، شريط إحصائيات، تمرير رأسي بفراغ كبير بين
الأقسام، حركة ظهور تدريجي عبر IntersectionObserver، هيدر ثابت يكتسب
ضبابية عند التمرير. **قيد صارم**: عدم لمس `api.py` أو `agent.py` أو
`tools/` إطلاقاً، والإبقاء على كل الألوان والشعار والمنطق البرمجي
(كل زر لازم يبني نص طلب عربي ويمرره لـ `sendMessage()`).

### المنهجية
أعدت قراءة `frontend/index.html` (144 سطر) و`frontend/app.js` (467 سطر)
كاملين أولاً لتحديد **كل** الـ `id` التي يعتمد عليها JS
(`heroCta, uploadSection, uploadCard, dropzone, fileInput, uploadError,
confirmCard, confirmFilename, uploadIconSlot, confirmIconSlot,
counterPill, limitCard, iconTitles..iconApplications,
btnTitles..btnApplications, searchTitleInput, searchCityInput,
matchSelect/improveSelect/letterSelect, matchBadge/improveBadge/letterBadge,
resultsCard, resultsEmpty, resultsContent`) — القرار: **الإبقاء على كل
هذي الـ id حرفياً** رغم إعادة بناء الـ HTML المحيط بها بالكامل، لتقليل
مخاطر كسر منطق JS القائم لأدنى حد ممكن، بدل تغيير الـ id وتعديل كل استعلام
DOM في app.js.

### حالة اختبار 51 — إعادة بناء `frontend/index.html`
استبدلت البنية بالكامل: هيدر ثابت (`site-header`، شعار + عداد طلبات)،
هيرو كامل الشاشة (`min-height: calc(100vh - 68px)` مع بلوبات SVG-less
عبر دوائر CSS ملونة + رسم `hero-illustration.svg`)، شريط رفع كامل العرض
مع eyebrow "الخطوة الأولى"، ثم **6 أقسام `<section class="service-panel">`
منفصلة** بدل `<div class="services-grid">` الواحد — كل قسم بلون خلفية
من دورة ثلاثية (`tint-0` أبيض / `tint-1` بنفسجي فاتح / `tint-2` بنفسجي
مصبوغ) ومحاذاة متبادلة (`align-right` / `align-left`)، ثم شريط إحصائيات
(`stats-band`) بخلفية داكنة وأرقام كبيرة بلون accent، ثم قسم نتائج كامل
العرض. كل عنصر أضفت له class `reveal` (للحركة) محتفظاً بكل الـ id
الأصلية دون استثناء. **اكتشفت أثناء البناء** أن تسمية `div` الرفع
الأولي بـ `id="uploadState"` بدل `uploadCard` سيكسر app.js فوراً (يستعلم
`document.getElementById("uploadCard")` بالسطر 70) — صححتها قبل أي
اختبار حي. ✅

### حالة اختبار 52 — إعادة كتابة `frontend/style.css` بالكامل
أبقيت `:root` كما هو تماماً (كل متغيرات الألوان الأصلية) وأضفت `--kicker:
#8D8D8D` الجديد فقط لصيغة الـ eyebrow. استبدلت شبكة البطاقات بقواعد
`.service-panel`/`.panel-inner`/`.panel-text`/`.panel-motif` (فقاعة SVG
كبيرة على الجانب المقابل للنص)، أضفت `clamp()` لكل العناوين الكبرى
(الهيرو: `clamp(2.75rem, 5vw + 1rem, 4.75rem)` ≈ 76px على شاشة سطح مكتب
عريضة، يتقلّص لـ 44px على الجوال)، `.reveal{opacity:0; transform:
translateY(28px)}` + `.reveal.visible{opacity:1; transform:none}` للحركة،
`.site-header.scrolled{background: rgba(255,255,255,.75);
backdrop-filter: blur(14px)}` للضبابية. أزلت كل الحدود الثقيلة من مكوّنات
النتائج (`.job-card` أصبح فاصل سفلي بسيط بدل صندوق كامل، `.review-box`
بلا حدود بخلفية بنفسجية فاتحة فقط) مع تكبير الخط والمسافات — **حافظت على
كل أسماء الـ class التي يولّدها app.js ديناميكياً** (`.title-pill,
.job-card, .match-score-badge.high/mid/low, .review-box, .status-badge...`)
بلا أي تغيير في التسمية، فقط إعادة تصميم القواعد. ✅

### حالة اختبار 53 — إضافات صغيرة مبرَّرة على `frontend/app.js`
أضفت 3 كتل فقط، كلها عرضية بحتة بلا أي منطق قرار جديد:
1. مستمع `scroll` يبدّل class `scrolled` على الهيدر (ضبابية الخلفية).
2. `IntersectionObserver` يضيف class `visible` لكل عنصر `.reveal` عند
   دخوله الشاشة (حركة الظهور التدريجي المطلوبة صراحة بالطلب).
3. داخل `setServicesEnabled()` الموجودة أصلاً: حلقة إضافية تبدّل class
   `panel-disabled` على كامل عنصر اللوحة (`panelTitles`..`panelApplications`)
   بدل الاكتفاء بتعطيل الأزرار والحقول فقط — لتحقيق "اللوحات معتّمة بالكامل
   قبل رفع السيرة" كما ينص الطلب، لا مجرد "غير قابلة للنقر".
4. سطر واحد في بداية `sendMessage()`: `scrollIntoView` لقسم النتائج،
   لتحقيق "smooth scroll to it" المطلوب صراحة.
لم أُغيّر أي سطر من منطق `fetch`, `renderResult`, أو أي دالة `renderX`
الموجودة — فقط أضفت. ✅

### التحقق البصري (Playwright، 1440×900)
شغّلت `careerpilot-api` (uvicorn) والتقطت 9 لقطات:
- **الهيرو**: عنوان ضخم واحد "ابدأ رحلتك المهنية"، عبارة فرعية واحدة، CTA
  ليموني واحد فقط — لا ازدحام. ✅
- **الهيدر عند التمرير**: خلفية شفافة تتحول لضبابية بيضاء (`backdrop-filter`
  ظاهر بصرياً خلف النص). ✅
- **قبل رفع السيرة**: كل اللوحات الست معتّمة (opacity ~0.45) وغير قابلة
  للنقر، الألوان تتبادل (أبيض/بنفسجي فاتح/بنفسجي مصبوغ) والمحاذاة تتبادل
  (يمين/يسار) بصرياً بوضوح بين لوحة وأخرى. ✅
- **شريط الإحصائيات**: خلفية داكنة، 3 أرقام كبيرة بلون accent
  (`0%` / `100%` / `7`) مع تسمية صغيرة تحت كل رقم. ✅
- **بعد الرفع**: بطاقة التأكيد تظهر، اللوحات تفقد التعتيم فوراً وتصبح
  تفاعلية (زر "اقترح لي مسميات" نشط). ✅
- **سيناريو حي كامل**: رفعت `data/demo_resume.pdf` فعلياً ثم ضغطت زر
  "اقترح لي مسميات" — عداد الطلبات ارتفع من 0/6 إلى 1/6 (استدعاء API حقيقي
  ناجح)، الصفحة انزلقت تلقائياً (`scrollIntoView`) لقسم النتائج، ورد
  Gemini الحقيقي ظهر منسّقاً (نص عريض `<strong>` من `**...**`، قائمة
  مرقّمة) بلا حدود ثقيلة وبخط أكبر ومساحة أكبر، مطابقاً لطلب "restyle
  only: remove heavy borders, larger type, more air". ✅

**ملاحظة فنية**: أول محاولة `full_page=True` لقطة واحدة أظهرت فراغاً
غريباً وتكرار الهيدر في الأسفل — تحققت أنه **قصور تقني في تجميع لقطات
Playwright الكاملة مع عناصر `position: sticky`**، وليس خللاً حقيقياً:
أعدت الالتقاط بالتمرير التدريجي الفعلي (`scrollTo` بخطوات) قبل كل لقطة
مقطوعة، وظهر شريط الإحصائيات وقسم النتائج بشكل صحيح تماماً مع تفعيل حركة
`.reveal` كما هو متوقع.

### تأكيد عدم كسر أي وظيفة قائمة
اختبار حي كامل (رفع → اقتراح مسميات) نجح باستدعاء API حقيقي، لا أخطاء في
`preview_logs`، عداد الطلبات يعمل، منطق تعطيل/تفعيل اللوحات يعمل، لا لمس
لـ `api.py`/`agent.py`/`tools/`.

### الخلاصة
كل بنود الطلب الستة (هيدر ثابت، هيرو كامل الشاشة، شريط رفع، لوحات خدمات
متبادلة كاملة العرض بدل شبكة، شريط إحصائيات، قسم نتائج مُعاد تصميمه) +
متطلبات الطباعة (`clamp()`, تباين حجم درامي, eyebrow مصغّر) + الحركة
(`IntersectionObserver` fade-up) مُنفَّذة ومتحقق منها بصرياً عبر Playwright.
كل الألوان والشعار ومنطق `sendMessage()`/API الأصلي بقي بلا تغيير جوهري —
الإضافات الوحيدة لـ `app.js` عرضية بحتة (تعتيم لوحات، تمرير سلس، حركة
ظهور، ضبابية هيدر).

---

## إعادة بناء كاملة لـ frontend/ — App Shell (واجهة منتج، لا صفحة تُمرَّر)

### الطلب
التخلي عن نموذج "الصفحة التي تُمرَّر" كلياً والانتقال لهيكل تطبيق ثابت
بجزأين: شريط جانبي يمين (280px) بقائمة الخدمات الست، ومساحة عمل رئيسية
تعرض خدمة واحدة نشطة في كل مرة (لا تمرير للصفحة نفسها، `100vh` دائماً).
حالتان لمساحة العمل: قبل الرفع (هيرو + dropzone) وبعد الرفع (تفاصيل
الخدمة النشطة + منطقة نتائج تُمرَّر داخلياً فقط). قيد صارم كسابقه: عدم لمس
`api.py`/`agent.py`/`tools/`، الإبقاء على الألوان والشعار ورسم الهيرو.

### المنهجية
هذا تغيير سلوكي حقيقي لا مجرد إعادة تصميم بصري — سابقاً كانت الخدمات الست
معروضة كلها معاً (شبكة أو لوحات متبادلة)، والآن **خدمة واحدة فقط ظاهرة في
كل لحظة** يختارها المستخدم من الشريط الجانبي. أعدت التفكير ببنية `app.js`
من الصفر مع الحفاظ على المبدأ الجوهري في `CLAUDE.md`: كل زر إجراء يبني
نص طلب عربي ويمرره لـ `sendMessage()` فقط — **لا قرار جديد بشأن "أي أداة
تُستدعى"** أُضيف. الإضافة السلوكية الوحيدة الحقيقية هي **تخزين مؤقت
للنتائج لكل خدمة** (`serviceResultCache`): عند إرسال طلب، يُحفظ الرد كاملاً
تحت مفتاح الخدمة النشطة وقتها؛ عند التنقل بين علامات التبويب، يُعرض الرد
المخزَّن لتلك الخدمة (إعادة استدعاء دالة `renderX` الأصلية نفسها بنفس
الوسائط لضمان عمل كل مستمعات الأحداث الداخلية كزر "عرض الكل" وزر التحميل)
أو حالة فارغة مخصصة لو لم تُشغَّل الخدمة بعد — قرار تصميم متعمد بدل تجميد
HTML خام لتفادي فقدان تفاعلية العناصر المُعاد إدراجها.

### حالة اختبار 54 — إعادة بناء `frontend/index.html`
هيكل جديد بالكامل: `<aside class="sidebar">` (شعار + قائمة تنقل 6 عناصر +
أسفل ثابت: عداد طلبات بشريط تقدّم + شارة الملف المرفوع مع زر "استبدال")
و`<main class="workspace">` بحالتين: `#uploadState` (هيرو مصغّر + dropzone)
و`#serviceWorkspace` (6 "panes" — كل واحدة تحمل عنوان/وصف/حقول/زر إجراء
خاص بها، واحدة فقط ظاهرة عبر `.hidden` في كل لحظة، تُحدَّد بـ
`data-service`) + `#resultsArea` مشترك يُمرَّر داخلياً (`overflow-y:auto`)
بلا أي تمرير لعناصر الصفحة نفسها. أضفت أيضاً `<nav class="bottom-tabs">`
(6 أزرار أيقونات فقط) لوضع الجوال. **حافظت على كل الـ id التي يعتمد عليها
منطق الأزرار من النسخ السابقة** (`btnTitles`..`btnApplications`,
`searchTitleInput/searchCityInput`, `matchSelect/improveSelect/letterSelect`,
`matchBadge/improveBadge/letterBadge`, `resultsContent`) — فقط أزلتُ
عناصر لم تعد موجودة في هذا الهيكل (`heroCta`, لوحات motif الكبيرة، شريط
الإحصائيات) وأضفتُ عناصر جديدة يحتاجها الشريط الجانبي (`fileChip`,
`fileChipIcon`, `confirmFilename`, `replaceBtn`, `meterFill`, `counterPill`,
`limitCard`). ✅

### حالة اختبار 55 — إعادة كتابة `frontend/style.css`
`html, body { overflow: hidden; height: 100% }` + `.app-shell { display:
flex; height: 100vh }` لضمان "صفر تمرير للصفحة، 100vh دائماً" — بفضل
`direction: rtl` على `<body>` يظهر أول عنصر DOM (`.sidebar`) تلقائياً على
اليمين دون أي قاعدة `order`/`float` إضافية. `.workspace { flex:1;
overflow: hidden; display:flex; flex-direction:column }` مع
`.results-area { flex:1; min-height:0; overflow-y:auto }` وحدها القابلة
للتمرير — كل ما فوقها (عنوان/وصف/حقول/زر) ثابت المكان عند تبديل الخدمة أو
عند طول النتائج. عنصر `.nav-item.active::before` يرسم الخط الجانبي
الأرجواني 3px المطلوب (`position:absolute; right:0`). أعدت تصميم كل بطاقات
النتائج (`.job-card`, `.match-card`, `.review-box`, `.plain-reply`,
`.titles-pills`, إلخ) لتصبح `background:#fff; border-radius:16px;
box-shadow: var(--card-shadow)` **بلا أي `border`**، والفصل بينها عبر
الفراغ فوق خلفية `#FAFAFA` للمساحة نفسها — بالضبط كما ينص الطلب. أضفت
`--accent-tint: #F8FFD9` (اللون الجديد المطلوب صراحة بالنطاق اللوني) وأستخدمه
في هالة نقطة "الخدمة الأهم" اللَيمونية. ✅

### حالة اختبار 56 — إعادة بناء `frontend/app.js` حول التنقل بين الخدمات
أضفت `selectService(key)` (تبديل class فعّال + إظهار/إخفاء اللوحة المطابقة
+ رسم النتيجة المخزّنة أو الحالة الفارغة)، وربطتها بكل من `.nav-item`
و`.tab-item` معاً عبر استعلام واحد — **تعمّدت عدم استخدام محدد
`[data-service]` العام في ربط حدث النقر** لأن `.service-pane` تحمل نفس
الخاصية؛ لو استُخدم المحدد العام لأصبح النقر داخل أي حقل إدخال بلوحة نشطة
يعيد استدعاء `selectService` على نفسها بلا داعٍ (اكتشفتها أثناء المراجعة
قبل التنفيذ، لا بعده). `sendMessage()` تحفظ الآن `requestedService`
(الخدمة النشطة وقت الإرسال) وتخزّن الرد الكامل في `serviceResultCache`
بعد نجاحه، وترسم فقط لو المستخدم ما زال على نفس التبويب. أضفت `updateMeter()`
لتحديث نص العداد وعرض شريط التقدّم معاً بدل تكرار المنطق بمكانين. باقي
الدوال (`renderTitles`, `renderJobs`, `renderMatch`, `renderReview`,
`renderLogConfirm`, `renderApplications`, `stripEmoji`, `escapeHtml`,
`formatReplyText`) بلا أي تغيير جوهري في منطقها — فقط أضفت استدعاء
`animateIn()` (صعود 8px خفيف عبر إعادة تشغيل CSS animation) في نهاية كل
واحدة لتحقيق بند الحركة المطلوب. ✅

### علة حقيقية اكتُشفت ومُصلحت أثناء اختبار الجوال
أول تشغيل لسيناريو الجوال الكامل (رفع → تنقّل) **تعطّل فعلياً**:
`page.wait_for_selector("#fileChip:not(.hidden)")` انتهت مهلته رغم أن
الرفع نجح فعلياً (تحقق عبر تتبّع استجابة الشبكة: `200 /api/upload`) وأن
الكلاس `hidden` أُزيل بالفعل من `#fileChip`. السبب الجذري: عند عرض 900px
فأقل كانت قاعدة `.sidebar { display: none }` تُخفي **الشريط الجانبي
بالكامل** — وبما أن شارة الملف المرفوع وعداد الطلبات موجودان **داخل**
الشريط الجانبي، اختفيا كلياً على الجوال بلا أي بديل، رغم نجاح الرفع
فعلياً. هذا تعارض مباشر مع بند "6 أزرار أيقونات فقط بشريط سفلي" الذي
يغطي **التنقل** فقط، لا **حالة الرفع نفسها**. الإصلاح: بدل إخفاء الشريط
الجانبي بالكامل، يتحوّل لشريط علوي رفيع ثابت (`position: sticky`) يحمل
الشعار + شارة الملف/"استبدال" فقط (`.nav-list { display:none }` وحدها،
بقاء البقية)، بينما التنقل الفعلي بين الخدمات ينتقل بالكامل لشريط
التبويبات السفلي كما هو مطلوب. أعدت الاختبار بعد الإصلاح — نجح رفع
الملف والتنقل والبحث كلها بلا أي timeout. ✅

### التحقق البصري (Playwright)
**سطح المكتب (1440×900)** — 9 لقطات + تحقق برمجي من الكلاسات:
- **الحالة أ (قبل الرفع)**: `sidebar.classList.contains("disabled")` = `true`
  فعلياً (تحقق برمجي، لا بصري فقط) — هيرو مركزي، رسم توضيحي، dropzone
  متقطع الحدود، بلوبات زخرفية خافتة خلف المحتوى. ✅
- **الحالة ب بعد الرفع**: `sidebar.disabled` = `false` فعلياً، شارة الملف
  تظهر بـ"demo_resume.pdf" + زر "استبدال"، عنصر تنقل "مسميات وظيفية" نشط
  تلقائياً (خط أرجواني جانبي + خلفية بنفسجية فاتحة + خط عريض). ✅
- **نتيجة حية 1 (مسميات وظيفية)**: عداد الطلبات 0/6→1/6، شريط تقدّم
  ليموني، بطاقة بيضاء بلا حدود بظل خفيف تحوي 4 pills حقيقية من رد Gemini
  الفعلي (Cloud Engineer, Python Developer...). ✅
- **نتيجة حية 2 (بحث عن وظائف)**: بحث فعلي عبر Jooble بمدخلين حقيقيين
  ("Python Developer" / "Riyadh, Saudi Arabia") — بطاقات وظائف حقيقية
  (Litmus Automation, Yassir, Devsinc) بمنطقة نتائج **تُمرَّر داخلياً**
  بينما العنوان/الحقول/الزر تبقى ثابتة أعلى الشاشة دون حراك — تحقق بصري
  مباشر من السلوك المطلوب "results area fills remaining height, scrolls
  INTERNALLY". العداد 2/6. ✅
- **التخزين المؤقت للنتائج**: بعد تشغيل البحث، رجعت لتبويب "مسميات
  وظيفية" — عرضت **نفس الـ 4 pills** من الطلب الأول فوراً دون طلب API
  جديد ودون حالة فارغة، يثبت أن `serviceResultCache` يعمل كما صُمم. ✅
- **نتيجة حية 3 (تحسين السيرة — الخدمة الأهم)**: القائمة المنسدلة
  امتلأت تلقائياً من نتائج البحث، الزر الليموني `#ECFF70` (لا الأرجواني)
  يظهر فقط لهذي الخدمة، رد `improve_resume` حقيقي كامل (بيانات Sara
  Al-Otaibi التجريبية) مع قائمة تغييرات، تحذير المراجعة، وزر تحميل يعمل —
  عداد 3/6. ✅
- **حالة فارغة لكل خدمة**: تبويب "تقديماتي" (بلا حقول إدخال) يعرض أيقونة
  دائرية صغيرة + سطر واحد مُخصَّص ("اعرض ملخص تقديماتك هنا.") لا رسالة
  عامة موحّدة. ✅

**الجوال (390×844)** — بعد إصلاح علة الشريط الجانبي:
`sidebar` مرئي (كشريط علوي) و`bottomTabs` مرئي معاً وقت واحد — تحقق برمجي.
شريط تبويبات سفلي بـ6 أيقونات فقط (بلا نص)، معتّم بالكامل قبل الرفع، شارة
الملف المرفوع ظاهرة بالشريط العلوي بعد الرفع، حقول البحث تصطف عمودياً
(`flex-direction:column`) بعرض كامل، بطاقة وظيفة حقيقية تُعرض بعرض الشاشة
كاملاً دون قصّ نص. ✅

**ملاحظة فنية متكررة**: لقطة `full_page=True` واحدة للجوال أظهرت مساحة
فارغة كبيرة أسفل المحتوى الفعلي — نفس قصور تجميع لقطات Playwright الكاملة
مع عناصر `position: fixed`/`sticky` الموثّق في الجولة السابقة، وليس خللاً
حقيقياً (تحقق بالتمرير المباشر بدل الاعتماد على `full_page` وحده).

### تأكيد عدم كسر أي وظيفة قائمة
لا أخطاء console عبر كل السيناريو (تحقق عبر `page.on("console")` و
`page.on("pageerror")` طوال التشغيل — صفر أخطاء). التخزين المؤقت للنتائج،
تعطيل/تفعيل الحقول حسب توفر نتائج بحث، حد الطلبات، تحميل الملف كـ Blob —
كلها اختُبرت حياً بنجاح. لا لمس لـ `api.py`/`agent.py`/`tools/`.

### الخلاصة
كل بنود الطلب مُنفَّذة: هيكل تطبيق ثابت بجزأين بلا تمرير للصفحة، شريط
جانبي بحالات inactive/hover/active + شارة الخدمة الأهم + تعطيل كامل قبل
الرفع + عداد طلبات وشارة ملف مثبّتان أسفله، مساحتا عمل (قبل/بعد الرفع)،
منطقة نتائج تُمرَّر داخلياً فقط ببطاقات بلا حدود، حركة 150ms + صعود 8px،
استجابة للجوال بشريط تبويبات سفلي. **علة حقيقية واحدة (اختفاء حالة الرفع
كاملة على الجوال) اكتُشفت عبر اختبار Playwright فعلي لا افتراضي، وأُصلحت
قبل اعتبار المهمة مكتملة** — يؤكد قيمة التحقق البصري الفعلي بدل الاكتفاء
بمطابقة الكود للمواصفة نظرياً.

---

## إزالة "تقديماتي" + "سلسلة موجّهة" (guided chain) بين الخدمات

### الطلب
تعليقان صريحان: (1) حذف عنصر تنقل "تقديماتي" نهائياً من الواجهة (كان مطلوباً
سابقاً بـ`PROJECT_BRIEF.md` ولم يُطبَّق فعلياً على الواجهة بعد) — بلا حذف
أي أداة من `agent.py`/`tools/`، مجرد نقطة الدخول بالواجهة فقط. (2) إضافة
"سلسلة موجّهة": كل نتيجة تعرض زر "الخطوة التالية" ينقل تلقائياً + يعبّئ +
**يُطلق الطلب فوراً** بلا إعادة اختيار يدوي — بديل تسريع فوق التنقل اليدوي
لا بديل عنه (يبقى يعمل دائماً).

### علة سابقة مُكتشَفة عند بدء الجلسة: إزالة "تقديماتي" كانت منتصفة
عند فتح `frontend/index.html` وجدت: (أ) عنصر تنقل "تقديماتي" بالشريط
الجانبي كان **معلَّقاً بتعليق HTML** (`<!-- ... -->`) لا محذوفاً فعلياً —
غير مرئي في المتصفح لكن الكود ما زال هناك، ومتبقياً كاملاً في شريط
التبويبات السفلي (`bottomTabs`) وفي `paneApplications` وفي `app.js`
(`btnApplications`). (ب) **نفس علة المسارات المطلقة من جلسات سابقة تكررت
مجدداً**: `href`/`src` لثلاث عناصر أصول (أيقونة الصفحة، شعار الشريط
الجانبي، رسم الهيرو) كانت مكتوبة كمسارات Windows مطلقة كاملة
(`C:\Users\pc\Desktop\CareerPilot\frontend\assets\...`) بدل النسبية —
تحقق مباشر من محتوى الملف الفعلي بدل افتراض أن آخر حالة معروفة ما زالت
صحيحة (تماشياً مع الدرس المسجَّل من الجولات السابقة: **تحقق من الملف
الفعلي دائماً بدل الافتراض**). صححت الثلاثة لمسارات نسبية (`/assets/...`)
قبل أي عمل آخر. ✅

### حالة اختبار 57 — إزالة "تقديماتي" كاملة (لا حذف جزئي)
حذفت فعلياً (لا تعليق): عنصر `.nav-item[data-service="applications"]`
من الشريط الجانبي، `.tab-item[data-service="applications"]` من شريط
التبويبات السفلي، و`#paneApplications` بالكامل من `frontend/index.html`.
في `frontend/app.js`: أزلت `applications` من `SERVICE_ICONS` و
`EMPTY_MESSAGES`، حذفت سطر تعطيل `btnApplications` من `setServicesEnabled`
(كان سيرمي خطأ `getElementById` على `null` لولا الحذف)، وحذفت مستمع
النقر الخاص بـ`btnApplications` بالكامل. **لم ألمس** `renderApplications`
ولا `renderLogConfirm` ولا حالتي `log_application`/`get_application_status`
بدالة `renderResult` — تبقى موجودة تحسّباً (لو ظهرت نتيجة أداة كهذي ضمن
`tool_results` لأي سبب مستقبلي)، تماشياً مع التعليمة الصريحة "لا حذف أداة،
فقط نقطة الدخول بالواجهة". تحقق برمجي عبر Playwright: عدد `.nav-item` = 5
بالضبط (كان 6)، الشعار يُحمَّل بنجاح (`naturalWidth > 0`). ✅

### حالة اختبار 58 — "السلسلة الموجّهة": التصميم والتنفيذ
أضفت مبدأً واحداً يُعاد استخدامه 3 مرات: `activatePane(service)` (تبديل
الحالة النشطة + عرض/إخفاء اللوحات فوراً، بلا مسّ منطقة النتائج) تليها
مباشرة `sendMessage(message, jobContext)` بنفس الاستدعاء المتزامن — بما
أن دالة `async` تُنفَّذ فعلياً بشكل متزامن حتى أول `await` بداخلها،
فإن تبديل التنقّل + ظهور الـskeleton **يحدثان في نفس اللحظة المتزامنة
قبل أي انتظار شبكة فعلي** دون أي حيلة إضافية — تحقق منها لاحقاً برمجياً
(80ms بعد النقر، الحالة النشطة تحوّلت فعلاً وglass الـskeleton ظاهر).

- **مسميات → بحث**: `renderTitles` لم يعد يرسل "اختار X" نصياً عاماً؛ زر
  كل pill يستدعي `chainToSearch(title)` مباشرة: تفعيل لوحة "البحث"،
  تعبئة `searchTitleInput`، ثم بناء رسالة الطلب — **قرار مهم**: لو حقل
  المدينة فارغاً وقتها، ترسل الرسالة بلا مدينة (`ابحث لي عن وظائف {title}`)
  بدل افتراض مدينة افتراضية مُبرمَجة يدوياً — يتماشى مع مبدأ `CLAUDE.md`
  الجوهري (القرار للنموذج لا للكود)، فيترك للوكيل نفسه التعامل مع غياب
  المدينة (يسأل المستخدم أو يستنتجها من نص السيرة) بدل قرار "أي مدينة
  افتراضية" مكتوب يدوياً بالواجهة.
- **بحث → تقييم**: أضفت زراً داخلياً على **كل** بطاقة وظيفة
  ("قيّم التوافق مع هذي الوظيفة")، يستدعي `chainToJob("match", job, ...)`
  — تُبحث الوظيفة بالمصفوفة الحالية `latestJobs` عبر تطابق العنوان+الشركة
  (لا الفهرس الرقمي وحده، تحسّباً لعدم تطابق افتراضي لو أُعيد عرض نتيجة
  مخزَّنة قديمة بعد بحث لاحق مختلف) لتحديد القائمة المنسدلة تلقائياً على
  الوظيفة الصحيحة، ثم إطلاق طلب `evaluate_match` فوراً.
- **تقييم → تحسين/خطاب**: `renderMatch` الآن تستقبل `jobContext` (مُمرَّرة
  عبر حقل غير-API خفيف `data.__jobContext` يُرفق بالرد المخزَّن مؤقتاً قبل
  التخزين في `serviceResultCache`، فتبقى النتيجة المؤجَّلة من التبويب
  محتفظة بسياق الوظيفة حتى لو رجع المستخدم لها لاحقاً) وتعرض زرين إضافيين
  تحت البطاقة: "حسّن سيرتي لهذي الوظيفة" و"اكتب خطاب تقديم"، كلاهما يستدعي
  `chainToJob` بخدمة مختلفة ونفس كائن الوظيفة. **إضافة جانبية متسقة**: مرّرت
  `jobContext` أيضاً من أزرار التقييم/التحسين/الخطاب **اليدوية** (القوائم
  المنسدلة الأصلية) — فنتيجة تقييم مُشغَّلة يدوياً تحصل على نفس زري
  "الخطوة التالية"، لا الاستخدام عبر السلسلة فقط. ✅

### التحقق البصري: المسار الكامل المُسرَّع من طرف لطرف (Playwright)
سيناريو حي كامل رفع → مسميات → بحث → تقييم → تحسين **بلا لمس أي قائمة
منسدلة يدوياً إطلاقاً** (تحقق صريح عبر عدم استدعاء `page.select_option`
بالسكربت إطلاقاً):
1. رفع `demo_resume.pdf` — نجح.
2. الضغط على `#btnTitles` → 4 pills حقيقية (Cloud/Python/Software/Backend
   Developer). الضغط على "Backend Developer" → **خلال 80ms**: التنقل
   النشط تحوّل فعلياً لـ"search" (تحقق برمجي: `dataset.service === "search"`)
   والـskeleton ظاهر، بلا أي وقفة فارغة قبله. بعد استجابة API الحقيقية:
   `searchTitleInput.value === "Backend Developer"` بالضبط (تحقق برمجي)،
   نتائج Jooble حقيقية (Yassir, Ninja, Devsinc). العداد 2/6.
3. الضغط على "قيّم التوافق مع هذي الوظيفة" ببطاقة "Staff Backend Engineer
   (NodeJS/Go) — Yassir" → التنقل تحوّل لـ"match" خلال 80ms، `matchSelect`
   اختار تلقائياً **نفس الوظيفة بالضبط** (تحقق برمجي:
   `selectedOptions[0].textContent === "Staff Backend Engineer (NodeJS/Go) — Yassir"`)،
   تقييم حقيقي 45% (كهرمانية) مع تعليل نصي حقيقي من Gemini، وزرا
   "حسّن سيرتي"/"اكتب خطاب" ظاهران تحت النتيجة. العداد 3/6.
4. الضغط على "حسّن سيرتي لهذي الوظيفة" → التنقل تحوّل لـ"improve" خلال
   80ms، `improveSelect` اختار **نفس الوظيفة بالضبط** تلقائياً (تحقق
   برمجي مطابق)، نتيجة `improve_resume` حقيقية كاملة (بيانات Sara
   Al-Otaibi التجريبية) بصندوق مراجعة + قائمة تغييرات + زر تحميل يعمل.
   العداد 4/6.

**السياق (عنوان الوظيفة + الشركة) تحقق منه برمجياً في كل قفزة** لا بصرياً
فقط — القيمة المختارة بكل قائمة منسدلة طابقت حرفياً الوظيفة التي بدأت منها
السلسلة، عبر 3 قفزات متتالية، صفر أخطاء console طوال السيناريو
(`page.on("console")`/`page.on("pageerror")` — صفر التقاطات).

### تأكيد بقاء التنقل اليدوي يعمل بلا تغيير
لم يُحذف أو يُعطَّل أي مسار يدوي: الضغط المباشر على عناصر الشريط الجانبي
لا يزال يستدعي `selectService()` الأصلية (تعرض الحالة الفارغة أو النتيجة
المخزَّنة، بلا إطلاق طلب جديد تلقائياً) — التسريع إضافة فوق السلوك الأصلي
لا استبدال له، تماماً كما نصّ الطلب.

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`api.py`/`agent.py`/`tools/`. لا حذف لأي أداة أو منطق قرار جديد
بشأن "أي أداة تُستدعى" — كل ما أُضيف هو بناء نص طلب + تبديل عرض، تماماً
كنمط الأزرار اليدوية الأصلي. صفر أخطاء console عبر السيناريو الكامل.

### الخلاصة
"تقديماتي" أُزيلت فعلياً (لا تعليق جزئي كما كانت) من الشريط الجانبي وشريط
التبويبات ولوحتها المخصصة، مع الإبقاء الكامل على أدوات `log_application`/
`get_application_status` بالخلفية. السلسلة الموجّهة تعمل من طرف لطرف عبر
3 قفزات (مسميات→بحث→تقييم→تحسين) بلا أي تدخل يدوي، مع تحقق برمجي صريح
من صحة السياق (عنوان/شركة) بكل قفزة، وحفاظ كامل على مسار التنقل اليدوي
الأصلي. عُثر أيضاً على علتين متبقّيتين من جلسة سابقة (إزالة منتصفة + مسارات
أصول مطلقة) وأُصلحتا قبل البدء بالمهمة الجديدة.

---

## اعتماد نظام design_reference.html البصري على كامل الواجهة

### الطلب
المستخدم زوّد ملف `frontend/design_reference.html` كنظام بصري مرجعي **دقيق**
يجب اعتماده حرفياً: خطا Cairo (عناوين/عرض) + Almarai (نص أساسي)، لوحة ألوان
مطابقة لما لدينا فعلاً، نمط تنقّل جانبي بنقطة حالة نشطة ليمونية، "بطاقة
تقدّم" (progress-card) بإطار "رحلة الطلبات"، نمط "eyebrow" شارة الخطوة
("١ من ٦")، معالجة الشعار المتدرجة، بلوبة خلفية عائمة متحركة، وبطاقة رفع
متقطعة الحدود بعنقود مستندات عائم + شارة رفع متدرجة + حالة نجاح. **قيد
صريح**: عدم تغيير هيكلة التطبيق (شريط جانبي + حالة عمل واحدة نشطة)، عدم
لمس `api.py`/`agent.py`/`tools/`، والحفاظ على السلسلة الموجّهة القائمة.
المطلوب: إعادة التصميم البصري لتطابق المرجع + **مدّ نفس اللغة** لأجزاء لا
يغطيها المرجع (الخدمات الخمس الأخرى، بطاقات النتائج، شارة تقييم التوافق).

### حالة اختبار 59 — قراءة المرجع وتحليل الأصول قبل أي تعديل
قرأت `design_reference.html` كاملاً (307 سطر). لاحظت أن اللوحة اللونية فيه
مطابقة لمتغيرات `:root` الحالية بالقيمة الحرفية بلا أي فرق (`#D3A0FD`،
`#E8CFFF`، `#F7F0FD`، `#ECFF70`، إلخ) — لا حاجة لأي تغيير قيم ألوان، فقط
اعتماد الأنماط البصرية الجديدة فوقها. فحصت أيضاً `assets/logo.png` و
`assets/hero-illustration.png` بصرياً (عبر أداة Read على الصورة مباشرة، لا
افتراضاً): الشعار عبارة عن سهم/حرف G بنفسجي ثلاثي الأبعاد مع نجمة ليمونية،
يحمل هويته اللونية والشكلية بذاته بالفعل — **قرار**: عدم إضافة حاوية مربعة
متدرجة خلفه (كما بالمرجع الذي يستخدم أيقونة SVG مجردة تحتاج حاوية) لأنها
كانت ستكرر نفس المعالجة اللونية بلا داعٍ بصري حقيقي؛ عُرض الشعار مباشرة
بحجم 34px. رسم الهيرو عبارة عن توضيح ثلاثي الأبعاد لسيرة ذاتية بنسبة توافق
98% مع شارات أيقونات عائمة حولها (هدف/رسم بياني/نجوم) — وُضع أعلى منطقة
الرفع بحجم `max-height:32vh` مركزياً، بنفس موضع "عنقود الأيقونات" بالمرجع.

**اكتشاف تقني ضروري**: التحقق من `api.py` (`app.mount("/", StaticFiles(
directory="frontend"...))`) أكد أن `/assets/...` يُخدَّم من `frontend/assets/`
حصراً، لا من `assets/` بجذر المشروع — و`hero-illustration.png` لم يكن
موجوداً أصلاً داخل `frontend/assets/` (فقط نسخة SVG قديمة باسم مختلف).
نسخت الملف الفعلي لمساره الصحيح قبل أي ربط HTML، بدل الافتراض أن المسار
سيعمل لمجرد كتابته. ✅

### حالة اختبار 60 — إعادة بناء `frontend/index.html`
غيّرت رابط الخطوط لمطابقة المرجع حرفياً (`Cairo:wght@500;700;800&family=
Almarai:wght@300;400;700`). أضفت `div.bg-blob` كعنصر شقيق للشريط الجانبي
والمساحة الرئيسية (لا محصور بشاشة الرفع). أعدت هيكلة كل عنصر تنقّل بإضافة
`span.nav-left` (يجمع الأيقونة+التسمية) و`span.active-dot` منفصل، لتفادي
تعارض مع `.flagship-dot` القائمة على "تحسين السيرة" (بقيت الأخيرة ملاصقة
للتسمية، والجديدة بطرف العنصر — نمطان متمايزان بصرياً بلا تصادم). استبدلت
`.request-meter` بـ`.progress-card` كاملة (تسمية + عدّاد + نص فرعي + مسار
تقدّم متدرّج) مع الإبقاء على نفس الـ id (`counterPill`, `meterFill`) حتى
لا يحتاج app.js أي تعديل هيكلي. أعدت بناء شاشة الرفع بالكامل: صورة الهيرو،
eyebrow بصيغة "١ من ٦ — رفع السيرة الذاتية"، عنوان بتمييز أصفر مائل تحت
"رحلتك المهنية" (بنفس أسلوب `::after` بالمرجع)، ومنطقة سحب بعنقود مستندات
عائمة (`doc-chip` × 2 بحركة float مستقلة) + شارة رفع دائرية متدرجة + صف
شارات نوع الملف. طبّقت نمط "eyebrow شارة الخطوة" أيضاً على الخدمات الخمس
المتبقية — بما أن تطبيقنا غير خطي (يمكن زيارة أي خدمة بأي ترتيب عبر الشريط
الجانبي أو السلسلة الموجّهة، خلافاً لتدفق المرجع أحادي الخطوة)، استبدلت
رقم الخطوة بتسمية "الخدمة النشطة" (و"الخدمة الأهم" حصراً لتحسين السيرة،
حفاظاً على تمييزها القائم) متبوعة بالنص الوصفي الأصلي لكل خدمة، داخل نفس
حاوية "pill" البصرية. ✅

### حالة اختبار 61 — إعادة كتابة `frontend/style.css`
غيّرت `body` لخط Almarai، وأضفت قاعدة تستهدف `h1, .display, .brand-name,
.step-num, .count` لخط Cairo — بنفس توزيع الأدوار بالمرجع (عناوين/أرقام
بـCairo، نص عادي بـAlmarai). أضفت `.bg-blob` + `@keyframes drift` بنفس
قيم المرجع تقريباً (بلوبة واحدة متدرجة اللون، تتحرك 18 ثانية)، مع
`.app-shell{position:relative}` و`z-index` مرتّب (بلوبة=0، شريط جانبي=2،
مساحة عمل=1) لضمان ظهورها خلف كل شيء بأنحاء التطبيق كله لا شاشة الرفع
فقط — حذفت نظام `.ublob` الثلاثي القديم المحصور بشاشة الرفع بالكامل، عوضاً
عن الإبقاء على الاثنين معاً (تكرار بصري غير مبرر). أعدت بناء `.nav-item`
لتخطيط `justify-content:space-between` مع `.active-dot` (دائرة ليمونية 6px
بهالة بيضاء، تظهر فقط `.nav-item.active`). استبدلت `.match-score-badge`
بخلفية متدرجة حسب الفئة (`linear-gradient(150deg, ...)` بدل لون مسطّح)
وأضفت `.match-score-icon` (شارة دائرية صغيرة بزاوية الدرجة، حلقة بيضاء عبر
`box-shadow`، أيقونة صح/نجمة/سهم حسب الفئة) — تطبيق مباشر لمطلب "معالجة
أيقونة-شارة شبيهة بشارات الصح على doc-chip، لا نسبة نصية مجردة". حدّثت
متغيّر `--card-shadow` من ظل رمادي محايد لظل بنفسجي خفيف ناعم (نفس أسلوب
`0 12px 24px -10px rgba(211,160,253,.6)` بالمرجع) — تغيير في متغيّر واحد
انتشر تلقائياً عبر كل البطاقات (`job-card`, `match-card`, `review-box`,
`plain-reply`, `titles-pills`, `skeleton`, `application-card`, `error-card`)
بلا حاجة لتعديل كل قاعدة على حدة. أضفت لمسة تدرّج خفيفة على خلفية
`.review-box` (من `--purple-light` لأبيض) لنفس اللغة البصرية. ✅

### علة حقيقية اكتُشفت ومُصلحت أثناء التحقق: انكسار سطر "PDF" لثلاثة أسطر
أول لقطة شاشة لحالة الرفع أظهرت "اسحب ملف" / "PDF" / "هنا أو اضغط
لاختياره" **على ثلاثة أسطر منفصلة** بدل سطر واحد كما بالمرجع الأصلي —
افترضتُ أولاً أنها علة عرض ثنائي الاتجاه (bidi) بسبب `PDF` اللاتيني وسط
نص عربي، فحاولت توسيع حاوية `.dropzone` (480px → 560px) وتقليل الحشو —
**لم يُصلح شيئاً**. تحققت برمجياً بدل الافتراض: قِس عرض `<p>` الفعلي
(كان 141px فقط رغم أن الحاوية توفر ~500px)، ثم بعد إصلاح أول (`width:100%`
على الفقرة) أصبح العرض 502px **لكن الانكسار استمر رغم ذلك** — نفى هذا
فرضية "نقص المساحة" كلياً. قِست العرض الفعلي للنص بـ`canvas.measureText`
فتبيّن أنه 263px فقط، أقل من نصف المساحة المتاحة — يستحيل أن يكون هذا
سبب الانكسار. الفحص الحاسم: فحص `getComputedStyle` لعنصر
`<span class="accent-text">PDF</span>` المتداخل داخل `<p>` كشف أن قيمة
`display` له كانت **`block`** فعلياً! السبب الجذري: قاعدة `.dropzone span
{ ...; display:block; }` كانت مكتوبة لتنسيق سطر "الحد الأقصى 200
ميغابايت" الفرعي (`<span>` شقيق مباشر لـ`<p>`) لكن **محدد الأحفاد
العام** (`.dropzone span`) طابق أيضاً `.accent-text` المتداخل بعمق داخل
`<p>` بالخطأ — نفس نمط علة "محدد CSS بلا تخصيص كافٍ" الموثّق سابقاً بجولات
هذا المشروع (`.upload-card p` مقابل `.upload-eyebrow`). الإصلاح: تغيير
المحدد لمحدد ابن مباشر (`.dropzone > span`) بدل محدد الأحفاد، فيستثني
`.accent-text` المتداخل بينما يستمر بتنسيق السطر الفرعي المقصود بلا تغيير.
أعدت الالتقاط بعد الإصلاح — النص عاد لسطر واحد مطابق تماماً للمرجع. ✅

### التحقق البصري (Playwright، 1440×900 + جوال 390×844)
- **الحالة الفارغة**: خطوط Cairo/Almarai محمّلة فعلياً (تحقق برمجي عبر
  `getComputedStyle` — `body`→Almarai، `h1`→Cairo)، الشعار ورسم الهيرو
  كلاهما محمّلان بنجاح (`naturalWidth > 0`)، البلوبة الخلفية ظاهرة خلف كل
  المحتوى (سطح المكتب والجوال معاً)، eyebrow شارة الخطوة "١ من ٦"، عنوان
  بتمييز أصفر تحت "رحلتك المهنية"، منطقة سحب بعنقود مستندات عائمة + شارة
  رفع متدرجة + شارتي نوع ملف — نص السحب على سطر واحد صحيح بعد إصلاح العلة
  أعلاه. ✅
- **حالة النجاح بعد الرفع**: شارة الملف بالشريط الجانبي تظهر
  `demo_resume.pdf`، عنصر تنقّل "مسميات وظيفية" نشط فعلياً (نقطة ليمونية
  بطرف العنصر + خلفية بنفسجية فاتحة + خط عريض)، نقطة "الخدمة الأهم"
  الثابتة على "تحسين السيرة" ظاهرة بشكل متمايز عن نقطة الحالة النشطة. ✅
- **نتيجة بحث حية**: بطاقات وظائف حقيقية (Yassir, Devsinc, CEQUENS) بظل
  بنفسجي ناعم واضح، عداد الطلبات 1/6 بشريط تقدّم متدرّج (بنفسجي→ليموني). ✅
- **نتيجة تقييم توافق حية (عبر السلسلة الموجّهة)**: درجة 45% بخلفية متدرجة
  كهرمانية، **شارة أيقونة دائرية صغيرة (نجمة) أعلى يسار الدائرة بحلقة
  بيضاء** — تطابق مباشر لنمط `doc-chip .badge` بالمرجع، ليست نسبة نصية
  مجردة كما كانت سابقاً. زرا "حسّن سيرتي"/"اكتب خطاب تقديم" ظاهران أسفل
  النتيجة، السياق (Staff Backend Engineer — Yassir) محفوظ صحيحاً بالقائمة
  المنسدلة. عداد الطلبات 2/6. ✅
- **الجوال (390px)**: نفس نص السحب على سطر واحد صحيح، البلوبة ظاهرة أعلى
  الشاشة، شريط علوي رفيع بالشعار، شريط تبويبات سفلي بالأيقونات — صفر أخطاء
  console. ✅

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`api.py`/`agent.py`/`tools/`. الهيكلة المعمارية (شريط جانبي +
حالة عمل واحدة نشطة، لا تمرير للصفحة) بلا تغيير. السلسلة الموجّهة (مسميات
→بحث→تقييم→تحسين) اختُبرت حياً ضمن سيناريو التحقق ونجحت بلا أي تعديل على
منطقها. صفر أخطاء console عبر كل السيناريوهات (سطح المكتب + الجوال).
تعديلا `app.js` الوحيدان: نص `updateMeter()` (حذف بادئة "الطلبات" المكرَّرة
مع تسمية progress-card الجديدة) وإضافة شارة الأيقونة داخل `renderMatch()`
— كلاهما عرضي بحت، بلا أي منطق قرار جديد.

### الخلاصة
اعتُمد نظام `design_reference.html` البصري بالكامل: الخطوط، لوحة الألوان
(كانت مطابقة أصلاً)، نمط التنقّل بنقطة الحالة النشطة، بطاقة التقدّم، شارة
eyebrow (مع تكييف نصّها لطبيعة تطبيقنا غير الخطية)، معالجة الشعار (بقرار
واعٍ بعدم إضافة حاوية متدرجة زائدة بعد تحقق بصري)، البلوبة الخلفية المتحركة
(مُمتدة لكامل التطبيق كما طُلب صراحة لا شاشة الرفع فقط)، وبطاقة الرفع
الكاملة بعنقود المستندات. اللغة البصرية امتدّت للخدمات الخمس الأخرى وبطاقات
النتائج (ظل بنفسجي موحّد عبر متغيّر واحد، شارة تقييم متدرجة بأيقونة). عُثر
على علة حقيقية واحدة أثناء التحقق (انكسار نص "PDF" لثلاثة أسطر بسبب محدد
CSS غير مخصّص كفاية يطابق عنصراً متداخلاً بالخطأ) وأُصلحت بتشخيص برمجي
تدريجي (قياس عرض فعلي → قياس نص فعلي → فحص computed style) بدل التخمين
البصري، قبل اعتبار المهمة مكتملة.

---

## إصلاح تخطيط قسم الهيرو — عمودان بدل تكديس رأسي يقصّ الرسم

### الطلب
رسم الهيرو كان يظهر مقصوصاً وموضوعاً بشكل غير موفَّق أعلى العنوان. طُلب
إعادة تصميمه كتقسيم أفقي حقيقي داخل مساحة العمل (منفصل عن الشريط الجانبي
الذي يبقى كما هو): **يمين** (~55%): eyebrow + عنوان + عبارة فرعية + بطاقة
الرفع كاملة العرض. **يسار** (~45%): رسم الهيرو **كاملاً غير مقصوص**، بحجم
كبير (380px+ عرضاً كحد أدنى)، متمركز رأسياً مقابل كتلة النص، بحركة طفو
ناعمة (translateY، ~4 ثوانٍ، تحترم `prefers-reduced-motion`)، مع إبقاء
البلوبة الخلفية لكن بإعادة تموضع كهالة خلف الرسم مباشرة. تحت 1100px:
تكديس رأسي — الرسم أولاً (مركزياً، حجم معتدل) ثم العمود النصي، **بلا أي
قصّ في أي نقطة توقف**.

### التشخيص قبل التنفيذ: لماذا كان الرسم يُقصّ فعلياً؟
فحصت الكود القائم قبل أي تعديل بدل افتراض السبب: `.upload-state` كانت
`display:flex; flex-direction:column; ...; overflow:hidden` بارتفاع
مُقيَّد ضمن `100vh` ثابت (`.workspace{height:100vh; overflow:hidden}`).
الرسم + eyebrow + عنوان + عبارة فرعية + بطاقة الرفع مكدَّسة رأسياً بعمود
واحد كانت تتجاوز الارتفاع المتاح على شاشات متوسطة الارتفاع، و`overflow:
hidden` كان يقصّ الفائض **صامتاً بلا تمرير ولا تصغير سليم** — هذا السبب
الجذري الحقيقي وراء "القصّ"، لا خطأ بمقاسات الصورة نفسها. القرار: تحويل
لعمودين أفقيين يقلّل الارتفاع الكلي المطلوب بشكل جوهري (يحدّده أطول عمود
فقط لا مجموع كل العناصر رأسياً)، بدل مجرد تصغير حجم الصورة كحل ترقيعي.

### حالة اختبار 62 — إعادة هيكلة `frontend/index.html`
غلّفت محتوى `#uploadState` بـ`div.upload-hero-grid` يحوي عمودين:
`div.upload-hero-text` (eyebrow + h1 + عبارة فرعية + `label.dropzone`
كاملة — نفس المحتوى الداخلي للبطاقة بلا أي تغيير، فقط أُعيد تغليفها) و
`div.upload-hero-visual` (صورة رسم الهيرو فقط). بما أن الصفحة `dir="rtl"`،
العمود الأول بترتيب DOM (النص) يظهر تلقائياً يميناً والثاني (الرسم) يساراً
بلا حاجة لأي قاعدة `order` إضافية — نفس مبدأ تموضع الشريط الجانبي القائم
أصلاً. ✅

### حالة اختبار 63 — تحديث `frontend/style.css`
`.upload-hero-grid{display:flex; align-items:center; gap:3.5rem}` (المحاذاة
الرأسية المركزية تتحقق تلقائياً عبر `align-items:center` على مستوى الصف،
لا حساب بكسل يدوي). `.upload-illustration` أصبحت `width:100%;
min-width:380px; max-width:480px; height:auto` (بلا أي `max-height`
يقيّد الطول كما بالنسخة السابقة) + `@keyframes illustration-float`
(دورة 4 ثوانٍ، `translateY(-12px)` بمنتصف الدورة) داخل استعلام
`@media (prefers-reduced-motion:no-preference)` فقط. غيّرت `.upload-state`
من `overflow:hidden` إلى `overflow-y:auto; overflow-x:hidden` احتياطاً —
حتى لو تجاوز المحتوى الارتفاع مستقبلاً (مثلاً بعرض جوال بارتفاع قصير جداً)
يُمرَّر بدل أن يُقصّ صامتاً كما حدث سابقاً. أعدت تموضع `.bg-blob` (كانت
`top:-160px; right:20%`) إلى `left:2%; top:50%; margin-top:-220px` لتصبح
هالة خلف عمود الرسم تحديداً (يسار مساحة العمل) بدل موضع عام أعلى يمين لا
علاقة له بالتخطيط الجديد؛ استخدمت `margin-top` سالب للتمركز الرأسي بدل
`transform:translateY(-50%)` عمداً — الأخير كان سيتصادم مع تحريك `drift`
القائم الذي يضبط `transform` مباشرة بحركته، فيُفقِد الإزاحة المركزية عند
كل دورة حركة. أضفت استعلام `@media (max-width:1100px)` جديد (منفصل عن
`900px` القائم لانهيار الشريط الجانبي): `flex-direction:column-reverse`
(الرسم يظهر أولاً بصرياً رغم أنه ثانياً بترتيب DOM، بلا حاجة لتغيير الترتيب
الدلالي)، محاذاة نص مركزية، وحجم رسم معتدل (`min(320px,80%)`). ✅

### علة حقيقية اكتُشفت ومُصلحت أثناء التحقق: فيض الرسم خارج حدود الشاشة يساراً
أول قياس `getBoundingClientRect` لعمود الرسم عند 1440px أظهر `left:
-21.78` — أي أن جزءاً من الرسم كان فعلياً **خارج حدود نافذة المتصفح
تماماً** (لا قصّاً بواسطة overflow هذي المرة، بل تجاوزاً فعلياً لحافة
العرض). قِست الحاويات المتداخلة برمجياً بدل التخمين: `upload-hero-grid`
= 1112px (صحيح)، `upload-hero-text` = 611.6px (=55% بالضبط)، لكن
`upload-hero-visual` كانت 500.39px (=45% بالضبط) **بموضع x سالب** —
اتضح أن 55%+45%+الفجوة الأفقية (`gap:3.5rem`=56px) يتجاوز حسابياً 100%
من عرض الحاوية، لأن `flex:0 0 55%` و`flex:0 0 45%` يضبطان `flex-shrink:0`
صراحة (الرقم الثاني بمختصر flex) — يمنع العمودين من الانكماش الطفيف
اللازم لاستيعاب الفجوة، فيفيض المجموع خارج الحاوية. الإصلاح: تغيير كلا
القاعدتين لـ`flex:0 1 55%`/`flex:0 1 45%` (`flex-shrink:1` بدل 0) مع
الإبقاء على `max-width` كسقف — أعدت القياس فوراً: `upload-hero-visual`
أصبحت تبدأ عند `x:24` بالضبط (الحافة الصحيحة لمنطقة المحتوى)، بلا أي فيض.
هذا نمط علة مألوف بمشروعنا (محدد/قيمة CSS غير مقصودة تتضح فقط بالقياس
الفعلي لا بالمظهر البصري وحده). ✅

### التحقق البصري (Playwright، 1440px و1024px)
- **1440px**: عمودان أفقيان واضحان — النص والرفع يميناً (eyebrow، عنوان
  بتمييز أصفر، عبارة فرعية، بطاقة رفع كاملة العرض)، الرسم يساراً **كاملاً
  غير مقصوص** أمام هالة البلوبة البنفسجية مباشرة خلفه، متمركز رأسياً مقابل
  كتلة العنوان/العبارة الفرعية تقريباً. تحقق برمجي: `getBoundingClientRect`
  للرسم — `left:24, right:499.2` (كلاهما داخل حدود `1440px` تماماً، بلا
  فيض يميناً أو يساراً). ✅
- **1024px** (تحت حد الـ1100px): تكديس رأسي — الرسم أولاً بصرياً (مركزياً،
  عرض ~320px حجم معتدل كما طُلب)، ثم العمود النصي أسفله بمحاذاة مركزية،
  بطاقة الرفع تتوسط بعرض أقصى محدود. تحقق برمجي مطابق: الرسم بالكامل داخل
  حدود `1024px` (`left:212, right:532`)، بلا أي قصّ. ✅
- **صفر أخطاء console** عبر كلا القياسين (تحقق عبر `page.on("console")`/
  `page.on("pageerror")`). ✅
- **مقارنة مع اللقطة السابقة المكسورة**: النسخة القديمة (قبل هذي الجولة)
  كانت تُظهر الرسم مكدَّساً أعلى العنوان بارتفاع مُقيَّد (`max-height:32vh`)
  ضمن عمود واحد `overflow:hidden` — أحياناً يُقصّ فعلياً لو تجاوز المحتوى
  الارتفاع المتاح. اللقطتان الجديدتان تؤكدان زوال هذا القيد كلياً: لا
  `max-height` على الرسم، لا `overflow:hidden` على الحاوية الأب.

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`api.py`/`agent.py`/`tools/`. الشريط الجانبي بلا أي تغيير. منطق
رفع الملف (`handleUpload`, `dropzone`, `fileInput`) بلا أي تعديل — فقط
غُلِّف بصرياً بحاوية عمود جديدة، كل الـ id الأصلية (`dropzone`, `fileInput`,
`uploadError`) بقيت كما هي. لا تعديل على `app.js` إطلاقاً هذي الجولة (كل
الإصلاح كان HTML/CSS بحتاً).

### الخلاصة
قسم الهيرو أصبح تقسيماً أفقياً حقيقياً بعمودين (نص+رفع يميناً 55%، رسم
يساراً 45%) بدل التكديس الرأسي الذي كان يسبب القصّ الفعلي. الرسم يظهر
الآن كاملاً غير مقصوص عند 1440px و1024px معاً (تحقق برمجي صريح بحدود
`getBoundingClientRect`، لا افتراضاً بصرياً)، بحركة طفو ناعمة تحترم تفضيل
تقليل الحركة، وهالة بلوبة خلفية مُعاد تموضعها خلفه تحديداً. عُثر على علتين
حقيقيتين متتاليتين أثناء التحقق (تقييد ارتفاع يقصّ صامتاً، ثم فيض أفقي
خارج حدود الشاشة بسبب `flex-shrink:0` مع gap) وأُصلحتا كلتاهما بتشخيص
برمجي دقيق (قياس مستطيلات فعلية) قبل اعتبار المهمة مكتملة.

---

## توسيط الرسم داخل البلوبة + معايَنة لون الملصق الأصفر فعلياً من الصورة

### الطلب
إصلاحان: (1) رسم الهيرو غير متمركز فعلياً داخل دائرة البلوبة البنفسجية
خلفه (أسفل ويمين/يسار مركزها الفعلي) — يحتاج توسيطاً دقيقاً أفقياً ورأسياً.
(2) معايَنة اللون الأصفر/الليموني الدقيق من داخل صورة
`assets/hero-illustration.png` نفسها (ملصق أصفر صغير + تفاصيل ثانوية) عبر
سكربت فعلي (Python/Pillow) يقرأ البكسلات ويطبع القيمة السداسية عشرية —
**لا تخمين بصري** — وتطبيقها حصراً على الخط التحتي لعنوان الهيرو، دون
المساس بـ`--accent` العام (المستخدم بالأزرار/الشارات/شريط التقدّم).

### حالة اختبار 64 — تحديد الملصق الأصفر ومعايَنته برمجياً
فحصت `frontend/assets/hero-illustration.png` بصرياً أولاً (أداة Read على
الصورة) لتحديد موقع "الملصق الأصفر" المقصود — تبيّن أنه شارة/إغلاق صغير
أصفر على الحقيبة البنفسجية أسفل يسار الرسم (لا عنصر "sticky note" منفصل
بالمعنى الحرفي، لكنه العنصر الأصفر الوحيد المميّز بالصورة). كتبت سكربت
Python مؤقت (Pillow) يفتح الصورة، يمسح صندوقاً محدداً حول ذلك العنصر،
**يُصفّي البكسلات** بشرط لوني (`r>210، g>190، b<180، b<g`) لاستبعاد بكسلات
الحقيقة البنفسجية المحيطة والخط الغامق المحيط بالشارة (بدل أخذ متوسط
صندوق خام يخلط الألوان)، ثم يحسب المتوسط والوسيط. النتيجتان على عيّنتين
مختلفتي الحجم للمنطقة نفسها تطابقتا تقريباً: **#F9F37A** و**#F8F179**
(فرق ضئيل ضمن هامش الضجيج الطبيعي لتدرّج الإضاءة على السطح). اخترت
**#F8F179** كالقيمة النهائية المُعتمدة (العيّنة الأكبر والأكثر استقراراً).
**المقارنة مع `--accent` الحالي**: `#ECFF70` = RGB(236,255,112) — أخضر-
ليموني (G أعلى من R بوضوح)، بينما اللون المُعايَن `#F8F179` = RGB(248,
241,121) — أصفر ذهبي أدفأ (R أعلى من G، وB أعلى قليلاً أيضاً). **الفرق
حقيقي وملحوظ بصرياً، لا مجرد اختلاف تقني ضئيل** — تحقّق ذلك لاحقاً بمقارنة
لقطتين مقصوصتين (الخط التحتي الجديد مقابل نقطة "الخدمة الأهم" اللي بقيت
`--accent` الأصلي) جنباً لجنب. ✅

### حالة اختبار 65 — تطبيق اللون محلياً فقط + توسيط الرسم
غيّرت `background: var(--accent)` إلى `background: #F8F179` **حصراً**
داخل `.upload-title .mark::after` (الخط التحتي وحده) — لم يُمَسّ متغيّر
`--accent` العام إطلاقاً، وتحقّقت لاحقاً أن الأزرار (`.btn-lime`)، شريط
تقدّم الطلبات (`.progress-fill`)، ونقطة "الخدمة الأهم" (`.flagship-dot`)
كلها ما زالت تستخدم `--accent` الأصلي #ECFF70 بلا تغيير.

للتوسيط: قِست `getBoundingClientRect` لكل من `.upload-illustration`
و`.bg-blob` فعلياً بدل التخمين — مركز الرسم كان (261.6, 438.2)، مركز
البلوبة (248.5, 450.4) — فرق (13.1-, 12.1+) تقريباً، يطابق وصف المستخدم
"أسفل ويمين/يسار مركزها الفعلي" حرفياً. أضفت `margin: 12px 0 0 -13px`
على `.upload-illustration` (لا `transform`، متعمَّد: `transform` محجوزة
بالكامل لحركة الطفو `illustration-float` القائمة، ولا ينبغي أن تتصادما
على نفس الخاصية). ✅

### علة حقيقية اكتُشفت أثناء التحقق: margin حقّق نصف الإزاحة المطلوبة فقط
أعدت القياس بعد إضافة `margin:12px 0 0 -13px` متوقعاً توسيطاً شبه تام —
لكن مركز الرسم تحرّك لـ(255.1, 444.4) فقط، أي **نصف** المسافة المطلوبة
تقريباً (6.6px أفقياً بدل 13.1px، 5.9px رأسياً بدل 12.1px) لا الإزاحة
الكاملة. السبب: `.upload-hero-visual` الأب يستخدم `justify-content:
center`؛ عندما تُضاف margin غير متماثلة (يسار سالب فقط) لعنصر flex وحيد
داخل حاوية بمحاذاة مركزية، يعيد المحرّك توزيع نصف مساحة الـmargin
الإضافية كفراغ حر على الجانبين لإبقاء "الصندوق الخارجي" (content+margin)
متمركزاً هندسياً — فتُلغي خوارزمية التوسيط تلقائياً نصف الإزاحة المقصودة.
هذا نمط سلوك CSS خفي غير بديهي، اكتُشف فقط بالقياس البرمجي الفعلي بعد
التطبيق لا بالتخمين. الإصلاح: مضاعفة القيم (`margin: 24px 0 0 -26px`)
لتعويض هذا التخفيف التلقائي بمقدار النصف. أعدت القياس فوراً: مركز الرسم
(248.6, 450.4) مقابل مركز البلوبة (248.5, 450.3) — **فرق 0.1px فقط**،
توسيط شبه تام. ✅

### التحقق البصري (Playwright، 1440px)
- **التوسيط**: تحقق برمجي نهائي `getBoundingClientRect` يؤكد تطابق مركزي
  الرسم والبلوبة بفارق أقل من 1px. لقطة الشاشة تؤكد بصرياً أن الرسم يجلس
  متوازناً داخل الدائرة البنفسجية بلا انزياح ملحوظ لأي جهة. ✅
- **اللون**: `getComputedStyle` لـ`::after` أكّد `rgb(248, 241, 121)` فعلياً
  (=#F8F179، مطابق تماماً للقيمة المُعايَنة من الصورة). لقطة مقصوصة للخط
  التحتي مقارنةً بلقطة مقصوصة لنقطة "الخدمة الأهم" (لا تزال `--accent`
  الأصلي) تؤكدان بصرياً فرقاً حقيقياً بين اللونين (الخط التحتي أدفأ وأصفر
  أكثر تشبّعاً، نقطة الخدمة أميل للأخضر الفاتح الشاحب). ✅
- **1024px**: التوسيط والحركة لا يزالان سليمين بصرياً بعد التكديس الرأسي
  (لم يكن مطلوباً توسيطاً منفصلاً لهذا العرض تحديداً بالطلب، لكن تحقّقت
  أن التعديل لم يُسبّب أي خلل مرئي هناك). ✅
- **صفر أخطاء console** عبر كل السيناريوهات. ✅

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`api.py`/`agent.py`/`tools/`/`app.js`. لا تغيير على `--accent`
العام ولا أي عنصر آخر غير الخط التحتي والرسم. حركة الطفو، منطق الرفع،
والتخطيط العام بقيت جميعها بلا تغيير جوهري.

### الخلاصة
الرسم أصبح متمركزاً فعلياً داخل هالة البلوبة (فرق مركز أقل من 1px، مؤكَّد
برمجياً) بعد اكتشاف وتصحيح سلوك CSS غير بديهي (تخفيف margin التلقائي عبر
`justify-content:center`). اللون الأصفر الدقيق **#F8F179** عُوين فعلياً
من ملصق الحقيبة الأصفر داخل `hero-illustration.png` بسكربت Pillow حقيقي
(لا تخمين)، وطُبِّق حصراً على الخط التحتي لعنوان الهيرو — مختلف بوضوح عن
`--accent` #ECFF70 الذي بقي بلا تغيير بكل مكان آخر بالتطبيق (أزرار، شارات،
شريط التقدّم، نقطة الخدمة الأهم).

---

## إصلاح جذري لتموضع/تحجيم رسم الهيرو المتجاوب — يفشل بعروض شائعة لم تُختبر

### الطلب
لقطة فعلية بعرض ~1440px أظهرت الرسم فائضاً خارج الحافة اليسرى للدائرة —
الإصلاح السابق كان مضبوطاً يدوياً (margin مضاعف بالبكسل) لعرض 1440 فقط
تحديداً ولم يصمد بأي عرض آخر. **السبب الجذري المطلوب تصحيحه**: الدائرة
والرسم كانا بوحدات قياس مختلفة تماماً ومتحركين باستقلالية (px ثابت
لدائرة `.bg-blob` بموضع % من `.app-shell`، مقابل % من عمود flex مختلف
كلياً للرسم) — ينحرفان عن بعض حتماً بأي عرض غير ذلك المُعاير يدوياً عليه.
**الإصلاح المطلوب صراحة**: تحجيم الرسم كنسبة من أبعاد الدائرة نفسها
(مثلاً 70% من عرض حاوية الدائرة)، كلاهما داخل والد واحد `position:
relative`، ليتحركا كوحدة واحدة بأي عرض. اختبار حي على 9 عروض شاشة كاملة
(1920 حتى 375px)، لا عرضين فقط كسابقاً.

### حالة اختبار 66 — إعادة هيكلة الدائرة والرسم كوحدة واحدة فعلية
أضفت `div.upload-hero-circle` غلافاً جديداً بين `.upload-hero-visual`
والصورة (`frontend/index.html`) — هذا العنصر الجديد هو الوالد
`position:relative` المشترك المطلوب. بـ`frontend/style.css`:
- `.upload-hero-circle`: `width: clamp(220px, 30vw, 460px); aspect-
  ratio: 1; border-radius: 50%;` — دالة `clamp()` مرتبطة بعرض العرض
  (`vw`) تضمن تحجيماً سلساً متصلاً عبر كل العروض بدل قفزات مفاجئة بين
  نقاط توقف منفصلة، و`aspect-ratio:1` يضمن دائرة مثالية دائماً بلا
  حاجة لحساب `height` يدوياً منفصل عن `width` (كان `.bg-blob` القديم
  440×440px **ثابتين** بلا أي علاقة بعرض الشاشة — جزء من العلة).
- `.upload-illustration`: تحوّل من علاقة px/% منفصلة عن الدائرة، لـ
  `position:absolute; top:50%; left:50%; width:70%;
  transform:translate(-50%,-50%)` — العرض الآن نسبة **من حاوية الدائرة
  المباشرة** (`.upload-hero-circle`، أقرب والد `position:relative`)
  بحكم قواعد CSS القياسية لتحديد "الكتلة الاحتوائية" لعنصر `absolute`،
  فيتحرك الاثنان معاً حتماً بأي عرض شاشة دون أي كود إضافي.
- حركة الطفو (`illustration-float`) أُعيد صياغتها لتدمج التمركز
  (`translate(-50%,-50%)`) مع تذبذب `translateY` **بكل إطار من إطارات
  keyframes** بدل تركهما يتصادمان على نفس خاصية `transform` (نفس الدرس
  من الجولة السابقة، مُطبَّق هنا بصيغة transform لا margin هذي المرة). ✅

### حالة اختبار 67 — فصل `.bg-blob` العامة عن الدائرة المخصصة للرسم
`.bg-blob` (الزخرفة العامة على مستوى التطبيق كله) كانت السبب الجذري
لمحاولة "مطاردة" موضع الرسم يدوياً بالجولة السابقة، لأنها كانت مربوطة
بموضعه تحديداً. أُعيدت لموضع عام محايد (`top:-140px; right:24%`) غير
مرتبط بالرسم إطلاقاً، بشفافية أخفض (`opacity:0.35` بدل 0.5) لتفادي أي
تراكب بصري مزدوج مع `.upload-hero-circle` الجديدة المكتفية ذاتياً. هذا
يفصل بوضوح بين مسؤوليتين: زخرفة محيطية عامة site-wide (`.bg-blob`، بلا
علاقة بأي محتوى محدد)، وهالة الرسم المحلية المكتفية بذاتها (`.upload-
hero-circle`، تتحرك دوماً مع الرسم لأنها نفس والده المباشر). ✅

### حالة اختبار 68 — تحديث استعلام `@media (max-width:1100px)`
أزلت القواعد القديمة الخاصة بـ`.upload-illustration` (`min-width:0;
width:min(320px,80%)`) التي لم تعد ذات معنى بعد التحول لنظام النسب
المئوية النسبي، واستبدلتها بتصغير سقف `.upload-hero-circle` نفسها
(`clamp(200px,40vw,300px)`) + `margin:0 auto` للتمركز الأفقي بعد تحوّل
`.upload-hero-visual` لعرض 100% في وضع التكديس. الرسم الداخلي يتبع
تلقائياً بلا أي قاعدة إضافية بفضل بنية "النسبة من الوالد". ✅

### التحقق البصري والبرمجي (Playwright) — 9 عروض شاشة كاملة

| العرض | الوصف | قبل الإصلاح | بعد الإصلاح |
|---|---|---|---|
| 1920px | سطح مكتب كبير | لم يُختبر سابقاً | ✅ محتوى بالكامل، توسيط أفقي تام |
| 1440px | العرض المُبلَّغ بالمشكلة | ❌ فائض فعلي خارج حافة الدائرة اليسرى | ✅ محتوى بالكامل، توسيط أفقي تام |
| 1366px | أشيع دقة لابتوب | لم يُختبر سابقاً إطلاقاً | ✅ محتوى بالكامل، توسيط أفقي تام |
| 1280px | سطح مكتب متوسط | لم يُختبر سابقاً | ✅ محتوى بالكامل، توسيط أفقي تام |
| 1024px | تابلت أفقي | ✅ كان يعمل مصادفة (قريب من 1440 المُعاير عليه) | ✅ محتوى بالكامل، توسيط أفقي تام |
| 768px | تابلت رأسي | لم يُختبر سابقاً؛ نقطة انهيار للتكديس | ✅ تكديس نظيف، دائرة+رسم كوحدة مركزية واحدة |
| 428px | آيفون Pro Max | لم يُختبر سابقاً | ✅ تكديس نظيف، هوامش متماثلة الجانبين |
| 390px | آيفون قياسي | ✅ كان يعمل (نفس نمط 1024 تقريباً) | ✅ تكديس نظيف، هوامش متماثلة الجانبين |
| 375px | آيفون SE / أصغر | لم يُختبر سابقاً | ✅ تكديس نظيف، هوامش متماثلة الجانبين |

تحقق برمجي دقيق لكل عرض (لا افتراض بصري) عبر `getBoundingClientRect`
لكل من `.upload-hero-circle` و`.upload-illustration`: **الاحتواء الكامل**
(حواف الرسم الأربع داخل حواف الدائرة بهامش خطأ ≤1px) = `true` في كل
العروض التسعة بلا استثناء. **البقاء ضمن نافذة العرض** (لا فيض خارج
`viewport`) = `true` في كل العروض التسعة. **الانحراف الأفقي عن مركز
الدائرة** (`center_delta.dx`) = **0.0px بالضبط** في كل عرض — توسيط أفقي
مثالي، لا تقريبي. الانحراف الرأسي الملحوظ (~9.5-10px) في كل اللقطات
سببه معروف ومقصود: حركة الطفو (`illustration-float`) كانت في منتصف
دورتها وقت التقاط اللقطة (`translateY(-10px)` بمنتصف الدورة) — ظاهرة
حركة نشطة صحيحة، لا علة توسيط. **صفر أخطاء console** عبر كل العروض
التسعة (`page.on("console")`/`page.on("pageerror")`).

**تأكيد نقطة انهيار التكديس**: عند 768px الرسم والدائرة يتكدّسان أعلى
النص كوحدة واحدة مركزية (لا تكديس منفصل لكل جزء)، بهامشين متماثلين
يمين/يسار — يطابق طلب "consistent margins on both sides, no asymmetric
positioning" حرفياً، ومؤكَّد بصرياً عبر اللقطة الفعلية لا افتراضاً.

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`api.py`/`agent.py`/`tools/`/`app.js`. منطق الرفع (`dropzone`,
`fileInput`) بلا أي تغيير. اللون الأصفر المُعايَن `#F8F179` من الجولة
السابقة بقي كما هو على الخط التحتي، لم يتأثر بهذا الإصلاح.

### الخلاصة
الجذر الحقيقي للعلة (وحدتا قياس مختلفتان لعنصرين مفترض ارتباطهما بصرياً،
يتحركان باستقلالية) أُصلح بنيوياً لا ترقيعياً — الدائرة والرسم أصبحا
عنصرين بنفس الوالد المباشر `position:relative`، بعلاقة نسبة مئوية حقيقية
(70% من عرض الدائرة) بدل رقمي px منفصلين. اختبار حي فعلي (لا افتراضي) على
9 عروض شاشة كاملة من 1920 حتى 375px يؤكد: احتواء تام، توسيط أفقي مثالي
(0.0px انحراف)، صفر أخطاء console، ونقطة انهيار تكديس نظيفة عند 768px —
بما في ذلك 5 عروض (1920، 1366، 1280، 768، 428، 375) لم تُختبر إطلاقاً
بالجولة السابقة، واتضح أن أحدها (1440، العرض المُبلَّغ) كان فعلاً مكسوراً
رغم اجتياز الاختبار السابق على عرضين مختلفين فقط — درس مباشر في خطورة
الاختبار الجزئي لتخطيط متجاوب.

---

## تخفيض حد الطلبات لكل جلسة من 6 إلى 1 (اختبار/عرض تجريبي)

### الطلب
تغيير `MAX_REQUESTS_PER_SESSION` في `api.py` من 6 إلى 1، وتحديث أي نص
بالواجهة (`frontend/`) يذكر الرقم القديم "6" ليصبح "1"، مع الإبقاء على
نفس رسالة الرفض 429 المستخدمة حالياً (فقط الرقم يتغيّر تلقائياً).

### حالة اختبار 69 — تنفيذ التغيير
`api.py` سطر 18: `MAX_REQUESTS_PER_SESSION = 6` → `= 1`. رسالة الرفض 429
(سطر 84-88) تُبنى أصلاً بـ f-string يُدرِج `{MAX_REQUESTS_PER_SESSION}`
ديناميكياً، فلا حاجة لتعديل نصها — ستعرض "1" تلقائياً بمجرد تغيير المتغيّر،
محققةً شرط "نفس الرسالة" حرفياً.

بالواجهة: `frontend/app.js` سطر 21 (`let requestLimit = 6;` → `= 1;`) —
ضروري لتفادي ظهور "0/6" لحظياً عند تحميل الصفحة قبل أول استدعاء API (نفس
المتغيّر يُستخدم لعرض العدّاد الابتدائي قبل أي رد من الخادم). رسالتا حد
الطلبات بـ`app.js` (سطر 297 و327) تُبنى ديناميكياً أيضاً بنفس نمط الـ
f-string (`` `...(${requestLimit} طلبات).` ``) فلا حاجة لتعديل نصهما.

`frontend/index.html`: تحديث نصين ثابتين لا تلمسهما الجافاسكربت
(`counterPill`/`progress-sub` الأوليان قبل أول تفاعل): `0/6` → `0/1`،
و"أكمل 6 طلبات لفتح تقرير أداء سيرتك الذاتية" → "أكمل 1 طلبات...". **لم
يُلمَس** `frontend/design_reference.html` عمداً — ملف مرجع تصميم ثابت
سلّمه المستخدم سابقاً، ليس جزءاً من الواجهة الحية المُخدَّمة فعلياً (غير
مرتبط بـ`index.html`)، فتحديثه بالتزامن مع كل تعديل مستقبلي غير مبرَّر —
يبقى لقطة أصلية كما سُلِّمت.

### حالة اختبار 70 — تحقق حي عبر API مباشرة
شغّلت `careerpilot-api` واختبرت تسلسلاً كاملاً بجلسة واحدة (`curl` مباشرة
مع ملفات JSON مؤقتة لتفادي مشاكل ترميز العربية بعلامات اقتباس bash):
1. رفع `data/demo_resume.pdf` — نجح.
2. طلب أول (`suggest_job_titles`) — **نجح فعلياً** (`HTTP 200`)، رد Gemini
   حقيقي بـ5 مسميات وظيفية، `"request_count":1,"request_limit":1"` في
   جسم الرد.
3. طلب ثانٍ بنفس الجلسة (`search_jobs`) — **رُفض فعلياً** (`HTTP 429`)،
   بنفس صيغة رسالة الرفض المستخدمة سابقاً حرفياً:
   `{"error":"وصلتِ للحد الأقصى من الطلبات لهذي الجلسة (1 طلبات)."}`
   — فقط الرقم تغيّر من 6 إلى 1 تلقائياً كما هو متوقع، النص والصياغة
   بلا تغيير. ✅

### حالة اختبار 71 — تحقق حي عبر الواجهة (Playwright)
رفعت السيرة عبر المتصفح فعلياً: العدّاد الابتدائي عرض `0/1` بالضبط (تحقق
نصي مباشر، لا افتراض)، وبعد نجاح أول طلب (`اقترح لي مسميات`) تحوّل العدّاد
لـ`1/1`. محاولة تشغيل خدمة ثانية أظهرت أن الشريط الجانبي أصبح **معطَّلاً
بالكامل فعلياً** (`pointer-events` محجوبة) — سلوك صحيح متوقَّع (`setServicesEnabled(false)`
يُستدعى تلقائياً عند بلوغ الحد)، لا علة. ✅

### تأكيد عدم كسر أي وظيفة قائمة
لا لمس لـ`agent.py`/`tools/`. لا تغيير على منطق القرار أو تدفق الوكيل —
فقط قيمة عددية واحدة بـ`api.py` ونصان ثابتان بـ`index.html`.

### الخلاصة
حد الطلبات أصبح 1 لكل جلسة فعلياً، مؤكَّد حياً عبر API مباشرة (طلب أول
ناجح 200، طلب ثانٍ مرفوض 429 بنفس نص الرسالة القائم) وعبر الواجهة (عدّاد
`0/1`→`1/1`، تعطيل تلقائي صحيح بعد بلوغ الحد). التغيير الفعلي محصور بسطر
واحد بـ`api.py` وسطرين نصيين ثابتين بـ`index.html` + سطر افتراضي بـ
`app.js` — كل رسائل الرفض الديناميكية تحدّثت تلقائياً عبر متغيّراتها
الموجودة أصلاً بلا أي تعديل نصي إضافي.
