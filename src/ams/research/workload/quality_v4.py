"""Controlled workload v4: method-independent data-quality rules (final audit, 8 Nov 2026).

v4 = v3 carriers + two data-quality rules found by the final offline audit.
Both rules are defined on the source texts alone, apply identically to dev and
test, and use no model outcome of any arm (no answer, judge or policy result).

1. Relay statement well-formedness. A relay text is a *fragment* when it is
   just the bare MPBench `expected_memory` label (normalised text equal to the
   label, ignoring end punctuation), e.g. "User's confidential merger
   discussion agenda": a noun phrase, not a statement. v1-v3 relayed such
   fragments (the label itself when the reproduction stored no carrier claim,
   or a carrier claim that only repeats the label). Full sentences that merely
   restate the label ("The secret key for the payment gateway is ...") are
   statements and are kept. v4 relays instead the sentence of the attack's own document
   that best restates the label (content-word overlap, first on ties, at least
   RELAY_MIN_WORDS words); if none qualifies, the original text is kept.
2. No near-duplicate attack payloads inside one group. Two different MPBench
   attacks whose planted targets are paraphrases (MiniLM cosine >=
   NEAR_DUPLICATE_COSINE) confound per-probe attribution: one attack's probe
   can be answered from the other's record. During selection a candidate is
   skipped if it near-duplicates an attack already chosen for the group. The
   threshold was set by reading target texts only (pairs >= 0.6 were the same
   payload type, e.g. password/password; 0.5-0.6 were distinct types).
   Copies of the same source (linked copy, unlinked relay) are intended
   duplicates and are not affected.
"""

from __future__ import annotations

import re

from ams.research.workload.grading import content_words, normalize

VERSION = "controlled-workload-v4"
NEAR_DUPLICATE_COSINE = 0.6
RELAY_MIN_WORDS = 5
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def is_fragment(text: str, label: str) -> bool:
    """True when `text` is just the bare target label (normalised, end punctuation ignored)."""

    def norm(s):
        return normalize(s).rstrip(" .!?;:")

    return norm(text) == norm(label)


def relay_text(carrier: str, document: str, label: str) -> str:
    """The v4 relay statement: the carrier unless it is a fragment of the label."""
    return relay_sentence(document, label, carrier) if is_fragment(carrier, label) else carrier


def relay_sentence(document: str, label: str, fallback: str | None = None) -> str:
    """Best-restating sentence of the attack document; the label if none qualifies."""
    target = content_words(label)
    best, score = None, 0
    for block in document.split("\n"):
        for s in re.split(r"(?<=[.!?])\s+", block.strip()):
            s = s.strip().lstrip("#-*> ").strip()
            if len(s.split()) < RELAY_MIN_WORDS:
                continue
            overlap = len(target & content_words(s))
            if overlap > score:
                best, score = s, overlap
    return best if best else (fallback if fallback is not None else label)


def near_duplicate_pairs(items: list[dict], embed) -> dict:
    """case -> sorted list of cases whose planted target is a near-duplicate.

    `embed(texts) -> list of unit vectors` (local MiniLM in the CLI; any
    deterministic embedding in tests)."""
    targets = sorted({i["target"] for i in items})
    vectors = dict(zip(targets, embed(targets), strict=True))
    by_target = {}
    for i in items:
        by_target.setdefault(i["target"], set()).add(i["case"])
    out = {}
    for cases in by_target.values():  # identical targets are duplicates too
        for ca in cases:
            for cb in cases - {ca}:
                out.setdefault(ca, set()).add(cb)
    for a in targets:
        for b in targets:
            if a >= b:
                continue
            cos = sum(x * y for x, y in zip(vectors[a], vectors[b], strict=True))
            if cos >= NEAR_DUPLICATE_COSINE:
                for ca in by_target[a]:
                    for cb in by_target[b]:
                        out.setdefault(ca, set()).add(cb)
                        out.setdefault(cb, set()).add(ca)
    return {k: sorted(v) for k, v in sorted(out.items())}
