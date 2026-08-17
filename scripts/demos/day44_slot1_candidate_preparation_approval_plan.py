"""Day 44 step 1: plan a least-privilege approval for Slot 1 candidate preparation."""

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
    """Allow approval evaluation/reporting while keeping preparation and execution locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 44 execution switch must be Boolean.")
    allowed_true = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 44 approval evaluation and reporting must be allowed.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 44 prohibited action enabled: " + ", ".join(prohibited))


def load_json_source(config, path_key, hash_key, task_key):
    """Load one exact frozen JSON source and validate its task/status metadata."""

    source = config["source"]
    path = PROJECT_ROOT / source[path_key]
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 44 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[task_key] or report.get("status") != "success":
        raise ValueError(f"The Day 44 source metadata is incorrect: {path_key}")
    return path, report


def validate_runbook(config, runbook):
    """Require CP09 as the manual gate after every real resource slot."""

    checkpoints = {item["checkpoint_id"]: item for item in runbook["checkpoints"]}
    cp09 = checkpoints.get("CP09_slot_gate")
    if not cp09:
        raise ValueError("The Day 35 runbook does not contain CP09.")
    checks = (
        cp09.get("stage") == "execution_gate",
        cp09.get("manual_decision_required") is True,
        cp09.get("automatic_execution") is False,
        "不得释放后续依赖节点" in cp09.get("fail_action", ""),
    )
    if not all(checks):
        raise ValueError("The Day 35 CP09 manual gate changed.")
    return cp09


def validate_request_and_target(config, request):
    """Bind the approval to the unchanged target and exact proposed value."""

    source = config["source"]
    target_path = PROJECT_ROOT / source["target_config"]
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target changed before Day 44 approval planning.")
    change = request["change"]
    boundary = config["candidate_boundary"]
    checks = (
        request.get("request_id") == "CR-DAY37-001",
        request.get("request_status") == "WAITING_FOR_APPROVAL",
        request.get("request_is_hypothetical") is True,
        Path(change["target_artifact"]).resolve() == target_path.resolve(),
        change["target_artifact_sha256"] == source["target_config_sha256"],
        change["target_field"] == boundary["target_field"],
        float(change["current_value"]) == float(boundary["current_value"]),
        float(change["proposed_value"]) == float(boundary["proposed_value"]),
        change["change_written_to_target"] is False,
        request.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 37 request does not match the Day 44 approval boundary.")
    return target_path


def validate_gate_and_slot(config, gate_report):
    """Verify Day 43 safety and identify only Slot 1 / Day 22 for preparation."""

    checks = (
        gate_report.get("simulation_only") is True,
        gate_report.get("drill_count") == 4,
        gate_report.get("state_row_count") == 28,
        gate_report.get("real_failure_occurred") is False,
        gate_report.get("review_tasks_approved_for_execution") is False,
        gate_report.get("review_tasks_executed") is False,
        gate_report.get("existing_source_modified") is False,
        all(row.get("state_origin") == "SIMULATED" for row in gate_report["state_rows"]),
    )
    if not all(checks):
        raise ValueError("The Day 43 failure-gate evidence is not a safe approval input.")
    schedule_path = Path(gate_report["source_day42_schedule"]["path"])
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    slot1 = next(slot for slot in schedule["slots"] if int(slot["slot"]) == 1)
    decision = config["decision"]
    if slot1["days"] != [22] or slot1["offline_only_days"] != [22] or slot1["uses_zosapi_days"]:
        raise ValueError("Day 42 Slot 1 is not the expected offline Day 22 task.")
    if int(decision["approved_slot"]) != 1 or decision["approved_days"] != [22]:
        raise ValueError("Day 44 approval is not limited to Slot 1 / Day 22.")
    return schedule_path, slot1


def validate_decision(config):
    """Ensure preparation is released without releasing source modification or execution."""

    decision = config["decision"]
    expected_status = "SLOT_01_APPROVED_FOR_ISOLATED_CANDIDATE_PREPARATION"
    if decision["decision_status"] != expected_status or decision["decision_is_teaching_record"] is not True:
        raise ValueError("The Day 44 decision status is incorrect.")
    approved = set(decision["approved_capabilities"])
    expected_approved = {
        "prepare_isolated_day22_candidate",
        "calculate_candidate_sha256",
        "generate_pre_execution_manifest",
    }
    if approved != expected_approved:
        raise ValueError("The Day 44 approved capabilities changed.")
    permissions = config["permissions"]
    true_permissions = {
        "candidate_preparation_released",
        "candidate_fingerprint_generation_released",
        "pre_execution_manifest_generation_released",
    }
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("Day 44 candidate-preparation permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 44 released a forbidden execution permission.")
    boundary = config["candidate_boundary"]
    required_boundary_flags = (
        "copy_official_config_before_edit",
        "edit_candidate_only",
        "require_exactly_one_declared_value_change",
        "require_candidate_sha256",
        "require_pre_execution_manifest",
        "future_execution_requires_separate_approval",
    )
    if any(boundary.get(key) is not True for key in required_boundary_flags):
        raise ValueError("The Day 44 isolated-candidate boundary is incomplete.")


def build_plan(config, gate_path, request_path, runbook_path, target_path, slot1):
    """Build the approval plan without generating a record or candidate."""

    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_gate": str(gate_path),
        "source_request": str(request_path),
        "source_runbook": str(runbook_path),
        "target_path": str(target_path),
        "approved_slot": int(config["decision"]["approved_slot"]),
        "approved_days": list(config["decision"]["approved_days"]),
        "execution_class": config["decision"]["approved_execution_class"],
        "slot_definition": slot1,
        "approved_capabilities": list(config["decision"]["approved_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
        "candidate_prepared": False,
        "approval_record_generated": False,
        "review_task_executed": False,
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
    config = load_config("configs/day44_slot1_candidate_preparation_approval.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    gate_path, gate_report = load_json_source(
        config, "day43_gate_report", "day43_gate_report_sha256", "expected_day43_task"
    )
    request_path, request = load_json_source(
        config, "day37_change_request", "day37_change_request_sha256", "expected_day37_task"
    )
    runbook_path, runbook = load_json_source(
        config, "day35_runbook", "day35_runbook_sha256", "expected_day35_task"
    )
    validate_runbook(config, runbook)
    target_path = validate_request_and_target(config, request)
    _, slot1 = validate_gate_and_slot(config, gate_report)
    plan = build_plan(config, gate_path, request_path, runbook_path, target_path, slot1)

    print_introduction(config)
    print("========== DAY 44 SLOT-1 CANDIDATE-PREPARATION APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, candidate file, source change or review task execution will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print(f"Approved scope: Slot {plan['approved_slot']} / Days {plan['approved_days']} / {plan['execution_class']}")
    print("Teaching value under preparation: 0.010 -> 0.012 mm")
    print("Approved capabilities:")
    for capability in plan["approved_capabilities"]:
        print(f"  - {capability}")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day 43, Day 37 and Day 35 fingerprints verified")
    print("[PASS] Day 22 target remains unchanged at the reviewed SHA256")
    print("[PASS] Approval is limited to isolated candidate preparation")
    print("[PASS] Slot 1 execution and all downstream slots remain locked")
    print("[PASS] ZOS-API, optical calculation and engineering-change claims remain forbidden")
    print("PLAN ONLY finished. No output, candidate or source modification was created.")


if __name__ == "__main__":
    main()
