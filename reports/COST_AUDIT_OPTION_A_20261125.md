# Cost audit: MPBench Option B (actual) vs LoCoMo + SAFE-Mem Option A (projected)

**Date:** 25 Nov 2026.

**Type:** read-only audit.
- No code, protocol, cache, configuration or frozen file was changed.
- No paid API call was made, and no approval file was created.
- The LoCoMo files were read from an extracted copy of branch `sdp/locomo-backup` (commit `0861f2f`). The MPBench ledgers were read from copies of `research_data/protocol_v2_optionB_run_v1/sessions_rerun3/*`.

**Labels used:**

| Label | Meaning |
|---|---|
| **[M]** | Measured from provider receipts or files |
| **[R]** | Reconstructed from code and artifacts |
| **[A]** | Assumption |

## Executive summary

**Short answer:** the LoCoMo cost is mostly real experiment size, not waste.
- MPBench's published defences had to check **975** distinct memory contexts; Option A has about **49,000**.
- Per context, LoCoMo is actually about 20% *cheaper*.

**The projected $90 is probably too high.** The realistic estimate is **about $75** (range $65–95).

**The full frozen evaluation can't be made much cheaper without changing what it measures.** At most about $1–4 can be saved by fixing duplicate concurrent calls.

**Recommendation:** keep the frozen code unchanged. Get exact counts with the free `estimate-final` step before the defence and answer stages.

## 0. Freeze and question count

