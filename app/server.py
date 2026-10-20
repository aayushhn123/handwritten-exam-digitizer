"""
Web UI for the Handwritten Exam Digitizer.

Serves a single-page interface where a user can upload a scanned PDF or an
image of a handwritten answer sheet and get back the digitized text. Every
page is pushed through the project's own reusable asset,
src/digitizer.py -> digitize_page(), so the UI shows exactly what the
pipeline produces.

Run from the project root:
    python app/server.py
then open http://127.0.0.1:5000
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import cv2  # noqa: E402
import pymupdf as fitz  # noqa: E402
import jiwer  # noqa: E402
import pytesseract  # noqa: E402


def _configure_tesseract():
    # On Windows, Tesseract is usually not on PATH after install, so point
    # pytesseract at the default install location (or TESSERACT_CMD if set).
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in candidates:
        if path and Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            return path
    return None


TESSERACT_PATH = _configure_tesseract()

from digitizer import digitize_page  # noqa: E402
from ocr_pipeline import enhance_page  # noqa: E402
from preprocess import preprocess_image  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024

WORK_DIR = Path(tempfile.gettempdir()) / "exam_digitizer_ui"
WORK_DIR.mkdir(exist_ok=True)

MAX_PAGES = 40
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")
jobs = {}
jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Plain-language descriptions shown in the "Project Architecture" tab
# ---------------------------------------------------------------------------

DESCRIPTIONS = {
    "": "The project root. Everything needed to run, test and reuse the digitizer lives here.",
    "README.md": "The project's front page: what it does, how to install it, and week-by-week progress notes.",
    "requirements.txt": "The list of Python libraries to install with `pip install -r requirements.txt`.",
    ".gitignore": "Tells Git which files NOT to upload (e.g. scanned images, Python cache files).",
    "data": "All the input data: original scans, cleaned scans and the hand-typed correct answers.",
    "data/raw_scans": "Original photos / scans of handwritten answer sheets, exactly as captured.",
    "data/preprocessed": "The same scans after cleaning (grayscale, threshold, straightened) by preprocess.py.",
    "data/ground_truth": "Hand-typed 'correct answers' for each scan. Used to measure how accurate the OCR is.",
    "data/ground_truth/aayush_page-01.json": "Manually transcribed text for Aayush's page 1 (student E007). The answer key for evaluation.",
    "data/ground_truth/rish_page-1.json": "Manually transcribed text for Rish's page 1. The answer key for evaluation.",
    "src": "The heart of the project: every step of the pipeline as small, separate Python files.",
    "src/preprocess.py": "Week 1-2 image cleaning (grayscale, blur, black/white threshold, deskew). Replaced by ocr_pipeline.py after Week 5 showed it hurt accuracy.",
    "src/segment.py": "Splits a page into question-wise chunks by spotting words like 'Q1', 'Q2' in the OCR output.",
    "src/baseline_ocr.py": "Step 2 - Runs Tesseract OCR on an image and returns the text plus an average confidence score.",
    "src/ner_extractor.py": "Step 3 (v1) - Finds Student ID, Question no., Marks and Page no. using spaCy pattern rules.",
    "src/ner_improved.py": "Step 3 (v2) - Smarter finder that tolerates OCR mistakes like 'O' instead of '0' and keeps every candidate.",
    "src/process_with_ner.py": "Early glue code (Week 3): OCR + spaCy NER on one page, combined into one record.",
    "src/digitizer.py": "THE reusable asset. One function, digitize_page(), runs OCR + NER and returns a clean structured record.",
    "src/ocr_pipeline.py": "Week 7 - Smarter OCR: removes coloured rules, shadows and ruled lines, straightens the page, then cleans the text. Cut errors from 43% to 19%.",
    "src/evaluate.py": "Measures OCR quality: CER and WER against ground truth (jiwer), for the original and the Week 7 enhanced OCR.",
    "src/evaluate_ner.py": "Measures NER quality (precision, recall, F1) on small labelled examples.",
    "src/compare_ner_approaches.py": "Side-by-side scorecard: Week 3 spaCy NER vs Week 4 improved NER.",
    "results": "Where evaluation outputs are saved.",
    "app": "This web interface. A small Flask server plus the HTML/CSS/JS you are looking at right now.",
    "app/server.py": "The web server. Accepts uploads, turns PDFs into page images, calls digitize_page() and sends results to the browser.",
    "app/templates": "HTML templates rendered by Flask.",
    "app/templates/index.html": "The page layout: tabs for Digitize, Pipeline, Flowcharts, Tech Stack and Architecture.",
    "app/static": "Static files (styles and scripts) the browser downloads.",
    "app/static/style.css": "All the styling: colours, fonts, cards, tabs, light & dark mode.",
    "app/static/app.js": "All the interactivity: uploading, progress polling, results, file tree, code viewer and diagrams.",
}

HIDDEN = {".git", "__pycache__", ".idea", ".vscode", ".claude", "node_modules", ".DS_Store"}
TEXT_EXTS = {".py", ".md", ".txt", ".json", ".html", ".css", ".js", ".gitignore", ".gitkeep", ".bat", ".sh", ".toml", ".cfg", ".yml", ".yaml"}


def _safe_path(rel):
    target = (ROOT / rel).resolve()
    if target != ROOT and ROOT not in target.parents:
        abort(403)
    if any(part in HIDDEN for part in target.relative_to(ROOT).parts):
        abort(403)
    if not target.exists():
        abort(404)
    return target


def _build_tree(path):
    rel = path.relative_to(ROOT).as_posix() if path != ROOT else ""
    node = {
        "name": path.name if path != ROOT else ROOT.name,
        "path": rel,
        "type": "dir" if path.is_dir() else "file",
        "description": DESCRIPTIONS.get(rel, ""),
    }
    if path.is_dir():
        children = []
        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name in HIDDEN or child.name.endswith(".pyc"):
                continue
            children.append(_build_tree(child))
        node["children"] = children
    else:
        node["size"] = path.stat().st_size
    return node


# ---------------------------------------------------------------------------
# Pipeline job runner
# ---------------------------------------------------------------------------

def _ground_truth_for(stem):
    gt_path = ROOT / "data" / "ground_truth" / (stem + ".json")
    if not gt_path.exists():
        return None
    with open(gt_path, encoding="utf-8") as f:
        gt = json.load(f)
    return " ".join(a["answer_text"] for a in gt.get("answers", []))


def _score(reference, hypothesis):
    ref = " ".join(reference.split())
    hyp = " ".join(hypothesis.split())
    if not ref:
        return None
    return {"cer": round(jiwer.cer(ref, hyp), 3), "wer": round(jiwer.wer(ref, hyp), 3)}


def _update(job_id, **fields):
    with jobs_lock:
        jobs[job_id].update(fields)


def _log(job_id, message):
    with jobs_lock:
        jobs[job_id]["log"].append({"t": round(time.time() - jobs[job_id]["started"], 2), "msg": message})


def _run_job(job_id, input_path, original_name, options):
    job_dir = WORK_DIR / job_id
    try:
        ext = input_path.suffix.lower()
        page_images = []

        _update(job_id, stage="render")
        t0 = time.time()
        if ext == ".pdf":
            doc = fitz.open(str(input_path))
            total = min(len(doc), MAX_PAGES)
            _log(job_id, f"PDF opened: {len(doc)} page(s)" + (f", processing first {MAX_PAGES}" if len(doc) > MAX_PAGES else ""))
            _update(job_id, total=total)
            zoom = options["dpi"] / 72.0
            for i in range(total):
                _update(job_id, page=i + 1)
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
                out = job_dir / f"page_{i + 1:03d}.png"
                pix.save(str(out))
                page_images.append(out)
            doc.close()
            _log(job_id, f"Rendered {total} page(s) to images at {options['dpi']} DPI")
        else:
            out = job_dir / ("page_001" + ext)
            shutil.copy(input_path, out)
            page_images.append(out)
            _update(job_id, total=1)
            _log(job_id, "Image received - no rendering needed")
        render_ms = int((time.time() - t0) * 1000)

        gt_text = _ground_truth_for(Path(original_name).stem) if len(page_images) == 1 else None

        results = []
        for idx, img_path in enumerate(page_images, start=1):
            _update(job_id, page=idx)
            ocr_input = img_path
            enhanced_name = None
            pre_ms = 0
            mode = options["enhance"]

            if mode == "smart":
                # save what Tesseract will actually see, for the preview toggle
                _update(job_id, stage="preprocess")
                t1 = time.time()
                enhanced_name = f"page_{idx:03d}_enhanced.png"
                cv2.imwrite(str(job_dir / enhanced_name), enhance_page(str(img_path)))
                pre_ms = int((time.time() - t1) * 1000)
                _log(job_id, f"Page {idx}: enhanced (red channel, lighting, straighten, rules erased) ({pre_ms} ms)")
            elif mode == "legacy":
                _update(job_id, stage="preprocess")
                t1 = time.time()
                cleaned = preprocess_image(str(img_path))
                ocr_input = job_dir / f"page_{idx:03d}_clean.png"
                cv2.imwrite(str(ocr_input), cleaned)
                enhanced_name = ocr_input.name
                pre_ms = int((time.time() - t1) * 1000)
                _log(job_id, f"Page {idx}: cleaned with Week 1-2 preprocess.py ({pre_ms} ms)")

            _update(job_id, stage="ocr")
            t2 = time.time()
            record = digitize_page(str(ocr_input), page_number=idx, use_improved_ner=options["improved_ner"],
                                   enhance=(mode == "smart"), spell_correct=options["spell"])
            dig_ms = int((time.time() - t2) * 1000)
            _log(job_id, f"Page {idx}: OCR + NER done - confidence {int(record['ocr_confidence'] * 100)}%, "
                         f"{len(record['entities_found'])} entit{'y' if len(record['entities_found']) == 1 else 'ies'} ({dig_ms} ms)")

            h, w = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE).shape[:2]
            page = {
                "page": idx,
                "image_url": f"/api/jobs/{job_id}/image/{img_path.name}",
                "enhanced_url": f"/api/jobs/{job_id}/image/{enhanced_name}" if enhanced_name else None,
                "width": w,
                "height": h,
                "record": record,
                "timings": {"preprocess_ms": pre_ms, "digitize_ms": dig_ms},
                "words": len(record["answer_text"].split()),
                "chars": len(record["answer_text"]),
            }
            if gt_text:
                page["accuracy"] = _score(gt_text, record["answer_text"])
                if page["accuracy"]:
                    _log(job_id, f"Ground truth found - CER {page['accuracy']['cer']}, WER {page['accuracy']['wer']}")
            results.append(page)
            with jobs_lock:
                jobs[job_id]["pages"] = list(results)

        _update(job_id, stage="assemble")
        _log(job_id, "Structured records assembled")
        _update(job_id, status="done", stage="done", render_ms=render_ms, finished=time.time())
    except Exception as exc:  # surface any failure to the UI
        _log(job_id, f"Error: {exc}")
        _update(job_id, status="error", error=str(exc))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    version = None
    if TESSERACT_PATH:
        try:
            version = str(pytesseract.get_tesseract_version())
        except Exception:
            version = None
    return jsonify({"tesseract": bool(version), "tesseract_version": version, "tesseract_path": TESSERACT_PATH})


@app.route("/api/samples")
def samples():
    folder = ROOT / "data" / "raw_scans"
    items = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in IMAGE_EXTS + (".pdf",):
            items.append({
                "name": p.name,
                "has_ground_truth": (ROOT / "data" / "ground_truth" / (p.stem + ".json")).exists(),
                "thumb": f"/api/raw?path=data/raw_scans/{p.name}",
            })
    return jsonify(items)


def _start_job(input_path, original_name, options):
    job_id = input_path.parent.name
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id, "status": "running", "stage": "upload", "page": 0, "total": 0,
            "pages": [], "log": [], "file": original_name, "options": options,
            "started": time.time(), "error": None,
        }
    _log(job_id, f"Received '{original_name}'")
    threading.Thread(target=_run_job, args=(job_id, input_path, original_name, options), daemon=True).start()
    return job_id


def _options_from(form):
    dpi = int(form.get("dpi", 300))
    return {
        "improved_ner": form.get("ner", "improved") == "improved",
        "enhance": form.get("enhance", "smart") if form.get("enhance") in ("smart", "raw", "legacy") else "smart",
        "spell": form.get("spell", "false") == "true",
        "dpi": max(100, min(dpi, 400)),
    }


@app.route("/api/digitize", methods=["POST"])
def digitize():
    if not TESSERACT_PATH:
        return jsonify({"error": "Tesseract OCR is not installed or could not be found."}), 500
    options = _options_from(request.form)
    sample = request.form.get("sample")

    job_id = uuid.uuid4().hex[:12]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True)

    if sample:
        src_path = (ROOT / "data" / "raw_scans" / Path(sample).name)
        if not src_path.exists():
            return jsonify({"error": "Sample not found"}), 404
        dest = job_dir / ("input" + src_path.suffix.lower())
        shutil.copy(src_path, dest)
        name = src_path.name
    else:
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "No file uploaded"}), 400
        ext = Path(f.filename).suffix.lower()
        if ext not in IMAGE_EXTS + (".pdf",):
            return jsonify({"error": f"Unsupported file type '{ext}'. Upload a PDF or an image."}), 400
        dest = job_dir / ("input" + ext)
        f.save(dest)
        name = f.filename

    return jsonify({"job_id": _start_job(dest, name, options)})


@app.route("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            abort(404)
        return jsonify(job)


@app.route("/api/jobs/<job_id>/image/<name>")
def job_image(job_id, name):
    path = (WORK_DIR / job_id / Path(name).name)
    if not path.exists():
        abort(404)
    return send_file(path)


@app.route("/api/score", methods=["POST"])
def score():
    data = request.get_json(force=True)
    result = _score(data.get("reference", ""), data.get("hypothesis", ""))
    if result is None:
        return jsonify({"error": "Reference text is empty"}), 400
    return jsonify(result)


@app.route("/api/tree")
def tree():
    return jsonify(_build_tree(ROOT))


@app.route("/api/file")
def file_content():
    path = _safe_path(request.args.get("path", ""))
    if path.is_dir():
        abort(400)
    rel = path.relative_to(ROOT).as_posix()
    ext = path.suffix.lower() or path.name.lower()
    info = {"path": rel, "name": path.name, "size": path.stat().st_size, "description": DESCRIPTIONS.get(rel, "")}
    if ext in IMAGE_EXTS:
        info.update(kind="image", url=f"/api/raw?path={rel}")
    elif ext == ".pdf":
        info.update(kind="pdf", url=f"/api/raw?path={rel}")
    elif ext in TEXT_EXTS or path.stat().st_size < 200_000:
        try:
            info.update(kind="text", content=path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            info.update(kind="binary")
    else:
        info.update(kind="binary")
    return jsonify(info)


@app.route("/api/raw")
def raw_file():
    path = _safe_path(request.args.get("path", ""))
    if path.is_dir():
        abort(400)
    return send_file(path)


if __name__ == "__main__":
    print("Tesseract:", TESSERACT_PATH or "NOT FOUND")
    print("Open http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
