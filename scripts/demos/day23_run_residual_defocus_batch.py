"""Day 23 step 3: run six reviewed residual-defocus Spot/MTF cases."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_residual_defocus_optical_impact_plan import (  # noqa: E402
    build_cases,
    find_latest_day22_report,
    validate_analysis_recipes,
    validate_day22_evidence,
    validate_day8_evidence,
    validate_guardrails,
    validate_input_model,
)
from scripts.demos.day23_validate_baseline_control import (  # noqa: E402
    execute_case,
    summarize_spot,
    validate_day9_baseline,
)


def require_batch_authorization(config):
    """Authorize six residual cases only after the control is locked."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "model copy": execution["allow_model_copy"],
        "focus-surface memory write": execution[
            "allow_focus_surface_in_memory_write"
        ],
        "Standard Spot": execution["allow_standard_spot"],
        "FFT MTF": execution["allow_fft_mtf"],
        "residual cases": execution["allow_residual_cases"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 23 residual batch not approved: " + ", ".join(missing))
    forbidden = {
        "baseline control": execution["allow_baseline_control"],
        "Quick Focus": execution["allow_quick_focus"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
        "engineering recommendation": execution["allow_engineering_recommendation"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 23 batch action: " + ", ".join(enabled))


def find_latest_control_report(config):
    """Find the most recent reviewed zero-offset control."""

    source = config["source"]
    root = PROJECT_ROOT / source["day23_control_output_root"]
    matches = list(root.glob(f"baseline_control_*/**/{source['day23_control_report_name']}"))
    if not matches:
        raise FileNotFoundError("No Day 23 baseline control report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_control_report(config, report_file, model_file, model_hash):
    """Require exact Spot/MTF reproduction and all safety properties."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    guardrails = config["guardrails"]
    checks = {
        "task": report.get("task") == config["source"]["expected_day23_control_task"],
        "status": report.get("status") == "success",
        "control": report.get("case", {}).get("is_control") is True,
        "zero offset": math.isclose(
            float(report.get("case", {}).get("offset_mm", 99.0)),
            0.0,
            abs_tol=1e-12,
        ),
        "input model": Path(report.get("input_model", "")).resolve()
        == model_file.resolve(),
        "input hash": report.get("input_sha256_before", "").upper() == model_hash,
        "input unchanged": report.get("input_model_unchanged") is True,
        "copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "Spot reproduction": float(
            report.get("spot_reproduction", {}).get(
                "maximum_absolute_difference_um", 99.0
            )
        )
        <= float(guardrails["baseline_spot_max_absolute_difference_um"]),
        "MTF reproduction": float(
            report.get("mtf_reproduction", {}).get(
                "maximum_absolute_difference", 99.0
            )
        )
        <= float(guardrails["baseline_mtf_max_absolute_difference"]),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 23 baseline control failed: " + ", ".join(failed))
    if "spot_summary" not in report:
        report["spot_summary"] = summarize_spot(report["spot_metrics"])
    return report


def frequency_map(mtf_summary):
    """Index transparent frequency summaries."""

    return {
        float(row["frequency_cyc_per_mm"]): row
        for row in mtf_summary["frequencies"]
    }


def build_row(result, control):
    """Build one flat comparison row relative to the zero-offset control."""

    case = result["case"]
    spot = result["spot_summary"]
    control_spot = control["spot_summary"]
    mtf = frequency_map(result["mtf_summary"])
    control_mtf = frequency_map(control["mtf_summary"])
    return {
        "case_id": case["case_id"],
        "offset_mm": float(case["offset_mm"]),
        "image_distance_mm": float(result["surface6_after"]["thickness"]),
        "spot_mean_rms_um": float(spot["equal_field_mean_rms_um"]),
        "spot_mean_change_um": float(spot["equal_field_mean_rms_um"])
        - float(control_spot["equal_field_mean_rms_um"]),
        "spot_worst_rms_um": float(spot["worst_field_rms_um"]),
        "mtf30_mean": float(mtf[30.0]["overall_mean_mtf"]),
        "mtf30_change": float(mtf[30.0]["overall_mean_mtf"])
        - float(control_mtf[30.0]["overall_mean_mtf"]),
        "mtf30_minimum": float(mtf[30.0]["minimum_mtf"]),
        "mtf50_mean": float(mtf[50.0]["overall_mean_mtf"]),
        "mtf50_change": float(mtf[50.0]["overall_mean_mtf"])
        - float(control_mtf[50.0]["overall_mean_mtf"]),
        "mtf50_minimum": float(mtf[50.0]["minimum_mtf"]),
    }


def write_csv(path, rows):
    """Write the six nonzero residual-defocus cases."""

    fields = tuple(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day23_residual_defocus_optical_impact.yaml")
    require_batch_authorization(config)
    model_file, model_hash = validate_input_model(config)
    validate_day8_evidence(config, model_file, model_hash)
    day22_file = find_latest_day22_report(config)
    validate_day22_evidence(config, day22_file)
    validate_analysis_recipes(config)
    validate_guardrails(config)
    _, day9 = validate_day9_baseline(config, model_file, model_hash)
    control_file = find_latest_control_report(config)
    control = validate_control_report(
        config,
        control_file,
        model_file,
        model_hash,
    )
    baseline = load_config(config["source"]["baseline_config"])
    cases = [case for case in build_cases(config) if not case["is_control"]]
    if len(cases) != int(config["comparison"]["residual_case_count"]):
        raise ValueError("Day 23 residual-case count is incorrect.")

    run_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("residual_batch_%Y%m%d_%H%M%S")
    )
    results = []
    rows = []

    print("========== DAY 23 REVIEWED RESIDUAL-DEFOCUS BATCH ==========")
    print(f"Approved by baseline control: {control_file}")
    print(f"Batch directory: {run_dir}")
    print("Six nonzero residual offsets run sequentially and stop on first failure.")
    print("Quick Focus, optimization and SaveAs are forbidden.")

    for case in cases:
        print(
            f"\nRunning {case['case_id']} at offset "
            f"{case['offset_mm']:+.3f} mm..."
        )
        result, _ = execute_case(
            config,
            baseline,
            case,
            run_dir / case["case_id"],
            model_file,
            task_name="day23_residual_defocus_case",
            report_name="result.json",
        )
        tolerance = float(config["guardrails"]["numeric_tolerance_mm"])
        if not math.isclose(
            float(result["surface6_after"]["radius"]),
            float(config["reference_state"]["surface6_radius_mm"]),
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValueError(f"{case['case_id']} changed Surface 6 radius.")
        row = build_row(result, control)
        results.append(result)
        rows.append(row)
        print(
            f"[PASS] Spot mean/worst: {row['spot_mean_rms_um']:.3f}/"
            f"{row['spot_worst_rms_um']:.3f} um"
        )
        print(
            f"[PASS] MTF30 mean/min: {row['mtf30_mean']:.4f}/"
            f"{row['mtf30_minimum']:.4f}"
        )
        print(
            f"[PASS] MTF50 mean/min: {row['mtf50_mean']:.4f}/"
            f"{row['mtf50_minimum']:.4f}"
        )
        print("[PASS] Connection closed; input and disk copy unchanged")

    run_dir.mkdir(parents=True, exist_ok=True)
    csv_file = run_dir / "residual_defocus_optical_metrics.csv"
    report_file = run_dir / "residual_defocus_batch_report.json"
    write_csv(csv_file, rows)
    report = {
        "task": "day23_residual_defocus_batch",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(model_file),
        "source_sha256": model_hash,
        "source_baseline_control": str(control_file),
        "source_day22_report": str(day22_file),
        "case_count": len(results),
        "rows": rows,
        "case_reports": [
            str(run_dir / result["case"]["case_id"] / "result.json")
            for result in results
        ],
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 23 RESIDUAL-DEFOCUS SUMMARY ==========")
    for row in rows:
        print(
            f"{row['case_id']}: offset={row['offset_mm']:+.3f} mm, "
            f"Spot mean={row['spot_mean_rms_um']:.3f} um, "
            f"MTF30={row['mtf30_mean']:.4f}, MTF50={row['mtf50_mean']:.4f}"
        )
    print("[PASS] Six residual cases completed; zero-offset control was not rerun")
    print("[PASS] All connections closed and disk models remained unchanged")
    print("[PASS] No Quick Focus, optimization or model save was used")
    print(f"[PASS] Comparison CSV: {csv_file}")
    print(f"[PASS] Batch report: {report_file}")


if __name__ == "__main__":
    main()
