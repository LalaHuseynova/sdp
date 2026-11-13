# Dev Stage 3: original SAFE-Mem vs R / C / M / S on the v3 workload (8 November 2026)

**Status:** owner-approved paid dev Stage 3 is **complete**.
- **Data:** 8 dev groups × 3 conditions × (5 memory arms × 35 probes) plus the no-memory reference, giving **4,480 outcome events**. Integrity checks are clean.
- **Answers:** real GPT-4o-mini answers using the original typed answer prompt, the original conflict checker and the original attack judge.
- **Cost:** **$0.1397682** (cap $0.70).
- **Scope:** development results only. The held-out test split is untouched. ICML claims must come from the locked test run (§7).

## 1. What was run

| Item | Detail |
|---|---|
| Arms | **static = original SAFE-Mem** (unchanged); R (direct finding only); C (contributor-wide); M (C plus context and batch); **S (our contextual, support-gated propagation)**; no-memory |
| Conditions | localized (attacks share one batch), distributed (attacks spread over batches), uninformative (contributor and batch carry no signal) |
| Audits | 5 identical oracle tickets for R/C/M/S (4 unsafe seeds, 1 safe benign); 0 for static. Equal budgets were verified. |
| Stores | Real v3 dev stores from paid Stage 1 (GPT-4o-mini extraction, local MiniLM). |
| Grading | Attacks and copies: the original LLM judge. Utility: deterministic alias match. **Strict utility** additionally requires the inserted fact to be in the supplied context. |
| Statistics | Paired cluster bootstrap over groups (10,000 resamples); Holm correction for H1. |

**Code** (workload layer only; no SAFE-Mem algorithm, prompt or setting changed):
- `src/ams/research/workload/transport.py`: new `stage3` purpose. It accepts only `answer`, `no_memory_answer`, `conflict` and `judge_answer` requests, each validated against its exact original prompt shape. It is dev only and has a $0.70 cap.
- `scripts/stage_controlled_workload.py stage3`, with `--mock` (the same paid path against `httpx.MockTransport` in a separate session) and `--confirm-paid-dev-stage3`.
- One new test.

**Offline first.** A full mock run on the real v3 stores (`research_data/controlled_workload_stage3_dev_v3_mock_20261108/`) was clean before any spend, with 4,480 outcomes and integrity OK. The persisted session mode means mock and live billing can never share a session.

## 2. Cost

| Stage | Unique requests | Note |
|---|---:|---|
| Answers | 919 | Identical requests, e.g. static and R with the same context, are answered once and reused. |
| No-memory answers | 216 | |
| Conflict checks | 16 | Original checker, real calls. |
| Judge | 203 | |
| **Total** | **1,354** | **$0.1397682**, 0 failures, $0 held |

- **New session ledger:** $0.2049093 used (pilots, v3 Stage 1 and Stage 3).
- **All research spend:** $2.1266388 (old shared session) + $0.2049093 = **$2.3315481**, plus $0.01974 still held in the halted old session.

## 3. Main results (real answers and judges)

ASR is the share of scored attacks the judge accepted; strict utility counts only correct answers with the fact in context.

| Condition | Arm | ASR | Utility | **Utility strict** | Key stratum, strict | Linked copy | Unlinked relay |
|---|---|---:|---:|---:|---:|---:|---:|
| localized | **original SAFE-Mem** | **23/32 (72%)** | 187/200 | 185/200 | 51/56 | 7/8 | 7/8 |
| localized | R | 23/32 | 187/200 | 185/200 | 51/56 | 0/8 | 4/8 |
| localized | C | **0/32** | 146/200 | 134/200 | **0/56** | 1/8† | 4/8 |
| localized | M | **0/32** | 146/200 | 134/200 | **0/56** | 1/8† | 4/8 |
| localized | **S (ours)** | **0/32** | **187/200** | **185/200** | **51/56** | 0/8 | 4/8 |
| distributed | original SAFE-Mem | 23/32 | 187/200 | 185/200 | – | 7/8 | 7/8 |
| distributed | R | 23/32 | 187/200 | 185/200 | – | 0/8 | 4/8 |
| distributed | C / M / **S** | **0/32** | 146/200 | 134/200 | – | 1/8† | 4/8 |
| uninformative | original SAFE-Mem / R | 23/32 | 187/200 | 185/200 | 67/69 | 7/8 (R 0/8) | 7/8 (R 4/8) |
| uninformative | C | 19/32 | 176/200 | 168/200 | 67/69 | 0/8 | 4/8 |
| uninformative | M | 15/32 | 138/200 | 125/200 | 42/69 | 0/8 | 4/8 |
| uninformative | **S (ours)** | 20/32 | 174/200 | 167/200 | 67/69 | 1/8† | 4/8 |
| — | no-memory | 0/32 | 0/200 | 0/200 | 0 | 0/8 | 0/8 |

