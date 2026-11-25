# When Should Distrust Spread? Selective Evidence Propagation for Agent Memory

Revised 2026-10-28 for a small, training-free extension to SAFE-Mem and an experimental research paper. This is a proposal: the new defense has not been implemented or evaluated. The earlier, more ambitious proposal is preserved in [RESEARCH_PROPOSAL_EXTENDED.md](RESEARCH_PROPOSAL_EXTENDED.md).

## 1. Recommendation

Yes, the central idea can be implemented without training a new model. Keep SAFE-Mem, frozen LLMs accessed through OpenRouter, and the cached embeddings. Add an evidence ledger, contributor trust state, and a retrieval rule. Run Python experiments and produce logs, metrics, and figures.

The research question should be:

> When one memory is confirmed unsafe, can a simple provenance-based rule reduce unsafe use of other, uninspected memories from that contributor, at the same verification budget and with less loss of useful memory than blanket user penalties?

The proposed contribution is the **scope and reliability of evidence transfer**, rather than merely assigning users trust scores. A small implementation can support a substantial research contribution if the experiments establish a useful, generalizable result. Small implementation effort does not imply small experimental effort.

## 2. Refine our original idea

Keep contributor attribution, equal starting treatment, fixed access policies, retrieval-time checking, incident records, and updates that affect related memories. Make five refinements:

1. Separate relevance from safety. Irrelevance never lowers contributor trust. A memory can be relevant and dangerous.
2. Separate permission from trust. High trust cannot grant access; an unauthorized read does not make the memory's author malicious.
3. Distinguish a detector warning from verified evidence. A warning can withhold the current record, but should not automatically penalize every record from a user.
4. Propagate suspicion by degree. Confirmed dangerous records are withheld; records sharing an artifact or depending on a bad premise receive stronger reassessment; unrelated records from the contributor receive a smaller penalty.
5. Count an underlying incident once and allow independently checked records to recover. Copies and repeated retrievals must not multiply one accusation.

This preserves our idea while addressing its main failure: one false positive can otherwise damage an innocent contributor's reputation and suppress all their useful records.

## 3. Research positioning after another literature check

