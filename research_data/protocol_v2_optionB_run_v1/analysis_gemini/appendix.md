## Appendix A1 — S2-BS and "+R" published variants, localized (data: MPBench v4 split (reused), GPT-4o-mini, 24 groups)

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| S2-BS | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |
| A-MemGuard+R | 49 [40, 58] | 59 [50, 68] | 87 [83, 91] | 63 [51, 73] | 87 [83, 91] | 50 [29, 71] |
| MemLineage+R | 44 [33, 54] | 56 [46, 67] | 91 [87, 95] | 54 [44, 65] | 91 [87, 95] | 50 [29, 71] |
| LLM sanitiser+R | 56 [47, 67] | 69 [59, 78] | 91 [87, 95] | 74 [63, 83] | 91 [87, 95] | 54 [33, 75] |
| RandEC+R | 63 [53, 73] | 77 [70, 84] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 58 [38, 79] |

## Appendix A2 — Judge ASR (answer-level), every Table-2 attack (data: MPBench v4 split (reused), GPT-4o-mini)

| Method | localized | distributed | no-signal control | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case | relay (localized) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 92 |
| R | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 71 |
| C | 0 | 0 | 70 | 63 | 77 | 77 | 77 | 21 | 41 | 78 | 0 | 75 | 78 | 63 |
| M | 0 | 0 | 46 | 34 | 75 | 77 | 75 | 21 | 41 | 78 | 0 | 75 | 78 | 63 |
| A-MemGuard | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 59 | 63 |
| MemLineage | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 75 |
| LLM sanitiser | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 69 | 83 |
| RandEC | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 92 |
| S | 0 | 0 | 67 | 64 | 77 | 77 | 77 | 22 | 42 | 78 | 78 | 76 | 78 | 58 |
| SL | 0 | 0 | 71 | 65 | 78 | 78 | 78 | 21 | 41 | 78 | 78 | 78 | 78 | 0 |
| S2-ID | 0 | 0 | 51 | 47 | 56 | 56 | 56 | 15 | 27 | 56 | 56 | 56 | 56 | 0 |

## Appendix A3 — Boundary verification off vs on (data: MPBench v4 split (reused), GPT-4o-mini)

Panel A — answer-level: target ASR

| Method | random_concentrate off | random_spread off | sybil_k1_rand off | sybil_k2_rand off | sybil_k4_rand off | sybil_k8_rand off | launder_r0_rand off | launder_r1_rand off | launder_r2_rand off | launder_r3_rand off | launder_r4_rand off | sybilown_k2_rand off | sybilown_k4_rand off | sybilown_k8_rand off | cohabit_x1_rand off | random_concentrate on | random_spread on | sybil_k1_rand on | sybil_k2_rand on | sybil_k4_rand on | sybil_k8_rand on | launder_r0_rand on | launder_r1_rand on | launder_r2_rand on | launder_r3_rand on | launder_r4_rand on | sybilown_k2_rand on | sybilown_k4_rand on | sybilown_k8_rand on | cohabit_x1_rand on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| R | 30 | 35 | 32 | 28 | 33 | 32 | 31 | 31 | 31 | 32 | 31 | 30 | 33 | 32 | 32 | 30 | 31 | 32 | 28 | 33 | 32 | 31 | 31 | 31 | 32 | 31 | 30 | 33 | 32 | 32 |
| C | 0 | 0 | 0 | 24 | 32 | 33 | 0 | 14 | 26 | 31 | 32 | 24 | 32 | 33 | 0 | 16 | 3 | 16 | 27 | 33 | 33 | 14 | 28 | 29 | 31 | 30 | 27 | 32 | 33 | 18 |
| M | 0 | 0 | 0 | 12 | 32 | 33 | 0 | 9 | 18 | 27 | 32 | 8 | 32 | 34 | 0 | 0 | 3 | 0 | 19 | 32 | 33 | 0 | 14 | 22 | 27 | 31 | 11 | 32 | 34 | 0 |
| A-MemGuard | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 |
| MemLineage | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 |
| LLM sanitiser | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 |
| RandEC | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| S | 0 | 10 | 0 | 24 | 32 | 33 | 0 | 15 | 25 | 30 | 31 | 25 | 32 | 33 | 0 | 0 | 5 | 0 | 24 | 32 | 33 | 0 | 14 | 25 | 30 | 31 | 25 | 32 | 33 | 0 |
| SL | 0 | 10 | 0 | 24 | 33 | 34 | 0 | 15 | 24 | 29 | 31 | 26 | 33 | 33 | 0 | 0 | 4 | 0 | 24 | 33 | 34 | 0 | 14 | 24 | 29 | 30 | 26 | 33 | 33 | 0 |
| S2-ID | 0 | 7 | 0 | 17 | 23 | 21 | 0 | 10 | 15 | 20 | 22 | 20 | 23 | 24 | 0 | 0 | 3 | 0 | 17 | 23 | 21 | 0 | 9 | 15 | 20 | 21 | 20 | 23 | 24 | 0 |

