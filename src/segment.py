import pytesseract
import re


def segment_questions(image_path):
    data = pytesseract.image_to_data(image_path, output_type=pytesseract.Output.DICT)
    segments = []
    current_question = None
    current_lines = []
    current_top = None

    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        if word == "":
            continue

        question_match = re.match(r"^Q(\d+)[\.\):]?$", word, re.IGNORECASE)

        if question_match:
            if current_question is not None:
                segments.append({
                    "question": current_question,
                    "text_region_lines": current_lines,
                    "top": current_top
                })
            current_question = "Q" + question_match.group(1)
            current_lines = []
            current_top = data["top"][i]
        else:
            current_lines.append((data["left"][i], data["top"][i], word))

    if current_question is not None:
        segments.append({
            "question": current_question,
            "text_region_lines": current_lines,
            "top": current_top
        })

    return segments
