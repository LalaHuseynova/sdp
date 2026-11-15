"""Protocol v2 freeze (plan.md step 2.2): the SHA-256 manifest, its verification and the
paid-stage gate. Offline; no model call."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ams.research.dynamic.models import LedgerError, digest
from ams.research.protocol_v2 import analysis as A
from ams.research.protocol_v2 import freeze as F
from ams.research.protocol_v2 import registry as REG

SPEC = {"source_files": ["src/**/*.py"], "dataset": ["data/*.jsonl", "data/manifest.json"]}


def _repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    (root / "src/pkg").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "src/pkg/a.py").write_text("x = 1\n")
    (root / "src/pkg/b.py").write_text("y = 2\n")
    (root / "data/rows.jsonl").write_text('{"a": 1}\n')
    (root / "data/manifest.json").write_text("{}\n")
    return root


def _prepare(tmp_path):
    root = _repo(tmp_path)
    out = tmp_path / "freeze/protocol_v2.json"
    saved = F.prepare(out, root=root, spec=SPEC, hf_root=None)
    return root, out, saved


def test_prepare_then_verify_is_clean_and_refuses_to_overwrite(tmp_path):
    root, out, saved = _prepare(tmp_path)
    body = json.loads(out.read_text())
    stored = body.pop("protocol_v2_digest")
    assert stored == saved["protocol_v2_digest"] == digest(body)
    assert set(body["hashes"]) == set(SPEC)
    assert F.compare(out, root=root, spec=SPEC, hf_root=None)[1] == []
    assert F.verify(out, root=root, spec=SPEC, hf_root=None) == stored
    with pytest.raises(LedgerError, match="overwrite"):
        F.prepare(out, root=root, spec=SPEC, hf_root=None)


@pytest.mark.parametrize("change", ["edit", "add", "delete"])
def test_any_changed_added_or_missing_file_fails_verification(tmp_path, change):
    root, out, _ = _prepare(tmp_path)
    if change == "edit":
        (root / "src/pkg/a.py").write_text("x = 2\n")
    elif change == "add":
        (root / "src/pkg/c.py").write_text("z = 3\n")
    else:
        (root / "data/rows.jsonl").unlink()
    diffs = F.compare(out, root=root, spec=SPEC, hf_root=None)[1]
    expected = {"edit": "source_files:src/pkg/a.py", "add": "source_files:src/pkg/c.py",
                "delete": "dataset:data/rows.jsonl"}[change]  # fmt: skip
    assert diffs == [expected]
    with pytest.raises(LedgerError, match="changed since the freeze"):
        F.verify(out, root=root, spec=SPEC, hf_root=None)


def test_an_edited_manifest_is_refused(tmp_path):
    root, out, _ = _prepare(tmp_path)
    body = json.loads(out.read_text())
    body["protocol"]["statistics"]["seed"] = 1  # e.g. a quietly changed bootstrap seed
    out.write_text(json.dumps(body))
    with pytest.raises(LedgerError, match="edited after"):
        F.verify(out, root=root, spec=SPEC, hf_root=None)


def test_paid_gate_needs_the_approval_to_name_this_freeze_and_the_frozen_inputs(tmp_path):
    root, out, saved = _prepare(tmp_path)
    ds = saved["protocol"]["dataset"]
    bundle, stage1 = root / ds["bundle"], root / ds["stage1"]
    kw = {"root": root, "spec": SPEC, "hf_root": None}
    good = {"approved_by": "owner", "protocol_v2_digest": saved["protocol_v2_digest"]}
    assert F.check_paid(out, good, bundle=bundle, stage1=stage1, **kw) == saved[
        "protocol_v2_digest"]  # fmt: skip
    with pytest.raises(LedgerError, match="another freeze"):
        F.check_paid(out, {**good, "protocol_v2_digest": "0" * 64}, bundle=bundle, **kw)
    with pytest.raises(LedgerError, match="frozen dataset"):
        F.check_paid(out, good, bundle=tmp_path / "other_bundle", **kw)
    with pytest.raises(LedgerError, match="frozen dataset"):
        F.check_paid(out, good, bundle=bundle, stage1=tmp_path / "other_stage1", **kw)
    (root / "src/pkg/b.py").write_text("y = 3\n")
    with pytest.raises(LedgerError, match="changed since the freeze"):
        F.check_paid(out, good, bundle=bundle, stage1=stage1, **kw)


def test_frozen_protocol_records_the_option_b_design_from_the_code():
    p = F.protocol()
    assert p == F.protocol()  # deterministic
    json.dumps(p)  # serialisable
    assert p["evidence"]["type"] == "replication"
    assert "not fresh held-out" in p["evidence"]["label"]
    assert p["dataset"]["groups"] == [f"G-T{i:02d}" for i in range(24)]
    assert p["methods"]["main"] == list(A.MAIN_METHODS)
    assert p["conditions"]["registry_fingerprint"] == REG.fingerprint()
    assert len(p["conditions"]["worst_case"]) == 46
    assert p["conditions"]["controls"] == ["uninformative"]
    assert p["runs"]["haiku"]["cells"] == REG.SECOND_BACKBONE
    assert set(p["hypotheses"]) == set(A.PRIMARY) and len(p["hypotheses"]) == 8
    h1 = p["hypotheses"]["H1 vs M"]["components"]
    assert [c["contrast"] for c in h1] == ["S - M", "S - M"]  # own comparator per contrast
    assert p["statistics"]["seed"] == A.SEED and p["statistics"]["resamples"] == A.RESAMPLES
    assert p["seeds"]["PYTHONHASHSEED"] == "0"
    assert p["models"]["answer"] == "openai/gpt-4o-mini"
    assert p["models"]["second_backbone"] == "anthropic/claude-haiku-5.5"
    assert (F.REPO / p["protocol_text"]).exists()


def test_default_spec_covers_code_prompts_data_models_and_the_protocol_text():
    sections = set(F.FILES)
    assert {"source_files", "prompt_files", "scripts", "configs", "environment",
            "protocol_text", "dataset", "dev_dataset", "mpbench", "models"} <= sections
    flat = [g for v in F.FILES.values() for g in v]
    assert "src/ams/**/*.py" in flat and "prompts/**/*.txt" in flat and "uv.lock" in flat
    assert F.PROTOCOL_TEXT in flat


def test_an_unsigned_draft_approval_is_refused(tmp_path):
    root, out, saved = _prepare(tmp_path)
    draft = {"approved_by": "PENDING_OWNER", "protocol_v2_digest": saved["protocol_v2_digest"]}
    with pytest.raises(LedgerError, match="owner"):
        F.check_paid(out, draft, root=root, spec=SPEC, hf_root=None)
