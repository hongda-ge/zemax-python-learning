"""Day 49 step 1: audit the Day 48 Slot 1 result at the CP09 gate."""

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
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Allow offline review/reporting only and keep every execution locked."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 49 execution switch must be Boolean.")
    allowed_true = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 49 review evaluation and reporting must be allowed.")
    if any(value is not False for key, value in execution.items() if key not in allowed_true):
        raise ValueError("Day 49 enabled an execution or modification capability.")


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    """Load one exact JSON source with verified task/status metadata."""

    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 49 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"The Day 49 source metadata is incorrect: {path_key}")
    return path, report


def validate_files(config):
    """Recheck official and candidate fingerprints after Slot 1 execution."""

    source = config["source"]
    official_path = (PROJECT_ROOT / source["official_day22_config"]).resolve()
    candidate_path = (PROJECT_ROOT / source["candidate_config"]).resolve()
    if not official_path.is_file() or sha256_file(official_path) != source["official_day22_sha256"]:
        raise ValueError("The official Day 22 config changed before CP09 review.")
    if not candidate_path.is_file() or sha256_file(candidate_path) != source["candidate_sha256"]:
        raise ValueError("The Day 22 candidate changed before CP09 review.")
    return official_path, candidate_path


def validate_authorization_and_safety(config, approval, result):
    """Require one authorized completion and all retained safety boundaries."""

    criteria = config["review_criteria"]
    source = config["source"]
    checks = (
        approval.get("decision_status") == "SLOT_01_APPROVED_FOR_CANDIDATE_OFFLINE_REVIEW_EXECUTION",
        approval.get("approved_task_executed") is False,
        result["authorization"]["day47_approval_sha256"] == source["day47_approval_sha256"],
        int(result["authorization"]["execution_count_consumed"])
        == int(criteria["require_execution_count_consumed"]),
        result.get("slot1_execution_completed") is criteria["require_slot1_completed"],
        result.get("cp09_review_status") == "PENDING",
        result.get("slot2_execution_released") is False,
        result.get("downstream_slots_released") is False,
        result.get("new_zosapi_connection_created") is False,
        result.get("new_optical_metric_calculated") is False,
        result.get("interpolation_used") is False,
        result.get("extrapolation_used") is False,
        result.get("existing_source_modified") is False,
        result.get("engineering_recommendation") is None,
        result.get("engineering_change_approved") is False,
    )
    if not all(checks):
        raise ValueError("The Day 48 result failed the CP09 authorization or safety audit.")


def source_allowance_map(report):
    """Return error-source allowances keyed by source id."""

    return {
        row["id"]: float(row["symmetric_allowance_mm"])
        for row in report["teaching_error_sources"]
    }


def combined_allowance(report, policy_id):
    """Read the repeated combined allowance from one policy's first detail row."""

    rows = [row for row in report["details"] if row["combination_policy_id"] == policy_id]
    if not rows:
        raise ValueError(f"Missing policy details: {policy_id}")
    values = {round(float(row["combined_error_allowance_mm"]), 12) for row in rows}
    if len(values) != 1:
        raise ValueError(f"Inconsistent combined allowance: {policy_id}")
    return float(rows[0]["combined_error_allowance_mm"])


