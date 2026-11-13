"""Conservative presentation alignment, never a semantic verdict repair."""

from ams.research.dynamic.models import check

from .calibration import validate_extraction

VERSION = "one_ascii_quote_pair_if_exact_v1"


def align(kind, body, raw):
    check(type(raw) is dict, "Extraction must be an object")
    text = body["passage"] if kind == "support" else body["question"]
    evidence = raw.get("evidence")
    check(isinstance(evidence, str), "Evidence must be a string")
    original = evidence
    method = "exact"
    if evidence and evidence not in text:
        check(
            len(evidence) > 2 and evidence[0] == evidence[-1] == '"',
            "Unsupported evidence presentation",
        )
        evidence = evidence[1:-1]
        check(evidence and evidence in text, "Unwrapped evidence is not an exact input span")
        method = "removed_one_outer_ascii_quote_pair"
    extraction = validate_extraction(kind, body, {**raw, "evidence": evidence})
    spans = []
    cursor = 0
    while evidence and (start := text.find(evidence, cursor)) >= 0:
        spans.append({"start": start, "end": start + len(evidence), "quote": evidence})
        cursor = start + 1
    return extraction, {
        "version": VERSION,
        "method": method,
        "raw_evidence": original,
        "exact_input_spans": spans,
    }
