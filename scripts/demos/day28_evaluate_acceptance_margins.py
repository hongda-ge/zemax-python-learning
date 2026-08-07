"""Day 28 step 2: evaluate independent acceptance margins offline."""

import csv
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day28_acceptance_margin_audit_plan import (  # noqa: E402
    load_day27_report,
    validate_candidates,
    validate_day27,
    validate_execution_lock,
    validate_guardrails,
    validate_limits,
)


CHINA_TIME = timezone(timedelta(hours=8))
METRICS = (
    "spot_mean_rms_um",
    "spot_worst_rms_um",
    "mtf30_minimum",
    "mtf50_minimum",
)


def calculate_margin(metric, value, limits):
    """Calculate one signed margin, with positive meaning pass."""

    if metric == "spot_mean_rms_um":
        return float(limits["spot_mean_rms_um_max"]) - float(value)
    if metric == "spot_worst_rms_um":
        return float(limits["spot_worst_rms_um_max"]) - float(value)
    if metric == "mtf30_minimum":
        return float(value) - float(limits["mtf30_minimum_min"])
    if metric == "mtf50_minimum":
        return float(value) - float(limits["mtf50_minimum_min"])
    raise ValueError(f"Unknown Day 28 metric: {metric}.")


def evaluate_state_margins(selected, limits):
    """Create one flat row per candidate, sampled state and metric."""

    rows = []
    for summary, states in selected:
        for state in states:
            for metric in METRICS:
                margin = calculate_margin(metric, state[metric], limits)
                rows.append(
                    {
                        "candidate_id": summary["candidate_id"],
                        "command_offset_mm": float(summary["command_offset_mm"]),
                        "state_id": state["state_id"],
                        "relative_offset_mm": float(state["relative_offset_mm"]),
                        "measured_offset_mm": float(state["measured_offset_mm"]),
                        "source_case_id": state["source_case_id"],
                        "metric": metric,
                        "measured_value": float(state[metric]),
                        "signed_margin": margin,
                        "margin_positive": margin >= 0.0,
                        "unit": "um" if metric.startswith("spot_") else "dimensionless",
                    }
                )
    return rows


def summarize_candidate_margins(selected, rows):
    """Take the minimum sampled margin independently for every metric."""

    summaries = []
    for candidate, _states in selected:
        candidate_id = candidate["candidate_id"]
        summary = {
            "candidate_id": candidate_id,
            "command_offset_mm": float(candidate["command_offset_mm"]),
            "sampled_state_count": 3,
        }
        for metric in METRICS:
            metric_rows = [
                row
                for row in rows
                if row["candidate_id"] == candidate_id and row["metric"] == metric
            ]
            minimum = min(row["signed_margin"] for row in metric_rows)
            limiting = [
                row
                for row in metric_rows
                if math.isclose(row["signed_margin"], minimum, abs_tol=1e-12)
            ]
            summary[f"{metric}_minimum_sampled_margin"] = minimum
            summary[f"{metric}_limiting_state_ids"] = [
                row["state_id"] for row in limiting
            ]
            summary[f"{metric}_limiting_offsets_mm"] = [
                row["measured_offset_mm"] for row in limiting
            ]
        summary["all_minimum_sampled_margins_positive"] = all(
            float(summary[f"{metric}_minimum_sampled_margin"]) >= 0.0
            for metric in METRICS
        )
        summaries.append(summary)
    return summaries


def find_separate_metric_leaders(summaries):
    """Report margin leaders per metric without combining their units."""

    leaders = []
    for metric in METRICS:
        key = f"{metric}_minimum_sampled_margin"
        best = max(float(item[key]) for item in summaries)
        winner_ids = [
            item["candidate_id"]
            for item in summaries
            if math.isclose(float(item[key]), best, abs_tol=1e-12)
        ]
        leaders.append(
            {
                "metric": metric,
                "largest_minimum_sampled_margin": best,
                "unit": "um" if metric.startswith("spot_") else "dimensionless",
                "leader_candidate_ids": winner_ids,
            }
        )
    return leaders


