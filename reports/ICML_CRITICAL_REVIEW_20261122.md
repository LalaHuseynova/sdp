# Critical ICML assessment of the SAFE-Mem propagation paper (22 Nov 2026)

Advisor-style critique, written from the final Option B results (CLAUDE_MEMORY_TRANSFER.md §8b, §14), `reports/PAPER_PLAN_20261122.md` and the Section 4 preview (`preview_main.pdf`). This is Claude's opinion, not data. It is not the formal 5-seat ARS panel review; that can be run separately on the full draft once it exists.

---

## 0. Verdict in one paragraph

As planned now ("S is a new defence: 0% ASR at 91% utility, beats four published defences"), the paper would most likely be **rejected** at ICML. The reason is not sloppiness. The protocol, pre-registration and honesty are well above the usual ICML submission. The reasons are three substantive problems:

1. The headline result is close to **true by construction** of the localized workload.
2. A **cheap adaptive attacker** (Sybil k ≥ 2, batch shift, laundering) brings S back to Original's ASR. Its worst case (65.6) is worse than MemLineage's (43.8).
3. The method is a **hand-set Beta-reputation count with three gates**. ICML reviewers will see little ML novelty in it.

The strongest *defensible* paper is a different framing: **"How far should audit evidence propagate in agent memory? A formalization of the granularity trade-off, an evidence-gated rule that is Pareto-optimal when provenance is informative, and a proven and measured evasion boundary for every label-based rule."** With a formal proposition, a structure sweep and a real (non-oracle) auditor, the paper becomes borderline-competitive. Without them, consider SaTML or an ICML workshop.

---

## 1. Limitations ranked by how much a reviewer will care

Severity: **F** = could sink the paper alone · **H** = serious, needs an experiment or reframing · **M** = needs a clear defence · **L** = acceptable if stated.

