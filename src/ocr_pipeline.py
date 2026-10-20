"""
Enhanced OCR for photographed handwritten pages (Week 7).

The Week 5 evaluation showed that the Week 1-2 preprocessing (adaptive
threshold + deskew) made Tesseract worse on phone photos of ruled paper.
This module replaces it with steps that each improved CER on the
ground-truth pages, while keeping a page at roughly one second:

    1. red colour channel     pink/red margins and rules vanish, blue and
                              black ink stay dark
    2. lighting correction    divide out shadows and phone-photo gradients
    3. straighten             rotate by the angle of the ruled lines
    4. erase ruled lines      paint faint rule pixels white, keep ink that
                              crosses them (no hard black/white threshold)
    5. upscale 1.5x           handwriting strokes get closer to the size
                              Tesseract's LSTM model expects
    6. Tesseract (psm 4)      one column of text of variable sizes
    7. clean text             drop rule debris such as "____", "—", "|"
    8. spelling (optional)    dictionary correction that never touches
                              capitalised words, IDs or numbers

Measured on data/raw_scans (CER, lower is better):
    aayush_page-01   0.399 -> 0.037
    rish_page-1      0.503 -> 0.341
"""

import math
import re
from functools import lru_cache

import cv2
import numpy as np
import pytesseract

TESSERACT_CONFIG = "--oem 1 --psm 4"
UPSCALE = 1.5


# ---------------------------------------------------------------------------
# Image preparation
# ---------------------------------------------------------------------------

def normalize_lighting(gray):
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    background = cv2.medianBlur(small, 21)
    background = cv2.resize(background, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_LINEAR)
    flat = cv2.divide(gray, background, scale=255)
    return cv2.normalize(flat, None, 0, 255, cv2.NORM_MINMAX)


def ruled_line_mask(gray):
    """Mask of long, thin horizontal lines (notebook rules)."""
    inv = 255 - gray
    mask = cv2.adaptiveThreshold(inv, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, -8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, gray.shape[1] // 8), 1))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def ruled_line_angle(gray):
    segments = cv2.HoughLinesP(ruled_line_mask(gray), 1, np.pi / 720, threshold=80,
                               minLineLength=gray.shape[1] // 4, maxLineGap=20)
    if segments is None:
        return 0.0
    angles = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in segments[:, 0]]
    angles = [a for a in angles if abs(a) < 10]
    return float(np.median(angles)) if angles else 0.0


def rotate(gray, angle):
    if abs(angle) < 0.1:
        return gray
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def erase_ruled_lines(gray):
    lines = ruled_line_mask(gray)
    lines = cv2.dilate(lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if not (ink > 0).any():
        return gray
    # only the faint rule pixels are painted over; dark pen strokes crossing a
    # rule are kept so letters sitting on the line stay whole
    strong_ink = gray < np.percentile(gray[ink > 0], 40)
    out = gray.copy()
    out[(lines > 0) & ~strong_ink] = 255
    return out


def enhance_page(image_path):
    """Load a page photo/scan and return the grayscale image Tesseract reads."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    gray = img[:, :, 2] if img.ndim == 3 else img
    flat = normalize_lighting(gray)
    straight = rotate(flat, ruled_line_angle(flat))
    clean = erase_ruled_lines(straight)
    return cv2.resize(clean, None, fx=UPSCALE, fy=UPSCALE, interpolation=cv2.INTER_CUBIC)


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def read_text(image, config=TESSERACT_CONFIG):
    """
    One Tesseract pass that returns both the text and the average word
    confidence (0-1). Text is rebuilt line by line from image_to_data, which
    avoids running OCR twice.
    """
    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
    lines, confidences = {}, []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        conf = float(data["conf"][i])
        if conf >= 0:
            confidences.append(conf)
    text = "\n".join(" ".join(words) for _, words in sorted(lines.items()))
    confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
    return text, round(confidence, 2)


def clean_text(text):
    """Remove debris that ruled lines and margins leave in OCR output."""
    text = re.sub(r"[_—–~]+", " ", text)
    text = re.sub(r"(?m)^[\s|!.,:;'\"-]+", "", text)
    text = re.sub(r"\s\|\s", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Optional spelling correction
# ---------------------------------------------------------------------------

_spell = {}


def _checkers():
    if not _spell:
        from spellchecker import SpellChecker

        _spell["d2"] = SpellChecker(distance=2)
        _spell["d1"] = SpellChecker(distance=1)
    return _spell["d2"], _spell["d1"]


def correct_spelling(text):
    """
    Dictionary spelling correction for OCR slips ("protess" -> "process").

    Leaves alone: words shorter than 3 letters, ALL-CAPS words (SMTP, IMAP),
    capitalised words (names such as "Nayak"), and anything with digits.
    A candidate that already appears correctly spelled elsewhere on the page
    is preferred, so "jaye" becomes "layer" on a page about OSI layers.
    """
    d2, d1 = _checkers()
    words = re.findall(r"[A-Za-z]+", text)
    page_vocab = {w.lower() for w in words if len(w) >= 3 and w.lower() in d2}

    @lru_cache(maxsize=None)
    def best(word):
        checker = d2 if len(word) <= 7 else d1
        candidates = [c for c in (checker.candidates(word) or ()) if c != word]
        if not candidates:
            return None

        def score(c):
            s = math.log(d2.word_usage_frequency(c) + 1e-12)
            if c in page_vocab:
                s += 8
            if len(c) == len(word):
                s += 1
            return s

        return max(candidates, key=score)

    def fix(match):
        word = match.group(0)
        if len(word) < 3 or word[0].isupper() or word.lower() in d2:
            return word
        return best(word.lower()) or word

    return re.sub(r"(?<![\w@$])[A-Za-z]+(?![\w@$])", fix, text)


def ocr_page(image_path, enhance=True):
    """
    Run OCR on one page image.

    enhance=True uses the Week 7 pipeline above; enhance=False reads the
    image as-is (the original Week 1-6 behaviour), kept for comparison.
    Returns (text, confidence 0-1).
    """
    if enhance:
        text, confidence = read_text(enhance_page(image_path))
        return clean_text(text), confidence
    from PIL import Image

    return read_text(Image.open(image_path), config="")
