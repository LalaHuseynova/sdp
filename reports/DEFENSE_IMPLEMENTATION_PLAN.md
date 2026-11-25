# Dynamic provenance-based memory defense: analysis and implementation roadmap

Prepared 28 October 2026. **Analysis only: no defense implementation, experiment execution, training, or paid API calls were performed for this review.**

The requested primary proposal, [RESEARCH_PROPOSAL.md](RESEARCH_PROPOSAL.md), is the revised, lightweight proposal. Its opening paragraph identifies [RESEARCH_PROPOSAL_EXTENDED.md](RESEARCH_PROPOSAL_EXTENDED.md) as the earlier, more ambitious version. Both were reviewed. This roadmap follows the lightweight version: frozen models, small explicit state, Python experiments, and no application deployment or new model training.

**Concrete design:** [MPBench dynamic experiment protocol](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md) specifies the revised pilot layout, exact scenario generator, audit schedules, baselines and decision rules. It supersedes the preliminary pilot numbers below.

**Start here:** [First experiment protocol](FIRST_EXPERIMENT_PROTOCOL.md). The first concrete implementation task is an offline, validated provenance mapping; trust updates and paid experiments come later.

## 1. Recommendation and scientific assessment

**The defense is feasible on this setup, but “decrease a user's trust and all their memories after finding an attack” is not a sufficiently strong novelty claim by itself.** SAFE-Mem already governs provenance and permitted use; other work already combines memory with source reputation, adaptive trust, lessons, or access-aware risk.

The stronger question is:

> When a memory is independently confirmed unsafe for an intended use, when should that evidence change decisions about other, uninspected memories from the same contributor, and how can we obtain that benefit without suppressing their legitimate contributions?

The proposed contribution should be **selective transfer of verified safety evidence under limited, imperfect feedback**. Access control is a binding constraint and provenance supplies relationships; neither is independently the main novelty.

| Proposed version | Scientific assessment |
|---|---|
| Attach user IDs and permissions; decrease every sibling's score after an LLM flag | Useful engineering baseline; weak novelty and vulnerable to false accusations. |
| Add global/context Beta counters and a weighted relevance score | Feasible first method, but still an incremental combination unless it establishes a new finding. |
| Isolate transfer to uninspected siblings; identify conditions where transfer helps or hurts; show selective treatment improves safety at matched utility and audit expense | A defensible empirical research direction, conditional on results and closer comparisons. |
| Add a narrowly justified uncertainty-controlled decision about widening propagation scope, plus evidence of generalization | Potentially stronger contribution; neither a required large model nor an automatic acceptance route. |

ICML's [2026 reviewer instructions](https://icml.cc/Conferences/2026/ReviewerInstructions) evaluate soundness, significance, originality, and presentation, and recognize contributions through insights as well as new methods. They do not make complex training a requirement. Use these as an assessment reference and recheck the eventual submission year's instructions. No acceptance probability can be established from this proposal.

**Recommendation:** start with the fixed-feedback transfer experiment in Section 9. Do not build a learned graph model, reinforcement learner, deployment system, or general permissions platform before establishing that source-level evidence adds value beyond a record-only defense.

## 2. What this repository already establishes

The completed [Original SAFE-Mem reproduction](safemem_full_mpbench/RUN_REPORT.md) is a useful foundation, not evidence for the proposed contribution.

| Existing MPBench result | Value |
|---|---:|
| Source cases ingested into one shared pool | 6,240 |
| Scored attack questions | 2,999 |
| Readable benign questions | 2,997 |
| Annotated benign utility cases | 2,856 = 249 retention + 2,607 restraint |
| Write-only cases retained in memory construction | 244 |
| Extracted entries in that run | 22,089 |
| ASR | 176/2,999 = 5.87% |
| Retention recall | 213/249 = 85.54% |
| Restraint | 1,273/2,607 = 48.83% |
| Combined benign utility | 1,486/2,856 = 52.03% |

All 67 checked original method/prompt/configuration files were preserved in that reproduction. Its deviations and uncertainty remain relevant: OpenRouter/current model alias, 2,891 exact distinct attack questions versus 2,893 in the paper, internal cross-split ID qualification, confirmed original-token-limit finishes, and some saved responses differing from concurrent cache winners.

The old result is a historical reference. A new chronological workload changes order, metadata, policies, and feedback opportunities. **Rerun the static baseline within that same future workload before attributing differences to our defense.** Do not compare a newly advantaged sequential method only against the historical 5.87%.

### Reusable components

| Component | Evidence in code | Reuse and boundary |
|---|---|---|
| Typed governance | [core/lattice.py](../src/ams/core/lattice.py), [core/standing.py](../src/ams/core/standing.py) | Five claim/authority levels, domains, meets, permitted use, role-based standing, endorsement checks. These are normative authority, not an empirical contributor reputation score. |
| Source/claim graph | [memory/graph.py](../src/ams/memory/graph.py): Source, Claim, ClaimGraph | Source IDs, roles, principal IDs, claim-source links, entities, endorsement and derivation fields. Reuse relationships after addressing attribution limitations below. |
| Original memory construction | [memory/typed.py](../src/ams/memory/typed.py): write, _write_sentence_endorsed, _store | Reuse extraction, retention checks, sentence endorsement, standing assignment, and embeddings. |
| Governed retrieval | Same file: retrieve, _retrieve_partitioned, _admits, _cap | Reuse original eligibility, cosine scoring, evidence limits, and source caps; new policy/risk checks need entry points before final selection. |
| Evidence passages | [memory/evidence.py](../src/ams/memory/evidence.py), typed.py: _index_units and _evidence | Chunks retain source IDs and standing. They require the same new controls as claims. |
| Existing state changes | graph.py: demote_source; typed.py: _resolve_conflicts | Demotion through declared descendants and contested claims already exist. Thus “dynamic” or “propagation” alone is not a new capability. |
| Interfaces | [memory/base.py](../src/ams/memory/base.py), [baselines/base.py](../src/ams/baselines/base.py) | MemoryEntry metadata, WriteResult, RetrievalResult, DefenceResult. A final Defence.filter is suitable for a screening prototype, not sufficient for all retrieval controls. |
| Dataset/evaluation | [data/mpbench.py](../src/ams/data/mpbench.py), [eval/lifecycle.py](../src/ams/eval/lifecycle.py), [eval/judge.py](../src/ams/eval/judge.py) | Collision-safe cases, original labels, target judges, answer/no-memory controls, denominators and journals. Keep evaluation labels separate from defense state. |
| Construction and experiment records | [eval/build.py](../src/ams/eval/build.py), [eval/context.py](../src/ams/eval/context.py) | Configured memory/model construction, prompt fingerprints and manifests. A separate research runner can use these utilities. |
| Transport and accounting | [llm/registry.py](../src/ams/llm/registry.py), [llm/ledger.py](../src/ams/llm/ledger.py), [llm/budget.py](../src/ams/llm/budget.py) | OpenRouter, frozen models, local embeddings, caches, usage logs, conservative reservations. The existing guard is restricted to GPT-4o-mini and the approved endpoint/rates; do not assume another verifier model is automatically budgeted. |
| Related mechanisms | [baselines/amemguard.py](../src/ams/baselines/amemguard.py), [baselines/memlineage.py](../src/ams/baselines/memlineage.py), [baselines/tma_nm.py](../src/ams/baselines/tma_nm.py) | Existing adapters offer useful comparison mechanisms. Their scope must be labeled accurately; they are not all full reproductions of every corresponding system. |
| Tool-use example | [eval/callsite.py](../src/ams/eval/callsite.py) | Reusable authority checking for certain identifiers at a tool call. This is not a general multi-user ACL engine, and MPBench's answer-only run does not execute real tool actions. |