def make_output_directory(config):
    """Create one timestamped offline audit directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / config["output"]["root"] / f"margin_audit_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_csv(path, rows):
    """Write UTF-8 CSV evidence for manual review."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day28_acceptance_margin_audit.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    report_file, day27 = load_day27_report(config)
    details, day27_summaries = validate_day27(config, day27)
    limits = validate_limits(config, day27)
    selected = validate_candidates(config, details, day27_summaries)

    state_rows = evaluate_state_margins(selected, limits)
    candidate_summaries = summarize_candidate_margins(selected, state_rows)
    leaders = find_separate_metric_leaders(candidate_summaries)
    if not all(item["all_minimum_sampled_margins_positive"] for item in candidate_summaries):
        raise ValueError("A Day 27 passing candidate has a negative Day 28 margin.")

    output_dir = make_output_directory(config)
    detail_csv = output_dir / "sampled_state_acceptance_margins.csv"
    summary_csv = output_dir / "candidate_minimum_sampled_margins.csv"
    leader_csv = output_dir / "separate_metric_margin_leaders.csv"
    report_output = output_dir / "acceptance_margin_audit_report.json"
    write_csv(detail_csv, state_rows)
    write_csv(summary_csv, candidate_summaries)
    write_csv(leader_csv, leaders)

    report = {
        "task": "day28_acceptance_margin_audit_evaluation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day27_report": str(report_file),
        "source_day27_report_sha256": config["source"]["day27_report_sha256"],
        "balanced_acceptance_limits": limits,
        "margin_definitions": config["margin_definitions"],
        "state_level_margins": state_rows,
        "candidate_minimum_sampled_margins": candidate_summaries,
        "separate_metric_margin_leaders": leaders,
        "cross_unit_margin_sum_used": False,
        "normalized_total_score_used": False,
        "hidden_weighted_score_used": False,
        "measured_points_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "optical_curve_fit_used": False,
        "continuous_interval_claimed": False,
        "unique_engineering_winner": None,
        "engineering_recommendation": None,
    }
    report_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("========== DAY 28 OFFLINE ACCEPTANCE-MARGIN RESULTS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print("All margins are minimum values across three exact sampled states.")
    print("Spot and MTF margins remain separate because their units differ.")
    print()
    for summary in candidate_summaries:
        print(
            f"{summary['candidate_id']}: command={summary['command_offset_mm']:+.3f} mm"
        )
        for metric in METRICS:
            margin = summary[f"{metric}_minimum_sampled_margin"]
            offsets = summary[f"{metric}_limiting_offsets_mm"]
            unit = " um" if metric.startswith("spot_") else ""
            formatted_offsets = ", ".join(f"{value:+.3f}" for value in offsets)
            print(
                f"  {metric}: minimum margin={margin:+.6f}{unit}, "
                f"limiting measured offset(s)=[{formatted_offsets}] mm"
            )
    print()
    print("Separate metric leaders by largest minimum sampled margin:")
    for leader in leaders:
        unit = " um" if leader["unit"] == "um" else ""
        print(
            f"  {leader['metric']}: {', '.join(leader['leader_candidate_ids'])}, "
            f"margin={leader['largest_minimum_sampled_margin']:+.6f}{unit}"
        )
    print()
    print("[RESULT] Both candidates retain positive margins in all four metrics")
    print("[RESULT] Different metrics can favor different candidates")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] No cross-unit sum, normalized total score or hidden weighting")
    print("[PASS] No interpolation or continuous interval claim")
    print(f"[PASS] State-margin CSV: {detail_csv}")
    print(f"[PASS] Candidate summary CSV: {summary_csv}")
    print(f"[PASS] Metric leaders CSV: {leader_csv}")
    print(f"[PASS] Report: {report_output}")


if __name__ == "__main__":
    main()
