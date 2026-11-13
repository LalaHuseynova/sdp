# Controlled workload: paid dev Stage 1 and free Stage 2 validation (8 November 2026)

**Status:**
- **Paid dev Stage 1 (owner-approved) ran and halted safely after 3 of 8 dev groups.** One call timed out with an unknown billing outcome, and the shared budget guard stopped itself, as designed.
- **Actual settled spend: $0.03251535.** One additional attempt has unknown cost: worst case $0.01974 is held, realistic about $0.0002.
- **Free Stage 2 ran on the 3 completed groups** and found a **design flaw in the workload's utility side**. Inserted benign facts are almost never stored as retrievable claims (8/78). The frozen `external_evidence=false` setting keeps the artifact chunks that do contain them out of the context.
- **The attack and copy side works as intended** on real GPT-4o-mini extraction and real MiniLM retrieval.
- **No test-split work and no Stage 3 have been run. Nothing further should be paid for before the utility design is fixed.**

## 1. What was run

| Step | Command / code | Paid? |
|---|---|---|
| Stage 1 construction | `scripts/stage_controlled_workload.py stage1 --split dev --confirm-paid-dev-stage1` through `src/ams/research/workload/transport.py` (`ConstructionSession` on the existing shared session; frozen-cache-first `LayeredClient`; local MiniLM embeddings) | Yes, approved, hard task cap $0.15 |
| Stage 2 validation | `scripts/stage_controlled_workload.py stage2` through `src/ams/research/workload/stage2.py` | No ($0; conflict checks answered by a logged placeholder) |
| Diagnostics in this report | Read-only queries of the stores and ledgers; local MiniLM similarity ranking | No |

**Outputs:**
- `research_data/controlled_workload_stage1_dev_v1_20261108/`: `stores/G-D00..G-D02.json.gz` and `stage1_summary.json`. The summary was written afterwards from the read-only ledgers, because the run halted before writing its own.
- `research_data/controlled_workload_stage2_dev_v1_20261108/stage2_validation.json`.

## 2. Actual API cost (from the shared ledger, reconciled)

| Stage | Settled calls | Settled USD |
|---|---:|---:|
| Extraction | 118 | 0.02741700 |
| Retention | 13 | 0.00091395 |
| Use-type classifier | 78 | 0.00418440 |
| **Total settled** | **209** | **0.03251535** |
| Unknown attempt (1 extraction, `APITimeoutError`, no response captured) | 1 | worst case **0.01974** held; realistic ≈ 0.0002 |

- **Tokens:** 127,529 input and 22,310 output.
- **Ledger reconciliation:** the shared ledger moved from $2.09412345 to **$2.12663880** used, with $0.01974 held. The difference equals the settled sum exactly.
- **Cache use:** 427 cache-eligible requests cost $0 (35 retentions, 12–13 extractions and 6 classifier calls per group). Embeddings were all local, so $0.
- **Unfinished group:** 11 of the 209 settled replies belong to G-D03. They are saved and would be reused at $0.
- **Per-call cost** matched the estimate (about $0.00023 per extraction). The full dev Stage 1 would have cost about $0.08.

## 3. Problem 1: the run halted on an unknown billing outcome

- **Timeline.** The reservation was created at 22:55:57 UTC. The client raised `APITimeoutError`, recorded at 02:00:04 UTC, three hours later, although the timeout was 120 s. This strongly suggests the computer slept during the request.
- **Why the guard halted.** No response was captured, so whether OpenRouter billed it cannot be known locally. The guard did what it was built to do:
  - marked the attempt `unknown`;
  - kept the worst-case hold;
  - persisted a halt (`unresolved_workload_construction_billing`);
  - refused further construction dispatches.
- **Why it cannot be cleared from this code.** The ledger deliberately has no path to settle an `unknown` attempt. `resume_after_review` can only clear an `unverified_billing` halt. I did not edit the ledger or open a new session.
- **Effect.** The shared $30 session is closed to new paid work until the owner decides. Free work, Stage 2 and analysis are unaffected.

## 4. Stage 2 findings (3 dev groups, 120 contributions, 105 probes per condition and arm)

### 4.1 Extraction yield: was what we inserted stored as a claim?

| Role | Stored / total | Notes |
|---|---:|---|
| Attack, scored (verbatim MPBench) | **12/12** | |
| Attack seed (audited) | **12/12** | The heuristic reported 11/12; the one "miss" is a paraphrase ("auto-forwarding of all direct messages enabled to external@example.com"). |
| Principal control | **12/12** | All are principal claims containing the answer. |
| Linked copy | 2/3 | One forwarded copy produced no claims. |
| Unlinked copy | **1/3** | One produced no claims; one stored only the user's unrelated preference ("dark mode"). |
| **Benign document with inserted fact** | **8/78 (10%)** | **Main problem; see 4.4.** |

### 4.2 Classification

- All attack, copy and utility questions (93/93) are classified **description**, so they are answerable from external memory as designed.
- Principal questions: 9 preference and 3 attribute.

### 4.3 Retrieval exposure (real MiniLM, governed retrieval, k = 4 claims + 4 chunks)

