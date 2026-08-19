"""Day 59 step 1: validate the minimal Slot 4 Day 25 control approval."""

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


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"Frozen Day 59 evidence changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 59 source metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 59 execution switch must be Boolean.")
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 59 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 59 enabled execution or source modification.")


def validate_day58_gate(config, review):
    checks = (
        review.get("decision_status") == config["source"]["expected_day58_status"],
        review.get("cp09_review", {}).get("task_review_status") == "PASS",
        review.get("permissions", {}).get("slot_03_acceptance_review_completed") is True,
        review.get("permissions", {}).get("slot_04_release_request_eligible") is True,
        review.get("permissions", {}).get("slot_04_execution_released") is False,
        review.get("new_zosapi_connection_created") is False,
        review.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 58 is not eligible for Slot 4 approval.")


def validate_day25_and_control(config, historical):
    source = config["source"]
    config_path = (PROJECT_ROOT / source["day25_config"]).resolve()
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    if sha256_file(config_path) != source["day25_config_sha256"]:
        raise ValueError("Day 25 config changed before Day 59 approval.")
    if sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("Focused model changed before Day 59 approval.")
    day25 = load_config(source["day25_config"])
    contract = config["approved_execution_contract"]
    checks = (
        day25["balanced_acceptance"]["combination_rule"] == "all_required_metrics_must_pass",
        math.isclose(float(day25["boundary_scan"]["baseline_control_offset_mm"]), 0.0, abs_tol=1e-12),
        int(day25["boundary_scan"]["new_case_count"]) == 9,
        historical.get("case", {}).get("case_id") == contract["approved_case_id"],
        math.isclose(float(historical["case"]["offset_mm"]), float(contract["approved_offset_mm"]), abs_tol=1e-12),
        historical.get("connection_closed") is True,
        historical.get("input_model_unchanged") is True,
        historical.get("working_copy_unchanged") is True,
        historical.get("quick_focus_used") is False,
        historical.get("optimization_used") is False,
        historical.get("save_as_used") is False,
    )
    if not all(checks):
        raise ValueError("Day 25 control recipe or historical safety evidence is invalid.")
    return config_path, model_path, day25


def validate_schedule(schedule):
    matching_slots = [
        slot
        for slot in schedule.get("slots", [])
        if int(slot.get("slot", -1)) == 4
    ]
    if len(matching_slots) != 1:
        raise ValueError("Day 42 Slot 4 is missing or duplicated.")
    slot = matching_slots[0]
    checks = (
        slot.get("days") == [25],
        slot.get("uses_zosapi_days") == [25],
        slot.get("offline_only_days") == [],
        slot.get("manual_approval_required") is True,
        slot.get("execution_released") is False,
        slot.get("automatic_execution") is False,
    )
    if not all(checks):
        raise ValueError("Day 42 does not place Day 25 in Slot 4.")


def validate_contract(config):
    c = config["approved_execution_contract"]
    checks = (
        int(c["resource_slot"]) == 4,
        int(c["day"]) == 25,
        c["execution_class"] == "uses_zosapi",
        c["approved_case_id"] == "boundary_control_000",
        math.isclose(float(c["approved_offset_mm"]), 0.0, abs_tol=1e-12),
        int(c["maximum_execution_count"]) == 1,
        int(c["maximum_active_zosapi_connections"]) == 1,
        int(c["maximum_working_copy_count"]) == 1,
        c["required_entrypoint"] == "scripts/demos/day60_execute_approved_day25_baseline_control.py",
        c["allow_standard_spot"] is True,
        c["allow_fft_mtf"] is True,
        c["allow_quick_focus"] is False,
        c["allow_optimization"] is False,
        c["allow_save_as"] is False,
        c["allow_nine_boundary_cases"] is False,
        c["require_historical_reproduction"] is True,
        c["require_balanced_acceptance_pass"] is True,
        c["require_stop_after_execution"] is True,
    )
    if not all(checks):
        raise ValueError("Day 59 Slot 4 control contract is unsafe.")
    permissions = config["permissions"]
    released = {"slot_04_zero_control_execution_released", "one_zosapi_connection_released", "one_working_copy_released", "spot_and_mtf_analysis_released"}
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 59 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 59 released a forbidden permission.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    review_path, review = load_frozen_json(config, "day58_review", "day58_review_sha256", "expected_day58_task")
    historical_path, historical = load_frozen_json(config, "historical_baseline_control", "historical_baseline_control_sha256", "expected_historical_task")
    schedule_path, schedule = load_frozen_json(config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task")
    validate_day58_gate(config, review)
    validate_schedule(schedule)
    day25_path, model_path, day25 = validate_day25_and_control(config, historical)
    return {
        "review_path": review_path,
        "historical_path": historical_path,
        "schedule_path": schedule_path,
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
    config = load_config("configs/day59_slot4_day25_baseline_approval.yaml")
    plan = prepare_plan(config)
    c = plan["contract"]
    limits = plan["day25"]["balanced_acceptance"]["limits"]
    print_introduction(config)
    print("========== DAY 59 SLOT-4 DAY25 BASELINE APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, ZOS-API connection, model copy or optical analysis will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Approved scope: Slot 4 / Day 25 / boundary_control_000 / one execution")
    print(f"Control offset: {float(c['approved_offset_mm']):+.3f} mm")
    print(f"Focused model: {plan['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Balanced thresholds: Spot mean<={limits['spot_mean_rms_um_max']:.3f}, worst<={limits['spot_worst_rms_um_max']:.3f} um, MTF30 min>={limits['mtf30_minimum_min']:.3f}, MTF50 min>={limits['mtf50_minimum_min']:.3f}")
    print(f"Required entrypoint: {c['required_entrypoint']}")
    print(f"Approved output root: {(PROJECT_ROOT / c['approved_output_root']).resolve()}")
    print("Nine boundary cases released: False")
    print("Slot 5-6 released: False")
    print()
    print("[PASS] Frozen Day58 CP09 review and Day42 Slot 4 verified")
    print("[PASS] Day25 config, focused model and historical control fingerprints verified")
    print("[PASS] Approval is limited to one zero-offset Spot/FFT MTF control")
    print("[PASS] One working copy and one Standalone connection are the maximum")
    print("[PASS] Nine boundary cases, Quick Focus, optimization and SaveAs remain locked")
    print("[PASS] Day59 itself creates no connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
