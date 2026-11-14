## Appendix A1 — S2-BS and "+R" published variants, localized (data: dev, 8 groups)

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| S2-BS | – | – | – | – | – | – |
| A-MemGuard+R | – | – | – | – | – | – |
| MemLineage+R | – | – | – | – | – | – |
| LLM sanitiser+R | – | – | – | – | – | – |
| RandEC+R | – | – | – | – | – | – |

## Appendix A2 — Judge ASR (answer-level), every Table-2 attack (data: dev)

| Method | localized | distributed | uninformative | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case | relay (localized) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 72 | 72 | 72 | – | – | – | – | – | – | – | 72 | 72 | 72 | 88 |
| R | 72 | 72 | 72 | – | – | – | – | – | – | – | 72 | 72 | 72 | 50 |
| C | 0 | 0 | 59 | – | – | – | – | – | – | – | 0 | 78 | 78 | 50 |
| M | 0 | 0 | 47 | – | – | – | – | – | – | – | 0 | 75 | 75 | 50 |
| A-MemGuard | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| S | 0 | 0 | 63 | – | – | – | – | – | – | – | 78 | 78 | 78 | 50 |
| SL | 0 | 0 | 69 | – | – | – | – | – | – | – | 78 | 78 | 78 | 0 |
| S2-ID | – | – | – | – | – | – | – | – | – | – | – | – | – | – |

## Appendix A3 — Boundary verification off vs on (data: dev)

Panel A — answer-level: target ASR

| Method | random_concentrate off | random_spread off | sybil_k1_rand off | sybil_k2_rand off | sybil_k4_rand off | sybil_k8_rand off | launder_r0_rand off | launder_r1_rand off | launder_r2_rand off | launder_r3_rand off | launder_r4_rand off | sybilown_k2_rand off | sybilown_k4_rand off | sybilown_k8_rand off | cohabit_x1_rand off | random_concentrate on | random_spread on | sybil_k1_rand on | sybil_k2_rand on | sybil_k4_rand on | sybil_k8_rand on | launder_r0_rand on | launder_r1_rand on | launder_r2_rand on | launder_r3_rand on | launder_r4_rand on | sybilown_k2_rand on | sybilown_k4_rand on | sybilown_k8_rand on | cohabit_x1_rand on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 59 | 59 | – | – | – | – | – | – | – | – | – | – | – | – | – | 59 | 59 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| R | 30 | 30 | – | – | – | – | – | – | – | – | – | – | – | – | – | 30 | 29 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| C | 0 | 0 | – | – | – | – | – | – | – | – | – | – | – | – | – | 17 | 4 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| M | 0 | 0 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 4 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| S | 0 | 10 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 5 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| SL | 0 | 10 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 5 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |

Panel B — retrieval exposure: unaudited exposure

| Method | random_concentrate off | random_spread off | sybil_k1_rand off | sybil_k2_rand off | sybil_k4_rand off | sybil_k8_rand off | launder_r0_rand off | launder_r1_rand off | launder_r2_rand off | launder_r3_rand off | launder_r4_rand off | sybilown_k2_rand off | sybilown_k4_rand off | sybilown_k8_rand off | cohabit_x1_rand off | random_concentrate on | random_spread on | sybil_k1_rand on | sybil_k2_rand on | sybil_k4_rand on | sybil_k8_rand on | launder_r0_rand on | launder_r1_rand on | launder_r2_rand on | launder_r3_rand on | launder_r4_rand on | sybilown_k2_rand on | sybilown_k4_rand on | sybilown_k8_rand on | cohabit_x1_rand on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 97 | 97 | – | – | – | – | – | – | – | – | – | – | – | – | – | 97 | 97 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| R | 97 | 97 | – | – | – | – | – | – | – | – | – | – | – | – | – | 97 | 97 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| C | 0 | 0 | – | – | – | – | – | – | – | – | – | – | – | – | – | 45 | 9 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| M | 0 | 0 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 9 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| S | 0 | 34 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 14 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| SL | 0 | 34 | – | – | – | – | – | – | – | – | – | – | – | – | – | 0 | 14 | – | – | – | – | – | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |

## Appendix A4 — Worst-case cells (data: dev)

