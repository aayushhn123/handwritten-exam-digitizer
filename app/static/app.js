/* Exam Digitizer UI - all client-side behaviour. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const ENTITY_INFO = {
  STUDENT_ID: { name: "Student ID", color: "var(--e-id)" },
  QUESTION_NUM: { name: "Question no.", color: "var(--e-q)" },
  MARKS: { name: "Marks", color: "var(--e-marks)" },
  PAGE_NUM: { name: "Page no.", color: "var(--e-page)" },
};

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("show"), 1800);
}

async function copyText(text, label = "Copied to clipboard") {
  try { await navigator.clipboard.writeText(text); toast(label); }
  catch { toast("Copy failed - select the text manually"); }
}

function download(name, content, type) {
  const blob = new Blob([content], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ============================== theme ============================== */

function currentTheme() {
  const forced = document.documentElement.dataset.theme;
  if (forced) return forced;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  const dark = currentTheme() === "dark";
  $("#hljs-light").disabled = dark;
  $("#hljs-dark").disabled = !dark;
  if (flowState.rendered) renderFlow(flowState.current);
}
(function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch {}
  if (saved) document.documentElement.dataset.theme = saved;
  $("#themeToggle").addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", next); } catch {}
    applyTheme(next);
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => applyTheme());
})();

/* ============================== tabs ============================== */

function showTab(name) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  if (name === "flow" && !flowState.rendered) renderFlow(flowState.current);
  if (name === "arch" && !treeState.loaded) loadTree();
  history.replaceState(null, "", "#" + name);
  window.scrollTo({ top: 0 });
}
$$(".tab").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

// any element with data-open="path" jumps to the code viewer
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-open]");
  if (!el) return;
  e.preventDefault();
  openFileFromAnywhere(el.dataset.open);
});

/* ============================== health ============================== */

fetch("/api/health").then((r) => r.json()).then((h) => {
  const el = $("#health");
  el.classList.add(h.tesseract ? "ok" : "bad");
  $(".health-text", el).textContent = h.tesseract ? `Tesseract ${h.tesseract_version.split(".").slice(0, 2).join(".")} ready` : "Tesseract not found";
  el.title = h.tesseract_path || "Install Tesseract OCR to enable digitizing";
}).catch(() => {});

/* ============================== upload ============================== */

const state = { file: null, sample: null, job: null, pages: [], current: 0, zoom: 1, fileName: "" };

function setFile(file) {
  state.file = file;
  state.sample = null;
  $$(".sample").forEach((s) => s.classList.remove("on"));
  renderChip(file ? file.name : null, file ? (file.size / 1024 / 1024).toFixed(1) + " MB" : "");
}
function renderChip(name, meta) {
  const chip = $("#fileChip");
  if (!name) { chip.classList.add("hidden"); $("#runBtn").disabled = true; return; }
  chip.innerHTML = `<svg viewBox="0 0 24 24"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/></svg><span>${esc(name)}</span><small class="muted">${esc(meta)}</small><button class="x" title="Remove" aria-label="Remove file">×</button>`;
  chip.classList.remove("hidden");
  $(".x", chip).addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); setFile(null); $("#fileInput").value = ""; });
  $("#runBtn").disabled = false;
}

$("#fileInput").addEventListener("change", (e) => e.target.files[0] && setFile(e.target.files[0]));
const dz = $("#dropzone");
["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
dz.addEventListener("drop", (e) => e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]));

fetch("/api/samples").then((r) => r.json()).then((list) => {
  const box = $("#sampleList");
  if (!list.length) { box.innerHTML = `<span class="muted small">No samples in data/raw_scans/</span>`; return; }
  box.innerHTML = list.map((s) => `
    <button class="sample" data-name="${esc(s.name)}">
      <img src="${s.thumb}" alt="">
      <span><b>${esc(s.name)}</b><small>${s.has_ground_truth ? "has ground truth · auto CER/WER" : "no ground truth"}</small></span>
    </button>`).join("");
  $$(".sample", box).forEach((b) => b.addEventListener("click", () => {
    state.file = null; $("#fileInput").value = "";
    state.sample = b.dataset.name;
    $$(".sample").forEach((s) => s.classList.toggle("on", s === b));
    renderChip(b.dataset.name, "sample");
  }));
});

$$(".segmented").forEach((seg) => seg.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  $$("button", seg).forEach((x) => x.classList.toggle("on", x === b));
}));
const segVal = (id) => $(`#${id} button.on`).dataset.val;

/* ============================== run + progress ============================== */

const STAGE_ORDER = ["upload", "render", "preprocess", "ocr", "ner", "assemble"];

function setSteps(stage, opts, finished) {
  const idx = STAGE_ORDER.indexOf(stage === "done" ? "assemble" : stage);
  $$("#liveSteps li").forEach((li) => {
    const i = STAGE_ORDER.indexOf(li.dataset.stage);
    li.className = "";
    if (li.dataset.stage === "preprocess" && opts && opts.enhance === "raw") { if (i <= idx || finished) li.className = "skipped"; return; }
    // OCR and NER run inside one digitize_page() call; light them together
    const effIdx = stage === "ocr" ? STAGE_ORDER.indexOf("ner") : idx;
    if (finished || i < idx) li.classList.add("done");
    else if (i <= effIdx) li.classList.add("active");
  });
}

function resetProgress() {
  $$("#liveSteps li").forEach((li) => (li.className = ""));
  $("#progressFill").style.width = "0";
  $("#liveLog").innerHTML = "";
}