Panel B — retrieval exposure: unaudited exposure

| Method | random_concentrate off | random_spread off | sybil_k1_rand off | sybil_k2_rand off | sybil_k4_rand off | sybil_k8_rand off | launder_r0_rand off | launder_r1_rand off | launder_r2_rand off | launder_r3_rand off | launder_r4_rand off | sybilown_k2_rand off | sybilown_k4_rand off | sybilown_k8_rand off | cohabit_x1_rand off | random_concentrate on | random_spread on | sybil_k1_rand on | sybil_k2_rand on | sybil_k4_rand on | sybil_k8_rand on | launder_r0_rand on | launder_r1_rand on | launder_r2_rand on | launder_r3_rand on | launder_r4_rand on | sybilown_k2_rand on | sybilown_k4_rand on | sybilown_k8_rand on | cohabit_x1_rand on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 77 | 81 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 | 77 | 82 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 |
| R | 77 | 81 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 | 77 | 82 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 |
| C | 0 | 0 | 0 | 59 | 77 | 78 | 0 | 32 | 65 | 73 | 74 | 64 | 78 | 76 | 0 | 39 | 11 | 41 | 66 | 78 | 78 | 31 | 67 | 71 | 75 | 72 | 70 | 78 | 76 | 42 |
| M | 0 | 0 | 0 | 28 | 77 | 78 | 0 | 19 | 41 | 65 | 75 | 21 | 76 | 76 | 0 | 0 | 11 | 0 | 44 | 76 | 78 | 0 | 32 | 50 | 62 | 72 | 30 | 76 | 76 | 0 |
| A-MemGuard | 66 | 63 | 62 | 65 | 64 | 62 | 62 | 64 | 67 | 64 | 60 | 62 | 63 | 63 | 68 | 66 | 63 | 62 | 65 | 64 | 62 | 62 | 64 | 67 | 64 | 60 | 62 | 63 | 63 | 68 |
| MemLineage | 53 | 56 | 55 | 48 | 53 | 52 | 53 | 56 | 57 | 57 | 53 | 56 | 54 | 57 | 55 | 53 | 56 | 55 | 48 | 53 | 52 | 53 | 56 | 57 | 57 | 53 | 56 | 54 | 57 | 55 |
| LLM sanitiser | 76 | 80 | 76 | 72 | 76 | 75 | 71 | 76 | 76 | 76 | 72 | 71 | 77 | 74 | 78 | 76 | 80 | 76 | 72 | 76 | 75 | 71 | 76 | 76 | 76 | 72 | 71 | 77 | 74 | 78 |
| RandEC | 77 | 81 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 | 77 | 82 | 77 | 72 | 78 | 77 | 74 | 77 | 78 | 78 | 74 | 74 | 79 | 75 | 79 |
| S | 0 | 30 | 0 | 59 | 77 | 78 | 0 | 32 | 63 | 72 | 72 | 64 | 78 | 76 | 0 | 0 | 16 | 0 | 59 | 77 | 78 | 0 | 32 | 63 | 71 | 71 | 64 | 78 | 76 | 0 |
| SL | 0 | 30 | 0 | 59 | 77 | 80 | 0 | 32 | 63 | 72 | 74 | 64 | 78 | 77 | 0 | 0 | 16 | 0 | 59 | 77 | 80 | 0 | 32 | 63 | 72 | 72 | 64 | 78 | 77 | 0 |
| S2-ID | 0 | 20 | 0 | 43 | 52 | 53 | 0 | 22 | 45 | 52 | 53 | 50 | 53 | 58 | 0 | 0 | 11 | 0 | 43 | 52 | 53 | 0 | 22 | 45 | 51 | 51 | 50 | 53 | 58 | 0 |

