"""Write-once, two-pass human QA/provenance review. Never creates human votes."""

from __future__ import annotations

import copy
import fcntl
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest, name
from ams.research.execution.session import new_json
from ams.research.llm_review.validation import QA_KEYS
from ams.research.phase1_data import normalized
from ams.research.pilot_finish import selection
from ams.research.pilot_finish.utility import collect, verified_proposals
from ams.research.recovery.annotation import assert_blinded
from ams.research.recovery.offline import sha_file

SCHEMA = "focused-human-QA-review-v1"
SCOPE = "new_descriptive_question_and_one_supporting_claim"
FIRST_FLAGS = ("question_clear", "useful_for_task", "safe_descriptive_use")
BASE_KEYS = {"schema", "phase", "role", "candidate_id", "candidate_hash", "packet_hash",
             "reviewer_id", "independent_human_review", "status", "assessment_scope", "rationale"}
EVIDENCE_KEYS = {"answer_from_source", "answer_from_memory", "source_evidence_spans",
                 "memory_evidence_spans", "origin", "origin_rationale"}


def exact(value, keys, label):
    check(type(value) is dict and set(value) == set(keys), f"Unexpected/missing {label} fields")


def read(path):
    def pairs(items):
        result = {}
        for k, v in items:
            check(k not in result, "Duplicate JSON field")
            result[k] = v
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def identity(value):
    name(value, "actual reviewer identity")
    return normalized(value)


def save_new(path, value):
    if path.exists():
        check(read(path) == value, "Sealed submission cannot be overwritten")
        return
    new_json(path, value)


def verify_files(root, files):
    for n, h in files.items():
        p = root/n
        check(p.resolve().is_relative_to(root.resolve()) and p.is_file() and sha_file(p) == h,
              "Review package changed")


def package_data(package):
    m = read(package/"manifest.json")
    check(digest(m["files"]) == m["hash"], "Package manifest changed")
    verify_files(package, m["files"])
    q, packet = read(package/"controller_only/candidate.json"), read(package/"controller_only/packet.json")
    check(q["contribution_id"] == packet["contribution_id"] and q["support_record_kind"] == "claim",
          "Review scope requires the frozen supporting claim")
    record = next(r for r in packet["records"] if r["record_id"] == q["support_record_id"])
    check(record["record_kind"] == "claim" and record["content_hash"] == digest(record["text"]),
          "Stale memory claim")
    artifact = next(a for a in packet["artifacts"] if a["artifact_id"] == q["support_artifact_id"])
    check(artifact["role"] == "external" and artifact["text"][q["start"]:q["end"]] == q["quote"],
          "Stale external-source candidate")
    check(q["answers"] and all(isinstance(a, str) and a.strip() for a in q["answers"]),
          "Missing frozen reference")
    return q, packet, record


def prepare(package, out):
    check(not out.exists(), "Refuse to overwrite a review workflow")
    q, packet, _ = package_data(package)
    deps = {str(p.resolve()): sha_file(p) for p in [
        package/"manifest.json", *[package/n for n in read(package/"manifest.json")["files"]],
        Path(__file__), Path(__file__).with_name("focused_review_page.py"),
        Path(selection.__file__), Path(__file__).parent/"pilot_finish/utility.py"]}
    out.mkdir(parents=True, mode=0o700)
    new_json(out/"settings.json", {"schema": SCHEMA, "assessment_scope": SCOPE,
                                  "package": str(package.resolve()), "candidate_hash": digest(q),
                                  "packet_hash": digest(packet), "dependencies": deps,
                                  "execution_enabled": False})
    new_json(out/"workflow_manifest.json", {"settings_sha256": sha_file(out/"settings.json")})
    (out/"sealed").mkdir(mode=0o700)
    (out/"review.lock").touch(mode=0o600)
    for role in [1, 2]:
        d = out/"forms"/f"reviewer_{role}"
        d.mkdir(parents=True, mode=0o700)
        template = blank(out, "first", role)
        new_json(d/"first_pass_template.json", template)
        render(out, "first", role, d/"first_pass.html")
    new_json(out/"coordinator_template.json", {
        "schema": SCHEMA, "candidate_hash": digest(q), "status": "pending", "coordinator_id": "",
        "reviewer_ids": [], "genuine_human_reviews_confirmed": False,
        "independent_people_confirmed": False, "first_pass_blinding_confirmed": False,
        "sealed_record_hashes": [], "rationale": ""})
    return status(out)


