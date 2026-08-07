"""Day 20 step 1: audit and print the focus-travel budget plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Guarantee that the plan cannot run Zemax or produce a decision."""

    execution = config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 20 execution must remain disabled.")
    reviewed_flags = (
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_model_copy",
        "allow_offline_evaluation",
        "allow_engineering_recommendation",
    )
    invalid = [
        key for key in reviewed_flags if not isinstance(execution[key], bool)
    ]
    if invalid:
        raise ValueError("Day 20 execution flag is not Boolean: " + ", ".join(invalid))
    for forbidden in (
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_model_copy",
        "allow_engineering_recommendation",
    ):
        if execution[forbidden] is not False:
            raise ValueError(f"Day 20 forbidden action is enabled: {forbidden}.")


def find_latest_report(root_name, report_name):
    """Find the newest report below a dated output directory."""

    root = PROJECT_ROOT / root_name
    matches = list(root.glob(f"**/{report_name}"))
    if not matches:
        raise FileNotFoundError(f"Required report not found: {report_name}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day8(config, report_file):
    """Require nine successful preserve-Solve focus samples."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    rows = report.get("rows", [])
    checks = {
        "task": report.get("task") == config["source"]["day8_expected_task"],
        "status": report.get("status") == "success",
        "case count": report.get("case_count") == 9,
        "success count": report.get("success_count") == 9,
        "rejected count": report.get("rejected_count") == 0,
        "nine rows": len(rows) == config["coverage"]["preserve_solve_grid"][
            "expected_point_count"
        ],
        "all successful": all(row.get("status") == "success" for row in rows),
        "one baseline": sum(bool(row.get("is_baseline")) for row in rows) == 1,
    }
    expected_deltas = [round(-0.4 + index * 0.1, 7) for index in range(9)]
    actual_deltas = sorted(round(float(row["delta_mm"]), 7) for row in rows)
    checks["complete grid"] = actual_deltas == expected_deltas
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 8 focus evidence failed: " + ", ".join(failed))
    return report, sorted(rows, key=lambda row: float(row["delta_mm"]))


def validate_day17(config, report_file, day8_file):
    """Require six audited paired-branch focus rows."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    rows = report.get("trend_rows", [])
    checks = {
        "task": report.get("task") == config["source"]["day17_expected_task"],
        "status": report.get("status") == "success",
        "source hash": report.get("source_sha256", "").upper()
        == config["source"]["expected_source_sha256"].upper(),
        "Day 8 provenance": Path(report.get("source_day8_report", "")).resolve()
        == day8_file.resolve(),
        "six rows": len(rows)
        == config["coverage"]["dual_branch_audit"]["expected_point_count"],
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    expected_deltas = sorted(
        float(value)
        for value in config["coverage"]["dual_branch_audit"][
            "sampled_deltas_mm"
        ]
    )
    actual_deltas = sorted(float(row["delta_mm"]) for row in rows)
    checks["audited deltas"] = all(
        math.isclose(actual, expected, abs_tol=1e-12)
        for actual, expected in zip(actual_deltas, expected_deltas)
    )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 17 branch evidence failed: " + ", ".join(failed))
    return report, sorted(rows, key=lambda row: float(row["delta_mm"]))


def validate_day19(config, report_file):
    """Require evidence that focus materially recovered MTF."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    rows = report.get("rows", [])
    checks = {
        "task": report.get("task") == config["source"]["day19_expected_task"],
        "status": report.get("status") == "success",
        "four rows": len(rows) == 4,
        "positive recoveries": all(
            float(row["preserve_mean_recovery"]) > 0.0
            and float(row["frozen_mean_recovery"]) > 0.0
            for row in rows
        ),
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated")
        is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 19 compensation evidence failed: " + ", ".join(failed))
    return report


def validate_limits(config):
    """Require ordered, positive teaching half-travel limits."""

    limits = [
        float(value)
        for value in config["compensator"][
            "teaching_symmetric_half_travel_limits_mm"
        ]
    ]
    if limits != sorted(set(limits)) or any(value <= 0.0 for value in limits):
        raise ValueError("Day 20 teaching travel limits are invalid.")
    if config["compensator"]["limits_are_engineering_requirements"] is not False:
        raise ValueError("Teaching limits cannot be engineering requirements.")
    if config["coverage"]["interpolation_allowed"] is not False:
        raise ValueError("Day 20 interpolation must remain forbidden.")
    if config["coverage"]["extrapolation_allowed"] is not False:
        raise ValueError("Day 20 extrapolation must remain forbidden.")
    return limits


def main():
    config = load_config("configs/day20_focus_travel_budget.yaml")
    validate_execution_lock(config)
    source = config["source"]
    day8_file = find_latest_report(
        source["day8_output_root"],
        source["day8_report_name"],
    )
    day17_file = find_latest_report(
        source["day17_output_root"],
        source["day17_report_name"],
    )
    day19_file = find_latest_report(
        source["day19_output_root"],
        source["day19_report_name"],
    )
    _, day8_rows = validate_day8(config, day8_file)
    _, day17_rows = validate_day17(config, day17_file, day8_file)
    validate_day19(config, day19_file)
    limits = validate_limits(config)

    print("========== DAY 20 FOCUS-TRAVEL BUDGET PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("The travel limits are teaching scenarios, not mechanism requirements.")
    print(f"Day 8 preserve-Solve evidence: {day8_file}")
    print(f"Day 17 paired-branch evidence: {day17_file}")
    print(f"Day 19 MTF recovery evidence: {day19_file}")
    print(
        "Teaching symmetric half-travel limits: "
        + ", ".join(f"+/-{value:.2f} mm" for value in limits)
    )
    print()
    print("Day 8 preserve-Solve grid (9 measured points):")
    for row in day8_rows:
        print(
            f"  {row['case_id']}: delta={float(row['delta_mm']):+.1f} mm, "
            f"focus shift={float(row['focus_shift_mm']):+.7f} mm"
        )
    print()
    print("Day 17 dual-branch audit (6 measured points):")
    for row in day17_rows:
        robust_requirement = max(
            abs(float(row["preserve_focus_shift_mm"])),
            abs(float(row["frozen_focus_shift_mm"])),
        )
        print(
            f"  delta={float(row['delta_mm']):+.1f} mm: "
            f"preserve={float(row['preserve_focus_shift_mm']):+.7f}, "
            f"frozen={float(row['frozen_focus_shift_mm']):+.7f}, "
            f"robust requirement={robust_requirement:.7f} mm"
        )
    print()
    print("Planned offline evaluation:")
    print("  1. Test each measured focus shift against each half-travel limit")
    print("  2. Report remaining travel margin, never interpolate a boundary")
    print("  3. Compare 9-point preserve-only and 6-point dual-branch coverage")
    print("  4. List uncovered measured cases instead of hiding them in a score")
    print()
    print("[PASS] Nine successful Day 8 focus samples verified")
    print("[PASS] Six audited Day 17 paired-branch samples verified")
    print("[PASS] Day 19 demonstrated material MTF recovery after focus")
    print("[PASS] Three explicit teaching travel limits verified")
    print("[PASS] Interpolation, extrapolation and engineering claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