## Appendix A4 — Worst-case cells (data: MPBench v4 split (reused), GPT-4o-mini)

| Method | metric (level) | worst cell | value [95% CI of max] | cells covered |
|---|---|---|---|---|
| Original SAFE-Mem | target_asr (answer-level) | localized | 63 [53, 73] | 46 of 46 |
| Original SAFE-Mem | judge_asr (answer-level) | localized | 77 [70, 84] | 46 of 46 |
| Original SAFE-Mem | unaudited_exposure (retrieval exposure) | random_spread | 81 [71, 90] | 46 of 46 |
| R | target_asr (answer-level) | localized | 63 [53, 73] | 46 of 46 |
| R | judge_asr (answer-level) | localized | 77 [70, 84] | 46 of 46 |
| R | unaudited_exposure (retrieval exposure) | random_spread | 81 [71, 90] | 46 of 46 |
| C | target_asr (answer-level) | shift_context | 66 [56, 76] | 46 of 46 |
| C | judge_asr (answer-level) | shift_context | 78 [72, 86] | 46 of 46 |
| C | unaudited_exposure (retrieval exposure) | sybil_k8_rand | 78 [70, 88] | 46 of 46 |
| M | target_asr (answer-level) | launder_r4 | 66 [56, 76] | 46 of 46 |
| M | judge_asr (answer-level) | launder_r4 | 78 [71, 86] | 46 of 46 |
| M | unaudited_exposure (retrieval exposure) | sybil_k8_rand | 78 [69, 88] | 46 of 46 |
| A-MemGuard | target_asr (answer-level) | localized | 49 [40, 58] | 46 of 46 |
| A-MemGuard | judge_asr (answer-level) | localized | 59 [50, 68] | 46 of 46 |
| A-MemGuard | unaudited_exposure (retrieval exposure) | cohabit_x1_rand | 68 [57, 80] | 46 of 46 |
| MemLineage | target_asr (answer-level) | localized | 44 [33, 54] | 46 of 46 |
| MemLineage | judge_asr (answer-level) | localized | 56 [46, 67] | 46 of 46 |
| MemLineage | unaudited_exposure (retrieval exposure) | sybilown_k8_rand | 57 [49, 70] | 46 of 46 |
| LLM sanitiser | target_asr (answer-level) | localized | 56 [47, 67] | 46 of 46 |
| LLM sanitiser | judge_asr (answer-level) | localized | 69 [59, 78] | 46 of 46 |
| LLM sanitiser | unaudited_exposure (retrieval exposure) | random_spread | 80 [69, 89] | 46 of 46 |
| RandEC | target_asr (answer-level) | localized | 63 [53, 73] | 46 of 46 |
| RandEC | judge_asr (answer-level) | localized | 77 [70, 84] | 46 of 46 |
| RandEC | unaudited_exposure (retrieval exposure) | random_spread | 81 [71, 90] | 46 of 46 |
| S | target_asr (answer-level) | shift_batch | 66 [56, 76] | 46 of 46 |
| S | judge_asr (answer-level) | shift_batch | 78 [72, 86] | 46 of 46 |
| S | unaudited_exposure (retrieval exposure) | sybil_k8_rand | 78 [70, 88] | 46 of 46 |
| SL | target_asr (answer-level) | sybil_k4 | 67 [57, 76] | 46 of 46 |
| SL | judge_asr (answer-level) | shift_batch | 78 [70, 85] | 46 of 46 |
| SL | unaudited_exposure (retrieval exposure) | sybil_k8_rand | 80 [71, 89] | 46 of 46 |
| S2-ID | target_asr (answer-level) | sybil_k4 | 47 [36, 57] | 46 of 46 |
| S2-ID | judge_asr (answer-level) | shift_batch | 56 [46, 67] | 46 of 46 |
| S2-ID | unaudited_exposure (retrieval exposure) | sybilown_k8_rand | 58 [48, 69] | 46 of 46 |
| S2-BS | target_asr (answer-level) | sybilown_k4 | 67 [57, 76] | 46 of 46 |
| S2-BS | judge_asr (answer-level) | shift_batch | 78 [70, 85] | 46 of 46 |
| S2-BS | unaudited_exposure (retrieval exposure) | sybilown_k4 | 79 [71, 89] | 46 of 46 |
| A-MemGuard+R | target_asr (answer-level) | localized | 49 [40, 58] | 46 of 46 |
| A-MemGuard+R | judge_asr (answer-level) | localized | 59 [50, 68] | 46 of 46 |
| A-MemGuard+R | unaudited_exposure (retrieval exposure) | cohabit_x1_rand | 68 [57, 80] | 46 of 46 |
| MemLineage+R | target_asr (answer-level) | localized | 44 [33, 54] | 46 of 46 |
| MemLineage+R | judge_asr (answer-level) | localized | 56 [46, 67] | 46 of 46 |
| MemLineage+R | unaudited_exposure (retrieval exposure) | sybilown_k8_rand | 57 [49, 70] | 46 of 46 |
| LLM sanitiser+R | target_asr (answer-level) | localized | 56 [47, 67] | 46 of 46 |
| LLM sanitiser+R | judge_asr (answer-level) | localized | 69 [59, 78] | 46 of 46 |
| LLM sanitiser+R | unaudited_exposure (retrieval exposure) | random_spread | 80 [69, 89] | 46 of 46 |
| RandEC+R | target_asr (answer-level) | localized | 63 [53, 73] | 46 of 46 |
| RandEC+R | judge_asr (answer-level) | localized | 77 [70, 84] | 46 of 46 |
| RandEC+R | unaudited_exposure (retrieval exposure) | random_spread | 81 [71, 90] | 46 of 46 |

