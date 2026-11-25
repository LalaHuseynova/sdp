# First step: define the controlled provenance-transfer experiment

**Updated concrete design:** [MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md) supersedes this preliminary sketch, including the contributor layout and verification schedule.

Status: proposed protocol only. No dataset changes, defense implementation, experiments, or API calls have been made for this step.

## The question we will test

**After one confirmed dangerous memory, can we reduce unsafe use of other memories from that contributor without losing their useful memories?**

The experiment must distinguish the benefit of provenance from simply blocking more records or making extra verification calls.

## Small starting workload

Use existing MPBench payloads with an explicitly synthetic contributor overlay. Keep the official dataset files unchanged.

- Target 20 pilot episodes, with four contributors and eight readable, annotated source cases per contributor: 32 cases per episode.
- Use at least two task contexts. Include dangerous and benign contributions from the same contributor, plus unrelated contributors and unrelated attacks.
- Include both explicit-retention and suggestive benign cases.
- Use separate development/test groups. Validate that the proposed sampling is feasible before freezing the case list; these sizes are a planning target, not a statistical power claim.
- This is a small mechanism test. The complete 6,240-record evaluation follows later if it supports the hypothesis.

## Metadata we need first

Prepare a separate JSONL mapping with these minimum fields:

| Field | Purpose |
|---|---|
| record_id | Opaque identifier such as m_001; no attack/benign prefix visible to the defense. |
| original_case_key | Link to the original MPBench case; evaluator-only if the key reveals labels. |
| contributor_id | Authenticated origin assigned by the experimental harness, such as u_01. |
| artifact_id | Unique original contribution, shared by its extracted claims and copies. |
| context_id | Predefined task context, such as email or calendar. |
| allowed_readers | Explicit permission to read the record. |
| event_order | When the record, query, or audit becomes available. |

Keep original attack labels and expected target memories in the evaluator, outside the defense input.

For this first diagnostic, all selected contributions are authorized and readable by the task principal. That isolates trust propagation from permission blocking. Every contributor starts with the same prior and zero initial reputation penalty. Keep the existing task principal separate from the synthetic contributor identity. Attribute external contributions only when their origin is explicit; do not blame an innocent uploader or relabel principal-authored preferences as another user's statements.

## What happens in each episode

1. Give every method the same initial memories, identities, permissions and state.
2. Reveal exactly one confirmed unsafe incident, with its attributable source, to every method at the same point. Count one audit for each method. This is controlled oracle feedback, not a claim that an autonomous detector has solved verification.
3. Query other records that have not been audited: unsafe siblings, benign siblings in the same context, benign siblings in another context, and unrelated controls.
4. Save the selected memories, answers, judgments and state changes in order. Hidden evaluation labels never update trust automatically.
5. Repeat with different groups and with source/history associations broken as a negative control. Consistent renaming of IDs is not sufficient to break those associations.

Containment of the already revealed incident does not count as evidence of transfer. The primary targets are the other, uninspected records.

## Comparisons

| Method | Response to the revealed incident |
|---|---|
| Static SAFE-Mem with the same permissions | Records the audit for accounting; no added incident-driven behavior. |
| Record-only defense | Withholds the confirmed unsafe record/use; leaves siblings unchanged. |
| Blanket contributor penalty | Penalizes all records from that contributor. |
| Simple context reputation | Updates contributor/context evidence counts and applies a fixed reputation rule. |
| Selective propagation | Contains the unsafe use and applies weaker treatment to more distant siblings, preserving separately verified benign evidence. |

Use identical feedback and verification budgets. Disable new content screening uniformly in the simplest diagnostic, or use exactly the same frozen checker for all arms. Development-selected thresholds must be frozen before the test comparison. If selective propagation is indistinguishable from simple context reputation, it has not established an additional contribution.

## What would justify continuing

Measure future sibling ASR, retention recall, restraint, benign utility from the implicated contributor, unrelated-source effects, and audit/API cost. Report raw counts and uncertainty; this small pilot may contain too few successful attacks for a precise ASR estimate.

Continue only if selective propagation shows a useful safety/utility tradeoff beyond record-only filtering and simple reputation, under matched evidence and cost. Lower ASR obtained solely by discarding useful memories is insufficient. Follow a positive pilot with false-accusation/recovery tests, realistic imperfect verification, and a full-data evaluation.

## First implementation task after this protocol

**Create and validate the provenance JSONL mapping before implementing trust updates.** Check unique IDs, contributor/artifact attribution, mixed benign/unsafe contributors, permissions, event ordering, and separation of hidden labels. That work can be done offline. Do not start paid inference while preparing it.

Full context: [DEFENSE_IMPLEMENTATION_PLAN.md](DEFENSE_IMPLEMENTATION_PLAN.md), especially Sections 5, 8, and 9.
