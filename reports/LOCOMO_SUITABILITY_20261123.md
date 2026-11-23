# Is LoCoMo suitable as the paper's second dataset? (free review, 23 Nov 2026)

**Sources:**
- `data/locomo/locomo10.json`: statistics recomputed locally today;
- from branch `sdp/locomo-backup`: `reports/LOCOMO_FEASIBILITY_20261119.md`, `reports/LOCOMO_PILOT_20261119.md`, `reports/PROTOCOL_LOCOMO_V1.md` and the v1.1/v1.2 amendments.

**Not opened:** the partial v1.1 run outcomes (`research_data/locomo_v1_run/`). They stay sealed until the one frozen analysis. No paid call; nothing changed.

## Verdict

**Yes, suitable, in a specific role:** an external check of the *utility side* and a *regime map* on natural provenance. It is **not** a second proof that S beats everything. In this role it also answers the strongest reviewer criticism (W1, "the result is built into the workload") better than any other available dataset.

## Data facts (verified today)

- 10 conversations, each with exactly 2 speakers.
- 19–32 timestamped sessions and 369–689 turns per conversation.
- 1,540 QA items in categories 1–4, with evidence turn ids written by LoCoMo's authors.
- CC BY-NC 4.0 (research use is fine).

## Fit with what S needs

| S needs | LoCoMo | OK? |
|---|---|---|
| Sender identity on every memory | speaker = contributor | ✅ natural |
| Several deliveries per sender | session = batch (19–32 per sender) | ✅ natural, timestamped |
| Poisoned and legitimate items from the same sender | hijacked speaker: poison turns + their own real turns in other sessions (the key stratum) | ✅ |
| Utility labels we did not write | evidence ids per question | ✅ **the main gain over MPBench** |
| Several contexts per sender (context gate across contexts, contributor gate) | context = conversation, one per speaker | ❌ the contributor (source) gate can never fire |
| An innocent third party | only 2 speakers, one of them the principal | ❌ no innocent-contributor control |
| A real attack | the template and wrong values are ours (random answers from another conversation, often incoherent → ASR only ~46%) | ⚠️ ours, conservative |
| SAFE-Mem's own store | turn-level RAG (LoCoMo's RAG setting), not SAFE-Mem's claim store | ⚠️ original SAFE-Mem and published defences are not compared on LoCoMo |

## Why it helps the paper (vs the ICML review weaknesses)

1. **W1 (result by construction):** on LoCoMo the hijack start is **uniform at random** and only its *length* varies (1 session, 2 sessions, ¼, spread). S's advantage then appears or disappears as a function of a natural parameter. This is essentially the "localization sweep" proposed in the ICML review, on data we did not design.
2. **Synthetic contributors / utility labels written by us:** the speakers, sessions and questions are LoCoMo's.
3. **Honesty:** the protocol pre-registers where S *loses* (H4, a 2-session hijack, is predicted to fail) and that S ≡ M under mixed audits.
4. **Precedent:** other 2026 papers also poison LoCoMo (ER-MIA 2602.15344; the Nous provenance-capped defence 2606.22030), so reviewers will accept the setup.

## Evidence so far (exploratory pilot, 2 conversations, $0.22)

| Hijack × audits | Result |
|---|---|
| 1 session, incident audits (A1) | ASR S 0 = C = M; accuracy on the hijacked speaker's unaffected sessions **S .38 vs C/M .10** (+.28; the same sign in both conversations) |
| 2 sessions, A1 | S keeps utility but **leaks: ASR .29 vs 0** (S's security cost) |
| Mixed audits (A2) | C fails (ASR = no defence); **S ≡ M exactly** |
| Spread | S = C = M |
| Memory owner's questions | ≈ .43 under every arm (no collateral damage) |

## Risks to manage

| Risk | Status / mitigation |
|---|---|
| Only 8 confirmatory conversations | Exact sign-flip test; the smallest p is 1/256, so a pass needs nearly all conversations to agree. Already pre-registered |
| The LoCoMo LLM judge accepts wrong answers (independent audit cited in 2606.22030) | The protocol already has a Haiku κ check and official F1 as robustness. Keep both |
| Weak, incoherent attack (46% ASR) | P2 (same-conversation wrong values) is pre-declared as the stronger secondary attack; it raises ASR for every arm equally |
| S's advantage over M exists only with incident-only audits (A1) | Say so: under mixed audits S = M on LoCoMo |
| No SAFE-Mem or published-defence comparison | State it; those comparisons stay on MPBench (already in the protocol) |
| Run infrastructure | The v1.1 run stopped by rule S2 (budget-DB failures on WSL), not a method issue; v1.2 fixed and re-froze it (`f04cc850…`) |

## Decision needed (owner)

Approve the LoCoMo v1.2 resume:
- about **$6.25** remaining (calibrated estimate; finished calls replay at $0);
- caps $30 + $1 (Haiku judge check);
- it runs on the co-author's machine, where the run state lives.

Then present the result in the paper as a **regime map**, not a blanket win.
