from baseline_ocr import run_tesseract_baseline
from ner_extractor import build_ner_pipeline, extract_entities


def process_page_with_ner(image_path, page_number, nlp=None):
    if nlp is None:
        nlp = build_ner_pipeline()

    raw_text, confidence = run_tesseract_baseline(image_path)
    entities = extract_entities(nlp, raw_text)

    student_id = None
    question_num = None
    marks = None

    for ent in entities:
        if ent["label"] == "STUDENT_ID" and student_id is None:
            student_id = ent["text"]
        if ent["label"] == "QUESTION_NUM" and question_num is None:
            question_num = ent["text"]
        if ent["label"] == "MARKS" and marks is None:
            marks = ent["text"]

    result = {
        "student_id": student_id,
        "question": question_num,
        "answer_text": raw_text,
        "page": page_number,
        "marks_detected": marks,
        "confidence": confidence,
        "all_entities": entities
    }

    return result


if __name__ == "__main__":
    import json
    result = process_page_with_ner("data/preprocessed/page_001.jpg", 1)
    print(json.dumps(result, indent=2))
