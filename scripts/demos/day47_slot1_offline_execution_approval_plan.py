"""Day 47 step 1: plan approval for one isolated Day 22 offline review."""

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Allow approval work only; never execute the approved task in Day 47."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 47 execution switch must be Boolean.")
    allowed_true = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 47 approval evaluation and reporting must be allowed.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 47 prohibited action enabled: " + ", ".join(prohibited))


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    """Load one frozen JSON source and verify task/status metadata."""

    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 47 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"The Day 47 source metadata is incorrect: {path_key}")
    return path, report


def validate_day46_review(config, review):
    """Require verified candidate eligibility without a prior execution release."""

    source = config["source"]
    checks = (
        review.get("decision_status") == source["expected_day46_status"],
        review.get("candidate", {}).get("sha256") == source["candidate_sha256"],
        review.get("candidate", {}).get("identity_verified") is True,
        review.get("verified_change", {}).get("semantic_difference_count") == 1,
        review.get("review_decision", {}).get("candidate_eligible_for_execution_approval_request") is True,
        review.get("review_decision", {}).get("slot_01_execution_approved") is False,
        review.get("permissions", {}).get("slot_01_execution_released") is False,
        review.get("review_task_executed") is False,
        review.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 46 candidate review is not eligible for Day 47 approval.")


def validate_schedule_and_gate(config, schedule, runbook):
    """Verify Slot 1 identity and CP09 as the post-execution manual gate."""

    slot1 = next((row for row in schedule["slots"] if int(row["slot"]) == 1), None)
    if not slot1:
        raise ValueError("The Day 42 schedule has no Slot 1.")
    slot_checks = (
        slot1["days"] == [22],
        slot1["offline_only_days"] == [22],
        slot1["uses_zosapi_days"] == [],
        slot1["manual_approval_required"] is True,
        slot1["execution_released"] is False,
        slot1["automatic_execution"] is False,
    )
    if not all(slot_checks):
        raise ValueError("The Day 42 Slot 1 definition changed.")
    cp09 = next(
        (row for row in runbook["checkpoints"] if row["checkpoint_id"] == "CP09_slot_gate"),
        None,
    )
    if not cp09 or cp09["manual_decision_required"] is not True:
        raise ValueError("The Day 35 CP09 manual gate is missing.")
    if cp09["automatic_execution"] is not False:
        raise ValueError("The Day 35 CP09 gate unexpectedly allows automatic execution.")
    return slot1, cp09


def validate_files_and_contract(config):
    """Bind the execution contract to unchanged official and candidate files."""

    source = config["source"]
    contract = config["approved_execution_contract"]
    official_path = (PROJECT_ROOT / source["official_day22_config"]).resolve()
    candidate_path = (PROJECT_ROOT / source["candidate_config"]).resolve()
    if not official_path.is_file() or sha256_file(official_path) != source["official_day22_sha256"]:
        raise ValueError("The official Day 22 config changed before Day 47 approval.")
    if not candidate_path.is_file() or sha256_file(candidate_path) != source["candidate_sha256"]:
        raise ValueError("The approved Day 22 candidate changed before Day 47 approval.")
    checks = (
        int(contract["resource_slot"]) == 1,
        int(contract["day"]) == 22,
        contract["execution_class"] == "offline_only",
        int(contract["maximum_execution_count"]) == 1,
        (PROJECT_ROOT / contract["input_config"]).resolve() == candidate_path,
        contract["input_sha256"] == source["candidate_sha256"],
        contract["required_dedicated_entrypoint"] == "scripts/demos/day48_execute_approved_day22_candidate.py",
        str(contract["approved_output_root"]).startswith("outputs/"),
        contract["require_isolated_output_directory"] is True,
        contract["require_official_config_unchanged_before_and_after"] is True,
        contract["require_candidate_unchanged_before_and_after"] is True,
        contract["require_no_zosapi_connection"] is True,
        contract["require_no_new_optical_calculation"] is True,
        contract["require_stop_after_slot1"] is True,
        contract["require_cp09_review_after_execution"] is True,
    )
    if not all(checks):
        raise ValueError("The Day 47 execution contract is incomplete or unsafe.")
    return official_path, candidate_path


def validate_decision(config):
    """Release exactly one offline execution and retain all other locks."""

    decision = config["decision"]
    if decision["decision_status"] != "SLOT_01_APPROVED_FOR_CANDIDATE_OFFLINE_REVIEW_EXECUTION":
        raise ValueError("The Day 47 decision status is incorrect.")
    expected_approved = {
        "execute_day22_offline_review_once_with_frozen_candidate",
        "read_frozen_day21_evidence",
        "write_isolated_slot1_result",
    }
    if set(decision["approved_capabilities"]) != expected_approved:
        raise ValueError("The Day 47 approved capabilities changed.")
    permissions = config["permissions"]
    true_permissions = {
        "slot_01_offline_execution_released",
        "frozen_candidate_use_released",
        "isolated_slot1_output_released",
    }
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("The Day 47 execution permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 47 released a forbidden capability.")


def build_plan(config, review_path, schedule_path, runbook_path, official_path, candidate_path, slot1):
    """Build the execution-approval plan without running the approved task."""

    contract = dict(config["approved_execution_contract"])
    contract["input_config"] = str(candidate_path)
    contract["approved_output_root"] = str(
        (PROJECT_ROOT / contract["approved_output_root"]).resolve()
    )
    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_day46_review": str(review_path),
        "source_day42_schedule": str(schedule_path),
        "source_day35_runbook": str(runbook_path),
        "official_path": str(official_path),
        "official_sha256": config["source"]["official_day22_sha256"],
        "candidate_path": str(candidate_path),
        "candidate_sha256": config["source"]["candidate_sha256"],
        "slot_definition": slot1,
        "execution_contract": contract,
        "approved_capabilities": list(config["decision"]["approved_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
    }


def print_introduction(config):
    """Print today's four-part teaching introduction."""

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
    config = load_config("configs/day47_slot1_offline_execution_approval.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    review_path, review = load_frozen_json(
        config, "day46_review_record", "day46_review_sha256", "expected_day46_task"
    )
    schedule_path, schedule = load_frozen_json(
        config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task"
    )
    runbook_path, runbook = load_frozen_json(
        config, "day35_runbook", "day35_runbook_sha256", "expected_day35_task"
    )
    validate_day46_review(config, review)
    slot1, _ = validate_schedule_and_gate(config, schedule, runbook)
    official_path, candidate_path = validate_files_and_contract(config)
    plan = build_plan(
        config, review_path, schedule_path, runbook_path, official_path, candidate_path, slot1
    )

    print_introduction(config)
    print("========== DAY 47 SLOT-1 OFFLINE EXECUTION APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, Day22 execution, source change or ZOS-API connection will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Approved scope: Slot 1 / Day 22 / offline_only / one execution")
    print(f"Frozen candidate SHA256: {plan['candidate_sha256']}")
    print(f"Required entrypoint: {plan['execution_contract']['required_dedicated_entrypoint']}")
    print(f"Approved output root: {plan['execution_contract']['approved_output_root']}")
    print("Approved capabilities:")
    for capability in plan["approved_capabilities"]:
        print(f"  - {capability}")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day 46 review, Day 42 schedule and Day 35 runbook verified")
    print("[PASS] Official and candidate fingerprints remain unchanged")
    print("[PASS] Approval is limited to one isolated Slot 1 offline execution")
    print("[PASS] Dedicated candidate entrypoint and output boundary frozen")
    print("[PASS] CP09 manual review required immediately after execution")
    print("[PASS] Day47 itself executes nothing; ZOS-API and Slot 2-6 remain locked")
    print("PLAN ONLY finished. No output, calculation or source modification was created.")


if __name__ == "__main__":
    main()
