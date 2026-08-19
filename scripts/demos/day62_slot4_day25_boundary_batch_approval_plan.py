"""Day 62 step 1: validate minimal approval for the Day 25 boundary batch."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day25_balanced_acceptance_boundary_scan_plan import (  # noqa: E402
    validate_new_offsets,
)
from scripts.demos.day25_run_boundary_scan import build_cases  # noqa: E402
from scripts.demos.day25_validate_baseline_control import validate_analysis_recipe  # noqa: E402


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
        raise ValueError(f"Frozen Day 62 evidence changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 62 metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 62 execution switch must be Boolean.")
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 62 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 62 enabled execution or source modification.")


def validate_day61_gate(config, review):
    checks = (
        review.get("decision_status") == config["source"]["expected_day61_status"],
        review.get("cp09_review", {}).get("task_review_status") == "PASS",
        review.get("cp09_review", {}).get("balanced_acceptance_pass") is True,
        review.get("permissions", {}).get("slot_04_baseline_review_completed") is True,
        review.get("permissions", {}).get("boundary_batch_release_request_eligible") is True,
        review.get("permissions", {}).get("boundary_batch_execution_released") is False,
        review.get("boundary_cases_executed") is False,
        review.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 61 is not eligible for boundary-batch approval.")


def validate_day60_result(result):
    checks = (
        result.get("case", {}).get("case_id") == "boundary_control_000",
        math.isclose(float(result["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        result.get("approval", {}).get("consumed_once") is True,
        result.get("balanced_acceptance_pass") is True,
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("nine_boundary_cases_executed") is False,
    )
    if not all(checks):
        raise ValueError("Day 60 control evidence is incomplete or unsafe.")


def validate_inputs_and_cases(config, historical):
    source = config["source"]
    day25_path = (PROJECT_ROOT / source["day25_config"]).resolve()
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    if not day25_path.is_file() or sha256_file(day25_path) != source["day25_config_sha256"]:
        raise ValueError("Day 25 config changed before Day 62 approval.")
    if not model_path.is_file() or sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("Focused model changed before Day 62 approval.")
    day25 = load_config(source["day25_config"])
    validate_analysis_recipe(day25)
    negative, positive = validate_new_offsets(day25)
    cases = build_cases(day25, negative, positive)
    contract = config["approved_execution_contract"]
    case_ids = [case["case_id"] for case in cases]
    offsets = [float(case["offset_mm"]) for case in cases]
    checks = (
        case_ids == contract["approved_case_ids"],
        offsets == [float(value) for value in contract["approved_offsets_mm"]],
        historical.get("case_count") == 9,
        [row["case_id"] for row in historical.get("rows", [])] == case_ids,
        [float(row["offset_mm"]) for row in historical.get("rows", [])] == offsets,
        historical.get("quick_focus_used") is False,
        historical.get("optimization_used") is False,
        historical.get("save_as_used") is False,
        historical.get("interpolation_used") is False,
        historical.get("continuous_tolerance_claimed") is False,
    )
    if not all(checks):
        raise ValueError("Day 25 cases or historical batch evidence changed.")
    return day25_path, model_path, cases


def validate_contract(config):
    contract = config["approved_execution_contract"]
    checks = (
        int(contract["resource_slot"]) == 4,
        int(contract["day"]) == 25,
        contract["execution_class"] == "uses_zosapi",
        int(contract["maximum_batch_execution_count"]) == 1,
        int(contract["maximum_case_execution_count"]) == 9,
        len(set(contract["approved_case_ids"])) == 9,
        len(set(float(value) for value in contract["approved_offsets_mm"])) == 9,
        contract["required_entrypoint"] == "scripts/demos/day63_execute_approved_day25_boundary_batch.py",
        contract["run_sequentially"] is True,
        int(contract["maximum_active_zosapi_connections"]) == 1,
        contract["use_independent_working_copy_per_case"] is True,
        contract["allow_standard_spot"] is True,
        contract["allow_fft_mtf"] is True,
        contract["allow_quick_focus"] is False,
        contract["allow_optimization"] is False,
        contract["allow_save_as"] is False,
        contract["allow_baseline_rerun"] is False,
        contract["stop_on_first_unexpected_failure"] is True,
        contract["acceptance_failure_stops_batch"] is False,
        contract["require_historical_reproduction"] is True,
        contract["require_stop_after_batch"] is True,
        contract["post_execution_gate"] == "CP09_slot_gate",
    )
    if not all(checks):
        raise ValueError("Day 62 boundary-batch contract is unsafe.")
    released = {
        "boundary_batch_execution_released",
        "sequential_zosapi_execution_released",
        "independent_working_copies_released",
        "spot_and_mtf_analysis_released",
        "balanced_acceptance_evaluation_released",
    }
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 62 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 62 released a forbidden permission.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    review_path, review = load_frozen_json(
        config, "day61_review_record", "day61_review_sha256", "expected_day61_task"
    )
    result_path, result = load_frozen_json(
        config, "day60_result", "day60_result_sha256", "expected_day60_task"
    )
    historical_path, historical = load_frozen_json(
        config,
        "historical_boundary_batch",
        "historical_boundary_batch_sha256",
        "expected_historical_task",
    )
    validate_day61_gate(config, review)
    validate_day60_result(result)
    day25_path, model_path, cases = validate_inputs_and_cases(config, historical)
    contract = dict(config["approved_execution_contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_day61_review": str(review_path),
        "source_day60_result": str(result_path),
        "historical_boundary_batch": str(historical_path),
        "day25_config": str(day25_path),
        "focused_model": str(model_path),
        "cases": cases,
        "execution_contract": contract,
        "approved_capabilities": list(config["decision"]["approved_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
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
    config = load_config("configs/day62_slot4_day25_boundary_batch_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["execution_contract"]
    print_introduction(config)
    print("========== DAY 62 SLOT-4 BOUNDARY-BATCH APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, ZOS-API connection, model copy or optical analysis will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Approved scope: Slot 4 / Day 25 / nine nonzero boundary cases / one batch")
    for case in plan["cases"]:
        print(f"  {case['case_id']}: offset={float(case['offset_mm']):+.3f} mm")
    print(f"Focused model: {plan['focused_model']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {contract['approved_output_root']}")
    print("Batch rules: sequential; one active Standalone connection; stop on unexpected failure")
    print("Acceptance FAIL is recorded and does not stop the batch.")
    print("Still forbidden: control rerun, Quick Focus, optimization, SaveAs and Slot 5-6")
    print()
    print("[PASS] Frozen Day61 CP09 review and Day60 control result verified")
    print("[PASS] Day25 config, focused model and historical nine-case evidence verified")
    print("[PASS] Exactly nine nonzero boundary cases and their order frozen")
    print("[PASS] One independent working copy and connection lifecycle required per case")
    print("[PASS] Optical acceptance is recorded; only unexpected execution failures stop the batch")
    print("[PASS] Day62 itself creates no ZOS-API connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
