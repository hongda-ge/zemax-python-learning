"""Day 63 step 1: plan the approved nine-case boundary execution."""

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


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 63 input changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 63 metadata is invalid: {path_key}")
    return path, report


def validate_execution_contract(config):
    execution = config["execution"]
    true_keys = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_boundary_cases",
        "allow_balanced_acceptance_evaluation",
    )
    false_keys = (
        "allow_baseline_control",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_source_modification",
        "allow_downstream_release",
    )
    checks = (
        all(execution[key] is True for key in true_keys),
        all(execution[key] is False for key in false_keys),
        int(execution["approved_resource_slot"]) == 4,
        int(execution["maximum_batch_execution_count"]) == 1,
        int(execution["maximum_case_execution_count"]) == 9,
        int(execution["maximum_active_zosapi_connections"]) == 1,
    )
    if not all(checks):
        raise ValueError("Day 63 execution permissions are unsafe.")


def validate_approval(config, approval):
    batch = config["approved_batch"]
    contract = approval["execution_contract"]
    expected_root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    checks = (
        approval.get("decision_status") == config["source"]["expected_day62_status"],
        approval.get("approved_scope", {}).get("resource_slot") == 4,
        approval.get("approved_scope", {}).get("case_ids") == batch["case_ids"],
        [float(value) for value in approval.get("approved_scope", {}).get("offsets_mm", [])]
        == [float(value) for value in batch["offsets_mm"]],
        approval.get("approved_scope", {}).get("maximum_batch_execution_count") == 1,
        approval.get("approved_scope", {}).get("maximum_case_execution_count") == 9,
        contract.get("required_entrypoint") == config["guardrails"]["required_entrypoint"],
        Path(contract.get("approved_output_root", "")).resolve() == expected_root,
        contract.get("run_sequentially") is True,
        contract.get("maximum_active_zosapi_connections") == 1,
        contract.get("use_independent_working_copy_per_case") is True,
        contract.get("allow_quick_focus") is False,
        contract.get("allow_optimization") is False,
        contract.get("allow_save_as") is False,
        contract.get("allow_baseline_rerun") is False,
        contract.get("stop_on_first_unexpected_failure") is True,
        contract.get("acceptance_failure_stops_batch") is False,
        contract.get("require_historical_reproduction") is True,
        contract.get("post_execution_gate") == config["guardrails"]["post_execution_gate"],
        approval.get("permissions", {}).get("boundary_batch_execution_released") is True,
        approval.get("approved_batch_executed_by_day62") is False,
        approval.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 62 approval does not authorize the Day 63 contract.")


def validate_control(result, config):
    checks = (
        result.get("case", {}).get("case_id") == "boundary_control_000",
        math.isclose(float(result["case"]["offset_mm"]), 0.0, abs_tol=1e-12),
        result.get("slot4_baseline_control_completed") is True,
        result.get("approval", {}).get("consumed_once") is True,
        result.get("balanced_acceptance_pass") is True,
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("nine_boundary_cases_executed") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("input_sha256_before") == config["source"]["focused_model_sha256"],
    )
    if not all(checks):
        raise ValueError("Day 60 control result is incomplete or unsafe.")


def validate_cases(config, day25, historical):
    negative, positive = validate_new_offsets(day25)
    cases = build_cases(day25, negative, positive)
    batch = config["approved_batch"]
    case_ids = [case["case_id"] for case in cases]
    offsets = [float(case["offset_mm"]) for case in cases]
    checks = (
        case_ids == batch["case_ids"],
        offsets == [float(value) for value in batch["offsets_mm"]],
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
        raise ValueError("Day 63 cases differ from the approved historical batch.")
    return cases


def ensure_approval_not_consumed(config):
    root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    marker = root / config["output"]["authorization_consumption_name"]
    results = list(root.glob(f"**/{config['output']['batch_result_name']}")) if root.exists() else []
    if marker.exists() or results:
        found = marker if marker.exists() else results[0]
        raise ValueError(f"The Day 62 one-time approval was already consumed: {found}")
    return root, marker


def collect_inputs(config):
    validate_execution_contract(config)
    approval_path, approval = load_frozen_json(
        config, "day62_approval", "day62_approval_sha256", "expected_day62_task"
    )
    control_path, control = load_frozen_json(
        config, "day60_control_result", "day60_control_sha256", "expected_day60_task"
    )
    historical_path, historical = load_frozen_json(
        config,
        "historical_boundary_batch",
        "historical_boundary_batch_sha256",
        "expected_historical_task",
    )
    day25_path = frozen_path(config, "day25_config", "day25_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    validate_approval(config, approval)
    validate_control(control, config)
    day25 = load_config(config["source"]["day25_config"])
    validate_analysis_recipe(day25)
    cases = validate_cases(config, day25, historical)
    output_root, marker = ensure_approval_not_consumed(config)
    return {
        "approval_path": approval_path,
        "approval": approval,
        "control_path": control_path,
        "control": control,
        "historical_path": historical_path,
        "historical": historical,
        "day25_path": day25_path,
        "day25": day25,
        "model_path": model_path,
        "cases": cases,
        "output_root": output_root,
        "marker": marker,
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
    config = load_config("configs/day63_approved_day25_boundary_batch.yaml")
    inputs = collect_inputs(config)
    print_introduction(config)
    print("========== DAY 63 APPROVED BOUNDARY-BATCH PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No authorization will be consumed and no ZOS-API connection will occur in this step.")
    print("Approved scope: Slot 4 / Day 25 / nine nonzero cases / one batch")
    print(f"Day62 approval: {inputs['approval_path']}")
    print(f"Focused model: {inputs['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    for case in inputs["cases"]:
        print(f"  {case['case_id']}: offset={float(case['offset_mm']):+.3f} mm, target image distance={float(case['target_image_distance_mm']):.10f} mm")
    print("Planned analyses: nine Standard Spot + nine FFT MTF exports")
    print("Planned connections/copies: nine sequential lifecycles / nine independent copies")
    print(f"Authorization marker: {inputs['marker']}")
    print(f"Isolated output root: {inputs['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day62 approval and one-time batch contract verified")
    print("[PASS] Day60 zero-offset control verified and excluded from the batch")
    print("[PASS] Nine approved identities, offsets and historical evidence verified")
    print("[PASS] No prior marker or result has consumed this approval")
    print("[PASS] Quick Focus, optimization, SaveAs and Slot 5-6 remain locked")
    print("PLAN ONLY finished. No output, authorization consumption or optical calculation was created.")


if __name__ == "__main__":
    main()
