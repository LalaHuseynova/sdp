## Protocol v2 dry-run cost and runtime estimate (step 1.12; free, no paid call)

Measured on 4 dev groups (free precompute), scaled to 96 held-out groups. Per-call costs are the actual USD of completed dev calls. **Low** = measured counts; **high** = upper bound for methods that cannot be measured free (each published filter, "+R" variant and S2-ID gives a new prompt for every distinct context of the retrieval it filters).

| Stage | Purpose | Low | High |
|---|---|---|---|
| 3.1 generation (Claude Sonnet) | v2_generation | $22.76 | $29.05 |
| 3.3 inclusion E2 + I1 | v2_inclusion | $0.50 | $1.00 |
| 3.5 Stage 1 memory, 96 groups | v2_stage1 | $1.13 | $2.26 |
| 4.2+4.3 answers, judges, conflicts | v2_stage3 | $9.22 | $18.42 |
| 4.3 A-MemGuard own calls | v2_published_amemguard | $3.78 | $8.21 |
| 4.3 LLM sanitiser own calls | v2_published_sanitiser | $0.47 | $1.02 |
| 4.3 MemLineage SensitiveAction | v2_published_memlineage | $0.06 | $0.06 |
| 4.4 replication (24 groups, Table 1 + hypothesis cells): answers, judges | v2_stage3 | $1.08 | $2.72 |
| 4.4 replication: A-MemGuard own calls | v2_published_amemguard | $0.95 | $2.05 |
| 4.4 replication: LLM sanitiser own calls | v2_published_sanitiser | $0.12 | $0.25 |
| 4.4 replication: MemLineage SensitiveAction | v2_published_memlineage | $0.01 | $0.01 |
| 4.5 Haiku answers | v2_backbone_answer | $2.59 | $14.06 |
| 4.5 GPT judges of Haiku answers | v2_stage3 | $0.59 | $1.49 |
| 6.2 ablations, option A (current cells) | v2_stage3 | $0.26 | $1.05 |
| **Total** | | **$43.52** | **$81.65** |

**Pending-scope variants** (change in cost if chosen):

- 4.4 replication on every cell instead: $1.22 to $1.89
- 6.2 ablations option B instead of A: $0.74 to $2.97
- 3.1 with Claude Haiku as generator instead: −$21.63 to −$27.60
- 3.1 hard bound (every call uses max_tokens; the cap stops it first): $101.83

**Scope scenarios** (every paid stage, with generation where it applies; ablations option A):

| Scenario | Low | High | Within allowance? |
|---|---|---|---|
| A. full plan: 96 generated groups + MPBench v4 replication | $43.52 | $81.65 | no |
| B. MPBench only: v4 split (24 groups) is the main result | $4.44 | $11.86 | yes |
| C. MPBench v4 main + 32 generated groups (every cell) | $17.08 | $31.87 | only at low |

**Proposed caps per scenario** (high × 1.3, rounded up; ✗ = above the code ceiling in `transport.V2_PURPOSES`):

- A. full plan: generation $38.00 ✗, inclusion $1.50, stage1 $3.00, stage3 $31.00, published_amemguard $14.00, published_sanitiser $2.00, published_memlineage $0.10, backbone_answer $19.00 ✗; **sum $108.60**
- B. MPBench only: stage3 $8.00, published_amemguard $3.00, published_sanitiser $0.35, published_memlineage $0.05, backbone_answer $5.00; **sum $16.40**
- C. MPBench v4 main + 32 generated groups (every cell): stage3 $16.00, published_amemguard $6.50, published_sanitiser $0.80, published_memlineage $0.05, backbone_answer $5.00, generation $13.00 ✗, inclusion $0.45, stage1 $1.00; **sum $42.80**

**Protocol §11 option (b)** (4.2+4.3 incl. published defences' calls): full 96 groups $13.53–$27.70; every cell on 32 groups + Table 1/hypothesis cells on the other 64: $10.26–$22.67.

**By paid purpose** (proposed cap = high × 1.3, rounded up; each cap needs its own owner approval):

| Purpose | Low | High | Proposed cap | Code ceiling | Fits |
|---|---|---|---|---|---|
| v2_generation | $22.76 | $29.05 | $38.00 | $10.00 | **no** |
| v2_inclusion | $0.50 | $1.00 | $1.50 | $5.00 | yes |
| v2_stage1 | $1.13 | $2.26 | $3.00 | $5.00 | yes |
| v2_stage3 | $11.16 | $23.68 | $31.00 | $80.00 | yes |
| v2_published_amemguard | $4.73 | $10.26 | $14.00 | $20.00 | yes |
| v2_published_sanitiser | $0.58 | $1.27 | $2.00 | $10.00 | yes |
| v2_published_memlineage | $0.07 | $0.07 | $0.10 | $0.50 | yes |
| v2_backbone_answer | $2.59 | $14.06 | $19.00 | $10.00 | **no** |

Sum of proposed caps: $108.60. Remaining research allowance: about $26.57.

**Per group (measured mean):** 631 distinct answer prompts, 297 judged, 3 distinct conflict checks; the unmeasured methods add at most 630 prompts. Original SAFE-Mem's retrieval varies across conditions for 0 of 140 measured probes (35 distinct contexts per group).

**Runtime** (the paid 4.2+4.3 stage is ONE process that recomputes retrieval, then sends calls one at a time):

- CPU per group: internal methods 2.00 h; published methods' retrieval 2.23 h; RandEC 9.78 h in every condition, 0.04 h cached (fix 1);
- API: 1,342–2,721 calls per group at 1.0–2.08 s per call = 0.37–1.57 h per group; rate-limit delay: none observed in 11,785 dev calls;

| Groups | Current code | Fix 1 (RandEC cache) | Fixes 1 + 2 (three steps) |
|---|---|---|---|
| 96 | 57.5–62.3 days | 18.6–23.3 days | 102–217 h |
| 24 | 14.4–15.6 days | 4.6–5.8 days | 25–54 h |
| 32 | 19.2–20.8 days | 6.2–7.8 days | 34–72 h |

Free precompute CPU (1,131 h current; 384 h for steps 1 + 2 of fix 2), parallel across groups.
