"""Day 54 step 1: plan the approved six-case residual-defocus execution."""

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


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def frozen_path(config, path_key, hash_key):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 54 input changed: {path_key}")
    return path


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    path = frozen_path(config, path_key, hash_key)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 54 metadata is invalid: {path_key}")
    return path, report


def validate_execution_contract(config):
    execution = config["execution"]
    true_keys = ("enabled", "allow_zosapi_connection", "allow_model_copy", "allow_focus_surface_in_memory_write", "allow_standard_spot", "allow_fft_mtf", "allow_residual_cases")
    false_keys = ("allow_baseline_control", "allow_quick_focus", "allow_optimization", "allow_save_as", "allow_source_modification", "allow_downstream_release")
    if any(execution[key] is not True for key in true_keys) or any(execution[key] is not False for key in false_keys):
        raise ValueError("Day 54 execution permissions are unsafe.")
    if int(execution["approved_resource_slot"]) != 2 or int(execution["maximum_batch_execution_count"]) != 1 or int(execution["maximum_case_execution_count"]) != 6 or int(execution["maximum_active_zosapi_connections"]) != 1:
        raise ValueError("Day 54 must be one six-case, single-channel Slot 2 batch.")


def validate_approval(config, approval):
    batch = config["approved_batch"]
    contract = approval["execution_contract"]
    expected_root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    checks = (
        approval.get("decision_status") == config["source"]["expected_day53_status"],
        approval.get("approved_scope", {}).get("resource_slot") == 2,
        approval.get("approved_scope", {}).get("case_ids") == batch["case_ids"],
        [float(value) for value in approval.get("approved_scope", {}).get("offsets_mm", [])] == [float(value) for value in batch["offsets_mm"]],
        approval.get("approved_scope", {}).get("maximum_batch_execution_count") == 1,
        approval.get("approved_scope", {}).get("maximum_case_execution_count") == 6,
        contract.get("required_entrypoint") == config["guardrails"]["required_entrypoint"],
        Path(contract.get("approved_output_root", "")).resolve() == expected_root,
        contract.get("run_sequentially") is True,
        contract.get("maximum_active_zosapi_connections") == 1,
        contract.get("allow_quick_focus") is False,
        contract.get("allow_optimization") is False,
        contract.get("allow_save_as") is False,
        contract.get("allow_baseline_rerun") is False,
        contract.get("post_execution_gate") == config["guardrails"]["post_execution_gate"],
        approval.get("permissions", {}).get("residual_batch_execution_released") is True,
        approval.get("approved_batch_executed") is False,
        approval.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 53 approval does not authorize the Day 54 contract.")


def validate_baseline(result, config):
    checks = (
        result.get("case", {}).get("case_id") == "defocus_004",
        result.get("slot2_baseline_control_completed") is True,
        result.get("approval", {}).get("consumed_once") is True,
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("residual_cases_executed") is False,
        result.get("downstream_slots_released") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("input_sha256_before") == config["source"]["focused_model_sha256"],
    )
    if not all(checks):
        raise ValueError("Day 51 baseline result is incomplete or unsafe.")


def validate_cases(config, day23, historical):
    cases = [case for case in build_cases(day23) if not case["is_control"]]
    batch = config["approved_batch"]
    if [case["case_id"] for case in cases] != batch["case_ids"] or [float(case["offset_mm"]) for case in cases] != [float(value) for value in batch["offsets_mm"]]:
        raise ValueError("Day 54 cases differ from the approved six-case scope.")
    if historical.get("case_count") != 6 or [row["case_id"] for row in historical["rows"]] != batch["case_ids"]:
        raise ValueError("Historical Day 23 case identities changed.")
    if any(math.isclose(float(case["offset_mm"]), 0.0, abs_tol=1e-12) for case in cases):
        raise ValueError("Day 54 must not rerun the zero-offset control.")
    return cases


def ensure_approval_not_consumed(config):
    root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    marker = root / config["output"]["authorization_consumption_name"]
    results = list(root.glob(f"**/{config['output']['batch_result_name']}")) if root.exists() else []
    if marker.exists() or results:
        found = marker if marker.exists() else results[0]
        raise ValueError(f"The Day 53 one-time approval was already consumed: {found}")
    return root, marker


def collect_inputs(config):
    validate_execution_contract(config)
    approval_path, approval = load_frozen_json(config, "day53_approval", "day53_approval_sha256", "expected_day53_task")
    baseline_path, baseline = load_frozen_json(config, "day51_baseline_result", "day51_baseline_sha256", "expected_day51_task")
    historical_path, historical = load_frozen_json(config, "historical_residual_batch", "historical_residual_batch_sha256", "expected_historical_task")
    day23_path = frozen_path(config, "day23_config", "day23_config_sha256")
    model_path = frozen_path(config, "focused_model", "focused_model_sha256")
    validate_approval(config, approval)
    validate_baseline(baseline, config)
    day23 = load_config(config["source"]["day23_config"])
    validate_analysis_recipes(day23)
    validate_guardrails(day23)
    cases = validate_cases(config, day23, historical)
    output_root, marker = ensure_approval_not_consumed(config)
    return {"approval_path": approval_path, "approval": approval, "baseline_path": baseline_path, "baseline": baseline, "historical_path": historical_path, "historical": historical, "day23_path": day23_path, "day23": day23, "model_path": model_path, "cases": cases, "output_root": output_root, "marker": marker}


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
    config = load_config("configs/day54_approved_day23_residual_batch.yaml")
    inputs = collect_inputs(config)
    print_introduction(config)
    print("========== DAY 54 APPROVED RESIDUAL-BATCH PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No authorization will be consumed and no ZOS-API connection will occur in this step.")
    print("Approved scope: Slot 2 / Day 23 / six nonzero cases / one batch")
    print(f"Day53 approval: {inputs['approval_path']}")
    print(f"Focused model: {inputs['model_path']}")
    print(f"Focused model SHA256: {config['source']['focused_model_sha256']}")
    for case in inputs["cases"]:
        print(f"  {case['case_id']}: offset={float(case['offset_mm']):+.3f} mm, target image distance={float(case['target_image_distance_mm']):.10f} mm")
    print("Planned analyses: six Standard Spot + six FFT MTF exports")
    print("Planned connections/copies: six sequential lifecycles / six independent copies")
    print(f"Authorization marker: {inputs['marker']}")
    print(f"Isolated output root: {inputs['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day53 approval and one-time batch contract verified")
    print("[PASS] Day51 zero-offset baseline verified and excluded from the batch")
    print("[PASS] Six approved case identities, offsets and historical evidence verified")
    print("[PASS] No prior marker or result has consumed this approval")
    print("[PASS] Quick Focus, optimization, SaveAs and Slot 3-6 remain locked")
    print("PLAN ONLY finished. No output, connection or optical calculation was created.")


if __name__ == "__main__":
    main()