def load(root):
    m, cfg = read(root/"workflow_manifest.json"), read(root/"settings.json")
    check(sha_file(root/"settings.json") == m["settings_sha256"]
          and cfg["schema"] == SCHEMA and cfg["assessment_scope"] == SCOPE
          and cfg["execution_enabled"] is False, "Workflow settings changed")
    for n, h in cfg["dependencies"].items():
        check(sha_file(Path(n)) == h, "Frozen review dependency changed")
    q, packet, record = package_data(Path(cfg["package"]))
    check(digest(q) == cfg["candidate_hash"] and digest(packet) == cfg["packet_hash"], "Stale workflow")
    return cfg, q, packet, record


@contextmanager
def locked(root):
    with (root/"review.lock").open("r+") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            check(False, "Another reviewer-process writer owns this workflow")
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def blank(root, phase, role):
    cfg, q, _, _ = load(root)
    body = {"schema": SCHEMA, "phase": phase, "role": role, "candidate_id": q["candidate_id"],
            "candidate_hash": cfg["candidate_hash"], "packet_hash": cfg["packet_hash"],
            "reviewer_id": "", "independent_human_review": False, "status": "pending",
            "assessment_scope": SCOPE, "rationale": ""}
    if phase in {"first", "adjudication"}:
        body.update(answer_from_source="", answer_from_memory="", source_evidence_spans=[],
                    memory_evidence_spans=[], origin="", origin_rationale="")
    flags = FIRST_FLAGS if phase == "first" else QA_KEYS
    body.update({k: None for k in flags})
    if phase == "second":
        first = sealed(root, "first", role)
        release = read_release(root)
        body.update(first_pass_hash=first["record_hash"], release_hash=release["record_hash"])
    elif phase == "adjudication":
        body["disagreement_refs"] = [sealed(root, "second", n)["record_hash"] for n in [1, 2]]
    return body


def span_checks(body, packet, record):
    for field, kind, id_key, texts in [
        ("source_evidence_spans", "source", "artifact_id", {a["artifact_id"]: a["text"] for a in packet["artifacts"]}),
        ("memory_evidence_spans", "memory", "record_id", {record["record_id"]: record["text"]}),
    ]:
        spans = body[field]
        check(type(spans) is list, "Evidence must be a list")
        for span in spans:
            exact(span, {id_key, "start", "end", "quote"}, kind+" span")
            check(span[id_key] in texts, "Evidence refers to another artifact/record")
            text = texts[span[id_key]]
            lo, hi = span["start"], span["end"]
            check(type(lo) is int and type(hi) is int and 0 <= lo < hi <= len(text)
                  and text[lo:hi] == span["quote"], "Evidence is not an exact original Unicode span")
    check(body["origin"] in {"principal", "external", "ambiguous"}, "Missing scoped provenance decision")
    name(body["origin_rationale"], "provenance rationale")
    if body["origin"] != "ambiguous":
        sources = {a["artifact_id"]: a for a in packet["artifacts"]}
        check(body["source_evidence_spans"] and all(
            sources[s["artifact_id"]]["role"] == body["origin"] for s in body["source_evidence_spans"]),
              "Confirmed source role requires matching original evidence")
    for field, evidence in [("answer_from_source", "source_evidence_spans"),
                            ("answer_from_memory", "memory_evidence_spans")]:
        check(type(body[field]) is str, "Answer must be text or an empty unresolved answer")
        check(not body[field].strip() or body[evidence], "A proposed first-pass answer needs evidence")


