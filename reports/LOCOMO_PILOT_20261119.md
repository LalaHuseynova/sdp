# LoCoMo real-LLM pilot: results (exploratory; 19 Nov 2026)

## Scope and setup

- **Pre-registration:** `research_data/locomo_pilot_20261119/PREREGISTRATION.md`, written before any LLM call. Its one deviation is the nltk overlay, an environment fix.
- **Code and outputs:** `research_data/locomo_pilot_20261119/`
  - `pilot.py`, `analyse.py`, `run.sh`;
  - `dry/`, `mock/` (free checks);
  - `paid/`: `outcomes.jsonl`, `results.json`, `scenarios.json`, `meta.json`, `budget_guard.sqlite`, `response_cache.sqlite`.
- **Frozen methods are unchanged.** The attack generator and seeds are exactly those of the feasibility study.
- **What was run:**
  - conv-48 and conv-49, drawn by seed;
  - speaker_a is the memory owner and speaker_b the hijacked contributor;
  - hijacks: 1 session, 2 sessions, spread, with 2 random draws each;
  - auditors: A1 (2 poison turns detected) and A2 (A1 + 10 random turns);
  - arms: no defence, C, M, S, plus a clean reference;
  - GPT-4o-mini via OpenRouter, answered and judged with the existing LoCoMo prompts;
  - top-10 turn retrieval.

## Cost and integrity

- **Actual cost:** **$0.21898665**: 3,398 settled calls, 0 unknown, 0 errors, guard never blocked. The cap was $5. The free estimate was $0.27.
- **Run time:** 622 s.
- **Free checks before the paid run:**
  - the dry run (cost, and the draws rule chose 2 draws);
  - the mock run (end to end, 0 errors);
  - stratum sizes: U_out is about 100 questions per scenario in conv-48 and about 35 in conv-49; 6 unaudited targets per scenario, 72 per arm × auditor.

## Results against the pre-registered criteria (all exploratory)

| Q | Result | Criterion |
|---|---|---|
| **Q1** does the poison change answers? | No-defence ASR **0.458**, clean (chance) **0.000**. The poison reached the context for 95/96 targets. | **Pass** (≥ .30 and ≥ .20 above clean) |
| **Q2** does S reduce ASR? | A1: no defence .458 → S **.097**. A2: .536 → S **.318**. | **Pass** both (≥ .20) |
| **Q3** does S preserve legitimate accuracy (1 session × A1, U_out)? | no defence .376, **S .380**, C .104, M .104. **S − C = S − M = +.276**; conv-48 +.295, conv-49 +.255. | **Pass** (≥ +.10, same sign in both) |
| **Q4** where does S lose security? | **2 sessions × A1: S .292 vs C/M 0** (flagged). Everywhere else S ≤ C/M. | 1 flagged cell |
| **Q5** does retrieval translate into answers? | S − C sign agreement: evidence recall vs accuracy 12/16 (4 disagree); exposure vs ASR 8/11 non-zero cells (13 both zero) | mostly yes |

