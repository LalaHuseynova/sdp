## Table 1 — Main result, localized, oracle audits; value [95% CI] (data: dev, 8 groups)

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| Original SAFE-Mem | 59 [44, 75] | 72 [56, 88] | 93 [85, 99] | 97 [91, 100] | 93 [85, 99] | 100 [100, 100] |
| R | 59 [44, 75] | 72 [56, 88] | 93 [85, 99] | 97 [91, 100] | 93 [85, 99] | 63 [25, 88] |
| C | 0 [0, 0] | 0 [0, 0] | 67 [61, 71] | 0 [0, 0] | 67 [61, 71] | 63 [25, 88] |
| M | 0 [0, 0] | 0 [0, 0] | 67 [61, 71] | 0 [0, 0] | 67 [61, 71] | 63 [25, 88] |
| A-MemGuard | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – |
| S | 0 [0, 0] | 0 [0, 0] | 93 [85, 99] | 0 [0, 0] | 93 [85, 99] | 63 [25, 88] |
| SL | 0 [0, 0] | 0 [0, 0] | 93 [85, 99] | 0 [0, 0] | 93 [85, 99] | 0 [0, 0] |
| S2-ID | – | – | – | – | – | – |

## Table 2 — ASR under every attack; answer-level: target ASR (strict utility) (data: dev, 8 groups)

| Method | localized | distributed | uninformative | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 59 (93) | 59 (93) | 59 (93) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 59 (93) | 59 (93) | 59 (93) |
| R | 59 (93) | 59 (93) | 59 (93) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 59 (93) | 59 (93) | 59 (93) |
| C | 0 (67) | 0 (67) | 47 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 0 (67) | 69 (61) | 69 (61) |
| M | 0 (67) | 0 (67) | 44 (63) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 0 (67) | 66 (55) | 66 (55) |
| A-MemGuard | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| MemLineage | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| LLM sanitiser | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| RandEC | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| S | 0 (93) | 0 (67) | 47 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 66 (78) | 69 (71) | 69 (71) |
| SL | 0 (93) | 0 (67) | 53 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 66 (78) | 66 (71) | 66 (78) |
| S2-ID | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |

## Table 2b — Exposure under every attack; retrieval exposure: unaudited exposure (useful-fact exposure) (data: dev, 8 groups)

| Method | localized | distributed | uninformative | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 97 (93) | 97 (93) | 97 (93) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 97 (93) | 97 (93) | 97 (93) |
| R | 97 (93) | 97 (93) | 97 (93) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 97 (93) | 97 (93) | 97 (93) |
| C | 0 (67) | 0 (67) | 78 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 0 (67) | 97 (61) | 97 (80) |
| M | 0 (67) | 0 (67) | 56 (63) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 0 (67) | 97 (55) | 97 (55) |
| A-MemGuard | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| MemLineage | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| LLM sanitiser | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| RandEC | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |
| S | 0 (93) | 0 (67) | 81 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 97 (78) | 97 (71) | 97 (78) |
| SL | 0 (93) | 0 (67) | 81 (84) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | 97 (78) | 97 (71) | 97 (78) |
| S2-ID | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) | – (–) |

Worst case: maximum over the registered cells present (9 of 47 cells); its parenthesis is the paired metric in that cell.

## Table 3 — Sybil-k, oracle and random audits (data: dev, 8 groups)

Panel A — answer-level: target ASR

| Method | k=1 | k=2 | k=4 | k=8 | k=1 random | k=2 random | k=4 random | k=8 random |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | – | – | – | – | – | – | – | – |
| R | – | – | – | – | – | – | – | – |
| C | – | – | – | – | – | – | – | – |
| M | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – |
| S | – | – | – | – | – | – | – | – |
| SL | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – |

Panel B — retrieval exposure: unaudited exposure

| Method | k=1 | k=2 | k=4 | k=8 | k=1 random | k=2 random | k=4 random | k=8 random |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | – | – | – | – | – | – | – | – |
| R | – | – | – | – | – | – | – | – |
| C | – | – | – | – | – | – | – | – |
| M | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – |
| S | – | – | – | – | – | – | – | – |
| SL | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – |

## Table 4 — Laundering-r, oracle and random audits (data: dev, 8 groups)

Panel A — answer-level: target ASR; innocent strict utility

| Method | r=0 | r=.25 | r=.5 | r=.75 | r=1 | r=0 random | r=.25 random | r=.5 random | r=.75 random | r=1 random | innocent-forwarder utility (r=.75 random) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | – | – | – | – | – | – | – | – | – | – | – |
| R | – | – | – | – | – | – | – | – | – | – | – |
| C | – | – | – | – | – | – | – | – | – | – | – |
| M | – | – | – | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – | – | – | – |
| S | – | – | – | – | – | – | – | – | – | – | – |
| SL | – | – | – | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – | – | – | – |

Panel B — retrieval exposure: unaudited exposure; innocent useful-fact exposure

| Method | r=0 | r=.25 | r=.5 | r=.75 | r=1 | r=0 random | r=.25 random | r=.5 random | r=.75 random | r=1 random | innocent-forwarder exposure (r=.75 random) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | – | – | – | – | – | – | – | – | – | – | – |
| R | – | – | – | – | – | – | – | – | – | – | – |
| C | – | – | – | – | – | – | – | – | – | – | – |
| M | – | – | – | – | – | – | – | – | – | – | – |
| A-MemGuard | – | – | – | – | – | – | – | – | – | – | – |
| MemLineage | – | – | – | – | – | – | – | – | – | – | – |
| LLM sanitiser | – | – | – | – | – | – | – | – | – | – | – |
| RandEC | – | – | – | – | – | – | – | – | – | – | – |
| S | – | – | – | – | – | – | – | – | – | – | – |
| SL | – | – | – | – | – | – | – | – | – | – | – |
| S2-ID | – | – | – | – | – | – | – | – | – | – | – |

