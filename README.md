# Handwritten Examination Digitizer

SNLP Course Project 2026 — AI University: Building Reusable NLP Assets
Group 1 — Roll Numbers E001, E002, E004, E005, E007

## Problem

University examinations are still largely handwritten on paper. Before any
automated evaluation of descriptive answers can happen, the handwritten
answer sheets need to be converted into structured, machine-readable text.
This project builds that conversion pipeline.

## What this does

Takes a scanned handwritten examination answer sheet and produces a
structured, question-wise digital transcription.

Input: scanned answer sheet (image or PDF page)

Output:

```json
{
  "student_id": "23D001",
  "question": "Q3",
  "answer_text": "...",
  "page": 4,
  "confidence": 0.91
}
```

## Folder structure

```
handwritten-exam-digitizer/
  data/
    raw_scans/              scanned answer sheet images
    preprocessed/            cleaned images after preprocessing
    ground_truth/            manually transcribed labels, one JSON per page
  src/
    preprocess.py              image cleaning and deskewing                 (Week 1-2)
    segment.py                  regex-based question segmentation            (Week 1-2)
    baseline_ocr.py             Tesseract OCR baseline                       (Week 1-2)
    make_split.py               train/test split                            (Week 1-2)
    evaluate.py                  CER and WER evaluation                       (Week 1-2)
    run_pipeline.py              full baseline pipeline runner                (Week 1-2)
    ner_extractor.py            spaCy rule-based NER component                (Week 3)
    process_with_ner.py          OCR + NER combined page processor            (Week 3)
    evaluate_ner.py               NER precision/recall/F1 evaluation          (Week 3)
    ner_improved.py              OCR-noise tolerant, multi-candidate NER       (Week 4, new)
    compare_ner_approaches.py    baseline vs improved NER comparison           (Week 4, new)
  results/                   evaluation outputs
  requirements.txt
```

## How to run

Install dependencies:

```
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Tesseract also needs to be installed on the system:

```
sudo apt-get install tesseract-ocr
```

Put scanned pages in `data/raw_scans/` and matching ground-truth JSON files
in `data/ground_truth/`, then run the baseline pipeline:

```
cd src
python run_pipeline.py
```

## Week 3 — Core NLP component (rule-based NER)

Replaces plain regex question-marker detection with a proper Named Entity
Recognition component built on spaCy's EntityRuler, extracting STUDENT_ID,
QUESTION_NUM, MARKS and PAGE_NUM from OCR text.

```
cd src
python process_with_ner.py
python evaluate_ner.py
```

## Week 4 — Improved approach (OCR-noise tolerant NER)

The Week 3 rule-based extractor takes the single first match per entity
label and has no tolerance for common OCR misreads (O read as 0, l read as
1, and so on). Week 4 introduces an improved extractor that:

- normalizes common OCR character confusions within digit runs
  (O/o to 0, l/I to 1, S to 5, B to 8)
- finds every candidate match per label, not just the first one
- ranks and selects the best candidate per label by position

Run the comparison between the Week 3 baseline and the Week 4 improved
approach on the same evaluation set:

```
cd src
python compare_ner_approaches.py
```

This prints precision, recall and F1 for both approaches side by side.

## Why this is the improved approach, not a different one

A genuinely new NER model (statistical or transformer-based) needs a
reasonably sized hand-labeled dataset to train on, which is not yet
available for this project since real scanned answer sheets are still
being collected. Instead of fitting a flashy but under-trained model, Week
4 focuses on a real, verifiable weakness in the Week 3 baseline (OCR noise
on handwritten-adjacent text) and fixes it directly, with before/after
numbers to show it. A statistical or transformer-based NER model remains
the planned Week 5+ direction once enough labeled real scans exist.

## Reusability — how another group can use this

```python
from process_with_ner import process_page_with_ner

result = process_page_with_ner("data/preprocessed/page_004.jpg", 4)
```

This returns a structured record in the JSON format shown above. Group 2
(AI Exam Grader) can consume this directly as their input.

## Status

Pipeline code (OCR baseline, rule-based NER, OCR-noise-tolerant improved
NER) is complete and runnable. Real scanned data collection is in
progress.
