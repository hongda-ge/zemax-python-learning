"""Day 73 step 2: consume Day 72 approval and attempt one recovery control."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_validate_baseline_control import compare_control, evaluate_balanced, observed_summary  # noqa: E402
from scripts.demos.day73_approved_recovery_baseline_retry_plan import collect_inputs, sha256_file  # noqa: E402


def consume_authorization(config, inputs, run_dir):
    marker = inputs["marker"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": "day73_retry_authorization_consumption",
        "status": "consumed_before_zosapi_retry_attempt",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(inputs["approval_path"]),
        "approval_sha256": config["source"]["day72_approval_sha256"],
        "decision_id": inputs["approval"]["decision_id"],
        "recovery_stage": "stage_01_zero_control_retry_01",
        "run_directory": str(run_dir),
        "maximum_execution_count": 1,
        "additional_retry_released": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return marker


def maximum_differences(comparison):
    spot = max(abs(float(row["difference"])) for row in comparison if row["metric"].startswith("spot_"))
    mtf = max(abs(float(row["difference"])) for row in comparison if row["metric"].startswith("mtf"))
    return spot, mtf


def append_common_audit(result, config, inputs, marker, outcome):
    result.update({
        "recovery_stage": "stage_01_zero_control_retry_01",
        "retry_outcome": outcome,
        "approval": {
            "path": str(inputs["approval_path"]),
            "sha256": config["source"]["day72_approval_sha256"],
            "decision_id": inputs["approval"]["decision_id"],
            "consumed_once": True,
            "consumption_marker": str(marker),
            "additional_retry_released": False,
        },
        "source_day71_review": str(inputs["review_path"]),
        "source_historical_control": str(inputs["historical_path"]),
        "seven_recovery_cases_executed": False,
        "day27_recalculated": False,
        "slot6_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
        "post_execution_gate": config["guardrails"]["post_execution_gate"],
        "cp09_manual_review_required": True,
    })


def main():
    config = load_config("configs/day73_approved_recovery_baseline_retry.yaml")
    inputs = collect_inputs(config)
    baseline = load_config(inputs["day25"]["source"]["baseline_config"])
    frozen_paths = (
        inputs["approval_path"], inputs["review_path"], inputs["historical_path"],
        inputs["day25_path"], inputs["model_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    stamp = datetime.now().astimezone().strftime(config["output"]["execution_directory_prefix"] + "%Y%m%d_%H%M%S")
    run_dir = inputs["output_root"] / stamp
    case_dir = run_dir / config["output"]["case_directory"]
    result_path = case_dir / config["output"]["result_name"]
    marker = consume_authorization(config, inputs, run_dir)

    print("========== DAY 73 APPROVED RECOVERY BASELINE RETRY ==========")
    print("Day72 one-attempt retry authorization has been consumed.")
    print("Only recovery_control_000 (0.000 mm) will be attempted once.")
    print(f"Focused input model: {inputs['model_path']}")
    print(f"Output directory: {run_dir}")
    print("One Standalone connection attempt; no Quick Focus, optimization or SaveAs.")

    try:
        result, result_path = execute_case(
            inputs["day25"], baseline, inputs["control"], case_dir, inputs["model_path"],
            task_name="day73_approved_recovery_baseline_retry_execution",
            report_name=config["output"]["result_name"],
        )
        observed = observed_summary(result)
        comparison = compare_control(inputs["day25"], inputs["historical"]["summary_metrics"], observed)
        balanced_checks = evaluate_balanced(inputs["day25"], observed)
        maximum_spot, maximum_mtf = maximum_differences(comparison)
        if maximum_spot > float(config["guardrails"]["maximum_spot_summary_difference_um"]):
            raise ValueError("Day 73 Spot reproduction exceeded the approved tolerance.")
        if maximum_mtf > float(config["guardrails"]["maximum_mtf_summary_difference"]):
            raise ValueError("Day 73 MTF reproduction exceeded the approved tolerance.")
        if not all((
            result.get("connection_closed") is True,
            result.get("input_model_unchanged") is True,
            result.get("working_copy_unchanged") is True,
            result.get("quick_focus_used") is False,
            result.get("optimization_used") is False,
            result.get("save_as_used") is False,
            all(balanced_checks.values()),
        )):
            raise ValueError("Day 73 failed the optical or safety audit.")
        for path, expected_hash in frozen_hashes.items():
            if sha256_file(path) != expected_hash:
                raise ValueError(f"A frozen Day 73 input changed during execution: {path}")

        append_common_audit(result, config, inputs, marker, "SUCCESS_LICENSE_AND_OPTICAL_BASELINE_REVERIFIED")
        result.update({
            "standalone_zosapi_license_reverified": True,
            "summary_metrics": observed,
            "historical_reproduction": comparison,
            "maximum_historical_spot_difference_um": maximum_spot,
            "maximum_historical_mtf_difference": maximum_mtf,
            "balanced_acceptance_checks": balanced_checks,
            "balanced_acceptance_pass": True,
            "recovery_baseline_retry_completed": True,
            "all_frozen_inputs_unchanged": True,
        })
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        print("[PASS] Day72 approval consumed exactly once")
        print("[PASS] Standalone ZOS-API license and connection reverified")
        print(f"[PASS] Spot mean/worst: {observed['spot_mean_rms_um']:.6f}/{observed['spot_worst_rms_um']:.6f} um")
        print(f"[PASS] MTF30 mean/min: {observed['mtf30_mean']:.6f}/{observed['mtf30_minimum']:.6f}")
        print(f"[PASS] MTF50 mean/min: {observed['mtf50_mean']:.6f}/{observed['mtf50_minimum']:.6f}")
        print(f"[PASS] Maximum historical Spot difference: {maximum_spot:.9f} um")
        print(f"[PASS] Maximum historical MTF difference: {maximum_mtf:.9f}")
        print("[PASS] Input and disk working-copy hashes unchanged; connection closed")
        print("[PASS] Seven recovery cases, Day27 recalculation and Slot 6 remain locked")
        print("[WAIT] CP09 manual review is required before any recovery-batch release")
        print(f"[PASS] Recovery retry result: {result_path}")
    except Exception as exc:
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
        else:
            result = {
                "task": "day73_approved_recovery_baseline_retry_execution",
                "status": "failed",
                "time_local": datetime.now().astimezone().isoformat(),
                "case": inputs["control"],
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        append_common_audit(result, config, inputs, marker, "FAILED_RETRY_REQUIRES_CP09_REVIEW")
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["standalone_zosapi_license_reverified"] = False
        result["recovery_baseline_retry_completed"] = False
        result["additional_retry_released"] = False
        result["all_frozen_inputs_unchanged"] = all(
            sha256_file(path) == expected_hash for path, expected_hash in frozen_hashes.items()
        )
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[FAIL] Day73 retry stopped safely: {type(exc).__name__}: {exc}")
        print("[PASS] Day72 approval remains consumed and cannot be reused")
        print("[PASS] No additional retry, seven-point batch, Day27 recalculation or Slot 6 release")
        print("[WAIT] CP09 failure review is required before any new action")
        print(f"[PASS] Failure result: {result_path}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
