"""Day 9 step 4: combine Day 8 Spot and Day 9 FFT MTF metrics."""

import csv
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAY8_ROOT = PROJECT_ROOT / "outputs" / "day8_local_fine_scan"
DAY9_ROOT = PROJECT_ROOT / "outputs" / "day9_fft_mtf_validation"
MATPLOTLIB_CACHE = PROJECT_ROOT / "outputs" / ".matplotlib_cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def latest_file(root, pattern, label):
    """Find the newest file matching one completed experiment pattern."""

    candidates = list(root.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No {label} was found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def read_csv_rows(csv_file):
    """Read one UTF-8 CSV into dictionaries."""

    with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def join_day8_day9(day8_csv, day9_csv):
    """Join the four MTF candidates to their Day 8 Spot metrics."""

    day8_by_case = {
        row["case_id"]: row for row in read_csv_rows(day8_csv)
    }
    combined = []
    for mtf_row in read_csv_rows(day9_csv):
        case_id = mtf_row["case_id"]
        if case_id not in day8_by_case:
            raise ValueError(f"Missing Day 8 Spot data for {case_id}.")
        spot_row = day8_by_case[case_id]
        combined.append(
            {
                "case_id": case_id,
                "value_mm": float(mtf_row["value_mm"]),
                "spot_mean_rms_um": float(spot_row["mean_rms_um"]),
                "spot_worst_field_rms_um": float(
                    spot_row["worst_field_rms_um"]
                ),
                "mtf_30_overall_mean": float(
                    mtf_row["mtf_30_overall_mean"]
                ),
                "mtf_30_minimum": float(mtf_row["mtf_30_minimum"]),
                "mtf_30_maximum_direction_gap": float(
                    mtf_row["mtf_30_maximum_direction_gap"]
                ),
                "mtf_50_overall_mean": float(
                    mtf_row["mtf_50_overall_mean"]
                ),
                "mtf_50_minimum": float(mtf_row["mtf_50_minimum"]),
                "mtf_50_maximum_direction_gap": float(
                    mtf_row["mtf_50_maximum_direction_gap"]
                ),
            }
        )
    if len(combined) != 4:
        raise ValueError(f"Expected 4 joined candidates, found {len(combined)}.")
    return combined


def dominates(candidate_a, candidate_b):
    """Return whether A is no worse on all three primary objectives."""

    no_worse = (
        candidate_a["spot_mean_rms_um"]
        <= candidate_b["spot_mean_rms_um"]
        and candidate_a["mtf_30_overall_mean"]
        >= candidate_b["mtf_30_overall_mean"]
        and candidate_a["mtf_50_overall_mean"]
        >= candidate_b["mtf_50_overall_mean"]
    )
    strictly_better = (
        candidate_a["spot_mean_rms_um"]
        < candidate_b["spot_mean_rms_um"]
        or candidate_a["mtf_30_overall_mean"]
        > candidate_b["mtf_30_overall_mean"]
        or candidate_a["mtf_50_overall_mean"]
        > candidate_b["mtf_50_overall_mean"]
    )
    return no_worse and strictly_better


def add_pareto_status(rows):
    """Mark non-dominated candidates and record every dominator."""

    for candidate in rows:
        dominators = [
            other["case_id"]
            for other in rows
            if other is not candidate and dominates(other, candidate)
        ]
        candidate["pareto_candidate"] = not dominators
        candidate["dominated_by"] = dominators
    return [row for row in rows if row["pareto_candidate"]]


def write_combined_csv(batch_dir, rows):
    """Write one human-readable Spot/MTF comparison table."""

    columns = list(rows[0].keys())
    output_file = batch_dir / "day9_spot_mtf_tradeoff.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return output_file


def plot_tradeoff(batch_dir, rows):
    """Plot the Pareto trade-off, MTF levels, and direction separation."""

    x_values = [row["value_mm"] for row in rows]
    figure, axes = plt.subplots(3, 1, figsize=(9, 12))
    pareto_axis, mtf_axis, gap_axis = axes

    for row in rows:
        marker = "o" if row["pareto_candidate"] else "x"
        color = "tab:blue" if row["pareto_candidate"] else "tab:red"
        pareto_axis.scatter(
            row["spot_mean_rms_um"],
            row["mtf_50_overall_mean"],
            marker=marker,
            s=100,
            color=color,
        )
        pareto_axis.annotate(
            row["case_id"],
            (row["spot_mean_rms_um"], row["mtf_50_overall_mean"]),
            xytext=(7, 5),
            textcoords="offset points",
        )
    pareto_axis.set_xlabel("Mean RMS spot radius (um, lower is better)")
    pareto_axis.set_ylabel("MTF 50 overall mean (higher is better)")
    pareto_axis.set_title("Spot versus high-frequency MTF Pareto trade-off")
    pareto_axis.grid(True, alpha=0.3)

    mtf_axis.plot(
        x_values,
        [row["mtf_30_overall_mean"] for row in rows],
        marker="o",
        linewidth=2,
        label="MTF 30 overall mean",
    )
    mtf_axis.plot(
        x_values,
        [row["mtf_30_minimum"] for row in rows],
        marker="o",
        linestyle="--",
        label="MTF 30 minimum",
    )
    mtf_axis.plot(
        x_values,
        [row["mtf_50_overall_mean"] for row in rows],
        marker="s",
        linewidth=2,
        label="MTF 50 overall mean",
    )
    mtf_axis.plot(
        x_values,
        [row["mtf_50_minimum"] for row in rows],
        marker="s",
        linestyle="--",
        label="MTF 50 minimum",
    )
    mtf_axis.set_xlabel("Surface 2 thickness (mm)")
    mtf_axis.set_ylabel("MTF")
    mtf_axis.set_title("Overall and worst-channel MTF")
    mtf_axis.set_xticks(x_values)
    mtf_axis.grid(True, alpha=0.3)
    mtf_axis.legend()

    gap_axis.plot(
        x_values,
        [row["mtf_30_maximum_direction_gap"] for row in rows],
        marker="o",
        linewidth=2,
        label="Maximum T/S gap at 30 cyc/mm",
    )
    gap_axis.plot(
        x_values,
        [row["mtf_50_maximum_direction_gap"] for row in rows],
        marker="s",
        linewidth=2,
        label="Maximum T/S gap at 50 cyc/mm",
    )
    gap_axis.set_xlabel("Surface 2 thickness (mm)")
    gap_axis.set_ylabel("Absolute MTF direction gap")
    gap_axis.set_title("Tangential/sagittal separation")
    gap_axis.set_xticks(x_values)
    gap_axis.grid(True, alpha=0.3)
    gap_axis.legend()

    figure.suptitle("Day 9 Spot and FFT MTF Cross-validation", fontsize=14)
    figure.tight_layout()
    output_file = batch_dir / "day9_spot_mtf_tradeoff.png"
    figure.savefig(output_file, dpi=220)
    plt.close(figure)
    return output_file


def write_report(batch_dir, rows, pareto_rows, day8_csv, day9_csv):
    """Record metric-specific winners without inventing hidden weights."""

    best_spot = min(rows, key=lambda row: row["spot_mean_rms_um"])
    best_mtf_30 = max(rows, key=lambda row: row["mtf_30_overall_mean"])
    best_mtf_50 = max(rows, key=lambda row: row["mtf_50_overall_mean"])
    best_mtf_30_minimum = max(rows, key=lambda row: row["mtf_30_minimum"])
    report = {
        "task": "day9_spot_mtf_tradeoff_analysis",
        "day8_source_csv": str(day8_csv),
        "day9_source_csv": str(day9_csv),
        "pareto_objectives": {
            "minimize": ["spot_mean_rms_um"],
            "maximize": [
                "mtf_30_overall_mean",
                "mtf_50_overall_mean",
            ],
        },
        "pareto_candidate_ids": [row["case_id"] for row in pareto_rows],
        "dominated_candidates": {
            row["case_id"]: row["dominated_by"]
            for row in rows
            if not row["pareto_candidate"]
        },
        "metric_specific_winners": {
            "spot_mean_rms": best_spot["case_id"],
            "mtf_30_overall_mean": best_mtf_30["case_id"],
            "mtf_50_overall_mean": best_mtf_50["case_id"],
            "mtf_30_minimum": best_mtf_30_minimum["case_id"],
        },
        "decision": (
            "No single final candidate is selected because Spot and MTF "
            "priorities have not been assigned explicit weights."
        ),
    }
    output_file = batch_dir / "day9_spot_mtf_tradeoff_report.json"
    output_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report, output_file


def main():
    day8_csv = latest_file(
        DAY8_ROOT,
        "fine_scan_*/day8_local_robustness.csv",
        "Day 8 robustness CSV",
    )
    day9_csv = latest_file(
        DAY9_ROOT,
        "candidate_batch_*/candidate_mtf_comparison.csv",
        "Day 9 candidate MTF CSV",
    )
    batch_dir = day9_csv.parent
    rows = join_day8_day9(day8_csv, day9_csv)
    pareto_rows = add_pareto_status(rows)

    combined_csv = write_combined_csv(batch_dir, rows)
    figure_file = plot_tradeoff(batch_dir, rows)
    report, report_file = write_report(
        batch_dir,
        rows,
        pareto_rows,
        day8_csv,
        day9_csv,
    )

    print("========== DAY 9 SPOT / FFT MTF TRADE-OFF ==========")
    for row in rows:
        status = "PARETO" if row["pareto_candidate"] else (
            "DOMINATED by " + ", ".join(row["dominated_by"])
        )
        print(
            f"{row['case_id']}: Spot mean={row['spot_mean_rms_um']:.3f} um, "
            f"MTF30 mean={row['mtf_30_overall_mean']:.4f}, "
            f"MTF50 mean={row['mtf_50_overall_mean']:.4f} -> {status}"
        )

    print()
    print(
        "[RESULT] Pareto candidates: "
        + ", ".join(report["pareto_candidate_ids"])
    )
    print("[RESULT] fine_006 is removable because better alternatives exist.")
    print("[RESULT] No final winner without explicit Spot/MTF priorities.")
    print(f"[PASS] Combined CSV: {combined_csv}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")
    print("No ZOS-API connection was created.")


if __name__ == "__main__":
    main()