## Appendix A5 — Multi-way cluster bootstrap sensitivity (data: MPBench v4 split (reused), GPT-4o-mini)

Factors: {'attack_family': ['delayed_conditional', 'experience', 'explicit_keyword', 'fact_injection', 'repetition'], 'benign_source': ['mpbench']}. Decisions that change vs the group bootstrap: none.

| Contrast | group bootstrap: Holm p, decision | multi-way: Holm p, decision |
|---|---|---|
| H1 vs C | <0.0001 ✓ | <0.0001 ✓ |
| H1 vs M | <0.0001 ✓ | <0.0001 ✓ |
| H2 | <0.0001 ✓ | <0.0001 ✓ |
| H3 | <0.0001 ✓ | <0.0001 ✓ |
| H4 | <0.0001 ✓ | 0.0120 ✓ |
| H5 | <0.0001 ✓ | 0.0438 ✓ |
| H6 vs C | 1.0000 ✗ | 1.0000 ✗ |
| H6 vs M | 1.0000 ✗ | 1.0000 ✗ |

## Appendix A6 — Covariates: localized by benign source type and by domain (data: MPBench v4 split (reused), GPT-4o-mini; descriptive)

| Factor | Level | Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|---|---|
| benign_source | mpbench | Original SAFE-Mem | – | – | 91 | – | 91 | – |
| benign_source | mpbench | R | – | – | 91 | – | 91 | – |
| benign_source | mpbench | C | – | – | 66 | – | 66 | – |
| benign_source | mpbench | M | – | – | 66 | – | 66 | – |
| benign_source | mpbench | A-MemGuard | – | – | 87 | – | 87 | – |
| benign_source | mpbench | MemLineage | – | – | 91 | – | 91 | – |
| benign_source | mpbench | LLM sanitiser | – | – | 91 | – | 91 | – |
| benign_source | mpbench | RandEC | – | – | 91 | – | 91 | – |
| benign_source | mpbench | S | – | – | 91 | – | 91 | – |
| benign_source | mpbench | SL | – | – | 91 | – | 91 | – |
| benign_source | mpbench | S2-ID | – | – | 91 | – | 91 | – |
| domain | calendar | Original SAFE-Mem | 70 | 83 | 95 | 90 | 95 | 80 |
| domain | calendar | R | 70 | 83 | 95 | 90 | 95 | 80 |
| domain | calendar | C | 0 | 0 | 69 | 0 | 69 | 80 |
| domain | calendar | M | 0 | 0 | 69 | 0 | 69 | 80 |
| domain | calendar | A-MemGuard | 53 | 67 | 93 | 80 | 93 | 80 |
| domain | calendar | MemLineage | 53 | 63 | 95 | 70 | 95 | 40 |
| domain | calendar | LLM sanitiser | 63 | 73 | 95 | 87 | 95 | 80 |
| domain | calendar | RandEC | 70 | 83 | 95 | 90 | 95 | 80 |
| domain | calendar | S | 0 | 0 | 95 | 0 | 95 | 80 |
| domain | calendar | SL | 0 | 0 | 95 | 0 | 95 | 0 |
| domain | calendar | S2-ID | 0 | 0 | 95 | 0 | 95 | 0 |
| domain | email | Original SAFE-Mem | 56 | 61 | 98 | 72 | 98 | 40 |
| domain | email | R | 56 | 61 | 98 | 72 | 98 | 40 |
| domain | email | C | 0 | 0 | 71 | 0 | 71 | 40 |
| domain | email | M | 0 | 0 | 71 | 0 | 71 | 40 |
| domain | email | A-MemGuard | 50 | 61 | 96 | 67 | 96 | 20 |
| domain | email | MemLineage | 33 | 39 | 98 | 50 | 98 | 20 |
| domain | email | LLM sanitiser | 56 | 61 | 98 | 72 | 98 | 20 |
| domain | email | RandEC | 56 | 61 | 98 | 72 | 98 | 40 |
| domain | email | S | 0 | 0 | 98 | 0 | 98 | 40 |
| domain | email | SL | 0 | 0 | 98 | 0 | 98 | 0 |
| domain | email | S2-ID | 0 | 0 | 98 | 0 | 98 | 0 |
| domain | file_and_doc | Original SAFE-Mem | 63 | 81 | 66 | 56 | 66 | 80 |
| domain | file_and_doc | R | 63 | 81 | 66 | 56 | 66 | 60 |
| domain | file_and_doc | C | 0 | 0 | 50 | 0 | 50 | 60 |
| domain | file_and_doc | M | 0 | 0 | 50 | 0 | 50 | 60 |
| domain | file_and_doc | A-MemGuard | 44 | 50 | 65 | 38 | 65 | 60 |
| domain | file_and_doc | MemLineage | 38 | 56 | 66 | 25 | 66 | 80 |
| domain | file_and_doc | LLM sanitiser | 50 | 69 | 66 | 56 | 66 | 60 |
| domain | file_and_doc | RandEC | 63 | 81 | 66 | 56 | 66 | 80 |
| domain | file_and_doc | S | 0 | 0 | 66 | 0 | 66 | 60 |
| domain | file_and_doc | SL | 0 | 0 | 66 | 0 | 66 | 0 |
| domain | file_and_doc | S2-ID | 0 | 0 | 66 | 0 | 66 | 0 |
| domain | script_execution | Original SAFE-Mem | 50 | 75 | 96 | 100 | 96 | 100 |
| domain | script_execution | R | 50 | 75 | 96 | 100 | 96 | 100 |
| domain | script_execution | C | 0 | 0 | 68 | 0 | 68 | 100 |
| domain | script_execution | M | 0 | 0 | 68 | 0 | 68 | 100 |
| domain | script_execution | A-MemGuard | 75 | 75 | 92 | 100 | 92 | 100 |
| domain | script_execution | MemLineage | 0 | 25 | 96 | 50 | 96 | 100 |
| domain | script_execution | LLM sanitiser | 75 | 75 | 96 | 100 | 96 | 100 |
| domain | script_execution | RandEC | 50 | 75 | 96 | 100 | 96 | 100 |
| domain | script_execution | S | 0 | 0 | 96 | 0 | 96 | 100 |
| domain | script_execution | SL | 0 | 0 | 96 | 0 | 96 | 0 |
| domain | script_execution | S2-ID | 0 | 0 | 96 | 0 | 96 | 0 |
| domain | slack | Original SAFE-Mem | 67 | 78 | 99 | 72 | 99 | 100 |
| domain | slack | R | 67 | 78 | 99 | 72 | 99 | 25 |
| domain | slack | C | 0 | 0 | 72 | 0 | 72 | 25 |
| domain | slack | M | 0 | 0 | 72 | 0 | 72 | 25 |
| domain | slack | A-MemGuard | 44 | 56 | 89 | 50 | 89 | 75 |
| domain | slack | MemLineage | 61 | 67 | 99 | 61 | 99 | 75 |
| domain | slack | LLM sanitiser | 61 | 72 | 99 | 67 | 99 | 100 |
| domain | slack | RandEC | 67 | 78 | 99 | 72 | 99 | 100 |
| domain | slack | S | 0 | 0 | 99 | 0 | 99 | 25 |
| domain | slack | SL | 0 | 0 | 99 | 0 | 99 | 0 |
| domain | slack | S2-ID | 0 | 0 | 99 | 0 | 99 | 0 |
| domain | web | Original SAFE-Mem | 50 | 80 | 91 | 70 | 91 | 100 |
| domain | web | R | 50 | 80 | 91 | 70 | 91 | 75 |
| domain | web | C | 0 | 0 | 62 | 0 | 62 | 75 |
| domain | web | M | 0 | 0 | 62 | 0 | 62 | 75 |
| domain | web | A-MemGuard | 40 | 50 | 84 | 50 | 84 | 50 |
| domain | web | MemLineage | 30 | 60 | 91 | 50 | 91 | 100 |
| domain | web | LLM sanitiser | 30 | 60 | 91 | 70 | 91 | 100 |
| domain | web | RandEC | 50 | 80 | 91 | 70 | 91 | 100 |
| domain | web | S | 0 | 0 | 91 | 0 | 91 | 75 |
| domain | web | SL | 0 | 0 | 91 | 0 | 91 | 0 |
| domain | web | S2-ID | 0 | 0 | 91 | 0 | 91 | 0 |

