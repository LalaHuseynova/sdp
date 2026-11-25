# Learning to Contain Memory Poisoning Through Provenance

Research proposal, revised 2026-10-28. This is a proposed extension, not an implemented method, an established novelty claim, or a guarantee of conference acceptance. The verified original SAFE-Mem implementation should remain a separate baseline.

## 1. Central research question

Can sparse, noisy verification of one unsafe memory improve decisions about **uninspected related memories**, while controlling unnecessary restrictions on legitimate contributions and preserving access policies?

The central contribution should be learning **when, where, and how strongly to share safety evidence across memories**. Attaching a user ID, subtracting a constant trust penalty, and saving an incident as a lesson are useful baselines, but insufficient novelty claims by themselves.

The intended setting is shared memory with authenticated contributors. Contributors may be honest, mistaken, or compromised; they can contribute a mixture of useful and unsafe records. The system does not receive their hidden attacker labels. Everyone starts from the same weak prior over source risk. Equal initial treatment does not certify that every record is safe.

## 2. Proposed abstract

Shared memory allows an unsafe contribution to influence an agent long after ingestion and alongside useful contributions from the same source. Record-only filtering cannot use a verified incident to reassess uninspected related records, while blanket source penalties can suppress legitimate information and amplify false alarms. We propose an online approach that combines immutable provenance and deterministic access policies with learned, context-dependent risk inference. Each verified incident updates beliefs about the implicated record, its source, and its domain or incident group. Related memories are reassessed through those shared beliefs without being assigned fabricated negative labels. A hierarchical model learns when evidence should remain local and when it should transfer across a source's contributions. A verification policy allocates a limited audit budget and retains exploration to avoid self-confirming trust estimates. Access permissions remain independent of learned reputation and cannot be expanded by a high trust score. We propose evaluation on chronological shared-memory workloads with delayed feedback, mixed benign and malicious contributions, source compromise, and noisy verification. The primary hypothesis is that controlled propagation reduces future unsafe memory use at a fixed verification budget and matched legitimate utility, compared with both record-only defenses and naive user-wide penalties.

No empirical improvement is claimed in this abstract; the experiments below must establish or refute the hypothesis.

## 3. What is already established

