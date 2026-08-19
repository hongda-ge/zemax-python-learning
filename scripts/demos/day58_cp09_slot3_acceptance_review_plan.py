"""Day 58 step 1: validate the CP09 Slot 3 acceptance review plan."""

import csv
import hashlib
import json
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
        raise ValueError(f"Frozen Day 58 evidence changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key, expected_status="success"):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != expected_status:
        raise ValueError(f"Frozen Day 58 source metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 58 execution switch must be Boolean.")
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 58 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 58 enabled rerun, ZOS-API or downstream work.")


def validate_authorization(config, result, marker, approval):
    checks = (
        result["authorization"]["day56_approval_sha256"] == config["source"]["day56_approval_sha256"],
        result["authorization"]["decision_id"] == approval["decision_id"],
        result["authorization"]["execution_count_consumed"] == 1,
        marker.get("approval_sha256") == config["source"]["day56_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("maximum_execution_count") == 1,
        marker.get("execution_count_consumed") == 1,
        marker.get("rerun_released") is False,
        Path(marker["run_directory"]).resolve() == Path(result["runtime_output_directory"]).resolve(),
        approval.get("approved_task_executed_by_day56") is False,
    )
    if not all(checks):
        raise ValueError("Day 57 one-time authorization evidence is invalid.")


def signature(summaries):
    return {
        row["scenario_id"]: {
            "passed_count": int(row["passed_count"]),
            "passed_case_ids": row["passed_case_ids"],
            "failed_case_ids": row["failed_case_ids"],
        }
        for row in summaries
    }


def validate_result(config, result):
    criteria = config["review_criteria"]
    counts = criteria["expected_scenario_counts"]
    actual = {row["scenario_id"]: int(row["passed_count"]) for row in result["scenario_summaries"]}
    checks = (
        result["authorization"]["resource_slot"] == int(criteria["expected_slot"]),
        result["authorization"]["day"] == int(criteria["expected_day"]),
        result["case_count"] == int(criteria["expected_case_count"]),
        len(result["details"]) == int(criteria["expected_detail_count"]),
        len(result["scenario_summaries"]) == int(criteria["expected_summary_count"]),
        actual == {key: int(value) for key, value in counts.items()},
        result["combination_rule"] == "all_required_metrics_must_pass",
        signature(result["scenario_summaries"]) == result["historical_reproduction_signature"],
        result["historical_day24_report"]["reproduced"] is True,
        result["slot3_execution_completed"] is True,
        result["cp09_review_status"] == "PENDING",
        result["slot4_execution_released"] is False,
        result["downstream_slots_released"] is False,
        result["measured_points_only"] is True,
        result["interpolation_used"] is False,
        result["extrapolation_used"] is False,
        result["hidden_weighted_score_used"] is False,
        result["continuous_tolerance_claimed"] is False,
        result["new_zosapi_connection_created"] is False,
        result["new_optical_metric_calculated"] is False,
        result["existing_source_modified"] is False,
        result["engineering_recommendation"] is None,
        result["engineering_change_approved"] is False,
    )
    if not all(checks):
        raise ValueError("Day 57 Slot 3 result failed CP09 review.")
    return actual


def validate_output_files(config, result):
    detail_path = frozen_path(config, "detail_csv", "detail_csv_sha256")
    summary_path = frozen_path(config, "summary_csv", "summary_csv_sha256")
    figure_path = frozen_path(config, "figure", "figure_sha256")
    with detail_path.open("r", encoding="utf-8-sig", newline="") as stream:
        detail_rows = list(csv.DictReader(stream))
    with summary_path.open("r", encoding="utf-8-sig", newline="") as stream:
        summary_rows = list(csv.DictReader(stream))
    if len(detail_rows) != len(result["details"]) or len(summary_rows) != len(result["scenario_summaries"]):
        raise ValueError("Day 57 CSV row counts do not match the JSON result.")
    if figure_path.stat().st_size <= 0:
        raise ValueError("Day 57 acceptance matrix is empty.")
    return detail_path, summary_path, figure_path


def validate_permissions(config):
    permissions = config["permissions"]
    released = {"slot_03_acceptance_review_completed", "slot_04_release_request_eligible"}
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 58 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 58 released a forbidden permission.")


def prepare_review(config):
    validate_execution_lock(config)
    validate_permissions(config)
    result_path, result = load_frozen_json(config, "day57_result", "day57_result_sha256", "expected_day57_task")
    marker_path, marker = load_frozen_json(config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task", "consumed_before_offline_evaluation")
    approval_path, approval = load_frozen_json(config, "day56_approval", "day56_approval_sha256", "expected_day56_task")
    validate_authorization(config, result, marker, approval)
    counts = validate_result(config, result)
    detail_path, summary_path, figure_path = validate_output_files(config, result)
    return {
        "result_path": result_path,
        "result": result,
        "marker_path": marker_path,
        "approval_path": approval_path,
        "counts": counts,
        "detail_path": detail_path,
        "summary_path": summary_path,
        "figure_path": figure_path,
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
    config = load_config("configs/day58_cp09_slot3_acceptance_review.yaml")
    review = prepare_review(config)
    print_introduction(config)
    print("========== DAY 58 CP09 SLOT-3 ACCEPTANCE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, rerun, ZOS-API connection or Slot 4 release will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Slot 3 acceptance task review: PASS")
    print(f"Cases / details / summaries: {review['result']['case_count']} / {len(review['result']['details'])} / {len(review['result']['scenario_summaries'])}")
    for scenario_id, count in review["counts"].items():
        print(f"  {scenario_id}: {count}/7 measured points pass")
    print("Historical Day24 reproduction: PASS")
    print("Slot 4 release approved: False")
    print()
    print("[PASS] Day57 execution and Day56 one-time authorization verified")
    print("[PASS] JSON, detail CSV, summary CSV and acceptance matrix fingerprinted")
    print("[PASS] Twenty-one detail rows and three scenario summaries verified")
    print("[PASS] Historical scenario signatures reproduced exactly")
    print("[PASS] Task-review PASS remains separate from per-scenario case coverage")
    print("[PASS] Day57 rerun, ZOS-API and Slot 4-6 remain locked")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
