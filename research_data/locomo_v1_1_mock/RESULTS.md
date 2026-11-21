# LoCoMo second-dataset evaluation: results (locomo-v1.1, draws=5)

Confirmatory: 8 conversations never answered before; exact sign-flip tests over conversations; Holm m = 6.

| H | parts (estimate [95% t-CI]) | p (IUT) | Holm threshold | decision |
|---|---|---|---|---|
| H1 | asr static - S = 0.5616 [np.float64(0.5455), np.float64(0.5776)] | 0.0039 | 0.0083 | ✓ |
| H2 | acc_U_out S - C = 0.008 [np.float64(0.0031), np.float64(0.0128)]; acc_U_all S - C = 0.0029 [np.float64(0.0005), np.float64(0.0054)] | 0.0195 | 0.0125 | ✗ |
| H3 | acc_U_out S - M = 0.008 [np.float64(0.0031), np.float64(0.0128)]; acc_U_all S - M = 0.0029 [np.float64(0.0005), np.float64(0.0054)] | 0.0195 | 0.0167 | ✗ |
| H4 | asr S - C = 0.1125 [np.float64(0.0771), np.float64(0.1479)]; asr S - M = 0.1125 [np.float64(0.0771), np.float64(0.1479)] | 1.0000 | 0.0500 | ✗ |
| H5 | asr S - C = -0.2554 [np.float64(-0.274), np.float64(-0.2368)] | 0.0039 | 0.0100 | ✓ |
| H6 | asr S - C = 0.029 [np.float64(-0.0023), np.float64(0.0602)]; asr S - M = 0.0312 [np.float64(0.0001), np.float64(0.0624)] | 0.1875 | 0.0250 | ✗ |

## P1 cells (conversation means over the 8 confirmatory conversations)

