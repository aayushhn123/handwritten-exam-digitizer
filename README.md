# Handwritten Examination Digitizer

SNLP Course Project 2026 — AI University: Building Reusable NLP Assets
Group 1 — Roll Numbers E001, E002, E004, E005, E007

## What this does

Takes a scanned or photographed handwritten examination answer sheet and
produces a structured, question-wise digital transcription.

```python
from digitizer import digitize_page

result = digitize_page("scans/page_004.jpg", page_number=4)
```

Output:

```json
{
  "student_id": "E007",
  "question": "Q1",
  "answer_text": "...",
  "page": 4,
  "marks_detected": null,
  "ocr_confidence": 0.54,
  "entities_found": [...]
}
```

## Folder structure

```
handwritten-exam-digitizer/
  data/
    raw_scans/              scanned/photographed answer sheet images
    preprocessed/            cleaned images after preprocessing
    ground_truth/            manually transcribed labels, one JSON per page
  src/
    preprocess.py              image cleaning and deskewing                 (Week 1-2)
    segment.py                  regex-based question segmentation            (Week 1-2)
    baseline_ocr.py             Tesseract OCR baseline                       (Week 1-2)
    evaluate.py                  CER and WER evaluation                       (Week 1-2, updated)
    ner_extractor.py            spaCy rule-based NER component                (Week 3)
    ner_improved.py              OCR-noise tolerant, multi-candidate NER       (Week 4)
    compare_ner_approaches.py   baseline vs improved NER comparison            (Week 4)
    digitizer.py                 reusable digitize_page() asset                (Week 6, new)
    ocr_pipeline.py              image enhancement + text clean-up for OCR     (Week 7, new)
  results/                   evaluation outputs
  app/                       web UI (Flask server + HTML/CSS/JS)
    server.py                 upload, PDF -> page images, calls digitize_page()
    templates/index.html      page layout and tabs
    static/                   styles and scripts
  requirements.txt
```

## How to run

```
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Tesseract also needs to be installed on the system:

```
sudo apt-get install tesseract-ocr
```

Evaluate OCR quality against ground truth:

```
cd src
python evaluate.py
```

## Web UI

A local web interface for trying the pipeline without writing code:

```
python app/server.py
```

Then open http://127.0.0.1:5000. It has five tabs:

- **Digitize**: upload a scanned PDF or a photo (or pick a sample from
  `data/raw_scans/`), watch each pipeline step run, then read the text with
  detected entities highlighted. You can download `.txt` / `.json`, and see
  CER/WER automatically when ground truth exists (or paste your own).
- **How it works**: each pipeline step in plain language, with technical
  details and links to the code.
- **Flowcharts**: end-to-end flow, inside `digitize_page()`, improved NER
  logic, web request flow, and evaluation flow.
- **Tech stack**: what each library is and what it does in this project.
- **Architecture**: the folder tree with descriptions and an in-browser
  code viewer with syntax highlighting.

On Windows, install Tesseract with
`winget install UB-Mannheim.TesseractOCR`. The server finds it in
`C:\Program Files\Tesseract-OCR` automatically, or set `TESSERACT_CMD`.
The UI loads fonts, highlight.js, marked and Mermaid from CDNs, so the
diagrams and code colouring need an internet connection.

## Week 5 — Evaluation and error analysis

Weeks 1-4 used short hand-built text snippets to test the pipeline, since
real scanned pages were still being collected. Week 5 runs the pipeline on
real handwritten answer sheets (photographed, not clean digital scans) and
reports real CER/WER plus a documented set of real failure cases, including
a genuine, previously unknown issue: the Week 1-2 preprocessing step
(adaptive thresholding and deskewing) made OCR accuracy worse, not better,
on photographed notebook pages, because it over-binarizes ruled lines so
they visually merge with letters sitting on them. See the full submission
document for the complete error analysis table.

## Week 6 — Asset engineering

The pipeline is now wrapped as a single reusable function in
`src/digitizer.py`:

```python
from digitizer import digitize_page

result = digitize_page(image_path, page_number=None, use_improved_ner=True)
```

- Structured input: one image path, with optional page number and a toggle
  between the Week 3 and Week 4 NER approaches.
- Structured output: a dict with `student_id`, `question`, `answer_text`,
  `page`, `marks_detected`, `ocr_confidence`, and the full list of entity
  candidates found (`entities_found`), for manual review of low-confidence
  pages.
- Confidence scores: `ocr_confidence` is Tesseract's own average per-word
  confidence for the page, so a caller (such as Group 2's AI Exam Grader)
  can decide whether to trust a page automatically or flag it for a human
  to check.
- Full docstring in the function itself (`help(digitize_page)` after
  importing it).

## Week 7 — Accuracy improvements

The Week 5 finding (thresholding hurts photographed ruled pages) led to a new
OCR front end, `src/ocr_pipeline.py`, now used by `digitize_page()` by
default:

1. read the red colour channel only (pink/red rules vanish, ink stays dark)
2. divide out uneven lighting (shadows, phone-photo gradients)
3. straighten the page using the angle of the ruled lines
4. erase the ruled lines without hard black/white thresholding
5. upscale 1.5x, then Tesseract (`--psm 4`)
6. strip rule debris (`____`, `—`, `|`) from the text
7. optional dictionary spelling correction (off by default, because it also
   "fixes" the student's own spelling; never touches names, IDs or acronyms)

| Page (CER / WER)  | Original OCR      | Week 7            |
|-------------------|-------------------|-------------------|
| aayush_page-01    | 0.397 / 0.490     | 0.037 / 0.163     |
| rish_page-1       | 0.455 / 0.964     | 0.341 / 0.969     |
| Average           | 0.426 / 0.727     | 0.189 / 0.566     |

Run `python src/evaluate.py` to reproduce both columns. About one second
per page.

`data/ground_truth/aayush_page-01.json` was also completed: it previously
stopped mid-page, so correctly read text after that point was counted as
errors.

Also tried and rejected (measured on the same pages):

- Microsoft TrOCR (transformer trained on handwriting): similar accuracy
  (CER 0.052 neat / 0.37 cursive) but 3-5 minutes per page on CPU.
- OCR line by line (`--psm 7`): worse (CER 0.21+ on the neat page).
- Tesseract `tessdata_best` model: no better, twice as slow.

NER (`ner_improved.py`) now also handles real OCR mistakes seen on these
pages: `QL.` -> Q1, `@1)` at the start of a line -> Q1, an ID straight after
"Roll no" / "ID" even with no real digit (`EO13` -> E013), and dates such as
5/11/2024 are no longer read as marks. `compare_ner_approaches.py` reports a
separate test set of these cases (F1 0.308 for Week 3, 1.0 now; the set is
small and comes from the same pages the rules were written for).

Known limit: Tesseract still misreads some handwritten IDs entirely (E007
-> "Eool", E013 -> "Ford"), so `student_id` can be `None` on cursive pages.

```python
result = digitize_page(path, enhance=True, spell_correct=False)  # defaults
result = digitize_page(path, enhance=False)  # original Week 1-6 behaviour
```

## Reusability — how another group can use this

```python
from digitizer import digitize_page

result = digitize_page("data/preprocessed/page_004.jpg", page_number=4)
```

Group 2 (AI Exam Grader) can consume this directly as their input.

## Status

Pipeline code (OCR baseline, rule-based NER, OCR-noise-tolerant improved
NER, reusable digitize_page asset) is complete and has been run on real
handwritten pages, not only synthetic text samples. Further real data
collection from the rest of the group is in progress for a larger
evaluation set.
