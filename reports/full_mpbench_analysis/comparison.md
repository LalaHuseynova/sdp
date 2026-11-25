# Full MPBench reproduction comparison

ASR is answer endorsement/action on the attack target, not detector FNR. Recall measures explicit retention; Restraint measures avoidance of suggested user claims. Benign utility is correct/2856 scorable benign cases. Complete claim-level unsafe labels are unavailable, so detector FPR/FNR are not reported.

Each metric cell is published / reproduced / difference in percentage points. Pending or rejected runs have no reproduced score.

| Backbone | Method | Status | ASR | Recall | Restraint | Benign utility |
|---|---|---|---|---|---|---|
| GPT-5.6-terra | No defense | pending | 26.7 / — / — | 75.9 / — / — | 35.1 / — / — | — |
| GPT-5.6-terra | A-MemGuard | pending | 13.1 / — / — | 70.3 / — / — | 42.1 / — / — | — |
| GPT-5.6-terra | DRIFT | pending | 25.1 / — / — | 75.9 / — / — | 34.6 / — / — | — |
| GPT-5.6-terra | RandEC | pending | 21.8 / — / — | 70.7 / — / — | 36.9 / — / — | — |
| GPT-5.6-terra | LLM sanitizer | pending | 24.2 / — / — | 74.3 / — / — | 35.1 / — / — | — |
| GPT-5.6-terra | MemLineage | pending | 24.6 / — / — | 72.3 / — / — | 35.3 / — / — | — |
| GPT-5.6-terra | TMA-NM | pending | 2.7 / — / — | 9.6 / — / — | 94.7 / — / — | — |
| GPT-5.6-terra | SAFE-Mem | pending | 2.6 / — / — | 86.3 / — / — | 48.4 / — / — | — |
| GPT-4o-mini | No defense | pending | 49.8 / — / — | 79.5 / — / — | 36.5 / — / — | — |
| GPT-4o-mini | A-MemGuard | pending | 41.0 / — / — | 73.5 / — / — | 37.3 / — / — | — |
| GPT-4o-mini | DRIFT | pending | 40.4 / — / — | 81.5 / — / — | 36.1 / — / — | — |
| GPT-4o-mini | RandEC | pending | 27.3 / — / — | 72.3 / — / — | 39.4 / — / — | — |
| GPT-4o-mini | LLM sanitizer | pending | 48.2 / — / — | 79.5 / — / — | 36.4 / — / — | — |
| GPT-4o-mini | MemLineage | pending | 45.4 / — / — | 81.1 / — / — | 37.1 / — / — | — |
| GPT-4o-mini | TMA-NM | pending | 2.4 / — / — | 9.6 / — / — | 94.7 / — / — | — |
| GPT-4o-mini | SAFE-Mem | pending | 6.2 / — / — | 85.9 / — / — | 50.6 / — / — | — |
| Claude Haiku 5.5 | No defense | pending | 10.9 / — / — | 71.5 / — / — | 45.8 / — / — | — |
| Claude Haiku 5.5 | A-MemGuard | pending | 7.1 / — / — | 56.2 / — / — | 64.0 / — / — | — |
| Claude Haiku 5.5 | DRIFT | pending | 10.6 / — / — | 71.5 / — / — | 47.9 / — / — | — |
| Claude Haiku 5.5 | RandEC | pending | 10.6 / — / — | 68.7 / — / — | 47.5 / — / — | — |
| Claude Haiku 5.5 | LLM sanitizer | pending | 10.5 / — / — | 71.5 / — / — | 45.6 / — / — | — |
| Claude Haiku 5.5 | MemLineage | pending | 8.3 / — / — | 67.9 / — / — | 56.5 / — / — | — |
| Claude Haiku 5.5 | TMA-NM | pending | 0.5 / — / — | 2.4 / — / — | 98.4 / — / — | — |
| Claude Haiku 5.5 | SAFE-Mem | pending | 1.5 / — / — | 84.3 / — / — | 51.4 / — / — | — |
| Qwen3.8-Flash | No defense | pending | 41.1 / — / — | 78.3 / — / — | 35.5 / — / — | — |
| Qwen3.8-Flash | A-MemGuard | pending | 18.7 / — / — | 64.7 / — / — | 55.9 / — / — | — |
| Qwen3.8-Flash | DRIFT | pending | 26.5 / — / — | 71.9 / — / — | 39.1 / — / — | — |
| Qwen3.8-Flash | RandEC | pending | 28.5 / — / — | 73.1 / — / — | 37.7 / — / — | — |
| Qwen3.8-Flash | LLM sanitizer | pending | 32.8 / — / — | 79.1 / — / — | 36.1 / — / — | — |
| Qwen3.8-Flash | MemLineage | pending | 37.4 / — / — | 76.7 / — / — | 36.4 / — / — | — |
| Qwen3.8-Flash | TMA-NM | pending | 1.4 / — / — | 2.0 / — / — | 98.7 / — / — | — |
| Qwen3.8-Flash | SAFE-Mem | pending | 1.9 / — / — | 83.1 / — / — | 49.2 / — / — | — |

Bootstrap uses the original review_stats.asr_ci implementation with 2,000 resamples and seed 0. The current dataset has 2,891 distinct scored attack questions; the paper reports 2,893. Costs exclude local embeddings and cache hits; shared run-directory costs must not be summed repeatedly for methods from the same directory.
Rows marked full_validated_model_substitution are full-data experiments with declared model changes, not faithful same-model reproductions. Lexical judge fallback counts and affected IDs are retained in the JSON; original verdicts are never silently replaced.
