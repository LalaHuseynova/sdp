# Dynamic-defense comparison: current status

The original SAFE-Mem reproduction is complete. The dynamic-method comparison has no measured outcomes yet.

## Historical full-MPBench reference

| Metric | Saved count | Historical result |
|---|---:|---:|
| asr | 176/2999 | 5.87% |
| retention_recall | 213/249 | 85.54% |
| restraint | 1273/2607 | 48.83% |
| combined_benign_utility | 1486/2856 | 52.03% |

These historical values are a separate reference. Static SAFE-Mem must be rerun in the new workload for a causal comparison.

## New matched comparison — all values pending

| Method | ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Source QA ↑ | Audit budget |
|---|---:|---:|---:|---:|---:|---:|
| static | Pending | Pending | Pending | Pending | Pending | 0 |
| R | Pending | Pending | Pending | Pending | Pending | 5 shared tickets |
| C | Pending | Pending | Pending | Pending | Pending | 5 shared tickets |
| M | Pending | Pending | Pending | Pending | Pending | 5 shared tickets |
| S | Pending | Pending | Pending | Pending | Pending | 5 shared tickets |
| no_memory | Pending | Pending | Pending | Pending | Pending | 0 |

R/C/M/S receive identical revealed feedback and equivalent verification resources. Static and no-memory are diagnostic references.

Current blocking strata:

- file_and_doc, explicit_benign: shortfall 1.

No failed reviewer, pending label, historical cache answer or invented test result is promoted into the new table.

Next gates: qualified data review; frozen cohort; native-store/provenance validation; checked and costed execution manifest; matched answering/judging; analysis.
