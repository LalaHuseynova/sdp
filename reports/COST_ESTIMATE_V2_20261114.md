# Protocol v2: dry-run cost and runtime estimate, and budget proposal (step 1.12)

Status: **done, 14 Nov 2026. Free: no paid call, no held-out data, no algorithm changed.** For the owner's step 2.1 decision (plan.md decision 31: "exact figure from the free dry run; then the owner decides between raising the allowance and reducing scope").

- Code: `src/ams/research/protocol_v2/cost.py`; CLI `scripts/estimate_cost_v2.py` (`measure`, `estimate`); tests `tests/test_v2_cost.py` (17 at completion, 19 after the runtime correction); runtime Fix 1 in §4b.
- Data: `research_data/protocol_v2_cost_measure_dev_v3_20261114/`
  - `G-D00..G-D03/`: per-method journals and `measure.json`;
  - `estimate.json`: every input and output;
  - `estimate.md`: the full rendered tables.

## 1. How the estimate was made

| Quantity | Source |
|---|---|
| Cost per call (GPT-4o-mini) | **Measured:** the actual USD of every completed dev call in the guarded ledger (`controlled_workload_session_v2_20261108`): answer $0.000130, judge $0.000048, conflict $0.000016, and so on |
| Published defences' own calls | **Measured:** dev run summaries (`published_paid_dev_v3_20261112`): A-MemGuard $0.001125 per context, sanitiser $0.000139 per context, MemLineage $0.000022 per question (27 questions per group) |
| Claude prices | Pricing files (list price, no discounts): Sonnet $2 / $10 and Haiku $0.10 / $0.50 per million input / output tokens |
| Number of calls | **Measured:** the free precompute (`pipeline.evaluate`, `answer=False`) of 7 internal methods × all 272 conditions on 4 dev groups. Identical requests are sent once, so a stage pays per **distinct** prompt. |
| Methods that cannot be measured free (A-MemGuard, MemLineage, sanitiser, S2-ID, "+R") | **Low** = no prompt beyond those measured. **High** = a strict upper bound: a filter of a retrieval cannot produce more distinct contexts than that retrieval has. |
| Generation output | The prompts' word limits (attack 180–450, benign 120–380 words) × 1.4 tokens/word + 200 JSON tokens. Low = the midpoint, high = the upper limit. The hard bound (max_tokens on every call) is reported separately. |
| Stage 1 and I1 | **Measured:** dev Stage-1 requests per group (35 classifier, 40 extraction, 40 retention, cached ones included), × measured call cost |

## 2. Main measured facts

1. **Few distinct prompts.** A group has about 66,600 (condition, method, question) rows for the 7 free methods, but only **631 distinct answer prompts** (297 of them judged) and 3 distinct conflict checks.
2. **Original SAFE-Mem's retrieval is identical in all 272 conditions** (0 of 140 probes vary). It gives 35 contexts per group.
   - The published defences filter that retrieval, so their own calls are paid **once per question, not per condition**.
   - A-MemGuard at 96 groups: $3.78 (measured basis), the same as the protocol's earlier ≈ $3.8.
3. **RandEC's output is also identical in every condition, and it is deterministic** (seeded by its input text).
4. **Generation dominates the full plan:** 1,440 attacks + 1,957 benign documents ≈ 2.0–2.6 M output tokens at $10 per million gives **$22.76–29.05**. The protocol's rough guess was $2–8.
5. **The Haiku high bound is pessimistic.** It assumes every answer uses its full 200 tokens; GPT-4o-mini averages 35.

## 3. Cost by scope option (all paid stages; ablations option A)

| Scenario | Low | High | Sum of proposed caps (high × 1.3) | Fits ≈ $26.57 left? |
|---|---|---|---|---|
| **A.** Full plan: 96 generated groups + MPBench v4 replication | $43.52 | $81.65 | $108.60 | **no** (2 caps also above code ceilings) |
| **B.** MPBench only: v4 test split (24 groups) as the main result | **$4.44** | **$11.86** | **$16.40** | **yes** |
| **C.** MPBench v4 main + 32 generated groups (every cell) | $17.08 | $31.87 | $42.80 | only at the low end (generation cap above its ceiling) |

**Proposed caps per paid purpose** (each still needs its own approval at its stage):