**Full grid** (ASR on unaudited targets; judge accuracy for U_out = hijacked speaker's unaffected sessions; U_in = benign questions whose evidence is in the hijacked sessions):

| Hijack × auditor | ASR: none / C / M / **S** | U_out acc: none / C / M / **S** | U_in acc: none / C / M / **S** |
|---|---|---|---|
| 1 session × A1 | .54 / 0 / 0 / **0** | .38 / .10 / .10 / **.38** | .17 / .08 / .08 / .08 |
| 2 sessions × A1 | .42 / 0 / 0 / **.29** | .36 / .11 / .11 / **.39** | .57 / .10 / .10 / **.38** |
| spread × A1 | .42 / 0 / 0 / **0** | – | .36 / .12 / .12 / .12 |
| 1 session × A2 | .54 / **.54** / .13 / **.13** | .38 / .38 / .39 / **.39** | (n small) |
| 2 sessions × A2 | .61 / **.61** / .41 / **.41** | .36 / .36 / .39 / **.39** | .57 / .57 / .38 / .38 |
| spread × A2 | .46 / **.46** / .42 / **.42** | – | .36 / .36 / .37 / .37 |

Accuracy on the principal's questions is ≈ .43 under every arm, so no collateral damage to the memory owner.

## Interpretation

1. **The attack works, but only half the time.**
   - The poison was retrieved for 95/96 targets but hijacked only 46% of answers.
   - The wrong values are random answers of the same category from other conversations, often semantically incoherent: a dish answered with "Max", a console with "Twice a week". The model often ignores them.
   - The attack is therefore conservative. It was fixed in advance and not strengthened after seeing results.
2. **Single-session hijack with incident audits:**
   - S contains the attack as well as C and M (ASR 0);
   - S keeps no-defence accuracy on questions grounded in the unaffected sessions (.38 vs .38), while C and M fall to .10.
   - This is the retrieval finding, confirmed at the answer level in both conversations. It is **the clearest answer-level evidence so far for the central idea.**
3. **Two-session hijack with incident audits:** S keeps utility (+.29 U_out, +.28 U_in), but lets the undetected session through (ASR .29 vs 0). This is the expected cost of selectivity, and it is real at the answer level.
4. **With realistic mixed audits (A2):**
   - **C fails completely.** Safe verdicts dilute contributor-level risk, so its ASR equals no defence.
   - **S ≡ M exactly**: same ASR, same accuracy.
   - S beats C on security, but S has no advantage over M.
5. **Spread injection:** S = C = M. No cost, no benefit.

## What this does and does not show

**It shows (exploratory; 2 conversations):**
- On natural LoCoMo sessions, with questions and evidence annotated by LoCoMo's authors, the retrieval-level regime map carries over to real GPT-4o-mini answers.
- Where its conditions hold, selective propagation contains harmful memories while preserving useful ones.
- Where they fail, the costs are visible and measurable.

**It does not show:**
- Anything confirmatory (2 conversations, one orientation, 2 draws).
- That S beats M under realistic auditing.
- That the attack is external: the template is ours, and its wrong values are random.
- Behaviour on SAFE-Mem's claim store (this used turn-level RAG).
- Anything about multi-contributor settings or the contributor/source gate.

## Does this justify the full experiment?

**The pre-registered rule says yes:**
- Q1 passes;
- Q3 passes in both conversations;
- the cost is about $0.11 per conversation-orientation for this grid, so 10 conversations fit far below $25.

**My assessment:** worth running, because it is cheap and the answer-level effect is large and consistent. But only as a **pre-registered regime map**, not as a claim that S dominates. It needs a new pre-registration before any result is seen:
- **Data:** all 10 conversations × both orientations × 5 draws.
- **Hijacks:** 1 session, 2 sessions, ¼ of sessions, spread.
- **Auditors:** A1 and A2.
- **Arms:** none, R, C, M, S, SL.
- **The attack:** unchanged as the primary. Optionally, one pre-declared stronger variant with type-matched wrong values. That variant strengthens the attack for every arm and does not favour S.
- **Confirmatory hypotheses:**
  - (i) 1 session × A1: U_out accuracy S − C > 0 and S − M > 0, with ASR non-inferiority;
  - (ii) A2: ASR S − C < 0 (C's dilution failure), with S − M reported as an identity;
  - (iii) spread: ASR non-inferiority of S vs C/M.
  - The 2-session security cost is reported as a pre-declared trade-off.
- **Statistics:** cluster bootstrap over the 10 conversations, with Holm correction.
- **Cost:** estimated at roughly $5–10 (about 30× this pilot's grid, with the cache); proposed cap $15.

**As ICML evidence:** a meaningful, independent *utility-side* complement to MINJA and MPBench. The sessions and the QA labels are natural; the attack is ours. It should be presented as a regime map: when selective propagation helps, when it equals M, and when it costs security.
