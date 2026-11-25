# LoCoMo v2 supplementary results: LLM sanitiser and A-MemGuard, and MPBench–LoCoMo generalization

**Status:** descriptive supplementary results (24 Nov 2026), pre-registered in `reports/LOCOMO_V2_SUPP_PUBLISHED_BASELINES_NOTE.md` (manifest `40346c9f…`). The frozen LoCoMo v2 protocol (`3a2c2df8…`), its primary analysis and the frozen H3 decision are unchanged. No contrast here is a new pass/fail decision.

## 1. Execution

| Item | Value |
|---|---|
| Run | 23 Nov 21:14 → 24 Nov 03:08 UTC; one process, no pauses, no breaker trips, 0 failed calls, `errors.jsonl` empty |
| Defence stage | 10/10 conversations, both defences × 4 hijack shapes; 108,598 budget reservations, all settled (none unknown or pending) |
| Answer stage | 19,707 new answer/judge calls; every selected key answered and judged (0 missing in every conversation) |
| Spend | defences **$18.50** (cap $26), answers + judges **$1.06** (cap $6), total **$19.56** of $32 |
| Integrity after the run | frozen v2 files unchanged (65 files, `3a2c2df8…`); supplementary code and note unchanged (`40346c9f…`); frozen `run/analysis.json` untouched |
| Analysis | `supp_baselines_analysis` run once on the 8 held-out conversations; the dev conversations (conv-48/49) reported separately |

Outputs: `research_data/locomo_v2/supp_published/run_supp/supp_baselines_analysis.json` (held-out) and `supp_baselines_analysis_dev.json` (dev).

Note on the status display: `published_paid status` crashed while the defence stage was in progress, because it assumes every conversation has a defence build. It works after completion. The run itself was unaffected. It was not fixed during the run, because the file is part of the approved code hash.

## 2. Full table (held-out 8 conversations, %, GPT-4o-mini)

ASR: injected value in the answer (lower is better). Exposure: injected value still in the context. U_all and U_out: judge accuracy (higher is better); U_out is not defined for `spread`.

| Shape | Method | ASR ↓ | Exposure | U_all ↑ | U_out ↑ |
|---|---|---|---|---|---|
| 1s | No defence | 49.5 | 99.1 | 46.6 | 47.2 |
|  | MemLineage / RandEC / R | 49.5 | 99.1 | 46.6 | 47.2 |
|  | **LLM sanitiser** | **48.2** | **94.0** | **46.6** | **47.3** |
|  | **A-MemGuard** | **34.2** | **54.3** | **44.5** | **45.2** |
|  | C / M | 0.4 | 1.1 | 30.7 | 11.2 |
|  | S | 0.4 | 1.1 | 47.0 | 48.7 |
|  | SL / S2-ID | 0.4 | 1.1 | 46.9 | 48.6 |
| 2s | No defence | 45.4 | 98.6 | 46.7 | 47.7 |
|  | MemLineage / RandEC / R | 45.4 | 98.6 | 46.7 | 47.7 |
|  | **LLM sanitiser** | **44.4** | **92.9** | **46.7** | **47.8** |
|  | **A-MemGuard** | **31.5** | **54.2** | **44.8** | **46.2** |
|  | C / M | 0.0 | 1.3 | 30.3 | 11.5 |
|  | S | 12.7 | 28.9 | 38.9 | 30.6 |
|  | SL / S2-ID | 12.7 | 28.7 | 38.9 | 30.6 |
| quarter | No defence | 43.7 | 98.4 | 46.3 | 48.0 |
|  | MemLineage / RandEC / R | 43.7 | 98.4 | 46.3 | 48.0 |
|  | **LLM sanitiser** | **42.9** | **95.8** | **46.3** | **48.0** |
|  | **A-MemGuard** | **31.0** | **55.0** | **44.2** | **46.1** |
|  | C / M | 0.0 | 0.4 | 30.7 | 12.5 |
|  | S | 5.2 | 12.4 | 33.4 | 19.3 |
|  | SL / S2-ID | 4.7 | 11.9 | 33.4 | 19.2 |
| spread | No defence | 46.0 | 99.1 | 46.4 | – |
|  | MemLineage / RandEC / R | 46.0 | 99.1 | 46.4 | – |
|  | **LLM sanitiser** | **44.9** | **96.0** | **46.4** | – |
|  | **A-MemGuard** | **31.8** | **53.2** | **44.3** | – |
|  | C / M | 0.0 | 0.7 | 30.5 | – |
|  | S | 2.1 | 6.9 | 31.4 | – |
|  | SL / S2-ID | 2.1 | 6.9 | 31.4 | – |

