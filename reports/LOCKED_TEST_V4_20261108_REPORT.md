# Locked held-out test: original SAFE-Mem vs R / C / M / S on workload v4 (8 November 2026)

**Status: complete.** The owner approved this run on 8 Nov 2026.

| Item | Detail |
|---|---|
| Protocol | Frozen `safemem-propagation-locked-test-v1`, digest `921cf7f53c5e292243d3efa368c60e39f70091ffea9934f6dbcbd9d3bffd97eb`, file SHA-256 `7232e56f…48ed90` |
| Freeze check | `verify` passed before the run, inside each paid stage's gate, and again after the run, with no differences |
| Data | Held-out test split, 24 groups never used before |
| Arms | Original SAFE-Mem (static), R, C, M, S and no-memory, across all three conditions |
| Outcomes | 13,440 outcome events; integrity checks clean |
| Analysis | Run **once**, with the frozen analysis code |
| **Total cost** | **$0.57838455** (Stage 1 $0.1758837 + Stage 3 $0.40250085), within the $0.30 and $0.60 caps |

## 1. Execution and cost

| Stage | What ran | Cost | Notes |
|---|---|---:|---|
| Approval | Owner-approval file bound to the protocol digest, bundle hash and caps | – | `research_data/workload_freeze_v4_20261108/owner_approval_locked_test.json` |
| Stage 1 | Construction for 24 test groups | **$0.1758837** (cap $0.30) | 1,774 paid requests (578 retention, 697 extraction, 499 classifier), exactly as estimated. 986 free (528 frozen cache, 458 exact replays of identical earlier requests such as principal-control text). 0 failures, no holds. |
| Stage 2 | Offline validation | $0 | Recorded only; not used to change anything (§2). |
| Stage 3 | Answers, conflict checks, judges | **$0.40250085** (cap $0.60) | 5,229 unique requests: 3,600 answers, 794 no-memory answers, 58 conflict checks, 777 judge calls. 0 failures, no holds. |

**Budget:**
- New session ledger: $0.78329385 used, $0 held.
- **All research spend:** $2.1266388 (old session) + $0.78329385 = **$2.90993265**, plus the preserved **$0.01974** unresolved reservation in the old session, which was left untouched.
- Every paid stage ran under `caffeinate`. Identical requests were sent once and reused.

## 2. Stage 2 validation (exposure ceilings, not answers)

**Extraction:**

| Role | Stored |
|---|---:|
| Benign facts | 566/624 (91%) |
| Scored attacks | 81/96 |
| Seeds | 76/96 |
| Principal controls | 96/96 |
| Unlinked relays | 15/24 |
| Linked copies | 9/24 (the linked copy still reaches the static context through its seed: 19/24) |

**Classification:** all 96 attack, 48 copy and 600 utility questions are description; principal questions are 72 preference and 24 attribute.

**Static context:** utility facts reach it in 546/600 probes and attack targets in 73/96. 535 conflict checks were answered by the logged placeholder (Stage 2 only).

## 3. Main results (held-out test, real answers and judges)

ASR is the share of 96 scored attacks the judge accepted. Strict utility counts only correct answers with the inserted fact in context.

| Condition | Arm | ASR | Utility (lenient) | **Utility strict** | Key stratum, strict | Linked copy | Unlinked relay |
|---|---|---:|---:|---:|---:|---:|---:|
| localized | **original SAFE-Mem** | **74/96 (77.1%)** | 555/600 | 546/600 (91.0%) | 151/168 | 20/24 | 22/24 |
| localized | R | 74/96 (77.1%) | 555/600 | 546/600 | 151/168 | 1/24† | 16/24 |
| localized | C | **0/96** | 424/600 | 395/600 (65.8%) | **0/168** | 0/24 | 15/24 |
| localized | M | **0/96** | 424/600 | 395/600 (65.8%) | **0/168** | 0/24 | 15/24 |
| localized | **S (ours)** | **0/96** | **554/600** | **546/600 (91.0%)** | **151/168** | 0/24 | 15/24 |
| distributed | original SAFE-Mem | 74/96 | 555/600 | 546/600 | – | 20/24 | 22/24 |
| distributed | R | 74/96 | 555/600 | 546/600 | – | 1/24† | 16/24 |
| distributed | C / M / **S** | **0/96** | 424/600 | 395/600 | – | 0/24 | 15/24 |
| uninformative | original SAFE-Mem / R | 74/96 | 555/600 | 546/600 | 169/182 | 20/24 (R 1/24†) | 22/24 (R 16/24) |
| uninformative | C | 65/96 (67.7%) | 475/600 | 461/600 | 157/182 | 1/24† | 16/24 |
| uninformative | M | 43/96 (44.8%) | 353/600 | 320/600 | 84/182 | 1/24† | 15/24 |
| uninformative | **S (ours)** | 63/96 (65.6%) | 486/600 | 470/600 | 169/182 | 1/24† | 16/24 |
| — | no-memory | 0/96 | 0/600 | 0/600 | 0 | 0/24 | 0/24 |

