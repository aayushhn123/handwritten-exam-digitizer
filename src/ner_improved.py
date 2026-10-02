import re


OCR_CONFUSIONS = {
    "O": "0",
    "o": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "B": "8",
}


def clean_digit_run(run):
    return "".join(OCR_CONFUSIONS.get(ch, ch) for ch in run)


def find_student_id_candidates(text):
    candidates = []
    pattern = r"\b([0-9OolIS]{2})([A-Za-z])([0-9OolIS]{3,4})\b"
    for match in re.finditer(pattern, text):
        raw = match.group()
        prefix_digits = clean_digit_run(match.group(1))
        letter = match.group(2)
        suffix_digits = clean_digit_run(match.group(3))
        cleaned = prefix_digits + letter + suffix_digits

        if re.match(r"^[0-9]{2}[A-Za-z][0-9]{3,4}$", cleaned):
            candidates.append({
                "text": cleaned,
                "original_text": raw,
                "label": "STUDENT_ID",
                "start_char": match.start(),
                "end_char": match.end()
            })
    return candidates


def find_question_candidates(text):
    candidates = []
    pattern = r"\b[Qq]([0-9OolIS]{1,2})[\.\):]?\b"
    for match in re.finditer(pattern, text):
        raw = match.group()
        cleaned = "Q" + clean_digit_run(match.group(1))
        candidates.append({
            "text": cleaned,
            "original_text": raw,
            "label": "QUESTION_NUM",
            "start_char": match.start(),
            "end_char": match.end()
        })
    return candidates


def find_marks_candidates(text):
    candidates = []
    pattern = r"\b([0-9OolIS]{1,2})\s*/\s*([0-9OolIS]{1,2})\b"
    for match in re.finditer(pattern, text):
        raw = match.group()
        cleaned = clean_digit_run(match.group(1)) + "/" + clean_digit_run(match.group(2))
        candidates.append({
            "text": cleaned,
            "original_text": raw,
            "label": "MARKS",
            "start_char": match.start(),
            "end_char": match.end()
        })
    return candidates


def find_page_candidates(text):
    candidates = []
    pattern = r"\bpage\s+[0-9OolIS]+\b"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = match.group()
        candidates.append({
            "text": raw,
            "original_text": raw,
            "label": "PAGE_NUM",
            "start_char": match.start(),
            "end_char": match.end()
        })
    return candidates


def rank_candidates(candidates):
    return sorted(candidates, key=lambda c: c["start_char"])


def extract_entities_improved(text):
    all_candidates = []
    all_candidates += find_student_id_candidates(text)
    all_candidates += find_question_candidates(text)
    all_candidates += find_marks_candidates(text)
    all_candidates += find_page_candidates(text)

    ranked = rank_candidates(all_candidates)

    best_by_label = {}
    for candidate in ranked:
        label = candidate["label"]
        if label not in best_by_label:
            best_by_label[label] = candidate

    return ranked, best_by_label


if __name__ == "__main__":
    sample_text = "23DOO1 Q3 The Viterbi algorithm is used for decoding. Page 4 Marks 7/1O"
    all_entities, best_picks = extract_entities_improved(sample_text)

    print("all candidates found:")
    for ent in all_entities:
        print(ent)

    print("\nbest pick per label:")
    for label, ent in best_picks.items():
        print(label, "->", ent["text"], "(raw OCR text was:", ent["original_text"] + ")")