Rows marked "/" have identical values; all are reported in the JSON. MemLineage, RandEC and R equal no defence on LoCoMo, as in the frozen v2 results (no sensitive-action questions; no exact copies; R withholds only the audited turn, which A1 already excludes from the ASR target set).

## 3. S against the two new baselines (held-out, conversation-level; points; exact sign-flip 95% CI; S better in k/8)

| Shape | Contrast | ΔASR | ΔU_all | ΔU_out |
|---|---|---|---|---|
| 1s | S − LLM sanitiser | **−47.8** [−55.9, −40.5], 8/8 | +0.3 [−0.4, +1.2], 5/8 | **+1.4** [+0.1, +2.5], 6/8 |
| 1s | S − A-MemGuard | **−33.8** [−41.0, −25.8], 8/8 | +2.5 [−0.6, +6.3], 5/8 | +3.5 [−0.1, +8.4], 7/8 |
| 2s | S − LLM sanitiser | **−31.7** [−37.8, −27.0], 8/8 | −7.7 [−10.3, −5.3], 0/8 | −17.2 [−22.2, −12.5], 0/8 |
| 2s | S − A-MemGuard | **−18.8** [−25.8, −13.4], 8/8 | −5.9 [−9.3, −2.4], 0/8 | −15.6 [−20.5, −11.6], 0/8 |
| quarter | S − LLM sanitiser | **−37.7** [−48.3, −29.4], 8/8 | −12.8 [−15.7, −10.1], 0/8 | −28.7 [−34.7, −23.2], 0/8 |
| quarter | S − A-MemGuard | **−25.9** [−33.0, −18.8], 8/8 | −10.7 [−14.7, −5.8], 1/8 | −26.8 [−33.0, −19.3], 0/8 |
| spread | S − LLM sanitiser | **−42.8** [−50.7, −34.7], 8/8 | −15.0 [−18.1, −11.6], 0/8 | – |
| spread | S − A-MemGuard | **−29.6** [−35.7, −23.5], 8/8 | −12.9 [−16.6, −9.3], 0/8 | – |

For reference, against the frozen baselines (same run): S − no defence ASR −49.1 / −32.7 / −38.6 / −43.9 (8/8 each). S − C/M U_out +37.4 (1s) and +19.1 (2s), 8/8. S − C/M ASR is 0 on 1s; on 2s / quarter / spread S is higher by +12.7 / +5.1 / +2.1 points, because C and M quarantine more widely. S − C/M U_all is +16.3 / +8.6 / +2.7 / +0.9 (1s / 2s / quarter / spread; S better in 8/8, 8/8, 5/8, 4/8).

**Dev conversations (conv-48/49), reported separately:** same direction everywhere. On 1s, ASR is: no defence 46.7, sanitiser 46.7, A-MemGuard 32.3, S 0.0. U_all is: 39.0, 39.1, 36.6, 39.0.

## 4. What the two defences did (pre-run predictions checked)

- **The LLM sanitiser is nearly inactive on LoCoMo.**
  - The poison's value stays in the context in 93–96% of attacked held-out cases, versus 98–99% with no defence. It is removed or rewritten in only 3–6 points' worth of cases.
  - ASR falls by only 0.8–1.3 points. Utility does not change.
  - This was the pre-registered expectation. It audits one turn in isolation, and LoCoMo's poison is a plausible false fact about fictional people rather than an instruction.
- **A-MemGuard is active, and its reach matches the co-retrieval ceiling.**
  - It removes the poison value from about 45% of attacked contexts (exposure 53–55%). That is close to the 52.5% of attacked contexts in which contradicting genuine evidence is co-retrieved, measured before the run.
  - That is consistent with detection by contradiction, though the agreement is aggregate, not a per-scenario test.
  - ASR falls by 12.7–15.4 points (about 30% relative) in every shape. It costs about 2 points of U_all in every shape (false positives, as on MPBench).
- **Both published defences are shape-invariant.** They filter each retrieved context on its own, so how the poison is spread over turns, batches or speakers does not change their behaviour. The audit-propagating methods (S, C, M) depend on the shape by design.

## 5. MPBench–LoCoMo generalization

MPBench numbers are the frozen Option B GPT-4o-mini results (24 groups, target ASR, strict utility; Table 1 of the paper tables). LoCoMo numbers are the held-out 1s shape, the closest analogue of MPBench's localized attack. The metrics differ between benchmarks (MPBench target ASR on instruction-following probes; LoCoMo word-bounded injected-value ASR), so compare changes and rankings, not absolute levels.

