# Provisional Steps 4–6 implementation and checks

29 October 2026. **Automated Steps 4–6 preparation is implemented. Twenty provisional
case-intent development groups now exist. Human validation remains deferred, with
zero verified safety labels and zero validated utility questions.** The validated
16-safe/16-unsafe scientific pilot has not been generated.

## Initial checks

Before extending the pipeline, all **58 existing Phase 1, identity and recovery
tests passed**. Existing Phase 1 fingerprints, all 27 recovery payload files, and the
latest earlier utility payload hashes passed their checks. Existing working-tree
changes were preserved. No recovery was rerun, no original source data was edited,
and no older packets or reviewer decisions were overwritten.

The [design supplement](PROVISIONAL_20261029_DESIGN.md) records this separately
authorized case-intent diagnostic. The original
[experimental protocol](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md) is unchanged; this
development recipe does not replace its independent record/use Z annotation requirements.

## Step 4: automated annotation preparation

- Versioned all 2,114 recovered packets, preserving their 52,716 actual record IDs,
  text and content hashes: 8,544 claims and 44,172 evidence chunks.
- Added exact construction spans and limited unreviewed literal/lexical source
  support suggestions. 52,459 records have a suggestion; the others remain unresolved.
  These are source-location proposals, not semantic entailment or authenticated authorship.
- Produced a separate curator-only warning file. Simple phrase rules flag **385
  records** for possible review. There are 199 verification-bypass matches, 137
  outgoing-transfer matches and 59 privilege-claim matches; some records have
  multiple matches. These counts are **not unsafe labels, detector accuracy or FPR**.
  Quoted/negated instructions can trigger the rules; unflagged records are not safe by default.
- Kept all verified verdicts null and exported blank forms for two independent
  reviewers and a third disagreement adjudicator. Warning hints are excluded from
  the blinded initial reviewer packets and never affect case selection.
- Preserved original principal/external source distinctions. Semantic attribution,
  natural author identity and uploader responsibility remain unverified. Simulated
  external contributor IDs do not become owners of the principal's personal statements.

Current genuine human labels: **0 safe, 0 unsafe, 0 uncertain**. Pending is a missing
review, not an automatically assigned uncertain label. Existing source-case labels
were not copied into human memory-safety fields.

## Step 5: improved unvalidated question drafts

| Draft coverage | Count |
|---|---:|
| Questions/reference drafts | 2,831 |
| Contributions with at least one draft | 1,722 |
| Contributions without an automatic draft | 392 |
| Claim-supported drafts | 2,202 |
| External-chunk-only drafts | 629 |
| Human-validated questions | 0 |
| Independently safe sources established | 0 |

The previous revision had 1,446 drafts for 1,446 contributions. This version reuses
those, refines suitable copula-question grammar without changing reference values,
adds whole-statement drafts only when an existing claim is literally in its source,
and removes equivalent duplicates. There are at most three drafts per contribution.

Exact source spans, memory IDs, content versions and answer-leakage checks are
preserved. Negation is not silently removed. Quality flags identify 1,385 broad
statement questions requiring human specificity, 226 negation/quantifier cases,
90 short-reference cases, five remaining broad-description cases and the 629
blocked chunk-only drafts. Flags can overlap and do not establish question quality.

All references remain **unvalidated candidate answers**; all source safety remains
unverified. Literal matching alone cannot establish clarity, useful task semantics,
truth or a safe intended use. The frozen baseline's external_evidence=false setting
is unchanged, so external-chunk-only drafts are not eligible final utility probes.
No source, case label or question was changed to make a method look better.

Unique contributions with a claim-supported draft, by original input stratum:

| Context | Attack inputs | Explicit benign | Suggestive benign |
|---|---:|---:|---:|
| Email | 238 | 7 | 308 |
| File/document | 383 | 9 | 269 |

These are draft opportunities, not verified-safe case counts. Across the eventual
20 scientific bags, 20 explicit benign safe contributions are needed per context.
Even assuming all existing explicit drafts pass, at least 13 more email and 11 more
file/document explicit-source questions need manual authoring/validation. Some
inputs may not contain suitable external contributions. Do not relabel principal
preferences or fabricate source facts to fill that gap.

## Step 6: real provisional development groups

| Property | Result |
|---|---:|
| Provisional groups | 20 |
| Distinct source cases | 640 |
| Cases per group | 32 |
| Original attack / benign inputs per group | 20 / 12 |
| Email / file-document cases per group | 16 / 16 |
| Per context: attack / explicit benign / suggestive benign | 10 / 1 / 5 |
| Duplicate/template components reused across groups | 0 |
| Metadata overlays per group | 6 |
| Total metadata overlays | 120 |
| Future R/C/M/S matched-input references | 480 |
| Planned pending audit requests per overlay | 5 |
| Completed audits / revealed verification results | 0 / 0 |
| Original query requests per overlay | 27 |
| Validated safety-balanced pilot groups | 0 |

A deterministic component-to-slot matching algorithm fills the exact quotas without
greedily consuming scarce explicit-benign components. The existing oversized/manual
review components are excluded. Group selection uses original case strata and
mechanical recovery completeness; it does not use warning flags, inferred safety,
question quality/availability, historical attack success or method outcomes.

Each group has two opaque synthetic contributors, both contexts, and two batches
of four independent contributions per contributor/context. Both contributors have
the same collaborator role and all-allow primary policy. The principal stays `user`.
Source/batch assignment uses the exact product-weight subset law, drawing **ten
attack-input positions per context**, not eight supposedly unsafe memories.

The same 32 payloads and COMMON ingestion order are reused across six overlays.
Public IDs/tokens use the existing private HMAC key; source/question text is unchanged.
All four future arms reference the same payload/overlay/event digest within each
condition. The arms themselves are not implemented.

