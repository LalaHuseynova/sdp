# LoCoMo + SAFE-Mem: readiness report (24 Nov 2026)

**Status:**
- Implemented, validated with free checks only, and frozen.
- **No paid call has been made; $0 spent.**
- Waiting for the owner's approval.

**Protocol:** `reports/PROTOCOL_LOCOMO_SAFEMEM.md` (supplementary, exploratory).

**Freeze:** `research_data/locomo_safemem/freeze/manifest.json`.
- Digest `2ec7d1bcfb397d051f7938c86031695960dc04676a7e8142bc1bf9245645c62a`.
- 155 files: this study's code and protocol, every frozen dependency, the prompts, SAFE-Mem's LoCoMo configs, the data, the recorded verdicts and the exact construction request list.
- `verify`: ok. The LoCoMo v2 freeze `3a2c2df8…` is intact.
- No frozen MPBench, SAFE-Mem or LoCoMo v2 file was modified (git status clean for `src/`, `prompts/`, `configs/`, `locomo_v1/`, `locomo_v2/`, `locomo_v2_supp/`, `data/`).

## 1. What the study answers

> Does S keep its MPBench behaviour when LoCoMo is evaluated on Original SAFE-Mem's own claim memory, under MPBench Option B's attacks, audits, methods and metrics?

- It removes the dataset/substrate confound: MPBench/SAFE-Mem vs LoCoMo/RAG (v2) vs LoCoMo/SAFE-Mem (this study).
- Every attack instance is identical to LoCoMo v2 (same generator and seeds), so the two LoCoMo substrates are paired.

## 2. What was built (`locomo_safemem/`, worktree `sdp-locomo-audit`, branch `locomo-audit`)

| Module | Role |
|---|---|
| `store.py` | SAFE-Mem stores: `write_dialogue` per session (its published LoCoMo ingestion and settings), each poison turn, relay copy or Sybil turn as its own write, MPBench-style roots, provenance, audits |
| `governance.py` | the single new semantic (`counterpart_turn` counts as an external source); an exact fast retrieval path; runtime caches; derived states |
| `scenarios.py` | the full experiment matrix (§3) |
| `evaluate.py`, `run.py` | per-store evaluation of 11 methods + S2-BS; parallel dry / mock / precompute / final passes; RandEC stage |
| `paid.py` | P1a construct, P1c conflicts, P2 defences, P3 answers: strict guards, cache, STOP, breaker, auto-resume, approval gate |
| `analysis.py`, `tables.py` | v2 metrics; MPBench H1–H6 (descriptive); contrasts with exact CIs; MPBench-style tables with the three-setting comparison |
| `freeze.py`, `equivalence.py`, `repro.py`, `tests/` | reproducibility manifest, fidelity checks |

## 3. Experiment matrix

**Conversations, orientations and draws.** 10 conversations (dev conv-48/49, 8 held-out) × 2 orientations × 5 draws.

**Stores and conditions:**
- `loc` 4 shapes × (A1, A2; 1s / spread also fn20, fp1, late, follow-up);
- `sybil` k2, k4, k8 (k2 also fn20, fp1, late, follow-up);
- `shift`; `relay` ×2;
- `frame` ×3 (false accusations, no attack);
- `embed` (ingestion sensitivity).

**Methods:** 11 main (Original SAFE-Mem, A-MemGuard, MemLineage, LLM sanitiser, RandEC, R, C, M, S, SL, S2-ID) + S2-BS.

**Not transferable, documented with reasons:** the no-signal control, context shift, own-batch Sybils, laundering by an innocent contributor, framing, cohabit (protocol §4).

## 4. Validation (all free)

