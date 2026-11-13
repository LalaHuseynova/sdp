# Brainstorm: threat model, adaptive attackers and the "uninformative" question

*10 November 2026 · for the ICML paper on contextual (selective) distrust propagation · thinking notes, not results*

---

## 0. Short answers to your questions

| Question | Short answer |
|---|---|
| Can an attacker poison everyone's chats and every agent's memory? | **No, not directly.** Memory is per user or agent. An attacker reaches a victim's memory only through content the victim's agent *reads* (emails sent to them, documents shared with them, web pages, channels). It can **broadcast** the same content to many victims, but inside one victim's memory that content still carries the attacker's own provenance. |
| Is the "uninformative" condition realistic as an *attacker*? | **Mostly not.** Our uninformative condition scatters the attacks randomly across *both* contributors and all batches. As an attacker that means controlling every source the victim reads, which is unrealistic. It **is** realistic in two other forms: (a) a well-funded attacker with **many identities** (Sybils or compromised accounts), and (b) **laundering**, where innocent people quote or forward poisoned content. Those should be modelled explicitly, not as random placement. |
| Is uninformative the attacker's best strategy? | **Against a provenance-only defense, yes, in the limit.** Spreading attacks over as many identities, contexts and batches as possible removes the provenance signal. But it costs the attacker identities. Uninformative is the **endpoint of a budget curve** (k = ∞ identities), not a typical attacker. |
| Can we beat it? | Not with provenance alone: with zero provenance signal, *no* provenance-based method can lower ASR below R without hurting innocents. We **can** (1) stop paying collateral damage there (fix H3) and (2) **restore a signal** by linking attacks through *content lineage* (paraphrased payloads, shared URLs and emails, copies) instead of only through contributor identity. That is a real method improvement and fits "contextual" well. |
| What is an adaptive attacker here? | An attacker who **knows the defense**: S's gates (1 / 2 / 4), the scopes and the threshold. It **adjusts** placement, identities, timing or text to stay under the gates. A correct robustness test reports **"ASR under the best adaptive attack"** for every defense. That ASR *should* be higher than for the simple attacker; the question is how much higher, and whether S stays better than the competitors. |
| Recommendation | Yes, enter this area, but **formalize the attacker first** (a budgeted threat model). Then: (1) show S beats competitors against the *simple, realistic* attacker (mostly done; add external baselines); (2) show the **ASR-vs-attacker-budget curve** for adaptive attackers; (3) add content-lineage linking and excess-risk gates as **S v2** to handle Sybils, laundering and the no-signal case. Replace "random uninformative" as the main robustness story with **budgeted adaptive attacks**, and keep uninformative as the no-signal control. |

---

## 1. Where we stand (what is already proven)

- **Locked held-out test, simple attacker:** one attacker identity, attacks concentrated in a context.
  - Original SAFE-Mem: **77% ASR**.
  - C and M: 0% ASR, but they destroy the attacker's other useful memories (key stratum 0/168).
  - **S: 0% ASR with original-level utility** (key stratum 151/168).
  - H1 and H2 supported.
- **H3 failed:** with random (uninformative) placement, S loses 11.5 points of utility vs R and still lets 63/96 attacks through.
- **So far we only compare against our own ablations (R, C, M) and SAFE-Mem.** The repo already contains the SAFE-Mem paper's competing defenses: **A-MemGuard, DRIFT, RandEC, LLM sanitizer, MemLineage, integrity gate, TMA-NM** (`src/ams/baselines/`). None of them has been run on our workload yet.

---

## 2. Threat model (proposal to formalize in the paper)

### 2.1 Setting

- **The victim** is one user with an agent and a long-term memory (SAFE-Mem underneath).
- **Contributions** enter memory from **sources**. Each contribution `c` carries provenance `(identity i, context x, batch b)`:
  - identity: the email sender, document author or account;
  - context: the channel or domain, such as email, files or Slack;
  - batch: a time window or session.
- **The defender:**
  - has an **audit budget B** (tickets): a slow, trusted check of chosen contributions;
  - keeps an **evidence ledger**;
  - applies a **propagation rule P**, which maps audit evidence to penalties on *related, unaudited* memories.
- **Utility** is correct answers from benign external memories. **ASR** is answers that follow planted content.

