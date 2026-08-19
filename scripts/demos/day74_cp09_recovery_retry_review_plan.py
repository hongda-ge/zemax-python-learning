"""Day 74 step 1: audit the Day 73 recovery retry at CP09."""

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
        raise ValueError("Every Day 74 execution switch must be Boolean.")
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 74 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 74 enabled execution or modification.")


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 74 evidence changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key]:
        raise ValueError(f"Frozen Day 74 task identity changed: {path_key}")
    if path_key != "authorization_marker" and report.get("status") != "success":
        raise ValueError(f"Frozen Day 74 evidence is not successful: {path_key}")
    return path, report


def validate_authorization(config, approval, marker, result):
    criteria = config["review_criteria"]
    checks = (
        approval.get("decision_status") == "DAY27_RECOVERY_BASELINE_RETRY_APPROVED_FOR_ONE_ZERO_CONTROL_ATTEMPT",
        approval.get("approved_execution_contract", {}).get("recovery_stage") == "stage_01_zero_control_retry_01",
        approval.get("approved_execution_contract", {}).get("maximum_execution_count") == 1,
        approval.get("approved_retry_executed_by_day72") is False,
        marker.get("status") == "consumed_before_zosapi_retry_attempt",
        marker.get("approval_sha256") == config["source"]["day72_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("maximum_execution_count") == 1,
        marker.get("additional_retry_released") is False,
        result.get("approval", {}).get("sha256") == config["source"]["day72_approval_sha256"],
        result.get("approval", {}).get("decision_id") == approval.get("decision_id"),
        result.get("approval", {}).get("consumed_once") is criteria["require_approval_consumed_once"],
        result.get("approval", {}).get("additional_retry_released") is False,
        Path(result.get("approval", {}).get("consumption_marker", "")).resolve()
        == (PROJECT_ROOT / config["source"]["authorization_marker"]).resolve(),
    )
    if not all(checks):
        raise ValueError("Day 73 did not consume the exact Day 72 authorization once.")


def validate_result_safety(config, result):
    criteria = config["review_criteria"]
    case = result.get("case", {})
    checks = (
        case.get("case_id") == criteria["expected_case_id"],
        math.isclose(float(case["offset_mm"]), float(criteria["expected_offset_mm"]), abs_tol=1e-12),
        case.get("is_control") is True,
        case.get("is_retry") is True,
        int(case.get("retry_number")) == int(criteria["expected_retry_number"]),
        result.get("retry_outcome") == criteria["expected_retry_outcome"],
        result.get("recovery_baseline_retry_completed") is True,
        result.get("standalone_zosapi_license_reverified") is criteria["require_license_reverified"],
        result.get("connection", {}).get("license_valid") is True,
        result.get("connection", {}).get("connected") is True,
        result.get("balanced_acceptance_pass") is criteria["require_balanced_acceptance_pass"],
        all(result.get("balanced_acceptance_checks", {}).values()),
        result.get("connection_closed") is criteria["require_connection_closed"],
        result.get("input_model_unchanged") is criteria["require_input_model_unchanged"],
        result.get("working_copy_unchanged") is criteria["require_working_copy_unchanged"],
        result.get("all_frozen_inputs_unchanged") is criteria["require_all_frozen_inputs_unchanged"],
        result.get("seven_recovery_cases_executed") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("day27_recalculated") is False,
        result.get("slot6_released") is False,
        result.get("continuous_tolerance_claimed") is False,
        result.get("engineering_change_approved") is False,
        result.get("cp09_manual_review_required") is criteria["require_cp09_pending"],
        result.get("post_execution_gate") == "CP09_retry_gate",
    )
    if not all(checks):
        raise ValueError("The Day 73 result failed the CP09 safety or recovery audit.")


def validate_files_and_metrics(config, result):
    criteria = config["review_criteria"]
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    historical_path = frozen_path(config, "historical_control", "historical_control_sha256")
    spot_path = frozen_path(config, "raw_spot", "raw_spot_sha256")
    mtf_path = frozen_path(config, "raw_mtf", "raw_mtf_sha256")
    working_path = Path(result["working_copy"])
    if not working_path.is_file() or sha256_file(working_path) != config["source"]["focused_model_sha256"]:
        raise ValueError("The Day 73 disk working copy differs from the focused model.")
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
        raise ValueError("Day 73 raw evidence or reproduction metrics are incomplete.")
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
    expected = "DAY73_RECOVERY_RETRY_RESULT_REVIEW_PASSED_WAITING_FOR_SEVEN_POINT_BATCH_APPROVAL"
    if config["decision"]["decision_status"] != expected:
        raise ValueError("The Day 74 decision status is incorrect.")
    released = {"recovery_retry_review_completed", "seven_point_batch_approval_request_eligible"}
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 74 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 74 unexpectedly released execution or change authority.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(config, "day73_result", "day73_result_sha256", "expected_day73_task")
    marker_path, marker = load_frozen_json(config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task")
    approval_path, approval = load_frozen_json(config, "day72_approval", "day72_approval_sha256", "expected_day72_task")
    review_path, review = load_frozen_json(config, "day71_review", "day71_review_sha256", "expected_day71_task")
    if review.get("failure_review", {}).get("safety_review_status") != "PASS":
        raise ValueError("Day 71 failure review is not a valid recovery-chain source.")
    validate_authorization(config, approval, marker, result)
    validate_result_safety(config, result)
    audit = validate_files_and_metrics(config, result)
    plan = {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "result_path": result_path,
        "approval_path": approval_path,
        "marker_path": marker_path,
        "review_path": review_path,
        "audit": audit,
        "released_capabilities": list(config["decision"]["released_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
    }
    return result, plan


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


def main():
    config = load_config("configs/day74_cp09_recovery_retry_review.yaml")
    _, plan = prepare_plan(config)
    audit = plan["audit"]
    print_introduction(config)
    print("========== DAY 74 CP09 RECOVERY-RETRY REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, rerun, ZOS-API connection or recovery-batch release will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Day73 recovery retry task review: PASS")
    print("Standalone ZOS-API license reverified: True")
    print("Executed case: recovery_control_000 / retry 01 / +0.000 mm")
    print(f"Maximum Spot reproduction difference: {audit['maximum_spot_difference_um']:.9f} um")
    print(f"Maximum MTF reproduction difference: {audit['maximum_mtf_difference']:.9f}")
    print(f"Spot raw text SHA256: {audit['spot_sha256']}")
    print(f"FFT MTF raw text SHA256: {audit['mtf_sha256']}")
    print("Balanced acceptance: PASS (four independent metrics)")
    print("Seven-point recovery batch execution approved: False")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Day73 result, Day72 approval and one-time consumption verified")
    print("[PASS] Day70 failure and Day73 recovery form a complete audited chain")
    print("[PASS] Standalone license, connection closure and model hashes verified")
    print("[PASS] Spot/MTF raw files and zero-difference reproduction verified")
    print("[PASS] Review PASS remains separate from seven-point batch approval")
    print("[PASS] No rerun, new connection or downstream release was used")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