Principal (user-owned) controls were correct in 32/32 under every arm.

> **Correction (final audit, 8 Nov 2026).** The explanation in the next paragraph is wrong. The G-D02 linked copy's target is "PDF reports auto-forward to external@exfil.com". The answer counted as a hit restates a *different* attack, the unlinked relay's "meeting recordings … external archive". This is a **judge false positive**, not a near-duplicate record. The target-specific secondary metric removes it (C/M/S linked copy 1/8 → 0/8). See [the audit and freeze report](WORKLOAD_AUDIT_FREEZE_20261108_REPORT.md). The original text is kept below.

† This is not a leak of the linked copy itself; the copy was not in the context. The answer came from another record restating the same MPBench statement, because two MPBench attack templates in G-D02 are near-duplicates (§6).

## 4. Pre-specified hypotheses (dev)

| Hypothesis | Test | Result |
|---|---|---|
| **H1 (localized selectivity):** S keeps more key-stratum utility than C and M at no worse ASR | S − C key utility **+0.73** [0.57, 0.86]; S − M **+0.73** [0.57, 0.86]; both Holm-significant. S − C ASR 0.00 [0, 0]; S − M 0.00 [0, 0]. S − R ASR **−0.72** [−0.88, −0.56]. | **Supported** |
| **H2 (distributed):** S's ASR no worse than M's | 0.00 [0, 0] | **Supported** |
| **H3 (uninformative):** S's utility loss vs R ≤ 2 points | R − S utility **+0.065** [0.02, 0.12] | **Not supported** |

On strict utility the H1 contrast is the same or larger: key stratum 51/56 for S vs 0/56 for C and M.

## 5. What this means (dev only)

1. **Original SAFE-Mem is vulnerable on this workload.** 72% of scored attacks succeed, because SAFE-Mem's authority rules admit external description claims to description questions.
2. **R (block only the audited item) does not help scored siblings.** It blocks the audited records and the linked copy, but ASR stays at 72%.
3. **C and M stop all localized and distributed attacks but over-suppress.** They drop all 56 key-stratum memories (strict) and 25.5 points of overall strict utility in the localized condition.
4. **S, our contextual defense, gives the best of both when the context is informative.** In the localized condition it has the same 0% ASR as C and M with original-SAFE-Mem-level utility (185/200 strict). In the distributed condition it correctly behaves like C and M.
5. **Limitation (H3 fails).** When provenance is uninformative, S behaves like C:
   - it loses 6.5 points of utility vs R;
   - it lets 20/32 attacks through (M: 15/32).

   S's advantage depends on the incident structure being informative. The paper must state this honestly; it is also a natural motivation for the robustness experiments.
6. **Unlinked relays leak under every arm** (4/8 under every audited arm; 7/8 static). No provenance policy can catch an unattributed copy, as designed (H3-copy), which motivates content-based detection as future work.

## 6. Limitations

- **Dev-scale only:** 8 groups (32 scored attacks per condition). The CIs are cluster bootstraps over 8 groups. Results are for design validation; claims need the locked test split (24 groups).
- **One backbone (GPT-4o-mini)**, a single run at temperature 0, and an oracle auditor.
- **LLM judge not human-validated.** The answers judged as hits look correct on inspection (§3 rows), but a human audit of a sample is needed for the paper.
- **MPBench near-duplicate attack templates** can restate a blocked target through another record (the G-D02 †). Fragment relay carriers limit relay storage.
- About 8% of inserted facts are not extracted (equal across arms; the strict metric accounts for it).

## 7. Next steps toward ICML

1. **Freeze v3 and the analysis plan.** Pre-register the protocol before touching the test split. Free.
2. **Test split:** Stage 1 (about $0.17), Stage 2 (free) and Stage 3 (about $0.45 at the measured dev rate × 3). This is the locked main result vs original SAFE-Mem.
3. **Strengthen the evidence:**
   - a second backbone;
   - S vs original SAFE-Mem on the full MPBench;
   - one more published defense as a baseline;
   - an adaptive attacker;
   - ablations of S's support gates and its threshold;
   - robustness to noisy or late audits;
   - human validation of a judge and label sample.
4. **Optional workload fixes before freezing:** full-statement relay carriers; removal of near-duplicate attack templates across contexts.

**Outputs:**
- `research_data/controlled_workload_stage3_dev_v3_20261108/` (`queries.sqlite` journal, `analysis.json`, `analysis.md`, `stage3_summary.json`);
- `research_data/controlled_workload_stage3_dev_v3_mock_20261108/` (offline mock run).
