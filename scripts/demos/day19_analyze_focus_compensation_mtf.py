"""Day 19 step 4: summarize paired FFT MTF results without Zemax."""

import csv
import json
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


def require_offline_lock(config):
    """Require every Zemax action off and offline analysis on."""

    execution = config["execution"]
    if execution.get("allow_offline_analysis") is not True:
        raise ValueError("Day 19 offline analysis is not approved.")
    unsafe = [
        key
        for key, value in execution.items()
        if key != "allow_offline_analysis" and value is not False
    ]
    if unsafe:
        raise ValueError("Day 19 Zemax action is still enabled: " + ", ".join(unsafe))


def find_latest_report(root, prefix, filename):
    """Find the newest report under a stable endpoint prefix."""

    matches = list(root.glob(f"{prefix}_*/{filename}"))
    if not matches:
        raise FileNotFoundError(f"No Day 19 report found: {filename}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_report(report, expected_task, expected_delta):
    """Require successful results and complete safety evidence."""

    checks = {
        "task": report.get("task") == expected_task,
        "status": report.get("status") == "success",
        "delta": abs(float(report.get("endpoint", {}).get("delta_mm", 99.0)) - expected_delta) <= 1e-12,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    for branch_name in ("preserve_solve", "freeze_radius"):
        branch = report.get(branch_name, {})
        checks[f"{branch_name} success"] = branch.get("status") == "success"
        checks[f"{branch_name} connection"] = branch.get("connection_closed") is True
        checks[f"{branch_name} source"] = branch.get("source_unchanged") is True
        checks[f"{branch_name} copy"] = branch.get("working_copy_unchanged") is True
        checks[f"{branch_name} fields before"] = branch.get(
            "fixed_image_mtf_metrics", {}
        ).get("field_count") == 3
        checks[f"{branch_name} fields after"] = branch.get(
            "focused_mtf_metrics", {}
        ).get("field_count") == 3
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 19 endpoint evidence failed: " + ", ".join(failed))


def frequency_map(branch, state):
    """Index one branch summary by target frequency."""

    key = "fixed_image_mtf_summary" if state == "fixed" else "focused_mtf_summary"
    return {
        float(row["frequency_cyc_per_mm"]): row
        for row in branch[key]["frequencies"]
    }


def maximum_sample_difference(report, state, frequency):
    """Find the maximum absolute T/S branch difference for one frequency."""

    key = (
        "fixed_image_branch_difference"
        if state == "fixed"
        else "focused_branch_difference"
    )
    candidates = []
    for sample in report[key]["samples"]:
        if abs(float(sample["frequency_cyc_per_mm"]) - frequency) > 1e-12:
            continue
        for direction in ("tangential", "sagittal"):
            difference = float(sample[f"{direction}_difference"])
            candidates.append(
                {
                    "field_y_degree": float(sample["field_y_degree"]),
                    "direction": direction,
                    "difference": difference,
                }
            )
    if not candidates:
        raise ValueError("No field/direction MTF differences were found.")
    return max(candidates, key=lambda item: abs(item["difference"]))


def build_rows(report):
    """Create frequency-level recovery and post-focus comparison rows."""

    preserve = report["preserve_solve"]
    frozen = report["freeze_radius"]
    preserve_fixed = frequency_map(preserve, "fixed")
    preserve_focused = frequency_map(preserve, "focused")
    frozen_fixed = frequency_map(frozen, "fixed")
    frozen_focused = frequency_map(frozen, "focused")
    if not (
        preserve_fixed.keys()
        == preserve_focused.keys()
        == frozen_fixed.keys()
        == frozen_focused.keys()
    ):
        raise ValueError("Day 19 branch frequencies do not match.")

    rows = []
    for frequency in sorted(preserve_fixed):
        pf = preserve_fixed[frequency]
        pc = preserve_focused[frequency]
        ff = frozen_fixed[frequency]
        fc = frozen_focused[frequency]
        focused_mean_difference = (
            float(fc["overall_mean_mtf"]) - float(pc["overall_mean_mtf"])
        )
        focused_mean_reference = (
            float(fc["overall_mean_mtf"]) + float(pc["overall_mean_mtf"])
        ) / 2.0
        fixed_maximum = maximum_sample_difference(report, "fixed", frequency)
        focused_maximum = maximum_sample_difference(report, "focused", frequency)
        rows.append(
            {
                "endpoint_id": report["endpoint"]["endpoint_id"],
                "delta_mm": float(report["endpoint"]["delta_mm"]),
                "frequency_cyc_per_mm": frequency,
                "preserve_fixed_mean_mtf": float(pf["overall_mean_mtf"]),
                "preserve_focused_mean_mtf": float(pc["overall_mean_mtf"]),
                "preserve_mean_recovery": float(pc["overall_mean_mtf"])
                - float(pf["overall_mean_mtf"]),
                "preserve_focused_minimum_mtf": float(pc["minimum_mtf"]),
                "frozen_fixed_mean_mtf": float(ff["overall_mean_mtf"]),
                "frozen_focused_mean_mtf": float(fc["overall_mean_mtf"]),
                "frozen_mean_recovery": float(fc["overall_mean_mtf"])
                - float(ff["overall_mean_mtf"]),
                "frozen_focused_minimum_mtf": float(fc["minimum_mtf"]),
                "fixed_frozen_minus_preserve_mean_mtf": float(
                    ff["overall_mean_mtf"]
                )
                - float(pf["overall_mean_mtf"]),
                "focused_frozen_minus_preserve_mean_mtf": focused_mean_difference,
                "focused_branch_relative_mean_difference_percent": (
                    abs(focused_mean_difference) / focused_mean_reference * 100.0
                ),
                "fixed_max_abs_sample_difference": abs(fixed_maximum["difference"]),
                "fixed_max_difference_field_degree": fixed_maximum[
                    "field_y_degree"
                ],
                "fixed_max_difference_direction": fixed_maximum["direction"],
                "focused_max_abs_sample_difference": abs(
                    focused_maximum["difference"]
                ),
                "focused_max_difference_field_degree": focused_maximum[
                    "field_y_degree"
                ],
                "focused_max_difference_direction": focused_maximum["direction"],
            }
        )
    return rows


def save_csv(rows, output_file):
    """Write comparison rows without overwriting evidence."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite CSV: {output_file}")
    with output_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_figure(rows, output_file):
    """Plot mean MTF before and after focus for both branches."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite figure: {output_file}")
    labels = [
        f"{row['delta_mm']:+.1f} mm\n{row['frequency_cyc_per_mm']:.0f} cyc/mm"
        for row in rows
    ]
    x_values = list(range(len(rows)))
    figure, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(
        x_values,
        [row["preserve_fixed_mean_mtf"] for row in rows],
        "o-",
        label="Preserve Solve",
    )
    axes[0].plot(
        x_values,
        [row["frozen_fixed_mean_mtf"] for row in rows],
        "s-",
        label="Freeze radius",
    )
    axes[0].set_ylabel("Mean MTF")
    axes[0].set_title("Fixed image: strong defocus drives MTF near zero")
    axes[0].grid(alpha=0.3)
    axes[0].legend()
    axes[1].plot(
        x_values,
        [row["preserve_focused_mean_mtf"] for row in rows],
        "o-",
        label="Preserve Solve",
    )
    axes[1].plot(
        x_values,
        [row["frozen_focused_mean_mtf"] for row in rows],
        "s-",
        label="Freeze radius",
    )
    axes[1].set_ylabel("Mean MTF")
    axes[1].set_title("After Quick Focus: branch means become close")
    axes[1].set_xticks(x_values, labels)
    axes[1].grid(alpha=0.3)
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(output_file, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day19_focus_compensation_mtf.yaml")
    require_offline_lock(config)
    root = PROJECT_ROOT / config["output"]["root"]
    negative_file = find_latest_report(
        root,
        "negative_endpoint",
        "negative_endpoint_mtf_report.json",
    )
    positive_file = find_latest_report(
        root,
        "positive_endpoint",
        "positive_endpoint_mtf_report.json",
    )
    negative = json.loads(negative_file.read_text(encoding="utf-8"))
    positive = json.loads(positive_file.read_text(encoding="utf-8"))
    validate_report(negative, "day19_negative_endpoint_mtf", -0.4)
    validate_report(positive, "day19_positive_endpoint_mtf", 0.4)
    rows = build_rows(negative) + build_rows(positive)

    output_dir = root / datetime.now().strftime("offline_analysis_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_file = output_dir / "focus_compensation_mtf_summary.csv"
    figure_file = output_dir / "day19_focus_compensation_mtf.png"
    report_file = output_dir / "focus_compensation_mtf_report.json"
    save_csv(rows, csv_file)
    save_figure(rows, figure_file)

    maximum_relative_mean_difference = max(
        row["focused_branch_relative_mean_difference_percent"] for row in rows
    )
    maximum_focused_sample = max(
        rows,
        key=lambda row: row["focused_max_abs_sample_difference"],
    )
    report = {
        "task": "day19_focus_compensation_mtf_analysis",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_negative_report": str(negative_file),
        "source_positive_report": str(positive_file),
        "rows": rows,
        "maximum_focused_relative_mean_difference_percent": (
            maximum_relative_mean_difference
        ),
        "maximum_focused_individual_sample_difference": {
            "endpoint_id": maximum_focused_sample["endpoint_id"],
            "delta_mm": maximum_focused_sample["delta_mm"],
            "frequency_cyc_per_mm": maximum_focused_sample[
                "frequency_cyc_per_mm"
            ],
            "absolute_difference": maximum_focused_sample[
                "focused_max_abs_sample_difference"
            ],
            "field_y_degree": maximum_focused_sample[
                "focused_max_difference_field_degree"
            ],
            "direction": maximum_focused_sample[
                "focused_max_difference_direction"
            ],
        },
        "fixed_image_attenuation_percent_reported": False,
        "fixed_image_attenuation_note": (
            "Fixed-image MTF values are near the zero floor, so ratios of "
            "branch differences are unstable and are not interpreted."
        ),
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 19 OFFLINE FFT MTF ANALYSIS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    for row in rows:
        print(
            f"delta {row['delta_mm']:+.1f} mm, "
            f"{row['frequency_cyc_per_mm']:.0f} cyc/mm: "
            f"preserve recovery={row['preserve_mean_recovery']:+.4f}, "
            f"frozen recovery={row['frozen_mean_recovery']:+.4f}, "
            "focused frozen-preserve="
            f"{row['focused_frozen_minus_preserve_mean_mtf']:+.4f} "
            f"({row['focused_branch_relative_mean_difference_percent']:.2f}%)"
        )
    print(
        "[RESULT] Maximum focused relative mean difference: "
        f"{maximum_relative_mean_difference:.2f}%"
    )
    print(
        "[RESULT] Maximum focused individual T/S sample difference: "
        f"{maximum_focused_sample['focused_max_abs_sample_difference']:.4f}"
    )
    print("[RESULT] Fixed-image difference ratios are not interpreted near MTF=0")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] Both endpoint evidence and safety audits verified")
    print(f"[PASS] Summary CSV: {csv_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Analysis report: {report_file}")


if __name__ == "__main__":
    main()
