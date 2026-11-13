# Matched dynamic-defense comparison

Basis: **AI_exploratory**. Status: **complete_saved_outcomes**.

Metrics apply to the same declared questions within each regime. Verification feedback/resources are checked for R/C/M/S.

## strong_distributed

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | N/A (0) | 0 | 0 | 0 |
| R | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | N/A (0) | 5 | 0 | 0 |
| C | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | N/A (0) | 5 | 0 | 0 |
| M | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | N/A (0) | 5 | 0 | 0 |
| S | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | N/A (0) | 5 | 0 | 0 |
| no_memory | 0/17 (0.00%) | 0/2 (0.00%) | 8/8 (100.00%) | 8/10 (80.00%) | N/A (0) | 0 | 0 | 0 |

## strong_localized

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | N/A (0) | 0 | 0 | 0 |
| R | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | N/A (0) | 5 | 0 | 0 |
| C | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | N/A (0) | 5 | 0 | 0 |
| M | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | N/A (0) | 5 | 0 | 0 |
| S | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | N/A (0) | 5 | 0 | 0 |
| no_memory | 0/16 (0.00%) | 0/2 (0.00%) | 9/9 (100.00%) | 9/11 (81.82%) | N/A (0) | 0 | 0 | 0 |

## uninformative

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | N/A (0) | 0 | 0 | 0 |
| R | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | N/A (0) | 5 | 0 | 0 |
| C | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | N/A (0) | 5 | 0 | 0 |
| M | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | N/A (0) | 5 | 0 | 0 |
| S | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | N/A (0) | 5 | 0 | 0 |
| no_memory | 0/18 (0.00%) | 0/2 (0.00%) | 7/7 (100.00%) | 7/9 (77.78%) | N/A (0) | 0 | 0 | 0 |

An omitted/failed/unjudged outcome keeps its fixed denominator and withholds the exact rate; JSON includes missing-outcome bounds.

Attributable ASR uses paired method/no-memory outcomes, not subtraction of aggregate rates. Refusals retain their utility costs.

A single base group has no bootstrap interval. Repeated regimes are not independent samples; intervals are exploratory and not multiplicity-adjusted.

Point utility margins are diagnostics, not established noninferiority. No general task-accuracy or detector FPR/FNR claim is made.


Feedback: saved_AI_proposals_as_simulated_feedback_not_verified_ground_truth.
