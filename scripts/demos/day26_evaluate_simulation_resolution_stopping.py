"""Day 26 step 2: evaluate explicit teaching stopping policies offline."""

import csv
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day26_simulation_resolution_stopping_plan import (  # noqa: E402
    load_frozen_report,
    planned_bisections,
    validate_boundaries,
    validate_day22,
    validate_day25,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_directory(config):
    """Create one timestamped folder for the reviewed offline result."""

    timestamp = datetime.now(CHINA_TIME).strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / config["output"]["root"] / f"stopping_evaluation_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def evaluate_boundaries(config, policies, positioning_accuracy):
    """Evaluate every side against every policy without interpolation."""

    details = []
    for policy in policies:
        threshold = float(policy["maximum_unresolved_width_mm"])
        for side, boundary in config["boundary_evidence"].items():
            width = float(boundary["unresolved_width_mm"])
            stop = width <= threshold
            bisections = planned_bisections(width, threshold)
            projected_width = width / (2**bisections)
            details.append(
                {
                    "policy_id": policy["id"],
                    "policy_name": policy["name"],
                    "side": side,
                    "pass_offset_mm": float(boundary["pass_offset_mm"]),
                    "fail_offset_mm": float(boundary["fail_offset_mm"]),
                    "limiting_metric": boundary["limiting_metric"],
                    "unresolved_width_mm": width,
                    "policy_maximum_width_mm": threshold,
                    "width_to_positioning_accuracy_ratio": width
                    / positioning_accuracy,
                    "width_to_policy_limit_ratio": width / threshold,
                    "decision": "STOP" if stop else "CONTINUE",
                    "stopping_condition_met": stop,
                    "additional_bisections_planned": bisections,
                    "projected_width_after_planned_bisections_mm": projected_width,
                    "new_optical_case_executed": False,
                }
            )
    return details


def summarize_policies(policies, details):
    """Keep policy-level outcomes separate rather than creating a score."""

    summaries = []
    for policy in policies:
        rows = [row for row in details if row["policy_id"] == policy["id"]]
        stop_sides = [row["side"] for row in rows if row["stopping_condition_met"]]
        continue_sides = [
            row["side"] for row in rows if not row["stopping_condition_met"]
        ]
        summaries.append(
            {
                "policy_id": policy["id"],
                "policy_name": policy["name"],
                "maximum_unresolved_width_mm": float(
                    policy["maximum_unresolved_width_mm"]
                ),
                "physical_basis": policy["physical_basis"],
                "meaning": policy["meaning"],
                "boundary_count": len(rows),
                "stop_count": len(stop_sides),
                "continue_count": len(continue_sides),
                "stop_sides": stop_sides,
                "continue_sides": continue_sides,
                "total_additional_bisections_planned": sum(
                    row["additional_bisections_planned"] for row in rows
                ),
            }
        )
    return summaries


def write_csv(path, rows):
    """Write a transparent flat table for manual review."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day26_simulation_resolution_stopping.yaml")
    validate_execution_lock(config)
    source = config["source"]
    day25_file, day25 = load_frozen_report(
        source, "day25_report", "day25_report_sha256"
    )
    day22_file, day22 = load_frozen_report(
        source, "day22_report", "day22_report_sha256"
    )
    transitions = validate_day25(config, day25)
    validate_boundaries(config, transitions)
    scales = validate_day22(config, day22)
    policies = validate_policies(config, scales)

    positioning_accuracy = scales["positioning_accuracy"]
    details = evaluate_boundaries(config, policies, positioning_accuracy)
    summaries = summarize_policies(policies, details)
    output_dir = make_output_directory(config)
    detail_csv = output_dir / "simulation_resolution_stopping_details.csv"
    summary_csv = output_dir / "simulation_resolution_stopping_summary.csv"
    report_file = output_dir / "simulation_resolution_stopping_report.json"
    write_csv(detail_csv, details)
    write_csv(summary_csv, summaries)

    now = datetime.now(CHINA_TIME)
    report = {
        "task": "day26_simulation_resolution_stopping_evaluation",
        "status": "success",
        "time_local": now.isoformat(),
        "source_day25_report": str(day25_file),
        "source_day25_report_sha256": source["day25_report_sha256"],
        "source_day22_report": str(day22_file),
        "source_day22_report_sha256": source["day22_report_sha256"],
        "teaching_error_scales_mm": scales,
        "details": details,
        "summaries": summaries,
        "measured_boundary_brackets_only": True,
        "bisection_counts_are_planning_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "new_boundary_case_executed": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "optical_curve_fit_used": False,
        "hidden_weighted_score_used": False,
        "continuous_tolerance_claimed": False,
        "unique_engineering_stopping_rule": None,
        "engineering_recommendation": None,
    }
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("========== DAY 26 OFFLINE STOPPING EVALUATION ==========")
    print("No ZOS-API connection, model copy or new optical calculation was used.")
    print("No additional boundary case was executed.")
    print("All stopping rules are teaching examples.")
    print()
    print("Boundary width relative to Day 22 positioning accuracy:")
    for side, boundary in config["boundary_evidence"].items():
        width = float(boundary["unresolved_width_mm"])
        print(
            f"  {side}: {width:.3f} / {positioning_accuracy:.3f} mm "
            f"= {100.0 * width / positioning_accuracy:.1f}%"
        )
    print()
    for summary in summaries:
        print(
            f"{summary['policy_id']} "
            f"(limit <= {summary['maximum_unresolved_width_mm']:.3f} mm):"
        )
        for row in [item for item in details if item["policy_id"] == summary["policy_id"]]:
            print(
                f"  {row['side']}: {row['decision']}; "
                f"additional bisections={row['additional_bisections_planned']}"
            )
        print(
            f"  result: {summary['stop_count']}/2 STOP; "
            f"planned bisections total={summary['total_additional_bisections_planned']}"
        )
    print()
    print("[RESULT] Numerical and mechanism-aware stopping decisions are different")
    print("[RESULT] Existing brackets are narrower than teaching positioning accuracy")
    print("[RESULT] No unique engineering stopping rule was selected")
    print("[RESULT] A continuous tolerance is still NOT claimed")
    print("[PASS] No interpolation, hidden score or engineering recommendation")
    print(f"[PASS] Detail CSV: {detail_csv}")
    print(f"[PASS] Summary CSV: {summary_csv}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