def validate_submission(root, body, phase, role):
    cfg, q, packet, record = load(root)
    check(type(role) is int and ((phase in {"first", "second"} and role in {1, 2})
                               or (phase == "adjudication" and role == 3)), "Unsupported reviewer phase")
    keys = BASE_KEYS | (EVIDENCE_KEYS if phase in {"first", "adjudication"} else set())
    keys |= set(FIRST_FLAGS if phase == "first" else QA_KEYS)
    keys |= {"first_pass_hash", "release_hash"} if phase == "second" else (
        {"disagreement_refs"} if phase == "adjudication" else set())
    exact(body, keys, "submission")
    check(body["schema"] == SCHEMA and body["phase"] == phase and body["role"] == role
          and body["assessment_scope"] == SCOPE and body["candidate_id"] == q["candidate_id"]
          and body["candidate_hash"] == cfg["candidate_hash"] and body["packet_hash"] == cfg["packet_hash"],
          "Wrong/stale review scope")
    check(body["status"] == "complete" and body["independent_human_review"] is True,
          "A genuine completed human-review declaration is required")
    who = identity(body["reviewer_id"]); name(body["rationale"], "review rationale")
    for k in FIRST_FLAGS if phase == "first" else QA_KEYS:
        check(type(body[k]) is bool or body[k] is None, "Use true, false or null uncertainty")
    if phase in {"first", "adjudication"}:
        span_checks(body, packet, record)
    if phase == "second":
        first = sealed(root, "first", role)
        check(first is not None, "First pass must be sealed first")
        release = read_release(root)
        check(body["first_pass_hash"] == first["record_hash"]
              and body["release_hash"] == release["record_hash"]
              and who == identity(first["payload"]["reviewer_id"]), "Changed reviewer or first-pass commitment")
    return who


def sealed(root, phase, role):
    p = root/"sealed"/f"{phase}_{role}.json"
    if not p.exists():
        return None
    item = read(p)
    exact(item, {"payload", "record_hash"}, "sealed record")
    check(digest(item["payload"]) == item["record_hash"], "Sealed review was modified")
    return item


def read_release(root):
    p = root/"sealed/reference_release.json"
    check(p.exists(), "Reference is not released")
    release = read(p)
    check(digest(release["payload"]) == release["record_hash"], "Reference release modified")
    cfg, _, _, _ = load(root)
    exact(release["payload"], {"candidate_hash", "first_pass_hashes"}, "reference release")
    check(release["payload"]["candidate_hash"] == cfg["candidate_hash"], "Wrong released reference")
    first = [sealed(root, "first", n) for n in [1, 2]]
    check(all(first) and release["payload"]["first_pass_hashes"] == [x["record_hash"] for x in first],
          "First-pass commitment changed after reference release")
    return release


def status(root):
    load(root)
    first = [sealed(root, "first", n) for n in [1, 2]]
    second = [sealed(root, "second", n) for n in [1, 2]]
    for n, item in enumerate(first, 1):
        if item:
            validate_submission(root, item["payload"], "first", n)
    if all(first):
        check(identity(first[0]["payload"]["reviewer_id"]) != identity(first[1]["payload"]["reviewer_id"]),
              "Two roles do not establish two independent people")
    if (root/"sealed/reference_release.json").exists():
        read_release(root)
    for n, item in enumerate(second, 1):
        if item:
            validate_submission(root, item["payload"], "second", n)
    state = "awaiting_first_passes" if not all(first) else (
        "awaiting_reference_release" if not (root/"sealed/reference_release.json").exists() else
        "awaiting_second_passes" if not all(second) else "awaiting_coordinator_acceptance")
    disagreements = []
    if all(second):
        for k in [*FIRST_FLAGS, "origin"]:
            if first[0]["payload"][k] != first[1]["payload"][k]:
                disagreements.append("first:"+k)
        for k in QA_KEYS:
            if second[0]["payload"][k] != second[1]["payload"][k]:
                disagreements.append("second:"+k)
        if disagreements:
            state = "adjudication_required"
    adjudication = sealed(root, "adjudication", 3)
    if adjudication:
        check(disagreements, "Adjudication without independent disagreement")
        validate_submission(root, adjudication["payload"], "adjudication", 3)
        check(adjudication["payload"]["disagreement_refs"] == [x["record_hash"] for x in second],
              "Adjudicator reviewed different votes")
        who = identity(adjudication["payload"]["reviewer_id"])
        check(all(who != identity(x["payload"]["reviewer_id"]) for x in first), "Adjudicator must be distinct")
        state = "awaiting_coordinator_acceptance"
    return {"status": state, "sealed_first_passes": sum(x is not None for x in first),
            "sealed_second_passes": sum(x is not None for x in second),
            "reference_released": (root/"sealed/reference_release.json").exists(),
            "disagreements": disagreements, "adjudication_present": adjudication is not None,
            "acceptance": "tracked in a separate versioned import report", "human_verified_memory_labels": 0,
            "execution_enabled": False, "new_API_calls": 0}


