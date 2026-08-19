"""Day 68 step 1: validate the Day 27 evidence-recovery plan."""

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


def load_json(config, path_key, hash_key, expected_task_key):
    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"Frozen Day 68 evidence changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 68 metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_plan_evaluation", "allow_plan_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 68 planning work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 68 enabled execution or source modification.")


def validate_day67(config, review):
    checks = (
        review.get("decision_status") == config["source"]["expected_day67_status"],
        review.get("cp09_review", {}).get("package_execution_review_status") == "PASS",
        review.get("cp09_review", {}).get("day26_result_review_status") == "ACCEPTED",
        review.get("cp09_review", {}).get("day27_task_state") == "BLOCKED_BY_MISSING_EXACT_MEASURED_STATES",
        review.get("cp09_review", {}).get("slot6_release_condition_met") is False,
        review.get("permissions", {}).get("evidence_recovery_plan_request_eligible") is True,
        review.get("permissions", {}).get("evidence_recovery_execution_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 67 does not permit evidence-recovery planning.")


def validate_recipe_and_control(config, control):
    source = config["source"]
    config_path = (PROJECT_ROOT / source["day25_config"]).resolve()
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    if sha256_file(config_path) != source["day25_config_sha256"]:
        raise ValueError("Day 25 config changed before Day 68 planning.")
    if sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("Focused model changed before Day 68 planning.")
    day25 = load_config(source["day25_config"])
    analysis = day25["analysis"]
    contract = config["analysis_contract"]
    checks = (
        analysis["standard_spot"]["reference"] == "centroid",
        analysis["standard_spot"]["fields"] == "all",
        analysis["standard_spot"]["wavelengths"] == "all",
        [float(value) for value in analysis["fft_mtf"]["evaluation_frequencies_cyc_per_mm"]] == [30.0, 50.0],
        control.get("case", {}).get("case_id") == "boundary_control_000",
        math.isclose(float(control["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        control.get("balanced_acceptance_pass") is True,
        control.get("connection_closed") is True,
        control.get("input_model_unchanged") is True,
        control.get("working_copy_unchanged") is True,
        control.get("quick_focus_used") is False,
        control.get("optimization_used") is False,
        control.get("save_as_used") is False,
        contract["quick_focus_allowed"] is False,
        contract["optimization_allowed"] is False,
        contract["save_as_allowed"] is False,
        contract["interpolation_allowed"] is False,
    )
    if not all(checks):
        raise ValueError("Day 68 optical recipe or recent control is invalid.")
    return config_path, model_path, day25


def build_recovery_cases(config, audit, measured_report):
    scope = config["recovery_scope"]
    expected_missing = sorted(round(float(value), 12) for value in scope["missing_offsets_mm"])
    actual_missing = sorted(round(float(value), 12) for value in audit["missing_unique_offsets_mm"])
    if actual_missing != expected_missing:
        raise ValueError("Day 68 missing-offset scope differs from Day 66 evidence.")
    measured = {round(float(row["offset_mm"]), 12) for row in measured_report["combined_measured_points"]}
    if any(value in measured for value in expected_missing):
        raise ValueError("A planned recovery offset already has an exact measurement.")
    reference = float(scope["reference_image_distance_mm"])
    dependency_map = {}
    for candidate in audit["candidate_requirements"]:
        for value in candidate["missing_offsets_mm"]:
            dependency_map.setdefault(round(float(value), 12), []).append(candidate["candidate_id"])
    rows = []
    for index, offset in enumerate(expected_missing, start=1):
        rows.append({
            "case_id": f"recovery_{index:03d}",
            "offset_mm": offset,
            "target_image_distance_mm": reference + offset,
            "required_by_candidates": dependency_map[offset],
            "standard_spot_planned": True,
            "fft_mtf_planned": True,
            "quick_focus_planned": False,
            "execution_released": False,
        })
    if len(rows) != int(scope["expected_new_case_count"]):
        raise ValueError("Day 68 recovery case count changed.")
    if set(dependency_map) != set(expected_missing) or any(not candidates for candidates in dependency_map.values()):
        raise ValueError("The seven-point recovery set is not minimally justified.")
    return rows


def validate_stages_and_permissions(config):
    stages = config["staged_recovery"]
    if [row["stage_id"] for row in stages] != [
        "stage_01_zero_control",
        "stage_02_seven_point_batch",
        "stage_03_day27_offline_recalculation",
        "stage_04_slot6_release_review",
    ]:
        raise ValueError("Day 68 recovery stages changed.")
    if any(row["execution_released"] is not False for row in stages):
        raise ValueError("Day 68 released a planned recovery stage.")
    released = {"evidence_recovery_plan_completed", "zero_control_approval_request_eligible"}
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 68 planning permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 68 released execution or Slot 6.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_stages_and_permissions(config)
    review_path, review = load_json(config, "day67_review", "day67_review_sha256", "expected_day67_task")
    audit_path, audit = load_json(config, "day27_evidence_audit", "day27_evidence_audit_sha256", "expected_day27_task")
    measured_path, measured = load_json(config, "day25_measured_report", "day25_measured_report_sha256", "expected_day25_task")
    control_path, control = load_json(config, "recent_zero_control", "recent_zero_control_sha256", "expected_zero_control_task")
    validate_day67(config, review)
    config_path, model_path, day25 = validate_recipe_and_control(config, control)
    cases = build_recovery_cases(config, audit, measured)
    workload = config["planned_workload_if_all_future_stages_are_approved"]
    if any(int(workload[key]) != expected for key, expected in {
        "total_zosapi_connections": 8,
        "total_independent_working_copies": 8,
        "total_standard_spot_exports": 8,
        "total_fft_mtf_exports": 8,
        "total_quick_focus_runs": 0,
    }.items()):
        raise ValueError("Day 68 planned workload changed.")
    return {
        "review_path": review_path,
        "audit_path": audit_path,
        "measured_path": measured_path,
        "control_path": control_path,
        "config_path": config_path,
        "model_path": model_path,
        "day25": day25,
        "cases": cases,
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
    config = load_config("configs/day68_day27_evidence_recovery_plan.yaml")
    plan = prepare_plan(config)
    print_introduction(config)
    print("========== DAY 68 DAY27 EVIDENCE-RECOVERY PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy, optical analysis or recovery execution will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print(f"Focused model: {plan['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print("Minimal sufficient seven-point recovery set:")
    for row in plan["cases"]:
        print(f"  {row['case_id']}: offset={row['offset_mm']:+.3f} mm, image={row['target_image_distance_mm']:.10f} mm, required_by={row['required_by_candidates']}")
    print("Planned stages:")
    for stage in config["staged_recovery"]:
        print(f"  {stage['stage_id']}: cases={stage['planned_cases']}, released={stage['execution_released']}, next={stage['next_gate']}")
    workload = config["planned_workload_if_all_future_stages_are_approved"]
    print(f"Total future workload after separate approvals: connections/copies/Spot/MTF={workload['total_zosapi_connections']}/{workload['total_independent_working_copies']}/{workload['total_standard_spot_exports']}/{workload['total_fft_mtf_exports']}")
    print("Zero-control execution released: False")
    print("Seven-point batch released: False")
    print("Slot 6 released: False")
    print()
    print("[PASS] Frozen Day67 review and Day66 evidence gap verified")
    print("[PASS] Seven new offsets are unique, unmeasured and each required by a candidate")
    print("[PASS] Focused model, Day25 Spot/FFT MTF recipe and recent zero control verified")
    print("[PASS] Control, batch, offline recalculation and Slot 6 review are separate stages")
    print("[PASS] Quick Focus, interpolation, source modification and engineering claims remain forbidden")
    print("[PASS] Day68 releases planning only; no execution permission was created")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
