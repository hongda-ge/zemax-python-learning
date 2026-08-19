"""Day 61 step 1: audit the Day 60 Slot 4 control at CP09."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 61 execution switch must be Boolean.")
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 61 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 61 enabled execution or modification.")


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 61 evidence changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key]:
        raise ValueError(f"Frozen Day 61 task identity changed: {path_key}")
    if path_key != "authorization_marker" and report.get("status") != "success":
        raise ValueError(f"Frozen Day 61 evidence is not successful: {path_key}")
    return path, report


def validate_authorization(config, approval, marker, result):
    criteria = config["review_criteria"]
    checks = (
        approval.get("decision_status") == "SLOT_04_APPROVED_FOR_DAY25_ZERO_OFFSET_CONTROL_EXECUTION",
        approval.get("approved_execution_contract", {}).get("resource_slot") == int(criteria["expected_slot"]),
        approval.get("approved_execution_contract", {}).get("approved_case_id") == criteria["expected_case_id"],
        approval.get("approved_execution_contract", {}).get("maximum_execution_count") == 1,
        approval.get("approved_task_executed_by_day59") is False,
        marker.get("status") == "consumed_before_zosapi_execution",
        marker.get("approval_sha256") == config["source"]["day59_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("maximum_execution_count") == 1,
        marker.get("rerun_released") is False,
        result.get("resource_slot") == int(criteria["expected_slot"]),
        result.get("approval", {}).get("sha256") == config["source"]["day59_approval_sha256"],
        result.get("approval", {}).get("decision_id") == approval.get("decision_id"),
        result.get("approval", {}).get("consumed_once") is criteria["require_approval_consumed_once"],
        Path(result.get("approval", {}).get("consumption_marker", "")).resolve()
        == (PROJECT_ROOT / config["source"]["authorization_marker"]).resolve(),
    )
    if not all(checks):
        raise ValueError("Day 60 did not consume the exact Day 59 authorization once.")


def validate_result_safety(config, result):
    criteria = config["review_criteria"]
    case = result.get("case", {})
    checks = (
        case.get("case_id") == criteria["expected_case_id"],
        math.isclose(float(case["offset_mm"]), float(criteria["expected_offset_mm"]), abs_tol=1e-12),
        case.get("is_control") is True,
        result.get("slot4_baseline_control_completed") is True,
        result.get("balanced_acceptance_pass") is criteria["require_balanced_acceptance_pass"],
        all(result.get("balanced_acceptance_checks", {}).values()),
        result.get("connection_closed") is criteria["require_connection_closed"],
        result.get("input_model_unchanged") is criteria["require_input_model_unchanged"],
        result.get("working_copy_unchanged") is criteria["require_working_copy_unchanged"],
        result.get("all_frozen_inputs_unchanged") is criteria["require_all_frozen_inputs_unchanged"],
        result.get("nine_boundary_cases_executed") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("downstream_slots_released") is False,
        result.get("continuous_tolerance_claimed") is False,
        result.get("engineering_change_approved") is False,
        result.get("cp09_manual_review_required") is criteria["require_cp09_pending"],
        result.get("post_execution_gate") == "CP09_slot_gate",
    )
    if not all(checks):
        raise ValueError("The Day 60 result failed the CP09 safety audit.")


def validate_files_and_metrics(config, result):
    criteria = config["review_criteria"]
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    historical_path = frozen_path(config, "historical_control", "historical_control_sha256")
    spot_path = frozen_path(config, "raw_spot", "raw_spot_sha256")
    mtf_path = frozen_path(config, "raw_mtf", "raw_mtf_sha256")
    working_path = Path(result["working_copy"])
    if not working_path.is_file() or sha256_file(working_path) != config["source"]["focused_model_sha256"]:
        raise ValueError("The Day 60 disk working copy differs from the focused model.")
    checks = (
        Path(result["spot_text"]).resolve() == spot_path,
        Path(result["mtf_text"]).resolve() == mtf_path,
        result.get("input_sha256_before") == config["source"]["focused_model_sha256"],
        result.get("input_sha256_after") == config["source"]["focused_model_sha256"],
        int(result["spot_metrics"]["field_count"]) == int(criteria["expected_spot_field_count"]),
        len(result["mtf_summary"]["frequencies"]) == int(criteria["expected_mtf_frequency_count"]),
        float(result["maximum_historical_spot_difference_um"])
        <= float(criteria["maximum_spot_reproduction_difference_um"]),
        float(result["maximum_historical_mtf_difference"])
        <= float(criteria["maximum_mtf_reproduction_difference"]),
        len(result.get("historical_reproduction", [])) == 6,
        all(row.get("passed") is True for row in result.get("historical_reproduction", [])),
    )
    if not all(checks):
        raise ValueError("Day 60 raw evidence or reproduction metrics are incomplete.")
    return {
        "focused_model": model_path,
        "historical_control": historical_path,
        "working_copy": working_path,
        "spot_text": spot_path,
        "spot_sha256": sha256_file(spot_path),
        "mtf_text": mtf_path,
        "mtf_sha256": sha256_file(mtf_path),
        "maximum_spot_difference_um": float(result["maximum_historical_spot_difference_um"]),
        "maximum_mtf_difference": float(result["maximum_historical_mtf_difference"]),
    }


def validate_decision(config):
    expected = "SLOT_04_BASELINE_RESULT_REVIEW_PASSED_WAITING_FOR_BOUNDARY_BATCH_APPROVAL"
    if config["decision"]["decision_status"] != expected:
        raise ValueError("The Day 61 decision status is incorrect.")
    released = {"slot_04_baseline_review_completed", "boundary_batch_release_request_eligible"}
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 61 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 61 unexpectedly released execution or change authority.")


def build_plan(config, result_path, approval_path, marker_path, audit):
    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "result_path": str(result_path),
        "result_sha256": config["source"]["day60_result_sha256"],
        "approval_path": str(approval_path),
        "marker_path": str(marker_path),
        "audit": audit,
        "released_capabilities": list(config["decision"]["released_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
    }


def print_introduction(config):
    intro = config["teaching_introduction"]
    print("========== TODAY'S INTRODUCTION ==========")
    print(f"Why today: {intro['why_today']}")
    print(f"Link to yesterday: {intro['relation_to_previous_day']}")
    print("Core concepts:")
    for concept in intro["concepts"]:
        print(f"  - {concept}")
    print(f"Completion standard: {intro['completion_standard']}")
    print()


def prepare_plan(config):
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(
        config, "day60_result", "day60_result_sha256", "expected_day60_task"
    )
    marker_path, marker = load_frozen_json(
        config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task"
    )
    approval_path, approval = load_frozen_json(
        config, "day59_approval", "day59_approval_sha256", "expected_day59_task"
    )
    validate_authorization(config, approval, marker, result)
    validate_result_safety(config, result)
    audit = validate_files_and_metrics(config, result)
    return result, build_plan(config, result_path, approval_path, marker_path, audit)


def main():
    config = load_config("configs/day61_cp09_slot4_baseline_review.yaml")
    _, plan = prepare_plan(config)
    audit = plan["audit"]
    print_introduction(config)
    print("========== DAY 61 CP09 SLOT-4 BASELINE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, ZOS-API connection, optical calculation or boundary-batch release will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Slot 4 zero-offset control task review: PASS")
    print("Executed case: boundary_control_000 only")
    print(f"Maximum Spot reproduction difference: {audit['maximum_spot_difference_um']:.9f} um")
    print(f"Maximum MTF reproduction difference: {audit['maximum_mtf_difference']:.9f}")
    print(f"Spot raw text SHA256: {audit['spot_sha256']}")
    print(f"FFT MTF raw text SHA256: {audit['mtf_sha256']}")
    print("Balanced acceptance: PASS (four independent metrics)")
    print("Nine-case boundary execution approved: False")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day60 result, consumption marker and Day59 approval verified")
    print("[PASS] One-time authorization and zero-offset case identity verified")
    print("[PASS] Spot/MTF raw files and historical reproduction are complete")
    print("[PASS] Balanced four-metric AND rule passed")
    print("[PASS] Model hashes and connection closure passed the safety audit")
    print("[PASS] Review PASS remains separate from boundary-batch execution approval")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
