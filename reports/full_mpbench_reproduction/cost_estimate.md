# Full MPBench offline cost estimate

No paid calls were made to produce this estimate. Execution requires approval.

Each job writes all 6,240 cases; reads/scoring follow the original protocol. Every job is priced as cold-cache; shared-cache reuse may lower the total.

| Backbone | Method | Typical paid requests | Typical USD | Conservative planning USD |
|---|---|---:|---:|---:|
| 4omini | no_defence | 30,087 | $2.78 | $6.66 |
| 4omini | safe_mem | 45,570 | $4.40 | $16.51 |
| 4omini | a_memguard | 60,067 | $8.59 | $20.61 |
| 4omini | drift | 36,327 | $4.29 | $25.08 |
| 4omini | randec_distil | 30,087 | $2.78 | $6.66 |
| 4omini | llm_sanitiser | 57,669 | $5.76 | $21.10 |
| 4omini | memlineage_coarse | 36,083 | $2.95 | $7.09 |
| 4omini | integrity_gate_all | 30,087 | $2.78 | $6.66 |
| gpt56 | no_defence | 30,087 | $32.80 | $78.71 |
| gpt56 | safe_mem | 45,570 | $65.38 | $258.46 |
| gpt56 | a_memguard | 60,067 | $154.63 | $371.12 |
| gpt56 | drift | 36,327 | $64.24 | $563.93 |
| gpt56 | randec_distil | 30,087 | $32.80 | $78.71 |
| gpt56 | llm_sanitiser | 57,669 | $78.51 | $339.12 |
| gpt56 | memlineage_coarse | 36,083 | $35.29 | $84.52 |
| gpt56 | integrity_gate_all | 30,087 | $32.80 | $78.71 |
| haiku55 | no_defence | 30,087 | $2.49 | $5.98 |
| haiku55 | safe_mem | 45,570 | $3.73 | $13.44 |
| haiku55 | a_memguard | 60,067 | $7.36 | $17.67 |
| haiku55 | drift | 36,327 | $3.76 | $23.65 |
| haiku55 | randec_distil | 30,087 | $2.49 | $5.98 |
| haiku55 | llm_sanitiser | 57,669 | $4.62 | $17.13 |
| haiku55 | memlineage_coarse | 36,083 | $2.61 | $6.27 |
| haiku55 | integrity_gate_all | 30,087 | $2.49 | $5.98 |
| qwen38flash | no_defence | 30,087 | $2.84 | $6.81 |
| qwen38flash | safe_mem | 45,570 | $4.52 | $16.76 |
| qwen38flash | a_memguard | 60,067 | $8.91 | $21.37 |
| qwen38flash | drift | 36,327 | $4.42 | $26.62 |
| qwen38flash | randec_distil | 30,087 | $2.84 | $6.81 |
| qwen38flash | llm_sanitiser | 57,669 | $5.86 | $21.64 |
| qwen38flash | memlineage_coarse | 36,083 | $3.02 | $7.23 |
| qwen38flash | integrity_gate_all | 30,087 | $2.84 | $6.81 |

All jobs: approximately **$595.55 typical**, **$2173.81 conservative planning**; 1,303,908 typical logical paid requests before cache savings.

GPT-4o-mini Simple Memory + SAFE-Mem only: **$7.18 typical**, **$23.17 conservative planning**.

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
