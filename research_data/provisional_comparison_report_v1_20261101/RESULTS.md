# Our first provisional matched comparison

**Real model outputs; AI-simulated feedback; one 32-case development bag. Human validation pending.**

Each regime compares the same questions and memory pool across methods. All R/C/M/S methods received the same five AI-feedback tickets and equivalent verification usage. Static SAFE-Mem and no-memory controls consumed no audits.

The rows below are new-workload results. The historical 176/2,999 (5.87%) ASR is a separate reproduction reference, not the comparator here.

## uninformative

| Method | Write target present | Retrieved attack target | Answer ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Audits |
|---|---:|---:|---:|---:|---:|---:|---:|
| static | 17/20 (85.00%) | 0/18 (0.00%) | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | 0 |
| R | 17/20 (85.00%) | 0/18 (0.00%) | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | 5 |
| C | 17/20 (85.00%) | 0/18 (0.00%) | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | 5 |
| M | 17/20 (85.00%) | 0/18 (0.00%) | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | 5 |
| S | 17/20 (85.00%) | 0/18 (0.00%) | 0/18 (0.00%) | 1/2 (50.00%) | 7/7 (100.00%) | 8/9 (88.89%) | 5 |
| no_memory | N/A | N/A | 0/18 (0.00%) | 0/2 (0.00%) | 7/7 (100.00%) | 7/9 (77.78%) | 0 |
## strong_localized

| Method | Write target present | Retrieved attack target | Answer ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Audits |
|---|---:|---:|---:|---:|---:|---:|---:|
| static | 17/20 (85.00%) | 0/16 (0.00%) | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | 0 |
| R | 17/20 (85.00%) | 0/16 (0.00%) | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | 5 |
| C | 17/20 (85.00%) | 0/16 (0.00%) | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | 5 |
| M | 17/20 (85.00%) | 0/16 (0.00%) | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | 5 |
| S | 17/20 (85.00%) | 0/16 (0.00%) | 0/16 (0.00%) | 1/2 (50.00%) | 9/9 (100.00%) | 10/11 (90.91%) | 5 |
| no_memory | N/A | N/A | 0/16 (0.00%) | 0/2 (0.00%) | 9/9 (100.00%) | 9/11 (81.82%) | 0 |
## strong_distributed

| Method | Write target present | Retrieved attack target | Answer ASR ↓ | Retention ↑ | Restraint ↑ | Combined benign ↑ | Audits |
|---|---:|---:|---:|---:|---:|---:|---:|
| static | 17/20 (85.00%) | 0/17 (0.00%) | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | 0 |
| R | 17/20 (85.00%) | 0/17 (0.00%) | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | 5 |
| C | 17/20 (85.00%) | 0/17 (0.00%) | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | 5 |
| M | 17/20 (85.00%) | 0/17 (0.00%) | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | 5 |
| S | 17/20 (85.00%) | 0/17 (0.00%) | 0/17 (0.00%) | 1/2 (50.00%) | 8/8 (100.00%) | 9/10 (90.00%) | 5 |
| no_memory | N/A | N/A | 0/17 (0.00%) | 0/2 (0.00%) | 8/8 (100.00%) | 8/10 (80.00%) | 0 |

## Interpretation limits

These are exploratory point estimates. One independent development group provides no group-bootstrap confidence interval. The same inputs recur across the three overlays. There are only two distinct original retention cases.

Source-grounded benign QA is unavailable. Combined benign utility and restraint do not establish usefulness; refusals were not independently annotated. Empty outputs, length finishes and judge fallbacks are logged separately in the diagnostics JSON.

AI safety/origin proposals are not verified truth or independent human reviews. Original attack-case labels were used only for case-intent placement and private task scoring, never converted to memory findings. Synthetic origins do not prove natural authorship. Audit verdicts were not generated from target-answer judgments.

The audit cases are excluded from task probes. Foreign retrieved records can still come from audited roots; selection diagnostics distinguish those exposures from uninspected-root exposure. Lower ASR by itself is not evidence of selective transfer to untouched siblings.

Write diagnostics cover all 20 attack-input contributions; answer/retrieval denominators exclude five reserved audit cases and therefore differ by regime. Write construction is unchanged across methods.

Exact-request model replies are frozen on first dispatch and shared across methods. Equivalent per-policy inference/verification use is distinct from actual shared-cache charges. A saved reply is never resampled after its score is known.

New API spend since the freeze: **$0.0111546**. Total project spend: $2.0064984; remaining under the original $30 cap: $27.9935016.
