"""Day 25 step 2: reproduce the zero-offset optical control."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_run_residual_defocus_batch import frequency_map  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_balanced_acceptance_boundary_scan_plan import (  # noqa: E402
    validate_day24_evidence,
    validate_guardrails,
    validate_source_files,
    validate_thresholds,
)


def require_baseline_authorization(config):
    """Authorize only the zero-offset control and keep nine cases locked."""

    execution = config["execution"]
    required = (
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_baseline_control",
    )
    missing = [key for key in required if execution.get(key) is not True]
    forbidden = (
        "enabled",
        "allow_boundary_cases",
        "allow_offline_acceptance",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_tolerance_claim",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if missing or enabled:
        raise ValueError(
            "Day 25 baseline authorization failed: " + ", ".join(missing + enabled)
        )


def validate_analysis_recipe(config):
    """Require exact reuse of the reviewed Day 23 Spot and MTF settings."""

    day23 = load_config(config["source"]["day23_config"])
    if config["analysis"] != day23["analysis"]:
        raise ValueError("Day 25 analysis recipe differs from Day 23.")


def load_day23_control(day24_report):
    """Load the measured zero-offset summaries used by Day 24."""

    day23_file = Path(day24_report["source_day23_report"])
    report = json.loads(day23_file.read_text(encoding="utf-8"))
    rows = [row for row in report.get("rows", []) if math.isclose(row["offset_mm"], 0.0)]
    if len(rows) != 1:
        raise ValueError("Day 23 does not contain one zero-offset control.")
    return day23_file, rows[0]


def observed_summary(result):
    """Flatten the reproduced Spot and MTF metrics for exact comparison."""

    mtf = frequency_map(result["mtf_summary"])
    return {
        "spot_mean_rms_um": float(result["spot_summary"]["equal_field_mean_rms_um"]),
        "spot_worst_rms_um": float(result["spot_summary"]["worst_field_rms_um"]),
        "mtf30_mean": float(mtf[30.0]["overall_mean_mtf"]),
        "mtf30_minimum": float(mtf[30.0]["minimum_mtf"]),
        "mtf50_mean": float(mtf[50.0]["overall_mean_mtf"]),
        "mtf50_minimum": float(mtf[50.0]["minimum_mtf"]),
    }


def compare_control(config, expected, observed):
    """Compare six summaries without rounding and enforce frozen tolerances."""

    spot_tolerance = float(config["guardrails"]["baseline_spot_max_absolute_difference_um"])
    mtf_tolerance = float(config["guardrails"]["baseline_mtf_max_absolute_difference"])
    rows = []
    for metric, actual in observed.items():
        reference = float(expected[metric])
        difference = actual - reference
        tolerance = spot_tolerance if metric.startswith("spot_") else mtf_tolerance
        rows.append(
            {
                "metric": metric,
                "day23_value": reference,
                "day25_value": actual,
                "difference": difference,
                "tolerance": tolerance,
                "passed": abs(difference) <= tolerance,
            }
        )
    failed = [row["metric"] for row in rows if not row["passed"]]
    if failed:
        raise ValueError("Day 25 control did not reproduce: " + ", ".join(failed))
    return rows


def evaluate_balanced_checks(config, observed):
    """Return the four balanced checks without enforcing control-point PASS."""
    limits = config["balanced_acceptance"]["limits"]
    return {
        "spot_mean": observed["spot_mean_rms_um"] <= limits["spot_mean_rms_um_max"],
        "spot_worst": observed["spot_worst_rms_um"] <= limits["spot_worst_rms_um_max"],
        "mtf30_minimum": observed["mtf30_minimum"] >= limits["mtf30_minimum_min"],
        "mtf50_minimum": observed["mtf50_minimum"] >= limits["mtf50_minimum_min"],
    }


def evaluate_balanced(config, observed):
    """Confirm that the reproduced zero-offset point still passes Day 24."""

    checks = evaluate_balanced_checks(config, observed)
    if not all(checks.values()):
        raise ValueError("Reproduced zero-offset control failed balanced acceptance.")
    return checks


def main():
    config = load_config("configs/day25_balanced_acceptance_boundary_scan.yaml")
    require_baseline_authorization(config)
    validate_guardrails(config)
    validate_analysis_recipe(config)
    day24_file, model_file = validate_source_files(config)
    day24_report, _ = validate_day24_evidence(config, day24_file)
    validate_thresholds(config, day24_report)
    day23_file, day23_control = load_day23_control(day24_report)
    baseline = load_config(config["source"]["baseline_config"])
    control = {
        "case_id": "boundary_control_000",
        "offset_mm": 0.0,
        "target_image_distance_mm": float(
            config["reference_state"]["focused_image_distance_mm"]
        ),
        "is_control": True,
    }
    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("baseline_control_%Y%m%d_%H%M%S")
    )
    case_dir = output_dir / control["case_id"]

    print("========== DAY 25 ZERO-OFFSET REPRODUCIBILITY CONTROL ==========")
    print("Only the 0.000 mm control will run; nine new boundary points stay locked.")
    print(f"Focused input model: {model_file}")
    print(f"Output directory: {output_dir}")
    print("Quick Focus, optimization and SaveAs are forbidden.")

    result, result_file = execute_case(
        config,
        baseline,
        control,
        case_dir,
        model_file,
        task_name="day25_boundary_baseline_control",
        report_name="baseline_control_report.json",
    )
    observed = observed_summary(result)
    comparison = compare_control(config, day23_control, observed)
    balanced_checks = evaluate_balanced(config, observed)
    result["source_day24_report"] = str(day24_file)
    result["source_day23_report"] = str(day23_file)
    result["summary_metrics"] = observed
    result["day23_reproduction"] = comparison
    result["balanced_acceptance_checks"] = balanced_checks
    result["balanced_acceptance_pass"] = True
    result["nine_boundary_cases_executed"] = False
    result_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("[PASS] ZOS-API connection and isolated working copy")
    print(f"[PASS] Spot mean/worst: {observed['spot_mean_rms_um']:.6f}/"
          f"{observed['spot_worst_rms_um']:.6f} um")
    print(f"[PASS] MTF30 mean/min: {observed['mtf30_mean']:.6f}/"
          f"{observed['mtf30_minimum']:.6f}")
    print(f"[PASS] MTF50 mean/min: {observed['mtf50_mean']:.6f}/"
          f"{observed['mtf50_minimum']:.6f}")
    maximum_spot = max(
        abs(row["difference"]) for row in comparison if row["metric"].startswith("spot_")
    )
    maximum_mtf = max(
        abs(row["difference"]) for row in comparison if row["metric"].startswith("mtf")
    )
    print(f"[PASS] Maximum Day 23 Spot summary difference: {maximum_spot:.9f} um")
    print(f"[PASS] Maximum Day 23 MTF summary difference: {maximum_mtf:.9f}")
    print("[PASS] Zero-offset control still passes balanced acceptance")
    print("[PASS] Input and disk working-copy hashes unchanged")
    print("[PASS] ZOS-API connection closed")
    print("[PASS] Nine new boundary points were not executed")
    print(f"[PASS] Result report: {result_file}")


if __name__ == "__main__":
    main()
