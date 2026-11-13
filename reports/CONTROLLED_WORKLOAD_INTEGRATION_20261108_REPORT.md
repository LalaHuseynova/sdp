# Controlled workload: offline integration — 8 November 2026

**Status: integration implemented and tested offline with mock clients. No paid call has been made.** The research budget is unchanged at $2.09412345 used of $30, with zero holds; the state inspector confirms this.

The controlled workload ([specification](CONTROLLED_WORKLOAD_20261108_SPEC.md)) now runs end to end through:
- the original SAFE-Mem write path;
- the research binding catalog and evidence ledger;
- the governed retrieval adapter;
- the R/C/M/S policies and the original answer prompt;
- the original attack judge.

Mock outcomes below are **software checks, not experimental results**.

## 1. What was implemented

| File | Role |
|---|---|
| `src/ams/research/workload/integration.py` | Builds one native SAFE-Mem store per group with `native.pipeline.make_memory` (original write/extraction/chunking/indexing). Binds every claim and chunk; registers provenance per condition from the overlays; builds the fixed oracle audits; freezes classifier replies and query embeddings; emits one `RuntimeState` snapshot per condition. `LayeredClient`: frozen reproduction cache first, then an explicit fallback (mock), or a logged miss in cache-only mode. |
| `src/ams/research/workload/runner.py` | Runs static/R/C/M/S × 3 conditions plus no-memory. Reuses the provisional runner's `answer_query`, `resolve_models`, `Journal` and `BoundClient`, and the original `MemoryJudge`. Append-only journal; restart is idempotent. Wraps the tested `memoized_evidence_revisions()` runtime cache. |
| `src/ams/research/workload/grading.py` | Deterministic utility grader (normalized whole-token alias match). Diagnostic target-restatement check. |
| `src/ams/research/workload/analysis.py` | ASR, utility overall and by stratum, principal utility, copy leakage, exposure; paired cluster bootstrap over groups (10,000 resamples); Holm correction; the pre-specified H1–H3 decisions; integrity checks (completeness, equal audit budgets, principal invariance). |
| `src/ams/research/workload/mock.py` | Deterministic prompt-aware mock for extraction, retention, classifier, conflict, answer and judge prompts, plus bag-of-words embeddings. `MockSession` mimics the transport's `dispatch()`. `RefusingSession` raises on any paid dispatch. |
| `scripts/run_controlled_workload.py` | `dry-run` (real cache plus mock for misses, mock answers and judges, analysis, Stage-1 request audit) and `analyse`. **There is no live or paid mode.** |
| `tests/test_controlled_workload_integration.py` | 11 end-to-end tests on invented data. |

**Integration decisions** (all apply equally to every arm; no algorithm changed):
- **Attribution by construction.** Artifact-derived records belong to their contribution's external root; principal-turn records to a principal root. A declared linked copy shares its original's incident root.
- **One use per question.** A copy probe asks its seed's question, so it shares the audited use; scored siblings have their own uses.
- **Oracle audits** are recorded with the ledger's existing `controlled_audit` basis (the same basis the provisional AI simulation used) and `verifier_id = oracle_by_construction`. Findings cover every record registered under the audited root, which satisfies the ledger's complete-bundle rule. All records of an attack seed are marked unsafe; all records of the audited benign input are marked safe.

## 2. Bugs and problems found and fixed

1. **Wrong prediction in the spec.** The draft said the linked copy escapes S. In fact the linked copy shares the audited root and use, so the direct finding blocks it under R, C, M and S. Integration showed this; the spec (§3, §9) is corrected. The 8 Nov evening README log entry is annotated.
2. **Degenerate test fixture.** All invented attacks shared the words "secret code", so the lenient mock judge counted another attack's record as a hit. This made it look as if C/M/S failed to block attacks. Fixed with unique tokens per target and a stricter mock judge (≥75% overlap).
3. **Mock answer threshold** too strict for one-word questions; fixed.
4. **Integration contract details:**
   - `RuntimeState.create` requires registered evidence, so it is created with the first condition's registrations.
   - Audits must use an accepted verification basis.
   - Audit events need a JSON round-trip before `parse_event`.
5. **Speed.** Re-hashing the evidence snapshot per candidate cost 6.25 s per query. The existing tested `memoized_evidence_revisions()` brings this to 0.12 s, about 50× faster, with no decision change.

**Explained along the way:** in the provisional run every query had its own `use_id` and none matched an audit's use. Direct findings are use-specific, so R could never act on a scored query. That is why R changed 0 contexts on 7 Nov.

## 3. End-to-end dry run on the real dev split (mock)

