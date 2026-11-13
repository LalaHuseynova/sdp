# Figure captions

Original SAFE-Mem: full-dataset reproduction

Table 1. Rates (%). Published SAFE-Mem results versus our reproduction; paper rates retain one decimal, reproduced rates use two. Metric denominators are shown above.
Bold: best available entry per column, including ties. -: unavailable; singleton bold entries do not establish superiority. Utility = combined benign memory-use score.
LoCoMo is a paper-only reference, not a reproduced result. All 244 write-only MPBench inputs remain in the pool; only reads are scored. Reproduction uses OpenRouter/current GPT-4o-mini.
Our proposed defense has NOT been evaluated on the full 6,240-case MPBench dataset.
Sources: SAFE-Mem v2, Table 1 and Sec. 5.1 (PDF p. 6); verified local final_results.json (28 October 2026).

Selective evidence propagation: preliminary subset evaluation

Table 2. Rates (%) on three provisional conditions. Each has 216 probe questions per method; metric denominators appear above. Utility = combined benign memory-use score, not general QA accuracy.
Bold: best per column including all ties and the no-memory control (zero retention). R/C/M/S receive identical B = 5 tickets per group (40 per condition); static/control receive none.
Feedback is AI-simulated and unverified; human validation is pending. Source-grounded QA is unvalidated/unscored. Distributed/Localized are strong case-intent overlays, not verified unsafe-memory regimes.
The same 256 inputs are reused; reserved audit cases and probe cohorts can differ. These are development results, not independent replications or a confirmed superiority finding.
Our proposed method has NOT been evaluated on the full 6,240-case MPBench dataset.
Source: verified frozen comparison.json, D00-D07 (1 November 2026). Only methods with saved pilot outcomes are shown; - denotes unavailable results.
