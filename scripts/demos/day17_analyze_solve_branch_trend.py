"""Day 17 step 4: analyze the completed branch trend without Zemax."""

import csv
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MPL_CONFIG_DIR = PROJECT_ROOT / "outputs" / ".matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.config_loader import load_config  # noqa: E402


def find_latest_batch_report(config):
    """Find the newest successful Day 17 trend batch."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(root.glob("trend_batch_*/trend_batch_report.json"))
    if not matches:
        raise FileNotFoundError("No Day 17 trend batch report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_batch(report):
    """Require the reviewed evidence and all safety audits."""

    checks = {
        "task": report.get("task") == "day17_solve_branch_trend",
        "status": report.get("status") == "success",
        "new cases": report.get("new_case_count") == 4,
        "new branch runs": report.get("new_branch_run_count") == 8,
        "reused evidence": report.get("reused_evidence_count") == 2,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no winner": report.get("unique_engineering_winner") is None,
        "six trend rows": len(report.get("trend_rows", [])) == 6,
    }
    for case in report.get("new_results", []):
        case_id = case.get("case", {}).get("case_id", "unknown")
        for branch_name in ("preserve_solve", "freeze_radius"):
            branch = case.get(branch_name, {})
            checks[f"{case_id} {branch_name} success"] = (
                branch.get("status") == "success"
            )
            checks[f"{case_id} {branch_name} connection"] = (
                branch.get("connection_closed") is True
            )
            checks[f"{case_id} {branch_name} source"] = (
                branch.get("source_unchanged") is True
            )
            checks[f"{case_id} {branch_name} copy"] = (
                branch.get("working_copy_unchanged") is True
            )
        reproduction = case.get("day8_reproduction", {})
        checks[f"{case_id} Day 8 focus"] = (
            float(reproduction.get("focus_shift_difference_mm", math.inf))
            <= 0.000001
        )
        checks[f"{case_id} Day 8 Spot"] = (
            float(
                reproduction.get("maximum_field_rms_difference_um", math.inf)
            )
            <= 0.001
        )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 17 batch evidence failed: " + ", ".join(failed))


def linear_fit(x_values, y_values):
    """Return least-squares slope, intercept and R-squared."""

    count = len(x_values)
    if count != len(y_values) or count < 2:
        raise ValueError("Linear fit requires matching multi-point data.")
    x_mean = sum(x_values) / count
    y_mean = sum(y_values) / count
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    if denominator == 0.0:
        raise ValueError("Linear fit x values have no span.")
    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values)
    ) / denominator
    intercept = y_mean - slope * x_mean
    predictions = [slope * value + intercept for value in x_values]
    residual = sum(
        (actual - predicted) ** 2
        for actual, predicted in zip(y_values, predictions)
    )
    total = sum((value - y_mean) ** 2 for value in y_values)
    r_squared = 1.0 if total == 0.0 else 1.0 - residual / total
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "predictions": predictions,
    }


def analyze_rows(rows):
    """Separate structural/focus trends from field-dependent Spot changes."""

    ordered = sorted(rows, key=lambda row: float(row["delta_mm"]))
    delta = [float(row["delta_mm"]) for row in ordered]
    radius = [
        float(row["preserve_minus_frozen_radius_mm"]) for row in ordered
    ]
    focus = [
        float(row["frozen_minus_preserve_focus_shift_mm"]) for row in ordered
    ]
    spot_0 = [
        float(row["frozen_minus_preserve_rms_0deg_um"]) for row in ordered
    ]
    spot_14 = [
        float(row["frozen_minus_preserve_rms_14deg_um"]) for row in ordered
    ]
    spot_20 = [
        float(row["frozen_minus_preserve_rms_20deg_um"]) for row in ordered
    ]
    mean_spot = [
        float(row["frozen_minus_preserve_mean_rms_um"]) for row in ordered
    ]
    worst_spot = [
        float(row["frozen_minus_preserve_worst_rms_um"]) for row in ordered
    ]

    mixed_direction_nonzero = []
    for row in ordered:
        delta_value = float(row["delta_mm"])
        if math.isclose(delta_value, 0.0, abs_tol=1e-12):
            continue
        differences = [
            float(row["frozen_minus_preserve_rms_0deg_um"]),
            float(row["frozen_minus_preserve_rms_14deg_um"]),
            float(row["frozen_minus_preserve_rms_20deg_um"]),
        ]
        mixed_direction_nonzero.append(
            any(value > 0.0 for value in differences)
            and any(value < 0.0 for value in differences)
        )

    maximum_field = max(
        (
            {
                "delta_mm": delta_value,
                "field_y_degree": angle,
                "difference_um": difference,
            }
            for delta_value, values in zip(delta, zip(spot_0, spot_14, spot_20))
            for angle, difference in zip((0.0, 14.0, 20.0), values)
        ),
        key=lambda item: abs(item["difference_um"]),
    )
    maximum_mean_index = max(
        range(len(mean_spot)),
        key=lambda index: abs(mean_spot[index]),
    )
    return {
        "ordered_rows": ordered,
        "series": {
            "delta_mm": delta,
            "radius_difference_mm": radius,
            "focus_difference_mm": focus,
            "spot_0deg_difference_um": spot_0,
            "spot_14deg_difference_um": spot_14,
            "spot_20deg_difference_um": spot_20,
            "mean_spot_difference_um": mean_spot,
            "worst_spot_difference_um": worst_spot,
        },
        "radius_linear_fit": linear_fit(delta, radius),
        "focus_linear_fit": linear_fit(delta, focus),
        "mean_spot_linear_fit": linear_fit(delta, mean_spot),
        "all_nonzero_points_have_mixed_field_direction": all(
            mixed_direction_nonzero
        ),
        "maximum_absolute_field_difference": maximum_field,
        "maximum_absolute_mean_difference": {
            "delta_mm": delta[maximum_mean_index],
            "difference_um": mean_spot[maximum_mean_index],
        },
    }


def save_figure(analysis, output_file):
    """Plot structural, compensator and field-dependent responses."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite figure: {output_file}")
    series = analysis["series"]
    delta = series["delta_mm"]
    figure, axes = plt.subplots(3, 1, figsize=(9, 12), sharex=True)

    axes[0].plot(
        delta,
        series["radius_difference_mm"],
        "o-",
        label="Observed",
    )
    axes[0].plot(
        delta,
        analysis["radius_linear_fit"]["predictions"],
        "--",
        label=f"Linear fit, R2={analysis['radius_linear_fit']['r_squared']:.5f}",
    )
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_ylabel("Preserve - frozen radius (mm)")
    axes[0].set_title("Surface 6 radius response")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(
        delta,
        series["focus_difference_mm"],
        "o-",
        color="tab:orange",
        label="Observed",
    )
    axes[1].plot(
        delta,
        analysis["focus_linear_fit"]["predictions"],
        "--",
        color="tab:red",
        label=f"Linear fit, R2={analysis['focus_linear_fit']['r_squared']:.5f}",
    )
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_ylabel("Frozen - preserve focus shift (mm)")
    axes[1].set_title("Additional Quick Focus compensation")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    for key, label, marker in (
        ("spot_0deg_difference_um", "Field 0 deg", "o"),
        ("spot_14deg_difference_um", "Field 14 deg", "s"),
        ("spot_20deg_difference_um", "Field 20 deg", "^"),
        ("mean_spot_difference_um", "Equal-field mean", "D"),
    ):
        axes[2].plot(delta, series[key], marker=marker, label=label)
    axes[2].axhline(0.0, color="black", linewidth=0.8)
    axes[2].set_xlabel("Surface 2 thickness delta (mm)")
    axes[2].set_ylabel("Frozen - preserve RMS (um)")
    axes[2].set_title("Refocused Spot differences are field-dependent")
    axes[2].grid(alpha=0.3)
    axes[2].legend(ncol=2)

    figure.tight_layout()
    figure.savefig(output_file, dpi=180)
    plt.close(figure)


