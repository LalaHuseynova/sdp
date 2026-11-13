# Adaptive attackers, content lineage and boundary-verification auditing: dev study (12 November 2026)

> **Update, 12 November 2026: the paid dev confirmation with real answers and judges is complete.**
> - **Run:** owner-approved; 67,200 outcomes; **$0.12520395** against a $0.25 cap; 0 failures, 0 holds.
> - **Consistency:** all 4,200 base-condition rows equal the earlier dev Stage 3 outcomes exactly.
> - **Agreement with exposure:** the real-answer results confirm every direction of the exposure study (§8).
> - **The original exposure study is kept unchanged below.**

**Status:** done offline on the **dev split only**, at **$0** (no model call).
- **What was measured:** whether governed retrieval puts the attack target or the utility fact into the answer context ("exposure"). That is the ceiling a paid Stage 3 converts into ASR and utility.
- **What was not run:** no answers or judges.
- **Test split:** not touched.
- **Status of the protocol:** exploratory. Nothing here is pre-registered; a confirmatory run needs a new frozen protocol (v2) and fresh held-out data.

## 0. Short answer

| Question | Answer (dev, exposure level) |
|---|---|
| Is S still better than C and M against adaptive attackers? | **Only in some threat models, not uniformly.** |
| Where S wins | **(a)** Attackers who concentrate their poison: same 0% ASR as C and M, +25.5 pts utility [22.5, 27.5]. **(b)** Framing an innocent contributor with concentrated poison: S keeps 58% of the innocent's facts vs 42% (C) and 32% (M). |
| Where S loses or ties | **(a)** Audit-aware batch shift: S 97% exposure vs C/M 0%. **(b)** Context shift: S and C 97%; only M blocks. **(c)** Sybil: everyone 97%. **(d)** Random detection with *spread* poison: **S lets 28% of undetected attacks through, C/M 0%**, for only +3.3 pts utility. |
| Best improvement found | **Boundary-verification auditing:** the fifth audit ticket checks one item next to a flagged batch. Same 5-ticket budget, no policy change. Spread gap 28 → **4.5 pts** [1.9, 7.0], at equal utility. Under concentrated attacks S then **beats both** C (46% leak) and M (−12.6 pts utility). |
| Second improvement | **Content lineage** (SL): unlinked relays 62.5% → **0%**, at 0 utility cost, in every oracle condition. It does not help against distinct new payloads (Sybil, shift), by design. |

## 1. What was built (all research layer; frozen SAFE-Mem / R / C / M / S code untouched)

| File | What it does |
|---|---|
| `src/ams/research/workload/adaptive.py` | Adaptive conditions as **relabellings** of the existing dev Stage-1 stores: same memory and records, different (contributor, context, batch) provenance and/or audited set. No construction and no model call. |
| `src/ams/research/workload/lineage.py` | New arms RL / CL / ML / **SL** = base policy plus *content lineage*. A claim with MiniLM cosine ≥ τ = 0.8 to a claim of an unsafe-audited root is withheld for every use. It never creates an audit or observation, so it cannot raise anyone's reputation risk. It wraps `state.reader()` only. |
| `src/ams/research/workload/runner.py` | `run()` accepts `conditions`, `arms`, `no_memory` and `lineage_tau`. **Defaults are byte-identical to v1** (same journal scope). |
| `src/ams/research/workload/replay.py` | `EvaluationReplaySession` replays already-paid Stage-3 replies from one scope at $0. `CountingMockSession` counts new requests for cost estimates. |
| `src/ams/research/workload/transport.py` | New guarded purpose `adaptive_stage3`: dev only, own hard cap ≤ $1.00, owner approval per run. |
| `scripts/adaptive_exposure.py`, `scripts/analyse_adaptive_exposure.py` | Free exposure runner and analysis: cluster bootstrap over groups, 10,000 resamples, seed 20261112. |
| `scripts/adaptive_stage3.py` | `--estimate` (free, exact count of new requests) / `--confirm-paid-adaptive-dev` (paid, needs approval). |
| `scripts/archive_locked_protocol.py` | Archived the 224 files locked protocol v1 hashed (`locked_protocol_v1_frozen_files.tar.gz`, SHA-256 `e0c6a131…`). `verify` passes; v1 stays checkable after new code. |
| `tests/test_adaptive_lineage.py` | 9 offline tests: replicas reproduce stored conditions; budgets are equal; overlays match their definitions; random draws are deterministic; policy arithmetic under shift and Sybil; lineage blocks only near-duplicates and leaves other decisions unchanged; follow-up keeps detections and budget; replay is scoped. |