| Check | Result |
|---|---|
| Option A digest | **[M]** `2ec7d1bcfb397d051f7938c86031695960dc04676a7e8142bc1bf9245645c62a`. Recomputed from `research_data/locomo_safemem/freeze/manifest.json`. All 155 frozen files match their hashes, including `data/locomo/locomo10.json` (checked against this repo's copy) |
| 1,540 vs 1,529 questions | **[M]** There are 1,540 category 1–4 questions in `locomo10.json`, all with an answer. Only 1,529 distinct question texts exist: 11 questions appear twice in the same conversation (e.g. "What are Jolene's favorite books?", "What are the names of Jolene's snakes?"). Calls keyed by question text, such as the use-type classifier (1,529 requests) and SensitiveAction, are billed 1,529 times. Answering covers all 1,540 |

Questions per conversation **[M]**: conv-26 152, conv-30 81, conv-41 152, conv-42 199, conv-43 178, conv-44 123, conv-47 150, conv-48 191, conv-49 156, conv-50 158. The dev split (conv-48/49) has 347 questions.

## 1. MPBench Option B: what was actually spent [M]

**Source:** provider receipts in `sessions_rerun3/*/dispatch.sqlite` and `budget.sqlite`.
- The ledgers add up exactly to the recorded project total of **$7.0031**.
- Every reservation is settled, and distinct request keys = dispatches.
- No calls from earlier runs were reused. Earlier MPBench phases (October reproduction, protocol v1) are not part of Option B and are not included.

| Ledger | Calls | Input tokens | Output tokens | Cost | Avg tokens per call (in / out) |
|---|---:|---:|---:|---:|---|
| A-MemGuard (`v2_published_amemguard`) | 7,900 (6,925 chains + 975 judgments) | 2.94M | 0.95M | **$1.0114** | chain 261 / 111; judgment 1,159 / 188 |
| LLM Sanitiser (`v2_published_sanitiser`) | 2,089 (2,065 audits + 24 rewrites) | 0.67M | 0.03M | **$0.1160** | audit 321 / 12; rewrite 267 / 48 |
| MemLineage (`v2_published_memlineage`) | 578 | 0.08M | 0.00M | $0.0127 | 139 / 2 |
| GPT answers + judge (`v2_stage3`) | 23,155 (14,722 answers + 8,373 judge + 60 conflict) | 12.44M | 0.83M | $2.3824 | answer 705 / 41; judge 245 / 28 |
| Claude Haiku answers (`v2_backbone_answer`) | 7,894 | 8.17M | 0.72M | $1.1898 | 1,035 / 91 |
| Gemini answers (`v2_backbone_gemini`) | 7,860 | 6.35M | 0.45M | $2.2907 | 808 / 57 |
| **Total** | **49,476** | **30.64M** | **2.98M** | **$7.0031** | |

Measured cost per call:

| Request type | Cost per 1,000 calls |
|---|---:|
| A-MemGuard chain | $0.1057 |
| A-MemGuard judgment | $0.2866 |
| Sanitiser audit | $0.0554 |

**Why MPBench was so cheap:** the attack cells reuse the same stored texts.
- The published defences ignore audits, so one pass over each group's static contexts served all 46 registered cells: **975 distinct contexts** in total.
- Answers were reused the same way: **3,655,680 scored rows needed only 14,722 billed GPT answers**.

**Workload:**
- 24 groups;
- 46 registered cells for GPT-4o-mini (8 cells for Haiku and Gemini);
- 16 method variants;
- about 35–40 probes per group;
- the random-audit cells use 6 draws.

## 2. Where Option A's 256,514 defence calls come from [R]

**Code:** `locomo_safemem/__main__.py::cmd_estimate`.
- A recorder (`locomo_v2_supp/published_supp.py::Recorder`) replays the frozen defence stage (`locomo_safemem/paid.py::defences`) on the dev mock (conv-48/49).
- It counts **distinct** request keys (`research_data/locomo_safemem/estimate.json`):
  - 37,887 A-MemGuard reasoning chains
  - 11,042 A-MemGuard judgments
  - 8,870 sanitiser audits
- Total: 57,799 distinct requests.

**Projection:** 57,799 × 4.438 (all 1,540 questions ÷ 347 dev questions) = **256,514**.

**Pricing:** priced at `V2_DEFENCE_USD_PER_CALL` = $18.50071995 ÷ (60,352 + 30,980 + 6,974) = **$0.000188 per call**. That is the LoCoMo v2 supplement's realised cost, giving **$48.27**.

**Why so many contexts?**
- Each conversation has 40 attacked "loc" stores: 4 shapes × 2 orientations × 5 draws.
- Checked in `research_data/locomo_v2/supp_published/estimate_build/conv-26.scenarios.json`: **all 40 have different poison targets and values**. There is no overlap of targets across shapes or between draws.
- So these are independent attack instances, not copies. Every store is checked on every question.
- The dev mock has 13,880 store × question pairs, which matches both `defence_jobs_added` 27,760 = 2 defences × 13,880 and RandEC `jobs_added` 13,880.

| | MPBench | LoCoMo Option A | Factor |
|---|---:|---:|---:|
| Stores the defences check | 24 (one per group) | 400 (40 × 10 conversations) | ×16.7 |
| Questions per store | about 35–40 | about 154 | ×3.8 |
| Distinct contexts (A-MemGuard judgments) | 975 **[M]** | ≈ 49,004 **[R]** (80% of the 61,600 store × question pairs) | **×50** |

**How a context becomes billed calls:**
- **A-MemGuard:** each distinct context costs 1 judgment, plus 1 chain for each retrieved memory whose question + memory pair hasn't been seen before.
  - Genuine memories repeat across stores and are cached.
  - So LoCoMo needs only **3.4 new chains per context**, against **7.1 on MPBench**.
- **Sanitiser:** 1 audit per distinct memory text, independent of the question, plus 1 rewrite per text it calls harmful.

**Breakdown by shape, orientation, draw and conversation:** this can't be computed exactly from the repo.
- The dev mock build (`research_data/locomo_safemem/mock/build/`, 811,980 jobs, 63,508 contexts) is not on the branch; it exists only on the teammate's machine.
- `reports/LOCOMO_SAFEMEM_OPTION_A_VS_B_20261124.md` gives the **marginal** cost of the 2-session + quarter shapes: 91,281 calls / $17.17.
- Orientations and draws are symmetric by design.

**Comparison with the LoCoMo v2 supplement** (same conversations, shapes, orientations and draws, but plain-RAG memory) **[M]**:

| Request type | v2 supplement | Option A projected | Ratio |
|---|---:|---:|---:|
| Chains | 60,352 | 168,142 | 2.8× |
| Judgments | 30,980 | 49,004 | 1.6× |
| Sanitiser audits | 6,974 | 39,365 | 5.6× |

SAFE-Mem contexts hold more entries (4 claims + up to 4 evidence chunks), and a larger share of contexts differ between stores (80% vs 50%).

## 3. Side-by-side comparison

| Metric | MPBench actual [M] | Option A projected | Explanation |
|---|---:|---:|---|
| Total cost | $7.00 | $90 (audit estimate: ≈ $75) | Experiment size |
| Published-defence cost | $1.13 | $48.27 | 50× more distinct contexts |
| A-MemGuard | $1.01 | ≈ $40.9 (inside $48.27) | 50× more contexts; cost per context $0.00104 (MPBench) vs $0.00083 (LoCoMo) |
| LLM Sanitiser | $0.116 | ≈ $7.4 (inside $48.27) | 19× more distinct texts × **3.4× over-pricing** (§5) |
| Answers + judge | $2.38 (GPT) | $39.70 | 23× more distinct answer keys (14,722 vs 341,489) |
| API calls | 49,476 | ≈ 950k as stated; ≈ 680k realistic | Judge calls overcounted (§5) |
| Input / output tokens | 30.6M / 3.0M | ≈ 250M input **[R, rough]** | Not measurable: the LoCoMo defence cache is not in the repo |
| Distinct defence contexts | 975 | ≈ 49,000 | Independent stores × more questions |
| Questions | ≈ 35–40 per group × 24 groups | 1,540 × 40 attacked stores each | |
| Attack configurations | 46 cells sharing 24 stores | 3,000 conditions on 1,120 independently built stores | |
| Answer backbones | 3 (GPT all cells; Haiku and Gemini 8 cells) | 1 (GPT) | Not a cost driver |
| Cache strategy | One draw per distinct prompt | The same | Identical; not a cost driver |

**Normalised metrics:**

| Metric | MPBench | Option A |
|---|---:|---:|
| A-MemGuard cost per distinct context (= per invocation) | $0.00104 [M] | $0.00083 [R] |
| Sanitiser cost per distinct text | $0.000056 [M] | $0.000188 (projection's price) |
| Answer + judge cost per distinct answer key | $0.000161 (GPT) [M] | $0.000116 (projection); LoCoMo v2 measured $0.0000811 |

**Share of the A-MemGuard difference** (log decomposition of ×40):

| Cause | Share |
|---|---:|
| More independent attacked stores (4 shapes × 10 repetitions vs 1) | ≈ 76% |
| More questions per store | ≈ 36% |
| More context reuse on LoCoMo | −6% |
| Lower cost per context | −6% |
| Duplicated or inefficient calls | ≈ 0% in the projection (see §4) |
| Backbone coverage, caching strategy | 0% |

## 4. Duplication and caching audit

| Check | Finding |
|---|---|
| Same prompt + model + settings sent twice | **No** in the projection. `ChatRequest.cache_key` covers provider, model, messages, temperature and max_tokens; the recorder counts distinct keys only |
| Same text sanitised again; same A-MemGuard check; same judge | Already removed by the cache (`ams.llm.pool.ManagedClient` with `ResponseCache`; temperature is not excluded from caching): one draw per distinct prompt, the same convention as MPBench (7,900 dispatches = 7,900 distinct keys) |
| Mixing up independent random draws | Not happening. A-MemGuard runs at temperature 1.0, one draw per distinct prompt. The 40 stores truly differ, so their contexts are not duplicates |
| **Concurrent duplicate billing** | **A real gap.** `ManagedClient.complete` (`src/ams/llm/pool.py`) checks the cache and then calls the API, with no guard against two workers sending the same request at once. The defence stage uses `map_concurrent(..., workers=16)`, so two workers sending the same request at the same moment both get billed. Evidence [M]: the v2 supplement billed **108,598 reservations for 98,306 distinct requests**. Sanitiser rewrites are cached per text, so at most 6,974 of the extras can be rewrites, leaving **≥ 3,318** as concurrent duplicates or retry attempts. Likely cost: about 3–10% of the defence stage. The current work order (store, then question) makes A-MemGuard races rare; sanitiser audits of shared texts are the most exposed |
| Cache keys too specific | No |
| Wrong request-count projection | The answer + judge call count (§5) |
| **Hard-coded path** | `locomo_v2_supp/published_supp.py:157` loads A-MemGuard from `upstream_root=Path("/mnt/c/Users/HP/Documents/sdp")`. The defence stage can only run on the teammate's machine |

## 5. Pricing check

The model ID (`openai/gpt-4o-mini`) and the prices ($0.15 / $0.60 per million tokens) match the MPBench receipts exactly. For example, 258 input + 69 output tokens is billed $0.0000801.

| Problem | Effect |
|---|---|
| One blended price per call for every request type | Sanitiser audits are priced at $0.000188 but really cost about $0.000055 (MPBench) → the ≈ $7.4 is really about $2–3. Chains are also over-priced (MPBench $0.000106); judgments are under-priced (MPBench $0.000287) |
| Per-type pricing | MPBench rates × the counts: 168,142 × $0.000106 + 49,004 × $0.000287 + 39,365 × $0.000055 ≈ $34.1. Times the 1.18 overrun seen on LoCoMo v2 (MPBench rates applied to v2 counts give $15.65 vs $18.50 realised) → **defence stage ≈ $40** (range $34–48) instead of $48 |
| "682,978 answer + judge calls" assumes one judge per answer key | The runner reuses judge calls per question + answer: the judge prompt holds no context. LoCoMo v2 needed **25,037 judge calls for 117,713 keys (21%) [M]** (`research_data/locomo_v2/run/`) → about **413k calls**, not 683k |
| Answer cost cross-check | LoCoMo v2 measured $9.55 / 117,713 = **$0.0000811 per key [M]**. Option A contexts are 1.42× longer (2,621 vs 1,845 characters; the 2,621 is derived from the mock projection, the 1,845 measured in the v2 build) → **≈ $36** (range $31–42). $39.70 is plausible but slightly high |
| Construction | Exact [M]: `requests/construction.jsonl.gz` holds 8,548 requests (7,019 extractions at a 2,400-token cap + 1,529 classifier calls at 24); 15.9M characters ≈ 3.97M input tokens → **$1.65** |
| Mock vs real counts | The defence and answer counts come from a **mock** memory (`locomo_safemem/clients.py::MockLLM`). It turns every turn of ≥ 4 words into a claim and marks 1 in 3 same-relation claim pairs as contradictions. Real counts could differ by ±15% or more. Scaling by questions (4.438) is reasonable for chains and judgments (scaling by questions × turns gives 4.421). Sanitiser texts scale with turns (4.943), about +11% for that small item. The free `estimate-final` step recounts exactly from the real contexts before the expensive stages |

**Revised estimate:**

| Stage | Frozen projection | Audit estimate |
|---|---:|---:|
| Construction | $1.65 | $1.65 |
| Conflict checks | ≤ $0.40 | ≤ $0.40 |
| Defences | $48.27 | ≈ $40 ($34–48) |
| Answers + judge | $39.70 | ≈ $36 ($31–42) |
| **Total** | **≈ $90** | **≈ $78 (range $65–95)** |

The $130 cap is adequate. Better: set the defences and answers caps at about 1.25× the exact `estimate-final` numbers once those exist.

## 6. Cutting cost without weakening the evaluation

| Opportunity | Calls / $ saved | Same results exactly? | Fairness, reproducibility | Re-freeze? |
|---|---|---|---|---|
| Stop concurrent duplicate calls: wait for an identical request already in flight, or send each distinct sanitiser text once first | ≈ 3–10% of defence calls ≈ **$1–4** | Yes | Unchanged | **Yes**: `src/ams/llm/pool.py` and `locomo_safemem/paid.py` are frozen; tests and a new digest needed |
| Pre-fill the judge cache from the LoCoMo v2 runs (the judge prompt is question + gold + answer, no context) | ≈ $0.2–0.5 | Yes, for byte-identical requests | Unchanged; document as a deviation | No code change |
| Pre-fill the defence cache from the v2 supplement's `defence_cache.sqlite` | Probably small (SAFE-Mem memories are claims and chunks, not raw turns); measurable for free | Yes, for byte-identical requests | Same convention: one draw per distinct prompt | Same as above |
| Reorder the work | ≈ 0 | The current order is already good for A-MemGuard | — | — |

**Not equivalent, so not recommended as engineering savings:**
- skipping A-MemGuard on contexts without poison (this would remove its false-positive / utility cost);
- reusing chains across questions;
- merging contexts that hold the same memories in a different order;
- changing the temperature.

Removing shapes, conditions, defences, questions or repetitions changes the science; it is not an optimisation.

## 7. Answers to the seven questions

1. **Why was MPBench cheaper?** 50× fewer distinct contexts for the defences (975 vs ≈ 49k) and 23× fewer answer keys (14,722 vs 341,489). MPBench's cells reuse one store per group; LoCoMo has 400 independent attacked stores × 154 questions. Per context, LoCoMo is about 20% *cheaper*.
2. **Why 256,514 calls?** One A-MemGuard check (1 judgment + new chains) for each distinct store × question context, plus one sanitiser audit per distinct memory text, over 40 independent stores per conversation. Counted from the dev mock (57,799 distinct requests) and scaled ×4.438.
3. **How many are truly needed?** In the projection, essentially all, since every counted request is distinct. During the run, 3–10% would be avoidable concurrent duplicates.
4. **Avoidable duplicates or caching problems?**
   - **Yes:** concurrent duplicate billing (no guard against simultaneous identical requests).
   - **In the projection:** the answer + judge call count is overstated (683k → ≈ 413k), and sanitiser audits are priced 3.4× too high.
5. **Can the full evaluation be much cheaper?** Not much: about $1–4 from real fixes. The bigger "saving" is that the original projection is about $12–15 too high.
6. **Lowest defensible cost:** about **$75** (range $65–95). About $72 with the duplicate fix.
7. **Keep the frozen code?** **Yes.** A $1–4 saving doesn't justify changing frozen files, re-testing and a new digest. Revisit only if the exact defence estimate comes out above about $55.

## 8. Recommended actions, in order

1. **Ask the teammate for two files from their machine:** the v2 supplement's `defence_cache.sqlite` and defence ledger (`~/.locomo_v2_supp_state/defence_guard.sqlite`), plus the Option A mock build. These turn the reconstructed per-type token figures into measured ones. Free.
2. **Approve construction and conflicts first** (≈ $2; caps $12 / $3). Then run the free precompute, final, RandEC and **`estimate-final`** passes to get exact counts.
3. **Re-price `estimate-final` per request type** from token counts, using a separate script outside the freeze (`__main__.py` is frozen). Set the defences and answers caps at about 1.25× the result.
4. **Run the defence stage on the teammate's machine**, because of the hard-coded A-MemGuard path.
5. **Correct the statement "answer + judge = 2 calls each"** in `reports/LOCOMO_SAFEMEM_OPTION_A_VS_B_20261124.md` (owner's decision, since it is existing work).
6. **Only if the exact defence estimate exceeds about $55:** consider the duplicate-call fix with re-testing and a re-freeze.

## 9. Evidence: files read

| What | Path |
|---|---|
| Option A protocol, estimate, draft approval, freeze manifest, mock report | `reports/PROTOCOL_LOCOMO_SAFEMEM.md`, `research_data/locomo_safemem/{estimate.json, owner_approval.DRAFT.json, freeze/manifest.json, mock/mock_report.json, requests/construction.jsonl.gz}` (branch `locomo-backup`) |
| Earlier full-vs-reduced comparison | `reports/LOCOMO_SAFEMEM_OPTION_A_VS_B_20261124.md` (branch `locomo-backup`) |
| Estimate and paid-stage code | `locomo_safemem/__main__.py` (`cmd_estimate`, `cmd_estimate_final`, `V2_DEFENCE_USD_PER_CALL`), `locomo_safemem/paid.py`, `locomo_safemem/clients.py` |
| Defence code | `src/ams/baselines/amemguard.py`, `src/ams/baselines/amemguard_borrowed.py` (`LLMSanitiser`), `src/ams/research/workload/published.py`, `third_party/AMemGuard/ReAct/consistency.py`, `locomo_v2_supp/published_supp.py`, `locomo_v2_supp/published_paid.py` |
| Cache and concurrency | `src/ams/llm/pool.py` (`ManagedClient.complete`, `map_concurrent`), `src/ams/llm/types.py` (`cache_key`), `locomo_v1/execute.py` (`_strict_client`) |
| LoCoMo v2 supplement actuals | `reports/LOCOMO_V2_SUPP_PUBLISHED_BASELINES_RESULTS_20261124.md`, `research_data/locomo_v2/supp_published/{estimate.json, estimate_build/, run_supp/}` |
| LoCoMo v2 main-run actuals | `reports/LOCOMO_V2_RESULTS_20261123.md`, `research_data/locomo_v2/run/{answers,judgements,progress}.jsonl` |
| MPBench Option B receipts | `research_data/protocol_v2_optionB_run_v1/sessions_rerun3/{v2_published_amemguard, v2_published_sanitiser, v2_published_memlineage, v2_stage3, v2_backbone_answer, v2_backbone_gemini}/{budget,dispatch}.sqlite` |
| MPBench protocol | `reports/PROTOCOL_V2_OPTION_B_20261115.md` |

**Not available in this repo** (so marked [R] above):
- the Option A mock build;
- the v2 supplement's defence cache and ledger;
- per-type tokens for LoCoMo defence calls.
