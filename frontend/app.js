/* app.js — طبقة عرض فقط فوق api.py. لا يوجد هنا أي منطق قرار "أي أداة
   تُستدعى" — كل زر يرسل نص طلب بالعربية لـ /api/message، والوكيل (Gemini)
   عبر agent.py يقرر بنفسه. الملف هنا فقط: (1) جلسة، (2) استدعاءات fetch،
   (3) تنسيق بصري للنتائج حسب نوع الأداة المُرجَعة من tool_results،
   (4) تبديل الخدمة النشطة في هيكل التطبيق (شريط جانبي + مساحة عمل). */

const SESSION_ID = crypto.randomUUID();
const REVIEW_TOOLS = new Set(["improve_resume", "draft_cover_letter"]);
const SERVICE_ICONS = { titles: "sparkle", search: "search", match: "check", improve: "star", letter: "document" };
const EMPTY_MESSAGES = {
  titles: "اضغط الزر لاقتراح مسميات وظيفية تناسب سيرتك.",
  search: "ابحث عن وظائف لعرض النتائج هنا.",
  match: "اختر وظيفة من نتائج بحثك لتقييم التوافق.",
  improve: "اختر وظيفة لتحسين سيرتك بما يتوافق معها.",
  letter: "اختر وظيفة لكتابة خطاب تقديم مخصص.",
};
const JOB_SELECT_ID = { match: "matchSelect", improve: "improveSelect", letter: "letterSelect" };

let resumeReady = false;
let requestCount = 0;
let requestLimit = 6;
let latestJobs = [];
let activeService = null;
let serviceResultCache = {}; // { [service]: lastApiResponseData }