def compare_results(config, baseline, candidate):
    """Prove the numerical changes follow only the declared allowance change."""

    criteria = config["review_criteria"]
    old_sources = source_allowance_map(baseline)
    new_sources = source_allowance_map(candidate)
    if set(old_sources) != set(new_sources):
        raise ValueError("The Day 22 error-source identities changed.")
    changed = [key for key in old_sources if not math.isclose(old_sources[key], new_sources[key], abs_tol=1e-12)]
    if changed != ["positioning_accuracy"]:
        raise ValueError("A non-approved Day 22 error source changed.")
    if not math.isclose(old_sources["positioning_accuracy"], float(criteria["baseline_positioning_accuracy_mm"]), abs_tol=1e-12):
        raise ValueError("The baseline positioning allowance is incorrect.")
    if not math.isclose(new_sources["positioning_accuracy"], float(criteria["candidate_positioning_accuracy_mm"]), abs_tol=1e-12):
        raise ValueError("The candidate positioning allowance is incorrect.")

    old_summaries = {row["combination_policy_id"]: row for row in baseline["summaries"]}
    new_summaries = {row["combination_policy_id"]: row for row in candidate["summaries"]}
    if set(old_summaries) != set(new_summaries):
        raise ValueError("The Day 22 combination policy identities changed.")
    comparisons = []
    for policy_id in sorted(old_summaries):
        old_summary = old_summaries[policy_id]
        new_summary = new_summaries[policy_id]
        old_allowance = combined_allowance(baseline, policy_id)
        new_allowance = combined_allowance(candidate, policy_id)
        allowance_delta = new_allowance - old_allowance
        required_delta = (
            float(new_summary["required_half_travel_for_full_sampled_coverage_mm"])
            - float(old_summary["required_half_travel_for_full_sampled_coverage_mm"])
        )
        if not math.isclose(required_delta, allowance_delta, abs_tol=1e-12):
            raise ValueError(f"The required-travel delta is unexplained: {policy_id}")
        if old_summary["passed_case_ids"] != new_summary["passed_case_ids"]:
            raise ValueError(f"The passed-case set changed unexpectedly: {policy_id}")
        if old_summary["failed_case_ids"] != new_summary["failed_case_ids"]:
            raise ValueError(f"The failed-case set changed unexpectedly: {policy_id}")
        comparisons.append(
            {
                "combination_policy_id": policy_id,
                "baseline_combined_allowance_mm": old_allowance,
                "candidate_combined_allowance_mm": new_allowance,
                "combined_allowance_increase_mm": allowance_delta,
                "required_half_travel_increase_mm": required_delta,
                "baseline_required_half_travel_mm": float(
                    old_summary["required_half_travel_for_full_sampled_coverage_mm"]
                ),
                "candidate_required_half_travel_mm": float(
                    new_summary["required_half_travel_for_full_sampled_coverage_mm"]
                ),
                "passed_case_ids": list(new_summary["passed_case_ids"]),
                "failed_case_ids": list(new_summary["failed_case_ids"]),
            }
        )
    linear = next(row for row in comparisons if row["combination_policy_id"] == "worst_case_linear")
    if not math.isclose(
        linear["combined_allowance_increase_mm"],
        float(criteria["expected_linear_allowance_increase_mm"]),
        abs_tol=1e-12,
    ):
        raise ValueError("The linear allowance increase does not equal 0.002 mm.")
    return changed, comparisons


def validate_decision(config):
    """Pass the Slot 1 evidence review without releasing Slot 2."""

    decision = config["decision"]
    if decision["decision_status"] != "SLOT_01_RESULT_REVIEW_PASSED_WAITING_FOR_SLOT_02_RELEASE_APPROVAL":
        raise ValueError("The Day 49 decision status is incorrect.")
    permissions = config["permissions"]
    true_permissions = {"slot_01_result_review_completed", "slot_02_release_request_eligible"}
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("The Day 49 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 49 unexpectedly released an execution or change capability.")


def build_plan(config, result_path, approval_path, baseline_path, official_path, candidate_path, changed_sources, comparisons):
    """Build the CP09 plan without generating a record or releasing Slot 2."""

    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "day48_result_path": str(result_path),
        "day48_result_sha256": config["source"]["day48_result_sha256"],
        "day47_approval_path": str(approval_path),
        "baseline_path": str(baseline_path),
        "official_path": str(official_path),
        "candidate_path": str(candidate_path),
        "changed_error_sources": changed_sources,
        "comparisons": comparisons,
        "released_capabilities": list(config["decision"]["released_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
        "task_review_passed": True,
        "all_teaching_cases_passed": False,
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
    config = load_config("configs/day49_cp09_slot1_result_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(
        config, "day48_result", "day48_result_sha256", "expected_day48_task"
    )
    approval_path, approval = load_frozen_json(
        config, "day47_approval", "day47_approval_sha256", "expected_day47_task"
    )
    baseline_path, baseline = load_frozen_json(
        config, "baseline_day22_result", "baseline_day22_sha256", "expected_baseline_task"
    )
    official_path, candidate_path = validate_files(config)
    validate_authorization_and_safety(config, approval, result)
    changed_sources, comparisons = compare_results(config, baseline, result)
    plan = build_plan(
        config, result_path, approval_path, baseline_path, official_path,
        candidate_path, changed_sources, comparisons,
    )

    print_introduction(config)
    print("========== DAY 49 CP09 SLOT-1 RESULT REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, source change, ZOS-API connection or Slot 2 execution will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Task review: PASS")
    print("All teaching cases pass: False (4/6 pass under both policies)")
    print(f"Only changed error source: {plan['changed_error_sources']}")
    print("New-versus-baseline audit:")
    for row in plan["comparisons"]:
        print(
            f"  {row['combination_policy_id']}: allowance +{row['combined_allowance_increase_mm']:.7f} mm, "
            f"required half travel +{row['required_half_travel_increase_mm']:.7f} mm, "
            f"failed={row['failed_case_ids']}"
        )
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day48 result, Day47 approval and baseline result verified")
    print("[PASS] Slot 1 executed once under the exact approval and retained all safety locks")
    print("[PASS] Only positioning accuracy changed from 0.010 to 0.012 mm")
    print("[PASS] Required-travel changes exactly equal the explicit allowance changes")
    print("[PASS] Task review PASS is kept separate from the 4/6 teaching-case result")
    print("[PASS] Slot 2 and all downstream tasks remain locked")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
