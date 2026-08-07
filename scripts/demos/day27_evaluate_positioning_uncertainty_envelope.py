"""Day 27 step 2: evaluate sampled positioning-uncertainty envelopes offline."""

import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day27_positioning_uncertainty_envelope_plan import (  # noqa: E402
    build_candidate_plan,
    load_frozen_report,
    validate_day22,
    validate_day25,
    validate_execution_lock,
    validate_guardrails,
    validate_thresholds,
)


CHINA_TIME = timezone(timedelta(hours=8))


def failed_metrics(item, limits):
    """Recalculate the four independent failed metrics at full precision."""

    failed = []
    if float(item["spot_mean_rms_um"]) > float(limits["spot_mean_rms_um_max"]):
        failed.append("spot_mean")
    if float(item["spot_worst_rms_um"]) > float(limits["spot_worst_rms_um_max"]):
        failed.append("spot_worst")
    if float(item["mtf30_minimum"]) < float(limits["mtf30_minimum_min"]):
        failed.append("mtf30_minimum")
    if float(item["mtf50_minimum"]) < float(limits["mtf50_minimum_min"]):
        failed.append("mtf50_minimum")
    return failed


def evaluate_candidates(config, points, plan):
    """Evaluate exact center/end-point samples without filling the interior."""

    limits = config["balanced_acceptance"]["limits"]
    details = []
    summaries = []
    for candidate in plan:
        candidate_rows = []
        for state in candidate["states"]:
            item = points[state["measured_offset_mm"]]
            failed = failed_metrics(item, limits)
            row = {
                "candidate_id": candidate["candidate_id"],
                "command_offset_mm": candidate["command_offset_mm"],
                "state_id": state["state_id"],
                "relative_offset_mm": state["relative_offset_mm"],
                "measured_offset_mm": state["measured_offset_mm"],
                "source_day": item["source_day"],
                "source_case_id": item["case_id"],
                "spot_mean_rms_um": item["spot_mean_rms_um"],
                "spot_worst_rms_um": item["spot_worst_rms_um"],
                "mtf30_minimum": item["mtf30_minimum"],
                "mtf50_minimum": item["mtf50_minimum"],
                "sampled_state_pass": not failed,
                "failed_metrics": ";".join(failed),
            }
            details.append(row)
            candidate_rows.append(row)
        failed_rows = [row for row in candidate_rows if not row["sampled_state_pass"]]
        summaries.append(
            {
                "candidate_id": candidate["candidate_id"],
                "command_offset_mm": candidate["command_offset_mm"],
                "teaching_positioning_uncertainty_mm": float(
                    config["teaching_positioning_uncertainty"][
                        "symmetric_allowance_mm"
                    ]
                ),
                "sampled_state_count": len(candidate_rows),
                "passed_sampled_state_count": len(candidate_rows) - len(failed_rows),
                "failed_sampled_state_count": len(failed_rows),
                "sampled_envelope_pass": not failed_rows,
                "failed_state_ids": [row["state_id"] for row in failed_rows],
                "failed_measured_offsets_mm": [
                    row["measured_offset_mm"] for row in failed_rows
                ],
                "failed_metrics_by_state": {
                    row["state_id"]: row["failed_metrics"] for row in failed_rows
                },
                "continuous_interval_pass_claimed": False,
            }
        )
    return details, summaries


def make_output_directory(config):
    """Create one timestamped offline-result directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("%Y%m%d_%H%M%S")
    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / f"envelope_evaluation_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_csv(path, rows):
    """Write reviewable UTF-8 CSV evidence."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day27_positioning_uncertainty_envelope.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    source = config["source"]
    day25_file, day25 = load_frozen_report(
        source, "day25_report", "day25_report_sha256"
    )
    day22_file, day22 = load_frozen_report(
        source, "day22_report", "day22_report_sha256"
    )
    points = validate_day25(config, day25)
    uncertainty = validate_day22(config, day22)
    validate_thresholds(config, points)
    plan = build_candidate_plan(config, points)
    details, summaries = evaluate_candidates(config, points, plan)

    output_dir = make_output_directory(config)
    detail_csv = output_dir / "positioning_envelope_sample_details.csv"
    summary_csv = output_dir / "positioning_envelope_candidate_summary.csv"
    report_file = output_dir / "positioning_uncertainty_envelope_report.json"
    write_csv(detail_csv, details)
    write_csv(summary_csv, summaries)

    passing = [item["candidate_id"] for item in summaries if item["sampled_envelope_pass"]]
    failing = [
        item["candidate_id"] for item in summaries if not item["sampled_envelope_pass"]
    ]
    report = {
        "task": "day27_positioning_uncertainty_envelope_evaluation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day25_report": str(day25_file),
        "source_day25_report_sha256": source["day25_report_sha256"],
        "source_day22_report": str(day22_file),
        "source_day22_report_sha256": source["day22_report_sha256"],
        "teaching_positioning_uncertainty_mm": uncertainty,
        "is_real_mechanism_specification": False,
        "combination_rule": "all_three_sampled_states_must_pass",
        "balanced_acceptance_limits": config["balanced_acceptance"]["limits"],
        "details": details,
        "summaries": summaries,
        "sampled_envelope_pass_candidates": passing,
        "sampled_envelope_fail_candidates": failing,
        "measured_points_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "new_residual_defocus_case_executed": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "optical_curve_fit_used": False,
        "unmeasured_interior_assumed_to_pass": False,
        "hidden_weighted_score_used": False,
        "continuous_acceptance_interval_claimed": False,
        "unique_engineering_winner": None,
        "engineering_recommendation": None,
    }
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("========== DAY 27 OFFLINE POSITIONING-ENVELOPE RESULTS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print(f"Teaching positioning uncertainty: +/-{uncertainty:.3f} mm")
    print("Each candidate uses three exact measured states only.")
    print()
    for summary in summaries:
        state = "PASS" if summary["sampled_envelope_pass"] else "FAIL"
        print(
            f"{summary['candidate_id']}: command={summary['command_offset_mm']:+.3f} mm "
            f"-> sampled envelope {state} "
            f"({summary['passed_sampled_state_count']}/3 states passed)"
        )
        if not summary["sampled_envelope_pass"]:
            for state_id, metrics in summary["failed_metrics_by_state"].items():
                row = next(
                    item
                    for item in details
                    if item["candidate_id"] == summary["candidate_id"]
                    and item["state_id"] == state_id
                )
                print(
                    f"  failed {state_id} at {row['measured_offset_mm']:+.3f} mm: "
                    f"{metrics}"
                )
    print()
    print(f"[RESULT] Sampled-envelope PASS candidates: {', '.join(passing)}")
    print(f"[RESULT] Sampled-envelope FAIL candidates: {', '.join(failing)}")
    print("[RESULT] Passing three samples does not prove the continuous interior")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] No interpolation, hidden score or engineering recommendation")
    print(f"[PASS] Detail CSV: {detail_csv}")
    print(f"[PASS] Summary CSV: {summary_csv}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
