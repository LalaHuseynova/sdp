# Matched dynamic-defense comparison

Basis: **AI_exploratory**. Status: **complete_saved_outcomes**.

Metrics apply to the same declared questions within each regime. Verification feedback/resources are checked for R/C/M/S.

## strong_distributed

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 4/117 (3.42%) | 12/12 (100.00%) | 54/60 (90.00%) | 66/72 (91.67%) | N/A (0) | 0 | 0 | 0 |
| R | 4/117 (3.42%) | 12/12 (100.00%) | 54/60 (90.00%) | 66/72 (91.67%) | N/A (0) | 35 | 0 | 0 |
| C | 4/117 (3.42%) | 12/12 (100.00%) | 54/60 (90.00%) | 66/72 (91.67%) | N/A (0) | 35 | 0 | 0 |
| M | 4/117 (3.42%) | 12/12 (100.00%) | 54/60 (90.00%) | 66/72 (91.67%) | N/A (0) | 35 | 0 | 0 |
| S | 4/117 (3.42%) | 12/12 (100.00%) | 54/60 (90.00%) | 66/72 (91.67%) | N/A (0) | 35 | 0 | 0 |
| no_memory | 0/117 (0.00%) | 0/12 (0.00%) | 59/60 (98.33%) | 59/72 (81.94%) | N/A (0) | 0 | 0 | 0 |

## strong_localized

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 5/115 (4.35%) | 11/11 (100.00%) | 56/63 (88.89%) | 67/74 (90.54%) | N/A (0) | 0 | 0 | 0 |
| R | 5/115 (4.35%) | 11/11 (100.00%) | 56/63 (88.89%) | 67/74 (90.54%) | N/A (0) | 35 | 0 | 0 |
| C | 5/115 (4.35%) | 11/11 (100.00%) | 55/63 (87.30%) | 66/74 (89.19%) | N/A (0) | 35 | 0 | 0 |
| M | 5/115 (4.35%) | 11/11 (100.00%) | 55/63 (87.30%) | 66/74 (89.19%) | N/A (0) | 35 | 0 | 0 |
| S | 5/115 (4.35%) | 11/11 (100.00%) | 55/63 (87.30%) | 66/74 (89.19%) | N/A (0) | 35 | 0 | 0 |
| no_memory | 0/115 (0.00%) | 0/11 (0.00%) | 62/63 (98.41%) | 62/74 (83.78%) | N/A (0) | 0 | 0 | 0 |

## uninformative

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audits | Refusals | Missing/errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| static | 6/122 (4.92%) | 11/11 (100.00%) | 51/56 (91.07%) | 62/67 (92.54%) | N/A (0) | 0 | 0 | 0 |
| R | 6/122 (4.92%) | 11/11 (100.00%) | 51/56 (91.07%) | 62/67 (92.54%) | N/A (0) | 35 | 0 | 0 |
| C | 6/122 (4.92%) | 11/11 (100.00%) | 50/56 (89.29%) | 61/67 (91.04%) | N/A (0) | 35 | 0 | 0 |
| M | 6/122 (4.92%) | 11/11 (100.00%) | 50/56 (89.29%) | 61/67 (91.04%) | N/A (0) | 35 | 0 | 0 |
| S | 6/122 (4.92%) | 11/11 (100.00%) | 50/56 (89.29%) | 61/67 (91.04%) | N/A (0) | 35 | 0 | 0 |
| no_memory | 0/122 (0.00%) | 0/11 (0.00%) | 55/56 (98.21%) | 55/67 (82.09%) | N/A (0) | 0 | 0 | 0 |

An omitted/failed/unjudged outcome keeps its fixed denominator and withholds the exact rate; JSON includes missing-outcome bounds.

Attributable ASR uses paired method/no-memory outcomes, not subtraction of aggregate rates. Refusals retain their utility costs.

A single base group has no bootstrap interval. Repeated regimes are not independent samples; intervals are exploratory and not multiplicity-adjusted.

Point utility margins are diagnostics, not established noninferiority. No general task-accuracy or detector FPR/FNR claim is made.

Feedback: saved_AI_proposals_as_simulated_feedback_not_verified_ground_truth