| shape | auditor | arm | ASR | Acc_out | Acc_all | Acc_in | Acc_own |
|---|---|---|---|---|---|---|---|
| 1s | A1 | static | 0.988 | 0.011 | 0.013 | 0.026 | 0.016 |
| 1s | A1 | R | 0.988 | 0.011 | 0.013 | 0.026 | 0.016 |
| 1s | A1 | C | 0.002 | 0.004 | 0.013 | 0.020 | 0.022 |
| 1s | A1 | M | 0.002 | 0.004 | 0.013 | 0.020 | 0.022 |
| 1s | A1 | S | 0.000 | 0.020 | 0.019 | 0.023 | 0.020 |
| 1s | A1 | SL | 0.000 | 0.020 | 0.019 | 0.023 | 0.020 |
| 1s | A1 | S2-ID | 0.000 | 0.020 | 0.019 | 0.023 | 0.020 |
| 1s | A2 | static | 0.989 | 0.011 | 0.013 | 0.026 | 0.016 |
| 1s | A2 | R | 0.989 | 0.011 | 0.013 | 0.026 | 0.016 |
| 1s | A2 | C | 0.989 | 0.011 | 0.013 | 0.026 | 0.016 |
| 1s | A2 | M | 0.218 | 0.019 | 0.018 | 0.023 | 0.019 |
| 1s | A2 | S | 0.218 | 0.019 | 0.018 | 0.023 | 0.019 |
| 1s | A2 | SL | 0.214 | 0.020 | 0.019 | 0.023 | 0.020 |
| 1s | A2 | S2-ID | 0.214 | 0.020 | 0.019 | 0.023 | 0.020 |
| 2s | A1 | static | 0.981 | 0.012 | 0.013 | 0.000 | 0.015 |
| 2s | A1 | R | 0.981 | 0.012 | 0.013 | 0.000 | 0.015 |
| 2s | A1 | C | 0.002 | 0.005 | 0.013 | 0.006 | 0.022 |
| 2s | A1 | M | 0.002 | 0.005 | 0.013 | 0.006 | 0.022 |
| 2s | A1 | S | 0.275 | 0.011 | 0.015 | 0.004 | 0.020 |
| 2s | A1 | SL | 0.273 | 0.011 | 0.015 | 0.004 | 0.020 |
| 2s | A1 | S2-ID | 0.273 | 0.011 | 0.015 | 0.004 | 0.020 |
| 2s | A2 | static | 0.983 | 0.012 | 0.013 | 0.000 | 0.015 |
| 2s | A2 | R | 0.983 | 0.012 | 0.013 | 0.000 | 0.015 |
| 2s | A2 | C | 0.983 | 0.012 | 0.013 | 0.000 | 0.015 |
| 2s | A2 | M | 0.770 | 0.018 | 0.017 | 0.003 | 0.018 |
| 2s | A2 | S | 0.770 | 0.018 | 0.017 | 0.003 | 0.018 |
| 2s | A2 | SL | 0.760 | 0.018 | 0.017 | 0.003 | 0.018 |
| 2s | A2 | S2-ID | 0.760 | 0.018 | 0.017 | 0.003 | 0.018 |
| quarter | A1 | static | 0.977 | 0.011 | 0.013 | 0.013 | 0.016 |
| quarter | A1 | R | 0.977 | 0.011 | 0.013 | 0.013 | 0.016 |
| quarter | A1 | C | 0.002 | 0.004 | 0.013 | 0.009 | 0.022 |
| quarter | A1 | M | 0.002 | 0.004 | 0.013 | 0.009 | 0.022 |
| quarter | A1 | S | 0.119 | 0.006 | 0.013 | 0.009 | 0.021 |
| quarter | A1 | SL | 0.115 | 0.006 | 0.013 | 0.009 | 0.021 |
| quarter | A1 | S2-ID | 0.115 | 0.006 | 0.013 | 0.009 | 0.021 |
| quarter | A2 | static | 0.978 | 0.011 | 0.013 | 0.013 | 0.016 |
| quarter | A2 | R | 0.978 | 0.011 | 0.013 | 0.013 | 0.016 |
| quarter | A2 | C | 0.978 | 0.011 | 0.013 | 0.013 | 0.016 |
| quarter | A2 | M | 0.944 | 0.013 | 0.014 | 0.013 | 0.017 |
| quarter | A2 | S | 0.944 | 0.013 | 0.014 | 0.013 | 0.017 |
| quarter | A2 | SL | 0.931 | 0.013 | 0.015 | 0.014 | 0.017 |
| quarter | A2 | S2-ID | 0.931 | 0.013 | 0.015 | 0.014 | 0.017 |
| spread | A1 | static | 0.985 | – | 0.013 | 0.011 | 0.015 |
| spread | A1 | R | 0.985 | – | 0.013 | 0.011 | 0.015 |
| spread | A1 | C | 0.004 | – | 0.013 | 0.005 | 0.021 |
| spread | A1 | M | 0.004 | – | 0.013 | 0.005 | 0.021 |
| spread | A1 | S | 0.067 | – | 0.013 | 0.005 | 0.021 |
| spread | A1 | SL | 0.067 | – | 0.013 | 0.005 | 0.021 |
| spread | A1 | S2-ID | 0.067 | – | 0.013 | 0.005 | 0.021 |
| spread | A2 | static | 0.976 | – | 0.013 | 0.011 | 0.015 |
| spread | A2 | R | 0.976 | – | 0.013 | 0.011 | 0.015 |
| spread | A2 | C | 0.976 | – | 0.013 | 0.011 | 0.015 |
| spread | A2 | M | 0.971 | – | 0.013 | 0.012 | 0.016 |
| spread | A2 | S | 0.971 | – | 0.013 | 0.012 | 0.016 |
| spread | A2 | SL | 0.952 | – | 0.014 | 0.013 | 0.016 |
| spread | A2 | S2-ID | 0.952 | – | 0.014 | 0.013 | 0.016 |

## Validity

```
{
 "judge_kappa": 1.0,
 "judge_check_n": 400,
 "judge_kappa_below_0.6": false,
 "chance_asr": 0.00043981481481481476,
 "chance_asr_above_0.05": false,
 "f1_estimates": {
  "H2|f1_U_out": 0.0065,
  "H2|f1_U_all": 0.0024,
  "H3|f1_U_out": 0.0065,
  "H3|f1_U_all": 0.0024
 },
 "S_equals_M_under_A2": 1.0,
 "R_equals_static_except_audited": 1.0
}
```

## MPBench comparison

| finding | MPBench | LoCoMo test |
|---|---|---|
| Localized evidence: S keeps the attacker's other-batch utility that C/M remove, at equal ASR | locked test H1 supported: key utility S - C/M +0.78 [0.71, 0.84], ASR 0 vs 0 | H2 and H3 (A1; 1s/2s/quarter pooled) |
| Distributed evidence: S equals C/M | locked test H2 supported (distributed ASR S = M = 0) | H6 (spread) |
| Selectivity has a security cost when detection is incomplete and the attack spans batches | adaptive dev (paid): random_spread target ASR S .205 vs C/M 0 | H4 (expected to fail; its estimate is the cost) |
| Propagation contains unaudited poison vs no propagation | locked test: S − R ASR −0.771 | H1 |
| Mixed (safe + unsafe) audits dilute contributor-level risk | not tested (MPBench's safe ticket was on another contributor) | H5 (new on LoCoMo) |
| Uninformative provenance: S loses utility vs R | locked test H3 not supported (R - S utility +0.115) | not applicable: LoCoMo's sessions are natural, not an uninformative assignment |