| Purpose | A | B | C | Code ceiling |
|---|---|---|---|---|
| v2_generation (Sonnet) | $38.00 ✗ | – | $13.00 ✗ | $10 |
| v2_inclusion | $1.50 | – | $0.45 | $5 |
| v2_stage1 | $3.00 | – | $1.00 | $5 |
| v2_stage3 (answers, judges, conflicts, ablations) | $31.00 | $8.00 | $16.00 | $80 |
| v2_published_amemguard | $14.00 | $3.00 | $6.50 | $20 |
| v2_published_sanitiser | $2.00 | $0.35 | $0.80 | $10 |
| v2_published_memlineage | $0.10 | $0.05 | $0.05 | $0.50 |
| v2_backbone_answer (Haiku) | $19.00 ✗ | $5.00 | $5.00 | $10 |

✗ means the cap is above the code ceiling. Raising a ceiling is a code change that needs the owner's approval; the guard otherwise refuses the approval file (step 1.9a).

**Pending-scope variants** (change in cost):
- replication on every cell instead of Table 1 + hypothesis cells: +$1.22 to +$1.89;
- ablations option B (adds Sybil/laundering cells for the source gate and τ): +$0.74 to +$2.97;
- Claude Haiku instead of Sonnet as generator (would change owner decision 22): −$21.63 to −$27.60.

The full per-stage table is in `estimate.md`.

## 4. Runtime

| | Current code | With the RandEC cache (proposed) | With the cache + paid stage reusing the free precompute (proposed) |
|---|---|---|---|
| Free precompute, 96 groups | ≈ 1,131 CPU-hours (RandEC recomputed in all 272 conditions: ≈ 9.6 h per group) | ≈ 196 CPU-hours | ≈ 196 CPU-hours |
| Paid 4.2+4.3 stage, 96 groups (one process) | 48–49 days | 9–10 days | **25–49 h** |
| Paid 4.2+4.3 stage, 24 groups (option B) | 12 days | 2.3–2.6 days | **6–12 h** |

- **Measured per group:** internal methods ≈ 120 min of CPU, of which SL alone is ≈ 39 min, because it is slow on the Sybil and laundering conditions. RandEC ≈ 65 s per condition.
- **The paid stage is one process.** The guarded session is single-writer, and the current `pipeline.evaluate(answer=True)` recomputes retrieval (and RandEC) itself before sending calls one at a time, at about 1 s per call. That rate comes from OpenRouter timestamps, which have 1-second resolution.
- **Proposed fixes, both result-identical engineering changes, NOT algorithm changes, pending approval at step 2.1:**
  1. Cache RandEC by input text. Its input is condition-invariant and its output deterministic.
  2. Let the paid stage read the contexts from the verified free-precompute journals instead of recomputing them. The pipeline already states that conflicts never change selection.

  Each would be implemented tests-first, with a check that the cached and recomputed outputs are identical.

> **Correction (14 Nov 2026, after the owner asked for a runtime breakdown):** the runtime figures above are **too low**. `cost.runtime()` omitted (a) the retrieval that A-MemGuard, the LLM sanitiser, MemLineage, their "+R" variants and S2-ID redo in the paid process (≈ 2.2 CPU-h per group), and (b) the published defences' own API calls (≈ +45% calls). Corrected for option B (24 groups): **current code ≈ 14.4–15.6 days** of the single paid process (not 12); with the RandEC cache ≈ 4.6–5.8 days; with both fixes ≈ 1.0–2.2 days for the paid process plus ≈ 12 h of free parallel precompute (not 6–12 h). Cost figures are unaffected. The formula will be corrected (tests first) only after owner approval.

## 4b. Runtime fixes: implementation result (14 Nov 2026, owner-approved, free)

The owner approved Fix 1 and Fix 2 "strictly as runtime optimizations", on two conditions: tests first, and "If exact equivalence cannot be demonstrated, stop and report the issue before proceeding". No frozen defence algorithm was changed, no paid call was made, no held-out data was opened, nothing was committed or frozen.

**Fix 1: RandEC cache (implemented and verified identical).**
- **Code:**
  - `src/ams/research/protocol_v2/randec_cache.py` (`cached_randec`): memoizes `RandECClassifier.harmful` by the exact text. On a cache hit it restores the Python global `random` state that the real call left behind. The real call reseeds `random` from the text, so this side effect is reproduced exactly.
  - `scripts/run_protocol_v2.py randec()` returns the cached classifier. The frozen class is not modified.
