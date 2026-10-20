from ner_extractor import build_ner_pipeline, extract_entities
from ner_improved import extract_entities_improved


def score_predictions(predicted_set, true_set):
    total_true = len(true_set)
    total_predicted = len(predicted_set)
    total_correct = len(predicted_set & true_set)

    precision = total_correct / total_predicted if total_predicted else 0
    recall = total_correct / total_true if total_true else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    return precision, recall, f1


def evaluate_baseline(nlp, test_cases):
    all_predicted = set()
    all_true = set()

    for text, true_entities in test_cases:
        predicted = extract_entities(nlp, text)
        predicted_set = set((e["text"], e["label"]) for e in predicted)
        all_predicted |= predicted_set
        all_true |= set(true_entities)

    return score_predictions(all_predicted, all_true)


def evaluate_improved(test_cases):
    all_predicted = set()
    all_true = set()

    for text, true_entities in test_cases:
        all_entities, best_picks = extract_entities_improved(text)
        predicted_set = set((e["text"], e["label"]) for e in best_picks.values())
        all_predicted |= predicted_set
        all_true |= set(true_entities)

    return score_predictions(all_predicted, all_true)


if __name__ == "__main__":
    test_cases = [
        ("23D001 Q3 answer text here", [("23D001", "STUDENT_ID"), ("Q3", "QUESTION_NUM")]),
        ("Q1 the algorithm works by iterating", [("Q1", "QUESTION_NUM")]),
        ("23D045 Q2 marks 8/10", [("23D045", "STUDENT_ID"), ("Q2", "QUESTION_NUM"), ("8/10", "MARKS")]),
        ("23DOO1 Q3 Page 4 Marks 7/1O", [("23D001", "STUDENT_ID"), ("Q3", "QUESTION_NUM"), ("Page 4", "PAGE_NUM"), ("7/10", "MARKS")]),
        ("23D099 Q1O marks 9/1O page 2", [("23D099", "STUDENT_ID"), ("Q10", "QUESTION_NUM"), ("9/10", "MARKS"), ("page 2", "PAGE_NUM")]),
    ]

    nlp = build_ner_pipeline()

    print("baseline (week 3, rule-based, single match per label)")
    baseline_precision, baseline_recall, baseline_f1 = evaluate_baseline(nlp, test_cases)
    print("precision:", round(baseline_precision, 3))
    print("recall:", round(baseline_recall, 3))
    print("f1:", round(baseline_f1, 3))

    print("\nimproved (week 4, ocr-noise tolerant, multi-candidate ranking)")
    improved_precision, improved_recall, improved_f1 = evaluate_improved(test_cases)
    print("precision:", round(improved_precision, 3))
    print("recall:", round(improved_recall, 3))
    print("f1:", round(improved_f1, 3))

    # Week 7: strings copied from real Tesseract output on the photographed
    # answer sheets, where the OCR itself garbled the labels
    real_ocr_cases = [
        ("QL OS! Model in Email Sending and Recening", [("Q1", "QUESTION_NUM")]),
        ("@1) 05t Mode) and email. ganding Receiving", [("Q1", "QUESTION_NUM")]),
        ("Roll no - EO13 Year - 3rd Date - 5/11/2024", [("E013", "STUDENT_ID")]),
        ("Roll no: E0I3 Q2) marks 6/1O", [("E013", "STUDENT_ID"), ("Q2", "QUESTION_NUM"), ("6/10", "MARKS")]),
        ("Q3] answer Roll call was fine", [("Q3", "QUESTION_NUM")]),
    ]
    print("\nreal OCR noise (week 7 test set)")
    real_baseline = evaluate_baseline(nlp, real_ocr_cases)
    real_improved = evaluate_improved(real_ocr_cases)
    print("metric      baseline   improved")
    for name, b, i in zip(["precision", "recall", "f1"], real_baseline, real_improved):
        print(f"{name:11s} {round(b, 3):<10} {round(i, 3)}")

    print("\nsummary")
    print("metric      baseline   improved")
    print("precision  ", round(baseline_precision, 3), "    ", round(improved_precision, 3))
    print("recall     ", round(baseline_recall, 3), "    ", round(improved_recall, 3))
    print("f1         ", round(baseline_f1, 3), "    ", round(improved_f1, 3))
