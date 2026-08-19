"""Day 71 step 1: audit the Day 70 pre-analysis license failure."""

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
        raise ValueError(f"Frozen Day 71 evidence changed: {path_key}")
    return path


def load_json(config, path_key, hash_key, expected_task_key, expected_status):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != expected_status:
        raise ValueError(f"Frozen Day 71 metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 71 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 71 enabled execution or source modification.")


def validate_authorization(config, approval, marker, failure, failure_path):
    checks = (
        approval.get("decision_id") == "AP-DAY69-001",
        approval.get("permissions", {}).get("recovery_zero_control_execution_released") is True,
        approval.get("approved_task_executed_by_day69") is False,
        marker.get("approval_sha256") == config["source"]["day69_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("recovery_stage") == "stage_01_zero_control",
        marker.get("maximum_execution_count") == 1,
        marker.get("rerun_released") is False,
        Path(marker.get("run_directory", "")).resolve() == failure_path.parent.parent.resolve(),
    )
    if not all(checks):
        raise ValueError("Day 70 authorization-consumption evidence is inconsistent.")


def validate_failure(config, failure, failure_path):
    criteria = config["review_criteria"]
    case_dir = failure_path.parent
    files = sorted(path.name for path in case_dir.iterdir() if path.is_file())
    expected_files = sorted([failure_path.name, Path(config["source"]["working_copy"]).name])
    checks = (
        failure.get("status") == "failed",
        failure.get("case", {}).get("case_id") == criteria["expected_case_id"],
        math.isclose(float(failure["case"]["offset_mm"]), float(criteria["expected_offset_mm"]), abs_tol=1e-12),
        failure.get("error", {}).get("type") == criteria["expected_error_type"],
        failure.get("error", {}).get("message") == criteria["expected_error_message"],
        failure.get("input_model_unchanged") is True,
        failure.get("working_copy_unchanged") is True,
        failure.get("quick_focus_used") is False,
        failure.get("optimization_used") is False,
        failure.get("save_as_used") is False,
        failure.get("connection_closed") is False,
        files == expected_files,
    )
    if not all(checks):
        raise ValueError("Day 70 failure evidence is incomplete or outside the approved boundary.")
    return files


def validate_decision(config):
    if config["decision"]["decision_status"] != "DAY70_LICENSE_FAILURE_REVIEWED_RETRY_APPROVAL_REQUEST_ELIGIBLE":
        raise ValueError("Day 71 decision status is incorrect.")
    criteria = config["review_criteria"]
    if criteria["operator_confirmed_gui_reopened_successfully"] is not True or criteria["operator_confirmed_gui_closed_before_review"] is not True:
        raise ValueError("Day 71 operator recovery observations are incomplete.")
    if criteria["standalone_zosapi_license_reverified"] is not False:
        raise ValueError("Day 71 must not claim that Standalone ZOS-API was reverified.")
    released = {"failure_review_completed", "retry_approval_request_eligible"}
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 71 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 71 released retry execution or a downstream action.")


def prepare_review(config):
    validate_execution_lock(config)
    validate_decision(config)
    failure_path, failure = load_json(config, "day70_failure_result", "day70_failure_sha256", "expected_day70_task", "failed")
    marker_path, marker = load_json(config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task", "consumed_before_zosapi_execution")
    approval_path, approval = load_json(config, "day69_approval", "day69_approval_sha256", "expected_day69_task", "success")
    config_path = frozen_path(config, "day70_config", "day70_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    copy_path = frozen_path(config, "working_copy", "working_copy_sha256")
    validate_authorization(config, approval, marker, failure, failure_path)
    files = validate_failure(config, failure, failure_path)
    if sha256_file(model_path) != sha256_file(copy_path):
        raise ValueError("Day 70 input and working-copy hashes differ after failure.")
    return {
        "failure_path": failure_path, "failure": failure,
        "marker_path": marker_path, "marker": marker,
        "approval_path": approval_path, "approval": approval,
        "config_path": config_path, "model_path": model_path,
        "copy_path": copy_path, "case_files": files,
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
    config = load_config("configs/day71_day70_license_failure_review.yaml")
    review = prepare_review(config)
    print_introduction(config)
    print("========== DAY 71 DAY70 LICENSE-FAILURE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, ZOS-API connection, retry execution or source modification will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print(f"Failure result: {review['failure_path']}")
    print(f"Failure SHA256: {config['source']['day70_failure_sha256']}")
    print("Failure classification: PRE_ANALYSIS_ZOSAPI_LICENSE_CONNECTION_FAILURE")
    print(f"Error: {review['failure']['error']['type']}: {review['failure']['error']['message']}")
    print("Authorization consumed: True; reusable: False")
    print("ZOS-API connection established: False")
    print("Spot/FFT MTF outputs created: 0/0")
    print("Input/working copy unchanged: True/True")
    print("Operator reported GUI reopened successfully and then closed: True")
    print("Standalone ZOS-API license reverified: False")
    print("Retry approval request eligible: True")
    print("Retry execution released: False")
    print("Seven-point batch and Slot 6 released: False")
    print()
    print("[PASS] Day69 approval and one-time Day70 consumption verified")
    print("[PASS] Failure occurred before optical analysis and created no raw analysis files")
    print("[PASS] Frozen model and isolated working copy hashes remain identical")
    print("[PASS] No Quick Focus, optimization, SaveAs or source modification")
    print("[PASS] GUI recovery observation retained without claiming API license verification")
    print("[PASS] Review releases only a new retry-approval request")
    print("PLAN ONLY finished. No output, execution or retry authorization was created.")


if __name__ == "__main__":
    main()
