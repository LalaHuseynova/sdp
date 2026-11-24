## Table 1 — Main result, localized, oracle audits; value [95% CI] (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

| Method | target ASR ↓ [answer-level] | judge ASR ↓ [answer-level] | strict utility ↑ [answer-level] | unaudited exposure ↓ [retrieval exposure] | useful-fact exposure ↑ [retrieval exposure] | relay exposure ↓ [retrieval exposure] |
|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 [53, 73] | 77 [70, 84] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| R | 63 [53, 73] | 77 [70, 84] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 58 [38, 79] |
| C | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| M | 0 [0, 0] | 0 [0, 0] | 66 [63, 68] | 0 [0, 0] | 66 [63, 68] | 58 [38, 79] |
| A-MemGuard | 49 [40, 58] | 59 [50, 68] | 87 [83, 91] | 63 [51, 73] | 87 [83, 91] | 58 [38, 79] |
| MemLineage | 44 [33, 54] | 56 [46, 67] | 91 [87, 95] | 54 [44, 65] | 91 [87, 95] | 63 [42, 79] |
| LLM sanitiser | 56 [47, 67] | 69 [59, 78] | 91 [87, 95] | 74 [63, 83] | 91 [87, 95] | 71 [54, 88] |
| RandEC | 63 [53, 73] | 77 [70, 84] | 91 [87, 95] | 76 [66, 85] | 91 [87, 95] | 79 [63, 92] |
| S | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 58 [38, 79] |
| SL | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |
| S2-ID | 0 [0, 0] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] | 91 [87, 95] | 0 [0, 0] |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 2 — ASR under every attack; answer-level: target ASR (strict utility) (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

| Method | localized | distributed | no-signal control† | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) |
| R | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) |
| C | 0 (66) | 0 (66) | 56 (77) | 51 (85) | 64 (90) | 64 (91) | 64 (90) | 18 (66) | 34 (66) | 66 (66) | 0 (66) | 63 (62) | 66 (80) |
| M | 0 (66) | 0 (66) | 36 (53) | 27 (75) | 60 (86) | 64 (91) | 60 (86) | 18 (66) | 34 (66) | 66 (66) | 0 (66) | 64 (54) | 66 (66) |
| A-MemGuard | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) | 49 (87) |
| MemLineage | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) | 44 (91) |
| LLM sanitiser | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) | 56 (91) |
| RandEC | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) | 63 (91) |
| S | 0 (91) | 0 (66) | 55 (78) | 51 (91) | 64 (91) | 64 (91) | 64 (91) | 19 (91) | 35 (91) | 66 (91) | 66 (77) | 61 (68) | 66 (77) |
| SL | 0 (91) | 0 (66) | 60 (78) | 52 (91) | 67 (91) | 66 (91) | 67 (91) | 18 (91) | 34 (91) | 66 (91) | 66 (77) | 65 (68) | 67 (91) |
| S2-ID | 0 (91) | 0 (66) | 42 (78) | 36 (91) | 47 (91) | 46 (91) | 47 (91) | 11 (91) | 21 (91) | 46 (91) | 46 (77) | 45 (68) | 47 (91) |