| Check | Result |
|---|---|
| Governance layer = frozen MPBench layer (Option B store G-T00, 6 conditions × 7 arms × 35 probes, SAFE-Mem conflict downgrades active) | **identical, 1,470/1,470** |
| Test suite (14 tests) | **14 passed**. Covers: counterpart binding, MPBench equivalence, static = Original SAFE-Mem `retrieve`, settings = `v31_locomo_withhold`, poison / Sybil / relay provenance, fast path and derived states = frozen loads on four store types × 7 arms, runtime caches change nothing, S2-ID shortcut = frozen `sv2` gate, late audits = MPBench two-state semantics, pairing with v2 |
| Dry pass (all 10 conversations) | 120 shards, 0 errors. **Exact** construction list: 8,548 requests |
| Mock end-to-end (dev conv-48/49, full matrix, all draws) | 24 shards, 0 errors. 1,600,867 retrievals, **64,021 re-checked through the frozen `GovernedRetrieval`: all identical** (plus cached decisions re-checked against the frozen `decide`). 811,980 jobs, 63,508 contexts. Mock defences + RandEC (8,870 texts). 76,946 answer keys answered and judged by the frozen v2 engine (0 failed, 0 missing). Analysis and tables produced |
| Reproducibility (one full shard recomputed from scratch) | **identical**: jobs, contexts, store metadata, defence exports (40,301 jobs) |
| Freeze + verify | ok (digest above) |

**Bugs found and fixed during validation:**
- the relay metric population (now v2's: targets whose poison is audited unsafe);
- late audits (now two independent states, as MPBench);
- a speed patch clash with LoCoMo's feasibility module;
- RandEC moved to its own stage because it is too slow inline.

Mock outcomes have no scientific meaning; only the plumbing is validated.

## 5. Cost (`research_data/locomo_safemem/estimate.json`; protocol §9.1)

| Paid stage | Count | Projected | Proposed cap |
|---|---|---|---|
| P1a SAFE-Mem construction (extraction + classifier) | **exact**: 8,548 requests | $1.65 (bound $10.73) | $12 |
| P1c SAFE-Mem conflict checks | exact after precompute (mock: ≈ 2,600) | < $0.50 | $3 |
| P2 A-MemGuard + LLM sanitiser (loc stores) | ≈ 256k requests (mock-projected) | ≈ $48 | $60 |
| P3 answers + judges | ≈ 341k keys (mock-projected) | ≈ $40 | $55 |
| **Total** | | **≈ $90** | **$130** |

**Note on the earlier estimate.** The $15–25 in the earlier assessment was for a *minimal* two-cell design. This is the full Option B matrix that was asked for.

**How the estimates are firmed up.** P2 and P3 are re-counted exactly from the real contexts (`estimate-final`, free) before they are sent. Each stage stops at its cap.

**Options to reduce cost** (each needs a small scoped change and a re-freeze before approval):
- A-MemGuard + LLM sanitiser on 2 shapes instead of 4: ≈ −$24.
- Drop S2-BS and the A2 / follow-up conditions from answering: ≈ −15% of P3.

## 6. Execution plan (commands under WSL: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_v2/run.sh -m locomo_safemem …`)

1. The owner signs `research_data/locomo_safemem/owner_approval.json`: digest + caps (draft: `owner_approval.DRAFT.json`).
2. `paid construct`: P1a, about 15–30 min.
3. `precompute --workers 6`: free, about 13 h. It records the exact conflict checks.
4. `paid conflicts`: P1c, minutes.
5. `final --workers 6`: free, up to about 13 h. Shards whose conflict replies contain no contradiction are reused exactly.
6. `randec --workers 6`: free, about 4.5 h.
7. `estimate-final`: free. Exact P2 and P3 counts; stop here if they exceed the caps.
8. `paid defences`: P2, about 2–3 h. `paid answers`: P3, about 3–4 h; dev conv-48 first.
9. `analyse`, then `tables`: once.

**Pause and resume.**
- `stop` writes STOP files. `status` shows the guards.
- Rerunning any command resumes it (cached calls and finished shards cost $0).
- The PC must stay awake during the free passes. A keep-awake helper is used (it changes no setting).

**Total wall time:** about 1.5–2 days, mostly free local compute.

## 7. Risks and limits (protocol §11)

- **Exploratory:** the LoCoMo v2 results were seen first.
- **Sample size:** 8 held-out conversations (min p = 1/256).
- **Scope:** one answer model; one attack template.
- **Granularity:** SAFE-Mem dialogue claims are not turn-attributed, so audits of genuine turns act on a speaker's session (reported).
- **Mixed-speaker chunks:** about 41% of chunks in the mock are mixed-speaker, so they carry an unknown attribution (reported).
- **Mock cap saturation:** about 55% of session writes hit 20 claims in the mock. The real value comes from P1a and is a pre-registered diagnostic.