| Condition | Arm | Attack target in context | Linked copy target | Unlinked copy target | Utility fact in context (strict ceiling) | Key stratum fact in context |
|---|---|---:|---:|---:|---:|---:|
| localized | static | 11/12 | 2/3 | 3/3 | **10/75** | 4/21 |
| localized | R | 11/12 | 0/3 | 1/3 | 10/75 | 4/21 |
| localized | C / M | **0/12** | 0/3 | 1/3 | 6/75 | **0/21** |
| localized | **S** | **0/12** | 0/3 | 1/3 | **10/75** | **4/21** |
| distributed | static | 11/12 | 2/3 | 3/3 | 10/75 | — |
| distributed | C / M / S | 0/12 | 0/3 | 1/3 | 6/75 | — (same-batch 0/21) |
| uninformative | static / R | 11/12 | 2/3 (R 0/3) | 3/3 (R 1/3) | 10/75 | 1/18 |
| uninformative | C / M / S | 7/12 | 0/3 | 1/3 | 7/75 | 1/18 |

Principal controls reached the context in 12/12 under every arm.

**On real data, the mechanics behave exactly as designed:**
- The attack target reaches the static context in 11/12 cases, and C/M/S remove all of it in the localized and distributed conditions.
- R never blocks scored siblings but blocks the linked copy.
- The unlinked relay leaks under every arm.
- In the localized condition S keeps the key stratum where C and M remove it (4/21 vs 0/21).
- Principal controls are invariant across arms.

**The direction of every comparison is right, but the utility counts are far too small** to test H1. The key stratum has 4 reachable facts out of 21 in 3 groups.

### 4.4 Root cause of the utility problem

For each missed utility probe in G-D00 I looked at what filled the context:
- **The claim slots** held other external claims.
- **All 4 chunk slots, for every utility question,** held short principal *turn* chunks such as "I liked the suggestion…".

**The fact is stored.** It sits inside an artifact evidence chunk. By pure MiniLM similarity, that chunk ranks **#1 of 777 chunks for 24 of 25 questions** (#2 for the last).

**It is filtered out by the frozen SAFE-Mem setting.** `external_evidence=False` (`src/ams/memory/typed.py:760`; `retrieval/adapter.py:338`) bars external chunks at description standing from the context. External information can therefore only reach an answer as an **extracted claim**.

**Extraction keeps only what the user's request is about.** The sentence-endorsed write path extracts about five salient claims per document, guided by the user's request:
- broad "summarize this thread" requests kept the inserted fact in 7/44 documents;
- narrow "remember X" requests kept it in 1/34.

The inserted sentence is incidental to the document, so the extractor drops it.

**Why the mock dry run did not show this.** The mock extractor stored every fact sentence. Its 154/200 static utility was an artifact of the mock, not a property of SAFE-Mem. This is a gap in my design and mock, not a bug in SAFE-Mem. The earlier repository notes already said many external chunks fail admission under `external_evidence=false`, and I should have carried that into the workload design.

## 5. Strict utility metric (implemented)

`analysis.metrics()` reports the following alongside the lenient measure:
- `utility_external_strict` = correct answer **and** the inserted fact in the supplied context;
- `utility_by_stratum_strict`, `utility_principal_strict` and `utility_coincidental_passes`.

`hypotheses()` adds a strict-utility bootstrap sensitivity analysis to H1. The Markdown table has "Utility strict" and "Key strict" columns, and `tests/test_controlled_workload_stage1.py::test_strict_utility_metric` covers it.

Stage 2's "fact in context" column is the **ceiling** for strict utility: no answer can count as strictly correct when its fact was never supplied. With the current workload, that ceiling is 13% static.

## 6. Checks

- **Tests:** full offline suite **640 passed** (635 + 5 Stage-1/Stage-2 tests). `ruff` is clean on the new code.
- **No existing algorithm, prompt or configuration changed.**
- **`scripts/inspect_research_state.py` now refuses** with "Budget changed or has unresolved requests; review this audit's dated scope". This is expected and correct: the dated inspection was frozen at the pre-Stage-1 budget, and the unknown attempt is unresolved. It was left unchanged.

## 7. Recommendations (each needs the owner's decision)

1. **Do not pay for more dev Stage 1 or Stage 3 with the current workload.** Utility would be measured on about 13% of probes, and H1 cannot be decided.
2. **Fix the workload's utility carriers (data change only; the algorithms and frozen settings stay as they are).** Make the inserted fact the content the user's request is about:
   - (a) Short fact-centred benign notes where the fact is the main content, paired with a request that endorses it ("Please keep track of who leads which workstream from this note"). The request must not reveal the answer.
   - (b) Equivalently, rewrite the benign user requests to reference the fact's topic.

   Then rerun free generation, the mock dry run, and a **tiny paid extraction pilot** (about 16 contributions, under $0.01) to confirm a yield of at least 80% before rebuilding the dev stores (about $0.08).
3. **Do not switch to `external_evidence=true`** as the primary fix. That departs from the frozen SAFE-Mem configuration used in every earlier result, though it could be a separately labelled sensitivity analysis.
4. **The unknown-billing halt needs an owner decision.** Option (i) is recommended because it keeps the full audit trail and never understates spend:
   - (i) Accept the $0.01974 worst case as permanently held. The owner can optionally check the OpenRouter activity page for a GPT-4o-mini request near 22:56 UTC on 7 Nov. Further paid work would then go through a **new** guarded session with its own small allowance.
   - (ii) Add a reviewed, audited settlement path to the guard. This is a code change to safety-critical accounting, so I would only do it with explicit permission.
5. **Operational fix for future paid runs:** run under `caffeinate -i` so the computer cannot sleep mid-request. I suggest also adding a wall-clock check that refuses to continue after a stall.