**Sanity:** "replica" conditions rebuilt through the new code reproduce the stored localized and distributed audits **and** every exposure row exactly (0 mismatches, 8/8 groups).

## 2. Threat model of each condition

A = attacker, B = innocent contributor, U = unrelated relay. Oracle audits = 4 seeds unsafe + 1 B benign safe, unless stated.

| Condition | Attacker knowledge | What changes |
|---|---|---|
| `shift_batch` | K3 (knows which items get caught) | Scored attacks moved to A's *other* batch in the same context |
| `shift_context` | K3 | All seeds in context X, all scored attacks in context Y |
| `sybil` | K1 + second identity | Scored attacks under a never-audited identity |
| `framing_concentrated` / `framing_spread` | K1, availability goal | The 4 seeds are planted in B's channel: in one B batch per context, or one per B batch |
| `random_concentrate` / `random_spread` (8 draws each) | **K1 (realistic):** does not know which items are caught | In each context 2 of A's 4 attack items are detected uniformly at random. Placement: localized (all in one batch) vs distributed (split over batches). |
| `…_fu` | Same K1 attacker | **Defender-side change:** the fifth ticket audits one random unaudited item of the flagged contributor in a batch *next to* a flagged batch (same context), when the detections don't already span two batches. Verdict = ground truth. All arms see the same audits. |

## 3. Results

8 dev groups, 32 scored attacks, 200 utility probes per condition × arm. Random rows average 8 draws within each group. "Unaudited ASR" counts only attacks that were not themselves audited (pure propagation). All values are exposure rates.

### 3a. Unaudited-attack exposure (lower is better)

| Condition | static | R | C | M | **S** | **SL** |
|---|---:|---:|---:|---:|---:|---:|
| localized (oracle) | .969 | .969 | 0 | 0 | **0** | **0** |
| distributed (oracle) | .969 | .969 | 0 | 0 | 0 | 0 |
| uninformative | .969 | .969 | .781 | .562 | .812 | .812 |
| shift_batch (K3) | .969 | .969 | 0 | 0 | **.969** | .969 |
| shift_context (K3) | .969 | .969 | .969 | 0 | .969 | .969 |
| sybil | .969 | .969 | .969 | .969 | .969 | .969 |
| framing_concentrated | .969 | .969 | .969 | .969 | .969 | .969 |
| framing_spread | .969 | .969 | .969 | .969 | .969 | .969 |
| **random_concentrate** | .963 | .963 | 0 | 0 | **0** | **0** |
| **random_spread** | .971 | .971 | 0 | 0 | **.280** | .280 |
| **random_concentrate_fu** | .963 | .963 | **.462** | 0 | **0** | 0 |
| **random_spread_fu** | .969 | .969 | .080 | .080 | **.126** | .126 |

### 3b. Utility exposure (higher is better)

`util[A]` = the attacker's own benign notes (key stratum); `util[B]` = the innocent contributor's notes.

