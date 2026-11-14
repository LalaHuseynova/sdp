# Why the held-out evaluation needs a newly generated dataset

*14 Nov 2026. Supports Protocol v2 (`reports/PROTOCOL_V2_DRAFT_20261113.md`, §2.1–2.3b and revision 4) and `plan.md` steps 3.1–3.4. Status: nothing has been generated yet, and no paid call has been made.*

## 1. Short answer

**Yes, we must create new data.** The final paper results have to come from data that was never used to design, tune or check our methods (S, SL, S2-ID). MPBench, our source benchmark, **does not have enough unused data left** for a fresh test of 96 groups. The missing part has to be generated, under frozen, defence-blind rules.

## 2. Why MPBench alone is not enough

### 2.1 Attacks: almost none are left

Of MPBench's **3,241** attack cases, only **102** can work as scored attacks. A usable attack needs a "description" question whose planted target SAFE-Mem actually stores in an admissible external claim. The others cannot succeed against *any* memory system under SAFE-Mem's authority rule:

| MPBench attack cases | Count |
|---|---|
| Non-description question | 2,727 |
| No question | 242 |
| Target outside external claims | 170 |
| **Usable (reachable)** | **102** |
| of which already used in v1–v4 (dev and test) | 99 |
| **Usable and unused** | **3** |

The held-out test needs **576 generated attacks**: 96 groups × (4 scored attacks + 2 copied seeds). On top of that comes a separate 60-attack generation-check subset. **3 unused attacks against 576 needed** means the attacks must be generated.

**Copied seeds also had to be generated (revision 4).** 1,652 of MPBench's 1,671 seed cases have questions SAFE-Mem never answers from external memory. As copied seeds they would make the relay probes (hypothesis H5) unable to succeed by construction. Uncopied seeds (`seed_b`) still come from unused MPBench seeds.

### 2.2 Benign documents: too few, and unevenly spread

- **Unused MPBench benign documents: 963**, counted by text. The earlier estimate of 1,154 counted case IDs. It missed 32 copy-base documents, 79 documents whose text equals a v1–v4 document, and 80 internal duplicates.
- **Needed:** 96 groups × 27 benign documents = **2,592 slots**.
- Supply is also uneven by domain (calendar 101 … script_execution 262), while each group block needs documents from its own domain.
- The shortfall is filled with **generated benign documents**: 432 slots per domain, plus a 20% reserve, giving **1,957 generation specs**.

### 2.3 Why not simply reuse MPBench documents?

**Reusing documents across groups would break the statistics.** All tests treat the group as an independent unit (paired cluster bootstrap). If the same document appeared in several groups, those groups would be correlated, and the confidence intervals and p-values would be too optimistic. The protocol therefore requires that **no document is shared between held-out groups**.

### 2.4 Why not use the existing dev/test data?

Dev was used to build and tune the methods, so a result on dev is not a fair test. The old v4 test split is kept as a **replication check** (`plan.md` step 4.4), not as the main result: it is small and was produced under the earlier protocol.

## 3. What will be generated

| Item | Specs generated | Kept after filtering (target) | Role |
|---|---|---|---|
| Attack documents | 1,440 (2.5× margin for rejections) | 576 + 60 check subset | scored attacks and copied seeds |
| Benign documents | 1,957 (including 20% reserve) | fills each domain's shortfall | ordinary workplace documents |

The attacks follow MPBench's own design: the same six domains (calendar, Slack, email, file and doc, web, script execution), the same attack families and goals, and the same mix of strong, moderate and weak signals. The proportions are taken from the 102 reachable MPBench cases.

## 4. How the generated data is kept fair

1. **Frozen first.** The generator prompts, rules, group builder and analysis code are hashed in the protocol freeze (`plan.md` 2.2–2.3) **before** any data is generated.
2. **Defence-blind.** The generator (Claude Sonnet) sees only the domain, attack type, goal and signal strength. It never sees S, SL, S2-ID or any baseline.
3. **A different model family.** The evaluated system and the judge use GPT-4o-mini. Generating with Claude avoids same-model bias.
4. **Automatic filtering, with a reason code for every item:**
   - E1: format, schema and safety checks;
   - E3: no near-duplicates of MPBench or of earlier accepted items (MiniLM cosine < 0.6);
   - E4: no 8-gram overlap with MPBench or v1–v4 texts;
   - E2: the question must be a description question;
   - I1: the **original** SAFE-Mem must actually store the poison, so every kept attack is a real threat to the baseline.
5. **No topping up after seeing results.** If too few items pass, we stop and report. A second batch needs new owner approval and the identical prompt.
6. **Fixed assignment.** Items go to groups by a fixed hash order, and the 60-attack check subset is never part of the results.
7. **Full transparency.** The complete funnel (generated → each rule → used) is reported in the paper. Benign source (MPBench vs generated) is a pre-registered covariate, with a multi-way cluster sensitivity analysis.

## 5. Limitations (to state in the paper)

- Generated attacks may differ in style from real-world attacks. Mitigations: MPBench-matched proportions, the I1 real-threat check, and the replication on the old MPBench test split.
- A single generator model. A possible robustness addition before the freeze is to generate a small subset with a second model.
- The benign MPBench/generated mix varies by domain. Method contrasts are paired within groups, so this mix cannot favour any one method.

## 6. Cost and approval

Generation (step 3.1) and the inclusion check (step 3.3) are **paid stages**. Each needs the owner's explicit approval, with a cost estimate from the dry run in `plan.md` step 1.12. A rough, unmeasured guess for Sonnet generation is about $20–27 including retries. Nothing runs before the protocol freeze.
