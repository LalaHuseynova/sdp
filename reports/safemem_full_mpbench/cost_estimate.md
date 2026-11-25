# Full MPBench offline cost estimate

No paid calls were made to produce this estimate. Execution requires approval.

Each job writes all 6,240 cases; reads/scoring follow the original protocol. Every job is priced as cold-cache; shared-cache reuse may lower the total.

| Backbone | Method | Typical paid requests | Typical USD | Conservative planning USD |
|---|---|---:|---:|---:|
| 4omini | safe_mem | 45,570 | $4.40 | $16.51 |

All jobs: approximately **$4.40 typical**, **$16.51 conservative planning**; 45,570 typical logical paid requests before cache savings.

Included GPT-4o-mini core-method jobs (4omini/safe_mem): **$4.40 typical**, **$16.51 conservative planning**.

## Assumptions and practical limits

- All jobs are planned cold-cache; no discount for existing cache, cross-method extraction, repeated judges, or cross-backbone judge reuse.
- Existing 80-case GPT-4o-mini usage calibrates extraction/answer/judge lengths only; this selected repetition-only smoke workload is not a representative sample.
- Typical read prompts have a 20% input/output allowance. Other-backbone output allowances are 1.5 for GPT-5.6, 1.25 for Claude, and 1.4 for Qwen; these are not measurements.
- Typical SAFE-Mem workload assumes 0.5 conflict checks/read and one extra extraction pass per labeled retention request; actual model outputs may differ.
- Unrun baseline assumptions per call: AMG chain 600 input/160 output tokens, audit 1100/100; sanitizer 650/8 with 15% rewrites at 550/110; DRIFT >=900/180.
- Conservative scenario doubles assumed input/output lengths. SAFE-Mem uses two extraction passes and up to six conflict checks/read; sanitizer rewrites all candidates; DRIFT uses two calls/write and 800-token replies before doubling.
- Conservative total adds a 20% incidental/pricing reserve. It is a planning scenario, not a statistical interval, hard dollar cap, or worst-case token bound.
- DRIFT permits 10,000 output tokens/call and AMG permits 2,048. Use near those caps could exceed this scenario. Reasoning must remain disabled as configured.
- Local embeddings cost zero API dollars and are excluded from paid chat counts. Cached operations cost zero new API dollars but appear in original ledger totals.
- Successful logical requests exclude SDK/managed retries, provider cache rates, taxes, credit fees, or unexpected surcharges. Prices are saved public catalog rates.

The conservative figure is not a guaranteed spending ceiling. A separately enforced execution budget is needed for a hard limit. This estimate grants no execution approval.
