import json
import os
import jiwer
from baseline_ocr import run_tesseract_baseline


def load_ground_truth_text(ground_truth_folder, filename):
    json_name = filename.replace(".jpg", ".json").replace(".png", ".json")
    json_path = os.path.join(ground_truth_folder, json_name)
    with open(json_path) as f:
        gt = json.load(f)
    combined = " ".join([a["answer_text"] for a in gt["answers"]])
    return combined


def evaluate_baseline(test_files, preprocessed_folder, ground_truth_folder):
    all_cer = []
    all_wer = []

    for filename in test_files:
        image_path = os.path.join(preprocessed_folder, filename)
        predicted_text, confidence = run_tesseract_baseline(image_path)
        ground_truth_text = load_ground_truth_text(ground_truth_folder, filename)

        if ground_truth_text.strip() == "":
            continue

        cer = jiwer.cer(ground_truth_text, predicted_text)
        wer = jiwer.wer(ground_truth_text, predicted_text)

        all_cer.append(cer)
        all_wer.append(wer)

        print(filename, "CER:", round(cer, 3), "WER:", round(wer, 3))

    avg_cer = sum(all_cer) / len(all_cer)
    avg_wer = sum(all_wer) / len(all_wer)

    print("\nAverage CER:", round(avg_cer, 3))
    print("Average WER:", round(avg_wer, 3))

    return avg_cer, avg_wer


if __name__ == "__main__":
    with open("data/split.json") as f:
        split_info = json.load(f)

    evaluate_baseline(split_info["test"], "data/preprocessed", "data/ground_truth")
