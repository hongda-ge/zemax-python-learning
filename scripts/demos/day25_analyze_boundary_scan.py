"""Day 25 step 4: combine old anchors and new boundary points offline."""

import csv
import json
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
from scripts.demos.day25_balanced_acceptance_boundary_scan_plan import (  # noqa: E402
    sha256_file,
    validate_day24_evidence,
    validate_guardrails,
    validate_new_offsets,
    validate_source_files,
    validate_thresholds,
)
from scripts.demos.day25_run_boundary_scan import (  # noqa: E402
    validate_baseline_report,
)


def require_offline_authorization(config):
    """Permit only offline evidence combination and plotting."""

    execution = config["execution"]
    if execution.get("allow_offline_acceptance") is not True:
        raise ValueError("Day 25 offline boundary analysis is not approved.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_baseline_control",
        "allow_boundary_cases",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_tolerance_claim",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 25 offline forbidden action enabled: " + ", ".join(enabled))


def load_frozen_report(path, expected_hash, label):
    """Load one report only after verifying its exact file fingerprint."""

    report_file = PROJECT_ROOT / path
    if not report_file.is_file():
        raise FileNotFoundError(f"{label} not found: {report_file}")
    if sha256_file(report_file) != expected_hash:
        raise ValueError(f"The frozen {label} changed.")
    return report_file, json.loads(report_file.read_text(encoding="utf-8"))