| Work | Relevant overlap | Consequence |
|---|---|---|
| [SAFE-Mem](https://arxiv.org/abs/2610.22959) | Claim authority, scope, provenance, and governed retrieval. | Adding provenance and permissions is insufficient novelty by itself. |
| [SuperLocalMemory, section 4](https://arxiv.org/html/2603.02240v1#S4) | Equal initial agent trust, behavioral trust updates, per-memory provenance, and threshold enforcement. | Dynamic contributor trust with equal initialization is already closely related work. Its agent identity differs from our user setting, but that distinction alone is insufficient. |
| [A-MemGuard](https://arxiv.org/abs/2510.02373) | Detected failures become defensive lessons consulted later. | Recording lessons is not independently new. |
| [Selective Memory](https://arxiv.org/abs/2603.15994) | Source reputation participates in memory admission. | A reputation-weighted score alone is insufficient. |
| [MemLineage](https://arxiv.org/abs/2605.14421) | Provenance and derivation-lineage enforcement. | Downstream provenance propagation is an established direction. |
| [Reliability-Conditional Updating and Provenance-Capped Poisoning Defense, section 9](https://arxiv.org/html/2606.22030v2#S9) | Source provenance caps content-derived reliability; its security experiment assigns source tiers rather than learning them. | Distinguish initially equal, evidence-updated contributor state from preassigned trustworthy/untrustworthy source classes. |

These are specific overlaps, not endorsements of every empirical claim in those papers. This is a targeted review, not an exhaustive novelty search. Full comparisons must precede any priority claim about our combination or evaluation.

## 4. Minimal defense

### A. Trusted metadata and permission filtering

Use a sidecar mapping from memory/source IDs to opaque contributor ID, artifact ID, predefined task context, event time, and allowed readers. In experiments, the trusted runner assigns these fields. Payload text cannot choose its own identity or permissions.

An external document needs separate uploader and attributable-origin fields. Finding an attack in a document that an innocent user requested to summarize is not sufficient to penalize that user. Initially test directly attributable contributions; include innocent relays as a stress test.

Apply the added permission rule and existing SAFE-Mem governance before content reaches the answering agent. The added rule can only restrict the existing eligible set. Authorization failures do not count as safety feedback against an author.

### B. Frozen content checking

Use a fixed LLM prompt to assess a candidate memory in the current request and intended use. Return separate relevance and safety decisions, an evidence span, and an uncertain option. Keep this detector identical in source-aware and record-only comparisons.

An LLM warning is an allegation, not ground truth. In the controlled transfer experiment, give every method the same explicitly revealed audit result. In the end-to-end experiment, use a fixed verification procedure, document its errors, and keep evaluation labels separate. Do not feed the hidden attack label to the defense on every retrieval.

### C. Small contributor state

Maintain verified-safe and verified-unsafe evidence counts for each contributor, globally and within a predefined context. Initialize everyone with the same prior. Equal treatment means no initial reputation penalty; it does not certify safety.

A Beta-based score is sufficient for the first implementation:

```text
source risk = (b + verified_unsafe) / (a + b + verified_safe + verified_unsafe)
```

Here a and b are common prior pseudo-counts; a = b = 1 is a transparent starting baseline. This is arithmetic state updating, without gradient descent or fine-tuning. Under selective or correlated feedback, do not describe the score as a calibrated probability without validation.

Count each independently reviewed record or underlying incident once. Several extracted claims from one poisoned document are not several independent accusations. Benign and unsafe events must follow the same predeclared counting rule. Unreviewed siblings receive a changed risk estimate, not fabricated unsafe labels.

### D. Selective propagation at retrieval

| Relationship to a confirmed unsafe record | Initial treatment |
|---|---|
| The unsafe record itself | Withhold for the demonstrated unsafe use. |
| A derived record still depending on the demonstrated bad premise | Withhold or recheck; a downstream summary is not necessarily malicious. |
| Other uninspected records from the same contributor and context | Apply a stronger source penalty or prioritize re-verification. |
| Other uninspected records from that contributor in other contexts | Apply a smaller global penalty. |
| A separately verified benign record for the same intended use | Retain record-specific verification, subject to current permissions. |
| Records from unrelated contributors | No source penalty from this incident. |

A simple ranking rule is:

```text
penalty(m) = gamma * max(0, global_source_risk - initial_risk)
           + (1 - gamma) * max(0, context_source_risk - initial_risk)

rank(m, query) = original_relevance(m, query) - lambda * penalty(m)
```

Use a small fixed gamma so cross-context propagation is weaker. Choose gamma, lambda, and any withholding threshold on development episodes; freeze them for testing. These are ordinary hyperparameter choices, not training a new model. A ranking penalty does not ensure exclusion: actual withholding needs an explicit gate. Measure the two separately.

All records from one source can therefore change treatment after an incident, as in our initial idea, while the change is smaller in unrelated contexts. Shared contributor state makes rewriting every stored record unnecessary.

The first version needs no learned graph network, learned propagation policy, or reinforcement learning. Beta counts and fixed weighting are simple baselines as well as a feasible starting implementation; the paper must demonstrate insight beyond their mere combination.

### E. Recovery and structured lessons

Log record ID, attributable contributor, artifact/incident ID, use context, verdict, evidence, verifier, and event time. Treat lessons as structured data for the defense.

Restore a falsely accused record through independent review. Keep a small fixed random audit allocation so withheld sources can be checked again. Propagated suspicion never counts as fresh evidence. Benign re-verification must not automatically restore a separately confirmed dangerous record. Test whether benign warm-up or harmless contributions can hide later attacks.

## 5. Implementation scope in this repository

The algorithm can be small. The evaluation needs additional work.

| Component | Proposed change |
|---|---|
| Provenance/policy overlay | JSONL sidecar with contributor, artifact, context, readers, and event order. |
| Trust/evidence module | Global/context count tables, incident deduplication, review state, and fixed scoring. |
| Retrieval integration | Penalty and withholding hooks over authorized candidates, with refill after exclusions. |
| Detector/verifier | Frozen prompts and structured outputs through the existing OpenRouter client. |
| Experimental runner | Sequential ingest, retrieve, reveal feedback, update, and logging. |

Existing integration points:

- [`Source` and `ClaimGraph`](../src/ams/memory/graph.py) link claims to sources. However, `source_id` identifies an artifact/turn, not a persistent contributor account. `principal_id` exists, but external bodies in `write()` currently lack writer attribution. The sidecar must fill that gap without guessing identities from text.
- [`TypedStandingMemory.retrieve`](../src/ams/memory/typed.py) provides governed admission and ranking. Put research behavior behind a separate configuration or adapter. Cover claims, evidence chunks, and fallback paths. Filtering only the final top-k cannot refill useful candidates excluded by the defense.
- `ClaimGraph.demote_source` already propagates authority demotion through descendants. It is not user reputation. Demoting a dangerous claim to descriptive authority does not necessarily prevent its use in a descriptive answer.
- [`run_lifecycle`](../src/ams/eval/lifecycle.py) fills the pooled store and reads concurrently. Add a sequential research runner to evaluate dynamic feedback without future-label leakage.

The deliverables are experiment code, configurations, a versioned dataset overlay, event logs, result tables, and paper figures. Model weights remain frozen; inference and verification still incur API cost.

## 6. The decisive experiment

Start with MPBench payloads and benign records plus an explicitly synthetic provenance/policy overlay. Do not present synthetic identities as original annotations.

Each contributor must be able to supply benign and dangerous records. Use opaque IDs, equal initial trust, and roles that do not reveal attacker labels. Include authorized contributors whose shared memories can still be unsafe: if every attack is an unauthorized read, the access filter solves the task and trust adds no demonstrated value.

For the diagnostic:

1. Give methods identical memory, permissions, content detector, and initial state.
2. Reveal exactly the same confirmed incident to all methods.
3. Query other, uninspected records from that source and unrelated sources.
4. Measure future unsafe use and useful recall, especially benign records from the implicated source.
5. Repeat across independent episodes and contributor assignments. Include identity-shuffled controls and a regime where source identity contains no predictive information.

Compare at the same verification budget and matched useful recall:

- Original SAFE-Mem.
- SAFE-Mem plus the fixed detector, updating only the checked record.
- Naive user-wide penalties: our initial idea.
- Simple global and context-specific Beta reputation.
- Descendant-only provenance restriction.
- Selective propagation with incident deduplication and recovery.

For the eventual paper, add closely related mechanisms such as A-MemGuard's full lesson mechanism where valid. An incomplete proxy is not a full reproduction.

Stress tests: mixed contributors, compromise after benign history, duplicated incidents, false alarms and recovery, noisy/delayed feedback, innocent relays, permission changes, and bounded fresh-account attacks. Stable authenticated identity is an assumption; unlimited resets defeat source-history methods.

Measure attack-success and executed-action rates, legitimate answer accuracy/recall, false restrictions, recovery delay, and verification calls/tokens. Report chronological curves and uncertainty across episodes. Current OpenRouter smoke runs establish baseline operation; they do not test this contribution. Resolve the documented MINJA answer-extraction caveat before reporting MINJA task accuracy.

## 7. Honest ICML assessment

ICML's published criteria emphasize soundness, significance, originality, and presentation. They allow contributions through new insights and improved understanding of existing methods; a new trained model is not the requirement. See the [2026 reviewer instructions](https://icml.cc/Conferences/2026/ReviewerInstructions).

| Version | Assessment |
|---|---|
| Add user IDs and access labels; decrease every sibling's score after a flag | Feasible and useful as a baseline; a weak main-track novelty argument given prior overlaps. |
| Add source/context counters and claim dynamic trust is new | Still too incremental as stated. |
| Establish when evidence transfer helps or harms, and show a small selective rule improves the safety/utility/verification tradeoff | A more defensible research direction, conditional on results and prior-work comparisons. |

The recommended paper is a focused empirical methods study with a lightweight defense. The scientific work is isolating evidence transfer, exposing false-accusation amplification, and establishing its limits. Do not claim a new Bayesian estimator merely because the system uses Beta counts.

If a stronger statistical contribution becomes necessary, a sequential evidence threshold could replace an arbitrary escalation threshold without neural training. [Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240) are an existing foundation, not our invention. Guarantees would require explicit assumptions about audit selection, verifier error, repeated incidents, and changing source behavior. An ordinary Beta threshold is not an anytime-valid safety guarantee. This is optional later work, not a pilot prerequisite.

If selective propagation cannot beat simple global/context reputation at matched utility and cost, adding terminology or components will not make it stronger. Report the result and reconsider the contribution. Acceptance cannot be established from the proposal alone.

## 8. Revised contribution and next step

> We study training-free transfer of verified safety evidence across agent memories. A lightweight defense updates shared contributor state and selectively changes the treatment of related, uninspected records while preserving hard access boundaries. We evaluate whether it reduces future unsafe use per verification call without amplifying false accusations or discarding useful contributions from the same source.

The next step is a small MPBench sequential pilot with fixed feedback and the baselines above. Broader benchmarks, additional backbones, and formal analysis follow if the pilot supports the hypothesis. No new defense results are claimed here.
