import re


OCR_CONFUSIONS = {
    "O": "0",
    "o": "0",
    "D": "0",
    "l": "1",
    "I": "1",
    "L": "1",
    "|": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
}

# characters OCR commonly produces in place of a digit
DIGIT_LIKE = "0-9OoDlIL|SBZ"

# words that usually come right before a student ID on an answer sheet
ID_CUES = r"(?:roll\s*(?:no|number|num)?|reg(?:istration)?\s*(?:no)?|enrol(?:l)?ment\s*(?:no)?|student\s*id|id)"


def clean_digit_run(run):
    return "".join(OCR_CONFUSIONS.get(ch, ch) for ch in run)


def find_student_id_candidates(text):
    candidates = []

    pattern_numeric_prefix = r"\b([0-9OolIS]{2})([A-Za-z])([0-9OolIS]{3,4})\b"
    for match in re.finditer(pattern_numeric_prefix, text):
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

    # requires at least one real digit (0-9) in the three characters after the
    # letter, so an ordinary word like "Roll" (letter + three plain letters,
    # with no digit anywhere) is never matched, while real OCR noise such as
    # "E0I3" (a mix of real digits and look-alike letters) still is
    pattern_letter_prefix = r"\b([A-Za-z])([0-9OolIS]{3})\b"
    for match in re.finditer(pattern_letter_prefix, text):
        raw = match.group()
        letter = match.group(1)
        raw_digits_part = match.group(2)
        has_real_digit = any(ch.isdigit() for ch in raw_digits_part)
        if not has_real_digit:
            continue
        cleaned = letter.upper() + clean_digit_run(raw_digits_part)
        candidates.append({
            "text": cleaned,
            "original_text": raw,
            "label": "STUDENT_ID",
            "start_char": match.start(),
            "end_char": match.end()
        })

    # right after a cue like "Roll no -" we trust the position more than the
    # characters, so an ID read with no real digit at all ("EOI3") is accepted
    pattern_after_cue = r"\b" + ID_CUES + r"\s*[.:\-=]*\s*([A-Za-z])\s?([" + DIGIT_LIKE + r"]{3,4})\b"
    seen = {(c["start_char"], c["end_char"]) for c in candidates}
    for match in re.finditer(pattern_after_cue, text, re.IGNORECASE):
        start, end = match.start(1), match.end(2)
        if (start, end) in seen:
            continue
        cleaned = match.group(1).upper() + clean_digit_run(match.group(2))
        if re.match(r"^[A-Z][0-9]{3,4}$", cleaned):
            candidates.append({
                "text": cleaned,
                "original_text": text[start:end],
                "label": "STUDENT_ID",
                "start_char": start,
                "end_char": end
            })

    return candidates


def find_question_candidates(text):
    candidates = []
    # "Q1", "Q1.", "Q1)", "Q1]" and OCR variants such as "QL." or "Ql"
    pattern = r"\b[Qq]([0-9OolILS|]{1,2})(?=[\s\.\):\]]|$)"
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

    # a handwritten "Q" is often read as "@"; only trusted at the start of a
    # line and when followed by a closing mark, e.g. "@1)" -> Q1
    pattern_at = r"(?m)^[ \t]*(@)\s?([0-9OolILS|]{1,2})[\.\):\]]"
    for match in re.finditer(pattern_at, text):
        candidates.append({
            "text": "Q" + clean_digit_run(match.group(2)),
            "original_text": match.group().strip(),
            "label": "QUESTION_NUM",
            "start_char": match.start(1),
            "end_char": match.end()
        })
    return candidates


def find_marks_candidates(text):
    candidates = []
    # the lookarounds stop dates such as 5/11/2024 being read as marks "5/11"
    pattern = r"(?<![/\d])\b([0-9OolIS]{1,2})\s*/\s*([0-9OolIS]{1,2})\b(?!\s*/\s*\d)"
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