def validate_boundary_batch(config, report, model_file, baseline_file, expected_offsets):
    """Audit all nine optical observations and their immutable case reports."""

    checks = {
        "task": report.get("task") == "day25_boundary_scan_batch",
        "status": report.get("status") == "success",
        "nine cases": report.get("case_count") == 9,
        "source model": Path(report.get("source_model", "")).resolve() == model_file.resolve(),
        "source hash": report.get("source_sha256", "").upper()
        == config["source"]["focused_model_sha256"],
        "baseline report": Path(report.get("approved_baseline_report", "")).resolve()
        == baseline_file.resolve(),
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no interpolation": report.get("interpolation_used") is False,
        "no tolerance claim": report.get("continuous_tolerance_claimed") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 25 batch evidence failed: " + ", ".join(failed))

    rows = report.get("rows", [])
    actual_offsets = [float(row["offset_mm"]) for row in rows]
    if actual_offsets != expected_offsets:
        raise ValueError("Day 25 batch offsets or order changed.")
    case_reports = [Path(path) for path in report.get("case_reports", [])]
    if len(case_reports) != 9 or len(set(case_reports)) != 9:
        raise ValueError("Day 25 case-report evidence is incomplete.")
    for case_file in case_reports:
        case = json.loads(case_file.read_text(encoding="utf-8"))
        case_checks = {
            "task": case.get("task") == "day25_boundary_case",
            "status": case.get("status") == "success",
            "input unchanged": case.get("input_model_unchanged") is True,
            "copy unchanged": case.get("working_copy_unchanged") is True,
            "connection closed": case.get("connection_closed") is True,
            "no Quick Focus": case.get("quick_focus_used") is False,
            "no optimization": case.get("optimization_used") is False,
            "no SaveAs": case.get("save_as_used") is False,
        }
        failed_case = [name for name, passed in case_checks.items() if not passed]
        if failed_case:
            raise ValueError(f"Case evidence failed ({case_file}): " + ", ".join(failed_case))
    return rows


def normalize_day24_rows(report, scenario_id):
    """Convert seven old anchors to the Day 25 combined-table schema."""

    details = [item for item in report["details"] if item["scenario_id"] == scenario_id]
    rows = []
    for item in details:
        rows.append(
            {
                "source_day": 23,
                "case_id": item["case_id"],
                "offset_mm": float(item["offset_mm"]),
                "spot_mean_rms_um": float(item["spot_mean_value"]),
                "spot_worst_rms_um": float(item["spot_worst_value"]),
                "mtf30_mean": float(item["mtf30_mean_diagnostic"]),
                "mtf30_minimum": float(item["mtf30_minimum_value"]),
                "mtf50_mean": float(item["mtf50_mean_diagnostic"]),
                "mtf50_minimum": float(item["mtf50_minimum_value"]),
                "balanced_acceptance_pass": item["all_required_metrics_pass"],
                "failed_metrics": item["failed_metrics"],
            }
        )
    return rows


def normalize_day25_rows(rows):
    """Select equivalent fields from the nine new observations."""

    fields = (
        "case_id",
        "offset_mm",
        "spot_mean_rms_um",
        "spot_worst_rms_um",
        "mtf30_mean",
        "mtf30_minimum",
        "mtf50_mean",
        "mtf50_minimum",
        "balanced_acceptance_pass",
        "failed_metrics",
    )
    return [{"source_day": 25, **{field: row[field] for field in fields}} for row in rows]


def find_state_transitions(rows):
    """Report adjacent measured points with opposing states, without interpolation."""

    transitions = []
    for left, right in zip(rows, rows[1:]):
        if left["balanced_acceptance_pass"] == right["balanced_acceptance_pass"]:
            continue
        transitions.append(
            {
                "left_offset_mm": left["offset_mm"],
                "left_pass": left["balanced_acceptance_pass"],
                "left_failed_metrics": left["failed_metrics"],
                "right_offset_mm": right["offset_mm"],
                "right_pass": right["balanced_acceptance_pass"],
                "right_failed_metrics": right["failed_metrics"],
                "unmeasured_width_mm": right["offset_mm"] - left["offset_mm"],
            }
        )
    if len(transitions) != 2:
        raise ValueError("Expected exactly two sampled PASS/FAIL transitions.")
    return transitions


def write_csv(path, rows):
    """Write dictionaries as UTF-8 spreadsheet-friendly CSV."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def create_figure(path, rows, limits):
    """Plot four required metrics at measured points only."""

    offsets = [row["offset_mm"] for row in rows]
    passed = [row["balanced_acceptance_pass"] for row in rows]
    colors = ["#17823b" if value else "#bd1530" for value in passed]
    panels = (
        ("spot_mean_rms_um", limits["spot_mean_rms_um_max"], "Spot mean RMS (um)"),
        ("spot_worst_rms_um", limits["spot_worst_rms_um_max"], "Worst field RMS (um)"),
        ("mtf30_minimum", limits["mtf30_minimum_min"], "Minimum MTF at 30 cyc/mm"),
        ("mtf50_minimum", limits["mtf50_minimum_min"], "Minimum MTF at 50 cyc/mm"),
    )
    figure, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), sharex=True)
    for axis, (metric, limit, label) in zip(axes.flat, panels):
        values = [row[metric] for row in rows]
        axis.plot(offsets, values, color="#555555", linewidth=1.0, alpha=0.7)
        axis.scatter(offsets, values, c=colors, s=46, zorder=3)
        axis.axhline(limit, color="black", linestyle="--", linewidth=1.0, label="threshold")
        axis.set_ylabel(label)
        axis.grid(True, alpha=0.25)
        axis.legend()
    for axis in axes[1]:
        axis.set_xlabel("Measured residual offset (mm)")
    figure.suptitle("Day 25 measured boundary evidence (green=PASS, red=FAIL)")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day25_balanced_acceptance_boundary_scan.yaml")
    require_offline_authorization(config)
    validate_guardrails(config)
    day24_file, model_file = validate_source_files(config)
    day24_report, _ = validate_day24_evidence(config, day24_file)
    validate_thresholds(config, day24_report)
    negative_values, positive_values = validate_new_offsets(config)
    source = config["source"]
    baseline_file, baseline = load_frozen_report(
        source["approved_baseline_report"],
        source["approved_baseline_report_sha256"],
        "Day 25 baseline report",
    )
    validate_baseline_report(config, baseline_file, model_file, day24_file)
    batch_file, batch = load_frozen_report(
        source["boundary_batch_report"],
        source["boundary_batch_report_sha256"],
        "Day 25 boundary batch report",
    )
    new_rows = validate_boundary_batch(
        config,
        batch,
        model_file,
        baseline_file,
        negative_values + positive_values,
    )
    del baseline

    rows = normalize_day24_rows(day24_report, source["expected_scenario_id"])
    rows.extend(normalize_day25_rows(new_rows))
    rows.sort(key=lambda item: item["offset_mm"])
    if len(rows) != 16 or len({row["offset_mm"] for row in rows}) != 16:
        raise ValueError("Day 25 combined evidence must contain 16 unique points.")
    transitions = find_state_transitions(rows)

    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("offline_analysis_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    metrics_file = output_dir / "combined_measured_boundary_metrics.csv"
    transitions_file = output_dir / "sampled_state_transitions.csv"
    figure_file = output_dir / "day25_boundary_evidence.png"
    report_file = output_dir / "boundary_analysis_report.json"
    write_csv(metrics_file, rows)
    write_csv(transitions_file, transitions)
    create_figure(figure_file, rows, config["balanced_acceptance"]["limits"])

    report = {
        "task": "day25_boundary_scan_offline_analysis",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day24_report": str(day24_file),
        "source_baseline_report": str(baseline_file),
        "source_boundary_batch_report": str(batch_file),
        "combined_measured_points": rows,
        "sampled_state_transitions": transitions,
        "measured_point_count": len(rows),
        "measured_points_only": True,
        "interpolation_used": False,
        "extrapolation_used": False,
        "curve_fit_used": False,
        "continuous_tolerance_claimed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "unique_engineering_winner": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("========== DAY 25 OFFLINE BOUNDARY ANALYSIS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print("Sixteen measured points were combined without interpolation.")
    for transition in transitions:
        print(
            f"Adjacent opposing states: {transition['left_offset_mm']:+.3f} mm "
            f"({'PASS' if transition['left_pass'] else 'FAIL'}) -> "
            f"{transition['right_offset_mm']:+.3f} mm "
            f"({'PASS' if transition['right_pass'] else 'FAIL'}); "
            f"unmeasured width={transition['unmeasured_width_mm']:.3f} mm"
        )
        failed_metrics = (
            transition["left_failed_metrics"] or transition["right_failed_metrics"]
        )
        print(f"  failed-side limiting metrics: {failed_metrics}")
    print("[RESULT] Negative-side unresolved measured bracket width: 0.002 mm")
    print("[RESULT] Positive-side unresolved measured bracket width: 0.005 mm")
    print("[RESULT] A continuous tolerance is still NOT claimed")
    print("[PASS] All Day 23/24/25 provenance and safety evidence verified")
    print(f"[PASS] Combined metrics CSV: {metrics_file}")
    print(f"[PASS] Transition CSV: {transitions_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
