"""Day 51 step 1: plan the approved zero-defocus baseline control."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_residual_defocus_optical_impact_plan import (  # noqa: E402
    build_cases,
    validate_analysis_recipes,
    validate_guardrails,
)
from scripts.demos.day23_validate_baseline_control import select_control  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def frozen_path(config, path_key, hash_key):
    """Resolve and fingerprint one frozen input."""

    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Frozen Day 51 input not found: {path}")
    if sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 51 input changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task=None):
    """Load one frozen JSON file after verifying its fingerprint."""

    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != "success":
        raise ValueError(f"Frozen Day 51 evidence is not successful: {path_key}")
    if expected_task and report.get("task") != expected_task:
        raise ValueError(f"Frozen Day 51 task identity changed: {path_key}")
    return path, report


def validate_execution_contract(config):
    """Require exactly one approved baseline task and preserve every lock."""

    execution = config["execution"]
    required_true = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
    )
    if any(execution[key] is not True for key in required_true):
        raise ValueError("The Day 51 baseline execution contract is incomplete.")
    required_false = (
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_residual_cases",
        "allow_source_modification",
        "allow_downstream_release",
    )
    if any(execution[key] is not False for key in required_false):
        raise ValueError("Day 51 released a forbidden capability.")
    if int(execution["approved_resource_slot"]) != 2 or int(execution["maximum_execution_count"]) != 1:
        raise ValueError("Day 51 must consume exactly one Slot 2 execution.")


def validate_approval(config, approval):
    """Bind execution to the exact Day 50 approval and its one-case scope."""

    control = config["approved_control"]
    contract = approval["execution_contract"]
    expected_output_root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    checks = (
        approval.get("decision_status") == config["source"]["expected_day50_status"],
        approval.get("approved_scope", {}).get("resource_slot") == 2,
        approval.get("approved_scope", {}).get("days") == [23],
        approval.get("approved_scope", {}).get("case_ids") == [control["case_id"]],
        approval.get("approved_scope", {}).get("maximum_execution_count") == 1,
        contract.get("required_entrypoint")
        == "scripts/demos/day51_execute_approved_day23_baseline_control.py",
        Path(contract.get("approved_output_root", "")).resolve() == expected_output_root,
        contract.get("approved_case_id") == control["case_id"],
        math.isclose(float(contract["approved_offset_mm"]), float(control["offset_mm"]), abs_tol=1e-12),
        contract.get("allow_single_standalone_connection") is True,
        contract.get("allow_standard_spot") is True,
        contract.get("allow_fft_mtf") is True,
        contract.get("allow_quick_focus") is False,
        contract.get("allow_optimization") is False,
        contract.get("allow_save_as") is False,
        contract.get("allow_residual_cases") is False,
        contract.get("require_stop_after_baseline_control") is True,
        contract.get("post_execution_gate") == config["guardrails"]["post_execution_gate"],
        approval.get("source_day48_change_evidence", {}).get("sha256")
        == config["source"]["day48_change_evidence_sha256"],
        approval.get("day23_optical_inputs", {}).get("config_sha256")
        == config["source"]["day23_config_sha256"],
        approval.get("day23_optical_inputs", {}).get("focused_model_sha256")
        == config["source"]["focused_model_sha256"],
        approval.get("previous_baseline_control", {}).get("sha256")
        == config["source"]["previous_day23_control_sha256"],
        approval.get("approved_task_executed") is False,
        approval.get("residual_cases_released") is False,
        approval.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("The Day 50 approval does not authorize the Day 51 contract.")


def validate_change_evidence(config, evidence):
    """Verify the new 0.012 mm evidence without treating it as an optical input."""

    expected = config["change_specific_evidence"]
    positioning = next(
        row for row in evidence["teaching_error_sources"] if row["id"] == "positioning_accuracy"
    )
    checks = (
        math.isclose(
            float(positioning["symmetric_allowance_mm"]),
            float(expected["positioning_accuracy_mm"]),
            abs_tol=1e-12,
        ),
        len(evidence["combination_policies"]) == int(expected["expected_policy_count"]),
        all(
            int(row["sampled_case_count"]) == int(expected["expected_case_count"])
            for row in evidence["summaries"]
        ),
        evidence.get("new_zosapi_connection_created") is False,
        evidence.get("new_optical_metric_calculated") is False,
        expected["evidence_changes_zemax_model"] is False,
        expected["evidence_changes_analysis_recipe"] is False,
    )
    if not all(checks):
        raise ValueError("The change-specific Day22 evidence is incomplete.")


def validate_optical_evidence(config, day23_config, previous_control):
    """Validate the unchanged optical recipe and select the zero-offset control."""

    validate_analysis_recipes(day23_config)
    validate_guardrails(day23_config)
    control = select_control(build_cases(day23_config))
    expected = config["approved_control"]
    checks = (
        control["case_id"] == expected["case_id"],
        math.isclose(float(control["offset_mm"]), float(expected["offset_mm"]), abs_tol=1e-12),
        math.isclose(
            float(control["target_image_distance_mm"]),
            float(expected["expected_image_distance_mm"]),
            abs_tol=1e-12,
        ),
        previous_control.get("case", {}).get("case_id") == expected["case_id"],
        previous_control.get("connection_closed") is True,
        previous_control.get("input_model_unchanged") is True,
        previous_control.get("working_copy_unchanged") is True,
        previous_control.get("quick_focus_used") is False,
        previous_control.get("optimization_used") is False,
        previous_control.get("save_as_used") is False,
    )
    if not all(checks):
        raise ValueError("The frozen Day23 baseline evidence is unsafe.")
    return control


def ensure_approval_not_consumed(config):
    """Refuse a second execution after any Day 51 result exists."""

    output_root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    result_name = config["output"]["result_name"]
    matches = list(output_root.glob(f"**/{result_name}")) if output_root.exists() else []
    if matches:
        raise ValueError(f"The Day 50 one-time approval was already consumed: {matches[0]}")
    return output_root


def collect_inputs(config):
    """Verify and return every input required by plan and execution."""

    approval_path, approval = load_frozen_json(
        config,
        "day50_approval",
        "day50_approval_sha256",
        config["source"]["expected_day50_task"],
    )
    evidence_path, evidence = load_frozen_json(
        config,
        "day48_change_evidence",
        "day48_change_evidence_sha256",
        config["source"]["expected_day48_task"],
    )
    day23_config_path = frozen_path(config, "day23_config", "day23_config_sha256")
    day8_batch_path = frozen_path(config, "day8_batch_report", "day8_batch_sha256")
    day8_case_path = frozen_path(config, "day8_case_report", "day8_case_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    day9_path = frozen_path(config, "day9_baseline_report", "day9_baseline_sha256")
    previous_path, previous = load_frozen_json(
        config,
        "previous_day23_control",
        "previous_day23_control_sha256",
        "day23_residual_defocus_baseline_control",
    )
    validate_approval(config, approval)
    validate_change_evidence(config, evidence)
    day23_config = load_config(config["source"]["day23_config"])
    control = validate_optical_evidence(config, day23_config, previous)
    output_root = ensure_approval_not_consumed(config)
    return {
        "approval_path": approval_path,
        "approval": approval,
        "evidence_path": evidence_path,
        "day23_config_path": day23_config_path,
        "day23_config": day23_config,
        "day8_batch_path": day8_batch_path,
        "day8_case_path": day8_case_path,
        "model_path": model_path,
        "day9_path": day9_path,
        "previous_path": previous_path,
        "previous_control": previous,
        "control": control,
        "output_root": output_root,
    }


def print_introduction(config):
    """Print the four-part daily teaching introduction."""

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
    config = load_config("configs/day51_approved_day23_baseline_control.yaml")
    validate_execution_contract(config)
    inputs = collect_inputs(config)
    control = inputs["control"]

    print_introduction(config)
    print("========== DAY 51 APPROVED DAY23 BASELINE CONTROL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will occur in this step.")
    print("Approved scope: Slot 2 / Day 23 / defocus_004 / one execution")
    print(f"Day50 approval: {inputs['approval_path']}")
    print(f"Change evidence: {inputs['evidence_path']}")
    print("Change-specific positioning accuracy: +/-0.012 mm (not an optical model input)")
    print(f"Focused model: {inputs['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    print(f"Control offset: {control['offset_mm']:+.3f} mm")
    print(f"Image distance: {control['target_image_distance_mm']:.10f} mm")
    print("Planned analyses: one Standard Spot + one FFT MTF at 30/50 cycles/mm")
    print(f"Isolated output root: {inputs['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day50 approval and one-time execution contract verified")
    print("[PASS] Day48 0.012 mm evidence verified and kept separate from optical inputs")
    print("[PASS] Day23 recipe, focused model and previous baseline fingerprints verified")
    print("[PASS] Exactly one zero-defocus control selected")
    print("[PASS] No prior result has consumed this approval")
    print("[PASS] Six residual cases, Quick Focus, optimization and SaveAs remain locked")
    print("PLAN ONLY finished. No output, connection or optical calculation was created.")


if __name__ == "__main__":
    main()
