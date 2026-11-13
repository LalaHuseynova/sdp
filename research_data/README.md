# MPBench Phase 1 artifacts

The scripts in `src/ams/research/phase1*.py` prepare data offline. They never
initialize a model, embedding service, transport, or budget client. The official
MPBench files, original SAFE-Mem code, historical run and protocol remain separate.

`mpbench_phase1/` is a generated inventory and **blank annotation workflow**,
not a completed annotated pilot. Its `composition_report.json` records readiness.
The preparation manifest fingerprints original inputs, the frozen write journal,
the protocol, preparation code/config and generated files. Rebuilding into a fresh
directory is deterministic on the recorded Python/PRNG version when the recorded
private identifier key is reused with `prepare --identifier-key`. The key affects
public names only; assignment weights, case selection and event chronology retain
the protocol's fixed seeds. Keep the key and ID mappings private until results are
locked. Hashing public seed/bag names without a key would allow profile enumeration.

- `public/candidate_inputs.jsonl`: original source text and source-boundary metadata,
  with opaque IDs and no added case labels/targets. This is a constructor input,
  not a full file to give an online agent.
- `private/case_index.jsonl`: original labels/targets, group membership, saved claims
  and diagnostic legacy IDs. These IDs are never security-bearing attribution.
- `private/blinded_packets.jsonl`: tasks, intended uses, sources and actual saved claims.
- `private/reviewer_{a,b}_template.jsonl`: blank record/use reviews.
- `private/utility_template.jsonl`: blank source-grounded utility questions.
- `private/duplicate_groups.jsonl`: duplicate/template components and review flags.
- `private/group_review_template.json`: explicit review of oversized components.
- `private/bag_validations_template.jsonl`: final-bag QA review, initially empty.
- `private/identifier_key.json`: private key for final runtime metadata IDs; never
  export it to a reviewer or defense. This is a research blinding key, not an API key.

Current packets contain saved **claims only**: actual evidence chunks were not
serialized by the old run. They support review preparation, but are incomplete for
final memory-bundle annotation under the unchanged four-evidence-slot protocol.
The builder blocks release even if all claim-only forms are completed. The optional
`prepare --evidence-catalog PATH` accepts an actual complete frozen/cached export
with one row per qualified original source case:

```text
cid, payload_hash, complete=true, exporter_fingerprint,
evidence_chunks=[{chunk_id, text, content_hash}, ...]
```

`payload_hash` and `content_hash` use `digest()` from `phase1_common.py`. The importer
checks full source coverage, source/text hashes and IDs; the trusted preparer must
independently establish that the export is genuine and has the correct original
configuration. It does not guess chunk boundaries or treat human-written replacement
text as the original chunk set. Imported chunks enter the same independently
reviewed packets with `record_kind="evidence_chunk"`. No such export currently exists.

Use `export-review` to give each independent reviewer only packets and blank forms;
do not give them the case index, another reviewer's votes or expected targets.
See [the annotation guide](../reports/PHASE1_ANNOTATION_GUIDE.md).

Future successful `build-pilot` output gives each R/C/M/S arm the **same shared
bundle digest**, not independently sampled runs. Its private event schedules include
future audit results. The trusted harness must call `runtime_view(episode, cursor)`
and pass only that returned object to a defense. It must control the cursor and
provide actual OS/tool isolation from evaluator files. Private files use mode 0600
and private directories 0700; this does not isolate arbitrary code running under
the same OS account. No autonomous runtime or sandbox is implemented in Phase 1.

`phase1_stress.py` supplies reviewed-input recipes for compromise, false accusation
and its matched correct-audit control, known copies, frozen noise and delay. These
are auxiliary preparation functions, not trust logic or experiments. False-accusation
construction additionally requires a separately reviewed 16-case reserve.

The config in `configs/research/mpbench_phase1.json` records fixed choices; it is
a documentary lock rather than a command-line tuning surface. Code/config changes
invalidate the preparation fingerprint. Do not modify the protocol to get a more
favorable result.

Generated artifacts and human reviews are locally ignored by this new directory's
`.gitignore`. Release suitably reviewed manifests, hashes and annotation provenance
as part of a future research release; do not mistake local preparation for a release.
