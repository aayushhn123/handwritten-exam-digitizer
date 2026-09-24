from ner_extractor import build_ner_pipeline, extract_entities


def evaluate_ner(nlp, labeled_examples):
    total_true = 0
    total_predicted = 0
    total_correct = 0

    for text, true_entities in labeled_examples:
        predicted = extract_entities(nlp, text)
        predicted_set = set((e["text"], e["label"]) for e in predicted)
        true_set = set(true_entities)

        total_true += len(true_set)
        total_predicted += len(predicted_set)
        total_correct += len(predicted_set & true_set)

    precision = total_correct / total_predicted if total_predicted else 0
    recall = total_correct / total_true if total_true else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print("Precision:", round(precision, 3))
    print("Recall:", round(recall, 3))
    print("F1:", round(f1, 3))
    return precision, recall, f1


if __name__ == "__main__":
    nlp = build_ner_pipeline()

    labeled_examples = [
        ("23D001 Q3 answer text here", [("23D001", "STUDENT_ID"), ("Q3", "QUESTION_NUM")]),
        ("Q1 the algorithm works by iterating", [("Q1", "QUESTION_NUM")]),
        ("23D045 Q2 marks 8/10", [("23D045", "STUDENT_ID"), ("Q2", "QUESTION_NUM"), ("8/10", "MARKS")]),
    ]

    evaluate_ner(nlp, labeled_examples)
