# Method figures v4: overview (Figure A) and worked example (Figure B)

23 Nov 2026. Request: replace the dense method figure with two simpler figures in the visual style of arXiv 2606.09935 (GitInject). Figure A shows how S works; Figure B shows what S does to one concrete case.

| File | Use |
|---|---|
| `fig_A_overview.pdf` / `.svg` / `.png` | Figure A, method overview. 6.75 × 2.11 in, 77 words |
| `fig_A_family.pdf` / `.svg` / `.png` | **Figure A with the method family**: the same three stages plus an exploratory-extensions band (SL, S2-ID) hooked where the code applies them. 6.75 × 2.79 in |
| `fig_B_example.pdf` / `.svg` / `.png` | Figure B, worked example. 6.75 × 3.04 in, 100 words |
| `fig_C_spread.pdf` / `.svg` / `.png` | Figure C, the method itself: how far distrust spreads as evidence grows. 6.75 × 2.09 in |
| `verify_figure_c.py` | Runs the frozen `Policy("S")` on Figure C's three stages (offline, read-only) |
| `make_figures.py` | Dependency-free generator for both figures. One shared style: palette, type scale, glyphs, boxes and arrows. It flags any text that overflows its box or is smaller than 16 units (≈ 5.6 pt). |

Regenerate: `python make_figures.py`. The PDFs and PNGs are rendered from the SVGs with headless Chrome: PDF width 6.75 in, PNG at scale 2. Both PDFs are vector, with no raster images and live text.

The previous single figure (v3, 199 words) stays in `../methodology_s_20261114/`. It still contains SL and S2-ID, so it can serve as an appendix figure.

## Design taken from the reference paper

- **From its Figure 3** (lifecycle): a few large rounded stages, each with a 2–4 word label and one line of detail, and one accent colour for the system's own component.
- **From its Figure 1** (config-file injection, its step-by-step example):
  - numbered column headers ("1. … 4. Outcome");
  - two contrasting rows that go through the same steps and end in different outcomes;
  - thick arrows between columns, and icons instead of sentences.
- **Kept from our figures** so that both new figures match the paper's earlier figures and slides:
  - the palette (lavender = S, grey = SAFE-Mem, red = unsafe / withheld);
  - the glyph set (✗ unsafe, ○ unaudited, ✓ kept / supported);
  - the notation.

## What was kept, merged, moved or removed

| Old figure element | Decision |
|---|---|
| Panel (a), provenance and audits | **Merged** into stage 1 of A: one record with its (u, c, b) chips, *T* tickets on a mostly unaudited memory, and the ledger. The detailed toy world moved to B. |
| Panel (b), the full gate formulas with θ / δ | **Simplified** in A to nested scopes with a gate lock on each, plus the one idea of S: *a scope opens only when verified incidents span it*. The exact gates appear where they matter, in B column 3, and in the caption. |
| Risk r, penalty d, D = max | **Kept** in A, in three lines. |
| R/C/M/S table | **Moved** to B (bottom strip). |
| Penalty bar chart against τ | **Removed.** B shows the same boundary case directly: d = 1/4, D ≥ τ, withheld. |
| Panel (c) steps 1–7 | **Merged** into four pills in A: admission, decision (ours), serve top k + m with refill, then conflict check and answer model. Direct audit findings are folded into the decision pill ("audited ✗ or D ≥ τ → withhold"). |
| SL and S2-ID boxes, Q3 relay, unlinked contributor U | **Removed** from both figures. They are exploratory (Appendix C), and the overview should show the contribution S. The caption points to Appendix C. They remain in the v3 figure if an appendix figure is wanted. |
| Boundary-verification note, the "not experimental results" sentence | **Caption only.** |

## Captions

**Figure A.** **Selective evidence propagation (S) on top of SAFE-Mem.**
(1) Every external record *x* carries trusted provenance: contributor *u*, context *c* and arrival batch *b*. A budget of *T* audit tickets inspects a few incident roots. An append-only evidence ledger counts each root at most once, using only active audits (neither superseded nor retracted).
(2) For an unaudited record, S considers three nested scopes of its provenance and admits a scope only when the verified incidents span it (Eq. 9):
- the record's batch, once the batch has ≥ θ_bat unsafe roots;
- the context, once ≥ θ_ctx unsafe roots fall in ≥ δ_ctx of its batches;
- the contributor, once it has ≥ θ_src unsafe roots and ≥ δ_src qualifying contexts.

Each supported scope has risk *r* = (1+n⁻)/(2+n⁻+n⁺) and penalty *d* = max(0, *r* − ½), where n⁻ and n⁺ count its unsafe and safe roots. *D* is the largest *d* over the supported scopes, or 0 if there is none.
(3) SAFE-Mem's retrieval is unchanged except for this decision. After admission α(*x*, *q*), a record audited unsafe for this use, or with *D* ≥ τ, is withheld. The remaining records are ranked by *s* − λ*D*, where *s* is cosine similarity. Withheld slots are refilled from the admissible pool, and the top *k* claims and *m* chunks pass through SAFE-Mem's conflict check to the answer model.

Only authenticated external records receive a transferred penalty. Main setting: τ = 1/4, λ = 1/2, k = m = 4; the gate thresholds are given in Section 3.8. The exploratory extensions SL and S2-ID are described in Appendix C.

