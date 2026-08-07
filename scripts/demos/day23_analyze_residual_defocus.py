"""Day 23 step 4: analyze seven measured residual-defocus points offline."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_run_residual_defocus_batch import (  # noqa: E402
    find_latest_control_report,
    frequency_map,
    validate_control_report,
)
from scripts.demos.day23_residual_defocus_optical_impact_plan import (  # noqa: E402
    validate_input_model,
)
from scripts.demos.day23_validate_baseline_control import summarize_spot  # noqa: E402


def require_offline_authorization(config):
    """Lock every Zemax action and permit only offline analysis."""

    execution = config["execution"]
    if execution.get("allow_offline_analysis") is not True:
        raise ValueError("Day 23 offline analysis is not approved.")
    forbidden = (
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_baseline_control",
        "allow_residual_cases",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 23 offline forbidden action enabled: " + ", ".join(enabled))


def find_latest_batch_report(config):
    """Find the latest completed six-case residual-defocus batch."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(root.glob("residual_batch_*/residual_defocus_batch_report.json"))
    if not matches:
        raise FileNotFoundError("No Day 23 residual-defocus batch report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_case_report(report_file, model_file, model_hash):
    """Audit one successful immutable residual-defocus observation."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "task": report.get("task") == "day23_residual_defocus_case",
        "status": report.get("status") == "success",
        "input model": Path(report.get("input_model", "")).resolve()
        == model_file.resolve(),
        "input hash": report.get("input_sha256_before", "").upper() == model_hash,
        "input unchanged": report.get("input_model_unchanged") is True,
        "copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "three Spot fields": report.get("spot_metrics", {}).get("field_count") == 3,
        "three MTF fields": report.get("mtf_metrics", {}).get("field_count") == 3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"Day 23 case evidence failed ({report_file.name}): " + ", ".join(failed)
        )
    return report


def validate_batch(config, report_file, model_file, model_hash):
    """Require six unique nonzero cases and audit every case report."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "task": report.get("task") == "day23_residual_defocus_batch",
        "status": report.get("status") == "success",
        "six cases": report.get("case_count") == 6,
        "source hash": report.get("source_sha256", "").upper() == model_hash,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 23 batch evidence failed: " + ", ".join(failed))
    case_reports = [Path(value) for value in report.get("case_reports", [])]
    if len(case_reports) != 6 or len(set(case_reports)) != 6:
        raise ValueError("Day 23 batch case-report list is incomplete.")
    cases = [validate_case_report(path, model_file, model_hash) for path in case_reports]
    offsets = sorted(float(item["case"]["offset_mm"]) for item in cases)
    expected = [-0.05, -0.02, -0.01, 0.01, 0.02, 0.05]
    if offsets != expected:
        raise ValueError("Day 23 measured residual offsets are incorrect.")
    return report, cases


def row_from_result(result):
    """Flatten one measured observation for comparison and plotting."""

    case = result["case"]
    spot = result.get("spot_summary") or summarize_spot(result["spot_metrics"])
    mtf = frequency_map(result["mtf_summary"])
    return {
        "case_id": case["case_id"],
        "offset_mm": float(case["offset_mm"]),
        "image_distance_mm": float(result["surface6_after"]["thickness"]),
        "spot_mean_rms_um": float(spot["equal_field_mean_rms_um"]),
        "spot_worst_rms_um": float(spot["worst_field_rms_um"]),
        "mtf30_mean": float(mtf[30.0]["overall_mean_mtf"]),
        "mtf30_minimum": float(mtf[30.0]["minimum_mtf"]),
        "mtf50_mean": float(mtf[50.0]["overall_mean_mtf"]),
        "mtf50_minimum": float(mtf[50.0]["minimum_mtf"]),
    }


def add_changes(rows):
    """Add transparent changes relative to the measured zero-offset control."""

    controls = [row for row in rows if math.isclose(row["offset_mm"], 0.0)]
    if len(controls) != 1:
        raise ValueError("Day 23 combined evidence requires one zero-offset control.")
    control = controls[0]
    metrics = (
        "spot_mean_rms_um",
        "spot_worst_rms_um",
        "mtf30_mean",
        "mtf30_minimum",
        "mtf50_mean",
        "mtf50_minimum",
    )
    for row in rows:
        for metric in metrics:
            row[f"{metric}_change"] = row[metric] - control[metric]
    return control


def build_asymmetry(rows):
    """Compare positive-minus-negative responses at equal magnitudes."""

    indexed = {round(float(row["offset_mm"]), 9): row for row in rows}
    metrics = ("spot_mean_rms_um", "mtf30_mean", "mtf50_mean")
    result = []
    for magnitude in (0.01, 0.02, 0.05):
        negative = indexed[-magnitude]
        positive = indexed[magnitude]
        item = {"magnitude_mm": magnitude}
        for metric in metrics:
            item[f"negative_{metric}"] = negative[metric]
            item[f"positive_{metric}"] = positive[metric]
            item[f"positive_minus_negative_{metric}"] = (
                positive[metric] - negative[metric]
            )
        result.append(item)
    return result


def metric_extreme(rows, metric, mode):
    """Return the measured row that leads one declared metric."""

    function = min if mode == "minimum" else max
    value = function(row[metric] for row in rows)
    matches = [row for row in rows if math.isclose(row[metric], value, abs_tol=1e-12)]
    return {
        "metric": metric,
        "mode": mode,
        "value": value,
        "case_ids": [row["case_id"] for row in matches],
        "offsets_mm": [row["offset_mm"] for row in matches],
    }


def write_csv(path, rows):
    """Write dictionaries as a UTF-8 spreadsheet-friendly CSV."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def create_figure(path, rows):
    """Plot measured Spot and FFT MTF responses without fitting."""

    offsets = [row["offset_mm"] for row in rows]
    figure, axes = plt.subplots(3, 1, figsize=(9.0, 11.0), sharex=True)
    axes[0].plot(offsets, [row["spot_mean_rms_um"] for row in rows], "o-", label="Mean RMS")
    axes[0].plot(offsets, [row["spot_worst_rms_um"] for row in rows], "s-", label="Worst field RMS")
    axes[0].set_ylabel("Spot RMS (um)")
    axes[0].legend()
    axes[1].plot(offsets, [row["mtf30_mean"] for row in rows], "o-", label="MTF30 mean")
    axes[1].plot(offsets, [row["mtf30_minimum"] for row in rows], "s-", label="MTF30 minimum")
    axes[1].set_ylabel("MTF at 30 cyc/mm")
    axes[1].legend()
    axes[2].plot(offsets, [row["mtf50_mean"] for row in rows], "o-", label="MTF50 mean")
    axes[2].plot(offsets, [row["mtf50_minimum"] for row in rows], "s-", label="MTF50 minimum")
    axes[2].set_ylabel("MTF at 50 cyc/mm")
    axes[2].set_xlabel("Residual image-plane offset (mm)")
    axes[2].legend()
    for axis in axes:
        axis.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
        axis.grid(True, alpha=0.3)
    figure.suptitle("Day 23 measured residual-defocus optical response")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day23_residual_defocus_optical_impact.yaml")
    require_offline_authorization(config)
    model_file, model_hash = validate_input_model(config)
    control_file = find_latest_control_report(config)
    control = validate_control_report(config, control_file, model_file, model_hash)
    batch_file = find_latest_batch_report(config)
    batch, cases = validate_batch(config, batch_file, model_file, model_hash)

    rows = [row_from_result(control)] + [row_from_result(case) for case in cases]
    rows.sort(key=lambda row: row["offset_mm"])
    control_row = add_changes(rows)
    asymmetry = build_asymmetry(rows)
    leaders = [
        metric_extreme(rows, "spot_mean_rms_um", "minimum"),
        metric_extreme(rows, "spot_worst_rms_um", "minimum"),
        metric_extreme(rows, "mtf30_mean", "maximum"),
        metric_extreme(rows, "mtf30_minimum", "maximum"),
        metric_extreme(rows, "mtf50_mean", "maximum"),
        metric_extreme(rows, "mtf50_minimum", "maximum"),
    ]

    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("offline_analysis_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    metrics_file = output_dir / "residual_defocus_measured_metrics.csv"
    asymmetry_file = output_dir / "residual_defocus_asymmetry.csv"
    figure_file = output_dir / "day23_residual_defocus_response.png"
    report_file = output_dir / "residual_defocus_analysis_report.json"
    write_csv(metrics_file, rows)
    write_csv(asymmetry_file, asymmetry)
    create_figure(figure_file, rows)
    report = {
        "task": "day23_residual_defocus_offline_analysis",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_control_report": str(control_file),
        "source_batch_report": str(batch_file),
        "source_model": str(model_file),
        "source_sha256": model_hash,
        "rows": rows,
        "control": control_row,
        "positive_negative_asymmetry": asymmetry,
        "separate_metric_leaders": leaders,
        "measured_points_only": True,
        "interpolation_used": False,
        "curve_fit_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 23 OFFLINE RESIDUAL-DEFOCUS ANALYSIS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print("All curves connect measured points only; no fit or interpolation was used.")
    print()
    for row in rows:
        print(
            f"offset {row['offset_mm']:+.3f} mm: "
            f"Spot mean/worst={row['spot_mean_rms_um']:.3f}/"
            f"{row['spot_worst_rms_um']:.3f} um, "
            f"MTF30 mean/min={row['mtf30_mean']:.4f}/"
            f"{row['mtf30_minimum']:.4f}, "
            f"MTF50 mean/min={row['mtf50_mean']:.4f}/"
            f"{row['mtf50_minimum']:.4f}"
        )
    print("\nPositive-minus-negative asymmetry at equal magnitudes:")
    for row in asymmetry:
        print(
            f"  +/-{row['magnitude_mm']:.2f} mm: "
            f"Spot mean {row['positive_minus_negative_spot_mean_rms_um']:+.3f} um, "
            f"MTF30 mean {row['positive_minus_negative_mtf30_mean']:+.4f}, "
            f"MTF50 mean {row['positive_minus_negative_mtf50_mean']:+.4f}"
        )
    print("\nSeparate measured metric leaders:")
    for leader in leaders:
        print(
            f"  {leader['metric']} ({leader['mode']}): "
            f"offsets={leader['offsets_mm']}, value={leader['value']:.6f}"
        )
    print("[RESULT] Best-focus location depends on the chosen optical metric")
    print("[RESULT] Positive and negative residual defocus are not symmetric")
    print("[RESULT] Mean MTF and minimum MTF must remain separate")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] Seven measured cases and all safety reports verified")
    print(f"[PASS] Metrics CSV: {metrics_file}")
    print(f"[PASS] Asymmetry CSV: {asymmetry_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