## Table 5 — Harm to innocents (data: dev, 8 groups)

Panel A — answer-level: innocent strict utility

| Method | framing concentrated | framing spread | cohabit | FP audit |
|---|---|---|---|---|
| Original SAFE-Mem | 94 | 94 | – | – |
| R | 94 | 94 | – | – |
| C | 42 | 42 | – | – |
| M | 32 | 42 | – | – |
| A-MemGuard | – | – | – | – |
| MemLineage | – | – | – | – |
| LLM sanitiser | – | – | – | – |
| RandEC | – | – | – | – |
| S | 58 | 42 | – | – |
| SL | 58 | 42 | – | – |
| S2-ID | – | – | – | – |

Panel B — retrieval exposure: innocent useful-fact exposure

| Method | framing concentrated | framing spread | cohabit | FP audit |
|---|---|---|---|---|
| Original SAFE-Mem | 94 | 94 | – | – |
| R | 94 | 94 | – | – |
| C | 42 | 42 | – | – |
| M | 32 | 42 | – | – |
| A-MemGuard | – | – | – | – |
| MemLineage | – | – | – | – |
| LLM sanitiser | – | – | – | – |
| RandEC | – | – | – | – |
| S | 58 | 42 | – | – |
| SL | 58 | 42 | – | – |
| S2-ID | – | – | – | – |

## Table 6 — Imperfect audits; answer-level: target ASR / strict utility (data: dev, 8 groups)

| Method | localized · perfect | localized · fn20 | localized · fp1 | localized · late | distributed · perfect | distributed · fn20 | distributed · fp1 | distributed · late | sybil_k2 · perfect | sybil_k2 · fn20 | sybil_k2 · fp1 | sybil_k2 · late | launder_r2 · perfect | launder_r2 · fn20 | launder_r2 · fp1 | launder_r2 · late |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 59 / 93 | – / – | – / – | – / – | 59 / 93 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| R | 59 / 93 | – / – | – / – | – / – | 59 / 93 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| C | 0 / 67 | – / – | – / – | – / – | 0 / 67 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| M | 0 / 67 | – / – | – / – | – / – | 0 / 67 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| A-MemGuard | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| MemLineage | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| LLM sanitiser | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| RandEC | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| S | 0 / 93 | – / – | – / – | – / – | 0 / 67 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| SL | 0 / 93 | – / – | – / – | – / – | 0 / 67 | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| S2-ID | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – | – / – |

## Table 8 — Pre-registered hypotheses (Holm over 8 primary contrasts, one-sided bound at the contrast's Holm level) (data: dev, 8 groups)

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound @ Holm level | Margin | Holm p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_strict_utility S − C (answer-level) | localized | +91 [+80, +98] | +77 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − C (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H1 vs M | key_strict_utility S − M (answer-level) | localized | +91 [+80, +98] | +77 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − M (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H2 | judge_asr S − M (answer-level) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | target_asr S − a_memguard (answer-level) | localized | not estimable | – | < 0 | 1.0000 | not estimable |
|  | target_asr S − memlineage (answer-level) | localized | not estimable | – | < 0 |  |  |
|  | target_asr S − llm_sanitiser (answer-level) | localized | not estimable | – | < 0 |  |  |
|  | target_asr S − randec (answer-level) | localized | not estimable | – | < 0 |  |  |
| H4 | target_asr S2-ID − S (answer-level) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | not estimable | – | < 0 | 1.0000 | not estimable |
|  | strict_utility S2-ID − S (answer-level) | localized | not estimable | – | > −5 |  |  |
| H5 | relay_exposure SL − S (retrieval exposure) | localized | −62 [−87, −25] | −25 | < 0 | 0.0010 | ✓ |
|  | strict_utility SL − S (answer-level) | localized | 0 [0, 0] | 0 | > −5 |  |  |
| H6 vs C | innocent_strict_utility S − C (answer-level) | imp_localized_fp1 | not estimable | – | > 0 | 1.0000 | not estimable |
| H6 vs M | innocent_strict_utility S − M (answer-level) | imp_localized_fp1 | not estimable | – | > 0 | 1.0000 | not estimable |

Gatekept key secondaries (tested at the contrast's Holm level only if its primary passed; never rescue a failed primary):

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound | Margin | p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_exposure S − C (retrieval exposure) | localized | +91 [+80, +98] | +77 | > +3 | <0.0001 | ✓ |
| H1 vs M | key_exposure S − M (retrieval exposure) | localized | +91 [+80, +98] | +77 | > +3 | <0.0001 | ✓ |
| H2 | unaudited_exposure S − M (retrieval exposure) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | not tested (primary did not pass) | | | | | | |
| H4 | not tested (primary did not pass) | | | | | | |
| H5 | relay_target_asr SL − S (answer-level) | localized | −50 [−87, −12] | −12 | < 0 | 0.0032 | ✓ |
| H6 vs C | not tested (primary did not pass) | | | | | | |
| H6 vs M | not tested (primary did not pass) | | | | | | |

## Table 7 — Generalization (answer-level; best published = None, best internal = C, pre-specified)

| Data | S: target ASR / strict utility | Best published: target ASR / strict utility | Best internal: target ASR / strict utility | S − best published, target ASR [95% CI] | S − best internal, strict utility [95% CI] |
|---|---|---|---|---|---|
| dev | 0 / 93 | – / – | 0 / 67 | – | +26 [+23, +28] |
