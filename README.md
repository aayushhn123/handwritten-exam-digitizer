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

## Approach

Baseline: image preprocessing (grayscale, denoising, adaptive thresholding,
deskewing) followed by Tesseract OCR and rule-based question segmentation
that looks for markers like "Q1", "Q2" in the page.

Improved approach (planned): a transformer-based handwritten text
recognition model, compared against the baseline using Character Error Rate
(CER) and Word Error Rate (WER).

## Folder structure

```
handwritten-exam-digitizer/
  data/
    raw_scans/         scanned answer sheet images go here
    preprocessed/       cleaned images after preprocessing
    ground_truth/       manually transcribed labels, one JSON per page
  src/
    preprocess.py        image cleaning and deskewing
    segment.py            question segmentation
    baseline_ocr.py       Tesseract OCR baseline
    make_split.py         train/test split
    evaluate.py            CER and WER evaluation
    run_pipeline.py        runs the full pipeline end to end
  results/               evaluation outputs get saved here
  requirements.txt
```

## How to run

Install dependencies:

```
pip install -r requirements.txt
```

Tesseract also needs to be installed on the system:

```
sudo apt-get install tesseract-ocr
```

Put scanned pages in `data/raw_scans/` and matching ground-truth JSON files
in `data/ground_truth/` (see the sample file already there for the format),
then run:

```
cd src
python run_pipeline.py
```

This preprocesses all scans, creates a train/test split, and prints CER and
WER for the baseline on the test set.

## Ground truth format

Each page needs a matching JSON file in `data/ground_truth/`, named the same
as the image but with a `.json` extension. For example `page_001.jpg` needs
`page_001.json`:

```json
{
  "student_id": "23D001",
  "answers": [
    {"question": "Q1", "answer_text": "manually transcribed answer text"},
    {"question": "Q2", "answer_text": "manually transcribed answer text"}
  ]
}
```

## Reusability — how another group can use this

Another application only needs to call `process_page` from
`src/baseline_ocr.py`:

```python
from baseline_ocr import process_page

result = process_page("data/preprocessed/page_004.jpg", "23D001", 4)
```

This returns a list of structured question-answer records in the JSON
format shown above. Group 2 (AI Exam Grader) can consume this directly as
their input, without needing to read the OCR or segmentation logic.

## Status

Pipeline code is complete and runnable. Real scanned data collection is in
progress; sample ground-truth format is included so the pipeline can be run
as soon as scans are available.
