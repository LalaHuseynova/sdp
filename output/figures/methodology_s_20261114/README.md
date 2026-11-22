# Methodology figure: selective evidence propagation (S) on SAFE-Mem

| File | Use |
|---|---|
| `fig_method.pdf` | Vector PDF for Overleaf: 6.75 × 3.11 in, embedded Arial/Times subsets, no raster images |
| `fig_method.svg` | Editable source (real text; groups `panel-a`, `panel-b-S`, `panel-c-retrieval`, `legend`) |
| `fig_method.png` | Preview, 2780 × 1280 px |
| `make_figure.py` | Dependency-free generator; flags any text wider than its box or smaller than 16 units (≈ 5.6 pt) |
| `versions/` | Earlier versions, each with its own generator, SVG, PDF and PNG (see "Versions") |
| `verify_toy_example.py` | Runs the frozen `Policy.decide` on the toy ledger of panel (a) and prints the R/C/M/S decisions shown in panel (b), table 3 (offline, read-only) |
| `PAPER_LATEX_EDITS.md` | Notation edits for the methodology draft, so the paper matches this figure |

Regenerate: `python make_figure.py --out fig_method.svg`. The PDF and PNG are rendered from the SVG with headless Chrome: PDF page 6.75 × 3.108 in; PNG at device scale 2.

**Editing colours or text.**
- The SVG starts with a `PALETTE` comment listing each colour and its role. Every role uses its own hex value, so a find-and-replace of one hex recolours that role everywhere.
- The same constants sit at the top of `make_figure.py`.
- All labels are live `<text>` elements.
- Palette roles:
  - S (our contribution): soft lavender;
  - SAFE-Mem: neutral grey;
  - SL: muted teal;
  - S2-ID: restrained amber, dashed;
  - unsafe / withheld: red.
- Line styles: solid = query path, dashed lavender = evidence, dotted teal = content near-copy (SL).

## Versions

| Version | What changed | Words in figure |
|---|---|---|
| `versions/v0_original/` | First figure (commit 047d085), numeric thresholds | 317 |
| `versions/v1_notation/` | 15 Nov: thresholds and notation aligned with the methodology draft (supervisor: "write them as variables"); text-only change, layout identical to v0 | 311 |
| `versions/v2_visual/` | 22 Nov: feedback "too dense with words, add more visuals". Same canvas, three panels, palette, notation and example; prose replaced by visuals (list below) | 198 |
| **current (v3)** | 22 Nov: feedback "simplify panel (b), clarify the symbols, make the figure match the implementation". Panel (b) rebuilt as three numbered steps; two fidelity fixes (list below) | 199 |

**v1 recovery note.** v1 was never committed. The fast-forward pull of 22 Nov (01:16) reset this folder to commit 047d085. The v1 SVG was recovered from the 15 Nov render page. The v1 generator was rebuilt by replaying the recorded edits onto 047d085, and it reproduces the recovered SVG byte for byte.

**v3 changes (panel b and fidelity):**
- **(b) is three numbered steps, read top to bottom.** (1) *Support gates for ZX-91*: one row per scope with its condition, the evidence for ZX-91 and the result (batch active; context and contributor not met). The nested boxes and the separate "here:" line are gone; the qualifying-context rule (θ_Q, δ_Q) is a footnote, still separate from the context gate. (2) *Risk → decision*: each formula carries a gloss (risk, penalty, S uses), s is glossed as similarity, and the chart's x-axis is labelled "unsafe roots n⁻ (with n⁺ = 0)". (3) *Toy example*: the R/C/M/S table.
- **Fidelity fix 1, M's scope chip: "src · 1/3" → "all · 1/3".** In `Policy.decide` M always applies all three scopes without support gates and takes the maximum (`policies.py:122-123`); 1/3 is that maximum (the contributor scope). The old chip suggested M uses only the contributor scope.
- **Fidelity fix 2, R's chip: "local" → "none".** R propagates over no scope (weight 0, no threshold, `policies.py:81-83`); direct audit findings still apply to every method (step 2).
- **Fidelity fix 3, S2-ID box titled "S2-ID: MemLineage gate".** The gate and its sensitivity classifier are MemLineage's (recorded verdicts, `sv2.py:119-127`), composed on top of SL; the figure no longer leaves this implicit. "Exploratory" stays in the legend.
- **Table 3 is checked by running the code**, not only by hand: `verify_toy_example.py` builds the toy ledger of panel (a) and calls the frozen `Policy.decide`. Output: ZX-91 is withheld by C (1/4), M (1/3) and S (1/4, batch scope only, the inclusive boundary) and served by R; Larkspur is withheld by C and M and kept by R and S (no active scope).

