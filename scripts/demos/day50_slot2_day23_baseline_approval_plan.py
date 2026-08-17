"""Day 50 step 1: plan a minimal ZOS-API approval for Day 23 baseline control."""

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
    """Permit approval work only; Day 50 itself cannot connect or execute."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 50 execution switch must be Boolean.")
    allowed_true = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 50 approval evaluation and reporting must be allowed.")
    if any(value is not False for key, value in execution.items() if key not in allowed_true):
        raise ValueError("Day 50 enabled a ZOS-API or execution capability.")


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    """Load one frozen JSON source and verify its task/status."""

    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 50 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"The Day 50 source metadata is incorrect: {path_key}")
    return path, report


def validate_day49_gate(config, review):
    """Require Slot 1 CP09 PASS and eligibility to request Slot 2 only."""

    source = config["source"]
    checks = (
        review.get("decision_status") == source["expected_day49_status"],
        review.get("cp09_review", {}).get("task_review_status") == "PASS",
        review.get("permissions", {}).get("slot_02_release_request_eligible") is True,
        review.get("permissions", {}).get("slot_02_execution_released") is False,
        review.get("decision", {}).get("slot_02_release_approved") is False,
        review.get("slot1_rerun_performed") is False,
        review.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("The Day 49 CP09 record is not eligible for Day 50 approval.")


def validate_slot2(config, schedule):
    """Require Slot 2 to contain only the single-channel Day 23 task."""

    slot = next((row for row in schedule["slots"] if int(row["slot"]) == 2), None)
    if not slot:
        raise ValueError("The Day 42 schedule has no Slot 2.")
    checks = (
        slot["days"] == [23],
        slot["uses_zosapi_days"] == [23],
        slot["offline_only_days"] == [],
        slot["manual_approval_required"] is True,
        slot["execution_released"] is False,
        slot["automatic_execution"] is False,
    )
    if not all(checks):
        raise ValueError("The Day 42 Slot 2 definition changed.")
    return slot


def validate_day48_change_evidence(config, result):
    """Verify the new Day 22 evidence and its 0.012 mm allowance set."""

    expected = config["change_specific_evidence"]
    allowances = sorted(
        {float(row["symmetric_allowance_mm"]) for row in result["teaching_error_sources"]}
    )
    expected_allowances = sorted(float(value) for value in expected["expected_component_allowances_mm"])
    positioning = next(
        row for row in result["teaching_error_sources"] if row["id"] == "positioning_accuracy"
    )
    checks = (
        math.isclose(
            float(positioning["symmetric_allowance_mm"]),
            float(expected["positioning_accuracy_mm"]),
            abs_tol=1e-12,
        ),
        allowances == expected_allowances,
        len(result["combination_policies"]) == int(expected["expected_day22_policy_count"]),
        all(
            int(row["sampled_case_count"]) == int(expected["expected_day22_case_count"])
            for row in result["summaries"]
        ),
        result.get("slot1_execution_completed") is True,
        result.get("new_zosapi_connection_created") is False,
        result.get("new_optical_metric_calculated") is False,
        result.get("engineering_recommendation") is None,
    )
    if not all(checks):
        raise ValueError("The Day 48 change-specific evidence is incomplete.")


def validate_optical_inputs(config, previous_control):
    """Freeze the Day 23 config, focused model and historical control evidence."""

    source = config["source"]
    config_path = (PROJECT_ROOT / source["day23_config"]).resolve()
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    if not config_path.is_file() or sha256_file(config_path) != source["day23_config_sha256"]:
        raise ValueError("The Day 23 config changed before Day 50 approval.")
    if not model_path.is_file() or sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("The focused Day 23 model changed before Day 50 approval.")
    checks = (
        previous_control.get("case", {}).get("case_id") == "defocus_004",
        math.isclose(float(previous_control["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        previous_control.get("connection_closed") is True,
        previous_control.get("input_model_unchanged") is True,
        previous_control.get("working_copy_unchanged") is True,
        previous_control.get("quick_focus_used") is False,
        previous_control.get("optimization_used") is False,
        previous_control.get("save_as_used") is False,
    )
    if not all(checks):
        raise ValueError("The previous Day 23 baseline control is not safe reference evidence.")
    return config_path, model_path


def validate_contract_and_decision(config):
    """Release only one zero-defocus control and keep the six residual cases locked."""

    contract = config["approved_execution_contract"]
    contract_checks = (
        int(contract["resource_slot"]) == 2,
        int(contract["day"]) == 23,
        contract["execution_class"] == "uses_zosapi",
        int(contract["maximum_execution_count"]) == 1,
        contract["approved_case_id"] == "defocus_004",
        math.isclose(float(contract["approved_offset_mm"]), 0.0, abs_tol=1e-12),
        contract["required_entrypoint"] == "scripts/demos/day51_execute_approved_day23_baseline_control.py",
        str(contract["approved_output_root"]).startswith("outputs/"),
        contract["allow_single_standalone_connection"] is True,
        contract["allow_standard_spot"] is True,
        contract["allow_fft_mtf"] is True,
        contract["allow_quick_focus"] is False,
        contract["allow_optimization"] is False,
        contract["allow_save_as"] is False,
        contract["allow_residual_cases"] is False,
        contract["require_stop_after_baseline_control"] is True,
    )
    if not all(contract_checks):
        raise ValueError("The Day 50 baseline execution contract is unsafe.")
    if config["decision"]["decision_status"] != "SLOT_02_APPROVED_FOR_DAY23_BASELINE_CONTROL_EXECUTION":
        raise ValueError("The Day 50 decision status is incorrect.")
    permissions = config["permissions"]
    true_permissions = {
        "day23_baseline_control_execution_released",
        "single_zosapi_connection_released",
        "isolated_working_copy_released",
        "spot_and_mtf_analysis_released",
    }
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("The Day 50 baseline permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 50 released a forbidden optical or downstream capability.")


def build_plan(config, review_path, result_path, schedule_path, day23_config_path, model_path, control_path, slot2):
    """Build the baseline-control approval plan without connecting to Zemax."""

    contract = dict(config["approved_execution_contract"])
    contract["approved_output_root"] = str(
        (PROJECT_ROOT / contract["approved_output_root"]).resolve()
    )
    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_day49_review": str(review_path),
        "source_day48_result": str(result_path),
        "source_day42_schedule": str(schedule_path),
        "day23_config": str(day23_config_path),
        "focused_model": str(model_path),
        "focused_model_sha256": config["source"]["focused_model_sha256"],
        "previous_control": str(control_path),
        "slot_definition": slot2,
        "execution_contract": contract,
        "approved_capabilities": list(config["decision"]["approved_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
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
    config = load_config("configs/day50_slot2_day23_baseline_approval.yaml")
    validate_execution_lock(config)
    validate_contract_and_decision(config)
    review_path, review = load_frozen_json(
        config, "day49_review_record", "day49_review_sha256", "expected_day49_task"
    )
    result_path, result = load_frozen_json(
        config, "day48_result", "day48_result_sha256", "expected_day48_task"
    )
    schedule_path, schedule = load_frozen_json(
        config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task"
    )
    control_path, previous_control = load_frozen_json(
        config, "previous_day23_control", "previous_day23_control_sha256", "expected_previous_control_task"
    )
    validate_day49_gate(config, review)
    slot2 = validate_slot2(config, schedule)
    validate_day48_change_evidence(config, result)
    day23_config_path, model_path = validate_optical_inputs(config, previous_control)
    plan = build_plan(
        config, review_path, result_path, schedule_path, day23_config_path,
        model_path, control_path, slot2,
    )

    print_introduction(config)
    print("========== DAY 50 SLOT-2 DAY23 BASELINE APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, ZOS-API connection, model copy or optical analysis will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Approved scope: Slot 2 / Day 23 / defocus_004 only / one execution")
    print(f"Focused model: {plan['focused_model']}")
    print(f"Focused model SHA256: {plan['focused_model_sha256']}")
    print("Change-specific Day22 positioning accuracy: +/-0.012 mm")
    print(f"Required entrypoint: {plan['execution_contract']['required_entrypoint']}")
    print(f"Approved output root: {plan['execution_contract']['approved_output_root']}")
    print("Approved capabilities:")
    for capability in plan["approved_capabilities"]:
        print(f"  - {capability}")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day49 CP09 review, Day48 evidence and Day42 Slot 2 verified")
    print("[PASS] Day23 config, focused model and previous baseline control verified")
    print("[PASS] New 0.012 mm evidence is explicit and does not change the optical model")
    print("[PASS] Approval is limited to one zero-defocus baseline control")
    print("[PASS] Six residual cases, Quick Focus, optimization and SaveAs remain locked")
    print("[PASS] Day50 itself creates no ZOS-API connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
