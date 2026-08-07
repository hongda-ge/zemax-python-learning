"""Day 25 step 3: run nine reviewed residual-defocus boundary cases."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_balanced_acceptance_boundary_scan_plan import (  # noqa: E402
    validate_day24_evidence,
    validate_guardrails,
    validate_new_offsets,
    validate_source_files,
    validate_thresholds,
)
from scripts.demos.day25_validate_baseline_control import (  # noqa: E402
    observed_summary,
    validate_analysis_recipe,
)


def require_boundary_authorization(config):
    """Authorize nine cases while keeping control and offline analysis locked."""

    execution = config["execution"]
    required = (
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_boundary_cases",
    )
    missing = [key for key in required if execution.get(key) is not True]
    forbidden = (
        "enabled",
        "allow_baseline_control",
        "allow_offline_acceptance",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_tolerance_claim",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if missing or enabled:
        raise ValueError(
            "Day 25 boundary authorization failed: " + ", ".join(missing + enabled)
        )


def find_latest_baseline_report(config):
    """Locate the newest successful Day 25 zero-offset control."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(root.glob("baseline_control_*/boundary_control_000/baseline_control_report.json"))
    if not matches:
        raise FileNotFoundError("No Day 25 zero-offset control report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_baseline_report(config, report_file, model_file, day24_file):
    """Require exact reproduction and complete safety evidence before the batch."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source_hash = config["source"]["focused_model_sha256"]
    checks = {
        "task": report.get("task") == "day25_boundary_baseline_control",
        "status": report.get("status") == "success",
        "input model": Path(report.get("input_model", "")).resolve() == model_file.resolve(),
        "input hash": report.get("input_sha256_before", "").upper() == source_hash,
        "input unchanged": report.get("input_model_unchanged") is True,
        "working copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "balanced pass": report.get("balanced_acceptance_pass") is True,
        "nine cases locked": report.get("nine_boundary_cases_executed") is False,
        "Day 24 source": Path(report.get("source_day24_report", "")).resolve()
        == day24_file.resolve(),
    }
    reproduction = report.get("day23_reproduction", [])
    checks["six reproduced summaries"] = len(reproduction) == 6 and all(
        row.get("passed") is True for row in reproduction
    )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 25 baseline evidence failed: " + ", ".join(failed))
    return report


def build_cases(config, negative_values, positive_values):
    """Build deterministic identities and target image distances."""

    reference = float(config["reference_state"]["focused_image_distance_mm"])
    cases = []
    for side, values in (("negative", negative_values), ("positive", positive_values)):
        for index, offset in enumerate(values, start=1):
            cases.append(
                {
                    "case_id": f"boundary_{side}_{index:03d}",
                    "side": side,
                    "offset_mm": offset,
                    "target_image_distance_mm": reference + offset,
                    "is_control": False,
                }
            )
    if len(cases) != 9 or len({item["case_id"] for item in cases}) != 9:
        raise ValueError("Day 25 did not build nine unique boundary cases.")
    return cases


def evaluate_balanced(config, metrics):
    """Evaluate four frozen rules independently at full precision."""

    limits = config["balanced_acceptance"]["limits"]
    checks = {
        "spot_mean": {
            "value": metrics["spot_mean_rms_um"],
            "limit": limits["spot_mean_rms_um_max"],
            "margin": limits["spot_mean_rms_um_max"] - metrics["spot_mean_rms_um"],
            "passed": metrics["spot_mean_rms_um"] <= limits["spot_mean_rms_um_max"],
        },
        "spot_worst": {
            "value": metrics["spot_worst_rms_um"],
            "limit": limits["spot_worst_rms_um_max"],
            "margin": limits["spot_worst_rms_um_max"] - metrics["spot_worst_rms_um"],
            "passed": metrics["spot_worst_rms_um"] <= limits["spot_worst_rms_um_max"],
        },
        "mtf30_minimum": {
            "value": metrics["mtf30_minimum"],
            "limit": limits["mtf30_minimum_min"],
            "margin": metrics["mtf30_minimum"] - limits["mtf30_minimum_min"],
            "passed": metrics["mtf30_minimum"] >= limits["mtf30_minimum_min"],
        },
        "mtf50_minimum": {
            "value": metrics["mtf50_minimum"],
            "limit": limits["mtf50_minimum_min"],
            "margin": metrics["mtf50_minimum"] - limits["mtf50_minimum_min"],
            "passed": metrics["mtf50_minimum"] >= limits["mtf50_minimum_min"],
        },
    }
    failed = [name for name, item in checks.items() if not item["passed"]]
    return checks, not failed, failed


def flatten_result(case, metrics, checks, passed, failed, report_file):
    """Create one CSV-friendly audit row."""

    row = {
        "case_id": case["case_id"],
        "side": case["side"],
        "offset_mm": case["offset_mm"],
        "target_image_distance_mm": case["target_image_distance_mm"],
        **metrics,
        "balanced_acceptance_pass": passed,
        "failed_metrics": ";".join(failed),
        "case_report": str(report_file),
    }
    for name, item in checks.items():
        row[f"{name}_margin"] = item["margin"]
    return row


def write_csv(path, rows):
    """Write the nine measured observations as a spreadsheet-friendly CSV."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day25_balanced_acceptance_boundary_scan.yaml")
    require_boundary_authorization(config)
    validate_guardrails(config)
    validate_analysis_recipe(config)
    day24_file, model_file = validate_source_files(config)
    day24_report, _ = validate_day24_evidence(config, day24_file)
    validate_thresholds(config, day24_report)
    negative_values, positive_values = validate_new_offsets(config)
    baseline_file = find_latest_baseline_report(config)
    validate_baseline_report(config, baseline_file, model_file, day24_file)
    cases = build_cases(config, negative_values, positive_values)
    baseline = load_config(config["source"]["baseline_config"])
    batch_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("boundary_batch_%Y%m%d_%H%M%S")
    )
    batch_dir.mkdir(parents=True, exist_ok=False)

    print("========== DAY 25 REVIEWED BOUNDARY SCAN ==========")
    print(f"Approved by zero-offset control: {baseline_file}")
    print(f"Batch directory: {batch_dir}")
    print("Nine new points run sequentially; optical failures stop the batch.")
    print("An acceptance FAIL is recorded and does not stop the batch.")
    print("Quick Focus, optimization and SaveAs are forbidden.")

    rows = []
    case_reports = []
    for case in cases:
        case_dir = batch_dir / case["case_id"]
        print(f"\nRunning {case['case_id']} at {case['offset_mm']:+.3f} mm...")
        result, result_file = execute_case(
            config,
            baseline,
            case,
            case_dir,
            model_file,
            task_name="day25_boundary_case",
            report_name="boundary_case_report.json",
        )
        metrics = observed_summary(result)
        checks, passed, failed = evaluate_balanced(config, metrics)
        result["summary_metrics"] = metrics
        result["balanced_acceptance_checks"] = checks
        result["balanced_acceptance_pass"] = passed
        result["failed_metrics"] = failed
        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        rows.append(flatten_result(case, metrics, checks, passed, failed, result_file))
        case_reports.append(str(result_file))
        print(
            f"[PASS] Optical analysis; acceptance={'PASS' if passed else 'FAIL'}"
            + (f" ({', '.join(failed)})" if failed else "")
        )
        print(
            f"  Spot mean/worst={metrics['spot_mean_rms_um']:.6f}/"
            f"{metrics['spot_worst_rms_um']:.6f} um"
        )
        print(
            f"  MTF30 mean/min={metrics['mtf30_mean']:.6f}/"
            f"{metrics['mtf30_minimum']:.6f}"
        )
        print(
            f"  MTF50 mean/min={metrics['mtf50_mean']:.6f}/"
            f"{metrics['mtf50_minimum']:.6f}"
        )
        print("  [PASS] Connection closed; input and disk copy unchanged")

    csv_file = batch_dir / "boundary_scan_results.csv"
    report_file = batch_dir / "boundary_scan_batch_report.json"
    write_csv(csv_file, rows)
    batch_report = {
        "task": "day25_boundary_scan_batch",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day24_report": str(day24_file),
        "approved_baseline_report": str(baseline_file),
        "source_model": str(model_file),
        "source_sha256": config["source"]["focused_model_sha256"],
        "case_count": len(rows),
        "rows": rows,
        "case_reports": case_reports,
        "acceptance_pass_count": sum(row["balanced_acceptance_pass"] for row in rows),
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "interpolation_used": False,
        "continuous_tolerance_claimed": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(batch_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n========== DAY 25 BOUNDARY-SCAN SUMMARY ==========")
    for row in rows:
        print(
            f"{row['case_id']}: offset={row['offset_mm']:+.3f} mm -> "
            f"{'PASS' if row['balanced_acceptance_pass'] else 'FAIL'}"
            + (f" ({row['failed_metrics']})" if row["failed_metrics"] else "")
        )
    print(f"[PASS] Successful optical cases: {len(rows)}")
    print(f"[RESULT] Balanced acceptance passes: "
          f"{sum(row['balanced_acceptance_pass'] for row in rows)}/{len(rows)}")
    print("[PASS] All connections closed and disk models remained unchanged")
    print("[PASS] No Quick Focus, optimization or model save was used")
    print("[RESULT] Continuous tolerance: NOT CLAIMED")
    print(f"[PASS] Results CSV: {csv_file}")
    print(f"[PASS] Batch report: {report_file}")


if __name__ == "__main__":
    main()