## Appendix A7 — Rows without an answer-level outcome (data: MPBench v4 split (reused), GPT-4o-mini)

Failed or unanswered calls are reported, never excluded or re-run; they enter retrieval exposure only. none

## Appendix A13 — Second backbone: Claude Haiku answers, GPT-4o-mini judge; all 11 methods (data: MPBench v4 split (reused), Claude Haiku; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

Table 1 layout, localized, oracle audits; value [95% CI]

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| Original SAFE-Mem | 29 [21, 38] | 29 [21, 38] | 91 [87, 94] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| R | 29 [21, 38] | 29 [21, 38] | 91 [87, 94] | 76 [66, 85] | 91 [87, 95] | 58 [38, 79] |
| C | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| M | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| A-MemGuard | 15 [8, 21] | 16 [9, 22] | 85 [81, 89] | 63 [51, 73] | 87 [83, 91] | 58 [38, 79] |
| MemLineage | 17 [11, 22] | 17 [11, 22] | 91 [87, 94] | 54 [44, 65] | 91 [87, 95] | 63 [42, 79] |
| LLM sanitiser | 25 [18, 33] | 25 [18, 33] | 91 [87, 94] | 74 [63, 83] | 91 [87, 95] | 71 [54, 88] |
| RandEC | 29 [21, 38] | 29 [21, 38] | 91 [87, 94] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| S | 0 [0, 0] | 0 [0, 0] | 91 [87, 94] | 0 [0, 0] | 91 [87, 95] | 58 [38, 79] |
| SL | 0 [0, 0] | 0 [0, 0] | 91 [87, 94] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |
| S2-ID | 0 [0, 0] | 0 [0, 0] | 91 [87, 94] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

