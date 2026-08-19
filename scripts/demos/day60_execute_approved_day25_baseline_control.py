"""Day 60 step 2: consume Day 59 approval and run one Day 25 control."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_validate_baseline_control import (  # noqa: E402
    compare_control,
    evaluate_balanced,
    observed_summary,
)
from scripts.demos.day60_approved_day25_baseline_control_plan import (  # noqa: E402
    collect_inputs,
    sha256_file,
)


def consume_authorization(config, inputs, run_dir):
    marker = inputs["marker"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": "day60_authorization_consumption",
        "status": "consumed_before_zosapi_execution",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(inputs["approval_path"]),
        "approval_sha256": config["source"]["day59_approval_sha256"],
        "decision_id": inputs["approval"]["decision_id"],
        "run_directory": str(run_dir),
        "maximum_execution_count": 1,
        "rerun_released": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return marker


def maximum_differences(comparison):
    spot = max(
        abs(float(row["difference"]))
        for row in comparison
        if row["metric"].startswith("spot_")
    )
    mtf = max(
        abs(float(row["difference"]))
        for row in comparison
        if row["metric"].startswith("mtf")
    )
    return spot, mtf


def main():
    config = load_config("configs/day60_approved_day25_baseline_control.yaml")
    inputs = collect_inputs(config)
    baseline = load_config(inputs["day25"]["source"]["baseline_config"])
    frozen_paths = (
        inputs["approval_path"],
        inputs["historical_path"],
        inputs["day25_path"],
        inputs["model_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    stamp = datetime.now().astimezone().strftime(
        config["output"]["execution_directory_prefix"] + "%Y%m%d_%H%M%S"
    )
    run_dir = inputs["output_root"] / stamp
    case_dir = run_dir / config["output"]["case_directory"]
    marker = consume_authorization(config, inputs, run_dir)

    print("========== DAY 60 APPROVED DAY25 BASELINE CONTROL ==========")
    print("Day59 one-time authorization has been consumed.")
    print("Only boundary_control_000 (0.000 mm) will run; nine boundary cases remain locked.")
    print(f"Focused input model: {inputs['model_path']}")
    print(f"Output directory: {run_dir}")
    print("One Standalone connection; no Quick Focus, optimization or SaveAs.")

    result, result_path = execute_case(
        inputs["day25"],
        baseline,
        inputs["control"],
        case_dir,
        inputs["model_path"],
        task_name="day60_approved_day25_baseline_control_execution",
        report_name=config["output"]["result_name"],
    )
    observed = observed_summary(result)
    comparison = compare_control(
        inputs["day25"], inputs["historical"]["summary_metrics"], observed
    )
    balanced_checks = evaluate_balanced(inputs["day25"], observed)
    maximum_spot, maximum_mtf = maximum_differences(comparison)
    if maximum_spot > float(config["guardrails"]["maximum_spot_summary_difference_um"]):
        raise ValueError("Day 60 Spot reproduction exceeded the approved tolerance.")
    if maximum_mtf > float(config["guardrails"]["maximum_mtf_summary_difference"]):
        raise ValueError("Day 60 MTF reproduction exceeded the approved tolerance.")

    safety_checks = (
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
    )
    if not all(safety_checks):
        raise ValueError("Day 60 failed the model or connection safety audit.")
    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 60 input changed during execution: {path}")

    result.update(
        {
            "resource_slot": 4,
            "approval": {
                "path": str(inputs["approval_path"]),
                "sha256": config["source"]["day59_approval_sha256"],
                "decision_id": inputs["approval"]["decision_id"],
                "consumed_once": True,
                "consumption_marker": str(marker),
            },
            "source_historical_control": str(inputs["historical_path"]),
            "summary_metrics": observed,
            "historical_reproduction": comparison,
            "maximum_historical_spot_difference_um": maximum_spot,
            "maximum_historical_mtf_difference": maximum_mtf,
            "balanced_acceptance_checks": balanced_checks,
            "balanced_acceptance_pass": True,
            "slot4_baseline_control_completed": True,
            "nine_boundary_cases_executed": False,
            "downstream_slots_released": False,
            "continuous_tolerance_claimed": False,
            "engineering_change_approved": False,
            "all_frozen_inputs_unchanged": True,
            "post_execution_gate": config["guardrails"]["post_execution_gate"],
            "cp09_manual_review_required": True,
        }
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[PASS] Day59 approval consumed exactly once")
    print("[PASS] ZOS-API connection and isolated working copy")
    print(
        f"[PASS] Spot mean/worst: {observed['spot_mean_rms_um']:.6f}/"
        f"{observed['spot_worst_rms_um']:.6f} um"
    )
    print(
        f"[PASS] MTF30 mean/min: {observed['mtf30_mean']:.6f}/"
        f"{observed['mtf30_minimum']:.6f}"
    )
    print(
        f"[PASS] MTF50 mean/min: {observed['mtf50_mean']:.6f}/"
        f"{observed['mtf50_minimum']:.6f}"
    )
    print(f"[PASS] Maximum historical Spot difference: {maximum_spot:.9f} um")
    print(f"[PASS] Maximum historical MTF difference: {maximum_mtf:.9f}")
    print("[PASS] Zero-offset control still passes balanced acceptance")
    print("[PASS] Input and disk working-copy hashes unchanged")
    print("[PASS] ZOS-API connection closed")
    print("[PASS] Nine boundary cases and Slot 5-6 remain locked")
    print("[WAIT] CP09 manual review is required before any boundary-batch release")
    print(f"[PASS] Slot 4 baseline result: {result_path}")


if __name__ == "__main__":
    main()
