"""Day 72 step 1: validate the minimum-permission retry approval plan."""

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


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 72 evidence changed: {path_key}")
    return path


def load_json(config, path_key, hash_key, expected_task_key, expected_status=None):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key]:
        raise ValueError(f"Frozen Day 72 task metadata is invalid: {path_key}")
    if expected_status is not None and report.get("status") != expected_status:
        raise ValueError(f"Frozen Day 72 status is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 72 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 72 enabled retry execution or a downstream action.")


def validate_review(config, review, failure, marker):
    checks = (
        review.get("decision_status") == config["source"]["expected_day71_status"],
        review.get("failure_review", {}).get("classification") == "PRE_ANALYSIS_ZOSAPI_LICENSE_CONNECTION_FAILURE",
        review.get("failure_review", {}).get("safety_review_status") == "PASS",
        review.get("decision", {}).get("retry_approval_request_eligible") is True,
        review.get("decision", {}).get("retry_execution_approved") is False,
        review.get("permissions", {}).get("retry_approval_request_eligible") is True,
        review.get("permissions", {}).get("retry_execution_released") is False,
        review.get("license_recovery_observation", {}).get("standalone_zosapi_license_reverified") is False,
        failure.get("status") == "failed",
        failure.get("error", {}).get("type") == "ZemaxConnectionError",
        failure.get("input_model_unchanged") is True,
        failure.get("working_copy_unchanged") is True,
        marker.get("status") == "consumed_before_zosapi_execution",
        marker.get("maximum_execution_count") == 1,
        marker.get("rerun_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 71 review does not permit a new minimum-scope retry approval.")


def validate_contract(config):
    contract = config["approved_execution_contract"]
    checks = (
        contract["recovery_stage"] == "stage_01_zero_control_retry_01",
        contract["approved_case_id"] == "recovery_control_000",
        math.isclose(float(contract["approved_offset_mm"]), 0.0, abs_tol=1e-12),
        contract["maximum_execution_count"] == 1,
        contract["maximum_active_zosapi_connections"] == 1,
        contract["maximum_working_copy_count"] == 1,
        contract["required_entrypoint"] == "scripts/demos/day73_execute_approved_recovery_baseline_retry.py",
        contract["allow_standard_spot"] is True,
        contract["allow_fft_mtf"] is True,
        contract["allow_quick_focus"] is False,
        contract["allow_optimization"] is False,
        contract["allow_save_as"] is False,
        contract["allow_seven_recovery_cases"] is False,
        contract["require_authorization_consumed_before_connection"] is True,
        contract["require_stop_after_execution_or_failure"] is True,
    )
    if not all(checks):
        raise ValueError("Day 72 retry contract exceeds the reviewed boundary.")


def validate_decision(config):
    if config["decision"]["decision_status"] != "DAY27_RECOVERY_BASELINE_RETRY_APPROVED_FOR_ONE_ZERO_CONTROL_ATTEMPT":
        raise ValueError("Day 72 decision status is incorrect.")
    released = {
        "one_zero_control_retry_attempt_released",
        "one_zosapi_connection_attempt_released",
        "one_working_copy_released",
        "spot_and_mtf_analysis_if_connected_released",
    }
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 72 minimum retry permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 72 released original-authorization reuse or downstream work.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    validate_decision(config)
    review_path, review = load_json(config, "day71_review", "day71_review_sha256", "expected_day71_task", "success")
    failure_path, failure = load_json(config, "day70_failure_result", "day70_failure_sha256", "expected_day70_task", "failed")
    marker_path, marker = load_json(config, "original_authorization_marker", "original_authorization_marker_sha256", "expected_marker_task", "consumed_before_zosapi_execution")
    day70_path = frozen_path(config, "day70_config", "day70_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    historical_path, historical = load_json(config, "historical_zero_control", "historical_zero_control_sha256", "expected_historical_task", "success")
    validate_review(config, review, failure, marker)
    if historical.get("balanced_acceptance_pass") is not True:
        raise ValueError("Frozen historical zero control did not pass balanced acceptance.")
    return {
        "review_path": review_path,
        "review": review,
        "failure_path": failure_path,
        "failure": failure,
        "marker_path": marker_path,
        "marker": marker,
        "day70_path": day70_path,
        "model_path": model_path,
        "historical_path": historical_path,
        "historical": historical,
        "contract": dict(config["approved_execution_contract"]),
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


def main():
    config = load_config("configs/day72_recovery_baseline_retry_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["contract"]
    print_introduction(config)
    print("========== DAY 72 RECOVERY-BASELINE RETRY APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, retry execution, ZOS-API connection or optical analysis will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Approved scope: Day27 recovery stage 01 / zero offset / retry 01 / one attempt")
    print(f"Day71 review: {plan['review_path']}")
    print(f"Original Day69 authorization consumed/reusable: True/False")
    print("Standalone ZOS-API license already reverified: False")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {PROJECT_ROOT / contract['approved_output_root']}")
    print("One retry execution released after approval record: True")
    print("Seven-point recovery batch, Day27 recalculation and Slot 6 released: False")
    print()
    print("[PASS] Frozen Day71 failure review and retry-request eligibility verified")
    print("[PASS] Original Day69 authorization remains consumed and non-reusable")
    print("[PASS] Frozen model, Day70 recipe and historical zero control verified")
    print("[PASS] Approval is limited to one new zero-offset connection attempt")
    print("[PASS] Success and repeated-failure paths both stop at CP09")
    print("[PASS] Day72 itself creates no ZOS-API connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
