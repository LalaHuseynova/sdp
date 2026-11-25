# LoCoMo v2: results (frozen protocol, single analysis, 23 Nov 2026)

**Protocol:** `reports/PROTOCOL_LOCOMO_V2.md`. The freeze (`3a2c2df8…`) was verified before and after the run.

**Supplementary note:** pre-registered and hashed before unblinding (manifest `4742a448…`).

**Execution** (`reports/LOCOMO_V2_EXECUTION_ADDENDUM.md`):
- owner-approved, $40 cap, reuse of the cached answers;
- conv-48 canary first, then the other nine conversations;
- 16:55–19:02 UTC;
- all 10 conversations complete, 117,713 answer keys, 0 failed calls, 0 pauses.

**Spend:** $9.55 (estimate $10.24); $0 held at the end.

**Analysis:** the frozen `locomo_v2.analysis`, run once on the 8 held-out conversations, then `locomo_v2_supp.supplementary`.

**Outputs:** `research_data/locomo_v2/run/analysis.json` and `run/supplementary/` (the `supplementary.json`, the all-10 secondary analysis and `forest_primary.png`).

## 1. Primary hypotheses (held-out, n = 8 conversations; Holm over 7 contrasts)

| # | Contrast | Estimate [95% t-CI] | k/8 favourable | Exact CI (S1) | Holm p (level) | Decision | MPBench |
|---|---|---|---|---|---|---|---|
| H1 vs C | acc_U_out S − C > +3 pt | **+37.4 pt** [31.9, 43.0] | 8/8 | [31.2, 43.3] | .0039 (.0071) | ✓ | ✓ |
| | ASR S − C < +5 pt | 0.0 | 8/8 | identical in 8/8 | | | |
| H1 vs M | the same vs M | +37.4 pt; ASR 0.0 | 8/8 | as above | .0039 (.0083) | ✓ | ✓ |
| H2 | ASR S − M < +5 pt (spread) | **+2.1 pt** [−0.4, 4.6] | 7/8 | [0.0, 4.8] | .0195 (.05) | ✓ | ✓ |
| H3 | ASR S − MemLineage < 0; S − RandEC < 0 | **−49.1 pt** [−56.2, −42.0] (each) | 8/8 | [−57.5, −41.8] | .0039 (.01) | ✓ | ✓ |
| H5 | relay exposure SL − S < 0 | **−100 pt** | 8/8 | identical in 8/8 | .0039 (.0125) | ✓ | ✓ (GPT) |
| | acc_U_all SL − S > −5 pt | +0.2 pt [−0.1, 0.6] | 8/8 | [−0.1, 0.6] | | | |
| H6 vs C | acc_U_ext S − C > 0 (2 false flags in one session) | **+36.1 pt** [31.1, 41.1] | 8/8 | [30.7, 41.0] | .0039 (.0167) | ✓ | ✗ (fp1: not a test) |
| H6 vs M | the same vs M | +36.1 pt | 8/8 | as above | .0039 (.025) | ✓ | ✗ (fp1: not a test) |

**All 7 primary contrasts reject** after Holm.
- **All-10 secondary analysis (S4):** the same 7 decisions, with p ≤ .0049.
- **H2's dissenting conversation:** conv-41, where S − M = +8.3 pt. It is the only one of the 8 above the 5-point margin.

**Validity (§10, S5):**
- **Chance ASR:** 0.00 in the primary cells, so no flag.
- **F1 sign:** consistent for H1 and H6. **Flag: H5's utility part.** The judge-accuracy difference (+0.2 pt) and the F1 difference (−0.1 pt) differ in sign. Both are within ±0.6 pt of zero, so the non-inferiority conclusion (margin −5 pt) holds under either metric. Per §10 it is reported as flagged.
- **Identities (build tests):** all passed. S2-ID equals SL in every cell, and MemLineage equals no defence.

**Retrieval vs answer (S3):** the same sign in 8/8 conversations for every part, except H5's utility part (6/8, where the differences are ≈ 0).

## 2. Estimation (held-out means over 8 conversations; ASR / acc_U_out)