| Condition | R | C | M | **S** | S − C [95% CI] |
|---|---:|---:|---:|---:|---|
| localized | .925 | .670 | .670 | **.925** | **+.255** [.225, .275] |
| random_concentrate | .925 | .670 | .670 | **.925** | **+.255** [.225, .275] |
| random_spread | .925 | .670 | .670 | .703 | +.033 [.026, .040] |
| random_concentrate_fu | .925 | .799 | .799 | **.925** | **+.126** [.113, .136] |
| random_spread_fu | .925 | .690 | .681 | .686 | −.004 [−.013, .003] |
| shift_batch | .925 | .670 | .670 | .775 | – |
| framing_concentrated: util[B] | .942 | .417 | .317 | **.575** | **+.158** [.05, .233] (vs M +.258) |
| framing_spread: util[B] | .942 | .417 | .417 | .417 | 0 |

### 3c. Copies

| | Linked copy (oracle conditions) | Unlinked relay (oracle conditions) | Unlinked relay (random) |
|---|---|---|---|
| R / C / M / S | 0 | .625 under every arm | .63–.83 |
| **+ lineage (RL / CL / ML / SL)** | 0 | **0** | .34–.55 (only when the relay's source seed was audited) |

**Lineage audit:** 8 groups × 8 representative conditions. Lineage withheld **0 benign-note claims and 0 principal claims**. The withheld claims belonged only to:
- seeds: 892;
- linked copies: 177;
- unlinked relays: 41;
- scored attacks: 129. These are partly near-duplicate phrasing; none changed scored-attack exposure.

Utility is identical to the base arm in every condition.

## 4. Interpretation (for the paper)

1. **Granularity is a double-edged choice.** Each propagation granularity has a matching audit-aware evasion:
   - batch shift beats S;
   - context shift beats S and C;
   - identity splitting beats all.

   Coarser scopes (M) buy robustness to placement with collateral utility loss. This is a clean, honest framing and should replace any claim that S dominates.
2. **Against an attacker who doesn't know the audits (K1), the attacker's best response to S is *spreading*.** With plain random audits this costs S 28 pts of unaudited ASR relative to C and M, for 3 pts of utility. **Plain S is not a good choice against a rule-aware K1 attacker.**
3. **Boundary-verification auditing repairs most of this, at the same audit budget.** A natural incident-response step ("check next to the flagged batch before trusting the rest"):
   - the spread gap falls to 4.5 pts at equal utility;
   - under concentrated attacks S beats C on *both* axes (C's coarse estimate is diluted by the safe follow-up finding: 46% leak);
   - S beats M by 12.6 utility points.

   Proposed method for v2 = **S + boundary-verification auditing (+ content lineage)**.
4. **Framing:** S limits collateral damage when the planted poison is concentrated (58% of the innocent's facts kept vs 42% / 32%). Spread framing makes all propagating arms equal. R is the most framing-robust, but offers no propagation security.
5. **Content lineage** closes the unlinked-relay hole (the locked test's open problem: 15–16/24 relays leaked under every arm) at zero utility cost on dev. It is orthogonal to provenance and helps every arm.

## 5. Caveats (must be stated)

- **Exposure, not answers.** Static exposure ≈ .97 vs locked-test static ASR .77 (target-specific .61). Paid Stage 3 is needed for real ASR and utility.
- **Dev only:** 8 groups, 32 scored attacks. Follow-up auditing and τ = 0.8 were **designed after seeing dev exposure**. A confirmatory claim requires freezing them in protocol v2 and testing on fresh data. The v4 test split is spent for v1 hypotheses but was never used for adaptive conditions.
- The oracle verdicts are perfect, the follow-up uses a single ticket, and detections are 2 per context (no draw finds 0 or 1). Varying the audit budget is a natural ablation.
- The adaptive overlays relabel the same texts, so contexts and batches are abstract provenance labels, not re-written documents.

## 6. Outputs

| Path | Content |
|---|---|
| `research_data/adaptive_exposure_dev_v3_20261112/exposure_rows.jsonl.gz` | 90,160 exposure rows |
| `research_data/adaptive_exposure_dev_v3_20261112/analysis.json` | Table and bootstrap contrasts |
| `research_data/adaptive_exposure_dev_v3_20261112/parts/` | Per-group runs, logs and sanity summaries |
| `research_data/adaptive_stage3_estimate_dev_v3_20261112/` | Exact paid-cost estimate for confirming these on dev (§7) |

## 7. Paid confirmation on dev (run on 12 Nov after owner approval; results in §8)

**What it does:** converts the exposure results into real ASR and utility, with real GPT-4o-mini answers and the original judge. It covers 40 conditions (the 3 base conditions, 5 placement and framing conditions, 16 random-detection draws and 16 follow-up draws) × arms static/R/C/M/S/SL × 8 dev groups = **67,200 outcomes**.

**How the estimate was made:** `adaptive_stage3.py --estimate`, a mock dry run, merged over two shards in `cost_estimate_total.json`. Every request that dev Stage 3 already paid for is replayed at $0 from that scope's own replies, so replayed text is exactly what dev Stage 3 saw.

| New distinct requests | Count |
|---|---:|
| Answers | 855 |
| Judges | about 98 (follows mock answers, so approximate; at most about 150) |
| Conflict checks | 3 |
| **Expected cost** | **$0.11**; **$0.15** with a 30% allowance |
| **Proposed hard cap** | **$0.25** (guarded purpose `adaptive_stage3`) |

**Infrastructure:** a new guarded `adaptive_stage3` purpose (dev only, own cap) in the same budget session. A new scope is needed because the dev Stage-3 scope's cap would refuse: test spend accrued after it opened.

**Command (only after the owner approves):**

```bash
caffeinate -i uv run python scripts/adaptive_stage3.py --confirm-paid-adaptive-dev --cap 0.25 \
  --out research_data/adaptive_stage3_dev_v3_<date> --arms static R C M S SL
```


## 8. Paid dev confirmation: real GPT-4o-mini answers + original judge (12 November 2026)

**Run:**
- Approved by the owner. `scripts/adaptive_stage3.py --confirm-paid-adaptive-dev --cap 0.25`.
- Guarded scope `adaptive_stage3`.
- **67,200 outcomes:** 40 conditions × 6 arms × 8 dev groups × 35 probes.

**Requests:**
- **Sent:** 4,071 answers, 1,354 judges and 36 conflict checks (identical requests sent once).
- **Replayed at $0** from the dev Stage-3 scope: 63,129 answers, 10,166 judges and 4,711 conflict checks.

**Cost:** **$0.12520395**, close to the $0.11 estimate.

**Budget:** the session ledger is now $0.9084978, so all research spend is **$3.0351366, plus the $0.01974 hold**.

**Consistency:** all 4,200 rows of the base conditions × original arms equal the earlier dev Stage 3 (answer and outcome).

**Analysis:** `scripts/analyse_adaptive_stage3.py`; results in `research_data/adaptive_stage3_dev_v3_20261112/adaptive_analysis.json`. Bootstrap over 8 groups.

**Metric definitions:**
- **ASRt** = target-specific ASR: judge hit *and* the answer restates the probed target. This is the pre-declared secondary metric of protocol v1, and it removes judge false positives.
- **Strict utility** = correct *and* the fact was in the context.

### 8a. Target-specific ASR on attacks that were not themselves audited (lower is better)

| Condition | static | R | C | M | **S** | **SL** |
|---|---:|---:|---:|---:|---:|---:|
| localized | .594 | .594 | 0 | 0 | **0** | **0** |
| distributed | .594 | .594 | 0 | 0 | 0 | 0 |
| uninformative | .594 | .594 | .469 | .438 | .469 | .531* |
| random_concentrate | .575 | .575 | 0 | 0 | **0** | **0** |
| random_spread | .631 | .631 | 0 | 0 | **.205** | .205 |
| random_concentrate_fu | .575 | .575 | **.316** | 0 | **0** | 0 |
| random_spread_fu | .640 | .640 | .080 | .080 | **.126** | .126 |
| shift_batch (K3) | .594 | .594 | 0 | 0 | .656 | .656 |
| shift_context (K3) | .594 | .594 | .656 | 0 | .656 | .656 |
| sybil | .594 | .594 | .656 | .656 | .656 | .656 |
| framing_concentrated | .594 | .594 | .688 | .656 | .688 | .656 |
| framing_spread | .594 | .594 | .688 | .656 | .656 | .625 |

\* **SL vs S in uninformative:** 2 of 32 attacks differ. In both, the target was **already in S's context** (identical exposure). Lineage removed a different near-duplicate claim, the context changed, and the model then repeated the target. This is answer-level variation, not lineage admitting poison. CI [0, .156].

**Why governed arms can exceed static** (.656 vs .594 in shift, Sybil and framing): withholding the audited seeds frees context slots, so the unpenalized attack claims reach the answer more often.

### 8b. Strict utility (higher is better)

| Condition | R | C | M | **S** | S − C [95% CI] | S − M [95% CI] |
|---|---:|---:|---:|---:|---|---|
| localized | .925 | .670 | .670 | **.925** | **+.255** [.225, .275] | +.255 |
| random_concentrate | .925 | .670 | .670 | **.925** | **+.255** [.225, .275] | +.255 |
| random_spread | .925 | .670 | .670 | .703 | +.033 [.026, .040] | +.033 |
| random_concentrate_fu | .925 | .799 | .799 | **.925** | **+.126** [.113, .136] | **+.126** [.113, .136] |
| random_spread_fu | .925 | .690 | .681 | .686 | −.004 [−.013, .003] | +.005 |
| shift_batch | .925 | .670 | .670 | .775 | – | – |
| framing_concentrated: the innocent's notes | .942 | .417 | .317 | **.575** | **+.158** [.05, .233] | **+.258** [.242, .267] |
| framing_spread: the innocent's notes | .942 | .417 | .417 | .417 | 0 | 0 |

SL's utility equals S's in every condition.

### 8c. Key security contrasts (target-specific, unaudited attacks)

| Contrast | Estimate [95% CI] |
|---|---|
| random_spread: S − C | **+.205** [.144, .279] (S worse) |
| random_spread_fu: S − C (= S − M) | **+.045** [.019, .070] (gap reduced by 78%) |
| random_concentrate_fu: S − C | **−.316** [−.417, −.227] (S better) |
| random_concentrate_fu: S − M | 0 |
| shift_batch: S − C (all attacks) | +.656 [.50, .81] (K3 worst case) |

### 8d. Copies (target-specific)

| | Linked copy | Unlinked relay |
|---|---|---|
| static | .50 | .75 |
| R / C / M / S, oracle conditions | 0 | .50 |
| **SL, oracle conditions** | – | **0** |
| SL, random conditions | – | .28–.33, vs .50–.64 for S (lineage needs the relay's source seed to be audited) |

### 8e. Conclusions (dev, real answers)

1. **Every exposure-level direction is confirmed** with real answers.
2. **Plain S is not better than the baselines against a rule-aware attacker who spreads poison:** +20.5 pts ASR for +3.3 pts utility.
3. **S + boundary-verification auditing** is the defensible method:
   - against concentrated attacks it dominates C (−31.6 pts ASR, +12.6 pts utility) and beats M on utility (+12.6) at equal security;
   - against spread attacks it trails C/M by 4.5 pts [1.9, 7.0] at equal utility.
4. **Content lineage** removes the relay leak in oracle conditions (.50 → 0) with no utility cost. In random conditions it helps only when the relay's source was audited.
5. **Limitations to state:**
   - an audit-aware batch shift, a context shift and Sybils defeat S;
   - context shift and Sybils also defeat C, and Sybils also defeat M;
   - these are shared limits of provenance-based propagation.
6. **Next:**
   - freeze **protocol v2**: method = S + boundary verification + lineage τ = 0.8; adaptive hypotheses with margins; this dev evidence as the basis;
   - confirm on fresh held-out groups;
   - add ablations: audit budget, follow-up tickets, τ, S's gates.