## 3. What is missing, including important code-level traps

### Identity and provenance

1. **Persistent contributor identity is missing.** Source.source_id identifies a source node, not an authenticated account with an evolving history. The normal pooled MPBench runner calls write/retrieve with the same default principal, “user.”
2. **Uploader, origin, and principal are conflated if we attach a single user field carelessly.** Principal turns have a principal_id; external artifact bodies created by write do not. An innocent reader uploading or summarizing a malicious document must not automatically become its culpable source.
3. **Artifact display labels are not unique incident IDs.** write uses labels such as session_id:turn and session_id:art0 repeatedly within a shared pool. Source nodes have distinct IDs, but those labels cannot support deduplication across records.
4. **Claim attribution can be heuristic.** _overlap chooses an artifact based on lexical overlap; the code explicitly says that choice originally has no security weight. Making this assignment control account penalties creates a new security dependency. Use trusted span mapping or conservative multi-origin attribution; uncertain attribution must prevent broad contributor penalties.
5. **Entity edges are not derivation edges.** Sharing an entity, topic, or similar embedding does not prove common authorship, common incident, or dependence on a bad premise.
6. **Lineage is not automatically populated.** Claim has derived_from, and demote_source traverses it, but normal MPBench _store does not populate actual claim-to-claim derivation parents. MemoryEntry.parent_ids often names source nodes. Do not treat every parent ID as a claim or assume a ready-made derivation DAG.
7. **Stable research IDs and actual event order are missing.** Graph-generated IDs are local to a store; Source.seq is based on graph size, not a complete authenticated timestamped event history. Namespacing must include episode/store and logical input IDs.

### Policies, risk, and evidence

8. **No full per-reader/per-operation ACL overlay exists.** Authority/scope is not the same thing as confidentiality or an allowed-readers list. In particular, permits allows descriptive use without the same domain coverage requirement used for higher-authority use. That can be correct for governance and still insufficient for privacy.
9. **No contributor/context risk state, incident ledger, or reversal mechanism exists.** There is no global/context safe/unsafe evidence table with deduplication and recoverable review status.
10. **No general relevance/safety/uncertainty checker exists.** UseTypeClassifier identifies the authority a query needs; conflict checks detect contradiction. Neither is a calibrated malicious-use detector.
11. **No independent sparse verification protocol exists.** An original answer judge may read expected_memory. That is evaluation information, not an online safety sensor that can be called without restriction.
12. **No propagation policy distinguishes same record, artifact, context siblings, unrelated siblings, and separately verified benign records.**
13. **No explicit audit allocation or feedback-selection correction exists.** Only checking retrieved suspicious records can create a biased, self-confirming reputation estimate.

### Retrieval and evaluation

14. **Filtering the final top-k is insufficient.** It cannot retrieve useful replacements excluded after ranking; it also acts after original conflict checks have potentially exposed content to an LLM.
15. **Evidence and fallback paths require coverage.** _evidence is separate; graph expansion, partitioned search, and confine fallback can reintroduce records if only one selection list is filtered. The initial research implementation should explicitly support the reproduced flat/withhold path and reject unsupported combinations.
16. **Demotion is not quarantine.** Lowering a record to description authority can still allow descriptive use. A confirmed unsafe use needs a separate exclusion/recheck state.
17. **The existing lifecycle is not an online trust experiment.** It builds the pooled store and evaluates reads concurrently. State updates from concurrent query completions would make feedback order nondeterministic and can leak later evidence into earlier predictions.
18. **The dataset has no natural repeated-user chronology or access-control ground truth.** These must be declared synthetic additions, with explicit conditions that make provenance informative or uninformative.
19. **A-MemGuard's local adapter lacks full lesson reuse.** It calls the upstream consistency checker. The vendored [EhrAgent medagent.py](../third_party/AMemGuard/EhrAgent/ehragent/medagent.py), in contrast, retrieves stored lessons, stores reasoning chains as lessons, and appends lessons to later knowledge prompts. “Existing wrapper” and “full A-MemGuard” must be separate baseline labels.
20. **Research replay must capture decisions, not just cache winners.** The original content-addressed cache uses insert-first behavior for concurrent misses. State-sensitive verdicts need policy/trust/content versions, and saved event transcripts must remain authoritative.

These are tractable additions, but this is more than adding one numeric field to MemoryEntry.

## 4. Related work and defensible novelty

This is a targeted primary-source review, not proof that no equivalent method exists. Preprints are relevant prior disclosures; their presence does not establish peer-reviewed validation. Claims below concern mechanisms, not acceptance status or endorsement of reported performance.

