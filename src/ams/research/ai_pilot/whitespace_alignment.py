"""Map presentation-only quote/whitespace differences to exact original spans."""

from ams.research.dynamic.models import check

from .calibration import validate_extraction

VERSION = "exact_original_spans_whitespace_and_one_quote_pair_v1"


def collapsed(text):
    chars = []
    positions = []
    i = 0
    while i < len(text):
        start = i
        if text[i].isspace():
            while i < len(text) and text[i].isspace():
                i += 1
            chars.append(" ")
            positions.append((start, i))
        else:
            chars.append(text[i])
            positions.append((i, i + 1))
            i += 1
    if chars and chars[0] == " ":
        chars.pop(0)
        positions.pop(0)
    if chars and chars[-1] == " ":
        chars.pop()
        positions.pop()
    return "".join(chars), positions


def align(kind, body, raw):
    check(
        type(raw) is dict and isinstance(raw.get("evidence"), str),
        "Evidence must be a string in an object",
    )
    text = body["passage"] if kind == "support" else body["question"]
    original = raw["evidence"]
    candidates = [(original, False)]
    if len(original) > 2 and original[0] == original[-1] == '"':
        candidates.append((original[1:-1], True))
    normalized_text, positions = collapsed(text)
    for candidate, unwrapped in candidates:
        spans = []
        method = "exact"
        cursor = 0
        if not candidate:
            extraction = validate_extraction(kind, body, raw)
            return extraction, {
                "version": VERSION,
                "method": "empty",
                "raw_evidence": original,
                "exact_input_spans": [],
            }
        while (start := text.find(candidate, cursor)) >= 0:
            spans.append({"start": start, "end": start + len(candidate), "quote": candidate})
            cursor = start + 1
        if not spans:
            needle, _ = collapsed(candidate)
            cursor = 0
            if not needle:
                continue
            while (start := normalized_text.find(needle, cursor)) >= 0:
                lo = positions[start][0]
                hi = positions[start + len(needle) - 1][1]
                quote = text[lo:hi]
                check(collapsed(quote)[0] == needle, "Alignment changed nonwhitespace content")
                spans.append({"start": lo, "end": hi, "quote": quote})
                cursor = start + 1
            method = "whitespace_only"
        if spans:
            extraction = validate_extraction(kind, body, {**raw, "evidence": spans[0]["quote"]})
            return extraction, {
                "version": VERSION,
                "method": ("one_outer_ascii_quote_pair+" if unwrapped else "") + method,
                "raw_evidence": original,
                "exact_input_spans": spans,
            }
    check(False, "Evidence has no exact or whitespace-only original span")
