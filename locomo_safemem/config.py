"""Constants of the LoCoMo + SAFE-Mem supplementary study (reports/PROTOCOL_LOCOMO_SAFEMEM.md).
Every value is hashed by the freeze. Nothing here was chosen from an answer or judgement of this
study. Scenario generation is LoCoMo v2's (same seeds), so every attack instance is identical to the
plain-RAG v2 study and the two are paired.
"""

from __future__ import annotations

from locomo_v2 import config as V2

REPO = V2.REPO
PROTOCOL_ID = "locomo-safemem-v1"
PROTOCOL_TEXT = "reports/PROTOCOL_LOCOMO_SAFEMEM.md"
EVIDENCE = "supplementary, exploratory (LoCoMo v2 plain-RAG results were inspected before this design)"
DATA, DATA_SHA256 = V2.DATA, V2.DATA_SHA256

CONVS, DEV, HELDOUT = V2.CONVS, V2.DEV, V2.HELDOUT  # dev = conv-48/49 (pilot), held-out = 8
ORIENTATIONS = V2.ORIENTATIONS
DRAWS = V2.DRAWS  # 5
SEED, SEED_V2 = V2.SEED, V2.SEED_V2  # v2 generator seeds (paired with v2)
SEED_SM = 20261124  # new draws of this study only (fp1 accused turn, late order, follow-up ticket)
QA_CATEGORIES = V2.QA_CATEGORIES
TAU = V2.TAU  # frozen lineage threshold 0.8
FN_RATE = V2.FN_RATE

# ------------------------------------------------------------------ experiment matrix
# store families (a store = one SAFE-Mem build); each maps to its audit conditions below
SHAPES = V2.SHAPES  # 1s, 2s, quarter, spread  (MPBench localized ... distributed)
SYBIL_KS = (2, 4, 8)  # MPBench sybil_k{2,4,8}; k = 1 is loc 1s
SYBIL_NAMES = (*V2.SYBIL_NAMES, "Rowan", "Sage", "Emerson", "Hollis")  # v2's three first: k = 2, 4 identical to v2
RELAY_RATES = V2.RELAY_RATES  # 0.5, 1.0 (unknown-origin verbatim copies; MPBench unlinked relays / H5)
FRAME_KINDS = V2.FRAME_KINDS  # fp1, fp2c, fp2s (false accusations, no attack; H6 analogue)
IMPERFECT_SHAPES = ("1s", "spread")  # MPBench imp_{localized,distributed}_*
LATE_SHARE = 0.5  # MPBench `pre_reveal_probes`: half of the questions answered before the audits

# methods (MPBench Option B main table order); S2-BS appendix-only, as on MPBench
INTERNAL_ARMS = ("R", "C", "M", "S", "SL", "S2-ID")
APPENDIX_ARMS = ("S2-BS",)
FREE_PUBLISHED = ("memlineage", "randec")
PAID_PUBLISHED = ("a_memguard", "llm_sanitiser")
MAIN_METHODS = ("static", "a_memguard", "memlineage", "llm_sanitiser", "randec", "R", "C", "M", "S", "SL", "S2-ID")
PAID_PUBLISHED_FAMILIES = ("loc",)  # scope of A-MemGuard, LLM sanitiser and RandEC (all audit-free)

# ------------------------------------------------------------------ models (pretrained only)
MODEL = "openai/gpt-4o-mini"  # SAFE-Mem memory model, answer model, judge (as MPBench + LoCoMo v2)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # local, free

# ------------------------------------------------------------------ statistics (descriptive)
ALPHA = 0.05
NI_MARGIN = V2.NI_MARGIN
SUP_MARGIN = V2.SUP_MARGIN