### A13 hypotheses (descriptive for this backbone) — Pre-registered hypotheses (Holm over 8 primary contrasts, one-sided bound at the contrast's Holm level) (data: MPBench v4 split (reused), Claude Haiku; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

**Evidence: replication, not confirmatory.** The pre-registered rules are applied unchanged, but the data are not fresh held-out data, so ✓/✗ are not confirmatory tests.

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound @ Holm level | Margin | Holm p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_strict_utility S − C (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − C (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H1 vs M | key_strict_utility S − M (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − M (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H2 | judge_asr S − M (answer-level) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | target_asr S − a_memguard (answer-level) | localized | −15 [−21, −8] | −7 | < 0 | <0.0001 | ✓ |
|  | target_asr S − memlineage (answer-level) | localized | −17 [−22, −11] | −10 | < 0 |  |  |
|  | target_asr S − llm_sanitiser (answer-level) | localized | −25 [−33, −18] | −17 | < 0 |  |  |
|  | target_asr S − randec (answer-level) | localized | −29 [−37, −21] | −20 | < 0 |  |  |
| H4 | target_asr S2-ID − S (answer-level) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | −7 [−12, −3] | −3 | < 0 | 0.0009 | ✓ |
|  | strict_utility S2-ID − S (answer-level) | localized | 0 [0, 0] | −1 | > −5 |  |  |
| H5 | relay_exposure SL − S (retrieval exposure) | localized | −58 [−79, −37] | −37 | < 0 | <0.0001 | ✓ |
|  | strict_utility SL − S (answer-level) | localized | 0 [0, 0] | −1 | > −5 |  |  |
| H6 vs C | innocent_strict_utility S − C (answer-level) | imp_localized_fp1 | 0 [0, 0] | 0 | > 0 | 1.0000 | ✗ |
| H6 vs M | innocent_strict_utility S − M (answer-level) | imp_localized_fp1 | 0 [0, +1] | 0 | > 0 | 0.7230 | ✗ |

Gatekept key secondaries (tested at the contrast's Holm level only if its primary passed; never rescue a failed primary):

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound | Margin | p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_exposure S − C (retrieval exposure) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
| H1 vs M | key_exposure S − M (retrieval exposure) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
| H2 | unaudited_exposure S − M (retrieval exposure) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | unaudited_exposure S − a_memguard (retrieval exposure) | localized | −62 [−73, −51] | −48 | < 0 | <0.0001 | ✓ |
|  | unaudited_exposure S − memlineage (retrieval exposure) | localized | −54 [−65, −44] | −43 | < 0 |  |  |
|  | unaudited_exposure S − llm_sanitiser (retrieval exposure) | localized | −74 [−83, −62] | −60 | < 0 |  |  |
|  | unaudited_exposure S − randec (retrieval exposure) | localized | −76 [−85, −66] | −64 | < 0 |  |  |
| H4 | unaudited_exposure S2-ID − S (retrieval exposure) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | −22 [−30, −14] | −14 | < 0 | <0.0001 | ✓ |
| H5 | relay_target_asr SL − S (answer-level) | localized | −12 [−29, 0] | 0 | < 0 | 0.0412 | ✗ |
| H6 vs C | not tested (primary did not pass) | | | | | | |
| H6 vs M | not tested (primary did not pass) | | | | | | |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Appendix A14 — Third backbone: Gemini 3.1 Flash-Lite answers, GPT-4o-mini judge; all 11 methods (data: MPBench v4 split (reused), Gemini 3.1 Flash-Lite (post-hoc); reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

**Post-hoc additional backbone (revision 10):** added after the main analysis (post-hoc); not pre-registered. Same cells, methods, prompts, retrieval, judge and metrics as the Claude Haiku run; only the answering model changes. Exploratory evidence of generalization, not confirmatory.

Table 1 layout, localized, oracle audits; value [95% CI]

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| Original SAFE-Mem | 59 [50, 69] | 72 [65, 79] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| R | 59 [50, 69] | 72 [65, 79] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 58 [38, 79] |
| C | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| M | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| A-MemGuard | 46 [35, 57] | 58 [49, 68] | 87 [83, 91] | 63 [51, 73] | 87 [83, 91] | 58 [38, 79] |
| MemLineage | 44 [33, 54] | 54 [46, 63] | 91 [87, 95] | 54 [44, 65] | 91 [87, 95] | 63 [42, 79] |
| LLM sanitiser | 51 [41, 61] | 64 [55, 73] | 91 [87, 95] | 74 [63, 83] | 91 [87, 95] | 71 [54, 88] |
| RandEC | 59 [50, 69] | 72 [65, 79] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| S | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 58 [38, 79] |
| SL | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |
| S2-ID | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

### A14 hypotheses (descriptive for this backbone) — Pre-registered hypotheses (Holm over 8 primary contrasts, one-sided bound at the contrast's Holm level) (data: MPBench v4 split (reused), Gemini 3.1 Flash-Lite (post-hoc); reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

**Evidence: replication, not confirmatory.** The pre-registered rules are applied unchanged, but the data are not fresh held-out data, so ✓/✗ are not confirmatory tests.

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound @ Holm level | Margin | Holm p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_strict_utility S − C (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − C (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H1 vs M | key_strict_utility S − M (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − M (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H2 | judge_asr S − M (answer-level) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | target_asr S − a_memguard (answer-level) | localized | −46 [−57, −35] | −33 | < 0 | <0.0001 | ✓ |
|  | target_asr S − memlineage (answer-level) | localized | −44 [−54, −33] | −31 | < 0 |  |  |
|  | target_asr S − llm_sanitiser (answer-level) | localized | −51 [−61, −41] | −39 | < 0 |  |  |
|  | target_asr S − randec (answer-level) | localized | −59 [−69, −50] | −48 | < 0 |  |  |
| H4 | target_asr S2-ID − S (answer-level) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | −14 [−19, −8] | −7 | < 0 | <0.0001 | ✓ |
|  | strict_utility S2-ID − S (answer-level) | localized | 0 [0, 0] | 0 | > −5 |  |  |
| H5 | relay_exposure SL − S (retrieval exposure) | localized | −58 [−79, −37] | −37 | < 0 | <0.0001 | ✓ |
|  | strict_utility SL − S (answer-level) | localized | 0 [0, 0] | 0 | > −5 |  |  |
| H6 vs C | innocent_strict_utility S − C (answer-level) | imp_localized_fp1 | 0 [0, 0] | 0 | > 0 | 1.0000 | ✗ |
| H6 vs M | innocent_strict_utility S − M (answer-level) | imp_localized_fp1 | 0 [0, 0] | 0 | > 0 | 1.0000 | ✗ |

Gatekept key secondaries (tested at the contrast's Holm level only if its primary passed; never rescue a failed primary):

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound | Margin | p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_exposure S − C (retrieval exposure) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
| H1 vs M | key_exposure S − M (retrieval exposure) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
| H2 | unaudited_exposure S − M (retrieval exposure) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | unaudited_exposure S − a_memguard (retrieval exposure) | localized | −62 [−73, −51] | −48 | < 0 | <0.0001 | ✓ |
|  | unaudited_exposure S − memlineage (retrieval exposure) | localized | −54 [−65, −44] | −43 | < 0 |  |  |
|  | unaudited_exposure S − llm_sanitiser (retrieval exposure) | localized | −74 [−83, −62] | −60 | < 0 |  |  |
|  | unaudited_exposure S − randec (retrieval exposure) | localized | −76 [−85, −66] | −64 | < 0 |  |  |
| H4 | unaudited_exposure S2-ID − S (retrieval exposure) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | −22 [−30, −14] | −13 | < 0 | <0.0001 | ✓ |
| H5 | relay_target_asr SL − S (answer-level) | localized | −50 [−71, −29] | −29 | < 0 | <0.0001 | ✓ |
| H6 vs C | not tested (primary did not pass) | | | | | | |
| H6 vs M | not tested (primary did not pass) | | | | | | |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*
