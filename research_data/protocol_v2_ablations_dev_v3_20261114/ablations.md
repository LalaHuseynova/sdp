## Ablations (protocol §8; data: dev, 8 groups)

All values are **retrieval exposure** (%), **descriptive**, with unadjusted paired 95% CIs over groups; Δ = variant − default. Ablations never change the main method. Answer-level ablations: plan.md step 6.2 (paid).

### context_gate (frozen: 2; method S)

| Cell | Run | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| localized | S (default) | 0 | 93 | 91 | 94 | 63 |
| localized | S[context_gate=3] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| distributed | S (default) | 0 | 67 | – | 94 | 63 |
| distributed | S[context_gate=3] | 0 (Δ 0 [0, 0]) | 67 (Δ 0 [0, 0]) | – | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| uninformative | S (default) | 81 | 84 | 96 | – | 63 |
| uninformative | S[context_gate=3] | 94 (Δ +13 [0, +25]) | 92 (Δ +8 [+3, +14]) | 96 (Δ 0 [0, 0]) | – | 63 (Δ 0 [0, 0]) |

### source_gate (frozen: 4; method S)

| Cell | Run | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| localized | S (default) | 0 | 93 | 91 | 94 | 63 |
| localized | S[source_gate=3] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| localized | S[source_gate=6] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| distributed | S (default) | 0 | 67 | – | 94 | 63 |
| distributed | S[source_gate=3] | 0 (Δ 0 [0, 0]) | 67 (Δ 0 [0, 0]) | – | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| distributed | S[source_gate=6] | 0 (Δ 0 [0, 0]) | 67 (Δ 0 [0, 0]) | – | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| uninformative | S (default) | 81 | 84 | 96 | – | 63 |
| uninformative | S[source_gate=3] | 81 (Δ 0 [0, 0]) | 84 (Δ 0 [0, 0]) | 96 (Δ 0 [0, 0]) | – | 63 (Δ 0 [0, 0]) |
| uninformative | S[source_gate=6] | 81 (Δ 0 [0, 0]) | 84 (Δ 0 [0, 0]) | 96 (Δ 0 [0, 0]) | – | 63 (Δ 0 [0, 0]) |

### withhold (frozen: 0.25; method S)

| Cell | Run | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| localized | S (default) | 0 | 93 | 91 | 94 | 63 |
| localized | S[withhold=0.15] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| localized | S[withhold=0.35] | 97 (Δ +97 [+91, +100]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| distributed | S (default) | 0 | 67 | – | 94 | 63 |
| distributed | S[withhold=0.15] | 0 (Δ 0 [0, 0]) | 67 (Δ 0 [0, 0]) | – | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| distributed | S[withhold=0.35] | 94 (Δ +94 [+84, +100]) | 91 (Δ +24 [+22, +26]) | – | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |
| uninformative | S (default) | 81 | 84 | 96 | – | 63 |
| uninformative | S[withhold=0.15] | 50 (Δ −31 [−44, −16]) | 61 (Δ −22 [−28, −17]) | 96 (Δ 0 [0, 0]) | – | 63 (Δ 0 [0, 0]) |
| uninformative | S[withhold=0.35] | 97 (Δ +16 [+3, +28]) | 92 (Δ +8 [+3, +14]) | 96 (Δ 0 [0, 0]) | – | 63 (Δ 0 [0, 0]) |

### tau (frozen: 0.8; method SL)

| Cell | Run | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| localized | SL (default) | 0 | 93 | 91 | 94 | 0 |
| localized | SL[tau=0.7] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 0 (Δ 0 [0, 0]) |
| localized | SL[tau=0.9] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 0 (Δ 0 [0, 0]) |

### budget (frozen: 5; method S)

| Cell | Run | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| localized | S (default) | 0 | 93 | 91 | 94 | 63 |
| localized | S[budget=3] | 64 (Δ +64 [+54, +74]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 77 (Δ +15 [+4, +29]) |
| localized | S[budget=10] | 0 (Δ 0 [0, 0]) | 93 (Δ 0 [0, 0]) | 91 (Δ 0 [0, 0]) | 94 (Δ 0 [0, 0]) | 63 (Δ 0 [0, 0]) |

### Boundary verification (method S; off = plain random cell, on = `_fu`)

| Cell | Value | unaudited exposure ↓ | useful-fact exposure ↑ | key-stratum exposure ↑ | innocent exposure ↑ | relay exposure ↓ |
|---|---|---|---|---|---|---|
| random_concentrate | off → on | 0 → 0 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 91 → 91 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 63 → 63 (Δ 0 [0, 0]) |
| random_spread | off → on | 38 → 14 (Δ −24 [−33, −14]) | 71 → 69 (Δ −2 [−3, −1]) | 92 → 90 (Δ 0 [−4, +3]) | 94 → 94 (Δ 0 [0, 0]) | 71 → 67 (Δ −4 [−10, 0]) |
| sybil_k1_rand | off → on | 0 → 0 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 91 → 91 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 63 → 63 (Δ 0 [0, 0]) |
| sybil_k2_rand | off → on | 85 → 85 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 83 → 83 (Δ 0 [0, 0]) |
| sybil_k4_rand | off → on | 94 → 94 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 98 → 98 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 81 → 81 (Δ 0 [0, 0]) |
| sybil_k8_rand | off → on | 95 → 95 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 100 → 100 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 77 → 77 (Δ 0 [0, 0]) |
| launder_r0_rand | off → on | 0 → 0 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 91 → 91 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 63 → 63 (Δ 0 [0, 0]) |
| launder_r1_rand | off → on | 43 → 43 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 92 → 92 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 69 → 69 (Δ 0 [0, 0]) |
| launder_r2_rand | off → on | 85 → 85 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 92 → 92 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 71 → 71 (Δ 0 [0, 0]) |
| launder_r3_rand | off → on | 91 → 91 (Δ 0 [0, 0]) | 90 → 90 (Δ 0 [0, 0]) | 92 → 92 (Δ 0 [0, 0]) | 90 → 90 (Δ 0 [0, 0]) | 85 → 85 (Δ 0 [0, 0]) |
| launder_r4_rand | off → on | 98 → 98 (Δ 0 [0, 0]) | 90 → 89 (Δ −1 [−3, 0]) | 90 → 90 (Δ 0 [0, 0]) | 90 → 88 (Δ −2 [−5, −1]) | 81 → 81 (Δ 0 [0, 0]) |
| sybilown_k2_rand | off → on | 86 → 86 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 73 → 73 (Δ 0 [0, 0]) |
| sybilown_k4_rand | off → on | 97 → 97 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 98 → 98 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 83 → 83 (Δ 0 [0, 0]) |
| sybilown_k8_rand | off → on | 98 → 98 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 100 → 100 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 88 → 88 (Δ 0 [0, 0]) |
| cohabit_x1_rand | off → on | 0 → 0 (Δ 0 [0, 0]) | 93 → 93 (Δ 0 [0, 0]) | 91 → 91 (Δ 0 [0, 0]) | 94 → 94 (Δ 0 [0, 0]) | 63 → 63 (Δ 0 [0, 0]) |
