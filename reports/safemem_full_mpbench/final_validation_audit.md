# Independent full-MPBench SAFE-Mem audit

Status: **passed_with_documented_caveats**. Audited 2026-10-28T14:35:14.927374+00:00. No API calls or source/result modifications.

32 independent checks passed; failed checks: [].

## Exact coverage

The completed run has **6,240 unique ingestions into pool0**, including all **244 write-only cases**, and **5,996 unique readable outcomes**: 2,999 attacks and 2,997 benign cases. The 141 readable benign cases without annotated expected memory remain in the outcomes and are excluded from benign accuracy.

Journal and CSV values agree across every field. Each outcome’s written memories match its own ingestion. Original IDs, questions, labels, attack categories, the complete shared pool, and seed-0 ingestion order are preserved.

## Metrics

| Measure | Successful/correct cases | Reproduced | Published | Difference (pp) |
|---|---:|---:|---:|---:|
| Attack success | 176/2999 | 5.8686% | 6.2% | -0.3314 |
| Retention recall | 213/249 | 85.5422% | 85.9% | -0.3578 |
| Restraint | 1273/2607 | 48.8301% | 50.6% | -1.7699 |
| Benign utility | 1486/2856 | 52.0308% | not printed | — |

Independent bootstrap with 2,000 resamples and seed 0 gives **5.0–6.7%** for both the case and query-clustered ASR intervals. The paper’s query-clustered interval is **5.4–7.1%**. The current official dataset has 2,891 distinct scored attack questions; the paper reports 2,893. No questions were changed to force agreement.

## Fidelity and saved-output checks

All **67 original method, prompt, baseline, and source-configuration files** and all **147 frozen source fingerprints** match. Both official dataset hashes match. Models, settings, and used prompts match the frozen plan.

**All 14,216 original judge requests were replayed from cached responses with zero missing responses, verdict mismatches, or lexical fallbacks.** This verifies saved judgments against the actual saved answers, including the answer variants described below.

All 8,995 answer/control requests have cache entries. However, **23 saved responses differ from the final cached winner**: 15 with-memory answers and 8 no-memory controls. They occur across **21 shared request keys**, covering 67 requests in total. Every cached winning text appears among the completed cases sharing that key. This is consistent with the original cache allowing concurrent misses and retaining one winner; causation is not independently proven. The journal and CSV preserve the actual answers, but the final response cache alone does not establish byte-identical replay for those 23 responses.

**22 saved with-memory answers match cached responses with a `length` finish** under the original 200-token cap. The original finish reasons of the 23 differing saved responses are unavailable and remain unknown. This is a cache-based diagnostic, not a complete distribution of original finish reasons. Exact IDs, request keys, response kinds, and qualified finish reasons are listed in the JSON audit. No outputs were repaired or regenerated.

## Costs and scope

The completed attempt’s ledger records 29,939 uncached OpenRouter operations and $2.5887795 in usage cost. Across both attempts, the persistent guard records **$3.9186663 in provider-reported settled charges** and **$0.371352 in retained unresolved reservations**, totaling **$4.2900183** against the unchanged $27 software allowance. **Zero missing-billing estimates were accepted as settlements.** Provider-reported usage charges are not an independently reconciled invoice.

This validates **one original SAFE-Mem/GPT-4o-mini full-MPBench row**. Simple Memory, other defenses, other backbones, and other paper experiments were not run under this approval. The `no_defence` outcome label denotes the extra post-retrieval filter setting; the memory system is the original typed-standing SAFE-Mem system.

Published values are rounded. The ASR confidence intervals overlap, so no superiority claim is established. Complete claim-level detector labels are unavailable; ASR and benign utility must not be relabeled as detector FNR/FPR or classification accuracy.