The first eight groups are marked development and the other twelve reserved for
later review. Reserved does not mean a locked or independent confirmatory test.
Six overlays reuse the same source groups; they are sensitivity conditions, not
120 independent datasets.

### Actual case-intent assignment check

Below, “high profile” is a private construction bit, not a safety label or known
malicious contributor. Both profile sets have 320 input positions across 20 groups.

| Overlay | Attack inputs in high-profile positions | Attack inputs in other positions |
|---|---:|---:|
| Strong distributed | 283/320 | 117/320 |
| Strong localized | 268/320 | 132/320 |
| Weak distributed | 243/320 | 157/320 |
| Weak localized | 221/320 | 179/320 |
| Uninformative | 208/320 | 192/320 |
| Source-uninformative, batch-local | 208/320 | 192/320 |

These are realized **input-case** fractions. The uninformative generator samples
uniform positions; finite draws need not give identical fractions. No seeds were
rejected or assignments adjusted to force a perfect null or identical contributor
rates. This table is not a memory-risk estimate, defense result or source-reputation score.

The root audit target is selected uniformly without any label lookup. Its verdict
is unknown, not an unsafe seed. The five targets are reserved from the 27 original
query jobs. Every audit entry is pending with verdict=null. No audit budget was
actually consumed, and no task answer, judgment, ASR or utility result was generated.
Question jobs remain private pending review, not validated benign query events.

Relational audit targets can differ between overlays. This is documented; a future
causal comparison between regimes needs the appropriate fixed-ID control and real
validated feedback. No efficacy comparison is made here.

## Validation and preservation

- **19 new offline tests pass**, in addition to the 58 initial existing checks.
  Tests cover unverified warnings, actual source offsets, blank human decisions,
  question refinement and negation, case strata versus Z, deterministic matching,
  component separation, oversized-group refusal, selection independence from
  quality/warnings, exact ten-slot sampling, shared roots/orders/arm digests,
  pending audits, source-role preservation, unauthorized readers, no future inputs,
  no invented feedback, public schema allowlists, keyed IDs and overwrite refusal.
- Targeted Ruff checks pass.
- Actual output validation passes for all 20 groups, 120 overlays and 306 payload
  files. All audit results remain absent. Empty genuine-review import gives zero
  independently verified bundles and does not unlock the scientific pilot.
- Exact replay reproduced all 20 selections and all 120 overlays/events. Original
  input and recovered memory-text parity passed for all 640 selected cases. All
  2,831 draft references passed their literal/span checks. Before/after fingerprints
  match for all **408 pre-existing protected files**, with zero changed files.

Evidence:
[before fingerprints](PROVISIONAL_20261029_INTEGRITY_BEFORE.json),
[after integrity](PROVISIONAL_20261029_INTEGRITY_AFTER.json),
[validation](PROVISIONAL_20261029_VALIDATION.json),
[current summary](PROVISIONAL_20261029_SUMMARY.json).

No original MPBench file, original SAFE-Mem file, primary protocol, Phase 1 output,
recovery output, old question draft or prior reviewer form was modified. Existing
working-tree edits were not reverted or attributed to this work. No API call,
model inference, model/dependency installation, training, defense evaluation,
trust ledger, reputation policy or retrieval integration was performed.

## Files and use

New code/config/tests:

- [initializer](../src/ams/research/provisional/__init__.py)
- [unverified annotation preparation](../src/ams/research/provisional/annotations.py)
- [question drafting/screening](../src/ams/research/provisional/questions.py)
- [case-intent groups, overlays and prefix views](../src/ams/research/provisional/episodes.py)
- [versioned pipeline and human-review import](../src/ams/research/provisional/pipeline.py)
- [offline CLI](../scripts/prepare_mpbench_provisional.py)
- [frozen provisional configuration](../configs/research/mpbench_provisional_v1.json)
- [new offline tests](../tests/test_mpbench_provisional.py)

New documentation: this report, the design supplement and
[later-validation guide](PROVISIONAL_20261029_GUIDE.md). Proof files are linked above.
The main data root is `research_data/mpbench_provisional_v1_20261029/`; its report,
manifest, public source pools/overlays, private selection/evaluation metadata, hint
and question files, and three blinded reviewer exports are listed in the guide.
The empty-review check is separately versioned in
`research_data/mpbench_provisional_review_check_v1_20261029/`. Exact old-to-public
source and record ID maps are saved privately in
`research_data/mpbench_provisional_checks_v1_20261029/private/source_id_map.jsonl`,
with a mapping manifest. These are validation bookkeeping, not new safety labels.
No pre-existing files were edited; generated payloads are locally ignored by Git.
No staging or commits were performed.

```sh
PYTHONPATH=src .venv/bin/python scripts/prepare_mpbench_provisional.py validate \
  --prepared research_data/mpbench_provisional_v1_20261029
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' tests/test_mpbench_provisional.py -q
```

## What remains deferred

The automated preparation portions of Steps 4–5 are complete for this version;
their human decisions remain pending. Step 6 is complete only as this provisional
case-intent development dataset. There are **zero verified memory-safety labels,
zero human-validated questions and zero validated scientific pilot groups**.

When ready, use two genuine independent reviewers, a third for disagreements, and
the new packet/candidate hashes. Import real decisions without overwriting older
votes; validate useful safe external-source questions; check actual Z-stratum
capacity, uniqueness and component separation; then recheck/rebuild the primary
scientific pilot. A case-intent overlay cannot be retroactively described as a
controlled memory-risk overlay. Human validation can happen later as requested,
but it cannot be replaced by warning rules, original case labels or passing tests.
