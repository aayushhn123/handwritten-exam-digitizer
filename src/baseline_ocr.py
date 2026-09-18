import pytesseract
from PIL import Image
from segment import segment_questions


def run_tesseract_baseline(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    confidences = [int(c) for c in data["conf"] if c != "-1"]
    avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0

    return text.strip(), round(avg_confidence, 2)


def process_page(image_path, student_id, page_number):
    segments = segment_questions(image_path)
    full_text, confidence = run_tesseract_baseline(image_path)

    results = []
    for seg in segments:
        line_words = [w[2] for w in seg["text_region_lines"]]
        answer_text = " ".join(line_words)
        results.append({
            "student_id": student_id,
            "question": seg["question"],
            "answer_text": answer_text,
            "page": page_number,
            "confidence": confidence
        })

    return results


if __name__ == "__main__":
    import json
    result = process_page("data/preprocessed/page_001.jpg", "23D001", 1)
    print(json.dumps(result, indent=2))
