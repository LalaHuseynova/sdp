# Research implementation guide

Reviewed 7 November 2026. Start with the [project README](../../../README.md) for results and the numbered completion table. This guide explains what our added code does and where to look. It does not authorize a new experiment.

## What we built

Our question is: after reviewing one dangerous memory, which other memories should receive a penalty? We compare direct containment, contextual reputation, fixed multi-scope reputation and our selective rule under the same revealed evidence.

Original SAFE-Mem still creates and governs memories. Our added layer records provenance and audit evidence, then restricts or reorders eligible records before they reach downstream models. No model training was added. The current implementation is a minimum heuristic, and its development results show no advantage over C or M.

## Follow the data through the code

| Stage | Files to read | What they do |
|---|---|---|
| Inventory and stable IDs | `phase1.py`, `phase1_data.py`, `phase1_common.py` | Inventory original cases, create stable identities and check preparation invariants. |
| Source mapping and review separation | `phase1_annotations.py`, `phase1_blinding.py` | Separate evaluator labels from blinded review/runtime views. |
| Synthetic assignment and stress recipes | `phase1_scenarios.py`, `phase1_stress.py` | Construct controlled provenance relationships and proposed stress scenarios. These are not natural author identities. |
| Memory recovery | `recovery/records.py`, `recovery/pipeline.py`, `recovery/offline.py` | Recover saved claims, reconstruct chunks with cached material, check hashes/spans and refuse network fallback. |
| Provisional groups | `provisional/episodes.py`, `provisional/pipeline.py` | Select disjoint template groups and assign two contributors, two contexts and four-input batches. Actual provisional composition is 20 attack inputs + 12 benign inputs. |
| Human-review preparation | `recovery/annotation.py`, `provisional/annotations.py`, `focused_review.py`, `focused_review_page.py` | Prepare/import reviews, preserve disagreement, and support focused question validation. The software cannot authenticate a human or invent a decision. |
| Question drafts and scoped cohorts | `provisional/questions.py`, `scoped_cohort.py` | Prepare source-supported candidate questions and check narrow eligibility. Drafts do not become ground truth automatically. |
| Automated review | `llm_review/`, `llm_followup/`, `pilot_finish/`, `ai_pilot/` | Save AI proposals, failures, follow-ups and quality checks. These modules represent successive stages, not interchangeable duplicate implementations. |
| New frozen stores | `native/construction.py`, `native/cache.py`, `native/pipeline.py` | Build fresh Original SAFE-Mem graph/index states using cached responses, preserving construction links and verifying recovered records. |
| Evidence state | `dynamic/models.py`, `dynamic/ledger.py` | Register records, reveal audit findings, deduplicate incident votes, apply corrections/retractions and save immutable snapshots. |
| Policy choices | `dynamic/policies.py` | Implement R/C/M/S, exact safe-use exceptions, risk scores and the hard gate. |
| Retrieval adapter | `retrieval/metadata.py`, `retrieval/adapter.py` | Bind native records to trusted metadata; enforce access, original authority and evidence decisions; rank and refill claims/chunks. |
| Offline sequence/restart | `sequential/state.py`, `sequential/runner.py`, `sequential/clients.py` | Save graph/index/client state, exact responses and ordered action history; reject replay misses. |
| Planning and guarded transport | `planning/`, `execution/` | Freeze engineering settings, estimate costs and use a persistent shared spending/dispatch journal. The offline runner and paid extension are separate layers. |
| Provisional execution | `provisional_execution.py`, `provisional_run/preparation.py`, `provisional_run/runner.py`, `provisional_run/transport.py`, `provisional_extension.py` | Freeze the exploratory scope, expose scheduled saved feedback and execute the matched comparison. |
| Analysis | `comparison.py` | Check matched inputs/evidence and aggregate saved answer outcomes. Private target judgments never update reputation. |
| Controlled workload (8 Nov) | `workload/design.py`, `generator.py`, `costs.py`, `integration.py`, `runner.py`, `grading.py`, `analysis.py`, `mock.py` | Frozen design, generator, cost estimate, native-store construction, R/C/M/S runner, utility grader, analysis and offline mocks. No live transport. |
| Controlled workload Stage 1/2 (8 Nov) | `workload/transport.py`, `workload/stage2.py` | Construction-only paid scope on the shared guarded session (dev only, $0.15 cap, halt on unknown billing) and free Stage-2 validation (extraction yield, classification, retrieval exposure). |
| Controlled workload v2 (8 Nov) | `workload/carriers_v2.py`, `workload/pilot.py`, `workload/replay.py` | Fact-centred carriers (`build(..., carriers="v2")`), the tiny extraction pilot (selection, criteria, evaluation, cost) and read-only reuse of already-paid replies by exact request key. |
| Controlled workload v3 (8 Nov) | `workload/carriers_v3.py` | Durable (standing reference) fact phrasing on v2 notes; same answers and draws (`build(..., carriers="v3")`). Validated on real dev data. |
| Controlled workload v4 (8 Nov) | `workload/quality_v4.py` | Method-independent data-quality rules (fragment relays; no near-duplicate payloads in a group). Final frozen dataset for the locked test. |
| Speed improvement | `evidence_memoization.py` | Reuse the hash of an immutable evidence snapshot. This is not a new policy or evidence source. |

## What a memory and its relationships mean

One MPBench input is a **contribution**. It can contain a principal turn and external artifacts, such as a document. Original SAFE-Mem extracts **claims** with an LLM and builds **evidence chunks** from source text using embedding-dependent chunking. Both can become retrievable memory records.