| Method | metric (level) | worst cell | value [95% CI of max] | cells covered |
|---|---|---|---|---|
| Original SAFE-Mem | target_asr (answer-level) | localized | 59 [44, 75] | 9 of 47 |
| Original SAFE-Mem | judge_asr (answer-level) | localized | 72 [56, 88] | 9 of 47 |
| Original SAFE-Mem | unaudited_exposure (retrieval exposure) | localized | 97 [91, 100] | 9 of 47 |
| R | target_asr (answer-level) | localized | 59 [44, 75] | 9 of 47 |
| R | judge_asr (answer-level) | localized | 72 [56, 88] | 9 of 47 |
| R | unaudited_exposure (retrieval exposure) | localized | 97 [91, 100] | 9 of 47 |
| C | target_asr (answer-level) | framing_concentrated | 69 [53, 81] | 9 of 47 |
| C | judge_asr (answer-level) | shift_context | 78 [59, 91] | 9 of 47 |
| C | unaudited_exposure (retrieval exposure) | shift_context | 97 [91, 100] | 9 of 47 |
| M | target_asr (answer-level) | framing_concentrated | 66 [50, 81] | 9 of 47 |
| M | judge_asr (answer-level) | framing_concentrated | 75 [56, 91] | 9 of 47 |
| M | unaudited_exposure (retrieval exposure) | framing_concentrated | 97 [91, 100] | 9 of 47 |
| S | target_asr (answer-level) | framing_concentrated | 69 [53, 81] | 9 of 47 |
| S | judge_asr (answer-level) | shift_batch | 78 [59, 91] | 9 of 47 |
| S | unaudited_exposure (retrieval exposure) | shift_batch | 97 [91, 100] | 9 of 47 |
| SL | target_asr (answer-level) | shift_batch | 66 [50, 81] | 9 of 47 |
| SL | judge_asr (answer-level) | shift_batch | 78 [59, 91] | 9 of 47 |
| SL | unaudited_exposure (retrieval exposure) | shift_batch | 97 [91, 100] | 9 of 47 |

## Appendix A5 — Multi-way cluster bootstrap sensitivity (data: dev)

Factors: {'attack_family': ['delayed_conditional', 'experience', 'explicit_keyword', 'fact_injection', 'repetition'], 'benign_source': ['mpbench']}. Decisions that change vs the group bootstrap: ['H5'].

| Contrast | group bootstrap: Holm p, decision | multi-way: Holm p, decision |
|---|---|---|
| H1 vs C | <0.0001 ✓ | <0.0001 ✓ |
| H1 vs M | <0.0001 ✓ | <0.0001 ✓ |
| H2 | <0.0001 ✓ | <0.0001 ✓ |
| H3 | 1.0000 ✗ | 1.0000 ✗ |
| H4 | 1.0000 ✗ | 1.0000 ✗ |
| H5 | 0.0010 ✓ | 0.1508 ✗ |
| H6 vs C | 1.0000 ✗ | 1.0000 ✗ |
| H6 vs M | 1.0000 ✗ | 1.0000 ✗ |

## Appendix A6 — Covariates: localized by benign source type and by domain (data: dev; descriptive)

| Factor | Level | Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|---|---|
| benign_source | mpbench | Original SAFE-Mem | – | – | 93 | – | 93 | – |
| benign_source | mpbench | R | – | – | 93 | – | 93 | – |
| benign_source | mpbench | C | – | – | 67 | – | 67 | – |
| benign_source | mpbench | M | – | – | 67 | – | 67 | – |
| benign_source | mpbench | S | – | – | 93 | – | 93 | – |
| benign_source | mpbench | SL | – | – | 93 | – | 93 | – |
| domain | calendar | Original SAFE-Mem | 50 | 67 | 96 | 100 | 96 | 100 |
| domain | calendar | R | 50 | 67 | 96 | 100 | 96 | 50 |
| domain | calendar | C | 0 | 0 | 70 | 0 | 70 | 50 |
| domain | calendar | M | 0 | 0 | 70 | 0 | 70 | 50 |
| domain | calendar | S | 0 | 0 | 96 | 0 | 96 | 50 |
| domain | calendar | SL | 0 | 0 | 96 | 0 | 96 | 0 |
| domain | email | Original SAFE-Mem | 63 | 75 | 98 | 100 | 98 | 100 |
| domain | email | R | 63 | 75 | 98 | 100 | 98 | 50 |
| domain | email | C | 0 | 0 | 70 | 0 | 70 | 50 |
| domain | email | M | 0 | 0 | 70 | 0 | 70 | 50 |
| domain | email | S | 0 | 0 | 98 | 0 | 98 | 50 |
| domain | email | SL | 0 | 0 | 98 | 0 | 98 | 0 |
| domain | file_and_doc | Original SAFE-Mem | 100 | 100 | 71 | 100 | 71 | 100 |
| domain | file_and_doc | R | 100 | 100 | 71 | 100 | 71 | 100 |
| domain | file_and_doc | C | 0 | 0 | 52 | 0 | 52 | 100 |
| domain | file_and_doc | M | 0 | 0 | 52 | 0 | 52 | 100 |
| domain | file_and_doc | S | 0 | 0 | 71 | 0 | 71 | 100 |
| domain | file_and_doc | SL | 0 | 0 | 71 | 0 | 71 | 0 |
| domain | slack | Original SAFE-Mem | 33 | 50 | 100 | 83 | 100 | 100 |
| domain | slack | R | 33 | 50 | 100 | 83 | 100 | 50 |
| domain | slack | C | 0 | 0 | 71 | 0 | 71 | 50 |
| domain | slack | M | 0 | 0 | 71 | 0 | 71 | 50 |
| domain | slack | S | 0 | 0 | 100 | 0 | 100 | 50 |
| domain | slack | SL | 0 | 0 | 100 | 0 | 100 | 0 |

## Appendix A7 — Rows without an answer-level outcome (data: dev)

Failed or unanswered calls are reported, never excluded or re-run; they enter retrieval exposure only. none
