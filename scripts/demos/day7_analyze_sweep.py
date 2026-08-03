"""Day 7: analyze the latest five-case sweep without opening Zemax."""

import csv
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SWEEP_ROOT = PROJECT_ROOT / "outputs" / "day7_five_case_sweep"
MATPLOTLIB_CACHE = PROJECT_ROOT / "outputs" / ".matplotlib_cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def find_latest_summary():
    """Return the newest completed five-case batch summary."""

    candidates = list(SWEEP_ROOT.glob("five_case_*/batch_summary.json"))
    if not candidates:
        raise FileNotFoundError(
            "No Day 7 batch_summary.json was found under outputs."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_rows(summary_file):
    """Load and validate the five planned design records."""

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    rows = summary["rows"]
    if len(rows) != 5:
        raise ValueError(f"Expected 5 Day 7 cases, found {len(rows)}.")

    for row in rows:
        if row["status"] not in {"success", "rejected"}:
            raise ValueError(
                f"{row['case_id']} has unresolved status: {row['status']}"
            )

    return summary, rows


def add_comparison_metrics(rows):
    """Add descriptive metrics only to optically valid cases."""

    valid_rows = []
    for row in rows:
        row["mean_rms_um"] = None
        row["worst_field_rms_um"] = None
        row["best_balanced_case"] = False

        if row["status"] != "success":
            continue

        rms_values = [
            row["rms_0deg_um"],
            row["rms_14deg_um"],
            row["rms_20deg_um"],
        ]
        row["mean_rms_um"] = sum(rms_values) / len(rms_values)
        row["worst_field_rms_um"] = max(rms_values)
        valid_rows.append(row)

    if not valid_rows:
        raise ValueError("No successful optical case is available to analyze.")

    best = min(
        valid_rows,
        key=lambda row: (row["mean_rms_um"], row["worst_field_rms_um"]),
    )
    best["best_balanced_case"] = True
    return valid_rows, best


def write_analysis_table(batch_dir, rows):
    """Write one compact table for later plotting or spreadsheet study."""

    columns = [
        "case_id",
        "status",
        "value_mm",
        "delta_mm",
        "is_baseline",
        "focused_image_distance_mm",
        "rms_0deg_um",
        "rms_14deg_um",
        "rms_20deg_um",
        "mean_rms_um",
        "worst_field_rms_um",
        "best_balanced_case",
        "rejection_reason",
    ]
    output_file = batch_dir / "day7_analysis.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in rows)
    return output_file


def plot_analysis(batch_dir, rows, valid_rows, best):
    """Plot field trade-offs, focus feasibility, and balanced metrics."""

    valid_x = [row["value_mm"] for row in valid_rows]
    all_x = [row["value_mm"] for row in rows]
    rejected = [row for row in rows if row["status"] == "rejected"]

    figure, axes = plt.subplots(3, 1, figsize=(9, 12), sharex=True)
    rms_axis, focus_axis, balance_axis = axes

    field_specs = [
        ("rms_0deg_um", "Field 0 deg", "o"),
        ("rms_14deg_um", "Field 14 deg", "s"),
        ("rms_20deg_um", "Field 20 deg", "^"),
    ]
    for key, label, marker in field_specs:
        rms_axis.plot(
            valid_x,
            [row[key] for row in valid_rows],
            marker=marker,
            linewidth=2,
            label=label,
        )
    for row in rejected:
        rms_axis.scatter(
            row["value_mm"],
            0.96,
            marker="x",
            s=90,
            color="crimson",
            transform=rms_axis.get_xaxis_transform(),
            clip_on=False,
        )
        rms_axis.annotate(
            "Spot not evaluated\n(focus rejected)",
            (row["value_mm"], 0.96),
            xycoords=rms_axis.get_xaxis_transform(),
            xytext=(-110, -15),
            textcoords="offset points",
            color="crimson",
        )
    rms_axis.set_ylabel("RMS spot radius (um)")
    rms_axis.set_title("Field performance trade-off")
    rms_axis.grid(True, alpha=0.3)
    rms_axis.legend()

    focus_rows = [
        row
        for row in rows
        if row.get("focused_image_distance_mm") is not None
    ]
    focus_axis.plot(
        [row["value_mm"] for row in focus_rows],
        [row["focused_image_distance_mm"] for row in focus_rows],
        marker="o",
        linewidth=2,
        color="tab:purple",
        label="Focused image distance",
    )
    focus_axis.axhspan(40.0, 44.5, color="tab:green", alpha=0.12)
    focus_axis.axhline(40.0, color="tab:green", linestyle="--", linewidth=1)
    focus_axis.axhline(44.5, color="tab:green", linestyle="--", linewidth=1)
    for row in rejected:
        if row.get("focused_image_distance_mm") is not None:
            focus_axis.scatter(
                row["value_mm"],
                row["focused_image_distance_mm"],
                marker="x",
                s=100,
                color="crimson",
                label="Rejected case",
                zorder=5,
            )
    focus_axis.set_ylabel("Image distance (mm)")
    focus_axis.set_title("Quick Focus feasibility gate [40.0, 44.5] mm")
    focus_axis.grid(True, alpha=0.3)
    focus_axis.legend()

    balance_axis.plot(
        valid_x,
        [row["mean_rms_um"] for row in valid_rows],
        marker="o",
        linewidth=2,
        label="Equal-field mean RMS",
    )
    balance_axis.plot(
        valid_x,
        [row["worst_field_rms_um"] for row in valid_rows],
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
        label=f"Best balanced: {best['case_id']}",
        zorder=5,
    )
    balance_axis.set_xlabel("Surface 2 thickness (mm)")
    balance_axis.set_ylabel("Descriptive RMS metric (um)")
    balance_axis.set_title("Balanced comparison (not a Zemax merit function)")
    balance_axis.set_xticks(all_x)
    balance_axis.grid(True, alpha=0.3)
    balance_axis.legend()

    figure.suptitle("Day 7 Cooke Surface 2 Thickness Sweep", fontsize=14)
    figure.tight_layout()
    output_file = batch_dir / "day7_sweep_analysis.png"
    figure.savefig(output_file, dpi=220)
    plt.close(figure)
    return output_file


def write_decision_report(batch_dir, summary, best, rows):
    """Record the transparent rule used to select the balanced candidate."""

    rejected_ids = [
        row["case_id"] for row in rows if row["status"] == "rejected"
    ]
    report = {
        "task": "day7_sweep_analysis",
        "source_batch": summary["batch_id"],
        "selection_rule": (
            "Among successful cases, minimize the equal-field arithmetic "
            "mean RMS; use worst-field RMS as the tie-breaker."
        ),
        "warning": (
            "This is a descriptive comparison, not the Zemax merit function."
        ),
        "best_balanced_case": best["case_id"],
        "best_thickness_mm": best["value_mm"],
        "mean_rms_um": best["mean_rms_um"],
        "worst_field_rms_um": best["worst_field_rms_um"],
        "rejected_cases": rejected_ids,
    }
    output_file = batch_dir / "day7_decision_report.json"
    output_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_file


def main():
    summary_file = find_latest_summary()
    summary, rows = load_rows(summary_file)
    valid_rows, best = add_comparison_metrics(rows)
    batch_dir = summary_file.parent

    table_file = write_analysis_table(batch_dir, rows)
    figure_file = plot_analysis(batch_dir, rows, valid_rows, best)
    report_file = write_decision_report(batch_dir, summary, best, rows)

    print("========== DAY 7 SWEEP ANALYSIS ==========")
    print(f"Source batch: {summary['batch_id']}")
    for row in rows:
        if row["status"] == "rejected":
            print(f"{row['case_id']}: REJECTED by focus boundary")
            continue
        print(
            f"{row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"mean RMS={row['mean_rms_um']:.3f} um, "
            f"worst field={row['worst_field_rms_um']:.3f} um"
        )

    print()
    print(
        f"[RESULT] Best balanced candidate: {best['case_id']} "
        f"at {best['value_mm']:.7f} mm"
    )
    print("This descriptive rule is not the Zemax merit function.")
    print(f"[PASS] Analysis CSV: {table_file}")
    print(f"[PASS] Analysis figure: {figure_file}")
    print(f"[PASS] Decision report: {report_file}")
    print("No ZOS-API connection was created.")


if __name__ == "__main__":
    main()