// ------------------------------------------------------------------
// أيقونات SVG بسيطة inline بستايل خط واحد موحّد — بلا إيموجي إطلاقاً
// ------------------------------------------------------------------
function icon(name, color = "#D3A0FD", size = 20) {
  const paths = {
    sparkle: '<path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z"/>',
    search: '<circle cx="10" cy="10" r="6"/><line x1="21" y1="21" x2="14.5" y2="14.5"/>',
    check: '<polyline points="4,12 9,17 20,6"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
    document: '<rect x="5" y="3" width="14" height="18" rx="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="12" y2="16"/>',
    list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
    star: '<path d="M12 2c0 5-2.5 7.5-7.5 7.5C9.5 9.5 12 12 12 17c0-5 2.5-7.5 7.5-7.5C14.5 9.5 12 7 12 2z"/>',
    pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  };
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[name] || ""}</svg>`;
}

// بعض نصوص الـ backend (تحذير improve_resume مثلاً) قد تحتوي إيموجي —
// نشيلها هنا على مستوى العرض بدل تعديل tools/ (ممنوع لمسه)، عشان تبقى
// الواجهة بلا أي إيموجي إطلاقاً كما هو مطلوب.
const EMOJI_PATTERN = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu;

function stripEmoji(str) {
  return (str ?? "").replace(EMOJI_PATTERN, "").replace(/\s{2,}/g, " ").trim();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = stripEmoji(str);
  return div.innerHTML;
}

// Gemini يرجّع نص Markdown بسيط أحياناً (**bold**) — نهرب الـ HTML أولاً
// (أمان) ثم نحوّل التنسيق الأساسي فقط، بدل عرض ** حرفياً كنص خام.
function formatReplyText(str) {
  return escapeHtml(str).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

// نتيجة جديدة تدخل مساحة النتائج بحركة صعود خفيفة 8px بدل ظهور مفاجئ
function animateIn() {
  const el = document.getElementById("resultsContent");
  el.classList.remove("results-fade-in");
  void el.offsetWidth;
  el.classList.add("results-fade-in");
}

// ------------------------------------------------------------------
// تهيئة أيقونات التنقل (الشريط الجانبي + شريط التبويبات السفلي معاً،
// كلاهما يحمل نفس [data-icon])
// ------------------------------------------------------------------
Object.entries(SERVICE_ICONS).forEach(([key, name]) => {
  document.querySelectorAll(`[data-icon="${key}"]`).forEach((el) => {
    el.innerHTML = icon(name, "#D3A0FD", 18);
  });
});
document.getElementById("fileChipIcon").innerHTML = icon("check", "#3F7A34", 14);

// ------------------------------------------------------------------
// التنقل بين الخدمات (هيكل تطبيق: خدمة نشطة واحدة فقط بالمساحة الرئيسية)
// ------------------------------------------------------------------
function selectService(key) {
  activeService = key;
  document.querySelectorAll(".nav-item, .tab-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.service === key);
  });
  document.querySelectorAll(".service-pane").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.service !== key);
  });

  document.getElementById("resultsContent").innerHTML = "";
  if (serviceResultCache[key]) {
    document.getElementById("resultsEmpty").classList.add("hidden");
    renderResult(serviceResultCache[key]);
  } else {
    showEmptyForService(key);
  }
}

function showEmptyForService(key) {
  document.getElementById("resultsContent").innerHTML = "";
  document.getElementById("resultsEmptyIcon").innerHTML = icon(SERVICE_ICONS[key], "#D3A0FD", 20);
  document.getElementById("resultsEmptyText").textContent = EMPTY_MESSAGES[key] || "";
  document.getElementById("resultsEmpty").classList.remove("hidden");
}

document.querySelectorAll(".nav-item, .tab-item").forEach((el) => {
  el.addEventListener("click", () => selectService(el.dataset.service));
});

// ------------------------------------------------------------------
// "سلسلة موجّهة": نقلة فورية لخدمة أخرى مع تعبئة السياق وإطلاق الطلب
// تلقائياً — تسريع فوق التنقل اليدوي، لا بديل عنه (يبقى يعمل دائماً).
// التبديل + عرض skeleton يحدثان بنفس اللحظة المتزامنة قبل أي انتظار شبكة،
// لأن sendMessage() تستدعي showSkeleton() فوراً قبل أول await بداخلها.
// ------------------------------------------------------------------
function activatePane(service) {
  activeService = service;
  document.querySelectorAll(".nav-item, .tab-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.service === service);
  });
  document.querySelectorAll(".service-pane").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.service !== service);
  });
}

function chainToSearch(title) {
  activatePane("search");
  document.getElementById("searchTitleInput").value = title;
  const city = document.getElementById("searchCityInput").value.trim();
  const message = city ? `ابحث لي عن وظائف ${title} في ${city}` : `ابحث لي عن وظائف ${title}`;
  sendMessage(message);
}

function chainToJob(service, job, message) {
  activatePane(service);
  const selectId = JOB_SELECT_ID[service];
  if (selectId && job) {
    const idx = latestJobs.findIndex((j) => j.title === job.title && j.company === job.company);
    if (idx >= 0) document.getElementById(selectId).value = String(idx);
  }
  sendMessage(message, job);
}

// ------------------------------------------------------------------
// رفع السيرة (يُستخدم أيضاً لمسار "استبدال" لاحقاً — نفس الدالة)
// ------------------------------------------------------------------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const uploadError = document.getElementById("uploadError");

document.getElementById("replaceBtn").addEventListener("click", () => {
  fileInput.click();
});

["dragover", "dragenter"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleUpload(file);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleUpload(fileInput.files[0]);
});

async function handleUpload(file) {
  uploadError.classList.add("hidden");
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    uploadError.textContent = "الملف يجب أن يكون PDF.";
    uploadError.classList.remove("hidden");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch("/api/upload", {
      method: "POST",
      headers: { "X-Session-Id": SESSION_ID },
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) {
      uploadError.textContent = stripEmoji(data.detail) || "تعذّر رفع الملف.";
      uploadError.classList.remove("hidden");
      return;
    }

    resumeReady = true;
    document.getElementById("uploadState").classList.add("hidden");
    document.getElementById("serviceWorkspace").classList.remove("hidden");
    document.getElementById("fileChip").classList.remove("hidden");
    document.getElementById("confirmFilename").textContent = data.filename;

    // سيرة جديدة تُبطل أي نتائج/وظائف من السيرة السابقة (مسار "استبدال")
    serviceResultCache = {};
    latestJobs = [];
    updateJobSelects();
    selectService(activeService || "titles");
  } catch (err) {
    uploadError.textContent = "تعذّر الاتصال بالخادم — تأكد من تشغيل السيرفر.";
    uploadError.classList.remove("hidden");
  }
}

// ------------------------------------------------------------------
// تفعيل/تعطيل عناصر الخدمات
// ------------------------------------------------------------------
function setServicesEnabled(enabled) {
  const limitReached = requestCount >= requestLimit;
  const actuallyEnabled = enabled && !limitReached;

  document.getElementById("btnTitles").disabled = !actuallyEnabled;
  document.getElementById("searchTitleInput").disabled = !actuallyEnabled;
  document.getElementById("searchCityInput").disabled = !actuallyEnabled;
  document.getElementById("btnSearch").disabled = !actuallyEnabled;

  const hasJobs = latestJobs.length > 0;
  ["match", "improve", "letter"].forEach((prefix) => {
    const select = document.getElementById(`${prefix}Select`);
    const btn = document.getElementById(`btn${capitalize(prefix)}`);
    const badge = document.getElementById(`${prefix}Badge`);
    select.disabled = !actuallyEnabled || !hasJobs;
    btn.disabled = !actuallyEnabled || !hasJobs;
    badge.classList.toggle("hidden", resumeReady ? hasJobs : true);
  });

  // الشريط الجانبي/شريط التبويبات: معطّل قبل رفع السيرة أو بعد بلوغ الحد
  const sidebarDisabled = !resumeReady || limitReached;
  document.getElementById("sidebar").classList.toggle("disabled", sidebarDisabled);
  document.getElementById("bottomTabs").classList.toggle("disabled", sidebarDisabled);
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function updateJobSelects() {
  const options = latestJobs
    .map((j, i) => `<option value="${i}">${escapeHtml(j.title)} — ${escapeHtml(j.company)}</option>`)
    .join("");
  ["matchSelect", "improveSelect", "letterSelect"].forEach((id) => {
    const el = document.getElementById(id);
    el.innerHTML = latestJobs.length ? options : "<option>لا توجد نتائج بحث بعد</option>";
  });
  setServicesEnabled(resumeReady);
}

function updateMeter() {
  document.getElementById("counterPill").textContent = `${requestCount}/${requestLimit}`;
  const pct = Math.min(100, (requestCount / requestLimit) * 100);
  document.getElementById("meterFill").style.width = `${pct}%`;
}

// ------------------------------------------------------------------
// إرسال رسالة للوكيل — المسار الوحيد لكل الأزرار
// ------------------------------------------------------------------
async function sendMessage(message, jobContext = null) {
  const requestedService = activeService;
  showSkeleton();

  let resp, data;
  try {
    resp = await fetch("/api/message", {
      method: "POST",
      headers: { "X-Session-Id": SESSION_ID, "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    data = await resp.json();
  } catch (err) {
    renderError("تعذّر الاتصال بالخادم. تأكد من تشغيل السيرفر وحاول مرة أخرى.");
    return;
  }

  if (resp.status === 429) {
    // نبني الرسالة هنا بدل عرض data.error من الـ backend مباشرة — نص
    // الخادم فيه صيغة تأنيث ("وصلتِ") لا يمكن تعديلها من هذا الملف
    // (api.py خارج نطاق هذي المهمة)، فنستخدم نفس نص الواجهة المذكّر
    // المستخدم أعلاه لضمان اتساق الصيغة بغض النظر عن مصدر الرسالة.
    requestCount = requestLimit;
    updateMeter();
    const limitMessage = `وصلت للحد الأقصى من الطلبات لهذي الجلسة (${requestLimit} طلبات).`;
    showLimitReached(limitMessage);
    renderError(limitMessage);
    return;
  }

  if (!resp.ok) {
    renderError(data.detail || "حدث خطأ غير متوقع.");
    return;
  }

  requestCount = data.request_count;
  requestLimit = data.request_limit;
  updateMeter();

  // حدّث قائمة الوظائف لو تضمّن الرد نتيجة بحث جديدة
  const searchResult = data.tool_results.find((t) => t.name === "search_jobs" && t.result && t.result.jobs);
  if (searchResult) {
    latestJobs = searchResult.result.jobs;
    updateJobSelects();
  }

  data.__jobContext = jobContext;
  serviceResultCache[requestedService] = data;
  if (requestedService === activeService) {
    renderResult(data);
  }
  setServicesEnabled(resumeReady);

  if (requestCount >= requestLimit) {
    showLimitReached(`وصلت للحد الأقصى من الطلبات لهذي الجلسة (${requestLimit} طلبات).`);
  }
}

function showLimitReached(message) {
  const card = document.getElementById("limitCard");
  card.textContent = stripEmoji(message);
  card.classList.remove("hidden");
  setServicesEnabled(false);
}

// ------------------------------------------------------------------
// عرض حالة الانتظار (skeleton)
// ------------------------------------------------------------------
function showSkeleton() {
  document.getElementById("resultsEmpty").classList.add("hidden");
  document.getElementById("resultsContent").innerHTML = `
    <div class="skeleton">
      <div class="skeleton-line w40"></div>
      <div class="skeleton-line w90"></div>
      <div class="skeleton-line w60"></div>
    </div>`;
}

function renderError(message) {
  document.getElementById("resultsEmpty").classList.add("hidden");
  document.getElementById("resultsContent").innerHTML = `<div class="error-card">${escapeHtml(message)}</div>`;
  animateIn();
}

// ------------------------------------------------------------------
// تنسيق النتيجة حسب آخر أداة مؤثرة في tool_results
// ------------------------------------------------------------------
function renderResult(data) {
  const container = document.getElementById("resultsContent");
  const results = data.tool_results || [];
  document.getElementById("resultsEmpty").classList.add("hidden");

  if (results.length === 0) {
    container.innerHTML = `<div class="plain-reply">${formatReplyText(data.reply)}</div>`;
    animateIn();
    return;
  }

  // آخر أداة "مؤثرة" (لها نتيجة قابلة للعرض كبطاقة) بدل نص خام موحّد
  const last = [...results].reverse().find((r) => r.result && !r.result.error) || results[results.length - 1];

  if (last.result && last.result.error) {
    renderError(last.result.error);
    return;
  }

  const jobContext = data.__jobContext || null;

  switch (last.name) {
    case "suggest_job_titles":
      renderTitles(last.result, data.reply);
      break;
    case "search_jobs":
      renderJobs(last.result, data.reply);
      break;
    case "evaluate_match":
      renderMatch(last.result, data.reply, jobContext);
      break;
    case "improve_resume":
      renderReview(last.result.improved_resume, last.result.changes, last.result.warning, "improved_resume.txt", data.reply);
      break;
    case "draft_cover_letter":
      renderReview(last.result.cover_letter, null, null, "cover_letter.txt", data.reply);
      break;
    case "log_application":
      renderLogConfirm(last.result, data.reply);
      break;
    case "get_application_status":
      renderApplications(last.result, data.reply);
      break;
    default:
      container.innerHTML = `<div class="plain-reply">${formatReplyText(data.reply)}</div>`;
      animateIn();
  }
}

function renderTitles(result, replyText) {
  const titles = result.suggested_titles || [];
  const container = document.getElementById("resultsContent");
  if (titles.length === 0) {
    container.innerHTML = `<div class="plain-reply">${formatReplyText(replyText)}</div>`;
    animateIn();
    return;
  }
  const pills = titles
    .map((t) => `<button class="title-pill" data-title="${escapeHtml(t)}">${escapeHtml(t)}</button>`)
    .join("");
  container.innerHTML = `<div class="titles-pills">${pills}</div>`;
  container.querySelectorAll(".title-pill").forEach((btn) => {
    btn.addEventListener("click", () => chainToSearch(btn.dataset.title));
  });
  animateIn();
}

function renderJobs(result, replyText) {
  const jobs = result.jobs || [];
  const container = document.getElementById("resultsContent");
  if (jobs.length === 0) {
    container.innerHTML = `<div class="plain-reply">${formatReplyText(replyText)}</div>`;
    animateIn();
    return;
  }
  const cards = jobs
    .map(
      (j, i) => `
    <div class="job-card">
      <div class="job-card-top">
        <h4 class="job-title">${escapeHtml(j.title)}</h4>
        <span class="job-company-badge">${escapeHtml(j.company)}</span>
      </div>
      <p class="job-location">${icon("pin", "#5F5F5F", 14)} ${escapeHtml(j.location)}</p>
      ${j.snippet ? `<p class="job-snippet">${escapeHtml(j.snippet)}</p>` : ""}
      <div class="job-card-actions">
        <a class="job-link" href="${escapeHtml(j.link)}" target="_blank" rel="noopener">عرض الإعلان الأصلي ←</a>
        <button class="btn job-inline-btn" type="button" data-index="${i}">قيّم التوافق مع هذي الوظيفة</button>
      </div>
    </div>`
    )
    .join("");
  container.innerHTML = `
    <div class="jobs-list">${cards}</div>
    <p class="legitimacy-notice">تحقق من شرعية الشركة قبل التقديم — النتائج مستمدة من محرك تجميع (Jooble).</p>`;
  container.querySelectorAll(".job-inline-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const job = jobs[Number(btn.dataset.index)];
      chainToJob("match", job, `قيّم توافق سيرتي مع وظيفة ${job.title} في شركة ${job.company}`);
    });
  });
  animateIn();
}

function renderMatch(result, replyText, jobContext) {
  const score = result.match_score ?? 0;
  const tier = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
  const tierIcon = { high: "check", mid: "star", low: "arrow-up" }[tier];
  const container = document.getElementById("resultsContent");
  const followUps = jobContext
    ? `<div class="chain-actions">
        <button class="btn" id="chainImprove" type="button">حسّن سيرتي لهذي الوظيفة</button>
        <button class="btn" id="chainLetter" type="button">اكتب خطاب تقديم</button>
      </div>`
    : "";
  container.innerHTML = `
    <div class="match-card">
      <div class="match-score-wrap">
        <div class="match-score-badge ${tier}">${score}%</div>
        <div class="match-score-icon ${tier}">${icon(tierIcon, "#fff", 11)}</div>
      </div>
      <div class="match-reasoning">${formatReplyText(result.reasoning || replyText)}</div>
    </div>
    ${followUps}`;
  if (jobContext) {
    document.getElementById("chainImprove").addEventListener("click", () => {
      chainToJob("improve", jobContext, `حسّن سيرتي الذاتية لتتوافق مع وظيفة ${jobContext.title} في شركة ${jobContext.company}`);
    });
    document.getElementById("chainLetter").addEventListener("click", () => {
      chainToJob("letter", jobContext, `اكتب لي خطاب تقديم لوظيفة ${jobContext.title} في شركة ${jobContext.company}`);
    });
  }
  animateIn();
}

function renderReview(fullText, changes, warning, filename, replyText) {
  const container = document.getElementById("resultsContent");
  const text = fullText || replyText;
  const changesHtml = changes && changes.length
    ? `<ul class="changes-list">${changes
        .map((c) => `<li><strong>${escapeHtml(c.section)}:</strong> ${escapeHtml(c.what_changed)} <em>${escapeHtml(c.grounding || "")}</em></li>`)
        .join("")}</ul>`
    : "";
  const warningHtml = warning ? `<p class="plain-reply" style="margin-top:0.75rem">${escapeHtml(warning)}</p>` : "";

  container.innerHTML = `
    <div class="review-box">
      <p class="review-title">${icon("sparkle", "#8B7B00", 18)} يحتاج مراجعتك</p>
      <div class="review-text-wrap">
        <div class="review-text" id="reviewText">${escapeHtml(text)}</div>
      </div>
      <button class="review-toggle" id="reviewToggle">عرض الكل</button>
      ${changesHtml}
      ${warningHtml}
      <div class="review-actions">
        <button class="btn" id="downloadBtn">تحميل كملف نصي جديد</button>
      </div>
    </div>`;

  const reviewText = document.getElementById("reviewText");
  document.getElementById("reviewToggle").addEventListener("click", (e) => {
    reviewText.classList.toggle("expanded");
    e.target.textContent = reviewText.classList.contains("expanded") ? "إخفاء" : "عرض الكل";
  });
  document.getElementById("downloadBtn").addEventListener("click", () => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  });
  animateIn();
}

function renderLogConfirm(result, replyText) {
  const container = document.getElementById("resultsContent");
  const app = result.application || {};
  container.innerHTML = `
    <div class="confirm-toast">
      ${icon("check", "#3F7A34", 20)}
      <span>تم تسجيل التقديم على ${escapeHtml(app.title || "")} في ${escapeHtml(app.company || "")}.</span>
    </div>
    <p class="plain-reply" style="margin-top:1rem">${formatReplyText(replyText)}</p>`;
  animateIn();
}

function renderApplications(result, replyText) {
  const apps = result.applications || [];
  const container = document.getElementById("resultsContent");
  if (apps.length === 0) {
    container.innerHTML = `<div class="plain-reply">${formatReplyText(replyText)}</div>`;
    animateIn();
    return;
  }
  const statusLabels = { submitted: "تم التقديم", interview: "مقابلة", offer: "عرض عمل", rejected: "مرفوض" };
  const cards = apps
    .map(
      (a) => `
    <div class="application-card">
      <div class="application-info">
        <strong>${escapeHtml(a.title)}</strong>
        <span>${escapeHtml(a.company)} — ${escapeHtml(a.date)}</span>
      </div>
      <span class="status-badge ${escapeHtml(a.status)}">${escapeHtml(statusLabels[a.status] || a.status)}</span>
    </div>`
    )
    .join("");
  container.innerHTML = `<div class="applications-list">${cards}</div>`;
  animateIn();
}

// ------------------------------------------------------------------
// ربط أزرار الخدمات — كل واحد يبني نص طلب فقط، لا استدعاء أداة مباشر
// ------------------------------------------------------------------
document.getElementById("btnTitles").addEventListener("click", () => {
  sendMessage("حلل سيرتي واقترح مسميات وظيفية تناسبني");
});

document.getElementById("btnSearch").addEventListener("click", () => {
  const title = document.getElementById("searchTitleInput").value.trim();
  const city = document.getElementById("searchCityInput").value.trim();
  if (!title || !city) {
    renderError("أدخل المسمى الوظيفي والمدينة أولاً.");
    return;
  }
  sendMessage(`ابحث لي عن وظائف ${title} في ${city}`);
});

document.getElementById("btnMatch").addEventListener("click", () => {
  const job = latestJobs[document.getElementById("matchSelect").value];
  if (!job) return;
  sendMessage(`قيّم توافق سيرتي مع وظيفة ${job.title} في شركة ${job.company}`, job);
});

document.getElementById("btnImprove").addEventListener("click", () => {
  const job = latestJobs[document.getElementById("improveSelect").value];
  if (!job) return;
  sendMessage(`حسّن سيرتي الذاتية لتتوافق مع وظيفة ${job.title} في شركة ${job.company}`, job);
});

document.getElementById("btnLetter").addEventListener("click", () => {
  const job = latestJobs[document.getElementById("letterSelect").value];
  if (!job) return;
  sendMessage(`اكتب لي خطاب تقديم لوظيفة ${job.title} في شركة ${job.company}`, job);
});

updateMeter();
setServicesEnabled(false);