Our sidecar metadata links each record to its actual source and content version. The experiment assigns opaque contributor and batch IDs to external contributions. A batch contains four independent inputs from one contributor in one source context. Shared batch membership does not prove copying or semantic dependence. Principal-owned records keep the original principal; uncertain attribution stays uncertain.

Keep three labels separate:

- Original attack/benign case label: used for benchmark scoring and the provisional assignment recipe.
- Independently reviewed record/use safety: required for the final scientific pilot; genuine human labels are still missing.
- Revealed audit verdict: evidence available to the policy at a particular event, possibly mistaken, unresolved or retracted.

The runtime names `authenticated_external`, `verified_audits` and `verified_safe_for_use` describe trusted-input contracts or decision reasons. In the provisional experiment they do not establish authenticated real-world authorship or human validation.

## How the ledger changes retrieval

1. Register records and trusted origin links before using them.
2. Reveal a scheduled audit only when its ticket is consumed. Store the exact record, content, use and policy version.
3. An unsafe finding withholds that exact use. A safe finding exempts that exact use from reputation penalties, but never grants access or authority.
4. Count at most one aggregate vote per independent incident root. Multiple claims or known copies cannot multiply the vote. Unresolved findings consume budget but add no safe/unsafe vote.
5. Recompute counts and supported scopes after corrections or retractions.
6. For a query, use only the current evidence snapshot. Compute cosine relevance, enforce authority/access, apply exact findings and the selected policy, then rank surviving claims and chunks separately.
7. Refill from the same eligible candidate universe, up to four claims and four chunks. Only eligible text goes to the original downstream conflict/answer path.

For each scope, `risk = (1 + U) / (2 + U + Safe)` and `penalty = max(0, risk - 0.5)`. `U` and `Safe` count distinct audited roots, not every record. The score is `cosine - 0.5 * penalty`. A penalty of at least 0.25 withholds an uninspected candidate. This score is a heuristic, not a calibrated probability.

| Policy | Scope used for an uninspected external record |
|---|---|
| R | None; direct findings only. |
| C | Its contributor/context. |
| M | Maximum penalty across its batch, contributor/context and contributor. |
| S | Maximum penalty across supported scopes only. |

S supports a batch after one unsafe root; a context after two unsafe roots spanning two batches; and a contributor after four, including two roots spanning two batches in each of two contexts. Two unsafe roots in the same batch therefore support the batch, but do not by themselves support the whole context. Support allows a penalty calculation; it does not label sibling records unsafe.

The adapter supports flat indexing, withhold mode and hops=0. The frozen experiment has `external_evidence=false`, so many external chunks fail original admission before our policy can matter. Exact safe-use findings cannot override that restriction.

## The experiment we actually executed

The [provisional results report](../../../reports/PROVISIONAL_RESULTS_20261101_REPORT.md) covers eight existing development groups, three conditions and six methods including no-memory controls. R/C/M/S receive the same five tickets per group/condition. Static and no-memory arms receive no audits. All five audits precede the scored questions. Feedback reuses saved AI assessments, and live content screening is disabled for all arms.

The methods share frozen inputs, ingestion order, permissions, query order and original prompts. Exact identical model requests reuse the first saved response. The result set has 3,888 answer events, not 3,888 independent source cases. S changed 23 of 648 query contexts and did not improve ASR. Human-validated external-use utility was not scored.

The primary protocol's verified 16-safe/16-unsafe groups, stronger baseline variants, continuous adaptation, answer-level robustness, a full-MPBench run of S and external validation remain unfinished.

## Where to inspect actual files

| Location from repository root | Contents |
|---|---|
| `data/mpbench/` | Unmodified official source inputs. |
| `research_data/mpbench_phase1/public/candidate_inputs.jsonl` | Initial candidate/source inventory; final synthetic assignments live in overlays. |
| `research_data/mpbench_recovery_v1_20261029/private/claims.jsonl` | Recovered claims. |
| `research_data/mpbench_recovery_v1_20261029/private/evidence_chunks.jsonl` | Recovered/reconstructed chunks and links. |
| `research_data/mpbench_provisional_v1_20261029/private/group_selections.json` | Selected source cases per development group. |
| `research_data/mpbench_provisional_v1_20261029/private/episode_index.json` | Mapping to condition overlays. |
| `research_data/mpbench_provisional_v1_20261029/public/` | Opaque contributor/context/batch assignments. |
| `research_data/dynamic_native_stores_v1_20261031/` | Frozen native memory stores and construction crosswalks. |
| `research_data/provisional_comparison_freeze_v1_20261101/` | First comparison freeze. |
| `research_data/provisional_extension_freeze_v1_20261101/` | Remaining development-group freeze. |
| `research_data/development_comparison_report_v1_20261101/RESULTS.md` | Combined result table. |
| `research_data/dynamic_execution_prep_v1_20261031/session/` | Shared research budget and dispatch journals. Never reset to obtain another allowance. |

Private paths contain evaluator/reviewer material, not model inputs. Do not copy whole private records into a runtime prompt.

## How to read the smaller READMEs

Module READMEs describe local interfaces and their original development stage. Their new status notes point to integrations that were added later. The root README is the current project-status entry point. Historical protocol/report files and frozen manifests remain unchanged.

See the [script guide](../../../scripts/README.md) for offline verification. Existing recorded tests cover mechanics, parity, restarts and accounting; they do not prove universal safety or scientific efficacy. The known Phase 1 fingerprint issue remains documented and is not repaired by this documentation cleanup.