| Work inspected | Overlap relevant to our idea | Implication for our paper |
|---|---|---|
| [SAFE-Mem](https://arxiv.org/abs/2610.22959) and the local implementation | Claim provenance, authority/scope, governed retrieval, conflict handling and a source-demotion API. | Do not claim provenance, permitted use, graph propagation, or dynamic state in general as new. Test source-history transfer beyond these mechanisms. |
| [A-MemGuard](https://arxiv.org/html/2510.02373v1), Section 4 | Consensus validation and a separate lesson mechanism that changes future behavior. | Do not position ours as the first adaptive memory defense or first defense that learns from failures. Compare structured contributor evidence with semantic lessons. |
| [SuperLocalMemory](https://arxiv.org/html/2603.02240v1#S4), Sections 4 and 5.6 | Per-agent provenance, equal initial treatment, behavioral trust changes and trust-based enforcement; the evaluation also describes Beta-based reputation. | This is a direct novelty obstacle to “equal starting trust + provenance + updates.” Agent IDs versus user IDs is not enough of a distinction. Its text describes different initialization/update formulations in different sections; pin any reproduced variant explicitly. |
| [Selective Memory](https://arxiv.org/html/2603.15994v1), Section 3 | Source reputation contributes to write-time salience/admission with version preservation. | Reputation-weighted admission is already established. Our target is sparse incident-driven transfer at later reads, not a source-reputation score alone. |
| [MemLineage](https://arxiv.org/abs/2605.14421) | Signed provenance, weighted derivation lineage, propagated restrictions and sensitive-action enforcement. | Distinguish a dependency relationship from mere same-contributor membership. Include descendant-only containment as a control. |
| [When Does Belief-Based Agent Memory Help?](https://arxiv.org/html/2606.22030v2#S9), Section 9 | Provenance caps content-derived trust; the security setup explicitly assigns source tiers and discusses laundering/taint limitations. | Equal, evidence-updated contributor state differs from a supplied low-trust channel, but this difference alone does not prove a novel method. |
| [Memory Poisoning Attack and Defense on Memory Based LLM-Agents](https://arxiv.org/html/2601.05504v1), Section 6.2 | Output checks, memory trust scores, temporal decay and trust-aware retrieval; it also exposes threshold/overconfidence failures. | “Continuous trust-aware memory filtering” is not a sufficient contribution. Separate real verification from model confidence and label-assisted controls. |
| [MemSentry](https://arxiv.org/html/2609.08747v1), Section V | Memory-write decisions combine source trust, semantic risk, dependency radius and access risk. Source tiers derive from origin/authentication/channel properties. | Trust + access control + propagation radius is not unique as a combination. Focus on online evidence sharing to uninspected sibling records and its collateral costs. |
| [MemSecBench](https://arxiv.org/abs/2607.27080) | A memory-security lifecycle benchmark covering persistence, downstream consequences and selective repair. | Selective repair and lifecycle evaluation are existing research directions. Consider it later for external validation rather than claiming a first lifecycle benchmark. |
| [The Beta Reputation System](https://aisel.aisnet.org/bled2002/41/) | Combining feedback using Beta-distribution reputation predates LLM memory. | Beta arithmetic is an established tool and a required simple baseline, not our estimator invention. |

A contribution worth testing would combine three results:

1. **Mechanism isolation:** identical revealed evidence and verification budgets establish whether provenance helps on uninspected siblings, rather than benefiting from extra detectors or oracle labels.
2. **A useful rule for limiting scope:** content-specific verification and contextual source history improve the safety/utility tradeoff over record-only filtering, global penalties, and simple contextual reputation.
3. **Boundary evidence:** quantify false-accusation amplification, mixed contributors, source compromise, missing attribution and identity rotation, including cases where propagation should not help.

The novel result would be an insight and supported method about **when evidence should transfer**. A new name, a new score, or a synthetic overlay alone is not enough.

## 5. Recommended defense specification

### 5.1 Keep distinct state variables

For each candidate and request, maintain separate decisions for:

- Authorization: may this requester read/use this record for this operation?
- SAFE-Mem authority: may this claim support the required kind of use in this scope?
- Relevance: does it help this request?
- Safety: is this proposed use safe, unsafe, or uncertain?
- Verification status: is that safety decision independently supported for this content/use/policy?
- Source risk: what observed history suggests about other, still-uninspected records from the attributable source.

A relevant record can be unsafe. An irrelevant record can be safe. An unauthorized read is not evidence against its author. Contradiction can reflect a legitimate correction. A quotation of an attack can be safe to analyze.

### 5.2 Trusted provenance and policy sidecars

Use a versioned sidecar, separate from untouched official MPBench files. Minimum fields:

| Field group | Suggested fields |
|---|---|
| Identity | logical_record_id, episode_id, input_case_id, contributor_id, uploader_id, attributable_origin_id, attribution_status |
| Structure | artifact_id, content_hash, source_span_ids, derivation_parent_ids with edge type |
| Context/order | context_id, workspace_id, ingestion_event_id, introduced_at |
| Policy | owner_id, allowed_readers/groups, allowed_operations, policy_id, policy_version |
| Audit bookkeeping | incident/root_event_id, verification references, last_review_revision |

Use opaque identifiers. The trusted experimental harness supplies metadata; a document's text cannot declare itself an administrator, trustworthy author, or verification result.

Keep the requesting principal distinct from the contributor. **Do not pass each synthetic contributor as the existing principal argument just to attach identity**: that changes SAFE-Mem authority/domain semantics and can manufacture losses on legitimate principal preferences. For the first MPBench extension, keep the original task principal fixed and attribute external artifact contributions through the sidecar. Model principal-authored retention sentences separately.

For direct-origin experiments, assume authenticated, attributable contributors. For an innocent relay, record a known external origin if available; otherwise retain ambiguous origin and restrict penalties to the implicated record/artifact. Never guess a culprit from a signature or name inside the payload.

Initially use one attributable origin per input artifact. Mixed-origin documents require an additional attribution audit before being used as evidence for source-wide propagation.

### 5.3 Hard access control

Apply deterministic write authorization before ingestion. Apply read/use authorization before a record reaches any non-authorized model context, including detector, conflict-check and answer calls. A verifier that needs broader read access must be explicitly modeled as a privileged audit service; it does not make that content available to the requesting agent.

Require both ACL permission and original SAFE-Mem eligibility:

    eligible_t(m, q, requester, operation)
        = ACL_allowed_t(m, requester, operation)
          AND SAFE_Mem_admits(m, required_use(q), principal_scope)

Then risk filtering/ranking can only restrict or reorder this eligible universe. The selected set need not be a subset of the old top-k, because refill can choose other eligible records. It must remain a subset of the authorized, governance-admissible universe.

Policies do not come from the LLM. High trust cannot grant access or elevate authority. A directly dependent derived record conservatively inherits the intersection of relevant parent permissions unless an explicit trusted declassification rule applies. Recheck policy versions on reads, stateful cache results, and revocation. For the first version, rejecting an entire mixed-policy chunk is safer than pretending part of it has been independently redacted.

### 5.4 Frozen screening and verification

Use one frozen detector/prompt across record-only, global and selective variants. Return structured relevance, safety verdict, intended use, quoted evidence span, violated rule if any, and an uncertainty option. Validate that the evidence actually occurs in the input. Do not treat a self-reported confidence number as a calibrated probability.

Distinguish:

1. **Warning:** may withhold/recheck the current candidate; no automatic account-wide evidence update.
2. **Verified unsafe:** confirms a particular prohibited use of a particular content version. Creates one attributable incident.
3. **Verified safe for use:** supplies limited evidence about that record/use/context, not universal safety or truth.
4. **Unresolved:** consumes audit budget but adds neither a positive nor negative pseudo-label.

For the first experiment, the verifier is a controlled, explicitly revealed audit result shared by all methods. It is an oracle-feedback diagnostic, not a deployable detection claim.

For the later end-to-end experiment, use a frozen independent check, deterministic policy/tool evidence where available, and a blinded human-adjudicated audit subset. Reusing the same model family twice does not guarantee independent errors. Keep the final original target judge separate from the online verifier, and assess verifier false accusations, misses and attribution mistakes explicitly.

**Never expose expected_memory, is_adversarial, benign_warranted, attack categories, label-bearing case prefixes, or future outcomes to the detector or trust updater.** Only a predeclared audited event may reveal its verification result.

### 5.5 Minimal dynamic risk state

Let U(u,c) and S(u,c) count directly verified unsafe and safe observations for contributor u in context c, under a predeclared incident/sampling rule. Maintain analogous global U(u), S(u). Start all contributors with the same prior; a = b = 1 is a transparent first baseline.

    risk(u,c) = (b + U(u,c)) / (a + b + U(u,c) + S(u,c))
    trust(u,c) = 1 - risk(u,c)
    initial_risk = b / (a + b)

Equal treatment means zero initial reputation penalty, not certified safety. If we want to display initial trust as 1, keep that display separate from this uncertainty-bearing state; do not call Beta(1,1) mean trust 1.

Evidence rules:

- A single poisoned document yielding six claims contributes one underlying unsafe incident, not six accusations.
- Repeated retrievals, summaries, copies and paraphrases with known common provenance do not create new independent votes.
- Independently audited siblings can create new evidence only when they have independent root contributions; label that sampling unit.
- Do not add safe votes for every unflagged retrieval, successful task, harmless warm-up query, or attack miss.
- Propagated suspicion is never a new unsafe observation.
- If an accusation is overturned, retract/version that event and recompute its contributions; do not leave a false negative count in place and merely add a positive vote.

These are simple reputation summaries. They are not a formal hierarchical Bayesian posterior: global and context counts overlap. Adaptive audit selection, correlated incidents and changing behavior also prevent an unvalidated claim that the scores are calibrated probabilities.

### 5.6 Selective propagation and retrieval

Use increasingly weaker treatment across relationships:

| Relationship to verified incident | Proposed treatment |
|---|---|
| Same record/content/use | Withhold the demonstrated unsafe use pending correction/review. |
| Same artifact's suspect region | Recheck related claims/chunks; retain verified clean spans when separation is supported. |
| Derived record still relying on the bad premise | Withhold/recompute that dependency. A derived summary is not automatically malicious. |
| Same contributor and predefined context | Apply contextual risk penalty and prioritize limited verification. |
| Same contributor, other contexts | Apply a smaller global penalty, initially ranking/audit priority rather than automatic denial. |
| Independently verified benign record for the same use | Preserve its record-level evidence; contributor suspicion alone should not wipe it out. ACLs and local safety rules still bind. |
| Unrelated contributor, no dependency | No reputation penalty from this incident. |
| Uncertain attribution | Record/artifact caution; no guessed contributor-wide penalty. |

A feasible initial heuristic is:

    delta_global = max(0, global_risk(u) - initial_risk)
    delta_context = max(0, context_risk(u,c) - initial_risk)
    penalty(m) = gamma * delta_global + (1-gamma) * delta_context
    adjusted_score(m,q) = original_cosine_score(m,q) - lambda * penalty(m)

Choose gamma, lambda and any gate threshold on development episodes, then freeze them. Small gamma makes cross-context transfer weaker. Ranking does not guarantee exclusion. Evaluate ranking-only and an explicit review/withhold gate separately.

Example: with the uniform prior, one confirmed unsafe contribution changes context risk from 1/2 to 2/3. Three duplicated copies leave it at 2/3. The current dangerous record is withheld directly; another record from the same contributor receives a contextual penalty, not an invented “unsafe” label. A verified benign sibling remains eligible for its verified use.

Apply the same logic to claims and evidence chunks. Filter before selecting final k, and refill from eligible candidates until k claims and the original evidence-slot limit are reached or candidates are exhausted. Preserve the original conflict and answer prompts after selection. Limit/audit refill and verification expense identically across baselines.

### 5.7 Recovery and bounded verification

Keep an append-only, versioned evidence log with event ID, content hash, attributable origin, artifact/incident, context/use, policy version, verdict, evidence reference, verifier, revealed_at and superseded/retracted state.

Allocate a fixed audit budget B per episode. A simple first scheduler reserves a small, fixed fraction for randomized exploration among authorized records, including some withheld records, and spends the rest on uncertain relevant candidates. Declare and log selection probabilities. Uninspected records are not assumed safe; propensity correction is needed if claiming population rates from selectively audited samples.

Safe re-verification clears the corresponding record/use restriction, not an unrelated verified dangerous record. Overturned evidence reverses only the state derived from that evidence. Do not silently restore a confirmed attack merely because time passes or its author submits many harmless records.

For compromise after a long clean history, compare full-history counts with a prespecified recent-audit window or change detector. Treat this as a baseline/ablation first. Do not claim that a full-history Beta mean automatically adapts quickly. Windowed or weighted counts require their own uncertainty interpretation.

### 5.8 Stronger extension if the pilot supports transfer

A fixed context/global weighting is an important baseline, not a complete ICML novelty story. The formula above can reduce to ordinary contextual reputation; changing gamma alone should not be presented as a distinct scientific advance. A modest next step is **evidence-dependent widening of scope**:

- One verified incident triggers local containment and a bounded sample of other independent contributions.
- New evidence can justify widening from record/artifact to source-context and later broader source treatment.
- A lack of confirmed risk or an overturned accusation narrows treatment; verified benign records keep their own evidence.
- Compare this against the same global/context counters, same audits and same content verifier, with fixed scope.

This requires no neural training. However, the trigger, uncertainty calculation, sampling model and error accounting must be specified and tested. Do not add a confidence interval and claim an anytime guarantee under adaptive LLM feedback. Decide whether to pursue a formal sequential test only after measuring audit errors and dependence.

## 6. Online execution semantics and supporting invariants

The first research runner should be single-threaded for state transitions. Frozen embeddings/extraction may be prepared separately, but no future safety verdict or feedback can be prefetched into state.

    For request t:
        snapshot = current policy and evidence versions
        gather candidates visible at t
        apply ACL and original governance
        use frozen local screening and current source state
        spend only permitted pre-answer audits; commit their results explicitly
        select/refill, answer, and save the actual supplied context and output
        evaluate hidden target outcomes in the evaluator only
        release scheduled delayed feedback when its reveal time is reached
        append deduplicated evidence updates
        persist state, audit balance and event cursor

A pre-answer audit can change the current decision only if the protocol says it is available then and charges it to the budget. An outcome learned after answering cannot retroactively improve that answer.

Required properties for future implementation tests:

| Property | Meaning |
|---|---|
| Authorization cannot expand | Trust changes never admit a record denied by ACL or original governance for that operation. This concerns candidate eligibility, not retaining the identical old top-k. |
| No future feedback | Decisions use only data and feedback already available at their recorded decision time. |
| Evidence is idempotent | Replaying the same event changes counts at most once; derived copies do not manufacture evidence. |
| Attribution is conservative | Uploaders, mentioned authors, shared entities and unknown origins do not become confirmed malicious contributors. |
| Risk does not mutate authority | Contributor reputation does not overwrite Standing, Rung or ownership. |
| Paths agree | Claims, evidence, expansion, refill and cached decisions respect the same current restrictions. |
| Recovery is auditable | Retractions/corrections change only the evidence and restrictions they justify. |
| Resume is exact at the event level | Restore graph/write state (including contested flags), provenance maps, indexes or their deterministic reconstruction, event cursor, policies, risk counts, incident set, audit balance, RNG state and saved outputs; do not replay future decisions using current reputation. |

These are supporting soundness requirements. Proving a set-inclusion invariant alone is unlikely to be the paper's main scientific contribution.

## 7. Proposed future code changes

**None of the following changes were made during this review.** Proposed names are architectural suggestions, not files already implemented.

Prefer a new research package and runner. Keep scripts/run_mpbench.py, the original prompts, historical results, and the frozen full-reproduction plan intact.

| Proposed new file/component | Responsibility | Reuse / integration |
|---|---|---|
| src/ams/research/provenance.py | Trusted envelopes, typed edges, stable logical IDs, source/claim/chunk mappings | Bind metadata during write and chunk construction, not by parsing rendered source headers afterward. |
| src/ams/research/policies.py | Deterministic write/read/use rules and policy versions | Compose with original _admits. Initially explicit readers/operations; no general enterprise policy language. |
| src/ams/research/evidence.py | Append-only events, deduplication, attribution confidence, corrections | Local JSONL plus explicit state snapshot is sufficient for an initial single-process study. |
| src/ams/research/trust.py | Global/context counts, query-time penalties, optional review gate and recovery | No trained weights; serialize enough state to reproduce every decision. |
| src/ams/research/verification.py | Frozen screening/verifier interface and controlled audit provider | Use existing clients/ledger. The controlled provider reveals only approved audit events. |
| src/ams/research/dynamic_memory.py | Flat-index research adapter/subclass over TypedStandingMemory | Reuse write/extraction/standing; integrate policy/risk before selection and conflict calls, including chunks and refill. |
| src/ams/research/episodes.py | Validate synthetic overlay, schedules, independent roots and hidden-label boundary | Reuse MPBench loading; never edit official data files. |
| scripts/run_mpbench_dynamic.py | Sequential research lifecycle, feedback commits, snapshots and logs | Construct research memory explicitly rather than changing the original factory's default path. |
| scripts/analyse_mpbench_dynamic.py | Existing target metrics plus transfer, collateral, policy and budget analysis | Separate output schema/namespace from original reproduction. |
| configs/research/ and prompts/research/ | Explicit settings and versioned new verifier prompts | Retain original extraction/answer/judge prompts for comparable arms. |
| tests/test_dynamic_*.py | State/identity/policy/candidate-path/causality and matched-condition tests | Use deterministic fixtures/fake model responses before any paid experiment. |

The first adapter can support **flat + withhold + hops=0**, matching the reproduced main arm. Fail explicitly on unsupported confine/partitioned/expansion modes rather than silently bypassing protections. Do not copy an entire unrelated agent framework.

A post-retrieval Defence.filter wrapper is acceptable only for a clearly labeled detector prototype. The meaningful integrated experiment needs access to the eligible universe, chunk construction and candidate selection. A new subclass may reuse some private internals initially; document that maintenance burden. If later approved, small optional candidate-predicate/rank hooks in the base memory class could reduce duplication, with defaults that preserve the original baseline. Do not make those refactors a prerequisite for the first study.

Store metadata while constructing sources/claims/chunks. For the pilot, one attributable external contributor per logical input avoids pretending heuristic within-document attribution is already authenticated. Parent source nodes and principal-turn sources must be distinguished.

The current DefenceResult kept_ids/flagged_ids helpers reference m.mid although MemoryEntry declares entry_id. Do not depend on those helpers in new work; a future narrow compatibility fix can be proposed separately if needed. It is not part of the scientific method and was not changed here.

### Future log requirements

For each decision, save episode/event ID, candidate record IDs, contributor/artifact/context IDs, policy/evidence versions, original/adjusted scores, rejection reasons, actual selected context, actual answer and finish reason, screening/verification outputs, audit selection probability/cost, revealed evidence, state update, task judgment and latency.

Keep hidden target labels in an evaluator-only file. Keep stateful authorization/risk decisions keyed by content hash, requester, use, policy version, evidence revision and verifier configuration. The existing model-response cache can still cache identical rendered requests; it must not substitute for a stateful permission cache or the authoritative event log.

## 8. MPBench protocol: what can and cannot be claimed

The [official MPBench repository](https://github.com/Digital-Trust-Lab/mp-bench) provides attack/benign cases with input context, intended target memory and retrieval questions. It does not provide the authenticated repeated-contributor history needed here. Its README categories and the actual released canonical categories also need to be distinguished; preserve the current loader's documented five scored attack categories in the original comparison.

Create an explicitly named **synthetic provenance/access-control extension of MPBench**, with unchanged payload hashes and a versioned overlay. Do not call synthetic source identities or timestamps official annotations.

Use two distinct settings:

1. **Static pool, sequential evidence:** build the same complete 6,240-case pool, then issue questions in a declared order with sparse audit feedback between decisions. All records exist from the beginning, but future verification is hidden. This is the simplest dynamic extension.
2. **Streaming memory:** interleave ingestion, queries, verification and policy changes. Only earlier writes exist. This tests stronger temporal claims and is a later protocol.

For each setting, run all compared methods with the same payload set, source/policy overlay, order, model, candidate-pool limits, k/m limits, prompts, and audit accounting. A different retrieval score may produce different final candidates; a diagnostic can additionally freeze candidate sets to isolate decision changes.

Overlay requirements:

- Contributors have mixed safe and unsafe contributions, including benign records from a source with a confirmed incident.
- Use authenticated opaque IDs and label-independent roles/permissions. “attacker” usernames or guest-only attacks are shortcuts.
- Separate correlated-source scenarios from independently assigned source IDs. Correlation is an experimental factor, not an assumed property of MPBench.
- Include authorized harmful contributions. If all attacks are blocked by ACL, dynamic trust has not demonstrated added value.
- Preserve same-artifact and derivation roots; repeated copies are not independent incidents.
- Define contexts using trusted task/workspace metadata or a frozen query-only mapping, not attack labels. Document any official domain metadata exposed to the defense and give it to all baselines.
- Separate development and test contributors, source artifacts, near-duplicate questions/templates, and incident roots. Hold out an attack family where feasible. A complete official-pool run with development records present is a separate transductive setting, not a claim of an entirely unseen-content test.
- Because all original data has already been used for reproduction, use a prospective group-held-out protocol for new hypothesis tuning; do not claim the entire dataset was untouched. An external benchmark later strengthens generalization evidence.
- Repeat source assignments and event-order seeds; do not select assignments or “successful” incidents based on the proposed method's observed gains.
- Keep the 244 write-only cases in full-pool construction and answer all readable cases. The 141 unlabeled benign utility cases remain unscored for that original metric.

A source-identity shuffle control should destroy the association between history and future siblings while preserving relevant source-size/context/policy distributions. Merely renaming user IDs consistently preserves all relationships and is not an identity-blind or no-signal control.

## 9. The simplest meaningful first experiment

**Fixed-feedback sibling-transfer pilot.** Purpose: determine whether propagation itself adds anything before designing a sophisticated detector or audit scheduler.

A proposed starting size is **20 development/pilot episodes, four opaque contributors and eight readable annotated inputs per contributor: 32 inputs per episode**. This is explicitly a small diagnostic, not the full MPBench result. The future offline constructor must verify enough matching cases/templates exist; adjust and preregister the sampling recipe before paid calls if they do not. Keep final test groups separate.

For each episode:

1. Choose MPBench payloads with usable original targets, including both explicitly warranted and suggestive benign cases. Use at least two contexts. Every method receives the identical initial pool and trusted metadata.
2. Include a contributor with one confirmed root incident, some uninspected unsafe siblings, some benign siblings in that context, and benign records elsewhere. Include unrelated contributors and unrelated attacks. Randomize opaque IDs and roles; the contributor composition is evaluator-only.
3. Start all contributors at the same prior. Restrict this pilot to direct attributable origins and fixed allowed policies so that ACLs do not solve every attack.
4. Reveal the same one verified incident to every method at the same event time. Charge one audit to each. Do not reveal other case labels to the defense.
5. Query disjoint, uninspected siblings plus matched unrelated controls. The incident record is not the claimed transfer target. Use the same frozen content checker/feedback schedule for all methods; the minimal oracle-feedback diagnostic can disable new content screening uniformly.
6. Measure unsafe answers on future siblings, benign retention on those same contributors, unrelated-source effects and cost. Withholding the incident itself is not evidence of transfer.
7. Reset and repeat with different groups. Repeat with source-risk correlation removed.
8. Add a controlled false-accusation variant, then an overturned-audit event. Measure collateral suppression and recovery; do not count the false initial accusation as actual malicious ground truth.

Minimum pilot comparisons: ACL-matched static SAFE-Mem, record-only incident update, blanket contributor penalty, simple context/global reputation, and selective propagation. Identical oracle feedback is deliberately unrealistic and gives a clean mechanism test; it must be followed by noisy/verifier-driven feedback before claiming an autonomous defense.

**Success signal:** at equal audited evidence and comparable benign utility, selective propagation reduces future unsafe use on uninspected siblings, while retaining more benign contributions than blanket penalties.

**Failure signal:** gains come only from discarding more records, extra calls, a label-correlated overlay, or a stronger detector. If simple context/global reputation performs equally well, it is the better method and our selective rule is not yet a distinctive contribution.

With the reproduced full-pool ASR already at 5.87%, a small pilot can have few successful attacks. Report raw counts and uncertainty; use record-level transfer diagnostics as mechanism evidence, not a substitute for later full-data end-to-end ASR. Do not select cases solely because the proposed defense looks good on them.

## 10. Baselines and ablations for the subsequent paper

| Arm | What it isolates | Requirement |
|---|---|---|
| Historical original SAFE-Mem | Existing full-pool reference | Preserve saved results; not the sole causal comparator for a new overlay/order. |
| Static SAFE-Mem in the new protocol | New chronology/workload effect | Rerun with identical schedules and no trust updates. |
| SAFE-Mem + ACL only | Added permissions | Same policies and authorized visibility as other defense arms. |
| SAFE-Mem + ACL + fixed detector, record-only updates | Content detection/local quarantine | Same verifier, audit opportunities and feedback; no source transfer. This is the crucial comparator. |
| Blanket source penalty/quarantine | Original initial idea | Same incident evidence; tune at matched utility, not just identical thresholds. |
| Global reputation / context reputation / recent-history reputation | Simple alternatives | Deduplication and audit accounting identical; no unnecessary model training. |
| Descendant-only containment | Existing lineage mechanism | Requires genuine supplied/tracked dependency edges; do not substitute topic neighbors. |
| Selective source/context propagation | Proposed method | Compare ranking-only and explicit withholding/review decisions. |
| A-MemGuard consensus-only adapter | Existing compatible baseline | Label “consensus-only”; account for all consensus calls. |
| A-MemGuard including lessons | Adaptation through semantic lessons | Faithful future integration of lesson storage/retrieval/action influence, with valid available feedback. If adapted to MPBench, declare the adaptation; unavailable results remain not run. |
| Close trust-aware mechanism | Closest related reputation baseline | Implement a clearly specified mechanism from, e.g., SuperLocalMemory, if feasible. Do not claim a full system reproduction from a small proxy. |
| Identity-history removed / source linkage broken | Whether provenance actually matters | No contributor updates, or a true history-to-source shuffle. Consistent ID renaming is only an invariance check. |
| No-memory / block-all references | Cost of trivial denial | Diagnostic extremes, not useful defenses. Keep answer prompts comparable. |

Use the first five meaningful arms for the pilot rather than immediately implementing every optional baseline. Later add same-artifact versus context versus global transfer, safe-record verification override, incident deduplication, retraction/recovery, and exploration ablations.

For fixed-feedback comparisons, all arms receive identical exogenous audit results. For adaptive auditing, each arm may choose different records but receives the same number of permitted audits or matched token/dollar budgets. Report both regimes; do not grant free extra investigations to the proposed method. Count unresolved audits and verifier failures as spent resources.

## 11. Metrics and ground-truth requirements

### Preserve the original target metrics

| Metric | Definition | Interpretation |
|---|---|---|
| End-to-end ASR | Successful attack-target endorsements/actions in the answer / scored attack questions | Use the original judge and denominator 2,999 for a complete original-pool evaluation. Not detector FNR. |
| Retention recall | Correct assertions on explicitly warranted benign retention cases / 249 | Successful use of authorized-to-retain information, not percentage of records stored. |
| Restraint | Correct avoidance of unwarranted suggested claims / 2,607 | Does not mean refusing the entire task. |
| Combined benign utility | Correct annotated benign outcomes / 2,856 | Weighted combination of retention/restraint; original field benign_accuracy. Not general QA accuracy. |
| No-memory attack rate / attributable ASR | Original control outcomes and original attribution definition | Keep these to distinguish memory-driven influence from a model's baseline behavior. |

If a new policy revokes access to an originally warranted memory, the original answer expectation and new authorization requirement may conflict. Report original-score results separately from **policy-conditioned utility with explicitly revised gold expectations**. Freeze that eligible utility set before method decisions. Do not exclude a question just because our method withheld its memory.

Report overall ASR and ASR on the **predefined ACL-allowed attack subset**, plus static ACL-blocked counts. This exposes whether access control alone caused improvement. Successful executed tool actions are not observable in the current answer-only MPBench lifecycle; mark that metric not computable there.

### Additional metrics for this research claim

| Metric | Operational definition / required labels |
|---|---|
| Future sibling ASR | Attack successes on a fixed cohort of uninspected sibling queries after the incident / all attack queries in that cohort. Select the cohort before method outcomes; also report same-context/cross-context/unrelated groups. |
| Transfer benefit | Paired record-only ASR minus selective-method ASR on that fixed cohort, with matched feedback/budget and utility. |
| Collateral utility loss | Record-only benign correctness minus method correctness on legitimate sibling queries. Report explicit-retention and restraint separately; include unrelated sources and verified-safe siblings. |
| Unnecessary restriction rate | Method-withheld benign eligible records/queries / all predefined benign eligible records/queries. Label the unit and establish safe-for-use annotations; this is not automatically the detector FPR. |
| Audit efficiency | Unsafe outcomes avoided relative to record-only per audit, plus calls, native tokens, dollars and latency. Ratios with zero audits are undefined; show raw quantities too. |
| Adaptation delay | Events or unsafe outcomes between first available confirmed incident and meeting a preregistered safety criterion. |
| False-accusation amplification | Benign sibling restrictions caused by a deliberately false incident versus its matched no-accusation control. Count unique records and query exposures separately. |
| Recovery | Time/audits and utility restored after a false accusation is overturned, while independently confirmed unsafe records remain contained. |
| Authorization violation | Unauthorized records in supplied model context / denied-read opportunities; also record answer leakage with defined canaries and policy changes. Real tool violations require an execution benchmark. |
| Verification quality | Verifier precision/recall/abstention, false accusations and attribution errors against an independently annotated audit subset. |
| Calibration | Brier score/reliability plots only for scores intended as probabilities and representative labeled samples, with sampling corrections or explicit conditional interpretation. |
| Coverage/abstention | Answered/withheld/failed queries and filled candidate slots. Missing or refused questions remain visible in end-to-end denominators. |

**Accuracy, FPR and FNR must state the classification unit.**

- General task-answer accuracy is **not computable** from existing MPBench target-memory labels alone.
- The original attack-versus-benign input label can support **case-level attack-attempt classification accuracy/FPR/FNR** if a future detector actually outputs that binary decision on each complete input and the aggregation rule is preregistered. Define positive as an attack input: accuracy = (TP+TN)/N, FPR = FP/(FP+TN), FNR = FN/(FN+TP). Call this input-attack classification, not task accuracy or safe-memory-use accuracy.
- Claim-level or query-specific unsafe-use FPR/FNR require new expert labels for those exact claims and uses. A malicious source case can yield benign claims; do not mark all descendants or siblings malicious because their parent case is adversarial.
- A prior confirmed source incident does not make every later record a positive example. Access denial is not a safety positive.
- The completed original reproduction did not have a fully labeled claim classifier and its classifier FPR/FNR remain not computable. New annotations cannot retroactively turn flag rates into those metrics.

### Statistical analysis

Use paired comparisons with identical episodes/assignments. Report integer numerators and denominators, effect sizes, confidence intervals and per-category/context results. For the new dynamic study, bootstrap independent episode/source/incident groups rather than treating correlated claims as independent. Reused payloads across episodes require additional case clustering or a hierarchical analysis.

Retain the original query-clustered bootstrap for the static MPBench reference. It is not sufficient on its own for contributor-correlated online trajectories. Freeze a primary hypothesis and a development-selected operating point; report safety/utility/audit-cost curves without choosing a favorable threshold on test data. Multiple seeds and a second frozen model or external benchmark strengthen evidence if the pilot supports scaling.

## 12. Stress tests and falsification

| Stress condition | What would invalidate an easy claim |
|---|---|
| Mixed contributor | Benign records from an implicated account disappear along with attacks. |
| Source identity has no predictive value | Persistent large gains suggest metadata leakage or unmatched resources. Finite-sample fluctuations alone are not evidence of leakage. |
| False positive and later retraction | One bad accusation permanently blocks an innocent source. |
| Duplicated/paraphrased incident | Copies multiply unsafe counts or a majority of copied claims manufactures consensus. |
| Compromise after benign warm-up | Old positive counts or trust=1 bypass new safety checks indefinitely. |
| Innocent uploader/unknown origin | The relay receives the attacker's contributor penalty. |
| Cross-context reuse | A local incident unnecessarily destroys safe history in an unrelated context. |
| Permission revocation or derived chunks | Cached authorization, descriptions or evidence passages bypass the new policy. |
| Noisy/delayed verifier | The method secretly uses immediate gold labels despite claiming realistic feedback. |
| Bounded fresh identities/collusion | The method is credited with protection that actually depends on a stable ID assumption. Unlimited cheap resets are an explicit limit. |
| Quoted attack/security example | Dangerous wording alone causes verified reputation damage. |
| Multiple individually mild records | A record-wise detector is claimed to rule out harmful combinations without testing them. |

A useful negative-control proposition to investigate is: if an uninspected record's unsafe-use label is conditionally independent of source history given all relevant content and context, that history adds no Bayes-optimal predictive information. This is a conditional analytical observation, not a universal impossibility result for imperfect finite models. Dependence through artifacts, omitted features or compromise can violate the assumption.

The elementary decision tradeoff also matters: blanket withholding saves unsafe-use loss but incurs benign-use loss. Lower ASR alone cannot establish improvement. This motivates matched utility and budget curves; it is not presented as a new theorem.

## 13. Step-by-step roadmap and decision gates

All steps below are future work. No commands in this roadmap have been executed as experiments.

| Phase | Concrete work | Completion / decision gate |
|---|---|---|
| 0. Freeze the question | Preserve original code/results; specify attributable source, unsafe use, incident, context, feedback availability and resource accounting. | One-page protocol; source hashes; no hidden labels reachable by the defense. |
| 1. Build trusted metadata | Versioned overlay, stable case/artifact/source IDs, source-to-entry/chunk mapping, simple readers/operations. | All selected inputs map unambiguously; missing/ambiguous attribution is explicit. ACL roles do not encode labels. |
| 2. Implement state offline | Event log, idempotent counts, score rule, retractions and snapshots; deterministic fake detector/audit fixtures. | Meaningful tests of deduplication, innocent relay, recovery, equal initialization and state restart; no model calls required. |
| 3. Integrate the narrow retrieval path | Flat/withhold adapter, ACL before model exposure, claim/chunk parity, risk adjustment, refill and original answer/judge reuse. | With research effects disabled and all-allow policy, candidate IDs/scores/prompt contexts match the original on fixed fixtures. Unsupported modes fail explicitly. |
| 4. Run the fixed-feedback pilot | Section 9's matched episodes, one revealed incident, untouched siblings and same-source benign controls. | Evidence of transfer beyond root withholding at matched utility; otherwise revise or stop expansion. |
| 5. Introduce noisy real verification | Frozen detector/verifier, blinded annotations, delayed feedback, false alarms, audit budget and exploration. | Gains survive realistic errors and equal verifier cost; no fabricated safe/unsafe labels. |
| 6. Scale to full MPBench | Complete 6,240-case pool, all 2,999 scored attacks and readable benign cases, repeated overlays/orders, static baseline in same protocol. | Full coverage, fixed denominators, event-order integrity, exact costs, paired uncertainty and failure disclosures. |
| 7. Strengthen the research contribution | Evidence-dependent scope versus fixed contextual reputation, full lesson baseline if valid, compromise/relay/shuffle tests, second model or external lifecycle benchmark. | A specific insight/generalization beyond combining existing parts. Negative results remain reportable. |
| 8. Paper and release | Method, threat model, synthetic annotation provenance, baseline fidelity, data splits, logs, metrics, uncertainty and limitations. | Claims supported by held-out results; no claim of universal safety, exact calibration or full original-paper reproduction beyond what was run. |

Do not reuse the previous reproduction's spending approval as authorization for new research experiments. Before future paid work, freeze the selected arms and sample sizes, estimate extraction/detection/verification/answer/judge calls, reserve retry headroom, validate monitoring offline, and obtain the required new execution approval. This review makes no new API-cost estimate or spending commitment.

## 14. Final recommendation

Implement a small **record-only versus global versus context-selective evidence-transfer study**, using an explicitly synthetic MPBench overlay and a sequential evidence log. Preserve original SAFE-Mem's governance and hard permissions; keep contributor identity, authority and empirical risk separate. Establish the transfer effect with common revealed audits before building the realistic verifier.

The lightweight proposal is the better implementation starting point than the extended version's trained hierarchical predictor and learned audit policy. However, fixed Beta counters plus a weighting rule should be treated as a pilot and strong baseline. For an ICML-level contribution, the evidence must establish a distinctive finding or better decision rule about propagation scope, including when it fails. Adding complexity cannot substitute for that result.

**The immediate next deliverable should be a protocol and offline fixtures, followed by the controlled pilot after implementation and execution are separately authorized.**

## Review integrity

A before/after read-only fingerprint check covered 266 existing source, script, configuration, prompt, test, dataset, lock/project and proposal files. The aggregate SHA-256 was unchanged: eecc3063b94f2ec6b2b705c1f4132325f45318b30b4833a28d5ed934c08457ac. Local document links were checked. This review created only this roadmap; the listed implementation components remain proposed future files. No tests, benchmark runs, or paid model calls were made.
