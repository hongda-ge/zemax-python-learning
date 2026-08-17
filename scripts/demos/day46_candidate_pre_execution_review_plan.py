"""Day 46 step 1: review the isolated Day 22 candidate before execution approval."""

import hashlib
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day45_isolated_day22_candidate_plan import semantic_differences  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Permit review/reporting only; keep every calculation and write locked."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 46 execution switch must be Boolean.")
    allowed_true = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 46 review evaluation and reporting must be allowed.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 46 prohibited action enabled: " + ", ".join(prohibited))


def load_frozen_json(config, path_key, hash_key, expected_task):
    """Load one exact JSON artifact and verify its task and success status."""

    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 46 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != expected_task or report.get("status") != "success":
        raise ValueError(f"The Day 46 source metadata is incorrect: {path_key}")
    return path, report


def validate_day44_approval(config, approval):
    """Require the exact preparation-only approval and retained execution locks."""

    source = config["source"]
    checks = (
        approval.get("decision_status") == source["expected_day44_decision"],
        approval.get("candidate_boundary", {}).get("future_execution_requires_separate_approval") is True,
        approval.get("permissions", {}).get("candidate_preparation_released") is True,
        approval.get("permissions", {}).get("slot_01_execution_released") is False,
        approval.get("permissions", {}).get("downstream_slots_released") is False,
        approval.get("review_task_executed") is False,
        approval.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 44 approval is not a safe Day 46 input.")
    return (PROJECT_ROOT / approval["candidate_boundary"]["root"]).resolve()


def validate_files_and_manifest(config, manifest, approved_root):
    """Recompute both hashes and the semantic difference from the files on disk."""

    source = config["source"]
    boundary = config["review_boundary"]
    official_path = (PROJECT_ROOT / source["official_day22_config"]).resolve()
    candidate_path = (PROJECT_ROOT / source["candidate_config"]).resolve()
    if not official_path.is_file() or sha256_file(official_path) != source["official_day22_sha256"]:
        raise ValueError("The official Day 22 config changed before Day 46 review.")
    if not candidate_path.is_file() or sha256_file(candidate_path) != source["candidate_sha256"]:
        raise ValueError("The Day 45 candidate fingerprint changed.")
    if approved_root not in candidate_path.parents:
        raise ValueError("The Day 45 candidate is outside the approved outputs root.")

    manifest_checks = (
        Path(manifest["official_source"]["path"]).resolve() == official_path,
        manifest["official_source"]["sha256"] == source["official_day22_sha256"],
        manifest["official_source"]["modified"] is False,
        Path(manifest["candidate"]["path"]).resolve() == candidate_path,
        manifest["candidate"]["sha256"] == source["candidate_sha256"],
        manifest["candidate"]["official_baseline"] is False,
        manifest["declared_change"]["field"] == boundary["canonical_field"],
        float(manifest["declared_change"]["source_value"]) == float(boundary["source_value"]),
        float(manifest["declared_change"]["candidate_value"]) == float(boundary["candidate_value"]),
        int(manifest["declared_change"]["semantic_difference_count"]) == 1,
        manifest.get("review_task_executed") is False,
        manifest.get("existing_source_modified") is False,
        manifest.get("engineering_change_approved") is False,
    )
    if not all(manifest_checks):
        raise ValueError("The Day 45 manifest does not match the Day 46 review boundary.")
    locked = (
        "source_modification_released",
        "slot_01_execution_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "downstream_slots_released",
    )
    if any(manifest["authorization"].get(key) is not False for key in locked):
        raise ValueError("The Day 45 manifest unexpectedly released execution.")

    official_doc = yaml.safe_load(official_path.read_text(encoding="utf-8"))
    candidate_doc = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    differences = semantic_differences(official_doc, candidate_doc)
    if len(differences) != 1 or differences[0]["path"] != boundary["canonical_field"]:
        raise ValueError("The candidate no longer has exactly one declared semantic difference.")
    if float(differences[0]["source"]) != float(boundary["source_value"]):
        raise ValueError("The candidate source value is incorrect.")
    if float(differences[0]["candidate"]) != float(boundary["candidate_value"]):
        raise ValueError("The candidate proposed value is incorrect.")
    return official_path, candidate_path, differences


def validate_decision(config):
    """Ensure Day 46 grants review eligibility but no execution capability."""

    decision = config["decision"]
    if decision["decision_status"] != "CANDIDATE_VERIFIED_WAITING_FOR_SLOT_01_EXECUTION_APPROVAL":
        raise ValueError("The Day 46 review status is incorrect.")
    expected_released = {
        "generate_candidate_pre_execution_review_record",
        "submit_slot_01_execution_approval_request",
    }
    if set(decision["released_capabilities"]) != expected_released:
        raise ValueError("The Day 46 released capabilities changed.")
    permissions = config["permissions"]
    true_permissions = {
        "candidate_identity_verified",
        "candidate_difference_verified",
        "candidate_eligible_for_execution_approval_request",
    }
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("The Day 46 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 46 unexpectedly released execution or modification.")


def build_plan(config, approval_path, manifest_path, official_path, candidate_path, differences):
    """Build the review plan without generating an approval or executing Day 22."""

    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_day44_approval": str(approval_path),
        "source_day45_manifest": str(manifest_path),
        "official_path": str(official_path),
        "official_sha256": config["source"]["official_day22_sha256"],
        "candidate_path": str(candidate_path),
        "candidate_sha256": config["source"]["candidate_sha256"],
        "semantic_differences": differences,
        "scope": {
            "resource_slot": int(config["review_boundary"]["resource_slot"]),
            "day": int(config["review_boundary"]["day"]),
            "execution_class": config["review_boundary"]["execution_class"],
        },
        "released_capabilities": list(config["decision"]["released_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
    }


def print_introduction(config):
    """Print the four-part teaching introduction."""

    intro = config["teaching_introduction"]
    print("========== TODAY'S INTRODUCTION ==========")
    print(f"Why today: {intro['why_today']}")
    print(f"Link to yesterday: {intro['relation_to_previous_day']}")
    print("Core concepts:")
    for concept in intro["concepts"]:
        print(f"  - {concept}")
    print(f"Completion standard: {intro['completion_standard']}")
    print()


def main():
    config = load_config("configs/day46_candidate_pre_execution_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    source = config["source"]
    approval_path, approval = load_frozen_json(
        config, "day44_approval_record", "day44_approval_sha256", source["expected_day44_task"]
    )
    manifest_path, manifest = load_frozen_json(
        config, "day45_manifest", "day45_manifest_sha256", source["expected_day45_task"]
    )
    approved_root = validate_day44_approval(config, approval)
    official_path, candidate_path, differences = validate_files_and_manifest(
        config, manifest, approved_root
    )
    plan = build_plan(
        config, approval_path, manifest_path, official_path, candidate_path, differences
    )

    print_introduction(config)
    print("========== DAY 46 CANDIDATE PRE-EXECUTION REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, source change, Day22 execution or ZOS-API connection will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Scope: Slot 1 / Day 22 / offline_only")
    print(f"Official SHA256: {plan['official_sha256']}")
    print(f"Candidate SHA256: {plan['candidate_sha256']}")
    difference = plan["semantic_differences"][0]
    print(
        f"Verified difference: {difference['path']} "
        f"{float(difference['source']):.3f} -> {float(difference['candidate']):.3f} mm"
    )
    print("Released after review record:")
    for capability in plan["released_capabilities"]:
        print(f"  - {capability}")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day 44 approval and Day 45 manifest verified")
    print("[PASS] Official and candidate SHA256 fingerprints independently reproduced")
    print("[PASS] Exactly one declared semantic difference independently reproduced")
    print("[PASS] Candidate remains inside the approved outputs root")
    print("[PASS] Slot 1 execution, ZOS-API and Slot 2-6 remain locked")
    print("PLAN ONLY finished. No output, calculation or source modification was created.")


if __name__ == "__main__":
    main()