- **Tests (written first):** `tests/test_v2_randec_cache.py` (7), plus `test_randec_cache_leaves_every_row_identical` in `tests/test_v2_pipeline.py`. They check:
  - identical verdicts and global random state after every call;
  - one model run per distinct text, with the exact text as key;
  - `filter` goes through the cache; wrapping twice is refused;
  - on the real DistilBERT model: cached = uncached, and numpy's generator is untouched;
  - the free and paid (mock) journals are identical for static, randec, R, randec+R, S, a_memguard and SL.
- **Real-data check:** `research_data/protocol_v2_randec_cache_check_dev_20261114/verification.json`.
  - Setup: G-D00, 4 conditions, methods static / randec / R / randec+R / S, 700 rows.
  - Result: **identical: true, 0 differing.** Wall time 569 s uncached vs 117 s cached; 83 distinct RandEC texts.
- **Two findings (no effect on results, reported for transparency):**
  1. **torch's global RNG.** DistilBERT's forward pass advances torch's global generator, so after a cache hit torch's RNG state differs from an uncached run. This is unobservable: the logits are bit-identical under 4 different torch seeds (eval mode), and no code in `src/ams` uses torch (both tested).
  2. **Pre-existing reproducibility issue in RandEC (not caused by the cache).** Its erase-and-check sampling goes through `list(set(...))`. Across separate processes, the sampled subsequences therefore depend on `PYTHONHASHSEED`. Within one process, cached and uncached runs are identical. **Recommendation, for owner decision at step 2.1:** fix `PYTHONHASHSEED` (for example `0`) for every v2 precompute and paid run, and record it in the freeze.

**Fix 2: paid stage reuses the free precompute (STOPPED: exact equivalence cannot be shown).**
- **The free precompute answers every conflict check with the placeholder reply "compatible".** A real reply containing "contradict" sets `claim.contested = True` (`src/ams/memory/typed.py:854`, `:867`). That puts a **"contested" mark into the memory text in the prompt** (`typed.py:932-933`). The flag stays on the claim for the rest of the probe.
- **Selection would not change, but the prompt can.** Selection (which entries are retrieved) does not depend on the reply. The prompt text sent to the answer model can.
- **On dev this actually happens:** 4 of the 61 real conflict replies in the dev ledger were "contradict".
- **The existing test only passed because of its mock.** `test_precompute_is_free_and_predicts_the_paid_prompts` passes only because its mock always answers "compatible".
- **Consequence:** reading the prompts from the free precompute would not reproduce the original pipeline's prompts, so Fix 2 was not implemented.
- **Exact alternative (proposal only, NOT implemented, needs owner approval):** a two-phase run.
  1. A tiny paid pass sends only the distinct conflict checks; there are about 3 per group, because the served sets do not depend on the replies.
  2. The free precompute is rerun, replaying the real conflict replies from the ledger, so its prompts become exactly the paid prompts.
  3. The paid stage then reads the contexts from that precompute after hash validation.

  This would remove the internal methods' recomputation (≈ 2.0 CPU-h per group) from the single paid process. The published methods' filtering (≈ 2.2 h per group) would stay unless treated the same way.

**Updated runtime (formula corrected tests-first; `cost.runtime()`, `cost.call_seconds()`).** Per group:
- CPU: internal methods 2.00 h; published methods' retrieval in the paid process 2.23 h; RandEC 9.78 h in every condition, or 0.04 h with Fix 1.
- API: 1,342–2,721 calls (published defences' own calls included) × 1.0–2.08 s per call (median and mean of the dev ledger's gaps), giving 0.37–1.57 h.
- Rate-limit delay: none observed in 11,785 dev calls, so none is added.

| Groups | Current code | **With Fix 1 (implemented)** |
|---|---|---|
| 24 (option B) | 14.4–15.6 days | **4.6–5.8 days** |
| 32 | 19.2–20.8 days | 6.2–7.8 days |
| 96 | 57.5–62.3 days | 18.6–23.3 days |

Free precompute at 96 groups: 1,131 CPU-h with the current code, 196 CPU-h with Fix 1; it runs in parallel. The §4 table and the correction note above are kept for the record. This table supersedes them.

## 4c. Fix 2, three-step version, and a fixed PYTHONHASHSEED (15 Nov 2026, owner-approved, free)

The owner approved two things:
- the three-step Fix 2, "only if exact equivalence with the original paid evaluation pipeline can be demonstrated";
- a fixed PYTHONHASHSEED for all Protocol v2 runs.