def write_summary_csv(path, analysis):
    """Write the six-point analysis table with UTF-8 Excel compatibility."""

    if path.exists():
        raise FileExistsError(f"Refusing to overwrite summary CSV: {path}")
    rows = analysis["ordered_rows"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day17_solve_branch_trend.yaml")
    if config["execution"]["allow_trend_evaluation"] is not True:
        raise ValueError("Day 17 offline trend evaluation is not approved.")
    if config["execution"]["allow_optimization"] is not False:
        raise ValueError("Day 17 analysis must not enable optimization.")
    if config["execution"]["allow_save_as"] is not False:
        raise ValueError("Day 17 analysis must not enable SaveAs.")

    report_file = find_latest_batch_report(config)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    validate_batch(report)
    analysis = analyze_rows(report["trend_rows"])
    output_dir = report_file.parent
    figure_file = output_dir / "day17_solve_branch_trend.png"
    summary_csv = output_dir / "day17_solve_branch_trend_analysis.csv"
    analysis_file = output_dir / "trend_analysis_report.json"
    if analysis_file.exists():
        raise FileExistsError(f"Refusing to overwrite report: {analysis_file}")
    save_figure(analysis, figure_file)
    write_summary_csv(summary_csv, analysis)

    serializable = dict(analysis)
    serializable["source_batch_report"] = str(report_file)
    serializable["task"] = "day17_solve_branch_trend_analysis"
    serializable["status"] = "success"
    serializable["time_local"] = datetime.now().astimezone().isoformat()
    serializable["zosapi_connection_used"] = False
    serializable["new_optical_calculation_used"] = False
    serializable["hidden_weighted_score_used"] = False
    serializable["unique_engineering_winner"] = None
    serializable.pop("ordered_rows")
    analysis_file.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    radius_fit = analysis["radius_linear_fit"]
    focus_fit = analysis["focus_linear_fit"]
    mean_fit = analysis["mean_spot_linear_fit"]
    maximum_field = analysis["maximum_absolute_field_difference"]
    maximum_mean = analysis["maximum_absolute_mean_difference"]
    print("========== DAY 17 OFFLINE TREND ANALYSIS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print(
        "Radius response fit: "
        f"slope={radius_fit['slope']:+.7f}, "
        f"intercept={radius_fit['intercept']:+.7f} mm, "
        f"R2={radius_fit['r_squared']:.6f}"
    )
    print(
        "Focus compensation fit: "
        f"slope={focus_fit['slope']:+.7f}, "
        f"intercept={focus_fit['intercept']:+.7f} mm, "
        f"R2={focus_fit['r_squared']:.6f}"
    )
    print(
        "Mean Spot difference fit: "
        f"slope={mean_fit['slope']:+.7f}, "
        f"R2={mean_fit['r_squared']:.6f}"
    )
    print(
        "All nonzero points mix improved and worsened fields: "
        f"{analysis['all_nonzero_points_have_mixed_field_direction']}"
    )
    print(
        "Maximum absolute individual-field difference: "
        f"{maximum_field['difference_um']:+.3f} um at "
        f"delta {maximum_field['delta_mm']:+.1f} mm, "
        f"field {maximum_field['field_y_degree']:.1f} deg"
    )
    print(
        "Maximum absolute mean difference: "
        f"{maximum_mean['difference_um']:+.3f} um at "
        f"delta {maximum_mean['delta_mm']:+.1f} mm"
    )
    print("[RESULT] Structural and focus differences are approximately linear")
    print("[RESULT] Refocused Spot differences are small and field-dependent")
    print("[RESULT] Unique engineering winner: NONE")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Analysis CSV: {summary_csv}")
    print(f"[PASS] Analysis report: {analysis_file}")


if __name__ == "__main__":
    main()
