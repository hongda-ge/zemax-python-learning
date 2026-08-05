"""Day 8 step 4: analyze the latest local fine scan without Zemax."""

import csv
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "day8_local_fine_scan"
MATPLOTLIB_CACHE = PROJECT_ROOT / "outputs" / ".matplotlib_cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


PLATEAU_RELATIVE_LIMIT = 0.05


def find_latest_batch_summary():
    """Return the newest completed Day 8 fine-scan summary."""

    candidates = list(OUTPUT_ROOT.glob("fine_scan_*/batch_summary.json"))
    if not candidates:
        raise FileNotFoundError("No Day 8 fine-scan batch summary was found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_successful_rows(summary_file):
    """Require nine successful, ordered fine-scan cases."""

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    rows = summary["rows"]
    if len(rows) != 9:
        raise ValueError(f"Expected 9 Day 8 rows, found {len(rows)}.")

    unsuccessful = [row["case_id"] for row in rows if row["status"] != "success"]
    if unsuccessful:
        raise ValueError(
            "Local robustness analysis requires nine successful cases: "
            + ", ".join(unsuccessful)
        )

    values = [row["value_mm"] for row in rows]
    if values != sorted(values):
        raise ValueError("Day 8 thickness values are not ordered.")
    return summary, rows


def add_robustness_metrics(rows):
    """Calculate transparent descriptive metrics for each design point."""

    for row in rows:
        rms_values = [
            row["rms_0deg_um"],
            row["rms_14deg_um"],
            row["rms_20deg_um"],
        ]
        row["mean_rms_um"] = sum(rms_values) / len(rms_values)
        row["worst_field_rms_um"] = max(rms_values)

    best = min(rows, key=lambda row: row["mean_rms_um"])
    plateau_limit = best["mean_rms_um"] * (1.0 + PLATEAU_RELATIVE_LIMIT)
    plateau_rows = [
        row for row in rows if row["mean_rms_um"] <= plateau_limit
    ]

    for row in rows:
        row["within_5_percent_plateau"] = row in plateau_rows
        row["mean_rms_relative_to_best_percent"] = (
            row["mean_rms_um"] / best["mean_rms_um"] - 1.0
        ) * 100.0

    return best, plateau_rows, plateau_limit


def fit_focus_line(rows):
    """Fit focus shift = slope * thickness + intercept using least squares."""

    x_values = [row["value_mm"] for row in rows]
    y_values = [row["focus_shift_mm"] for row in rows]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values)
    ) / denominator
    intercept = y_mean - slope * x_mean
    predicted = [slope * value + intercept for value in x_values]
    residual_sum = sum(
        (actual - estimate) ** 2
        for actual, estimate in zip(y_values, predicted)
    )
    total_sum = sum((actual - y_mean) ** 2 for actual in y_values)
    r_squared = 1.0 - residual_sum / total_sum
    return {
        "slope_mm_focus_per_mm_thickness": slope,
        "intercept_mm": intercept,
        "r_squared": r_squared,
        "predicted_focus_shift_mm": predicted,
    }


def write_analysis_csv(batch_dir, rows):
    """Write the calculated local-robustness metrics."""

    columns = [
        "case_id",
        "value_mm",
        "delta_mm",
        "focus_shift_mm",
        "rms_0deg_um",
        "rms_14deg_um",
        "rms_20deg_um",
        "mean_rms_um",
        "worst_field_rms_um",
        "mean_rms_relative_to_best_percent",
        "within_5_percent_plateau",
    ]
    output_file = batch_dir / "day8_local_robustness.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in rows)
    return output_file


