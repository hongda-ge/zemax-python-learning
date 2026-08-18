"""Day 53 step 1: validate a minimal approval for the Day 23 residual batch."""

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
        raise ValueError(f"Frozen Day 53 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 53 source metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 53 execution switch must be Boolean.")
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 53 approval work must be enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 53 enabled execution or source modification.")


def validate_day52_gate(config, review):
    checks = (
        review.get("decision_status") == config["source"]["expected_day52_status"],
        review.get("cp09_review", {}).get("task_review_status") == "PASS",
        review.get("permissions", {}).get("slot_02_baseline_review_completed") is True,
        review.get("permissions", {}).get("residual_batch_release_request_eligible") is True,
        review.get("permissions", {}).get("residual_case_execution_released") is False,
        review.get("permissions", {}).get("zosapi_execution_released") is False,
        review.get("residual_cases_executed") is False,
        review.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 52 is not eligible for residual-batch approval.")


def validate_day51_result(result):
    checks = (
        result.get("case", {}).get("case_id") == "defocus_004",
        math.isclose(float(result["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        result.get("approval", {}).get("consumed_once") is True,
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("residual_cases_executed") is False,
    )
    if not all(checks):
        raise ValueError("Day 51 baseline evidence is incomplete or unsafe.")


def validate_inputs_and_cases(config, historical):
    source = config["source"]
    day23_path = (PROJECT_ROOT / source["day23_config"]).resolve()
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    if sha256_file(day23_path) != source["day23_config_sha256"]:
        raise ValueError("Day 23 config changed before Day 53 approval.")
    if sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("Focused model changed before Day 53 approval.")
    day23 = load_config(source["day23_config"])
    offsets = [float(value) for value in day23["residual_defocus"]["offsets_mm"] if not math.isclose(float(value), 0.0, abs_tol=1e-12)]
    contract = config["approved_execution_contract"]
    if offsets != [float(value) for value in contract["approved_offsets_mm"]]:
        raise ValueError("Approved offsets do not match the six Day 23 nonzero cases.")
    if historical.get("case_count") != 6 or [row["case_id"] for row in historical["rows"]] != contract["approved_case_ids"]:
        raise ValueError("Historical six-case evidence does not match the approved identities.")
    if historical.get("quick_focus_used") or historical.get("optimization_used") or historical.get("save_as_used"):
        raise ValueError("Historical residual-batch safety evidence is invalid.")
    return day23_path, model_path


def validate_contract(config):
    contract = config["approved_execution_contract"]
    checks = (
        int(contract["resource_slot"]) == 2,
        int(contract["day"]) == 23,
        int(contract["maximum_batch_execution_count"]) == 1,
        int(contract["maximum_case_execution_count"]) == 6,
        len(set(contract["approved_case_ids"])) == 6,
        contract["required_entrypoint"] == "scripts/demos/day54_execute_approved_day23_residual_batch.py",
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
        contract["require_stop_after_batch"] is True,
    )
    if not all(checks):
        raise ValueError("Day 53 residual-batch contract is unsafe.")
    permissions = config["permissions"]
    released = {"residual_batch_execution_released", "sequential_zosapi_execution_released", "independent_working_copies_released", "spot_and_mtf_analysis_released"}
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 53 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 53 released a forbidden permission.")


def build_plan(config, review_path, result_path, historical_path, day23_path, model_path):
    contract = dict(config["approved_execution_contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "source_day52_review": str(review_path),
        "source_day51_result": str(result_path),
        "historical_residual_batch": str(historical_path),
        "day23_config": str(day23_path),
        "focused_model": str(model_path),
        "execution_contract": contract,
        "approved_capabilities": list(config["decision"]["approved_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
    }


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    review_path, review = load_frozen_json(config, "day52_review_record", "day52_review_sha256", "expected_day52_task")
    result_path, result = load_frozen_json(config, "day51_result", "day51_result_sha256", "expected_day51_task")
    historical_path, historical = load_frozen_json(config, "historical_residual_batch", "historical_residual_batch_sha256", "expected_historical_task")
    validate_day52_gate(config, review)
    validate_day51_result(result)
    day23_path, model_path = validate_inputs_and_cases(config, historical)
    return build_plan(config, review_path, result_path, historical_path, day23_path, model_path)


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
    config = load_config("configs/day53_slot2_residual_batch_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["execution_contract"]
    print_introduction(config)
    print("========== DAY 53 SLOT-2 RESIDUAL-BATCH APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, ZOS-API connection, model copy or optical analysis will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Approved scope: Slot 2 / Day 23 / six nonzero residual cases / one batch")
    for case_id, offset in zip(contract["approved_case_ids"], contract["approved_offsets_mm"]):
        print(f"  {case_id}: offset={float(offset):+.3f} mm")
    print(f"Focused model: {plan['focused_model']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {contract['approved_output_root']}")
    print("Batch rules: sequential; one active Standalone connection; stop on unexpected failure")
    print("Still forbidden: baseline rerun, Quick Focus, optimization, SaveAs and Slot 3-6")
    print()
    print("[PASS] Frozen Day52 CP09 review and Day51 baseline result verified")
    print("[PASS] Day23 config, focused model and historical six-case evidence verified")
    print("[PASS] Exactly six nonzero residual cases and their order frozen")
    print("[PASS] One independent working copy and connection lifecycle required per case")
    print("[PASS] Optical performance is recorded; only unexpected execution failures stop the batch")
    print("[PASS] Day53 itself creates no ZOS-API connection or optical result")
    print("PLAN ONLY finished. No output, connection or source modification was created.")


if __name__ == "__main__":
    main()