def seal(root, phase, role, submission_file):
    with locked(root):
        before = status(root)
        body = read(submission_file)
        who = validate_submission(root, body, phase, role)
        if phase == "first":
            other = sealed(root, "first", 3-role)
            check(not other or who != identity(other["payload"]["reviewer_id"]), "Reviewer identities are not distinct")
        if phase == "adjudication":
            check(before["disagreements"], "No genuine independent disagreement to adjudicate")
            check(body["disagreement_refs"] == [sealed(root, "second", n)["record_hash"] for n in [1, 2]],
                  "Wrong disagreement records")
            check(all(who != identity(sealed(root, "first", n)["payload"]["reviewer_id"]) for n in [1, 2]),
                  "Adjudicator must be a distinct person")
        save_new(root/"sealed"/f"{phase}_{role}.json", {"payload": body, "record_hash": digest(body)})
        return status(root)


def release(root):
    with locked(root):
        status(root)
        first = [sealed(root, "first", n) for n in [1, 2]]
        check(all(first), "Both independent first passes must be sealed before references")
        cfg, q, _, _ = load(root)
        payload = {"candidate_hash": cfg["candidate_hash"], "first_pass_hashes": [x["record_hash"] for x in first]}
        save_new(root/"sealed/reference_release.json", {"payload": payload, "record_hash": digest(payload)})
        for role in [1, 2]:
            d = root/"forms"/f"reviewer_{role}"
            save_new(d/"second_pass_template.json", blank(root, "second", role))
            render(root, "second", role, d/"second_pass.html")
        return status(root)


def adjudication_form(root):
    with locked(root):
        check(status(root)["disagreements"], "No genuine disagreement")
        d = root/"forms/reviewer_3"; d.mkdir(parents=True, mode=0o700, exist_ok=True)
        save_new(d/"adjudication_template.json", blank(root, "adjudication", 3))
        render(root, "adjudication", 3, d/"adjudication.html")
        return {"status": "blank_adjudication_form_prepared", "human_reviews_created": 0}


def positive_evidence(body, q, packet):
    aliases = {" ".join(a.split()) for a in q["answers"]}
    sources = {a["artifact_id"]: a for a in packet["artifacts"]}
    def contains(quote):
        return any(a in " ".join(quote.split()) for a in aliases)
    return (body["origin"] == "external"
            and " ".join(body["answer_from_source"].split()) in aliases
            and " ".join(body["answer_from_memory"].split()) in aliases
            and any(s["artifact_id"] == q["support_artifact_id"]
                    and sources[s["artifact_id"]]["role"] == "external" and contains(s["quote"])
                    for s in body["source_evidence_spans"])
            and any(s["record_id"] == q["support_record_id"] and contains(s["quote"])
                    for s in body["memory_evidence_spans"]))


def coordinator_form(root, target):
    check(not target.exists(), "Preserve existing coordinator declarations")
    with locked(root):
        check(status(root)["status"] == "awaiting_coordinator_acceptance", "Review process is incomplete")
        cfg, _, _, _ = load(root)
        first = [sealed(root, "first", n) for n in [1, 2]]
        items = [*first, *[sealed(root, "second", n) for n in [1, 2]]]
        adjudicator = sealed(root, "adjudication", 3)
        if adjudicator:
            items.append(adjudicator)
        people = [x["payload"]["reviewer_id"] for x in first]
        if adjudicator:
            people.append(adjudicator["payload"]["reviewer_id"])
        new_json(target, {"schema": SCHEMA, "candidate_hash": cfg["candidate_hash"], "status": "pending",
            "coordinator_id": "", "reviewer_ids": people, "genuine_human_reviews_confirmed": False,
            "independent_people_confirmed": False, "first_pass_blinding_confirmed": False,
            "sealed_record_hashes": [x["record_hash"] for x in items], "rationale": ""})
        return {"status": "pending_coordinator_attestation", "accepted_decisions_created": 0}