def plot_results(batch_dir, rows, best, plateau_rows, focus_fit):
    """Plot field trade-offs, the near-best plateau, and focus sensitivity."""

    x_values = [row["value_mm"] for row in rows]
    plateau_min = plateau_rows[0]["value_mm"]
    plateau_max = plateau_rows[-1]["value_mm"]
    baseline = next(row for row in rows if row["is_baseline"])

    figure, axes = plt.subplots(3, 1, figsize=(9, 12), sharex=True)
    field_axis, balance_axis, focus_axis = axes

    field_specs = [
        ("rms_0deg_um", "Field 0 deg", "o"),
        ("rms_14deg_um", "Field 14 deg", "s"),
        ("rms_20deg_um", "Field 20 deg", "^"),
    ]
    for key, label, marker in field_specs:
        field_axis.plot(
            x_values,
            [row[key] for row in rows],
            marker=marker,
            linewidth=2,
            label=label,
        )
    field_axis.axvline(
        baseline["value_mm"],
        color="gray",
        linewidth=1,
        linestyle="--",
        label="Baseline",
    )
    field_axis.set_ylabel("RMS spot radius (um)")
    field_axis.set_title("Local field trade-off")
    field_axis.grid(True, alpha=0.3)
    field_axis.legend()

    balance_axis.axvspan(
        plateau_min,
        plateau_max,
        color="tab:green",
        alpha=0.12,
        label="Within 5% of best mean RMS",
    )
    balance_axis.plot(
        x_values,
        [row["mean_rms_um"] for row in rows],
        marker="o",
        linewidth=2,
        label="Equal-field mean RMS",
    )
    balance_axis.plot(
        x_values,
        [row["worst_field_rms_um"] for row in rows],
        marker="s",
        linewidth=2,
        label="Worst-field RMS",
    )
    balance_axis.scatter(
        best["value_mm"],
        best["mean_rms_um"],
        marker="*",
        s=220,
        color="gold",
        edgecolor="black",
        zorder=5,
        label=f"Best sampled mean: {best['case_id']}",
    )
    balance_axis.set_ylabel("Descriptive RMS metric (um)")
    balance_axis.set_title("Near-best local plateau")
    balance_axis.grid(True, alpha=0.3)
    balance_axis.legend()

    focus_axis.plot(
        x_values,
        [row["focus_shift_mm"] for row in rows],
        marker="o",
        linewidth=2,
        label="Quick Focus shift",
    )
    focus_axis.plot(
        x_values,
        focus_fit["predicted_focus_shift_mm"],
        linewidth=1.5,
        linestyle="--",
        label=(
            "Linear fit: "
            f"slope {focus_fit['slope_mm_focus_per_mm_thickness']:.3f}"
        ),
    )
    focus_axis.axhline(0.0, color="gray", linewidth=1)
    focus_axis.set_xlabel("Surface 2 thickness (mm)")
    focus_axis.set_ylabel("Focus shift (mm)")
    focus_axis.set_title(
        f"Focus sensitivity (R squared = {focus_fit['r_squared']:.5f})"
    )
    focus_axis.set_xticks(x_values)
    focus_axis.grid(True, alpha=0.3)
    focus_axis.legend()

    figure.suptitle("Day 8 Local Thickness Robustness", fontsize=14)
    figure.tight_layout()
    output_file = batch_dir / "day8_local_robustness.png"
    figure.savefig(output_file, dpi=220)
    plt.close(figure)
    return output_file


def write_report(
    batch_dir,
    summary,
    best,
    plateau_rows,
    plateau_limit,
    focus_fit,
):
    """Record the decision rule and its limitations."""

    report = {
        "task": "day8_local_robustness_analysis",
        "source_batch": summary["batch_id"],
        "selection_metric": "equal-field arithmetic mean RMS spot radius",
        "best_sampled_case": best["case_id"],
        "best_sampled_thickness_mm": best["value_mm"],
        "best_mean_rms_um": best["mean_rms_um"],
        "best_worst_field_rms_um": best["worst_field_rms_um"],
        "plateau_rule": "mean RMS no more than 5 percent above sampled best",
        "plateau_limit_mean_rms_um": plateau_limit,
        "plateau_case_ids": [row["case_id"] for row in plateau_rows],
        "plateau_min_thickness_mm": plateau_rows[0]["value_mm"],
        "plateau_max_thickness_mm": plateau_rows[-1]["value_mm"],
        "sampled_plateau_width_mm": (
            plateau_rows[-1]["value_mm"] - plateau_rows[0]["value_mm"]
        ),
        "focus_sensitivity": {
            "slope_mm_focus_per_mm_thickness": focus_fit[
                "slope_mm_focus_per_mm_thickness"
            ],
            "r_squared": focus_fit["r_squared"],
        },
        "warning": (
            "The 5 percent plateau is a project decision rule, not a Zemax "
            "merit function and not a manufacturing tolerance specification."
        ),
    }
    output_file = batch_dir / "day8_local_robustness_report.json"
    output_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_file


def main():
    summary_file = find_latest_batch_summary()
    summary, rows = load_successful_rows(summary_file)
    best, plateau_rows, plateau_limit = add_robustness_metrics(rows)
    focus_fit = fit_focus_line(rows)
    batch_dir = summary_file.parent

    csv_file = write_analysis_csv(batch_dir, rows)
    figure_file = plot_results(
        batch_dir,
        rows,
        best,
        plateau_rows,
        focus_fit,
    )
    report_file = write_report(
        batch_dir,
        summary,
        best,
        plateau_rows,
        plateau_limit,
        focus_fit,
    )

    print("========== DAY 8 LOCAL ROBUSTNESS ANALYSIS ==========")
    for row in rows:
        plateau_mark = " <- within 5% plateau" if row[
            "within_5_percent_plateau"
        ] else ""
        print(
            f"{row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"mean RMS={row['mean_rms_um']:.3f} um, "
            f"worst field={row['worst_field_rms_um']:.3f} um"
            f"{plateau_mark}"
        )

    print()
    print(
        f"[RESULT] Best sampled mean RMS: {best['case_id']} at "
        f"{best['value_mm']:.7f} mm"
    )
    print(
        f"[RESULT] Sampled 5% plateau: "
        f"{plateau_rows[0]['value_mm']:.7f} to "
        f"{plateau_rows[-1]['value_mm']:.7f} mm"
    )
    print(
        f"[RESULT] Focus sensitivity: "
        f"{focus_fit['slope_mm_focus_per_mm_thickness']:+.4f} "
        "mm/mm"
    )
    print(f"[PASS] Analysis CSV: {csv_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")
    print("No ZOS-API connection was created.")


if __name__ == "__main__":
    main()
