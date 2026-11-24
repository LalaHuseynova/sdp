# Should LoCoMo also be evaluated on the original SAFE-Mem pipeline? (assessment, 24 Nov 2026)

**Scope:** free, read-only. Code inspected: `src/ams/memory/typed.py`, `src/ams/eval/locomo.py`, `scripts/run_locomo.py`, `configs/*locomo*`, the MPBench store construction (`src/ams/research/workload/integration.py`), the policy retrieval adapter (`src/ams/research/retrieval/adapter.py`, `metadata.py`), the Stage-1 store summary, and the original SAFE-Mem README. No experiment implemented, no paid call. Every MPBench and LoCoMo result is unchanged.

## 1. What we evaluate today

| | MPBench (Option B) | LoCoMo v2 + supplement |
|---|---|---|
| Memory | **SAFE-Mem**: LLM-extracted typed claims plus evidence chunks, withhold mode, standing labels, conflict downgrading | **Plain RAG**: raw turns, MiniLM top-10 |
| Base row | Original SAFE-Mem | No defence (static retrieval) |
| Policy unit (root) | one contribution (user query + document) and all its claims and chunks | one turn |
| Policies | frozen R / C / M / S / SL / S2-ID through `GovernedRetrieval` (refill, static-parity mode) | the same frozen policy code, through the v2 retrieval |

The two benchmarks therefore differ in **dataset and memory substrate at the same time**.

## 2. What already exists for SAFE-Mem on LoCoMo

- **The original SAFE-Mem paper used LoCoMo** (arXiv 2610.22959; `UPSTREAM_README.md`). It reports "+15 points LoCoMo accuracy". That was benign accuracy only, with no attack.
  - Configurations: `configs/v31_locomo_withhold_{a,b}.yaml`, with each speaker as principal: typed memory, withhold mode, hops 0, sentence endorsement, 4 evidence slots, 20 claims per session, k = 4.
  - OpenRouter mirrors: `openrouter_locomo_safemem_{a,b}.yaml`.
- **Ingestion path:** `run_memory` → `TypedStandingMemory.write_dialogue`, one write per session with a fixed principal.
  - Per session there are two extraction calls: the principal's lines, and the whole dialogue for the counterpart.
  - Claims are labelled with standing (principal vs counterpart).
  - Evidence chunks keep turn-level `source_ids`.
- **The policy adapter is compatible.** `GovernedRetrieval` supports exactly "flat + withhold + hops = 0", which is the v3.1 LoCoMo configuration.
- **What does not exist:** an attacked SAFE-Mem LoCoMo run, a binding of SAFE-Mem's LoCoMo records to roots, batches and contributors, and audits on that store. The only LLM calls ever made on it were 10 benign smoke-test questions (28 Oct).

## 3. How much of the MPBench setup can be reproduced faithfully

| MPBench element | On SAFE-Mem + LoCoMo | Faithful? |
|---|---|---|
| SAFE-Mem write, extraction, standing, withhold retrieval, conflict downgrading | the original code and the v3.1 LoCoMo config, unchanged | ✓ |
| Principal / external roles | principal = speaker a or b; that is v2's two orientations | ✓ |
| Policy retrieval with refill, static-parity check | `GovernedRetrieval`, unchanged | ✓ |
| Provenance: batch = session, context = conversation, contributor = speaker | as v2 | ✓ (contributor gate never fires, as in v2) |
| **Root = one write unit with all its claims and chunks** | dialogue mode writes per session, and **all counterpart claims of a session are attributed to the first counterpart turn** (`typed.py`, `write_dialogue`) | ⚠ the root becomes "speaker × session" for claims, so the record level coincides with the batch (§5, P1) |
| Oracle audits of poison turns | a turn-level audit maps to that session's counterpart claims plus the chunks containing the turn | ⚠ coarser than MPBench and v2 |
| Localized and distributed attacks (MPBench Table 1) | v2's 1-session and all-sessions hijacks | ✓ |
| Sybil, shift, framing | relabelling and audit changes | ✓ (not needed for the minimum) |
| Relays / laundering (unknown-origin copies) | the dialogue mode has no "unknown origin" role | ⚠ needs a new role mapping |
| Published defences filter SAFE-Mem's retrieval, no refill | as on MPBench | ✓ |
| S2-ID | ≡ SL (no sensitive-action questions), as in v2 | ✓, untestable |
| Metrics | ASR (word-bounded value), value exposure, judge utility, all from v2. Strict utility (correct **and** evidence in context) becomes computable through the chunks' turn `source_ids` | ✓ |

