"""Day 67 step 1: audit the completed Day 66 Slot 5 offline review package."""

import csv
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
        raise ValueError(f"Frozen Day 67 evidence changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key, expected_status="success"):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != expected_status:
        raise ValueError(f"Frozen Day 67 metadata is invalid: {path_key}")
    return path, report


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 67 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 67 enabled execution or source modification.")


def validate_authorization(config, approval, marker, package, package_path):
    criteria = config["review_criteria"]
    checks = (
        approval.get("decision_id") == "AP-DAY65-001",
        approval.get("permissions", {}).get("slot_05_offline_review_package_execution_released") is True,
        approval.get("approved_task_executed_by_day65") is False,
        marker.get("approval_sha256") == config["source"]["day65_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("resource_slot") == int(criteria["expected_slot"]),
        marker.get("days") == criteria["expected_days"],
        marker.get("maximum_execution_count") == 1,
        marker.get("execution_count_consumed") == 1,
        marker.get("rerun_released") is False,
        Path(marker.get("run_directory", "")).resolve() == package_path.parent.resolve(),
        package.get("authorization", {}).get("day65_approval_sha256") == config["source"]["day65_approval_sha256"],
        package.get("authorization", {}).get("execution_count_consumed") == 1,
        Path(package.get("authorization", {}).get("consumption_marker", "")).resolve()
        == (PROJECT_ROOT / config["source"]["authorization_marker"]).resolve(),
    )
    if not all(checks):
        raise ValueError("Day 66 authorization-consumption evidence is inconsistent.")


def validate_day26(config, result, detail_rows, summary_rows):
    criteria = config["review_criteria"]
    summaries = {row["policy_id"]: row for row in result["summaries"]}
    checks = (
        result.get("task_state") == criteria["expected_day26_state"],
        math.isclose(float(result["positioning_accuracy_mm"]), 0.012, abs_tol=1e-12),
        len(result.get("details", [])) == int(criteria["expected_day26_detail_count"]),
        len(result.get("summaries", [])) == int(criteria["expected_day26_summary_count"]),
        len(detail_rows) == int(criteria["expected_day26_detail_count"]),
        len(summary_rows) == int(criteria["expected_day26_summary_count"]),
        math.isclose(float(summaries["numerical_1um"]["maximum_unresolved_width_mm"]), 0.001, abs_tol=1e-12),
        summaries["numerical_1um"]["stop_count"] == 0,
        summaries["numerical_1um"]["total_additional_bisections_planned"] == 4,
        math.isclose(float(summaries["positioning_accuracy_matched"]["maximum_unresolved_width_mm"]), 0.012, abs_tol=1e-12),
        summaries["positioning_accuracy_matched"]["stop_count"] == 2,
        math.isclose(float(summaries["backlash_matched"]["maximum_unresolved_width_mm"]), 0.020, abs_tol=1e-12),
        summaries["backlash_matched"]["stop_count"] == 2,
        result.get("sibling_day27_state_does_not_invalidate_result") is True,
        result.get("interpolation_used") is False,
        result.get("new_zosapi_connection_created") is False,
        result.get("new_optical_metric_calculated") is False,
    )
    if not all(checks):
        raise ValueError("Day 26 change-specific result is incomplete or unsafe.")


def validate_day27(config, result, availability_rows):
    criteria = config["review_criteria"]
    missing = [round(float(value), 12) for value in result["missing_unique_offsets_mm"]]
    expected_missing = [round(float(value), 12) for value in criteria["expected_day27_missing_offsets_mm"]]
    available_csv = sum(row["exact_measurement_available"].lower() == "true" for row in availability_rows)
    checks = (
        result.get("task_state") == criteria["expected_day27_state"],
        result.get("candidate_count") == 4,
        result.get("required_state_count") == int(criteria["expected_day27_state_count"]),
        result.get("available_state_count") == int(criteria["expected_day27_available_state_count"]),
        result.get("missing_state_count") == int(criteria["expected_day27_missing_state_count"]),
        len(availability_rows) == int(criteria["expected_day27_state_count"]),
        available_csv == int(criteria["expected_day27_available_state_count"]),
        missing == expected_missing,
        result.get("envelope_evaluation_executed") is False,
        result.get("pass_candidates") is None,
        result.get("fail_candidates") is None,
        result.get("blocked_is_not_failure") is True,
        result.get("sibling_day26_result_overblocked") is False,
        result.get("interpolation_used") is False,
        result.get("new_zosapi_connection_created") is False,
        result.get("new_optical_metric_calculated") is False,
    )
    if not all(checks):
        raise ValueError("Day 27 evidence-block result is incomplete or unsafe.")


def validate_package(config, package):
    criteria = config["review_criteria"]
    interpretation = package["task_outcome_interpretation"]
    checks = (
        package.get("task_states", {}).get("day26") == criteria["expected_day26_state"],
        package.get("task_states", {}).get("day27") == criteria["expected_day27_state"],
        interpretation.get("package_execution_succeeded") is True,
        interpretation.get("day26_scientific_review_completed") is True,
        interpretation.get("day27_scientific_review_completed") is False,
        interpretation.get("day27_blocked_by_missing_evidence") is True,
        interpretation.get("blocked_is_not_execution_failure") is True,
        package.get("slot5_execution_completed") is True,
        package.get("cp09_review_status") == "PENDING",
        package.get("slot6_execution_released") is False,
        package.get("downstream_slots_released") is False,
        package.get("sibling_isolation_preserved") is True,
        package.get("new_zosapi_connection_created") is False,
        package.get("new_optical_metric_calculated") is False,
        package.get("interpolation_used") is False,
        package.get("existing_source_modified") is False,
        package.get("engineering_change_approved") is False,
    )
    if not all(checks):
        raise ValueError("Day 66 package-level evidence is incomplete or unsafe.")


def validate_decision(config):
    expected = "SLOT_05_EXECUTION_REVIEW_PASSED_DAY27_EVIDENCE_BLOCKED_SLOT_06_LOCKED"
    if config["decision"]["decision_status"] != expected:
        raise ValueError("Day 67 decision status is incorrect.")
    released = {
        "slot_05_execution_review_completed",
        "day26_result_accepted",
        "day27_evidence_block_confirmed",
        "evidence_recovery_plan_request_eligible",
    }
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 67 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 67 released execution or an engineering claim.")


def prepare_review(config):
    validate_execution_lock(config)
    validate_decision(config)
    package_path, package = load_frozen_json(config, "day66_package_result", "day66_package_sha256", "expected_day66_task")
    marker_path, marker = load_frozen_json(config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task", "consumed_before_offline_evaluation")
    approval_path, approval = load_frozen_json(config, "day65_approval", "day65_approval_sha256", "expected_day65_task")
    day26_path, day26 = load_frozen_json(config, "day26_result", "day26_result_sha256", "expected_day26_task")
    day27_path, day27 = load_frozen_json(config, "day27_result", "day27_result_sha256", "expected_day27_task")
    day26_detail_path = frozen_path(config, "day26_detail_csv", "day26_detail_csv_sha256")
    day26_summary_path = frozen_path(config, "day26_summary_csv", "day26_summary_csv_sha256")
    day27_csv_path = frozen_path(config, "day27_availability_csv", "day27_availability_csv_sha256")
    validate_authorization(config, approval, marker, package, package_path)
    validate_package(config, package)
    validate_day26(config, day26, read_csv(day26_detail_path), read_csv(day26_summary_path))
    validate_day27(config, day27, read_csv(day27_csv_path))
    return {
        "package_path": package_path,
        "package": package,
        "marker_path": marker_path,
        "approval_path": approval_path,
        "day26_path": day26_path,
        "day26": day26,
        "day27_path": day27_path,
        "day27": day27,
        "day26_detail_path": day26_detail_path,
        "day26_summary_path": day26_summary_path,
        "day27_csv_path": day27_csv_path,
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
    config = load_config("configs/day67_cp09_slot5_offline_review.yaml")
    review = prepare_review(config)
    print_introduction(config)
    print("========== DAY 67 CP09 SLOT-5 OFFLINE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, rerun, ZOS-API connection, evidence recovery or Slot 6 release will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print(f"Day66 package result: {review['package_path']}")
    print(f"Day66 package SHA256: {config['source']['day66_package_sha256']}")
    print("Slot 5 package execution review: PASS")
    print("Day26 scientific review: COMPLETED / ACCEPTED")
    print("  numerical_1um: 0/2 STOP; planned bisections=4")
    print("  positioning_accuracy_matched: 2/2 STOP at 0.012 mm")
    print("  backlash_matched: 2/2 STOP at 0.020 mm")
    print("Day27 scientific review: BLOCKED_BY_MISSING_EXACT_MEASURED_STATES")
    print(f"  exact states: {review['day27']['available_state_count']}/{review['day27']['required_state_count']} available")
    print(f"  missing offsets: {review['day27']['missing_unique_offsets_mm']}")
    print("Slot 6 release request eligible: False")
    print("Evidence-recovery plan request eligible: True")
    print()
    print("[PASS] Day65 approval and one-time Day66 consumption verified")
    print("[PASS] Day26 JSON plus six detail and three summary rows verified")
    print("[PASS] Day27 JSON plus twelve exact-state availability rows verified")
    print("[PASS] Package PASS remains separate from Day27 scientific blocking")
    print("[PASS] Day26 result retained without same-slot overblocking")
    print("[PASS] No rerun, interpolation, ZOS-API or Slot 6 release")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