**Figure A (family version).** Same as Figure A, plus: *Exploratory extensions (Appendix C), composable S → SL → S2-ID.* **SL** adds a content-lineage veto inside each candidate decision: a non-principal claim whose embedding has cosine ≥ η to a claim of a root with an unsafe audit is withheld, unless it is itself verified safe. This covers relays the harness cannot link, which form new roots to which provenance scopes give D = 0. Unlike S, SL also counts unsafe audits that were later superseded or retracted (a limitation of the evaluated implementation). **S2-ID** adds MemLineage's sensitive-query gate to SL: if the query is sensitive (MemLineage's classifier) and the final context holds any non-principal memory, the context is emptied. The gate uses no identity signal and targets Sybil and laundering attacks. η = 0.8.

Hook points in code: SL = `LineagePolicy.decide` wrapping `Policy("S")` (`workload/lineage.py:54-60`); S2-ID = `_GatedReader` on the retrieved context (`workload/sv2.py:95-116`), composed as S + lineage + gate (`sv2.py:47-50, 130-150`).

**Which to use (ICML):** if SL and S2-ID results appear in the main text, use the family version as Figure 1: S stays the visually dominant contribution, and the extensions read as clearly marked add-ons. If they stay in the appendix, use the S-only Figure A in the main text and the family version in Appendix C.

**Figure B.** **Worked example: one contributor, two unaudited records.** Contributor A planted the claim ZX-91 in batch 1 of context X. A also wrote a useful note (Larkspur) in batch 2 of the same context. Neither record is audited. Four of A's other roots were audited unsafe: two in batch 1 of X and two in batch 1 of context Y.
(2) A's verified incidents, by context and batch.
(3) For ZX-91, only the batch scope is supported. The context and contributor gates fail because none of A's contexts has incidents in two batches. Batch 1 has n⁻ = 2 and n⁺ = 0, so *r* = 3/4 and *D* = *d* = 1/4. For the Larkspur note, no scope is supported, so *D* = 0.
(4) With τ = 1/4, ZX-91 is withheld: *D* = τ is withheld because the comparison is inclusive. Its slot is refilled, and the note is still served.

Bottom: on the same two records, record-local containment (R) serves the planted claim. Contributor-context (C) and maximal (M) propagation withhold it but also discard the useful note. Only S separates the two.

The outcomes come from running the frozen decision rule on this constructed example (`../methodology_s_20261114/verify_toy_example.py`). They illustrate the mechanism and are not experimental results. Example content is fictional.

**Figure C.** **How far S spreads distrust.** One contributor A, three contexts (X, Y, Z) and two batches each; every cell holds one unaudited record. (1) One verified incident supports only its batch: D = d = 1/6 < τ, so the batch's records are only ranked lower. (2) Once incidents recur in δ_ctx batches of context X, the context scope opens: D = 1/4 ≥ τ withholds all of X, while Y and Z are untouched. (3) Once δ_src contexts qualify, the contributor scope opens: D = 1/3 withholds all of A's records, including context Z, which has no incident. Main setting, no safe audits (n⁺ = 0); outcomes from the frozen decision rule (`verify_figure_c.py`). Illustrative, not experimental results.

## Notation note for the paper

Figure B writes the gates as θ_bat, δ_ctx and δ_src, following the symbolic Eqs. 8–9 proposed in `../methodology_s_20261114/PAPER_LATEX_EDITS.md`. The 21 Nov draft (`main.pdf`) still writes these thresholds as numbers. If the paper keeps the numbers, change the three chips to "2 ✗ ≥ 1", "✗ in 1 batch < 2" and "0 qualifying < 2". Everything else already uses the draft's notation: α(x, q), r, d, D, n⁻ / n⁺, τ, λ, s, k, m, and the policy names from Table 1.

## Verification against the implementation

| Figure element | Code / check |
|---|---|
| Provenance (u, c, b); only authenticated external records get a penalty | `Provenance`, `dynamic/models.py:58`; `policies.py:119` |
| One vote per root; only active audits | `EvidenceSnapshot.observations`, `ledger.py:274`; `_project`, `ledger.py:89` |
| Nested scopes, gates | `group`, `active_scopes`, `ledger.py:286-327` |
| r, d (exact `Fraction`); D = max over supported scopes, 0 if none | `GroupStats`, `ledger.py:68-78`; `policies.py:135` |
| Withheld if audited unsafe for this use, or D ≥ τ (inclusive); otherwise score s − λD | `Policy.decide`, `policies.py:98-143` (local status 115, gate 137) |
| Admission → decision → refill to k claims + m chunks → conflict check (flags only) | `GovernedRetrieval.retrieve_with_trace`, `retrieval/adapter.py:182-399` |
| Figure B: gates for ZX-91 = {batch}, for Larkspur = ∅; D = 1/4 and 0; R/C/M/S outcomes in the bottom strip | **executed:** `verify_toy_example.py` runs the frozen `Policy.decide` on this toy ledger |
| No mechanism beyond the frozen code; SL and S2-ID omitted, not altered | — |

No research code, protocol, configuration, data or result was changed. No paid API call was made.
