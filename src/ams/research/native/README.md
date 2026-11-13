# Cache-only native memory stores

> Status note — 7 November 2026: These base stores were prepared and then used by the separately frozen provisional comparison. The base construction leaves external origins unknown; later provisional preparation applies the declared synthetic overlay and saved AI origin proposals in a new state. That later attribution remains an experimental assumption, not authenticated natural authorship. See the [current research guide](../README.md) and [project README](../../../../README.md).

This package prepares new research-owned Original SAFE-Mem stores for the
existing provisional 32-case groups. It does not construct validated pilot
groups, reveal feedback, run retrieval/answer experiments, contact an API, load a
model, download a tokenizer or install dependencies.

```sh
.venv/bin/python scripts/prepare_dynamic_native.py prepare --out research_data/my_new_native_stores
.venv/bin/python scripts/prepare_dynamic_native.py check --bundle research_data/my_new_native_stores
.venv/bin/python -m pytest tests/test_dynamic_native.py
```

The CLI blocks socket connections, requires a new output directory and has no
paid-execution option. Existing MPBench, Original SAFE-Mem, caches, review forms
and earlier preparation outputs are read-only. A miss or mismatch is reported as
an unavailable native store; an incomplete graph is not published as complete.

## Construction and checks

`ConstructionCache` reads existing immutable SQLite responses using exact original
request keys. GPT-4o-mini chat responses and 384-dimensional MiniLM vectors must
already exist. Missing usage/model/text/vector fields are not invented. Only
response-dataclass defaults are supplied where older cache formats omit them.
The client has no provider delegate, SDK, retry or model fallback.

`ObservedMemory` calls the original `write`, extraction, retention, chunking,
embedding and graph code. It observes source creation at each contribution's
explicit construction boundary. Principal/artifact roots are created before
sentence indexing; each indexed sentence is aligned literally to its actual
parent text. Repeated display labels or identical text do not merge sources.
After construction the observer is removed: the runtime memory is exactly
`TypedStandingMemory`, preserving the strict retrieval type boundary.

Every contribution is checked against existing saved/recovered records:

- Claim count, order, exact raw text, hashes, type, standing, usable kind,
  subject, initial contested flag and structural parent artifact.
- Chunk count, order, exact text/hash, parent artifact and supporting spans.
- Complete native source/record mappings, artifact permissions, index vectors,
  and registration in the current evidence snapshot.
- Cached classification and query embeddings for the original questions, without
  running those questions through retrieval or answering.
- Lossless graph/index/client/classifier/RNG state save/load.

Native source/claim/chunk IDs are allocated afresh. Crosswalks join recovered
logical records to actual newly constructed IDs after content/structure checks;
historical IDs never become new native IDs by assumption. The ingestion order is
the existing COMMON provisional-ingestion permutation, identical for every arm
and correlation variant sharing that bag. This is the all-ingest primary setup;
it does not create compromise/streaming trajectories.

## Attribution and label boundary

Principal records have separate roots owned by the original `user` principal.
External origins remain unknown. In particular, original lexical `_overlap`
claim assignment is retained as a structural link but cannot create an
authenticated contributor or source penalty. Ambiguous external claims inherit
all plausible contribution-artifact permissions, including endorsement parents.
Literal claim-support spans remain unreviewed candidates; exact chunk construction
spans are not semantic safety labels.

Only `Register` events are created. No audit outcome, safe vote, unsafe label,
case label, expected target, hidden risk profile or future verdict is copied into
runtime state. Private historical joins are used only for verification. Raw
review packets and any human decisions remain unchanged.

The outputs do not authenticate natural authorship. Before scientific execution,
independently checked provenance and the declared synthetic contributor/batch
overlay must be applied in a new initial-state version. Unknown origins cannot
be promoted silently by editing these frozen ledgers. No claim of selective
propagation efficacy follows from preparing these stores.

## Artifacts and use

Each opaque group directory under `private/` contains:

- `initial_state.json.gz`: complete original memory, vectors, exact replay tables,
  binding catalog, all-allow artifact policy, registration-only evidence and RNG.
- `construction_crosswalk.json.gz`: per-record new native IDs, original logical
  IDs, exact source spans, verification status, cache receipts and prompt-size
  inspection. This file is controller-only and is not a model prompt.
- `arms.json`: R/C/M/S descriptors pointing to the same immutable base snapshot.

One base snapshot avoids four redundant disk copies. `load_store` creates a fresh
graph, indexes, clients and classifier cache on every call:

```python
from pathlib import Path
from ams.research.native.pipeline import load_store

root = Path("research_data/my_new_native_stores")
r_state = load_store(root, opaque_group_token, "R")
s_state = load_store(root, opaque_group_token, "S")
```

Loaders verify hashes/runtime locks and then validate the real native bindings.
No provider or budget is opened. Attaching a session and any later scientific
dispatch remain subject to the existing execution preflight and the user's
single USD 30 total API ceiling.

## Limits

These are new stores built from frozen cached replies, not the full historical
6,240-case graph or its query/conflict state. Historical visible claim metadata
and recovered text/spans are matched; complete historical object/relation fields
were not saved and are not independently verified. Those fields in the new
stores come from the exact cached extractor reply. Run static SAFE-Mem in the
same future workload before attributing differences to propagation.

Original `max_claims=6` is retained per extraction call. Separate principal and
external passes may together produce more than six claims; no new case-wide
truncation is introduced. Grounded utility drafts are not promoted to validated
questions or purchased classifier responses by this preparation.

Prompt inspection renders conservative longest-field answer/conflict contexts
without retrieval/model calls. The UTF-8 byte/scaffolding proxy is not measured
GPT tokenization or a guaranteed token bound. Billing reservations remain
independent of that proxy. Future finalized questions, changing conflict state
and newer records require updated request inspection and cost estimates.
