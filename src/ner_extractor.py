import spacy


def build_ner_pipeline():
    nlp = spacy.load("en_core_web_sm")

    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
    else:
        ruler = nlp.get_pipe("entity_ruler")

    patterns = [
        {"label": "STUDENT_ID", "pattern": [{"TEXT": {"REGEX": "^[0-9]{2}[A-Za-z][0-9]{3,4}$"}}]},
        {"label": "QUESTION_NUM", "pattern": [{"TEXT": {"REGEX": "^[Qq][0-9]{1,2}[\\.\\):]?$"}}]},
        {"label": "MARKS", "pattern": [{"TEXT": {"REGEX": "^[0-9]{1,2}/[0-9]{1,2}$"}}]},
        {"label": "PAGE_NUM", "pattern": [{"LOWER": "page"}, {"IS_DIGIT": True}]},
    ]

    ruler.add_patterns(patterns)
    return nlp


def extract_entities(nlp, text):
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start_char": ent.start_char,
            "end_char": ent.end_char
        })
    return entities


if __name__ == "__main__":
    nlp = build_ner_pipeline()
    sample_text = "23D001 Q3 The Viterbi algorithm is used for decoding. Page 4 Marks 7/10"
    result = extract_entities(nlp, sample_text)
    for ent in result:
        print(ent)