| Method | MPBench ASR (Δ vs none) | LoCoMo 1s ASR (Δ vs none) | MPBench utility Δ | LoCoMo 1s U_all Δ |
|---|---|---|---|---|
| No defence | 62.5 | 49.5 | – | – |
| LLM sanitiser | 56.2 (−6.3; −10% rel.) | 48.2 (−1.3; −3% rel.) | 0.0 | 0.0 |
| A-MemGuard | 49.0 (−13.5; −22% rel.) | 34.2 (−15.4; −31% rel.) | −3.8 | −2.1 |
| MemLineage | 43.8 (−18.7) | 49.5 (0.0; inactive by construction) | 0.0 | 0.0 |
| RandEC | 62.5 (0.0) | 49.5 (0.0) | 0.0 | 0.0 |
| C / M | 0.0 (−62.5) | 0.4 (−49.1) | −25.2 | −15.9 (U_out −36.0) |
| **S** | **0.0 (−62.5)** | **0.4 (−49.1)** | **0.0** | **+0.4** |

**What generalizes (localized / single-poison attack).**
1. **The ranking is the same on both benchmarks:** S ≈ C/M < A-MemGuard < LLM sanitiser ≤ no defence on ASR. Among the defences that cut ASR, only S keeps the baseline utility.
2. **The published defences behave the same way on both benchmarks.**
   - A-MemGuard gives a partial ASR cut (13–15 points) at a small utility cost (2–4 points).
   - The sanitiser costs no utility and gives a small cut. The cut is smaller on LoCoMo: it targets instruction-like content, and LoCoMo's attack is factual misinformation.
3. **S's advantage over every published defence holds on LoCoMo.**
   - On 1s, S is below the strongest published defence (A-MemGuard) by 33.8 points, in 8/8 conversations, with no utility loss: U_all +2.5, CI including 0.
   - This closes the gap noted after the v2 run. The frozen H3 compared S only with MemLineage and RandEC, which are inactive on LoCoMo. That decision is unchanged and remains the confirmatory one; this comparison is descriptive.

**What does not generalize unchanged (multi-poison shapes 2s / quarter / spread).**
4. **S still has the lowest ASR of the published-baseline comparisons in every shape (8/8 each), but it pays for it in utility.**
   - S lowers U_all by 6–13 points relative to A-MemGuard and by 8–15 points relative to the sanitiser, 0–1/8 conversations favouring S.
   - The published defences barely change utility in any shape.
   - The mechanism is S's evidence-gated propagation. Once two audits span two sessions, distrust extends to the speaker's context and withholds that speaker's genuine turns too. This is the selective-propagation trade-off. S still keeps at least as much utility as C/M in every shape, but the margin shrinks from +16.3 points U_all (1s) to +0.9 (spread).
5. **This matches MPBench.**
   - MPBench also shows S costing utility once multiple audit signals justify wider propagation: framing −23.5 / −29.2, batch shift −14.3 (Table 7b).
   - The published defences have the same flat profile there: A-MemGuard −3.8, the sanitiser 0 in every column.
   - So the qualitative picture transfers: S is safer than the published defences everywhere, and it matches their utility only when the audit evidence is localized.

**What is not shown.**
- **This is not an equal-information comparison.** S receives oracle A1 audits; the published defences receive none (same asymmetry as on MPBench). The comparison says that propagating a few audits beats audit-free filtering. It does not say S's detector is better.
- **One answer model** (GPT-4o-mini). On MPBench, Haiku gave the same ranking; on LoCoMo this is untested.
- **A-MemGuard used one draw at temperature 1.0.** Its numbers carry sampling noise that the conversation-level CIs only partly capture.
- **The contrasts are descriptive, as pre-registered.** At n = 8 the smallest two-sided sign-flip p is 1/128 ≈ 0.008. A family-wise correction over the 24 contrasts with the new baselines (threshold ≈ 0.002) could therefore reject none of them, however consistent. The ASR contrasts are 8/8 in every shape, the most extreme outcome the test allows.

## 6. Suggested wording for the paper

> On LoCoMo, both published defences we could port (the LLM sanitiser and A-MemGuard; MemLineage and RandEC are inactive by construction) reproduce their MPBench behaviour. A-MemGuard reduces injected-value ASR by about 30% at a 2-point utility cost; the sanitiser, designed for instruction-like poison, barely acts on factual misinformation. Under a single poisoned turn, S removes the attack (49.5→0.4%) with no utility loss and is 34 points below A-MemGuard in all 8 held-out conversations. When the poison spans several turns and sessions, S remains the safest non-quarantining method in every shape, but its evidence-gated propagation withholds 6–13 points of utility relative to A-MemGuard, mirroring its MPBench cost under framing and shift attacks.
