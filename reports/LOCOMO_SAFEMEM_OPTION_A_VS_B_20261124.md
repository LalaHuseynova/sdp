# LoCoMo + SAFE-Mem: Option A (full) vs Option B (reduced) — decision report

**Date and status:** 24 Nov 2026. Read-only analysis: no code, protocol or freeze changed, no API call.

**References:**
- `reports/PROTOCOL_V2_OPTION_B_20261115.md` (MPBench Option B)
- `reports/PROTOCOL_LOCOMO_SAFEMEM.md` (frozen `2ec7d1bc…`)

**Where the numbers come from.**
- The full-matrix mock on the dev conversations (conv-48/49), projected to all 10 conversations by question count (× 4.438).
- Distinct answer keys and their prompt lengths are counted from the mock build. Defence requests come from replaying the frozen v2 request recorder.
- Construction counts are exact (dry pass).
- P2 and P3 projections inherit the mock's context mix. The exact counts are recomputed free from the real contexts before P2/P3 are sent.

**Option B definitions** (as offered):
1. A-MemGuard and LLM Sanitiser on 2 hijack shapes (1-session, all-sessions) instead of 4.
2. Drop S2-BS, the A2 review-dilution conditions and the follow-up (boundary-verification) conditions from answering.

## 1. Exact experiment matrix

### 1.1 Identical in A and B

| Item | Value (both options) |
|---|---|
| Dataset, split | LoCoMo `locomo10.json` (SHA-256 `79fa87e9…`); held-out 8 = conv-26, 30, 41, 42, 43, 44, 47, 50; dev 2 = conv-48, 49 (reported separately) |
| Memory | Original SAFE-Mem, `v31_locomo_withhold` settings (withhold, hops 0, ≤ 20 claims per session, 4 evidence slots, k = 4) |
| Model | GPT-4o-mini (SAFE-Mem extraction, classifier, conflict checks, answers, judge; A-MemGuard and Sanitiser backbone); local MiniLM embeddings |
| Seeds | v2 generator 20261119; v2 draws 20261123; this study 20261124 (fp1 turn, late order, follow-up ticket) |
| Repetitions | 2 orientations × 5 draws per conversation; frame (no attack): 2 orientations × 5 draws of false accusations |
| Questions | all LoCoMo category 1–4 questions (1,540) in every condition |
| Statistics | conversation-level; exact sign-flip; Holm; descriptive (exploratory) |
| Stores | 112 per conversation, 1,120 in total (loc 40, sybil 30, shift 10, relay 20, embed 10, frame 2) |

### 1.2 Conditions per (conversation × orientation × draw)

| Family | Variant | Condition | MPBench cell | A | B |
|---|---|---|---|---|---|
| loc | 1s | A1 (2 of 8 poison detected) | localized / random detection | ✓ | ✓ retained |
| loc | 2s | A1 | localization curve | ✓ | ✓ retained |
| loc | quarter | A1 | localization curve | ✓ | ✓ retained |
| loc | spread | A1 | distributed | ✓ | ✓ retained |
| loc | 1s, 2s, quarter, spread | A2 (A1 + 10 safe reviews) | none (LoCoMo v2 addition, "review dilution") | ✓ | **✗ removed (4 conditions)** |
| fn20 | 1s, spread | 20% missed detections | imp_{localized,distributed}_fn20 | ✓ | ✓ retained |
| imp | 1s, spread | fp1 (one false flag) | imp_*_fp1 | ✓ | ✓ retained |
| imp | 1s, spread | late (half the questions before audits) | imp_*_late | ✓ | ✓ retained |
| imp | 1s, spread | fu (boundary verification) | random-detection `_fu` (appendix A3) | ✓ | **✗ removed (2 conditions)** |
| sybil | k2 | A1, fn20, fp1, late | sybil_k2, imp_sybil_k2_* | ✓ | ✓ retained |
| sybil | k2 | fu | sybil `_fu` (appendix A3) | ✓ | **✗ removed (1 condition)** |
| sybil | k4, k8 | A1 | sybil_k4, sybil_k8 | ✓ | ✓ retained |
| shift | 2s | O (audit-aware) | shift_batch | ✓ | ✓ retained |
| relay | r0.5, r1.0 | A1 | unlinked relays (H5) | ✓ | ✓ retained |
| embed | 1s | A1 (poison inside its session write) | none (ingestion sensitivity) | ✓ | ✓ retained |
| frame | fp1, fp2c, fp2s | false accusations, no attack | fp1 / harm to innocents (H6) | ✓ | ✓ retained |
| **Total per (conv × orient × draw)** | | | | **30** | **23** |
| **Total conditions** | | | | **3,000** | **2,300** |