**Overall:** the memory system, retrieval, policies and attacks carry over. The one real compromise is **provenance granularity**.

## 4. The minimum scientifically meaningful evaluation

**Question:** do MPBench's two headline results reproduce when S runs on SAFE-Mem's own store on a second dataset? And does Original SAFE-Mem's conflict handling already change the picture?

| Item | Minimum |
|---|---|
| Memory | Original SAFE-Mem, `v31_locomo_withhold` settings unchanged, principal = each speaker (= v2's orientations) |
| Conditions | v2's **localized (1 session)** and **all-sessions** hijacks, A1 audits (MPBench Table 1's localized / distributed pair); 5 draws × 2 orientations, v2's seeds, targets and values |
| Methods | Original SAFE-Mem, R, C, M, S, SL (S2-ID ≡ SL); MemLineage and RandEC (free). Optional: A-MemGuard and the LLM sanitiser on 1 session |
| Conversations | v2's 8 held-out (unit of analysis); conv-48/49 dev reported separately |
| Measures | v2's ASR and eligibility, value exposure, net and key-evidence utility; strict utility as a secondary measure |
| Status | pre-registered, **estimation-only (descriptive)**, no new confirmatory family; v2 and MPBench untouched |
| Not included | adaptive families (Sybil, shift, relay, missed audits, framing): they test the policy's provenance logic, which v2 already covers |

**Reported questions:**
- **(Q1)** Original SAFE-Mem's ASR on LoCoMo.
- **(Q2)** The H1 pattern: S at C/M-level ASR with base-level key-evidence utility.
- **(Q3)** The H2 pattern on the all-sessions hijack.
- **(Q4)** Rankings against the published defences, if those are included.

## 5. Implementation problems