| Cell | No defence | R | C | M | S | SL / S2-ID | MemLineage / RandEC |
|---|---|---|---|---|---|---|---|
| loc 1s, A1 | .50 / .47 | .50 / .47 | .00 / .11 | .00 / .11 | **.00 / .49** | .00 / .49 | .50 / .47 |
| loc 2s, A1 | .45 / .48 | .45 / .48 | .00 / .11 | .00 / .11 | .13 / .31 | .13 / .31 | .45 / .48 |
| loc quarter, A1 | .44 / .48 | .44 / .48 | .00 / .12 | .00 / .12 | .05 / .19 | .05 / .19 | .44 / .48 |
| loc spread, A1 | .46 | .46 | .00 | .00 | .02 | .02 | .46 |
| loc 1s, A2 (review) | .51 / .47 | .51 | **.51** / .47 | .10 / .48 | .10 / .48 | .10 / .49 | .51 |
| loc spread, A2 | .42 | .42 | .42 | .42 | .42 | .41 | .42 |
| fn20, 1s | .50 / .47 | .50 | .21 / .26 | .21 / .26 | .21 / .48 | .21 / .48 | – |
| Sybil k = 2 | .45 / .48 | .45 | .38 / .36 | .38 / .36 | .33 / .48 | .33 / .48 | – |
| Sybil k = 4 | .43 / .48 | .43 | .42 / .44 | .42 / .44 | .40 / .48 | .40 / .48 | – |
| shift (audit-aware) | .47 / .48 | .47 | .00 / .11 | .00 / .11 | **.47** / .48 | .46 / .48 | – |
| relay r = 1, relay ASR | .61 / .46 | .47 | .70 / .11 | .70 / .11 | .46 / .47 | **.00** / .48 | – |

Net utility (acc_U_all), loc 1s A1: none .47, C/M .31, **S .47**, SL .47.

**Framing** (accused speaker's utility, acc_U_ext):

| Kind | No defence | C / M | S | SL |
|---|---|---|---|---|
| fp1 (one false flag) | .49 | .44 | .48 | .48 |
| fp2c (two flags, one session) | .49 | .11 | **.48** | .47 |
| fp2s (two flags, two sessions) | .49 | .11 | .11 | .11 |

## 3. What transfers from MPBench (transfer rule, protocol §9)

| MPBench finding | LoCoMo |
|---|---|
| Localized: S keeps utility at C/M security (H1) | **Transfers**: +37 pt on the attacker's out-of-window evidence, 0 ASR cost, 8/8. *Answer-level confirmation of a retrieval-level mechanism.* |
| Distributed: S ≈ M (H2) | **Transfers**: +2.1 pt; 7/8 within the margin; conv-41 +8.3 |
| S beats the published defences (H3) | **Transfers, with caveats.** On LoCoMo, MemLineage never fires (0 sensitive questions) and RandEC flags nothing, so H3 here is S vs effectively no defence. S also uses audits that they do not |
| SL removes relays at no utility cost (H5) | **Transfers**: relay exposure 1.00 → 0, utility unchanged; the F1 sign flag is noted |
| Innocent protection under false accusation (H6) | **New positive** (not testable on MPBench's fp1): two false flags in one session: S .48 vs C/M .11. With flags in two sessions, S escalates to C/M (.11) |
| Partial localization costs security | **Reproduced**: S's ASR .13 (2 sessions), .05 (quarter), .02 (spread), with utility falling .49 → .31 → .19 |
| Audit-aware shift breaks S | **Reproduced**: S .47 = no defence, vs C/M 0 |
| Sybils defeat label-based rules | **Reproduced**: k = 2: S .33, C/M .38 (none .45); k = 4: all ≈ none |
| Imperfect audits (fn20) | **Reproduced**: equal ASR (.21) for C, M, S; S keeps utility (.48 vs .26) |
| (new) Review dilution | Safe reviews disable C entirely (= none); S = M; nothing contains spread poison |
| S2-ID hybrid | **Not testable** on LoCoMo (≡ SL by construction) |

## 4. Limits (protocol §12, unchanged)

- 8 held-out conversations: LLM-generated and human-edited (third-party, not designed by us).
- One constructed attack template; oracle tickets.
- Turn-level retrieval, not SAFE-Mem's claim store.
- No contributor gate; no sensitive actions.
- The Haiku κ re-judge was not run (optional in the protocol).
- H1, H5 and H6 are largely retrieval-determined: the answer level confirms that the model uses the evidence.