| Related work | Relevant overlap | Consequence for positioning |
|---|---|---|
| [SAFE-Mem](https://arxiv.org/abs/2610.22959) | Claim authority, scope, provenance, and use-dependent retrieval | Combining provenance with permitted memory use is not a new contribution by itself. |
| [A-MemGuard](https://arxiv.org/abs/2510.02373) | Consensus validation and a separate memory of defensive lessons | Learning defensive lessons from past failures is already present in prior work. |
| [MemLineage](https://arxiv.org/abs/2605.14421) | Authenticated provenance and propagation through derivation lineage | A provenance graph and downstream influence tracking are established directions. |
| [Selective Memory for Artificial Intelligence](https://arxiv.org/abs/2603.15994) | Source reputation as a signal in memory write gating | Source reputation inside a memory system is not, on its own, a novelty claim. |
| [Trust propagation and structural containment](https://arxiv.org/abs/2609.17648) | Authorization boundaries containing compromised agent behavior | Hard permission enforcement must be distinguished from uncertain model judgments. |
| [The Beta Reputation System](https://aisel.aisnet.org/bled2002/41/) | Statistical reputation updates from feedback | A Bayesian reputation counter is an important baseline, not a sufficient new learning algorithm. |

These comparisons use inspected abstracts and the current checkout, not a complete systematic literature review. Full papers and additional recent systems must be checked before making a priority claim.

There is also direct overlap in this repository: `ClaimGraph.demote_source` in `src/ams/memory/graph.py` demotes claims associated with a source and walks their derivation descendants. This is code support for demotion; it does not establish that the published system learns online user reputation. The new contribution must go beyond adding that traversal.

## 4. Separate permission, relevance, and risk

The proposed three-way classification mixes distinct properties. A record can be relevant and dangerous, irrelevant and harmless, or useful but inaccessible to a particular requester.

Maintain separate quantities:

- **Authorization:** may this requester read or use this claim for this operation under the current policy?
- **Relevance:** how useful is the claim for the present request?
- **Unsafe-use risk:** how likely is using this claim in this request and context to produce a prohibited outcome?
- **Uncertainty:** how much reliable evidence supports that risk estimate?

Relevance affects retrieval priority. Irrelevance is not evidence against the contributor. A safe record requested by an unauthorized reader is an access mismatch, not evidence that its author is unsafe. A security document quoting a malicious instruction is not automatically an attack.

Hard authorization and SAFE-Mem's authority/scope rules constrain the candidate set before unauthorized content reaches the answering agent. A learned reputation score may make admission more cautious; it must never grant a role, enlarge a scope, bypass a permission, or override an authority cap. Recheck sensitive tool use at execution time.

Policies come from the trusted runtime or policy service, not text inside a memory. Derived records must retain the restrictions of the sources they actually depend on, with policy-version changes and revocation reflected in retrieval and caches.

## 5. Define the provenance unit carefully

Store authenticated contributor identity, ingestion actor, original source, source type, domain, timestamp, policy version, and derivation parents. Preserve claim-level links when an input yields several claims.

The person who uploaded a file, the person it quotes, and the agent that summarized it are not necessarily the same source. A forged author signature inside a document must not control attribution. A malicious external document must not automatically discredit the innocent user who asked for a summary.

The risk estimate should describe a contributor account or source **in context**, rather than an immutable judgment about a person's character. Start with source/domain/incident groups; only propagate across a broader account when the evidence supports that scope.

Assume initially that contributor identities are authenticated and cannot be forged or reset without cost. Test bounded identity rotation separately. No source-reputation method can promise protection against unlimited fresh identities whose contributions are otherwise indistinguishable.

## 6. Proposed learning mechanism

### Shared priors and contextual source state

Use the same weak prior for every new contributor, with visible uncertainty. If an optimistic prior is used, choose its strength on development data and report sensitivity. A score of one should not mean proven safety.

Use a hierarchical risk model combining:

1. Local content and request evidence.
2. A source's recent state in the relevant domain.
3. Artifact or incident membership and derivation relationships.
4. Independently verified evidence about the particular claim.

For example, an initial model can combine a trained local risk predictor with online source/domain and incident effects. Learn the relative influence of these effects across training streams and update their state online for previously unseen contributors. Compare this with a simple Beta reputation baseline before adding architectural complexity.

The proposed research contribution is deciding whether an incident is best explained by a local record problem, a shared artifact, a domain-specific source problem, or broader source compromise. An elaborate graph network is not automatically necessary or novel.

### Evidence updates and propagation

For each verified incident:

1. Record the evidence, verifier, policy context, confidence, affected claim, and attributable source or parents.
2. Deduplicate the incident using its original provenance. Paraphrased copies must not create independent votes.
3. Update the relevant source/domain/incident beliefs once.
4. Recompute risk for related uninspected records using the updated shared beliefs.
5. Audit or quarantine the records whose risk and uncertainty justify intervention.

**Do not turn all related records into new negative training labels.** That would fabricate evidence and create an escalating self-confirmation loop. Propagation changes a prior belief about a record; it does not prove that the record is unsafe.

Different relationships justify different treatment. A derived claim that still depends on a demonstrated bad premise may need invalidation or recomputation. An unrelated, independently verified claim from the same contributor should generally receive a smaller change. A shared artifact or recent compromised interval may deserve stronger reassessment than an old contribution in another domain.

Do not duplicate a verification event across every derived copy. Revoked trust or quarantine should be reversible through independent re-verification. Passive time alone should not erase verified evidence in a way an attacker can exploit simply by waiting.

### Lessons and verification

Store lessons as structured, auditable events rather than unrestricted instructions inserted into the agent's control context. Suggested fields are record ID, root source, event time, intended use, violated rule, evidence reference, verifier reliability, and review status.

Distinguish a detector's allegation from confirmed evidence. A confident LLM assertion is not automatically a reliable label. Use policy violations, tool outcomes, authenticated corrections, or independently calibrated audits where possible. Unsafe outcomes must not be attributed to a contributor merely because their record appeared somewhere in the context.

Allocate a bounded verification budget to uncertain and potentially consequential records, including a small randomized audit of records the system would otherwise withhold or trust. Log audit probabilities. Without this exploration, a system that stops retrieving a source's records can mistakenly conclude that it has learned that source is bad forever.

Maintain a separate evaluation oracle. The same LLM should not supply the online accusations and be the sole judge of the method's success.

## 7. Formal problem and research targets

Let G_t be the authenticated provenance graph and H_t the evidence available before request t. Estimate contextual unsafe-use risk r_t(m, q, operation | G_t, H_t, policy). The learned retrieval and verification strategy selects from the deterministically authorized and SAFE-Mem-admissible set.

The task objective is to reduce cumulative unsafe outcomes and lost legitimate utility under a fixed verification budget. This is a partially observed online decision problem: at deployment, most record labels are not available. A training loss that assumes all hidden labels are known would not match the claimed setting.

Report a tradeoff curve instead of selecting arbitrary cost weights that make the proposed method look best. Compare methods at matched legitimate utility and matched verification expense.

Possible formal work, to be established rather than claimed in advance:

- Prove the system's learned risk updates cannot expand authorization, conditional on correct runtime policies and provenance. This is a supporting invariant, not the main novelty.
- Derive a bound on unnecessary source-level restrictions in a simplified setting with representative audits, controlled verifier error, and stated assumptions about within-source dependence. Adaptive selection and delayed feedback must be reflected in those assumptions.
- Explain the limits of transfer: when record hazards are independent of contributor identity after conditioning on content, source-level propagation need not help. This provides a useful negative-control regime.

Do not promise universal safety, conformal coverage under arbitrary adaptive attacks, or regret bounds without the corresponding assumptions and proofs. Marginal record-risk estimates also do not automatically bound the risk of a combination of individually innocuous records.

## 8. Dataset and evaluation redesign

Create a separate, versioned chronological benchmark rather than silently relabeling an original dataset as naturally multi-user.

- **MPBench:** preserve original payloads and labels, then add an explicitly synthetic overlay of authenticated contributors, roles, policies, and event times. Ensure a source can contribute both legitimate and unsafe records.
- **EHRAgent/MINJA:** retain actual shared-user provenance where available, but expose opaque contributor IDs rather than literal IDs such as `attacker` and `victim`. Keep hidden adversary labels only in the evaluator. Resolve the already documented upstream prediction-extraction problem before reporting task accuracy.
- **LoCoMo:** use speaker identity and benign recall as utility controls. Any added access rules or injected attacks are a separately labeled extension, not original LoCoMo annotations.

Role assignment must not encode the attack label. Neither usernames nor permissions should reveal which users are adversarial. A classifier must not get a shortcut such as all attackers being guests and all benign users being administrators.

Include a regime in which static policy checks already block cross-scope violations, and a distinct regime where contributors are authorized to contribute and share but their permitted records can still be false or unsafe to use. The latter tests a limitation that static authorization alone does not settle. State explicitly that this broadens the source-trust assumptions of the original SAFE-Mem setting.

Every episode starts from a common initial state. Ingestions, requests, audits, corrections, and policy changes occur in a defined order. A prediction at t can use only evidence observed before t. Training, development, and test episodes must separate contributor identities, templates, and attack families as appropriate.

The current MPBench runner writes a pooled store and then evaluates reads concurrently. It cannot be used unchanged to establish a chronological online-learning claim. Add a new runner with deterministic evidence commits between rounds; keep the original runner and original SAFE-Mem baseline intact.

## 9. Decisive experiments

The most important test is **transfer to related records that have not themselves been verified**.

Give methods the same initial state, candidate records, and one verified incident at the same time. Then measure subsequent unsafe use and legitimate recall on held-out records from the same source and on unrelated sources. In this diagnostic, hold the local content detector and feedback sequence fixed so that the propagation mechanism is the component that differs. Follow with a realistic experiment where the verification policy selects its own audits under a common budget.

Stress the assumptions with:

- Mixed benign and malicious contributions from the same account.
- An honest account that is later compromised, benign warm-up, and intermittent attacks.
- A false accusation against an innocent source and its recovery.
- Repeated and paraphrased copies with common provenance.
- Innocent uploaders relaying an attacker's document or a benign security example.
- Policy revocation, cross-domain reuse, and allowed sharing among equal-role users.
- Delayed or erroneous verification, bounded fresh-account attacks, and attempts to poison lesson records.
- A negative control where source identity carries no additional risk information.

The method should not be credited for simply refusing more requests. Include benign contributions from suspicious sources and measure collateral loss explicitly.

## 10. Baselines, ablations, and measurements

Essential comparisons, under identical policies and candidate retrieval:

1. Original SAFE-Mem.
2. SAFE-Mem plus the same local risk detector, without source updates.
3. Naive global user penalties: the initial research idea.
4. Source/domain Beta reputation or a simple recent-history score.
5. Provenance descendant invalidation without learned source-level transfer.
6. A-MemGuard with its published lesson-learning mechanism, not just a consensus-only substitute.
7. An identity-blind version of the proposed learner.
8. The proposed mechanism with global, domain, and incident effects removed one at a time.

Compare fixed and learned propagation strength, verified and noisy feedback, and uniform and learned audit allocation. All methods must have the same audit opportunities or an explicitly matched audit cost. Do not give the proposed method a stronger verifier than its baselines.

Primary measurements:

- Cumulative unsafe answers and executed actions over a chronological episode.
- Future unsafe use from unverified records after a source incident.
- Legitimate recall and answer accuracy, including benign records from penalized sources.
- Unnecessary restrictions on innocent contributors and recovery after a false alarm.
- Privacy/access violations in the supplied context, answer, and tool calls.
- Verification calls, tokens, latency, and adaptation delay.
- Calibration and uncertainty of risk predictions.

Plot safety/utility and safety/verification-budget curves, not only an aggregate attack-success number. Use multiple independent episodes and seeds, with uncertainty intervals that respect contributor and trajectory clustering.

## 11. What would make or break the paper

A stronger ICML case would show that a learned rule for sharing sparse evidence across records generalizes to unseen sources and attacks, beats simple reputation rules at matched utility and audit budget, and avoids amplifying false accusations. A careful sequential benchmark and a meaningful statistical analysis would support that claim.

The central hypothesis is weakened if the gains disappear when feedback, permissions, source labels, and utility are controlled; if source-wide constant penalties perform equally well; if all improvement comes from extra LLM calls; or if the method succeeds only when each simulated source is entirely good or entirely bad. Those outcomes should change the research direction rather than be hidden by additional components.

Start with the smallest pilot that can resolve this: fixed policies, one local detector, record-only defense, naive user penalties, and a source/domain/incident learner. Introduce verification-budget learning only after the source-transfer effect is established. This keeps the research question testable before building a large framework.

## Revised contribution statement

We study how an agent can learn the scope of distrust in shared memory. A verified unsafe contribution updates uncertain beliefs about its provenance and selectively changes the treatment of related, uninspected records, while deterministic permissions remain binding. The contribution to test is whether this evidence sharing improves future safety per verification call without sacrificing legitimate contributions from the same source.