### 2.2 What the attacker CAN do (capabilities, each with a cost)

| Capability | Realism | Cost to the attacker |
|---|---|---|
| **C1. Inject content via its own identities**: send emails, share documents, post in channels the victim reads | Very realistic (phishing, malicious documents, poisoned web pages) | Low for 1 identity |
| **C2. Multiple identities (Sybils)**: new email addresses or accounts | Realistic if identities are unauthenticated; harder if the identities must be trusted (verified domains, colleagues) | Grows with k, and new identities have no history |
| **C3. Compromise a legitimate account**: send as a trusted colleague | Realistic but expensive and rare | High per account |
| **C4. Choose timing and context**: when, and through which channel | Realistic within the channels it can reach | Low |
| **C5. Choose the text**: paraphrase payloads, mix with benign text, imitate benign style | Realistic | Low |
| **C6. Laundering**: get innocents to repeat the payload (a viral document, a forwarded email, a quoted web page) | Realistic and important | Medium; no control over who repeats it |
| **C7. Broadcast**: the same attack to many victims | Realistic | Low; also increases the chance of being caught somewhere |

### 2.3 What the attacker CANNOT do (assumptions)

- **Cannot write the user's own words** (principal turns). Principal-owned memory is out of reach, as in SAFE-Mem.
- **Cannot edit other people's contributions** or the defender's ledger.
- **Cannot see audit verdicts directly.** It may infer them from feedback, for example noticing that its attack stopped working.
- **Cannot choose which contributions get audited.** It may try to *avoid* audits by blending in.
- **Cannot read other victims' memories.**

### 2.4 Attacker knowledge levels

- **K0, oblivious (simple):** doesn't know the defense. This is our current localized and distributed attacker.
- **K1, white-box (Kerckhoffs):** knows S's rule, gates and threshold, but not which items will be audited. This is the **standard adaptive attacker** for a security paper.
- **K2, feedback-adaptive:** additionally sees over time whether its content is being used, and reacts, e.g. by switching identity after it is detected.
- **K3, audit-aware:** knows the audit schedule. Too strong; mention only as an upper bound.

### 2.5 Attacker goal and budget

- **Goal:** maximize ASR on the target questions.
- **Budget:** n attacks, k identities, the reachable contexts, and time.
- **Optional second goal (availability, "framing"):** make the defender suppress an *innocent* contributor's useful memories. See A6; it is very relevant to the C/M vs S comparison.

### 2.6 Where "uninformative" sits in this model

- **Random placement across all contributors** = an attacker with access to all sources (k = all identities, no cost). That is an **unrealistic extreme**, but it is a valid **upper bound** on attacker power against provenance defenses.
- **Better: replace it with explicit, budgeted versions:**
  - **Sybil-k:** attacks spread over k attacker-controlled identities, k = 1, 2, 4, 8;
  - **Laundering-r:** a fraction r of the attacks is repeated by innocent contributors;
  - **No-signal control:** what the current uninformative condition really measures, the collateral cost when provenance carries no information. Keep it, but call it a control, not an attack.

---

## 3. Adaptive attacker catalogue (how to implement each in our framework)

All of these except A7 are **data or overlay changes only**. The contribution texts and stores stay the same, so Stage 1 is $0 (exact replay), and only answering and judging cost money: about $0.05 per condition on 8 dev groups and about $0.13 on 24 test groups.