### 1.3 Methods

| Method | Where it runs in A | B |
|---|---|---|
| Original SAFE-Mem (static), MemLineage | every condition | retained |
| R, C, M, S, SL, S2-ID | every condition | retained |
| S2-BS (appendix) | every condition | **✗ removed** |
| RandEC (local, free) | loc stores, 4 shapes, every loc condition | retained (free; the option does not touch it) |
| A-MemGuard | loc stores, **4 shapes** | **reduced to 1s + spread** |
| LLM Sanitiser | loc stores, **4 shapes** | **reduced to 1s + spread** |

## 2. Scientific impact of each removal

| Removed in B | Supports | Weakens generalization? | Already covered? | Evidence lost |
|---|---|---|---|---|
| **A-MemGuard + Sanitiser on 2s and quarter** | H3 extended: "S below every published defence" across the localization curve; the security–utility trade-off against published defences | **Yes, materially.** On LoCoMo/RAG, 2s and quarter are where S is *weakest*: ASR 12.7% / 5.1%, and U_all −5.9 / −10.7 vs A-MemGuard. They are the shapes where S's advantage over published defences is smallest and could fail on SAFE-Mem. Keeping only 1s and spread shows the two ends and hides the middle, which a reviewer can call cherry-picking | Only on plain RAG (LoCoMo v2 supplement, 4 shapes, 8/8). MPBench has no localization curve for published defences | S vs A-MemGuard / Sanitiser at partial localization on SAFE-Mem, the regime where the claim is most at risk |
| **A2 review dilution** (4 conditions) | No MPBench hypothesis. Robustness: "can safe reviews of the attacker's genuine turns dilute S/C/M?" | No. It is not part of the MPBench-to-LoCoMo transfer question | Yes, on LoCoMo/RAG (v2: safe reviews disable C, S = M) | Whether SAFE-Mem's session-level roots change review dilution (each safe review covers a whole session's records) |
| **Follow-up / boundary verification** (3 conditions) | MPBench appendix A3, not in H1–H6, excluded from the worst case | No | Yes, on MPBench (appendix) | An auditing-protocol variant on LoCoMo; secondary |
| **S2-BS** | MPBench appendix negative result; no claim planned | No | Yes, on MPBench | Nothing material. Its contexts almost always equal S/SL's, so it costs ≈ $0.03 |

## 3. Does B still support the main contribution?

| Evidence needed for "S's security–utility advantage generalizes on SAFE-Mem" | A | B |
|---|---|---|
| Localized poisoning: S vs R / C / M, ASR + key utility (H1) | ✓ | ✓ |
| Distributed poisoning: S vs M (H2) | ✓ | ✓ |
| Full localization curve (1s → spread) for internal arms | ✓ | ✓ |
| S vs every published defence, localized (H3) | ✓ | ✓ |
| S vs published defences across the localization curve | ✓ (4 shapes) | **partial (2 of 4)** |
| Adaptive attacks: Sybil k2 / 4 / 8, audit-aware shift, relays | ✓ | ✓ |
| Imperfect audits: missed, false positive, late | ✓ | ✓ |
| Harm to the falsely accused (H6) | ✓ | ✓ |
| Utility preservation (U_out, U_all, strict) | ✓ | ✓ |
| Ingestion sensitivity (embedded poison) | ✓ | ✓ |

**SL and S2-ID.**
- **SL** gets its key test in both options: relays r0.5 / r1.0 (H5) and every other condition. That is sufficient for "SL removes relay exposure at no utility cost" on SAFE-Mem.
- **S2-ID** cannot be evaluated *as S2-ID* on LoCoMo in either option: 0 of 1,529 questions are sensitive, so its gate never acts and S2-ID ≡ SL. This is the same as in LoCoMo v2. H4 on LoCoMo tests lineage only.
- **Consequence:** the paper's S2-ID claims must rest on MPBench (all three answer models). LoCoMo can only report "S2-ID ≡ SL here, by construction". No option changes this.

**Verdict.** B keeps every MPBench hypothesis cell and all adaptive and imperfect-audit evidence for the internal arms. Its one material loss is the published-defence comparison at 2-session and quarter localization: the regime where S's advantage is narrowest, and exactly the comparison a reviewer would check.

## 4. Cost vs scientific value