| # | Weakness | Sev. | Defend by explanation, or needs work? |
|---|---|---|---|
| W1 | **Result by construction.** In the localized condition both seeds and both scored attacks share batch 1, which is exactly S's batch gate. Once the 2 seeds are audited, S withholds batch 1 and leaves batch 2 (the key stratum) alone. The 0/91 vs 0/66 split follows from the layout, and the LLM stages add only noise. A reviewer will write: "The workload is designed so that the proposed rule's scope equals the attack's scope." | **F** | **Needs work.** Explanation alone fails. Show S's advantage as a *function* of how localized the attack is (sweep), and argue with evidence that real poisoning arrives clustered (one email thread or one tool output carrying several injections; MINJA/AgentPoison-style multi-injection). |
| W2 | **Adaptive attacker defeats S.** Sybil k = 4 → 64, batch shift → 66, laundering r = 1 → 66, vs Original 63. S's worst case (65.6 GPT) is the worst of all real defences. In security-flavoured ML, "a trivial adaptive attack breaks it" is the most common rejection reason. | **F/H** | **Partly defensible**, if (a) the threat model states that provenance is *system-assigned and authenticated* (identity = verified account, batch = delivery event recorded by the system), so a Sybil costs real accounts; (b) the failure is proven to be shared by every label-based rule (C, M fail too), turning it into a theorem rather than a bug; (c) the cost to the attacker is quantified (k identities, deliveries). Still needs the formal proposition (A2 below). |
| W3 | **Limited ML novelty.** Beta(1,1) reputation (Jøsang-style), a fixed threshold and count gates of 1/2/4. SL is cosine dedup at τ = 0.8. S2-ID's gain comes entirely from MemLineage's gate. No learning, no theory yet. | **H** | **Reframe.** Do not sell S as an algorithmic novelty. Sell the *problem formulation* (propagation granularity of audit evidence), the *trade-off characterization* and the *evaluation protocol*. Simplicity then becomes a strength: "the simplest rule that respects evidence already reaches the frontier." |
| W4 | **Unfair comparison in H3.** S gets 5 oracle audit tickets. The four published defences use no audits. "Beats published defences" compares methods with different information. | **H** | **Mostly fixable by framing + an existing appendix.** Reword C3 to "audit propagation adds protection that audit-free defences cannot provide; the two are complementary". Promote the "+R" variants (published method on R's retrieval) and, if possible, add published-method + S (stacking). |
| W5 | **Oracle auditor.** Main tables assume perfect, timely tickets that hit exactly the seeds. Imperfect audits already hurt: 20% missed → 21, late → 33. | **H** | **Needs one experiment.** Feed S audits from a *real detector* (LLM sanitiser, A-MemGuard or RandEC verdicts on a sampled subset of memories) and show that propagation multiplies the detector's reach. This also turns W4 into a strength. |
| W6 | **One synthetic workload, 24 groups, split used twice** ("replication evidence, not confirmatory"). Contributor structure is synthetic; benign texts all from MPBench. | **H** | **Defend + one external check.** The controlled workload is needed (only 102/3,241 MPBench attacks are propagation-reachable, and no contributor submits twice: a real finding worth stating). A second source is still expected: a fresh v5 subset (32 groups, ~$17–32) *or* a feasibility port to AgentPoison/MINJA. |
| W7 | **Toy store size.** 40 contributions per group. Real agent memories hold thousands of records, so retrieval contention and gate firing may change. | **M** | **Explain + cheap scaling probe** (add benign distractor contributions; exposure is LLM-free after extraction, but extraction itself is paid). |
| W8 | **Hand-set constants and the 0.25 boundary.** S's penalties sit exactly at 0.25, so security rests on `>=`; threshold 0.35 opens the attack (dev ablation). The source gate and τ were inert in every tested cell. | **M** | **Explain + free sensitivity plot.** Derive 0.25 from the prior (penalty ≥ 0.25 ⇔ risk ≥ 0.75 ⇔ 2 unsafe, 0 safe) and present it as a decision rule. Show a threshold × gate Pareto frontier on exposure (free). Say plainly that the source gate never fired and is kept for completeness, or drop it from the claims. |
| W9 | **Judge not human-validated**; target-specific ASR is a lexical filter. | **M** | **Free to fix** (kit ready; needs 3 named people). Meanwhile stress that the deterministic, LLM-free **exposure** metric gives the same ranking. |
| W10 | **Post-hoc variants.** SL's τ was chosen after v1; S2-ID was designed after seeing dev. | **L/M** | **Explanation suffices** if labelled as such (already done). Both were frozen before the Option B run. |
| W11 | **Second backbone thin.** Haiku: 8 of 62 cells, no temperature, reasoning off. | **L** | Explanation: the ranking and every ✓/✗ replicate. Retrieval decisions do not depend on the answer model. |
| W12 | **Negative results.** H6 ✗ (tie), distributed utility 66 = C = M, v1 H3 ✗ (no gain without structure). | **L** | Acceptable, and it builds credibility. Present the distributed and no-signal results as the predicted boundary of the method, not as failures. |
| W13 | **Relevance of the threat slice.** Original reaches 63% here vs 5.9% on full MPBench, because the workload keeps only propagation-reachable attacks. | **M** | **Explain**: the paper studies the slice where propagation is decisive and makes no prevalence claim. Motivate with a concrete scenario (a compromised colleague account sending several poisoned messages). |

**Which ones can lead to rejection:** W1, W2 and W3 together. Any one of them alone is survivable with good framing. All three together read as "a heuristic tuned to its own benchmark that an adaptive attacker breaks". W4, W5 and W6 are the next tier; reviewers will list them, but they rarely decide alone.

---

## 2. Novelty: what is actually new

| Claimed piece | Honest novelty | Comment |
|---|---|---|
| Distrust from an audited memory to its siblings | **Low–medium.** Reputation and trust propagation (Beta reputation, EigenTrust, Sybil defences), plus contributor trust in A-MemGuard and SuperLocalMemory | The idea of reputation is not new |
| *Granularity* of propagation (record / batch / context / contributor), gated by evidence | **Medium. This is the real contribution.** No agent-memory paper we know of asks *how far* audit evidence should spread or measures the safety–utility cost of each scope | Must be the centre of the paper |
| "Every label scope has a matching evasion" | **Medium–high if proven.** Turns the main weakness into a result | Not yet written (plan step 7.2) |
| Controlled propagation workload + pre-registered protocol | **Medium** as a methodological contribution: shows MPBench cannot test propagation (3.1% reachable, no repeat contributors) | Release it as a benchmark |
| SL (content lineage) | Low (embedding dedup) | Useful engineering; H5 is clean |
| S2-ID | Low (borrowed gate) | Keep as "composition" evidence, not a contribution |

**Is it enough for ICML?** Not as "a new defence". Possibly as "a principled analysis of evidence propagation with a theorem, a frontier and an honest evasion boundary", which ICML does accept (in the trustworthy-ML / safety track) when the analysis is crisp and the experiments test predictions of the theory.

---

## 3. How to state the contributions (suggested wording)

1. **Problem.** We formalize *audit-evidence propagation* in agent memory: given audit verdicts on some memories, how should distrust transfer to unaudited memories that share provenance? We show that the standard benchmark cannot test it (only 3.1% of MPBench attacks are propagation-reachable, and no contributor submits twice).
2. **Theory.** For any rule that uses only provenance labels, (a) a scope-wide rule pays a utility cost proportional to the legitimate items in the scope; (b) an attacker who controls labels evades any scope at a cost that we bound (identities or deliveries needed). An evidence-gated rule is on the frontier when provenance is informative and reduces to the scope-wide rules otherwise. *(To be written; see A2.)*
3. **Method.** S, the simplest rule that spreads distrust only to scopes the evidence supports, plus SL (content lineage for unlinked relays).
4. **Evidence.** Under a frozen, pre-registered protocol on two answer models, S matches the scope-wide rules on attack success (0%) while keeping 91% vs 66% utility (+90 points on the key stratum). The predicted evasion boundary appears exactly where the theory says (Sybil k, laundering r), and it is shared by every label-based rule.
5. **Complementarity.** Audit propagation and audit-free content defences fail in different places. Combining them (S2-ID) lowers the adaptive worst case (65.6 → 46.9).

Use the word **"characterize"** more than "outperform".

---

## 4. Additional experiments and analyses (value vs effort)

| ID | What | Addresses | Cost | Value |
|---|---|---|---|---|
| A1 | **Localization sweep:** fraction of A's attacks co-batched from 0 → 1 (and seeds-per-batch 1 → 4). Plot unaudited exposure and key exposure for R, C, M, S | W1 (the main one) | **Free** (exposure is deterministic, existing stores; new conditions in the research layer, no policy change) | Very high |
| A2 | **Formal proposition + predicted breakpoints**, checked against the existing Sybil-k and laundering-r curves (Tables 5–6) | W2, W3 | Free (writing) | Very high |
| A3 | **Threshold × gate sensitivity frontier** (utility vs exposure) | W8 | Free (exposure) | High |
| A4 | **Real auditor:** audits come from a detector's flags on a sampled subset (first check whether the recorded A-MemGuard / sanitiser / RandEC verdicts can be reused at no cost; RandEC is local and free) | W5, W4 | Free if RandEC or recorded verdicts; else small paid | Very high |
| A5 | **Human judge check** (300 cases, kit ready) | W9 | Free (3 people) | High (cheap credibility) |
| A6 | **Stacking:** published defence applied on top of S's retrieval (like the "+R" variants) | W4 | Small paid (answers + judge) | Medium–high |
| A7 | **Fresh confirmation:** v5, 32 groups | W6 | ~$17–32 (fits the ~$22 left only at the low end) | Medium–high |
| A8 | **Second benchmark feasibility** (AgentPoison / MINJA in `third_party/`) | W6 | Free check first | High if feasible, but slow |
| A9 | **Store-size scaling** (add benign distractors) | W7 | Paid extraction (small) | Medium |
| A10 | Haiku on all cells | W11 | ~$14–17, over the cap | Low |

---

## 5. Likely reviewer comments and suggested replies

| Reviewer will say | Reply | Needs evidence? |
|---|---|---|
| "The localized condition is built so that S's batch gate matches the attack. The result is circular." | "Yes, localized is the *informative* regime by design. A1 shows S's advantage as a function of localization: it shrinks to zero when there is no structure (as in our v1 no-signal condition), as the theory predicts. Real deliveries are clustered (examples)." | **A1** |
| "A trivial Sybil attack breaks S. This is not a defence." | "Every rule that uses provenance labels fails at the same point. We prove the bound (A2) and measure it. Under authenticated identities a Sybil costs k real accounts. Combining S with a content defence lowers the worst case." | **A2** |
| "The comparison with published defences is unfair: S has audits." | "Agreed, which is why we frame it as complementarity: audit-free defences cannot exploit audits that exist in deployment. Stacking (A6) / +R results show the gains add up." | A6 (or the existing +R) |
| "Oracle audits are unrealistic." | "A4: with audits from a real detector, propagation extends its reach from k flagged items to their siblings." | **A4** |
| "This is a reputation system; where is the ML?" | "The contribution is the propagation-granularity question, its theory and the evidence. The rule is deliberately the simplest one that respects evidence." | A2 |
| "Synthetic, small, one benchmark, reused split." | "MPBench cannot test propagation (3.1% reachable, no repeat contributors). We release the workload. Pre-registration and the frozen protocol remove tuning freedom. A7/A8 add a fresh or external check." | A7 or A8 |
| "Threshold 0.25 is exactly at the boundary; it looks tuned." | "It is fixed by the prior (two unsafe audits, zero safe), was frozen before test data, and A3 shows the full frontier." | A3 |
| "LLM judge not validated." | "Human check (A5); the LLM-free exposure metric gives the same ranking." | A5 |

---

## 6. Research direction: what makes it more novel

1. **Theory first** (A2). A short, clean proposition with a matching empirical curve is the single biggest lift for ICML fit.
2. **Propagation as a force multiplier for detectors** (A4). This turns "oracle audits" into "any detector + S". It is a more useful story for practitioners and a natural bridge to the published defences.
3. **Content-anchored propagation** (longer term, likely a follow-up paper): spread distrust along *content* lineage, which the attacker controls less, rather than labels. SL is a first step; the dev check of content similarity (AUC ≈ 0.73) suggests it needs learning. This could be the ML-novel next paper.
4. Do **not** add more hand-designed variants (S-G, S2-BS have already failed). More heuristics weaken the paper.

---

## 7. Prioritized action plan

Order = research value ÷ effort. "Free" = no paid API call. Every paid item needs the owner's explicit approval first (standing rule).

| Priority | Action | Cost | Time (rough) |
|---|---|---|---|
| 1 | **Reframe** the abstract, intro and contributions around propagation granularity and characterization (§3). Reword C3 as complementarity. | Free | 1–2 days |
| 2 | **Write the formal proposition** (A2) and check its predicted breakpoints against the existing Sybil-k / laundering-r numbers | Free | 3–5 days |
| 3 | **Localization sweep** (A1) + **sensitivity frontier** (A3) on exposure: new figure(s) | Free (small new research-layer code; no policy change) | 2–4 days |
| 4 | **Human judge check** (A5): name 2 annotators + 1 adjudicator | Free | 1 week elapsed |
| 5 | **Real-auditor experiment** (A4), starting with RandEC (local, free) or recorded verdicts | Free → small paid | 3–5 days |
| 6 | Promote the **+R / stacking** results to the main text (A6) | Existing appendix; small paid if new | 1–2 days |
| 7 | Decide: **fresh v5 32 groups** (A7, ~$17–32) or the **second-benchmark feasibility check** (A8, free first) | Owner decision | 1–2 weeks |
| 8 | Fix the draft: Section 4 still describes protocol v1 (seed 20261108, Holm over two contrasts, one backbone, "Section ??"). Update it to protocol v2 (seed 20261114, 8 contrasts, two backbones) | Free | 1 day |
| — | Skip: Haiku on all cells, new S variants, scaling unless asked by reviewers | — | — |

**Minimum viable ICML version:** items 1–5 + 8 (all free or nearly free). **Strong version:** add 6 and 7.
