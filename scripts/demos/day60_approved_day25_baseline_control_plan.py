"""Day 60 step 1: plan the approved Day 25 zero-offset control."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day25_validate_baseline_control import (  # noqa: E402
    validate_analysis_recipe,
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 60 input changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 60 metadata is invalid: {path_key}")
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
        "allow_zero_offset_control",
    )
    false_keys = (
        "allow_boundary_cases",
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
        int(execution["maximum_execution_count"]) == 1,
        int(execution["maximum_active_zosapi_connections"]) == 1,
        int(execution["maximum_working_copy_count"]) == 1,
    )
    if not all(checks):
        raise ValueError("Day 60 execution permissions are unsafe.")


def validate_approval(config, approval):
    control = config["approved_control"]
    contract = approval["approved_execution_contract"]
    expected_root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    checks = (
        approval.get("decision_status") == config["source"]["expected_day59_status"],
        approval.get("approved_execution_contract", {}).get("resource_slot") == 4,
        approval.get("approved_execution_contract", {}).get("day") == 25,
        contract.get("approved_case_id") == control["case_id"],
        math.isclose(float(contract["approved_offset_mm"]), float(control["offset_mm"]), abs_tol=1e-12),
        contract.get("maximum_execution_count") == 1,
        contract.get("maximum_active_zosapi_connections") == 1,
        contract.get("maximum_working_copy_count") == 1,
        contract.get("required_entrypoint") == config["guardrails"]["required_entrypoint"],
        Path(contract.get("approved_output_root", "")).resolve() == expected_root,
        contract.get("allow_standard_spot") is True,
        contract.get("allow_fft_mtf") is True,
        contract.get("allow_quick_focus") is False,
        contract.get("allow_optimization") is False,
        contract.get("allow_save_as") is False,
        contract.get("allow_nine_boundary_cases") is False,
        contract.get("require_historical_reproduction") is True,
        contract.get("require_balanced_acceptance_pass") is True,
        contract.get("stop_checkpoint") == config["guardrails"]["post_execution_gate"],
        approval.get("permissions", {}).get("slot_04_zero_control_execution_released") is True,
        approval.get("permissions", {}).get("boundary_batch_execution_released") is False,
        approval.get("approved_task_executed_by_day59") is False,
        approval.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 59 approval does not authorize the Day 60 contract.")


def validate_optical_inputs(config, day25, historical):
    control = config["approved_control"]
    validate_analysis_recipe(day25)
    checks = (
        day25["balanced_acceptance"]["combination_rule"] == "all_required_metrics_must_pass",
        math.isclose(float(day25["boundary_scan"]["baseline_control_offset_mm"]), 0.0, abs_tol=1e-12),
        int(day25["boundary_scan"]["new_case_count"]) == 9,
        historical.get("case", {}).get("case_id") == control["case_id"],
        math.isclose(float(historical["case"]["offset_mm"]), float(control["offset_mm"]), abs_tol=1e-12),
        math.isclose(float(historical["case"]["target_image_distance_mm"]), float(control["expected_image_distance_mm"]), abs_tol=1e-9),
        historical.get("balanced_acceptance_pass") is True,
        historical.get("connection_closed") is True,
        historical.get("input_model_unchanged") is True,
        historical.get("working_copy_unchanged") is True,
        historical.get("quick_focus_used") is False,
        historical.get("optimization_used") is False,
        historical.get("save_as_used") is False,
    )
    if not all(checks):
        raise ValueError("Day 60 historical control or optical recipe is unsafe.")


def ensure_approval_not_consumed(config):
    root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    marker = root / config["output"]["authorization_consumption_name"]
    results = list(root.glob(f"**/{config['output']['result_name']}")) if root.exists() else []
    if marker.exists() or results:
        found = marker if marker.exists() else results[0]
        raise ValueError(f"The Day 59 one-time approval was already consumed: {found}")
    return root, marker


def collect_inputs(config):
    validate_execution_contract(config)
    approval_path, approval = load_frozen_json(
        config, "day59_approval", "day59_approval_sha256", "expected_day59_task"
    )
    historical_path, historical = load_frozen_json(
        config,
        "historical_baseline_control",
        "historical_baseline_control_sha256",
        "expected_historical_task",
    )
    day25_path = frozen_path(config, "day25_config", "day25_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    validate_approval(config, approval)
    day25 = load_config(config["source"]["day25_config"])
    validate_optical_inputs(config, day25, historical)
    output_root, marker = ensure_approval_not_consumed(config)
    control = {
        "case_id": config["approved_control"]["case_id"],
        "offset_mm": float(config["approved_control"]["offset_mm"]),
        "target_image_distance_mm": float(config["approved_control"]["expected_image_distance_mm"]),
        "is_control": True,
    }
    return {
        "approval_path": approval_path,
        "approval": approval,
        "historical_path": historical_path,
        "historical": historical,
        "day25_path": day25_path,
        "day25": day25,
        "model_path": model_path,
        "output_root": output_root,
        "marker": marker,
        "control": control,
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
    config = load_config("configs/day60_approved_day25_baseline_control.yaml")
    inputs = collect_inputs(config)
    control = inputs["control"]
    print_introduction(config)
    print("========== DAY 60 APPROVED DAY25 BASELINE CONTROL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No authorization will be consumed and no ZOS-API connection will occur in this step.")
    print("Approved scope: Slot 4 / Day 25 / boundary_control_000 / one execution")
    print(f"Day59 approval: {inputs['approval_path']}")
    print(f"Focused model: {inputs['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Control offset: {control['offset_mm']:+.3f} mm")
    print(f"Image distance: {control['target_image_distance_mm']:.10f} mm")
    print("Planned analyses: one Standard Spot + one FFT MTF at 30/50 cycles/mm")
    print(f"Authorization marker: {inputs['marker']}")
    print(f"Isolated output root: {inputs['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day59 approval and one-time execution contract verified")
    print("[PASS] Day25 recipe, focused model and historical control verified")
    print("[PASS] Exactly one zero-offset control selected")
    print("[PASS] No prior marker or result has consumed this approval")
    print("[PASS] Nine boundary cases, Quick Focus, optimization and SaveAs remain locked")
    print("PLAN ONLY finished. No output, authorization consumption or optical calculation was created.")


if __name__ == "__main__":
    main()
