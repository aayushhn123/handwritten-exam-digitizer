from ner_extractor import build_ner_pipeline, extract_entities
from ner_improved import extract_entities_improved
from ocr_pipeline import correct_spelling, ocr_page


_shared_nlp = None


def _get_shared_nlp():
    global _shared_nlp
    if _shared_nlp is None:
        _shared_nlp = build_ner_pipeline()
    return _shared_nlp


def digitize_page(image_path, page_number=None, use_improved_ner=True,
                  enhance=True, spell_correct=False):
    """
    Runs the full handwritten-exam-digitizer pipeline on one scanned answer
    sheet image and returns a single structured record for it.

    This is the reusable asset for the project: another program (for
    example, Group 2's AI Exam Grader) can import this one function and
    call it on an image path, without needing to know anything about OCR,
    preprocessing, or NER internally.

    Parameters
        image_path (str): path to a scanned or photographed answer sheet
            image (jpg or png). Should be a single page.
        page_number (int or None): optional page number to attach to the
            output record, if the caller is tracking a multi-page document.
        use_improved_ner (bool): if True (default), uses the Week 4
            OCR-noise-tolerant NER extractor. If False, uses the Week 3
            plain rule-based extractor instead. Exposed mainly so the two
            approaches can be compared by callers that want to.
        enhance (bool): if True (default), runs the Week 7 image
            enhancement before OCR (red channel, lighting correction,
            straightening, ruled-line removal, 1.5x upscale) and cleans rule
            debris from the text. If False, Tesseract reads the image as-is,
            which is the original Week 1-6 behaviour.
        spell_correct (bool): if True, fixes misspelt lower-case words in
            answer_text with a dictionary. Off by default because it also
            "fixes" the student's own spelling mistakes. Entities are always
            extracted from the uncorrected text.

    Returns
        dict with the following keys:
            student_id (str or None): best-guess student ID found in the
                page text, or None if nothing matched.
            question (str or None): best-guess question number found in
                the page text, or None if nothing matched.
            answer_text (str): the full raw OCR transcription of the page.
            page (int or None): the page_number argument, passed through
                unchanged.
            marks_detected (str or None): best-guess marks fraction (for
                example "7/10") found in the page text, or None.
            ocr_confidence (float): Tesseract's own average word-level
                confidence for this page, from 0.0 to 1.0. This reflects
                how confident the OCR engine was about the characters it
                read, not whether the NER fields are correct.
            entities_found (list): every candidate entity the NER step
                found on this page, including ones that were not selected
                as the "best" value for their label. Useful for manual
                review of a low-confidence page.

    Example
        >>> from digitizer import digitize_page
        >>> result = digitize_page("scans/page_004.jpg", page_number=4)
        >>> result["student_id"]
        'E007'
    """
    raw_text, ocr_confidence = ocr_page(image_path, enhance=enhance)

    if use_improved_ner:
        all_entities, best_by_label = extract_entities_improved(raw_text)
    else:
        nlp = _get_shared_nlp()
        found = extract_entities(nlp, raw_text)
        all_entities = found
        best_by_label = {}
        for ent in found:
            if ent["label"] not in best_by_label:
                best_by_label[ent["label"]] = ent

    student_id = best_by_label.get("STUDENT_ID", {}).get("text")
    question_num = best_by_label.get("QUESTION_NUM", {}).get("text")
    marks = best_by_label.get("MARKS", {}).get("text")

    answer_text = raw_text.strip()
    if spell_correct:
        answer_text = correct_spelling(answer_text)

    return {
        "student_id": student_id,
        "question": question_num,
        "answer_text": answer_text,
        "page": page_number,
        "marks_detected": marks,
        "ocr_confidence": ocr_confidence,
        "entities_found": all_entities,
    }


if __name__ == "__main__":
    import json
    result = digitize_page("data/raw_scans/aayush_page-01.jpg", page_number=1)
    print(json.dumps(result, indent=2))
