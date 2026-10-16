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
  results/                   evaluation outputs
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