$("#runBtn").addEventListener("click", async () => {
  if (!state.file && !state.sample) return;
  const btn = $("#runBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Digitizing…`;
  resetProgress();
  $("#results").classList.add("hidden");

  const fd = new FormData();
  if (state.file) fd.append("file", state.file); else fd.append("sample", state.sample);
  fd.append("ner", segVal("nerMode"));
  fd.append("dpi", segVal("dpi"));
  fd.append("enhance", segVal("enhance"));
  fd.append("spell", $("#spell").checked ? "true" : "false");
  state.fileName = state.file ? state.file.name : state.sample;

  try {
    const r = await fetch("/api/digitize", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Upload failed");
    await poll(data.job_id);
  } catch (err) {
    $("#liveLog").innerHTML += `<div class="err">✕ ${esc(err.message)}</div>`;
    $("#progressLabel").textContent = "Failed";
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg> Digitize`;
  }
});

async function poll(jobId) {
  while (true) {
    const job = await (await fetch(`/api/jobs/${jobId}`)).json();
    const finished = job.status === "done";
    setSteps(job.stage, job.options, finished);
    $("#liveLog").innerHTML = job.log.map((l) => `<div class="${l.msg.startsWith("Error") ? "err" : ""}"><span class="t">${l.t.toFixed(1)}s</span>${esc(l.msg)}</div>`).join("");
    $("#liveLog").scrollTop = 1e6;

    const total = job.total || 1;
    let pct = 5;
    if (job.stage === "render") pct = 5 + 15 * ((job.page || 0) / total);
    else if (["preprocess", "ocr", "ner"].includes(job.stage)) pct = 20 + 75 * (job.pages.length / total);
    else if (finished) pct = 100;
    $("#progressFill").style.width = pct + "%";
    $("#progressLabel").textContent = finished ? `Done in ${(job.finished - job.started).toFixed(1)}s`
      : job.total ? `Page ${job.page} of ${job.total}` : "Starting…";

    if (job.status === "error") throw new Error(job.error);
    if (finished) { state.job = job; showResults(job); return; }
    await new Promise((res) => setTimeout(res, 600));
  }
}

/* ============================== results ============================== */

function confColor(c) { return c >= 0.75 ? "var(--ok)" : c >= 0.5 ? "var(--warn)" : "var(--bad)"; }
function confWord(c) { return c >= 0.75 ? "High" : c >= 0.5 ? "Medium - worth a quick review" : "Low - please check manually"; }

function showResults(job) {
  state.pages = job.pages;
  state.current = 0;
  $("#results").classList.remove("hidden");
  const o = job.options;
  const enhanceName = { smart: "smart enhancement", raw: "no enhancement", legacy: "Week 1-2 threshold" }[o.enhance];
  $("#resultsFile").textContent = `${job.file} · ${enhanceName} · ${o.improved_ner ? "improved NER" : "spaCy NER"}${o.spell ? " · spelling corrected" : ""}`;

  const avgConf = job.pages.reduce((s, p) => s + p.record.ocr_confidence, 0) / job.pages.length;
  const words = job.pages.reduce((s, p) => s + p.words, 0);
  const ents = job.pages.reduce((s, p) => s + p.record.entities_found.length, 0);
  const secs = (job.finished - job.started).toFixed(1);
  $("#stats").innerHTML = `
    <div class="stat"><div class="k">Pages</div><div class="v">${job.pages.length}</div><div class="s">processed</div></div>
    <div class="stat"><div class="k">Avg. OCR confidence</div><div class="v" style="color:${confColor(avgConf)}">${Math.round(avgConf * 100)}%</div>
      <div class="conf-meter"><div style="width:${avgConf * 100}%;background:${confColor(avgConf)}"></div></div></div>
    <div class="stat"><div class="k">Words extracted</div><div class="v">${words.toLocaleString()}</div><div class="s">${job.pages.reduce((s, p) => s + p.chars, 0).toLocaleString()} characters</div></div>
    <div class="stat"><div class="k">Entities found</div><div class="v">${ents}</div><div class="s">IDs, questions, marks, pages</div></div>
    <div class="stat"><div class="k">Total time</div><div class="v">${secs}s</div><div class="s">${(secs / job.pages.length).toFixed(1)}s per page</div></div>`;

  $("#pageNav").innerHTML = job.pages.map((p, i) => `
    <button class="page-btn ${i === 0 ? "on" : ""}" data-i="${i}">
      <img src="${p.image_url}" alt="">
      <span>Page ${p.page}<span class="pc" style="color:${confColor(p.record.ocr_confidence)}">${Math.round(p.record.ocr_confidence * 100)}% conf.</span></span>
    </button>`).join("");
  $("#pageNav").classList.toggle("hidden", job.pages.length < 2);
  $$(".page-btn").forEach((b) => b.addEventListener("click", () => {
    $$(".page-btn").forEach((x) => x.classList.toggle("on", x === b));
    state.current = +b.dataset.i;
    renderPage();
  }));
  renderPage();
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function locateEntities(text, ents) {
  // Entity offsets are relative to Tesseract's raw text; the record's
  // answer_text is trimmed, so re-anchor each one by its surface string.
  const spans = [];
  for (const e of ents) {
    const surface = e.original_text || e.text;
    let pos = -1;
    for (const d of [0, -1, -2, -3, 1, 2]) {
      if (text.substr(e.start_char + d, surface.length) === surface) { pos = e.start_char + d; break; }
    }
    if (pos < 0) pos = text.indexOf(surface, Math.max(0, e.start_char - 40));
    if (pos < 0) pos = text.indexOf(surface);
    if (pos >= 0) spans.push({ s: pos, e: pos + surface.length, ent: e });
  }
  spans.sort((a, b) => a.s - b.s);
  return spans.filter((sp, i) => i === 0 || sp.s >= spans[i - 1].e);
}

function highlighted(text, ents) {
  let out = "", last = 0;
  for (const sp of locateEntities(text, ents)) {
    const info = ENTITY_INFO[sp.ent.label] || { name: sp.ent.label };
    const tip = `${info.name}: ${sp.ent.text}` + (sp.ent.original_text && sp.ent.original_text !== sp.ent.text ? ` (OCR read "${sp.ent.original_text}")` : "");
    out += esc(text.slice(last, sp.s)) + `<mark class="ent ${sp.ent.label}" title="${esc(tip)}">${esc(text.slice(sp.s, sp.e))}</mark>`;
    last = sp.e;
  }
  return out + esc(text.slice(last));
}

function renderPage() {
  const p = state.pages[state.current];
  const rec = p.record;
  state.zoom = 1; applyZoom();
  const vm = $("#viewMode");
  vm.classList.toggle("hidden", !p.enhanced_url);
  const showEnh = p.enhanced_url && $("#viewMode button.on").dataset.val === "enh";
  $("#scanImg").src = showEnh ? p.enhanced_url : p.image_url;

  const txt = rec.answer_text || "(No text was recognised on this page.)";
  $("#pageText").innerHTML = $("#hlEntities").checked ? highlighted(txt, rec.entities_found) : esc(txt);

  const field = (label, key, val) => `<div class="field"><div class="k">${key ? `<i style="background:${ENTITY_INFO[key].color}"></i>` : ""}${label}</div>
    <div class="v ${val == null ? "none" : ""}">${val == null ? "not found" : esc(val)}</div></div>`;
  const rows = rec.entities_found.map((e) => `<tr>
      <td><span class="tag" style="background:${ENTITY_INFO[e.label]?.color || "var(--surface-2)"}">${esc(e.label)}</span></td>
      <td><code>${esc(e.text)}</code></td>
      <td><code>${esc(e.original_text ?? e.text)}</code></td>
      <td class="muted">${e.start_char}–${e.end_char}</td></tr>`).join("");
  $("#details").innerHTML = `
    <div class="fields">
      ${field("Student ID", "STUDENT_ID", rec.student_id)}
      ${field("Question", "QUESTION_NUM", rec.question)}
      ${field("Marks detected", "MARKS", rec.marks_detected)}
      <div class="field"><div class="k">OCR confidence</div><div class="v" style="color:${confColor(rec.ocr_confidence)}">${Math.round(rec.ocr_confidence * 100)}%</div>
        <div class="small muted">${confWord(rec.ocr_confidence)}</div></div>
    </div>
    <h3 style="margin-bottom:8px">All candidates found (${rec.entities_found.length})</h3>
    ${rec.entities_found.length ? `<table class="ents"><thead><tr><th>Label</th><th>Cleaned value</th><th>As read by OCR</th><th>Position</th></tr></thead><tbody>${rows}</tbody></table>`
      : `<p class="muted">No entities matched on this page. Handwritten IDs and question labels are often misread by OCR (for example “Q1” read as “QL”), so they no longer fit the patterns. This is a known limitation on real handwriting.</p>`}
    <div class="note">The first candidate of each kind (by position on the page) becomes the official value. All candidates are kept so a human can review low-confidence pages. Timing: OCR + NER took ${(p.timings.digitize_ms / 1000).toFixed(1)}s${p.timings.preprocess_ms ? `, cleaning ${p.timings.preprocess_ms} ms` : ""}.</div>`;

  const code = $("#pageJson");
  code.textContent = JSON.stringify(rec, null, 2);
  code.removeAttribute("data-highlighted");
  if (window.hljs) hljs.highlightElement(code);

  $("#autoAccuracy").innerHTML = p.accuracy ? `<div class="note" style="margin:0 0 4px">Ground truth found in <code>data/ground_truth/</code> for this sample, scored automatically:</div>${scoreHtml(p.accuracy)}` : "";
  $("#scoreOut").innerHTML = "";
}

function scoreHtml(s) {
  const cls = (v) => (v <= 0.15 ? "good" : v <= 0.4 ? "mid" : "bad");
  return `<div class="score-row">
    <div class="score ${cls(s.cer)}"><div class="k">CER · character errors</div><div class="v">${(s.cer * 100).toFixed(1)}%</div><div class="small muted">character edits needed ÷ true length</div></div>
    <div class="score ${cls(s.wer)}"><div class="k">WER · word errors</div><div class="v">${(s.wer * 100).toFixed(1)}%</div><div class="small muted">word edits needed ÷ true word count; one wrong letter makes a whole word wrong</div></div></div>`;
}

$("#hlEntities").addEventListener("change", () => state.pages.length && renderPage());
$("#viewMode").addEventListener("click", (e) => {
  const p = state.pages[state.current];
  if (!e.target.closest("button") || !p?.enhanced_url) return;
  // .segmented's own handler has already moved the "on" class
  setTimeout(() => { $("#scanImg").src = segVal("viewMode") === "enh" ? p.enhanced_url : p.image_url; });
});
$("#outTabs").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  $$("#outTabs button").forEach((x) => x.classList.toggle("on", x === b));
  $$(".text-card .out").forEach((o) => o.classList.toggle("on", o.classList.contains("out-" + b.dataset.out)));
});
function applyZoom() { $("#scanImg").style.width = state.zoom * 100 + "%"; $("#zoomVal").textContent = Math.round(state.zoom * 100) + "%"; }
$("#zoomIn").addEventListener("click", () => { state.zoom = Math.min(3, state.zoom + 0.25); applyZoom(); });
$("#zoomOut").addEventListener("click", () => { state.zoom = Math.max(0.5, state.zoom - 0.25); applyZoom(); });

$("#scoreBtn").addEventListener("click", async () => {
  const ref = $("#refText").value.trim();
  if (!ref) return toast("Paste the correct text first");
  const r = await fetch("/api/score", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reference: ref, hypothesis: state.pages[state.current].record.answer_text }) });
  const d = await r.json();
  $("#scoreOut").innerHTML = r.ok ? scoreHtml(d) : `<p class="muted">${esc(d.error)}</p>`;
});

const allText = () => state.pages.map((p) => `===== Page ${p.page} =====\n${p.record.answer_text}`).join("\n\n");
const baseName = () => (state.fileName || "digitized").replace(/\.[^.]+$/, "");
$("#copyAll").addEventListener("click", () => copyText(allText(), "All text copied"));
$("#copyPage").addEventListener("click", () => copyText(state.pages[state.current].record.answer_text, "Page text copied"));
$("#dlTxt").addEventListener("click", () => download(baseName() + "_digitized.txt", allText(), "text/plain"));
$("#dlJson").addEventListener("click", () => download(baseName() + "_digitized.json", JSON.stringify(state.pages.map((p) => p.record), null, 2), "application/json"));

/* ============================== pipeline content ============================== */

const PIPELINE = [
  {
    title: "Upload & split into pages",
    plain: "You give the system a PDF or a photo. A PDF can hold many pages, so each page is turned into its own high-resolution picture. OCR only works on pictures, not on PDF files.",
    input: "PDF / JPG / PNG", output: "One image per page",
    files: ["app/server.py"],
    tech: ["PyMuPDF renders each PDF page at 300 DPI (dots per inch), so small handwriting stays sharp.", "Photos skip this step and go straight through.", "Up to 40 pages per upload."],
  },
  {
    title: "Enhance the image",
    plain: "Phone photos of notebook pages have pink margins, ruled lines, shadows and a slight tilt, and all of these confuse OCR. This step strips them away while leaving the pen strokes untouched, so the page looks more like clean print.",
    input: "Colour page photo", output: "Clean, straight grayscale page",
    files: ["src/ocr_pipeline.py", "src/preprocess.py"],
    tech: [
      "Red colour channel only: pink and red rules turn white, while blue and black ink stays dark.",
      "Lighting correction: divide by a heavily blurred copy of the page to remove shadows and gradients.",
      "Straighten: measure the angle of the ruled lines (Hough transform) and rotate them level.",
      "Erase ruled lines: find long thin horizontal lines and paint only their faint pixels white, keeping dark ink that crosses them.",
      "Upscale 1.5× so strokes are closer to the size Tesseract's model expects.",
      "Replaces the Week 1-2 preprocess.py (hard black/white threshold), which Week 5 showed hurt accuracy. It is still selectable in the UI for comparison.",
    ],
    example: "Character error rate before → after this step:\n  neat handwriting  39.7% → 3.7%\n  cursive           45.5% → 34.1%",
  },
  {
    title: "Read the handwriting (OCR)",
    plain: "Tesseract looks at the cleaned picture and works out which letters are written where, producing plain text. It also reports how sure it is about every word, which becomes a 0-100% confidence score for the page.",
    input: "Enhanced page image", output: "Raw text + confidence score",
    files: ["src/ocr_pipeline.py", "src/digitizer.py"],
    tech: ["One pytesseract.image_to_data() pass gives every word, its line and its confidence. The text is rebuilt from it, so OCR runs only once.", "Page segmentation mode 4: a single column of text of varying sizes.", "Confidence = average word confidence ÷ 100.", "Tesseract is trained mostly on print, so cursive still lowers accuracy."],
    example: 'Scan: "Q1. OSI Model in Email Sending"\nOCR:  "QL OS! Model in Email Sending"',
  },
  {
    title: "Clean up the text",
    plain: "Leftover bits of ruled lines show up as “____”, “—” or “|”, so these are removed. Optionally, a spell checker can fix words OCR got slightly wrong, like “protess” → “process”.",
    input: "Raw OCR text", output: "Clean text",
    files: ["src/ocr_pipeline.py"],
    tech: ["Regex removes runs of _ — – ~ and stray | characters at line edges.", "Spelling (optional, off by default): pyspellchecker with edit distance 1-2. Prefers words that already appear correctly elsewhere on the same page.", "Never changes capitalised words (names), ALL-CAPS terms (SMTP) or anything with digits.", "Entities are always found before spelling correction, so IDs can't be altered.", "Off by default because it would also 'fix' the student's own spelling mistakes."],
    example: 'OCR:        "with ___ opeific tespon sihilities in dako"\nCleaned:    "with opeific tespon sihilities in dako"',
  },
  {
    title: "Split by question",
    plain: "Answer sheets are organised by question. This step scans the OCR words for markers like “Q1”, “Q2.” and groups everything after each marker into that question's answer.",
    input: "OCR words with positions", output: "Text grouped per question",
    files: ["src/segment.py"],
    tech: ["Uses image_to_data() so it knows where each word sits on the page.", "Regex ^Q(\\d+)[.):]?$ detects a new question.", "Used by the baseline OCR script; digitize_page() currently keeps the whole page as one answer."],
  },
  {
    title: "Find key details (NER)",
    plain: "Named Entity Recognition: pick out the important facts in the text, namely the Student ID, Question number, Marks and Page number. The improved version also fixes common OCR mix-ups, like reading the digit 0 as the letter O.",
    input: "Raw text", output: "Student ID, Question, Marks, Page",
    files: ["src/ner_extractor.py", "src/ner_improved.py"],
    tech: ["Week 3: spaCy EntityRuler with token patterns (e.g. ^[0-9]{2}[A-Za-z][0-9]{3,4}$ for IDs like 23D001).", "Week 4: pure regex that allows look-alike characters, then repairs them: O→0, D→0, l/I/L→1, S→5, B→8, Z→2.", "Week 7: an ID right after “Roll no”, “ID” or “Reg no” is accepted even with no real digit (“EO13” → E013).", "Week 7: “QL.” → Q1, and “@1)” at the start of a line → Q1 (a handwritten Q is often read as @).", "Week 7: dates like 5/11/2024 are no longer mistaken for marks “5/11”.", "Every candidate is kept; the earliest one on the page wins for each label."],
    example: 'OCR text:  "23DOO1 Q3 ... Marks 7/1O"\nCleaned:   STUDENT_ID=23D001  QUESTION_NUM=Q3  MARKS=7/10',
  },
  {
    title: "Package the record",
    plain: "Everything is put into one tidy, predictable record per page that any other program can read. Group 2's AI Exam Grader takes this as its input.",
    input: "Text + entities + confidence", output: "JSON record",
    files: ["src/digitizer.py"],
    tech: ["One public function: digitize_page(image_path, page_number=None, use_improved_ner=True, enhance=True, spell_correct=False).", "Returns student_id, question, answer_text, page, marks_detected, ocr_confidence, entities_found.", "The spaCy model is loaded once and reused across pages."],
    example: '{ "student_id": "E007", "question": "Q1",\n  "answer_text": "...", "ocr_confidence": 0.54, ... }',
  },
  {
    title: "Measure quality",
    plain: "To know if the system is any good, we compare its output with text typed by hand (the ground truth). We count how many characters and words are wrong, and how many entities were found correctly.",
    input: "OCR output + ground truth", output: "CER, WER, Precision, Recall, F1",
    files: ["src/evaluate.py", "src/evaluate_ner.py", "src/compare_ner_approaches.py"],
    tech: ["CER (character error rate) and WER (word error rate) via jiwer. Lower is better.", "evaluate.py scores both the original and the Week 7 enhanced OCR.", "NER precision / recall / F1 on labelled examples, plus a Week 7 set of real OCR mistakes.", "compare_ner_approaches.py scores Week 3 vs Week 4 NER side by side."],
  },
];

const TIMELINE = [
  { w: "Weeks 1-2", t: "Foundations", d: "Image cleaning, question segmentation, Tesseract baseline and CER/WER evaluation." },
  { w: "Week 3", t: "Rule-based NER", d: "spaCy EntityRuler finds student IDs, question numbers, marks and page numbers." },
  { w: "Week 4", t: "Noise-tolerant NER", d: "Regex that repairs OCR look-alikes and keeps every candidate. Compared against Week 3." },
  { w: "Week 5", t: "Real-data evaluation", d: "Ran on real photographed answer sheets. Found that preprocessing hurt accuracy." },
  { w: "Week 6", t: "Reusable asset", d: "Whole pipeline wrapped as digitize_page() for other groups to import." },
  { w: "Web UI", t: "Web interface", d: "This UI: upload PDFs, watch the pipeline run, read the code." },
  { w: "Week 7", t: "Accuracy boost", d: "Smart image enhancement and text clean-up: average CER 42.6% → 18.9%. Smarter NER for real OCR mistakes." },
];

$("#pipelineSteps").innerHTML = PIPELINE.map((s, i) => `
  <div class="step">
    <div class="step-num">${i + 1}</div>
    <div>
      <h3>${s.title}${s.optional ? '<span class="tag-opt">optional</span>' : ""}</h3>
      <p>${s.plain}</p>
      <div class="io"><span class="lbl">In</span><span class="chip">${s.input}</span><span class="arrow">→</span><span class="lbl">Out</span><span class="chip">${s.output}</span></div>
      ${s.example ? `<div class="example">${esc(s.example)}</div>` : ""}
      <details><summary>Technical details</summary><ul>${s.tech.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></details>
      <div class="files">${s.files.map((f) => `<a class="file-link" data-open="${f}">${f}</a>`).join("")}</div>
    </div>
  </div>`).join("");
$("#timeline").innerHTML = TIMELINE.map((t) => `<div class="tl"><div class="w">${t.w}</div><b>${t.t}</b><p>${t.d}</p></div>`).join("");

/* ============================== flowcharts ============================== */

const FLOWS = {
  e2e: {
    name: "End-to-end pipeline",
    caption: "<b>The full journey of one upload.</b> Diamonds are decisions. The left branch is what happens for PDFs; the NER branch depends on the option you pick in the Digitize tab.",
    code: `flowchart TD
  A(["Upload PDF or photo"]) --> B{"Is it a PDF?"}
  B -- "yes" --> C["Render every page to an image<br/><small>PyMuPDF · 300 DPI</small>"]
  B -- "no" --> D["Use the photo as-is"]
  C --> E{"Image enhancement?"}
  D --> E
  E -- "Smart (default)" --> F["Red channel → even lighting → straighten<br/>→ erase ruled lines → upscale 1.5×<br/><small>ocr_pipeline.py · OpenCV</small>"]
  E -- "Week 1-2" --> F2["Threshold + deskew<br/><small>preprocess.py</small>"]
  E -- "None" --> G
  F --> G["Read text with Tesseract OCR<br/><small>text + per-word confidence</small>"]
  F2 --> G
  G --> CL["Remove rule debris ____ — |<br/><small>ocr_pipeline.py</small>"]
  CL --> H{"Which entity finder?"}
  H -- "Improved" --> I["Regex + fix OCR look-alikes<br/><small>ner_improved.py</small>"]
  H -- "Baseline" --> J["spaCy EntityRuler patterns<br/><small>ner_extractor.py</small>"]
  I --> K["Pick the first candidate per label"]
  J --> K
  K --> SP{"Auto-correct spelling?"}
  SP -- "yes" --> SC["pyspellchecker on answer text<br/><small>names, IDs and acronyms untouched</small>"]
  SP -- "no (default)" --> L
  SC --> L[["Structured record per page<br/><small>digitize_page() · digitizer.py</small>"]]
  L --> M(["Shown in UI · download .txt / .json"])
  L --> N(["Group 2: AI Exam Grader"])`,
  },
  digitize: {
    name: "Inside digitize_page()",
    caption: "<b>What the reusable asset does when called.</b> This is the single function other groups import. The UI calls it once per page.",
    code: `sequenceDiagram
  autonumber
  participant Caller as Caller (UI / Group 2)
  participant D as digitize_page()
  participant T as Tesseract OCR
  participant N as NER extractor
  Caller->>D: image_path, page_number, use_improved_ner
  D->>T: image_to_string(image)
  T-->>D: raw text
  D->>T: image_to_data(image)
  T-->>D: word confidences → average (0-1)
  alt use_improved_ner = True
    D->>N: extract_entities_improved(text)
  else
    D->>N: spaCy pipeline + extract_entities(text)
  end
  N-->>D: all candidates + best per label
  D-->>Caller: { student_id, question, answer_text,<br/>page, marks_detected, ocr_confidence, entities_found }`,
  },
  ner: {
    name: "Improved NER logic",
    caption: "<b>How the Week 4 entity finder tolerates OCR mistakes.</b> Four finders run over the same text; look-alike letters inside number positions are repaired before validation.",
    code: `flowchart LR
  T(["Raw OCR text<br/><small>'23DOO1 Q3 ... 7/1O'</small>"]) --> S1["Student ID finder"]
  T --> S2["Question finder<br/><small>Q + 1-2 digits</small>"]
  T --> S3["Marks finder<br/><small>n / n</small>"]
  T --> S4["Page finder<br/><small>'page' + number</small>"]
  S1 --> R["Repair look-alikes<br/><small>O→0 · l→1 · I→1 · S→5 · B→8</small>"]
  S2 --> R
  S3 --> R
  S4 --> V
  R --> V{"Valid after repair?<br/><small>IDs need ≥1 real digit</small>"}
  V -- "no" --> X(["Discard"])
  V -- "yes" --> C["All candidates<br/><small>sorted by position</small>"]
  C --> B[["Best per label = first on page<br/><small>23D001 · Q3 · 7/10</small>"]]`,
  },
  web: {
    name: "How this web app works",
    caption: "<b>Request flow between your browser and the local server.</b> Processing runs in a background thread so the page can show live progress.",
    code: `sequenceDiagram
  participant B as Browser (this page)
  participant S as Flask server (app/server.py)
  participant W as Background worker
  participant P as Pipeline (src/)
  B->>S: POST /api/digitize (file + options)
  S->>W: start job in a thread
  S-->>B: job_id
  loop every 0.6 s
    B->>S: GET /api/jobs/{id}
    S-->>B: stage, page x of n, log
  end
  W->>W: PDF → page images (PyMuPDF)
  W->>P: preprocess_image() (optional)
  W->>P: digitize_page() per page
  P-->>W: structured record
  W->>W: CER / WER if ground truth exists
  B->>S: GET /api/jobs/{id} → done
  S-->>B: pages + records + image URLs`,
  },
  eval: {
    name: "Evaluation flow",
    caption: "<b>How accuracy is measured.</b> OCR is scored against hand-typed ground truth; NER is scored against labelled examples.",
    code: `flowchart TD
  subgraph OCR ["OCR quality · evaluate.py"]
    A["data/raw_scans/*.jpg"] --> B["Tesseract OCR"]
    C["data/ground_truth/*.json<br/><small>hand-typed answers</small>"] --> D
    B --> D["jiwer compares texts"]
    D --> E(["CER and WER<br/><small>lower = better</small>"])
  end
  subgraph NERQ ["NER quality · compare_ner_approaches.py"]
    F["Labelled examples<br/><small>incl. noisy '23DOO1'</small>"] --> G["Week 3 spaCy NER"]
    F --> H["Week 4 improved NER"]
    G --> I["Precision · Recall · F1"]
    H --> I
    I --> J(["Side-by-side scorecard"])
  end`,
  },
};

const flowState = { current: "e2e", rendered: false, n: 0 };
$("#flowPills").innerHTML = Object.entries(FLOWS).map(([k, f]) => `<button class="pill ${k === "e2e" ? "on" : ""}" data-k="${k}">${f.name}</button>`).join("");
$("#flowPills").addEventListener("click", (e) => {
  const b = e.target.closest(".pill");
  if (!b) return;
  $$(".pill").forEach((x) => x.classList.toggle("on", x === b));
  renderFlow(b.dataset.k);
});

async function renderFlow(key) {
  flowState.current = key;
  const f = FLOWS[key];
  $("#flowCaption").innerHTML = f.caption;
  const canvas = $("#flowCanvas");
  if (!window.mermaid) { canvas.innerHTML = `<pre class="example">${esc(f.code)}</pre>`; return; }
  if (document.fonts) await document.fonts.ready;
  const css = getComputedStyle(document.documentElement);
  const v = (n) => css.getPropertyValue(n).trim();
  mermaid.initialize({
    startOnLoad: false, theme: "base", securityLevel: "loose",
    fontFamily: "Inter, system-ui, sans-serif",
    flowchart: { curve: "basis", padding: 14, htmlLabels: true },
    sequence: { mirrorActors: false, actorMargin: 60 },
    themeVariables: {
      fontSize: "14px", background: v("--surface"),
      primaryColor: v("--accent-soft"), primaryBorderColor: v("--accent"), primaryTextColor: v("--ink"),
      secondaryColor: v("--surface-2"), tertiaryColor: v("--surface-2"),
      lineColor: v("--muted"), textColor: v("--ink"), mainBkg: v("--accent-soft"), nodeBorder: v("--accent"),
      clusterBkg: v("--surface-2"), clusterBorder: v("--border-strong"), edgeLabelBackground: v("--surface"),
      actorBkg: v("--accent-soft"), actorBorder: v("--accent"), actorTextColor: v("--ink"), signalColor: v("--ink-2"), signalTextColor: v("--ink"),
      labelBoxBkgColor: v("--surface-2"), labelBoxBorderColor: v("--border-strong"), labelTextColor: v("--ink"), loopTextColor: v("--ink"),
      noteBkgColor: v("--warn-soft"), noteTextColor: v("--ink"), noteBorderColor: v("--warn"), activationBkgColor: v("--surface-2"),
    },
  });
  try {
    const { svg } = await mermaid.render("flow" + ++flowState.n, f.code);
    canvas.innerHTML = svg;
    flowState.rendered = true;
  } catch (err) {
    canvas.innerHTML = `<pre class="example">${esc(String(err))}</pre>`;
  }
}

/* ============================== tech stack ============================== */

const STACK = [
  {
    group: "Core pipeline", blurb: "The tools that actually turn a picture into structured text.",
    items: [
      { n: "Python 3", what: "Programming language", mono: "Py", c: "#3572A5", use: "Every part of the project is written in Python, chosen for its NLP and computer-vision libraries.", pts: ["Glue between OCR, NER and evaluation", "Each step is a small, importable module"], files: ["src/digitizer.py"] },
      { n: "Tesseract OCR 5", what: "Open-source text recognition engine (Google)", mono: "Tz", c: "#0f766e", use: "The engine that reads the characters off the page image. Chosen over TrOCR, which was no more accurate here and took minutes per page on CPU.", pts: ["LSTM model, page segmentation mode 4", "Returns every word with a confidence (0-100), averaged into ocr_confidence"], files: ["src/ocr_pipeline.py", "src/baseline_ocr.py", "src/segment.py"] },
      { n: "pytesseract", what: "Python wrapper for Tesseract", mono: "pT", c: "#14b8a6", use: "Lets Python call the Tesseract program and get results back as strings or dictionaries.", pts: ["image_to_string(): full text", "image_to_data(): words, positions, confidences"], files: ["src/digitizer.py", "src/evaluate.py"] },
      { n: "OpenCV", what: "Computer-vision library (cv2)", mono: "CV", c: "#5c3ee8", use: "Prepares the page photo before OCR.", pts: ["Week 7: red channel, lighting correction (divide by blurred background)", "Ruled-line detection with morphology + Hough transform, used to straighten the page and erase rules", "Week 1-2: Gaussian blur, adaptive threshold, minAreaRect deskew"], files: ["src/ocr_pipeline.py", "src/preprocess.py"] },
      { n: "Pillow (PIL)", what: "Image loading library", mono: "PIL", c: "#a16207", use: "Opens image files so they can be passed to Tesseract.", pts: ["Image.open() for JPG / PNG"], files: ["src/digitizer.py", "src/baseline_ocr.py"] },
      { n: "spaCy", what: "Industrial NLP library + en_core_web_sm", mono: "sp", c: "#09a3d5", use: "The Week 3 entity finder. An EntityRuler adds our own patterns in front of spaCy's statistical NER.", pts: ["Token-level regex patterns for STUDENT_ID, QUESTION_NUM, MARKS, PAGE_NUM", "Model loaded once and cached"], files: ["src/ner_extractor.py"] },
      { n: "pyspellchecker", what: "Dictionary spell checker (Peter Norvig's method)", mono: "abc", c: "#0e7490", use: "Optional clean-up that fixes OCR slips in ordinary words.", pts: ["Edit distance 1-2 candidates ranked by word frequency", "Boosts words already used correctly on the same page", "Off by default to preserve the student's own spelling"], files: ["src/ocr_pipeline.py"] },
      { n: "Python re (regex)", what: "Built-in pattern matching", mono: ".*", c: "#475569", use: "Powers the improved NER, question segmentation and text clean-up.", pts: ["Allows look-alike characters (O, l, I, S, B) where digits are expected", "Then repairs them to real digits"], files: ["src/ner_improved.py", "src/segment.py"] },
    ],
  },
  {
    group: "Evaluation", blurb: "How we prove (or disprove) that the pipeline works.",
    items: [
      { n: "jiwer", what: "Speech/OCR error-rate library", mono: "WER", c: "#be123c", use: "Computes CER and WER between the OCR output and the hand-typed ground truth.", pts: ["jiwer.cer(): character error rate", "jiwer.wer(): word error rate", "Also powers the Accuracy check in this UI"], files: ["src/evaluate.py", "app/server.py"] },
      { n: "Precision / Recall / F1", what: "Standard NER metrics", mono: "F1", c: "#9333ea", use: "Scores the entity finders on labelled examples, computed in plain Python.", pts: ["Precision: of what we found, how much was right", "Recall: of what existed, how much we found"], files: ["src/evaluate_ner.py", "src/compare_ner_approaches.py"] },
      { n: "scikit-learn", what: "Machine-learning toolkit", mono: "skl", c: "#f7931e", use: "Listed in requirements.txt for metric utilities. The current scripts compute their metrics by hand, so it is not imported yet.", pts: ["Available for future classification-report style metrics"], files: ["requirements.txt"] },
      { n: "JSON ground truth", what: "Hand-typed answer keys", mono: "{ }", c: "#64748b", use: "One JSON file per scanned page with the true student ID and answer text.", pts: ["Matched to scans by file name", "Used by evaluate.py and this UI's auto CER/WER"], files: ["data/ground_truth/aayush_page-01.json"] },
    ],
  },
  {
    group: "Web interface", blurb: "What powers this page. Added on top of the pipeline without changing it.",
    items: [
      { n: "Flask", what: "Lightweight Python web framework", mono: "Fl", c: "#1f2937", use: "Runs the local server: receives uploads, runs jobs in background threads, serves results and source files.", pts: ["/api/digitize, /api/jobs/<id>, /api/tree, /api/file, /api/score"], files: ["app/server.py"] },
      { n: "PyMuPDF (fitz)", what: "PDF rendering library", mono: "PDF", c: "#dc2626", use: "Turns each PDF page into a 300 DPI image so Tesseract can read it.", pts: ["No external Poppler install needed"], files: ["app/server.py"] },
      { n: "HTML · CSS · JavaScript", what: "Plain front-end, no build step", mono: "JS", c: "#ca8a04", use: "Tabs, drag-and-drop upload, live progress, entity highlighting, file tree.", pts: ["Light & dark themes", "Responsive down to phone width"], files: ["app/templates/index.html", "app/static/app.js", "app/static/style.css"] },
      { n: "Mermaid", what: "Text-to-diagram library", mono: "◇", c: "#ff3670", use: "Draws every flowchart and sequence diagram in the Flowcharts tab from plain text.", pts: [], files: ["app/static/app.js"] },
      { n: "highlight.js + marked", what: "Code highlighting & Markdown rendering", mono: "</>", c: "#2563eb", use: "Colours the code in the Architecture viewer and renders README.md.", pts: [], files: ["app/static/app.js"] },
    ],
  },
];

$("#stackGroups").innerHTML = STACK.map((g) => `
  <div class="stack-group">
    <h2>${g.group}</h2><p>${g.blurb}</p>
    <div class="stack-grid">${g.items.map((t) => `
      <div class="tech">
        <div class="tech-top"><div class="mono" style="background:${t.c}">${esc(t.mono)}</div><div><div class="tech-name">${t.n}</div><div class="tech-what">${t.what}</div></div></div>
        <p class="use">${t.use}</p>
        ${t.pts.length ? `<ul>${t.pts.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>` : ""}
        <div class="files">${t.files.map((f) => `<a class="file-link" data-open="${f}">${f.split("/").pop()}</a>`).join("")}</div>
      </div>`).join("")}
    </div>
  </div>`).join("");

/* ============================== architecture ============================== */

const LAYERS = [
  { p: "data", c: "#d97706", d: "Inputs: raw scans, cleaned scans and hand-typed ground truth." },
  { p: "src", c: "#3345d1", d: "The pipeline: preprocessing, OCR, segmentation, NER, evaluation, and the digitize_page() asset." },
  { p: "app", c: "#0f766e", d: "This web UI: Flask server + HTML/CSS/JS front-end." },
  { p: "results", c: "#be123c", d: "Where evaluation outputs are written." },
];
const treeState = { loaded: false, data: null, pending: null };

const ICON_DIR = `<svg class="ic" viewBox="0 0 24 24"><path d="M3 7a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/></svg>`;
const ICON_FILE = `<svg class="ic" viewBox="0 0 24 24"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/></svg>`;
const ICON_IMG = `<svg class="ic" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/></svg>`;

function countFiles(n) { return n.type === "file" ? 1 : (n.children || []).reduce((s, c) => s + countFiles(c), 0); }

async function loadTree() {
  treeState.loaded = true;
  const data = await (await fetch("/api/tree")).json();
  treeState.data = data;
  const byPath = Object.fromEntries((data.children || []).map((c) => [c.path, c]));
  $("#layers").innerHTML = LAYERS.map((l) => `<div class="layer" style="--c:${l.c}" data-layer="${l.p}"><div class="ln">${l.p}/</div><p>${l.d}</p><div class="cnt">${byPath[l.p] ? countFiles(byPath[l.p]) + " files" : ""}</div></div>`).join("");
  $$(".layer").forEach((el) => el.addEventListener("click", () => revealInTree(el.dataset.layer, true)));
  $("#tree").innerHTML = `<ul>${renderNode(data, true)}</ul>`;
  $("#tree").addEventListener("click", (e) => {
    const node = e.target.closest(".node");
    if (!node) return;
    const li = node.parentElement;
    if (node.classList.contains("dir")) li.classList.toggle("collapsed");
    else openFile(node.dataset.path);
  });
  if (treeState.pending) { openFile(treeState.pending); treeState.pending = null; }
}

function renderNode(n, root = false) {
  const isDir = n.type === "dir";
  const icon = isDir ? ICON_DIR : /\.(jpe?g|png|gif|webp|bmp)$/i.test(n.name) ? ICON_IMG : ICON_FILE;
  const collapsed = isDir && !root && !["src", "app"].includes(n.path);
  return `<li class="${collapsed ? "collapsed" : ""}">
    <div class="node ${isDir ? "dir" : "file"}" data-path="${esc(n.path)}" title="${esc(n.description)}">
      ${isDir ? '<span class="car">▶</span>' : '<span class="car"></span>'}${icon}
      <div><span class="nm">${esc(n.name)}${isDir ? "/" : ""}</span>${n.description ? `<span class="ds">${esc(n.description)}</span>` : ""}</div>
    </div>
    ${isDir && n.children?.length ? `<ul>${n.children.map((c) => renderNode(c)).join("")}</ul>` : ""}
  </li>`;
}

function revealInTree(path, scroll) {
  let node = null;
  $$("#tree .node").forEach((n) => { n.classList.toggle("on", n.dataset.path === path); if (n.dataset.path === path) node = n; });
  if (!node) return;
  let li = node.parentElement;
  if (node.classList.contains("dir")) li.classList.remove("collapsed");
  while (li && li.id !== "tree") { if (li.tagName === "LI" && li !== node.parentElement) li.classList.remove("collapsed"); li = li.parentElement; }
  if (scroll) node.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

$("#expandAll").addEventListener("click", (e) => {
  const anyCollapsed = $$("#tree li.collapsed").length > 0;
  $$("#tree li").forEach((li) => li.querySelector(":scope > ul") && li.classList.toggle("collapsed", !anyCollapsed));
  e.target.textContent = anyCollapsed ? "Collapse all" : "Expand all";
});

function openFileFromAnywhere(path) {
  showTab("arch");
  if (treeState.data) openFile(path); else treeState.pending = path;
}

const LANG = { py: "python", md: "markdown", json: "json", html: "xml", css: "css", js: "javascript", txt: "plaintext", gitignore: "bash", bat: "dos", sh: "bash", yml: "yaml", yaml: "yaml" };

// Split highlight.js HTML into lines while keeping spans that cross newlines intact
function splitHighlighted(html) {
  const lines = [];
  let open = [], cur = "";
  const re = /(<span[^>]*>)|(<\/span>)|(\n)|([^<\n]+|<)/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[1]) { open.push(m[1]); cur += m[1]; }
    else if (m[2]) { open.pop(); cur += m[2]; }
    else if (m[3]) { cur += "</span>".repeat(open.length); lines.push(cur); cur = open.join(""); }
    else cur += m[4];
  }
  lines.push(cur);
  return lines;
}

function codeTable(content, lang) {
  let html;
  try { html = window.hljs ? hljs.highlight(content, { language: lang, ignoreIllegals: true }).value : esc(content); }
  catch { html = esc(content); }
  const lines = splitHighlighted(html);
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  return `<table class="code-table hljs"><tbody>${lines.map((l, i) => `<tr><td class="ln">${i + 1}</td><td class="cl">${l || " "}</td></tr>`).join("")}</tbody></table>`;
}

async function openFile(path) {
  revealInTree(path, true);
  const r = await fetch("/api/file?path=" + encodeURIComponent(path));
  if (!r.ok) { $("#viewer").innerHTML = `<div class="empty"><p>Could not open ${esc(path)}</p></div>`; return; }
  const f = await r.json();
  const parts = f.path.split("/");
  $("#crumbs").innerHTML = parts.map((p, i) => (i === parts.length - 1 ? `<b>${esc(p)}</b>` : esc(p))).join(" / ") + ` <span class="muted">· ${(f.size / 1024).toFixed(1)} KB</span>`;
  $("#fileDesc").classList.toggle("hidden", !f.description);
  $("#fileDesc").textContent = f.description;
  const copyBtn = $("#copyCode");
  copyBtn.classList.toggle("hidden", f.kind !== "text");
  copyBtn.onclick = () => copyText(f.content, "File copied");

  const viewer = $("#viewer");
  if (f.kind === "image") viewer.innerHTML = `<div class="img-view"><img src="${f.url}" alt="${esc(f.name)}"></div>`;
  else if (f.kind === "pdf") viewer.innerHTML = `<iframe src="${f.url}" style="width:100%;height:75vh;border:0"></iframe>`;
  else if (f.kind === "binary") viewer.innerHTML = `<div class="empty"><p>Binary file, no preview available.</p></div>`;
  else {
    const ext = f.name.includes(".") ? f.name.split(".").pop().toLowerCase() : f.name.toLowerCase();
    let content = f.content;
    if (ext === "json") { try { content = JSON.stringify(JSON.parse(content), null, 2); } catch {} }
    if (ext === "md" && window.marked) {
      viewer.innerHTML = `<div class="viewer-head" style="background:none;border:0;padding:12px 16px 0"><div class="segmented" id="mdMode"><button class="on" data-v="r">Rendered</button><button data-v="s">Source</button></div></div><div id="mdBody"></div>`;
      const show = (mode) => {
        $("#mdBody").innerHTML = mode === "r" ? `<div class="md">${marked.parse(content)}</div>` : codeTable(content, "markdown");
        if (mode === "r" && window.hljs) $$("#mdBody pre code").forEach((c) => hljs.highlightElement(c));
      };
      $("#mdMode").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; $$("#mdMode button").forEach((x) => x.classList.toggle("on", x === b)); show(b.dataset.v); });
      show("r");
    } else {
      viewer.innerHTML = content.trim() ? codeTable(content, LANG[ext] || "plaintext") : `<div class="empty"><p class="muted">This file is empty.${f.name === ".gitkeep" ? "<br>It only exists so Git keeps the (otherwise empty) folder." : ""}</p></div>`;
    }
  }
  viewer.scrollTop = 0;
}

/* ============================== boot ============================== */

const TAB_NAMES = ["digitize", "pipeline", "flow", "stack", "arch"];
const tabFromHash = () => { const t = location.hash.slice(1); if (TAB_NAMES.includes(t)) showTab(t); };
window.addEventListener("hashchange", tabFromHash);
tabFromHash();
applyTheme();