No paid call was made, no held-out data was opened, no frozen algorithm was changed, and nothing was committed or frozen. `git diff` is empty for `src/ams/baselines`, `memory`, `workload`, `provisional_run`, `sequential`, `retrieval`, `third_party` and `prompts`.

**Design** (`src/ams/research/protocol_v2/two_phase.py`; the pipeline gains a `contexts=` option):
1. **Free:** the placeholder precompute records every distinct conflict-check request.
   - These requests do not depend on the replies. Selection never does, every served pair is checked, and the request renders the raw claim texts. Tested by answering "compatible" vs "contradict" everywhere: the same requests come out.
   - **Paid** (tiny; about 2–3 checks per group on dev): only those requests are sent through the guarded v2_stage3 session.
2. **Free, shardable:** the precompute is rerun, replaying the **real** replies. It stores per row:
   - the retrieved entries, so the contested labels are included;
   - the frozen answer template, the answer model and the conflict call ids.
3. **Paid:** answers, judges and the published defences read those contexts. Before anything is written or sent, step 3 checks:
   - the code version, and the inputs fingerprint (bundle plus a SHA-256 of every Stage-1 store);
   - that the conditions are identical, and the hashes of every blob and row;
   - every internal row against its recomputation;
   - every conflict reply against the live paid ledger. This is an exact $0 reuse, and a guarded ledger is checked first, so verification can never pay.

   S2-ID needs MemLineage's paid classifier, so it is still computed the original way inside the paid process.

**Equivalence results:**

| Check | Data | Result |
|---|---|---|
| Unit: full journal vs original `evaluate(answer=True)`; all 16 methods, 3 conditions including late audits; mock answers "contradict" to half the conflict checks | test fixture | **identical** (every field, including `model_call_ids`); contested labels present; the same distinct requests dispatched |
| Guarded end to end: real `ConstructionSession`, httpx mock transport | test fixture | **identical** journals; **identical set of wire requests**, each sent once; **identical spend** per purpose |
| Real dev store G-D00: 5 conditions (localized, distributed, sybil_k2_rand_d0, random_spread_d0, imp_localized_late_d0) × 16 methods; real dev-ledger conflict replies; real cached RandEC | dev | **2,800 rows identical**, 0 differing, the same requests sent. Its 2 real replies were "compatible", so no contested label occurred. |
| Same, with every conflict reply "contradict" (stress) | dev | **2,800 rows identical**; **119 stored contexts carry a "contested" label**; the same requests sent |
| Mutation checks: step 2 forced back to placeholder replies, or conflict ids dropped | fixture | both **detected** (rows differ) |
| Validation: other inputs, other conditions, stale conflict reply, tampered blob, duplicate shard, missing reply in step 2, guarded ledger without step 1 | fixture | all **refused**, before anything is written or paid |

On the real-data slice the paid process took 22 s with fix 2, against 488 s for the original path.

**PYTHONHASHSEED = 0** (`src/ams/research/protocol_v2/hashseed.py`). Seed 0 disables string-hash randomization.
- `run_protocol_v2.py` and `estimate_cost_v2.py` re-execute themselves with the seed.
- Every run command (`precompute`, `conflicts`, `contexts`, `paid`, `measure`) refuses an interpreter without it, before loading data.

Verification on G-D00, same 5 conditions, all 9 free methods:

| Comparison | Result |
|---|---|
| Seed 0 vs seed 0 vs seed 1 vs seed 2 (separate processes) | **all 1,575 rows identical**, internal methods and RandEC (kept/flagged identical) |
| Seed 0 internal rows vs the step-1.12 journals (run with random seeds) | **1,225 / 1,225 identical** |

So the fixed seed changes no frozen method's output. It is a safeguard: RandEC's sampled subsequences depend on the seed (`list(set(...))`), but on this slice no verdict changed.

**Updated runtime** (`cost.runtime()`, tests first):

| Groups | Current code | Fix 1 | **Fixes 1 + 2** |
|---|---|---|---|
| **24 (option B)** | 14.4–15.6 days | 4.6–5.8 days | **25–54 h** |
| 32 | 19.2–20.8 days | 6.2–7.8 days | 34–72 h |
| 96 | 57.5–62.3 days | 18.6–23.3 days | 102–217 h |

- With both fixes, per group:

  | Part | Time | Type |
  |---|---|---|
  | S2-ID recomputed (timed as SL) | 0.65 h | CPU |
  | RandEC on the stored contexts | 0.04 h | CPU |
  | 1,342–2,721 calls | 0.37–1.57 h | API |

  No rate-limit delay was observed (11,785 dev calls).