† No-signal control (owner decision 35): it assumes the attacker controls every contributor, so no audit can carry signal. It is reported, but it is not an attack and is excluded from the worst case.

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 2b — Exposure under every attack; retrieval exposure: unaudited exposure (useful-fact exposure) (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

| Method | localized | distributed | no-signal control† | sybil k=2 | sybil k=4 | sybil k=8 | own-batch k=4 | launder r=.25 | launder r=.5 | launder r=1 | audit-aware shift (batch) | framing (concentrated) | worst case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 81 (91) |
| R | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 81 (91) |
| C | 0 (66) | 0 (66) | 65 (77) | 65 (85) | 77 (90) | 76 (91) | 77 (90) | 20 (66) | 40 (66) | 78 (66) | 0 (66) | 76 (62) | 78 (91) |
| M | 0 (66) | 0 (66) | 46 (53) | 35 (75) | 74 (86) | 76 (91) | 74 (86) | 20 (66) | 40 (66) | 78 (66) | 0 (66) | 76 (54) | 78 (91) |
| A-MemGuard | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 63 (87) | 68 (87) |
| MemLineage | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 54 (91) | 57 (91) |
| LLM sanitiser | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 74 (91) | 80 (91) |
| RandEC | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 76 (91) | 81 (91) |
| S | 0 (91) | 0 (66) | 65 (78) | 64 (91) | 77 (91) | 76 (91) | 77 (91) | 20 (91) | 40 (91) | 78 (91) | 78 (77) | 76 (68) | 78 (91) |
| SL | 0 (91) | 0 (66) | 67 (78) | 65 (91) | 79 (91) | 78 (91) | 79 (91) | 20 (91) | 40 (91) | 78 (91) | 78 (77) | 78 (68) | 80 (91) |
| S2-ID | 0 (91) | 0 (66) | 47 (78) | 46 (91) | 56 (91) | 55 (91) | 56 (91) | 13 (91) | 25 (91) | 55 (91) | 55 (77) | 55 (68) | 58 (91) |

† No-signal control (owner decision 35): it assumes the attacker controls every contributor, so no audit can carry signal. It is reported, but it is not an attack and is excluded from the worst case.

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

Worst case: maximum over the registered cells present (46 of 46 cells); its parenthesis is the paired metric in that cell.

## Table 3 — Sybil-k, oracle and random audits (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

Panel A — answer-level: target ASR

| Method | k=1 | k=2 | k=4 | k=8 | k=1 random | k=2 random | k=4 random | k=8 random |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| R | 63 | 63 | 63 | 63 | 32 | 28 | 33 | 32 |
| C | 0 | 51 | 64 | 64 | 0 | 24 | 32 | 33 |
| M | 0 | 27 | 60 | 64 | 0 | 12 | 32 | 33 |
| A-MemGuard | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 |
| MemLineage | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 |
| LLM sanitiser | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 |
| RandEC | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| S | 0 | 51 | 64 | 64 | 0 | 24 | 32 | 33 |
| SL | 0 | 52 | 67 | 66 | 0 | 24 | 33 | 34 |
| S2-ID | 0 | 36 | 47 | 46 | 0 | 17 | 23 | 21 |

Panel B — retrieval exposure: unaudited exposure

| Method | k=1 | k=2 | k=4 | k=8 | k=1 random | k=2 random | k=4 random | k=8 random |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 76 | 76 | 76 | 76 | 77 | 72 | 78 | 77 |
| R | 76 | 76 | 76 | 76 | 77 | 72 | 78 | 77 |
| C | 0 | 65 | 77 | 76 | 0 | 59 | 77 | 78 |
| M | 0 | 35 | 74 | 76 | 0 | 28 | 77 | 78 |
| A-MemGuard | 63 | 63 | 63 | 63 | 62 | 65 | 64 | 62 |
| MemLineage | 54 | 54 | 54 | 54 | 55 | 48 | 53 | 52 |
| LLM sanitiser | 74 | 74 | 74 | 74 | 76 | 72 | 76 | 75 |
| RandEC | 76 | 76 | 76 | 76 | 77 | 72 | 78 | 77 |
| S | 0 | 64 | 77 | 76 | 0 | 59 | 77 | 78 |
| SL | 0 | 65 | 79 | 78 | 0 | 59 | 77 | 80 |
| S2-ID | 0 | 46 | 56 | 55 | 0 | 43 | 52 | 53 |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 4 — Laundering-r, oracle and random audits (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

Panel A — answer-level: target ASR; innocent strict utility

| Method | r=0 | r=.25 | r=.5 | r=.75 | r=1 | r=0 random | r=.25 random | r=.5 random | r=.75 random | r=1 random | innocent-forwarder utility (r=.75 random) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 92 |
| R | 63 | 63 | 63 | 63 | 63 | 31 | 31 | 31 | 32 | 31 | 92 |
| C | 0 | 18 | 34 | 48 | 66 | 0 | 14 | 26 | 31 | 32 | 88 |
| M | 0 | 18 | 34 | 48 | 66 | 0 | 9 | 18 | 27 | 32 | 87 |
| A-MemGuard | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 88 |
| MemLineage | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 44 | 92 |
| LLM sanitiser | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 56 | 92 |
| RandEC | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 92 |
| S | 0 | 19 | 35 | 48 | 66 | 0 | 15 | 25 | 30 | 31 | 88 |
| SL | 0 | 18 | 34 | 48 | 66 | 0 | 15 | 24 | 29 | 31 | 88 |
| S2-ID | 0 | 11 | 21 | 30 | 46 | 0 | 10 | 15 | 20 | 22 | 88 |

Panel B — retrieval exposure: unaudited exposure; innocent useful-fact exposure

| Method | r=0 | r=.25 | r=.5 | r=.75 | r=1 | r=0 random | r=.25 random | r=.5 random | r=.75 random | r=1 random | innocent-forwarder exposure (r=.75 random) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 76 | 76 | 76 | 76 | 76 | 74 | 77 | 78 | 78 | 74 | 92 |
| R | 76 | 76 | 76 | 76 | 76 | 74 | 77 | 78 | 78 | 74 | 92 |
| C | 0 | 20 | 40 | 56 | 78 | 0 | 32 | 65 | 73 | 74 | 88 |
| M | 0 | 20 | 40 | 56 | 78 | 0 | 19 | 41 | 65 | 75 | 87 |
| A-MemGuard | 63 | 63 | 63 | 63 | 63 | 62 | 64 | 67 | 64 | 60 | 88 |
| MemLineage | 54 | 54 | 54 | 54 | 54 | 53 | 56 | 57 | 57 | 53 | 92 |
| LLM sanitiser | 74 | 74 | 74 | 74 | 74 | 71 | 76 | 76 | 76 | 72 | 92 |
| RandEC | 76 | 76 | 76 | 76 | 76 | 74 | 77 | 78 | 78 | 74 | 92 |
| S | 0 | 20 | 40 | 56 | 78 | 0 | 32 | 63 | 72 | 72 | 88 |
| SL | 0 | 20 | 40 | 56 | 78 | 0 | 32 | 63 | 72 | 74 | 88 |
| S2-ID | 0 | 13 | 25 | 36 | 55 | 0 | 22 | 45 | 52 | 53 | 88 |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 5 — Harm to innocents (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

Panel A — answer-level: innocent strict utility

| Method | framing concentrated | framing spread | cohabit | FP audit |
|---|---|---|---|---|
| Original SAFE-Mem | 92 | 92 | 92 | 92 |
| R | 92 | 92 | 92 | 92 |
| C | 43 | 43 | 92 | 92 |
| M | 29 | 43 | 92 | 92 |
| A-MemGuard | 88 | 88 | 88 | 88 |
| MemLineage | 92 | 92 | 92 | 92 |
| LLM sanitiser | 92 | 92 | 92 | 92 |
| RandEC | 92 | 92 | 92 | 92 |
| S | 53 | 43 | 92 | 92 |
| SL | 53 | 43 | 92 | 86 |
| S2-ID | 53 | 43 | 92 | 86 |

Panel B — retrieval exposure: innocent useful-fact exposure

| Method | framing concentrated | framing spread | cohabit | FP audit |
|---|---|---|---|---|
| Original SAFE-Mem | 92 | 92 | 92 | 92 |
| R | 92 | 92 | 92 | 92 |
| C | 43 | 43 | 92 | 92 |
| M | 29 | 43 | 92 | 92 |
| A-MemGuard | 88 | 88 | 88 | 88 |
| MemLineage | 92 | 92 | 92 | 92 |
| LLM sanitiser | 92 | 92 | 92 | 92 |
| RandEC | 92 | 92 | 92 | 92 |
| S | 53 | 43 | 92 | 92 |
| SL | 53 | 43 | 92 | 86 |
| S2-ID | 53 | 43 | 92 | 86 |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 6 — Imperfect audits; answer-level: target ASR / strict utility (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

Panel A — localized and distributed

| Method | localized · perfect | localized · fn20 | localized · fp1 | localized · late | distributed · perfect | distributed · fn20 | distributed · fp1 | distributed · late |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| R | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| C | 0 / 66 | 21 / 75 | 0 / 66 | 33 / 78 | 0 / 66 | 21 / 75 | 0 / 66 | 33 / 78 |
| M | 0 / 66 | 20 / 75 | 0 / 66 | 33 / 78 | 0 / 66 | 20 / 75 | 0 / 66 | 33 / 78 |
| A-MemGuard | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 |
| MemLineage | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 |
| LLM sanitiser | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 |
| RandEC | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| S | 0 / 91 | 21 / 91 | 0 / 91 | 33 / 91 | 0 / 66 | 19 / 75 | 0 / 66 | 33 / 78 |
| SL | 0 / 91 | 21 / 91 | 0 / 88 | 33 / 91 | 0 / 66 | 20 / 75 | 0 / 63 | 33 / 78 |
| S2-ID | 0 / 91 | 16 / 91 | 0 / 88 | 24 / 91 | 0 / 66 | 15 / 75 | 0 / 63 | 24 / 78 |

Panel B — Sybil k=2 and laundering r=.5

| Method | sybil_k2 · perfect | sybil_k2 · fn20 | sybil_k2 · fp1 | sybil_k2 · late | launder_r2 · perfect | launder_r2 · fn20 | launder_r2 · fp1 | launder_r2 · late |
|---|---|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| R | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| C | 51 / 85 | 55 / 86 | 50 / 85 | 56 / 88 | 34 / 66 | 45 / 75 | 34 / 66 | 51 / 78 |
| M | 27 / 75 | 39 / 81 | 28 / 75 | 45 / 83 | 34 / 66 | 44 / 75 | 35 / 66 | 51 / 78 |
| A-MemGuard | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 | 49 / 87 |
| MemLineage | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 | 44 / 91 |
| LLM sanitiser | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 | 56 / 91 |
| RandEC | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 | 63 / 91 |
| S | 51 / 91 | 55 / 91 | 50 / 91 | 57 / 91 | 35 / 91 | 45 / 91 | 34 / 91 | 51 / 91 |
| SL | 52 / 91 | 56 / 91 | 52 / 88 | 58 / 91 | 34 / 91 | 44 / 91 | 34 / 88 | 51 / 91 |
| S2-ID | 36 / 91 | 39 / 91 | 36 / 88 | 41 / 91 | 21 / 91 | 29 / 91 | 20 / 88 | 35 / 91 |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 8 — Pre-registered hypotheses (Holm over 8 primary contrasts, one-sided bound at the contrast's Holm level) (data: MPBench v4 split (reused), GPT-4o-mini; reused MPBench v4 split: replication evidence, not fresh held-out; 24 groups)

**Evidence: replication, not confirmatory.** The pre-registered rules are applied unchanged, but the data are not fresh held-out data, so ✓/✗ are not confirmatory tests.

| Contrast | Part (level) | Population | Estimate [95% CI] | Bound @ Holm level | Margin | Holm p | Decision |
|---|---|---|---|---|---|---|---|
| H1 vs C | key_strict_utility S − C (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − C (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H1 vs M | key_strict_utility S − M (answer-level) | localized | +90 [+83, +95] | +82 | > +3 | <0.0001 | ✓ |
|  | judge_asr S − M (answer-level) | localized | 0 [0, 0] | 0 | < +5 |  |  |
| H2 | judge_asr S − M (answer-level) | distributed | 0 [0, 0] | 0 | < +5 | <0.0001 | ✓ |
| H3 | target_asr S − a_memguard (answer-level) | localized | −49 [−58, −40] | −37 | < 0 | <0.0001 | ✓ |
|  | target_asr S − memlineage (answer-level) | localized | −44 [−54, −33] | −31 | < 0 |  |  |
|  | target_asr S − llm_sanitiser (answer-level) | localized | −56 [−67, −47] | −45 | < 0 |  |  |
|  | target_asr S − randec (answer-level) | localized | −62 [−73, −53] | −51 | < 0 |  |  |
| H4 | target_asr S2-ID − S (answer-level) | sybil_k4, sybilown_k4, launder_r4, launder_r3_rand, sybilown_k4_rand | −14 [−20, −9] | −8 | < 0 | <0.0001 | ✓ |
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
| H5 | relay_target_asr SL − S (answer-level) | localized | −54 [−75, −33] | −33 | < 0 | <0.0001 | ✓ |
| H6 vs C | not tested (primary did not pass) | | | | | | |
| H6 vs M | not tested (primary did not pass) | | | | | | |

*n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*

## Table 7 — Generalization (answer-level; best published = MemLineage, best internal = C, pre-specified on the first measured row; data: reused MPBench v4 split: replication evidence, not fresh held-out)

| Data | S: target ASR / strict utility | Best published: target ASR / strict utility | Best internal: target ASR / strict utility | S − best published, target ASR [95% CI] | S − best internal, strict utility [95% CI] |
|---|---|---|---|---|---|
| Fresh v5, GPT-4o-mini | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) |
| Fresh v5, Claude Haiku | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) | not run (needs fresh v5 data) |
| MPBench v4 split (reused), GPT-4o-mini | 0 / 91 | 44 / 91 | 0 / 66 | −44 [−54, −33] | +25 [+23, +27] |
| MPBench v4 split (reused), Claude Haiku | 0 / 91 | 17 / 91 | 0 / 66 | −17 [−22, −11] | +25 [+23, +27] |
| MPBench v4 split (reused), Gemini 3.1 Flash-Lite (post-hoc) | 0 / 91 | 44 / 91 | 0 / 66 | −44 [−54, −33] | +25 [+23, +27] |

*MPBench v4 split (reused), GPT-4o-mini: n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*
*MPBench v4 split (reused), Claude Haiku: n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*
*MPBench v4 split (reused), Gemini 3.1 Flash-Lite (post-hoc): n = 24 groups; probes: 96 scored-attack, 24 unlinked-relay, 24 linked-copy, 600 utility, 96 principal-utility. Each value is the mean over groups of per-group rates (random-audit draws averaged within a group first).*