**v2 visual changes:**
- **(a)** Memories are short record tiles grouped by contributor → context → batch, instead of sentences. The audit budget is five ticket glyphs, each showing its verdict (4 × unsafe for A's seeds, 1 × safe for B). The boundary-verification sentence moved to the caption.
- **(b)** The gate conditions use the ✗ glyph for "unsafe root". The context box shows why its gate is not met (here: b1 ✗✗, b2 ○). The risk box draws the penalty d for n⁻ = 0, 1, 2 (n⁺ = 0) against the τ line, with the worked example as the bar on the boundary; bar colours show withhold vs. down-rank. The table uses scope chips (local / ctx / bat / src · D) and record tiles as column heads.
- **(c)** Each query shows its outcome inline, which replaced the "Example outcomes" list. SL is drawn as relay ⋯ seed with cos ≥ η; S2-ID as "→ context ∅". A new slot diagram shows step 4 for Q1: R serves ZX-91, while S withholds it and refills the freed slot. The S2-ID note moved to the caption.
- **Legend:** shorter labels, and "audited safe" added (grey check), distinct from "kept" (lavender check, a retrieval outcome).

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{fig_method.pdf}
  \caption{...}  % see below
  \label{fig:method}
\end{figure*}
```

## Caption

Notation follows the methodology draft (`main.pdf`, Section 3 and Appendix B).

**Selective evidence propagation on top of SAFE-Mem (illustrative toy example).** **(a)** Each external memory belongs to an incident root with trusted provenance: contributor, context and batch. Five audit tickets, the same for R, C, M and S, record verdicts in an evidence ledger that counts at most one vote per root. Four tickets flag attacker A's seeds as unsafe (✗), and one confirms a benign item of contributor B as safe. Under the optional boundary-verification protocol, the fifth ticket instead audits A's other batch. An unrelated contributor U relays a near-copy of an unsafe-audited seed; U itself has no audit evidence. **(b)** S extends distrust from audited to unaudited memories only over scopes the evidence supports. Step 1 checks the support gates (Eqs. 8–9) for the unaudited record ZX-91:
- **batch:** the contributor has ≥ θ_bat unsafe roots in the batch;
- **context:** it has ≥ θ_ctx unsafe roots in ≥ δ_ctx batches of the context;
- **contributor:** it has ≥ θ_src unsafe roots and ≥ δ_src qualifying contexts, each with ≥ θ_Q unsafe roots in ≥ δ_Q batches.

Each active scope has risk r = (1+n⁻)/(2+n⁻+n⁺), where n⁻ and n⁺ count distinct unsafe and safe audited roots, and penalty d = max(0, r − ½). S takes D, the largest d over the active scopes. It withholds a record when D ≥ τ (inclusive), and otherwise ranks it by s − λD, where s is cosine similarity. The bars show d for n⁻ = 0, 1, 2 with n⁺ = 0, against τ at its main setting. In the localized example only the batch scope is active. Batch 1 has n⁻ = 2, so r = 3/4 and d = 1/4 = τ, and S withholds the attacker's unaudited planted claim (ZX-91). It keeps the same contributor's useful note (Larkspur), which contextual reputation (C, context scope, ungated) and multi-scope reputation (M, maximum over all three scopes, ungated) discard; R propagates over no scope. These outcomes are those of the frozen decision rule run on this toy ledger. **(c)** S acts inside SAFE-Mem's governed retrieval, after its unchanged admission check α(x, q). After re-ranking, freed slots are refilled, so the top k claims and m chunks are still served, as shown for Q1. Provenance scopes cannot reach U's relay (S assigns it D = 0). SL is an exploratory extension, designed after the locked held-out test (Appendix B). During candidate selection it vetoes any non-principal claim whose embedding has cosine ≥ η to a claim of a root with an unsafe audit; a copy of an unaudited claim is not vetoed. Unlike S, SL also counts unsafe audits that were later superseded or retracted, a limitation of the evaluated implementation. The exploratory hybrid S2-ID adds MemLineage's sensitive-action gate and its recorded sensitivity verdicts: for a sensitive query whose final context contains any non-principal memory, it clears that context. S2-ID is evaluated under Sybil and laundering attacks, which move poison outside the audited scopes; the gate uses no identity signal and does not detect Sybils. SL and S2-ID were evaluated on the development split and, as replication evidence (reused MPBench v4 split; not fresh held-out, not confirmatory), in protocol v2. User-owned and unknown-origin memories receive no source penalty, and answer judgments never update trust.

**Parameters.** All thresholds are fixed constants: none adapts at run time or depends on batch size. The main evaluated setting of S, fixed before the locked held-out test, is θ_bat = 1, θ_ctx = δ_ctx = 2, θ_src = 4, δ_src = 2, θ_Q = δ_Q = 2, τ = 1/4 and λ = 1/2. Retrieval uses the reproduced SAFE-Mem configuration with k = m = 4, and SL uses η = 0.8. Development-split ablations varied θ_ctx, θ_src, τ, η and the audit budget, one at a time. The figure illustrates the mechanism on a constructed example with fictional content; its outcomes are not experimental results, and evidence that S, SL and S2-ID work comes only from the evaluation sections.

## Notation and evaluated settings

The figure writes thresholds as parameters, aligned with the methodology draft. This is a presentation choice only: the algorithm, code, protocol, configurations and data are unchanged. The frozen implementation is exactly the symbolic rule at the main-setting values below.

| Symbol (draft) | Meaning | Main setting | Code | Varied? |
|---|---|---|---|---|
| θ_bat | batch gate: min. unsafe roots of the contributor in the batch | 1 | `ledger.py:316` (`any(...)`) | literal; never varied |
| θ_ctx | context gate: min. unsafe roots in the context | 2 | `ledger.py:318` | literal; dev ablation {2, 3} (`ablations.py:49, 73-77`) |
| δ_ctx | context gate: min. distinct batches among them | 2 | `ledger.py:318` | literal; never varied |
| θ_src | contributor gate: min. unsafe roots of the contributor | 4 | `ledger.py:326` | literal; dev ablation {3, 4, 6} |
| δ_src | contributor gate: min. qualifying contexts | 2 | `ledger.py:326` | literal; never varied |
| θ_Q, δ_Q | a qualifying context: ≥ θ_Q unsafe roots in ≥ δ_Q batches | 2, 2 | `ledger.py:320-325` | literal; never varied, **including in the θ_ctx ablation** (`ablations.py:74-76`) |
| r, d, D | risk, scope penalty, max over active scopes (Eqs. 6–7) | — | `GroupStats`, `ledger.py:67-78`; `policies.py:135` | — |
| τ | withhold when D ≥ τ (inclusive; exact `Fraction` comparison) | 1/4 | `Policy.threshold`, `policies.py:64, 137` | dev ablation {0.15, 0.25, 0.35} |
| λ | ranking weight, s − λD | 1/2 | `Policy.weight`, `policies.py:63, 143` | never varied |
| η | SL cosine threshold (Eq. 12); **called `tau` in code and in the protocol-v2 documents** | 0.8 | `DEFAULT_TAU`, `lineage.py:30`; `TAU`, `pipeline.py:51` | dev ablation {0.7, 0.8, 0.9} |
| k, m | claims and chunks served (step 4) | 4, 4 | `k`, `adapter.py:188, 382`; `evidence_slots`, `adapter.py:383` | never varied |
| α(x, q) | SAFE-Mem admission (draft Eq. 2) | — | `TypedStandingMemory._admits`, `memory/typed.py` | — |

The audit budget T (5 tickets) was also varied on dev ({3, 5, 10}). Not parameterized (design choices): the Beta(1,1) risk estimate and its ½ baseline, the maximum over active scopes, and one vote per root.

**Why θ_Q, δ_Q are separate from θ_ctx, δ_ctx.** In the frozen code the qualifying rule and the context gate are two separate literal pairs that happen to be equal (2, 2). The θ_ctx = 3 dev ablation changed only the context gate; the qualifying rule stayed at (2, 2). Writing the contributor gate as "the context gate holds in ≥ δ_src contexts" would claim a shared dependency that the ablation did not have.

**Consequences of the main setting** (for the appendix):
- **Withholding threshold:** d ≥ τ ⟺ n⁻ ≥ (4τ + (1+2τ)n⁺)/(1−2τ); at τ = 1/4 this is n⁻ ≥ 3n⁺ + 2 (draft Prop. 3.2). The worked example (n⁻ = 2, n⁺ = 0 → r = 3/4, d = 1/4) lies exactly on the boundary, as the chart shows, and is withheld only because the comparison is inclusive.
- **Context count:** θ_ctx binds only when θ_ctx > δ_ctx. At (2, 2) the count is implied by the batch condition.
- **Contributor count:** θ_src binds only when θ_src > δ_src·θ_Q. At 4 = 2·2 it is implied, so the θ_src = 3 ablation is identical to the default by construction, not an empirical robustness result.
- **Fixed thresholds:** they do not depend on batch size, context size or contributor history. Only the evidence counts change as audits arrive, are superseded or are retracted.

**Known limitation (SL, documented, not changed).** S reads only active audits. SL's reference set is built from every UNSAFE audit event in the snapshot (`lineage.py:65-67` iterates over `ev.events`), so an unsafe audit that was later superseded or retracted still blocks near-copies. This contrasts with draft App. A ("superseded or retracted evidence is never revived implicitly"). The code is frozen and unchanged; the paper should state this.

**Evaluation history of SL and S2-ID** (as of 22 Nov 2026, from this repository):
- Both were designed after the locked v1 test, and `lineage.py` is not in the v1 freeze.
- First scored on the development split (retrieval exposure).
- Protocol v2 Option B, P-B2 (GPT-4o-mini), completed 20 Nov: SL (H5) and S2-ID (H4) on the reused MPBench v4 split, labelled "replication, not confirmatory". The early analysis is recorded as a protocol deviation (`logs/deviation_early_gpt_analysis.md`); the final combined analysis follows P-B3 (README §10).
- The LoCoMo and MINJA protocols contain further runs. The caption names only the evaluation types and quotes no results.
- The 15 Nov version of this caption said "development split only", which became outdated with P-B2.

## Verification against the implementation

| Figure element | Code |
|---|---|
| Provenance (contributor, context, batch, attribution) | `Provenance`, `src/ams/research/dynamic/models.py:58` |
| One vote per root; corrections supersede, retractions remove | `EvidenceSnapshot.observations`, `ledger.py:274`; `_project`, `ledger.py:89` |
| Gates (main setting 1; 2, 2; 4, 2; 2, 2) | `active_scopes`, `ledger.py:304-327` |
| r, d (n⁻, n⁺ = distinct unsafe / safe roots) | `GroupStats`, `ledger.py:67-78` |
| Chart bars: d(0) = 0, d(1) = 1/6, d(2) = 1/4 for n⁺ = 0; red iff d ≥ τ at τ = 1/4 | Eq. 6 evaluated exactly in the generator (`num * 4 >= den`) |
| S takes the max over supported scopes; C uses context; M uses max(batch, context, contributor) | `Policy.decide`, `policies.py:119-136` |
| Withhold at D ≥ τ (inclusive); otherwise score = s − λD | `policies.py:137-143` (weight 0.5, threshold 0.25) |
| Only authenticated external roots propagate; principal and unknown roots get no source penalty | `policies.py:119, 141`; `ledger.py:307` |
| Retrieval order: admission α(x, q) → direct findings → policy → re-rank and refill to k claims + m chunks → conflict check | `GovernedRetrieval.retrieve_with_trace`, `adapter.py:240-399` |
| Refill (Q1 slot diagram): a withheld claim frees its slot, which the next eligible claim fills; R does not withhold the unaudited ZX-91 | `adapter.py:346-383` (full-pool refill); Alg. 2 of the draft |
| Conflict check (step 5) only marks claims contested and removes none | `adapter.py:382-399`; `_resolve_conflicts`, `memory/typed.py:828-877` |
| Localized example: only the batch scope is active (2 unsafe in batch 1); context not met (both flags in b1); contributor not met (no context has flags in 2 batches) | `active_scopes`, `ledger.py:313-326` |
| Table values: R none; C ctx 1/4 (2 unsafe in X); M all three scopes, max = 1/3 (contributor: 4 unsafe in A); S bat 1/4 for batch 1, no active scope for batch 2 | **executed:** `verify_toy_example.py` (frozen `Policy.decide` on the toy ledger); localized placement in `design.py` (`PLACEMENT`) |
| SL per candidate, before ranking: cos ≥ η to a claim of an unsafe-audited root (including superseded or retracted, see limitation); principal exempt; verified-safe not vetoed | `LineagePolicy.decide`, `blocked_records`, `lineage.py:54-102` |
| S2-ID on the final context: sensitive query + any non-principal entry → empty context; always includes SL | `_GatedReader`, `sv2.py:95-116`; `CANDIDATES`, `apply`, `sv2.py:47-150` |
| Audit allocation: 4 seed tickets (unsafe; 2 per context) + 1 benign ticket of B (safe), same IDs for R, C, M, S | `oracle_audits`, `integration.py:308-343`; `AUDIT_TICKETS`, `design.py` |
| Boundary verification (caption only): the 5th ticket audits another batch of the flagged contributor instead of the benign one | `_followup_ticket`, `adaptive.py:333-358` |
| Unlinked relay (U): own root; in the workload it copies A's context-Y seed s2a, drawn here as a copy of a context-X seed for compactness (lineage ignores context) | `design.py:20-28`; `integration.py:153-158`; `adaptive.py:275-279` |

Not shown in the figure (by design): ACL checks (all-allow in the experiments), external evidence chunks (hidden by `external_evidence=false`), and any results.