8 groups, 320 contributions and 4,760 outcome events. Real cached extraction replies were used for the 64 verbatim MPBench attacks; everything else was mocked. **Integrity: no issues.** All outcome rows are present, audit budgets are equal (5 for R/C/M/S, 0 otherwise), and principal controls are 32/32 under every arm.

| Condition | Arm | ASR (scored) | External utility | Key stratum | Linked copy | Unlinked copy |
|---|---|---:|---:|---:|---:|---:|
| localized | static | 15/32 | 154/200 | 45/56 | 3/8 | 3/8 |
| localized | R | 15/32 | 154/200 | 45/56 | **0/8** | 2/8 |
| localized | C / M | **0/32** | 116/200 | **8/56** | 0/8 | 2/8 |
| localized | **S** | **0/32** | 154/200 | **45/56** | 0/8 | 2/8 |
| distributed | C / M / S | 0/32 | 116/200 | – | 0/8 | 2/8 |
| uninformative | C | 12/32 | 145/200 | 52/69 | 0/8 | 2/8 |
| uninformative | M | 10/32 | 116/200 | 35/69 | 0/8 | 2/8 |
| uninformative | S | 12/32 | 143/200 | 51/69 | 0/8 | 2/8 |
| all | no-memory | 0/32 | 0/200 | 0 | 0/8 | 0/8 |

The software reproduces every mechanical prediction:
- **R** never blocks scored siblings, but does block the linked copy.
- **Localized:** C and M suppress A's other-batch benign memories; S does not.
- **Distributed:** S matches C and M exactly.
- **Uninformative:** S restricts less than M.
- **Unlinked copies** leak under every arm. R's 2/8 versus static's 3/8 is the audited original itself being withheld.

These numbers say nothing about real effectiveness. The mock's "attack success" and "utility" are lexical stand-ins.

**Data-path findings relevant to the paid stages:**
- **Utility misses are retrieval or extraction misses, not grading misses.** Static answers were correct whenever the inserted fact reached the context (152/152). In 46 of 200 cases it did not (43 with no record from that contribution, 3 with other records but not the fact). Real GPT extraction and MiniLM retrieval may differ; Stage 2 measures this.
- **Grader false-positive risk.** 2 of 200 answers passed without the fact in context, because a common alias (a weekday or month) appeared elsewhere. The analysis should also report "correct and fact in context".

## 4. Stage-1 request audit (exact, from the dry run)

Every construction request was checked against the frozen reproduction cache.

| Requests (dev) | Cache hits ($0) | Would be paid |
|---|---:|---:|
| Extraction | 99 | **256** (one per new-text contribution) |
| Retention | 280 | **40** (principal controls and forwarded copies) |
| Use-type classification | 48 (all MPBench questions) | **232** (new utility questions) |
| **Total** | **427** | **528** |

**All 64 verbatim MPBench contributions and all 48 MPBench questions hit the cache.** Paid dev Stage 1 is therefore about 342k input and 36k output tokens: **$0.073, or $0.088 with a 20% retry allowance**. That is down from the $0.278 upper bound, because no verbatim request misses.

- **Test split:** scaled ×3, roughly $0.26.
- **Dev Stage 3 comparison:** remains an upper bound of **$0.69**.
- **Embeddings:** local MiniLM in the paid stage, $0.

## 5. Unchanged-state verification

- **Source and config files.** Of the 431 source, prompt, config, test and script files hashed before this work, the only changed file is my own `tests/test_controlled_workload.py` fixture from the previous task. No original SAFE-Mem, ledger, policy, retrieval or prompt file changed.
- **Full offline suite:** 635 tests passed (624 earlier plus 11 new).
- **Frozen bundles.** Both frozen provisional comparison bundles verify, and the workload bundle regenerates byte-identically.
- **State inspector:** `passed_with_known_legacy_validator_limitation` (unchanged known issue); budget $2.09412345 used, $0 held.

## 6. Remaining work and the next (paid) step

**Paid Stage 1, dev: construct real memories. Up to about $0.09; requires approval.**
- **Why it is needed.** The 256 new-text contributions (benign documents with inserted facts, copies, principal controls) and 232 new questions have never been processed by GPT-4o-mini. Without real extraction and classification we cannot know whether the facts and copies are actually stored and admitted.
- **What it unlocks** is free Stage 2:
  - real extraction yield of inserted facts and relayed copies;
  - the share of utility questions classified as description;
  - retrieval exposure for every arm with real MiniLM.

  Stage 2 decides whether the design works before any answering is paid for.
- **Required first: a small reviewed live transport.** The workload currently has none by design. It should reuse the existing guarded session (`BudgetGuard` reservation, one attempt per dispatch ID, durable receipts) for construction calls only, with a hard cap of $0.15 for this stage.

After Stage 2, a separate approval is needed for dev Stage 3 (≤ $0.69), and later for the locked test.