- Free precompute: steps 1 and 2 are two passes of the internal methods, ≈ 4.0 CPU-h per group. That is ≈ 96 CPU-h for option B (384 for 96 groups), and it runs in parallel across groups.

**Remaining risks:**
1. **The equivalence is shown with mock answers and with real or forced conflict replies on dev data, not with live GPT replies.** The paid stage itself is unchanged code (the same requests, the same guard). The only paid-path difference is that the answer is dispatched directly rather than through `RecordedReplayClient`, and the guarded test shows the wire requests are identical.
2. **Step 1 needs its own owner approval at the paid stage.** It uses the v2_stage3 cap, and the same session directory must be used in steps 1 and 3; otherwise step 3 refuses.
3. **S2-ID's retrieval stays in the paid process** (≈ 0.65 h per group). Precomputing it would need MemLineage's paid classifier first; this is not proposed.
4. **Disk:** contexts take ≈ 1.4 KB per row, ≈ 90 MB per group, ≈ 2.2 GB for option B, plus the step-2 journals.
5. **A partly written step-2 shard is refused.** It has no manifest until it finishes, and a rerun needs a new output directory.
6. **Old stores (dev, v4)** still need the prompt-checkpoint decision (pending from step 1.10). The verification used `ablations.checkpoint_prompts`, as step 1.12 did.

Data: `research_data/protocol_v2_two_phase_check_dev_20261114/` (`fix2/`, `fix2_all_contradict/`, `hashseed_*/`, `hashseed_comparison.json`, `scripts/`, `logs/`). Each `verification.json` holds the figures above.

## 5. Budget proposal (recommendation)

1. **With the current allowance (≈ $26.57), only option B fits.** Its caps total $16.40, leaving ≈ $10 of margin. It matches the owner's stated preference for now (MPBench replication table).
   - **Cost:** the main result is on a split used once before (protocol v1) and has 24 groups, so CIs are wider and H4/H6 are likely underpowered.
2. **Option A needs about $110 of caps.** That means roughly +$85 of allowance, plus raising two code ceilings (generation $10 → $38, Haiku $10 → $19).
3. **Option C needs about $43 of caps.** That means roughly +$17 of allowance, plus raising the generation ceiling to $13. It keeps one fresh held-out result.
4. **Whatever the scope,** approve the two runtime fixes at step 2.1. Without them, even option B's paid stage runs for about 12 days in one process.

The scope choice is the owner's. Nothing is approved by this report.

## 6. Assumptions and limitations

- 4 of 8 dev groups were measured. They agree closely: 35 static contexts each, 41 R contexts each, SL 279–422.
- v4 test groups have the same structure as dev (35 questions: 4 attack, 2 copy, 25 utility, 4 principal-utility); this was checked. Held-out v5 groups are assumed to be similar.
- Per-call costs are dev averages. Generated documents may be longer, so I1 and Stage 1 have a 2× high bound.
- **Generation:** tokens per word (1.4) and JSON overhead (200) are assumptions, and rejected generations are not regenerated (the spec counts include the 2.5× oversampling). The approved cap stops the stage before the hard bound ($101.83).
- The ablations on the replication split are scaled by groups from the measured dev jobs. Option B's cost is a bound (4 variants × S's distinct prompts in the Sybil/laundering cells).
- The precompute timings exclude periods when the Mac slept or the run was paused (monotonic clock).
- MemLineage questions per group (27) and A-MemGuard calls per context come from the dev localized runs.

## 7. Other things found during this step

- **RandEC offline.** RandEC tried to reach Hugging Face inside `no_network()`. `run_protocol_v2.randec()` now forces the local cache (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`), which also fixes a latent failure in `run_protocol_v2.py precompute`. Test added.
- **A flaky test.** `test_v2_imperfect_audits.py::test_late_reveals_audits_after_half_the_probes` picked one draw with `set.pop()` (hash-seed dependent) and failed about 1 run in 6. It now checks every draw, with the same intent. Test code only.
- **The tests caught two bugs in the cost model, now fixed:**
  - wrong registry family names for option B;
  - the replication's published-defence calls were filed under `v2_stage3` instead of their own purposes.
- **Owner decision 35 (during this step):** uninformative stays a Table 2 column labelled "no-signal control" and is excluded from the worst case. It is implemented at step 2.1 and does not change the cost.