| | Option A (frozen) | Option B | Intermediate C (see below) |
|---|---|---|---|
| P1a construction (exact) | 8,548 calls, $1.65 (bound $10.73) | same | same |
| P1c conflict checks | ≈ 2,600 calls, ≤ $0.40 | same | same |
| P2 A-MemGuard + Sanitiser | **256,514 calls, $48.27** | **165,233 calls, $31.10** | 256,514 calls, $48.27 |
| P3 answer keys (answer + judge = 2 calls each) | **341,489 keys = 682,978 calls, $39.70** | **286,453 keys = 572,906 calls, $33.61** | 312,000 keys ≈ 624,000 calls, $36.23 |
| **Total projected** | **≈ $90.0** | **≈ $66.8** | **≈ $86.6** |
| Caps (construct / conflicts / defences / answers) | 12 / 3 / 60 / 55 = **$130** | 12 / 3 / 40 / 45 = **$100** | 12 / 3 / 60 / 50 = **$125** |

**Where B's ≈ $23 saving comes from (measured marginal savings):**

| Removal | Answer keys saved | P3 $ | P2 $ | Total $ |
|---|---|---|---|---|
| A-MemGuard + Sanitiser on 2s + quarter | 24,959 | 2.60 | **17.17** | **19.77** |
| A2 review dilution | 18,853 | 2.13 | — | 2.13 |
| Follow-up conditions | 10,962 | 1.34 | — | 1.34 |
| S2-BS | 222 | 0.03 | — | 0.03 |

So **85% of B's saving comes from the published-defence reduction**, which is the one scientifically material removal. The three other removals save about $3.50 together.

**Intermediate option C:** A minus A2 and the follow-up conditions.
- Keeps every MPBench hypothesis cell, all published defences on all 4 shapes, every adaptive and imperfect-audit cell, and S2-BS.
- Removes only the two conditions that are not MPBench main cells and are already covered: A2 on LoCoMo/RAG, follow-up on MPBench.
- Saves about $3.50 (4%) and needs a small change and a re-freeze. **The saving is too small to justify a re-freeze. It is listed for completeness, not recommended.**

**For context, the most expensive families in A** (marginal P3 cost): loc $11.18, relay $8.50, embed $4.07, sybil $4.04, imp $1.81, shift $1.34, frame $0.73, fn20 $0.08. Relay and Sybil are core adaptive evidence (H5; MPBench sybil_k), so cutting them would remove MPBench cells.

## 5. Recommendation: **Option A (the frozen full design)**

1. **Scientific validity.**
   - B removes the published-defence comparison exactly where S is weakest (2-session and quarter hijacks). It keeps only the two ends of the curve.
   - On LoCoMo/RAG that middle region is where S's margin over A-MemGuard shrank (−18.8 pt ASR at 2s) and where S lost 6–11 points of utility against it.
   - For an ICML generalization claim ("S beats published defences on SAFE-Mem across poison localization"), that is the comparison a reviewer will look for, and omitting it invites a cherry-picking objection.
2. **Cost.**
   - The difference is about $23 (≈ $90 vs ≈ $67). 85% of it is that one removal.
   - The other removals are scientifically minor and save only about $3.50.
3. **No re-freeze.** A is already frozen and verified (`2ec7d1bc…`). B and C would need code changes, re-testing and a new freeze.

**Classification:**

| | Experiments |
|---|---|
| **Essential** (the MPBench → LoCoMo/SAFE-Mem transfer) | loc 1s / spread A1 (H1, H2, H3); loc 2s / quarter A1 (localization curve); published defences on all 4 shapes; Sybil k2 / 4 / 8; shift; relay r0.5 / 1.0 (H5, SL); fn20, fp1, late (imperfect audits); frame fp1 / fp2c / fp2s (H6); internal arms R, C, M, S, SL; Original SAFE-Mem |
| **Supplementary** (useful, not required for the claim) | embed 1s (ingestion sensitivity); A2 review dilution; follow-up boundary verification; RandEC and MemLineage (both near-inactive on LoCoMo but needed for MPBench's method set) |
| **Redundant on LoCoMo** (kept because they cost ≈ nothing) | S2-ID (≡ SL by construction; reported as such); S2-BS (appendix, ≈ $0.03) |

**If the budget must be capped below A's $130:** approve A with caps lowered toward its projections (construct $12, conflicts $3, defences $55, answers $50 = $120). The strict guards stop each stage at its cap. The exact P2 and P3 counts are recomputed from the real contexts before those stages, so you see them before most of the money is spent.