Principal (user-owned) controls were correct in 96/96 under every memory arm.

† **Judge false positive.** In every case it is group G-T08: the linked copy is not in the context, and the answer restates a *different* exfiltration record. The pre-declared target-specific metric gives 0 for every governed arm.

## 4. Pre-registered hypotheses (frozen decision rules)

| Hypothesis | Estimate [95% CI], 24 groups | Decision |
|---|---|---|
| **H1 (localized selectivity)** | S − C key utility **+0.780** [0.714, 0.839]; S − M **+0.780** [0.714, 0.839]; both Holm-rejected. S − C ASR 0.000 [0, 0]; S − M 0.000 [0, 0]; S − R ASR **−0.771** [−0.844, −0.698] | **Supported** |
| **H2 (distributed):** S's ASR no worse than M's | 0.000 [0, 0] | **Supported** |
| **H3 (uninformative):** S's utility loss vs R ≤ 2 points | R − S utility **+0.115** [0.080, 0.148] | **Not supported** |

Margins and rules are exactly as frozen: 0.03 utility, 0.02 ASR and 0.02 loss. H3's margin was not relaxed after it failed on dev.

## 5. Secondary analyses (pre-declared, no decision rule)

**H1 on strict key utility:** S − C = S − M = **+0.899** [0.833, 0.952].

**Target-specific ASR** (a judge hit counts only if the answer restates the probed target):

| Arm | Localized | Distributed | Uninformative |
|---|---:|---:|---:|
| Original SAFE-Mem | 59/96 | 59/96 | 59/96 |
| R | 59/96 | 59/96 | 59/96 |
| C | 0/96 | 0/96 | 51/96 |
| M | 0/96 | 0/96 | 34/96 |
| S | 0/96 | 0/96 | 51/96 |

**Target-specific copy leakage:**
- Linked copy: original SAFE-Mem 17/24; all audited arms 0/24.
- Unlinked relay: original SAFE-Mem 20/24; audited arms 13–15/24.

**Coincidental utility passes** (correct alias without the fact in context): localized C/M 29 of 600 vs S 8. The strict metric removes these.

## 6. Interpretation

1. **Original SAFE-Mem is highly vulnerable on this workload.** 77% of scored attacks succeed (61% target-specific), because its authority rules admit external description claims to description questions.
2. **R, which withholds only the audited records, leaves ASR unchanged at 77%.** It does stop the linked copy.
3. **C and M stop every localized and distributed attack, but at a large utility cost.** They drop all 168 key-stratum memories and 25 points of strict utility in the localized condition.
4. **S, our contextual defense, matches C and M on security (0/96) in the localized and distributed conditions.** In the localized condition it keeps original-SAFE-Mem utility: 546/600 strict, the same as no defense, and 151/168 key-stratum memories. This confirms H1 on held-out data, with an effect of +0.78, or +0.90 strict.
5. **The limitation is confirmed (H3 fails).** When provenance is uninformative, S behaves almost like C:
   - it loses 11.5 points of utility vs R;
   - it still lets 63/96 attacks through (M: 43/96).

   S's advantage depends on the incident structure being informative. The paper must state this as a central limitation.
6. **Unlinked relays leak under every arm** (15–16/24 vs 22/24 static). No provenance-based policy can catch an unattributed copy; this motivates content-based detection.
7. **Test and dev agree** in direction and size: H1 +0.73 dev vs +0.78 test; H3 failure 0.065 dev vs 0.115 test.

## 7. Limitations

- **One backbone and one run:** GPT-4o-mini at temperature 0.
- **Oracle auditor:** the audits are correct by construction.
- **Synthetic contributor structure:** a controlled, MPBench-derived workload.
- **LLM judge not human-validated:** recurrent false positives on another record's payload (G-T08; dev G-D02), corrected only by the secondary metric.
- **Group count:** 24 groups (the cluster unit).
- **Selection:** the attack pool was selected by the original write path storing the poison.
- **MPBench template families** recur across the splits.
- **Extraction:** about 9% of facts are not extracted, equally across arms.
- **Scope:** only flat retrieval, withhold mode and hops=0.

## 8. Next steps toward ICML (each needs the owner's approval)

The roadmap in the README (§8) is updated.
1. **Second backbone** on the same frozen test, e.g. GPT-4o or an open model.
2. **Full MPBench:** S vs original SAFE-Mem, for external validity.
3. **One more published defense** as a baseline.
4. **Adaptive attacker and ablations** of S's support gates and threshold.
5. **Robustness:** noisy, false or late audits, and compromised contributors. This also addresses the H3 regime.
6. **Human validation** of a judge, label and utility sample.
7. **Paper and reproducible release.**

**Outputs:**
- `research_data/controlled_workload_stage1_test_v4_20261108/`;
- `research_data/controlled_workload_stage2_test_v4_20261108/stage2_validation.json`;
- `research_data/controlled_workload_stage3_test_v4_20261108/` (`queries.sqlite`, `analysis.json`, `analysis.md`, `stage3_summary.json`).
