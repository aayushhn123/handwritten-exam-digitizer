import json
import os
import jiwer
import pytesseract
from PIL import Image
from ocr_pipeline import ocr_page


def load_ground_truth_text(ground_truth_folder, filename):
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(ground_truth_folder, base_name + ".json")
    with open(json_path) as f:
        gt = json.load(f)
    combined = " ".join(a["answer_text"] for a in gt["answers"])
    return combined


def run_ocr(image_path, enhance=False):
    if enhance:
        raw_text, _ = ocr_page(image_path, enhance=True)
    else:
        img = Image.open(image_path)
        raw_text = pytesseract.image_to_string(img)
    return " ".join(raw_text.split())


def evaluate_folder(image_folder, ground_truth_folder, enhance=False):
    results = []

    for filename in sorted(os.listdir(image_folder)):
        if not filename.endswith((".jpg", ".png", ".jpeg")):
            continue

        image_path = os.path.join(image_folder, filename)
        predicted_text = run_ocr(image_path, enhance=enhance)

        try:
            ground_truth_text = load_ground_truth_text(ground_truth_folder, filename)
        except FileNotFoundError:
            print("no ground truth for", filename, "- skipping")
            continue

        cer = jiwer.cer(ground_truth_text, predicted_text)
        wer = jiwer.wer(ground_truth_text, predicted_text)

        results.append({
            "file": filename,
            "cer": round(cer, 3),
            "wer": round(wer, 3)
        })

        print(filename, "CER:", round(cer, 3), "WER:", round(wer, 3))

    if results:
        avg_cer = sum(r["cer"] for r in results) / len(results)
        avg_wer = sum(r["wer"] for r in results) / len(results)
        print("\nAverage CER:", round(avg_cer, 3))
        print("Average WER:", round(avg_wer, 3))

    return results


if __name__ == "__main__":
    print("evaluating raw scans (no preprocessing)")
    evaluate_folder("data/raw_scans", "data/ground_truth")

    print("\nevaluating raw scans with week 7 enhancement (ocr_pipeline.py)")
    evaluate_folder("data/raw_scans", "data/ground_truth", enhance=True)
