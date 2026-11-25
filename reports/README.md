# Report guide

Reviewed 7 November 2026. The [project README](../README.md) is the current overview. Reports in this directory retain the date and scope of the work they describe. An old “not implemented yet” statement is historical, not a claim that the later implementation is missing.

## Aim and experimental design

- [Research proposal](RESEARCH_PROPOSAL.md): why contributor reputation alone is insufficient and why we study propagation scope.
- [Implementation roadmap](DEFENSE_IMPLEMENTATION_PLAN.md): original code audit, design choices and research risks.
- [Primary protocol](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md): planned independently annotated mechanism study, fixed budgets and scientific decision criteria. It is not an executed preregistration.
- [Provisional design](PROVISIONAL_20261029_DESIGN.md): separate case-intent preparation before genuine human labels.
- [AI-feedback exploratory protocol](LLM_EXPLORATORY_PROTOCOL_20261031.md): automated reviews remain proposals, not human ground truth.

## What actually completed

- [Original SAFE-Mem reproduction](safemem_full_mpbench/RUN_REPORT.md): full source pool, paper comparison, deviations, outcomes and accounting.
- [Memory recovery](RECOVERY_20261029_REPORT.md): what was recovered/reconstructed and the historical verification limits.
- [Preliminary defense results](PROVISIONAL_RESULTS_20261101_REPORT.md): executed development comparison, denominators, attribution/admission diagnostics and limitations.
- [Attack-carrier diagnostic, 7 Nov](ATTACK_CARRIER_DIAGNOSTIC_20261107_REPORT.md): which records carried the 15 attack successes and why S changed only 23 contexts; concludes the null result is mainly a workload problem.
- [Propagation feasibility, 8 Nov](PROPAGATION_FEASIBILITY_20261108_REPORT.md): only 102/3,241 MPBench attacks are reachable by propagation (23 attributable now); MPBench alone cannot power the S vs R/C/M test, so a controlled workload is needed.
- [Controlled workload v1 specification, 8 Nov](CONTROLLED_WORKLOAD_20261108_SPEC.md): MPBench-derived propagation workload, ASR and utility metrics, hypotheses, power, free vs paid stages and the GPT-4o-mini cost estimate. Generated offline; not yet run.
- [Controlled workload integration, 8 Nov](CONTROLLED_WORKLOAD_INTEGRATION_20261108_REPORT.md): offline end-to-end integration with SAFE-Mem and R/C/M/S, mock dry run, bugs fixed, and an exact Stage-1 request audit (528 paid requests, about $0.09).
- [Controlled workload Stage 1/2, 8 Nov](CONTROLLED_WORKLOAD_STAGE1_STAGE2_20261108_REPORT.md): paid dev Stage 1 halted safely after 3/8 groups ($0.0325 settled, one unknown attempt held); Stage 2 confirms the attack mechanics but finds that inserted utility facts rarely reach the context (10/75) under frozen `external_evidence=false`; strict utility metric; recommendations.
- [Controlled workload v2 carriers, 8 Nov](CONTROLLED_WORKLOAD_V2_FACT_CARRIERS_20261108_REPORT.md): fact-centred utility notes (data-only fix), byte-identical attacks, overlays, audits, probes and split; 648 tests; mock dry run; tiny extraction pilot prepared (expected $0.006, cap $0.03), not run.
- [Controlled workload v3 pilots/Stage 1/Stage 2, 8 Nov](CONTROLLED_WORKLOAD_V3_PILOTS_STAGE1_STAGE2_20261108_REPORT.md): v2 pilot failed (10/18), v3 durable carriers passed (16/18); real v3 dev stores: facts in context 185/200, S keeps the localized key stratum 51/56 vs C/M 0/56; $0.0651 spent.
- [Dev Stage 3, 8 Nov](CONTROLLED_WORKLOAD_DEV_STAGE3_20261108_REPORT.md): real answers and judges; localized: original SAFE-Mem 72% ASR, C/M 0% ASR but key utility 0/56, S 0% ASR with key utility 51/56; H1 and H2 supported, H3 not (dev only); $0.14.
- [Final dataset audit and freeze, 8 Nov](WORKLOAD_AUDIT_FREEZE_20261108_REPORT.md): workload v4 (fragment relays and near-duplicate payloads fixed; no leakage), frozen protocol `921cf7f5…`, test verified untouched, locked-test cost $0.618 ($0.742 with allowance).
- [Locked held-out test, 8 Nov](LOCKED_TEST_V4_20261108_REPORT.md): frozen v4, 24 groups. Original SAFE-Mem 77% ASR; localized S 0% ASR with original-level utility vs C/M key utility 0/168. H1 and H2 supported, H3 not. $0.578.
- [Full comparison table](../research_data/development_comparison_report_v1_20261101/RESULTS.md): static, R/C/M/S and no-memory outcomes across three conditions.
- [1 November audit](RESEARCH_AUDIT_20261101_REPORT.md): previous test and saved-artifact review.
- [7 November repository review](REPOSITORY_REVIEW_20261107.md): refreshed checks, documentation corrections and conservative cleanup.

The selective method did not improve ASR in the preliminary comparison. It has not run on full MPBench. Successful preparation or mechanics tests do not change either fact.

## Human review still pending

- [Review guide](PROVISIONAL_20261029_GUIDE.md).
- [Focused question-review guide](FOCUSED_REVIEW_WORKFLOW_20261101_GUIDE.md).
- [Failed AI question-adjudication round](AI_PILOT_ADJUDICATION_20261101_REPORT.md): retained so failed controls cannot be hidden or called validation.

Two independent reviewers and disagreement adjudication are still needed under our protocol. The currently recorded human-verified safety and validated utility-question counts are zero.

## Files that look repetitive

Different dates, prefixes, refreshed provider receipts, failed gate checks and interrupted runs describe different states. They are retained as evidence. Several frozen bundles intentionally include identical configuration or input snapshots. Deleting those snapshots would break integrity checks or make a bundle incomplete.

`full_mpbench_reproduction/` includes earlier preparation material; `safemem_full_mpbench/` is the scope-specific completed Original SAFE-Mem report set. Neither folder is a second copy of the other. Test totals from overlapping reports must not be added together.

Use the indexes rather than flattening these files into one directory or rewriting old reports to match the current status. No original report, experiment output, review form or budget journal was deleted in the 7 November cleanup.
