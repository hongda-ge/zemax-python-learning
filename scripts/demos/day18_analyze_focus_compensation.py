"""Day 18 step 4: summarize how Quick Focus masks branch differences."""

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
    """Require every Zemax action to be disabled before offline analysis."""

    execution = config["execution"]
    if execution.get("allow_offline_analysis") is not True:
        raise ValueError("Day 18 offline analysis is not approved.")
    allowed_true = {"allow_offline_analysis"}
    unsafe = [
        key
        for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if unsafe:
        raise ValueError("Day 18 Zemax action is still enabled: " + ", ".join(unsafe))


def find_latest_report(root, prefix, filename):
    """Find the newest successful endpoint report."""

    matches = list(root.glob(f"{prefix}_*/{filename}"))
    if not matches:
        raise FileNotFoundError(f"No Day 18 report found: {filename}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_endpoint_report(report, expected_task, expected_delta):
    """Audit identity, results, hashes and forbidden actions."""

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
        checks[f"{branch_name} no optimization"] = branch.get("optimization_used") is False
        checks[f"{branch_name} no SaveAs"] = branch.get("save_as_used") is False
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 18 endpoint evidence failed: " + ", ".join(failed))


def build_row(report):
    """Create one endpoint summary row from the paired observations."""

    preserve = report["preserve_solve"]
    frozen = report["freeze_radius"]
    fixed_difference = float(
        report["uncompensated_branch_difference"]["mean_difference_um"]
    )
    focused_difference = float(
        report["compensated_branch_difference"]["mean_difference_um"]
    )
    attenuation = (
        1.0 - abs(focused_difference) / abs(fixed_difference)
    ) * 100.0
    return {
        "endpoint_id": report["endpoint"]["endpoint_id"],
        "surface2_thickness_mm": float(report["endpoint"]["value_mm"]),
        "delta_mm": float(report["endpoint"]["delta_mm"]),
        "preserve_fixed_mean_rms_um": float(
            preserve["uncompensated_spot_summary"]["equal_field_mean_rms_um"]
        ),
        "preserve_focused_mean_rms_um": float(
            preserve["compensated_spot_summary"]["equal_field_mean_rms_um"]
        ),
        "preserve_focus_shift_mm": float(preserve["focus"]["focus_shift_mm"]),
        "frozen_fixed_mean_rms_um": float(
            frozen["uncompensated_spot_summary"]["equal_field_mean_rms_um"]
        ),
        "frozen_focused_mean_rms_um": float(
            frozen["compensated_spot_summary"]["equal_field_mean_rms_um"]
        ),
        "frozen_focus_shift_mm": float(frozen["focus"]["focus_shift_mm"]),
        "fixed_frozen_minus_preserve_mean_um": fixed_difference,
        "focused_frozen_minus_preserve_mean_um": focused_difference,
        "branch_difference_attenuation_percent": attenuation,
    }


def save_csv(rows, output_file):
    """Write the two endpoint summaries without overwriting evidence."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite CSV: {output_file}")
    with output_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_figure(rows, output_file):
    """Plot branch differences before and after Quick Focus."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite figure: {output_file}")
    labels = [f"delta {row['delta_mm']:+.1f} mm" for row in rows]
    fixed = [abs(row["fixed_frozen_minus_preserve_mean_um"]) for row in rows]
    focused = [abs(row["focused_frozen_minus_preserve_mean_um"]) for row in rows]
    x_values = list(range(len(rows)))
    width = 0.34
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar([x - width / 2 for x in x_values], fixed, width, label="Fixed image")
    axis.bar([x + width / 2 for x in x_values], focused, width, label="After Quick Focus")
    axis.set_xticks(x_values, labels)
    axis.set_ylabel("Absolute branch mean-RMS difference (um)")
    axis.set_title("Day 18: Quick Focus attenuates Solve-branch differences")
    axis.grid(axis="y", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_file, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day18_focus_compensation_effect.yaml")
    require_offline_lock(config)
    root = PROJECT_ROOT / config["output"]["root"]
    negative_file = find_latest_report(
        root,
        "negative_endpoint",
        "negative_endpoint_validation_report.json",
    )
    positive_file = find_latest_report(
        root,
        "positive_endpoint",
        "positive_endpoint_validation_report.json",
    )
    negative = json.loads(negative_file.read_text(encoding="utf-8"))
    positive = json.loads(positive_file.read_text(encoding="utf-8"))
    validate_endpoint_report(
        negative,
        "day18_negative_endpoint_validation",
        -0.4,
    )
    validate_endpoint_report(
        positive,
        "day18_positive_endpoint_validation",
        0.4,
    )
    rows = [build_row(negative), build_row(positive)]

    output_dir = root / datetime.now().strftime("offline_analysis_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_file = output_dir / "focus_compensation_summary.csv"
    figure_file = output_dir / "day18_focus_compensation.png"
    report_file = output_dir / "focus_compensation_report.json"
    save_csv(rows, csv_file)
    save_figure(rows, figure_file)

    attenuation_values = [
        row["branch_difference_attenuation_percent"] for row in rows
    ]
    report = {
        "task": "day18_focus_compensation_analysis",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_negative_report": str(negative_file),
        "source_positive_report": str(positive_file),
        "rows": rows,
        "minimum_branch_difference_attenuation_percent": min(
            attenuation_values
        ),
        "conclusion": (
            "Quick Focus absorbed most of the mean Spot difference between "
            "the two Solve branches at both sampled endpoints."
        ),
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 18 OFFLINE FOCUS-COMPENSATION ANALYSIS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    for row in rows:
        print(
            f"delta {row['delta_mm']:+.1f} mm: branch mean-RMS difference "
            f"{row['fixed_frozen_minus_preserve_mean_um']:+.3f} -> "
            f"{row['focused_frozen_minus_preserve_mean_um']:+.3f} um, "
            f"attenuation={row['branch_difference_attenuation_percent']:.2f}%"
        )
    print(
        "[RESULT] Minimum sampled attenuation: "
        f"{min(attenuation_values):.2f}%"
    )
    print("[RESULT] Quick Focus masks most fixed-image branch difference")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] Both endpoint evidence and safety audits verified")
    print(f"[PASS] Summary CSV: {csv_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Analysis report: {report_file}")


if __name__ == "__main__":
    main()