1. **P1, provenance granularity (central).**
   - Dialogue mode extracts the counterpart's claims from the whole session and binds them all to the first counterpart turn. A claim derived from a poison turn cannot be told apart from the speaker's genuine claims of that session.
   - So an audit of one poison turn withholds that speaker's whole session of claims.
   - R becomes session-level (≈ S's first gate), and S − R is no longer separable on 1 session.
   - **Options:**
     - (a) keep SAFE-Mem's dialogue ingestion (faithful to SAFE-Mem; state the coarser root). **Recommended.**
     - (b) write each turn separately: turn-level roots, but not SAFE-Mem's published LoCoMo ingestion, and extraction loses dialogue context.
2. **P2, the binding layer is MPBench-narrow.**
   - `SourceBinding` accepts only `principal_turn`, `authenticated_principal` and `external_body`; dialogue mode produces `counterpart_turn`.
   - Changing `src/ams` would break the Option B freeze, which hashes every `src/ams/**/*.py`.
   - The adapter must live outside `src/ams` and outside v2's frozen set (a new package, like `locomo_v2_supp/`).
3. **P3, conflict downgrading interacts with the poison.**
   - The poison contradicts a genuine claim. If both come from the hijacked speaker (same standing), SAFE-Mem marks **both** contested ("none served at its kind").
   - If the genuine fact came from the principal, the poison is downgraded.
   - So Original SAFE-Mem may already reduce ASR, or lose utility, in ways plain RAG does not. This is the main open scientific question, and the reason Q1 matters.
4. **P4, extraction transforms the poison.**
   - Poison may be paraphrased, merged or dropped. The session cap of 20 claims lets 8 poison turns crowd out genuine claims in a 1-session hijack.
   - Exposure must be measured by value, not by turn. Utility effects partly reflect extraction, not the policies.
5. **P5, the clean pairing is weaker than in v2.**
   - A poisoned session is re-extracted, so its genuine claims differ between scenarios.
   - The arms remain paired within a scenario (the same store), which is what the contrasts need.
6. **P6, multi-turn chunks.** Chunks span turns, and a chunk mixing speakers takes the lower standing. An audited poison turn withholds whole chunks, genuine turns included.
7. **P7, a different context budget.** k = 4 claims + 4 evidence chunks, versus v2's top-10 turns. Absolute levels are not comparable with v2; only within-substrate contrasts are.
8. **P8, freeze hygiene.** Re-verify the Option B manifest and v2's `3a2c2df8…` before and after. All new code goes in a new folder. No call goes through a v2 ledger.

## 6. Cost (GPT-4o-mini via OpenRouter, $0.15 / $0.60 per M tokens; to be replaced by exact mock counts)

| Part | Calls (approx.) | Cost |
|---|---|---|
| Clean stores: 272 sessions × 2 orientations × 2 extractions + retention and use-type calls (MPBench Stage-1 ratios) | ~2,900 | ~$1 |
| Re-extraction of poisoned sessions: 1 session ×100 scenarios; all sessions ≤ 8 × 100 | ~900 + classifiers | ~$1 |
| Query-time conflict checks (claim pairs with the same predicate, cached by pair) | ≤ 50k, likely far fewer | ≤ $3 |
| Answers + judge: 1,540 questions × 2 shapes × 10 scenarios × ~3 distinct contexts; SAFE-Mem contexts ~2× v2's | ~92k answers + 92k judgments | $12–18 |
| **Core total** | | **≈ $15–25** (cap $30) |
| Optional: A-MemGuard + LLM sanitiser on 1 session (≈ ¼ of the $18.50 four-shape cost, plus answers) | | +$5–8 (cap $40 overall) |

- The answer cache from v2 cannot be reused: SAFE-Mem contexts differ.
- **Engineering:** 2–4 days, comprising:
  - the adapter (ingestion, record binding, overlays, audits);
  - reuse of v2's scenarios and metrics;
  - a mock end to end with exact call counts;
  - a static-parity identity test (effects off must reproduce SAFE-Mem's own retrieval);
  - pre-registration and freeze.

## 7. Is it necessary for the ICML generalization claim?

It depends on which claim the paper makes.

| Claim | Evidence now | SAFE-Mem LoCoMo needed? |
|---|---|---|
| S's propagation mechanism transfers beyond MPBench's constructed workload | v2 + supplement: natural speakers, sessions and questions; H1, H2, H3, H5 transfer; same ranking against all published defences; 8/8 | **No** |
| S is a provenance-level policy usable on more than one memory system | two substrates, but confounded with the dataset | helpful (it separates dataset from substrate) |
| **SAFE-Mem + S, the system, generalizes** | none outside MPBench | **Yes** |

**Reviewer risk.**
- The objection is predictable: "the system evaluated on MPBench is never evaluated elsewhere, although SAFE-Mem's own paper ran LoCoMo".
- Answering it with "different substrate" is weak when the substrate is already in the repository.
- The objection is not fatal if the framing is honest, because the mechanism claim is well supported. But the omission can look like avoidance.

**The unknown is real (P3).** SAFE-Mem's conflict downgrading may already stop much of LoCoMo's poison, or cost utility. That would change S's marginal value on that system, and no current result tells us which way it goes.

## 8. Recommendation

1. **Do the minimum SAFE-Mem LoCoMo supplement** (§4): the 1-session and all-sessions hijacks, Original SAFE-Mem, R, C, M, S and SL, estimation-only, about $15–25 (cap $30; $40 with the optional published defences).
   - It turns the most predictable reviewer objection into evidence.
   - It separates the dataset from the substrate, giving three cells: MPBench/SAFE-Mem, LoCoMo/RAG, LoCoMo/SAFE-Mem.
   - It answers Q1.
   - Keep SAFE-Mem's dialogue ingestion (faithful to SAFE-Mem) and report the coarser root (P1) as a stated property, not a fix.
2. **Free steps first**, with no paid call:
   - adapter in a new folder;
   - mock end to end with exact call counts;
   - static-parity and freeze checks;
   - pre-registration note.

   Then a paid decision on the measured estimate.
3. **Whatever the result,** report it as a substrate check. Do not make it confirmatory, and do not merge it with v2.
4. **If you decide not to run it,** reframe the paper as "S, a provenance-level policy, evaluated on SAFE-Mem (MPBench) and on a turn-level memory (LoCoMo)", and state the limitation explicitly. In that case the LoCoMo tables PDF should not be titled "SAFE-Mem: results on LoCoMo" (it currently is), because it evaluates S on plain retrieval.
