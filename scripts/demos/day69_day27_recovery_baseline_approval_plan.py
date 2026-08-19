"""Day 69 step 1: validate the minimal Day 27 recovery-control approval."""

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
        raise ValueError(f"Frozen Day 69 evidence changed: {path_key}")
    return path


def load_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 69 metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 69 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 69 enabled execution or source modification.")


def validate_day68(config, plan, case_csv_path):
    checks = (
        plan.get("decision_status") == config["source"]["expected_day68_status"],
        plan.get("recovery_case_count") == 7,
        plan.get("minimal_sufficient_set_verified") is True,
        plan.get("permissions", {}).get("evidence_recovery_plan_completed") is True,
        plan.get("permissions", {}).get("zero_control_approval_request_eligible") is True,
        plan.get("permissions", {}).get("zero_control_execution_released") is False,
        plan.get("permissions", {}).get("seven_point_batch_execution_released") is False,
        plan.get("permissions", {}).get("day27_recalculation_released") is False,
        plan.get("permissions", {}).get("slot_06_execution_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 68 does not permit zero-control approval.")
    with case_csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 7 or [round(float(row["offset_mm"]), 3) for row in rows] != [-0.012, 0.008, 0.012, 0.018, 0.022, 0.032, 0.042]:
        raise ValueError("Day 68 seven-point recovery list changed.")
    return rows


def validate_recipe_model_control(config, historical):
    source = config["source"]
    config_path = frozen_path(config, "day25_config", "day25_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    day25 = load_config(source["day25_config"])
    contract = config["approved_execution_contract"]
    checks = (
        day25["analysis"]["standard_spot"]["reference"] == "centroid",
        [float(value) for value in day25["analysis"]["fft_mtf"]["evaluation_frequencies_cyc_per_mm"]] == [30.0, 50.0],
        historical.get("case", {}).get("case_id") == "boundary_control_000",
        math.isclose(float(historical["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        historical.get("balanced_acceptance_pass") is True,
        historical.get("connection_closed") is True,
        historical.get("input_model_unchanged") is True,
        historical.get("working_copy_unchanged") is True,
        historical.get("quick_focus_used") is False,
        historical.get("optimization_used") is False,
        historical.get("save_as_used") is False,
        math.isclose(float(contract["target_image_distance_mm"]), float(day25["reference_state"]["focused_image_distance_mm"]), abs_tol=1e-12),
    )
    if not all(checks):
        raise ValueError("Day 69 model, recipe or historical control is invalid.")
    return config_path, model_path, day25


def validate_contract_and_permissions(config):
    contract = config["approved_execution_contract"]
    checks = (
        contract["recovery_stage"] == "stage_01_zero_control",
        int(contract["day"]) == 27,
        contract["execution_class"] == "uses_zosapi",
        contract["approved_case_id"] == "recovery_control_000",
        math.isclose(float(contract["approved_offset_mm"]), 0.0, abs_tol=1e-12),
        int(contract["maximum_execution_count"]) == 1,
        int(contract["maximum_active_zosapi_connections"]) == 1,
        int(contract["maximum_working_copy_count"]) == 1,
        contract["required_entrypoint"] == "scripts/demos/day70_execute_approved_recovery_baseline_control.py",
        contract["allow_standard_spot"] is True,
        contract["allow_fft_mtf"] is True,
        contract["allow_quick_focus"] is False,
        contract["allow_optimization"] is False,
        contract["allow_save_as"] is False,
        contract["allow_seven_recovery_cases"] is False,
        contract["require_stop_after_execution"] is True,
    )
    if not all(checks):
        raise ValueError("Day 69 control contract is unsafe.")
    released = {"recovery_zero_control_execution_released", "one_zosapi_connection_released", "one_working_copy_released", "spot_and_mtf_analysis_released"}
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 69 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 69 released a forbidden permission.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract_and_permissions(config)
    plan_path, day68 = load_json(config, "day68_plan", "day68_plan_sha256", "expected_day68_task")
    case_csv_path = frozen_path(config, "recovery_case_csv", "recovery_case_csv_sha256")
    historical_path, historical = load_json(config, "historical_zero_control", "historical_zero_control_sha256", "expected_zero_control_task")
    cases = validate_day68(config, day68, case_csv_path)
    day25_path, model_path, day25 = validate_recipe_model_control(config, historical)
    return {
        "plan_path": plan_path,
        "day68": day68,
        "case_csv_path": case_csv_path,
        "historical_path": historical_path,
        "cases": cases,
        "day25_path": day25_path,
        "model_path": model_path,
        "day25": day25,
        "contract": config["approved_execution_contract"],
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
    config = load_config("configs/day69_day27_recovery_baseline_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["contract"]
    print_introduction(config)
    print("========== DAY 69 DAY27 RECOVERY BASELINE APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, ZOS-API connection, model copy or optical analysis will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Approved scope: recovery stage 01 / zero offset / one execution")
    print(f"Control offset/image distance: {contract['approved_offset_mm']:+.3f} mm / {contract['target_image_distance_mm']:.10f} mm")
    print(f"Focused model: {plan['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {(PROJECT_ROOT / contract['approved_output_root']).resolve()}")
    print("Seven-point recovery batch released: False")
    print("Day27 recalculation released: False")
    print("Slot 6 released: False")
    print()
    print("[PASS] Frozen Day68 plan and seven-point case list verified")
    print("[PASS] Focused model, Day25 Spot/FFT MTF recipe and historical control verified")
    print("[PASS] Approval is limited to one zero-offset recovery control")
    print("[PASS] One working copy and one Standalone connection are the maximum")
    print("[PASS] Seven recovery points, Quick Focus, optimization and SaveAs remain locked")
    print("[PASS] Day69 itself creates no connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