| # | Attack (knowledge) | What it exploits | How to build it | Expected effect |
|---|---|---|---|---|
| **A1** | **Gate-aware spreading**, 1 identity (K1) | S widens to a context only after 2 unsafe audits across 2 batches, and to the contributor after 4 across 2 contexts | Overlay: at most one attack per batch, spread over all batches and contexts the identity can reach | S's ASR rises (only batch-level penalties). C (context counts) also weakens. **M still catches it at contributor level** → we expect **S worse than M** here. Must be shown honestly. |
| **A2** | **Sybil-k** (K1) | All reputation methods count per identity | Overlay: split the attacks over k new attacker identities (k = 2, 4, 8) | ASR rises for C, M and S alike. Shows the limit of identity-based reputation. Motivates content linking (§4). |
| **A3** | **Rotate after detection** (K2) | Penalties attach to the old identity | Sequential order: after the audits reveal identity i, the remaining attacks come from a fresh identity. Uses our existing sequential runner. | Same as A2 but with fewer identities. Realistic and important. |
| **A4** | **Benign padding / reputation farming** (K1) | Risk = (1 + unsafe) / (2 + unsafe + safe); safe audits lower risk, and padding lowers the chance an attack is audited | Overlay: many benign items from the attacker identity; with a random audit selector, the audits hit benign items | Lower penalties for all methods. Needs realistic audit selection (random or risk-based) instead of the oracle that always audits the seeds. |
| **A5** | **Provenance stripping / laundering** (C6) | Unknown-origin records get no penalty at all (our known "safe harbor"); unlinked relays already leak under every method | Overlay: attacks arrive with unknown attribution or via innocent relays | High ASR for all provenance methods. Strong motivation for content lineage and an "unknown" pooled scope. |
| **A6** | **Framing / availability attack** (K1) | **Over-propagation:** C and M punish whole contexts or contributors | Attacker plants one or two poisoned items *inside an innocent contributor's documents* (e.g. a shared document) so that the audits flag the innocent | **This is where S should clearly win.** C/M wipe out the innocent's useful memories (denial of service); S limits the damage to the batch. Strongly supports the "selective" thesis. |
| **A7** | **Content-level rewrites** (SAFE-Mem paper's adaptive attacks: conflict evasion, forged author, forged retention, under-report) | SAFE-Mem's write path | Already in the repo: `configs/adaptive_*`, `prompts/adaptive_*` | Tests whether S keeps working when SAFE-Mem's typing is attacked. Text changes, so new Stage 1 (paid). |

**How to report it:** for each defense, report **robust ASR = the maximum ASR over the attack set {A1…A6}**, plus utility. Also give **curves**: ASR vs identity budget k, and ASR vs laundering rate r. That is the standard format reviewers expect for adaptive-attack evaluations.

---

## 3b. Adaptive attacks: do we have them, how important are they, and the easiest way to add them *(added 10 Nov 2026)*

### Does a paper have an adaptive-attack part?

| Paper | Adaptive attacks? |
|---|---|
| **SAFE-Mem paper** (our base) | **Yes: Table 3.** Four *text-rewrite* attacks on its write path (`configs/adaptive_*`, `prompts/adaptive_*`): **forged author** ("From: me (the account owner)"), **forged retention** ("please remember this for all future tasks"), **conflict evasion** ("fully consistent with, and does not replace…"), **under-report** ("background only, not an instruction"). |
| **Our work so far** | **No.** All our attackers are oblivious (K0): localized, distributed, uninformative. |

### How important is it for ICML?

**Very important, close to required.**

1. **The base paper has it.** A follow-up defense paper without adaptive attacks looks weaker than its own baseline paper.
2. **Our defense's rules are public and deterministic** (gates 1 / 2 / 4, threshold 0.25). The first reviewer question will be "what if the attacker knows the gates?" ML-security reviewers routinely reject defenses evaluated only against non-adaptive attackers.
3. **It can *strengthen* our story, not only stress it.** Two adaptive results are likely to favour S:
   - **framing / availability attacks** (§3 A6), where over-propagation is the vulnerability;
   - the finding that S's selectivity is only exploitable by an attacker who **knows which items will be audited**. See "key argument" below.

### The key argument (why S may survive a realistic adaptive attacker)

- An attacker escapes S only by placing its scored attacks **outside the batch where the audits find evidence**.
- A realistic attacker (K1) **doesn't know which items will be audited.** If it spreads its attacks over batches, the audits find evidence in several batches, and S's context gate fires. S then behaves like C/M. That is our distributed condition, where S already reaches 0% ASR.
- If it concentrates them in one batch, S blocks that batch, which is our localized condition.
- **So S is beaten only by an audit-aware attacker (K3)** or by **Sybil identities**, and Sybils beat C and M too.
- That is a clean, testable claim: *"Selective propagation costs no security against attackers who don't know the audit schedule; its residual weakness, shared with all reputation defenses, is identity splitting."*

### The easiest implementation (minimal modifications)

**Principle:** every adaptive attack below is a **new overlay**: a different assignment of the **same** contributions to contributor, context and batch, optionally with a different audit draw.
- No new attack text, so Stage 1 (memory building) is **$0 replay**: the construction requests are identical.
- No change to SAFE-Mem, S, prompts or the judge.
- Only Stage 3 (answers and judges) is paid.

**Step 1: three overlay attacks with today's oracle audits** (smallest change)

| Condition | Overlay rule | Expected | Role in the paper |
|---|---|---|---|
| **framing** (A6) | The 4 audited seeds are assigned to the **innocent** contributor B's identity, as if the attacker had poisoned B's shared documents. B keeps its 16 useful notes. | C and M wipe out B's useful memories; S loses only the poisoned batch | **S wins**: over-propagation is an attack surface |
| **sybil-2** (A2) | The scored attacks come from a **second attacker identity** that was never audited | Every reputation method (C, M, S) falls to about R's ASR | An honest **shared limitation**; motivates content-lineage linking (S v2, I2) |
| **audit-aware batch shift** (K3 upper bound) | Same identity, but the scored attacks are moved to the batch **without** audited seeds | S misses them (batch gate only); C and M block them | **S's worst case**, reported as an upper bound requiring audit knowledge |

**Step 2: realistic audits** (adds the key argument)
- Replace the oracle's "always audit the seeds" with **random audits**: draw m of A's items uniformly, over several draws (seeds).
- Attacker strategies (K1): **concentrate** (all attacks in one batch) vs **spread** (one per batch).
- Report expected ASR and utility over the audit draws.
- Prediction: S has C/M's security and better utility under concentrate, and about C's security under spread. So **S weakly dominates C/M unless the attacker knows the audits.**

**Code changes needed** (small; workload layer only):
1. **New module** `workload/adaptive.py`: builds the extra overlays, per-condition audit schedules and strata from the v4 bundle into a new bundle directory. The v4 files are not edited.
2. **Make the condition list a parameter** (default = today's three, so nothing changes) in `integration.build_states`, `runner.run`, `stage2` and `analysis`. About 20 lines.
3. **Rebuild the snapshots** for the new conditions with the replay cache. Expected 0 paid requests; check it in a dry run.
4. **Adaptive metrics:** robust ASR (the maximum over attacks), innocent-contributor utility (for framing), and the protocol-v2 hypotheses.

**Before any code change:** the locked protocol v1 hashes *all* source files, so any new file makes its `verify` report differences. The test is done, so that is acceptable, but first **archive the frozen state**: a git commit or tag (needs your OK), or a hashed snapshot of the frozen files. Anyone can then still re-verify v1.

**Cost:**

| Run | Cost |
|---|---|
| Dev, step 1 (3 conditions) | about **$0.15** |
| Dev, step 2 (random audits, about 5 draws × 2 strategies) | about **$0.3–0.5** |
| Test, after freezing protocol v2 | about $0.4–0.6, or about $0.2 more with fresh test groups (recommended) |

The SAFE-Mem paper's four text-rewrite attacks (A7) can come later. They need new attack text, so a paid Stage 1, and they test SAFE-Mem's write path more than our propagation.

---

## 4. Can we improve S to handle the hard cases? (S v2 ideas)

Each change is an algorithm change and needs your approval. Develop on dev, then freeze a **new** protocol and test on fresh held-out groups. The locked result stays as **S v1**.

| Idea | Fixes | Sketch | Risk |
|---|---|---|---|
| **I1. Excess-risk gates** | **H3** (collateral when there is no signal) | Propagate to a scope only if its unsafe rate is **significantly above the population base rate** (a hierarchical Bayesian or likelihood-ratio test against all contributors), not on absolute counts 1 / 2 / 4. With random placement every contributor looks the same, so no propagation and R-like utility. | ASR in the no-signal case stays at R's level (unavoidable for provenance). Needs more contributors per group to estimate a base rate. |
| **I2. Content-lineage propagation** | **A2, A3, A5** (Sybils, rotation, laundering) | Treat an **attack family** as a context: link records by paraphrased payload (MiniLM similarity, as in `quality_v4`), shared indicators (URLs, emails, domains such as `exfil.example.com`) and copy relations. Propagate distrust **along content lineage across identities**. "Contextual" then means provenance context *plus* content context. | False links (benign paraphrases); needs thresholds and ablations. Compare with MemLineage, the closest prior work. |
| **I3. No safe harbor for unknown origin** | **A5** | Pool all unknown-origin records into an "unknown" scope with its own evidence counts | Could penalize benign unattributed content. |
| **I4. Newcomer prior** | **A2** (cheap Sybils) | A new identity starts with a small positive penalty that decays with clean history | Fairness to new legitimate sources; ablate. |
| **I5. Adaptive audit selection** | **A4**; uses the audit budget better | Spend audit tickets where risk or uncertainty is highest (active learning) instead of a fixed schedule | Makes the defender adaptive too. Compare methods at equal budget. |

**The likely strongest paper story:** S v1 (scope selection by evidence support) plus I1 and I2 becomes **"evidence-supported, content-aware propagation."** Its claims would be:
- (i) beats static and over-propagating defenses against simple attackers (done);
- (ii) degrades gracefully against budgeted adaptive attackers, with curves, and **beats competitors at every budget, or the paper says where it doesn't**;
- (iii) wins clearly against framing / availability attacks, where over-propagation is itself the vulnerability.

---

## 5. Competing models (needed for "we are better than competitors")

- **Already in the repo** (SAFE-Mem paper baselines, `src/ams/baselines/`): **MemLineage** (provenance lineage, the closest to us), **A-MemGuard** (lessons from detected failures, close to "evidence propagation"), **LLM sanitizer** (content filter), **integrity gate**, **DRIFT**, **RandEC**, **TMA-NM**.
- **Proposed set for the paper:**
  - **SAFE-Mem** (static);
  - **MemLineage**;
  - **A-MemGuard**;
  - **LLM sanitizer**;
  - **R / C / M** (our ablations, which are also standard reputation designs);
  - **S v1 / S v2**.
- **Fairness rule:** every method that can use audit evidence gets the **same audit tickets**, as R/C/M/S already do. Content filters get no audits but are counted for their extra LLM calls.
- **Work needed:** an adapter so these baselines run on our workload stores. They operate on the plain extract-and-store substrate, so check first whether they can sit on top of SAFE-Mem retrieval. This is a free feasibility check before any paid run.

---

## 6. Proposed plan (each paid step needs approval)

| Phase | What | Cost |
|---|---|---|
| **0. Formalize** (free) | Write the threat model (§2) into the protocol. Build overlays for A1, A2 (k = 2, 4, 8), A5 and A6 on **dev**. Run a mock dry run. Check whether the baselines can be adapted. | $0 |
| **1. Dev adaptive run** | Stage 3 only (the stores are reused) for A1, A2, A5, A6 under SAFE-Mem, R, C, M, S | about $0.3–0.5 |
| **2. S v2 on dev** (after you approve the algorithm change) | Implement I1 and I2 (maybe I3); evaluate on dev with all conditions | about $0.3–0.5 |
| **3. Baselines on dev** | MemLineage, A-MemGuard, sanitizer on the same workload | about $1–3 (content filters add LLM calls) |
| **4. Freeze protocol v2** | Pre-register the adaptive hypotheses, for example: "robust ASR of S v2 ≤ C at every k"; "framing damage of S < C/M"; "no-signal utility loss of S v2 ≤ R + 2 points" | $0 |
| **5. Fresh held-out test** | New held-out groups (generate a second test set; the current test set is used once) | about $1–2 |
| **6. Generality** | Second backbone; full MPBench (S vs SAFE-Mem); human check of the judge | about $5–20 |

---

## 7. Possible paper framing

- **Working title:** *When Should Distrust Spread? Evidence-Supported Propagation for Poisoning Defenses in Agent Memory.*
- **Contributions:**
  1. **Problem and threat model:** propagating audit evidence to related memories, with a budgeted adaptive attacker (identities, contexts, timing, laundering, framing).
  2. **Method:** S, which propagates only to scopes the evidence supports, plus (v2) excess-risk gates and content-lineage linking.
  3. **Benchmark:** a controlled, MPBench-derived workload with a pre-registered, locked held-out protocol (a contribution in itself).
  4. **Findings:**
     - selective propagation dominates static and over-propagating defenses against simple attackers;
     - the robustness curves against adaptive attackers;
     - over-propagation itself is an attack surface (framing).
- **What we must not claim:**
  - that S beats provenance-free attackers with unlimited identities;
  - that S replaces SAFE-Mem. It complements SAFE-Mem's typing.

---

## 7b. Is SAFE-Mem the right baseline?

**Short answer: SAFE-Mem is the right base, and a necessary reference. On its own it is not a sufficient, or even a fair, *competitor*.**

### Why SAFE-Mem is good to keep

- **It is the base system.** S is a layer on top of SAFE-Mem, so "SAFE-Mem without S" is the natural control: it shows what our layer adds.
- **It is a strong published defense.** In its paper it beats A-MemGuard, DRIFT, MemLineage, the LLM sanitizer, RandEC and TMA-NM on MPBench. Improving on it means improving on the published state of the art.
- **It isolates our contribution.** We change nothing in SAFE-Mem, so any difference comes from propagation.

### Why it is not enough on its own

1. **Unequal information.** S, R, C and M receive **5 oracle audits**; SAFE-Mem receives **none**. "S beats SAFE-Mem" therefore partly says "audits help", which nobody doubts. The **fair** comparison is against methods given the **same audits**. R is exactly that: same audits, no propagation. That is why **S vs R and S vs C/M** carry the scientific claim, not S vs SAFE-Mem.
2. **The workload targets SAFE-Mem's known gap.** We deliberately chose description-type external attacks, the one class SAFE-Mem's typing admits. Hence 77% ASR here, against about 6% on full MPBench. A reviewer may call the comparison stacked against SAFE-Mem. We must say this openly, and also show **full MPBench**, where SAFE-Mem is strong and S must at least not hurt.
3. **R, C and M are our own ablations.** Reviewers want **published** competitors too. Name R/C/M after the designs they represent (record-only containment; contextual reputation; multi-scope reputation), cite prior work, and add external methods.

### Suggested baseline set (three tiers)

| Tier | Baselines | Gets audits? | Why |
|---|---|---|---|
| **1. Same information** (the core claim) | **R** (record-only), **C** (contextual / beta reputation, as in trust systems such as SuperLocalMemory-style behavioural trust), **M** (multi-scope), **source quarantine** (block a contributor after k unsafe audits; trivial to add) | yes, the same 5 | Isolates *how far to propagate*. S must win here. |
| **2. Published defenses given the same audits** | **A-MemGuard** (learns "lessons" from detected failures: feed it our audit verdicts as its detected failures); **MemLineage** (propagates distrust along content lineage: seed it with the audited records as untrusted) | yes, adapted | The closest prior work on "learning from detections" and "lineage propagation". Beating these is the strongest claim. Both are already in `src/ams/baselines/`. |
| **3. Content-based defenses** (no audits) | **LLM sanitizer**, **integrity gate**, **DRIFT** isolator, **TMA-NM** | no (they inspect every item with an LLM) | A different philosophy. Report their extra LLM cost. Also test **S + sanitizer** to show the approaches are **complementary**. |

The **reference** rows are original SAFE-Mem (static) and no-memory.

### Practical notes

- **Feasibility check first (free).** The `src/ams/baselines/` defenses act on retrieved memory in the plain extract-and-store setting. Check whether each one can sit on top of SAFE-Mem retrieval in our runner, or needs its own substrate. Then check how to give A-MemGuard and MemLineage the audit verdicts fairly.
- **Equal budgets.** Same audit tickets for every audit-using method. Report LLM calls and cost for content filters.
- **Most important pair to add first: MemLineage and A-MemGuard.** They are the competitors a reviewer will name.

**Paper wording:** "We compare against (i) the unchanged base defense (SAFE-Mem), (ii) equal-audit propagation baselines (record-only, contextual and multi-scope reputation, source quarantine), (iii) published defenses adapted to receive the same audits (A-MemGuard, MemLineage), and (iv) content-based filters."

---

## 8. Open decisions for you

1. Accept the threat model in §2, especially that "uninformative" becomes a **no-signal control**, with **Sybil-k and laundering** as the realistic strong attackers.
2. Which adaptive attacks first? My suggestion: **A6 (framing, where S should win), A1 and A2 (where S is stressed)**, then A5.
3. May I design S v2 (I1 excess-risk gates, I2 content lineage)? This is an algorithm change, so it needs your explicit approval.
4. Which external baselines? My suggestion: **MemLineage and A-MemGuard** first.
5. Budget for phases 1–3 on dev: about $2–4 in total.