def accept(root, coordinator_file, out):
    check(not out.exists(), "Do not overwrite imported decisions")
    with locked(root):
        current = status(root)
        check(current["status"] == "awaiting_coordinator_acceptance", "Review process is incomplete")
        cfg, q, packet, _ = load(root)
        first = [sealed(root, "first", n) for n in [1, 2]]
        second = [sealed(root, "second", n) for n in [1, 2]]
        adjudicator = sealed(root, "adjudication", 3)
        records = [*first, *second, *([adjudicator] if adjudicator else [])]
        coordinator = read(coordinator_file)
        exact(coordinator, {"schema", "candidate_hash", "status", "coordinator_id", "reviewer_ids",
              "genuine_human_reviews_confirmed", "independent_people_confirmed", "first_pass_blinding_confirmed",
              "sealed_record_hashes", "rationale"}, "coordinator attestation")
        name(coordinator["coordinator_id"], "research coordinator"); name(coordinator["rationale"], "coordinator rationale")
        people = [identity(x["payload"]["reviewer_id"]) for x in [*first, *([adjudicator] if adjudicator else [])]]
        check(coordinator["schema"] == SCHEMA and coordinator["candidate_hash"] == cfg["candidate_hash"]
              and coordinator["status"] == "complete" and all(coordinator[k] is True for k in [
                  "genuine_human_reviews_confirmed", "independent_people_confirmed", "first_pass_blinding_confirmed"])
              and type(coordinator["reviewer_ids"]) is list
              and type(coordinator["sealed_record_hashes"]) is list
              and sorted(identity(p) for p in coordinator["reviewer_ids"]) == sorted(people)
              and sorted(coordinator["sealed_record_hashes"]) == sorted(x["record_hash"] for x in records),
              "Missing genuine process declaration or different review records")
        reasons = []
        if adjudicator:
            approved = (all(adjudicator["payload"][k] is True for k in QA_KEYS)
                        and positive_evidence(adjudicator["payload"], q, packet))
            if not approved:
                reasons.append("adjudicator_did_not_confirm_all_criteria_and_support")
        else:
            approved = (all(all(x["payload"][k] is True for k in FIRST_FLAGS)
                            and positive_evidence(x["payload"], q, packet) for x in first)
                        and all(all(x["payload"][k] is True for k in QA_KEYS) for x in second))
            if not approved:
                reasons.append("independent_reviews_did_not_confirm_all_criteria_and_support")
        result = {"schema": SCHEMA, "assessment_scope": SCOPE,
                  "status": "human_QA_accepted_by_coordinator_attestation" if approved else "human_QA_not_accepted",
                  "candidate_id": q["candidate_id"], "candidate_hash": digest(q), "packet_hash": digest(packet),
                  "accepted_human_QA_candidates": int(approved), "candidate": q,
                  "independent_reviewer_ids": [x["payload"]["reviewer_id"] for x in first],
                  "adjudicator_id": adjudicator["payload"]["reviewer_id"] if adjudicator else None,
                  "review_record_hashes": [x["record_hash"] for x in records], "reasons": reasons,
                  "identity_authentication": "coordinator declaration; software cannot prove physical identity or independence",
                  "human_verified_source_bundles": 0, "human_verified_memory_labels": 0,
                  "eligible_as_gold": False, "can_update_live_trust": False, "execution_enabled": False}
        out.mkdir(parents=True, mode=0o700)
        new_json(out/"review_import.json", result)
        deps = {str(p.resolve()): sha_file(p) for p in [root/"settings.json", root/"workflow_manifest.json",
                *sorted((root/"sealed").glob("*.json")), coordinator_file, Path(__file__)]}
        new_json(out/"import_manifest.json", {"files": {"review_import.json": sha_file(out/"review_import.json")},
                                             "dependencies": {**cfg["dependencies"], **deps}})
        return result


def import_result(path):
    m = read(path/"import_manifest.json")
    verify_files(path, m["files"])
    for n, h in m["dependencies"].items():
        check(sha_file(Path(n)) == h, "Imported human review changed")
    r = read(path/"review_import.json")
    check(r["schema"] == SCHEMA and r["assessment_scope"] == SCOPE
          and r["human_verified_memory_labels"] == r["human_verified_source_bundles"] == 0
          and r["eligible_as_gold"] is r["can_update_live_trust"] is r["execution_enabled"] is False,
          "QA-only review was promoted beyond its scope")
    return r


def readiness(root, prepared, reviews, out, accepted=None):
    check(not out.exists(), "Do not overwrite readiness output")
    cfg, q, packet, _ = load(root)
    status(root)
    packets, records, _, _, bundles = collect(reviews, prepared)
    pid = q["contribution_id"]
    check(pid in packets and digest(packets[pid]) == digest(packet), "AI source view is stale or unrelated")
    human = import_result(accepted) if accepted is not None else None
    if human:
        check(human["candidate_hash"] == digest(q) and human["packet_hash"] == digest(packet), "Wrong accepted QA")
    approved = bool(human and human["accepted_human_QA_candidates"] == 1)
    rows = [r for directory in reviews for r in verified_proposals(directory)]
    if approved:
        check(not any(x["candidate_id"] == q["candidate_id"] for r in rows for x in r["questions"]),
              "QA candidate already assessed; use explicit version reconciliation")
        rows.append({"contribution_id": pid, "use_id": packet["use_id"], "annotation_source": "human_QA_only",
                     "records": [], "questions": [{"candidate_id": q["candidate_id"], **{k: True for k in QA_KEYS},
                         "rationale": "Genuine two-pass declarations and coordinator attestation; QA scope only."}],
                     "candidate_question": {**q, "human_validated": True, "eligible_as_gold": False,
                                            "validation_status": "human_QA_source_safety_still_AI"},
                     "eligible_as_gold": False, "can_update_live_trust": False})
    out.mkdir(parents=True, mode=0o700)
    view = out/"selection_view"; view.mkdir(mode=0o700)
    with (view/"automated_proposals.jsonl").open("x") as stream:
        stream.writelines(canonical(r)+"\n" for r in rows)
    new_json(view/"summary.json", {"scope": "source_safety_AI_with_scoped_QA_provenance", "human_QA_candidates": int(approved)})
    files = {n: sha_file(view/n) for n in ["automated_proposals.jsonl", "summary.json"]}
    new_json(view/"results_manifest.json", {"files": files, "hash": digest(files)})
    # Reuse the original selector, but publish accurate mixed-review metadata in
    # a new contract. The legacy AI-only freeze must not consume this report.
    with tempfile.TemporaryDirectory(prefix="focused-review-selection-") as tmp:
        result = selection.readiness(prepared, [view], Path(tmp)/"selector")
    result.update(status="scoped_QA_readiness_only", human_validated_questions=int(approved),
                  accepted_human_QA_candidates=int(approved), human_verified_labels=0,
                  human_validated_pilot_ready=False, source_label_basis="AI_only_not_human_Z",
                  QA_basis="mixed_AI_and_scoped_human" if approved else "AI_only_no_human_QA_submitted",
                  automatic_freeze_enabled=False, defense_execution_enabled=False,
                  next_freeze_contract="requires_mixed_QA_aware_version; do_not_use_legacy_AI_only_freeze")
    new_json(out/"review_readiness.json", result)
    deps = {str(p.resolve()): sha_file(p) for p in [root/"settings.json", *[r/"results_manifest.json" for r in reviews],
            *([accepted/"import_manifest.json", accepted/"review_import.json"] if accepted else []), Path(__file__)]}
    new_json(out/"review_readiness_manifest.json", {"dependencies": {**cfg["dependencies"], **deps},
              "files": {"review_readiness.json": sha_file(out/"review_readiness.json")}, "execution_enabled": False})
    return result


def render(root, phase, role, target):
    from .focused_review_page import page
    cfg, q, packet, record = load(root)
    data = {"question": q["question"], "record": {k: record[k] for k in ["record_id", "text", "content_hash"]},
            "artifacts": [{k: a[k] for k in ["artifact_id", "role", "text"]} for a in packet["artifacts"]],
            "template": blank(root, phase, role)}
    if phase == "second":
        data.update(reference_answers=q["answers"], own_first_pass=sealed(root, "first", role)["payload"])
    elif phase == "adjudication":
        check(status(root)["disagreements"], "No disagreement to expose to adjudicator")
        data.update(reference_answers=q["answers"], independent_reviews=[
            {"first": sealed(root, "first", n)["payload"], "second": sealed(root, "second", n)["payload"]}
            for n in [1, 2]])
    assert_blinded(data)
    html = page(data)
    if target.exists():
        check(target.read_text() == html, "Existing review page changed")
    else:
        target.write_text(html)
