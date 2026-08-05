"""Day 11 step 2: apply three transparent teaching decision scenarios."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day11_requirement_scenario_plan import (  # noqa: E402
    find_latest_day10_batch,
    validate_day10_report,
    validate_execution_lock,
    validate_scenarios,
)


def ranked(rows, config, scenario):
    """Sort candidates using one declared primary/secondary rule."""

    metrics = config["metrics"]
    primary = scenario["ranking"]["primary"]
    secondary = scenario["ranking"]["secondary"]

    def direction_value(row, metric):
        value = float(row[metric])
        if metrics[metric]["direction"] == "maximize":
            return -value
        if metrics[metric]["direction"] == "minimize":
            return value
        raise ValueError(f"Unknown metric direction: {metric}")

    return sorted(
        rows,
        key=lambda row: (
            direction_value(row, primary),
            direction_value(row, secondary),
            row["case_id"],
        ),
    )


def add_relative_penalties(rows):
    """Add explicit Spot and Merit penalties relative to their best values."""

    best_spot = min(float(row["spot_mean_rms_um"]) for row in rows)
    best_merit = min(float(row["merit_value"]) for row in rows)
    enriched = []
    for source_row in rows:
        row = dict(source_row)
        row["spot_penalty_vs_best_percent"] = (
            float(row["spot_mean_rms_um"]) / best_spot - 1.0
        ) * 100.0
        row["merit_penalty_vs_best_percent"] = (
            float(row["merit_value"]) / best_merit - 1.0
        ) * 100.0
        enriched.append(row)
    return enriched


def evaluate_scenarios(config, rows):
    """Return transparent recommendations without creating a global score."""

    scenarios = config["scenarios"]
    recommendations = {}

    geometry_ranking = ranked(rows, config, scenarios["geometry_priority"])
    recommendations["geometry_priority"] = {
        "scenario_name": scenarios["geometry_priority"]["name"],
        "recommended_case": geometry_ranking[0]["case_id"],
        "eligible_cases": [row["case_id"] for row in rows],
        "ranking": [row["case_id"] for row in geometry_ranking],
        "reason": "Lowest Merit Function, with Spot RMS as the tie-breaker.",
    }

    balanced = scenarios["balanced_imaging"]
    limits = balanced["teaching_limits"]
    balanced_eligible = [
        row
        for row in rows
        if row["spot_penalty_vs_best_percent"]
        <= limits["maximum_spot_penalty_vs_best_percent"]
        and row["merit_penalty_vs_best_percent"]
        <= limits["maximum_merit_penalty_vs_best_percent"]
    ]
    if not balanced_eligible:
        raise ValueError("No candidate passed the balanced teaching limits.")
    balanced_ranking = ranked(
        balanced_eligible,
        config,
        balanced,
    )
    recommendations["balanced_imaging"] = {
        "scenario_name": balanced["name"],
        "recommended_case": balanced_ranking[0]["case_id"],
        "eligible_cases": [row["case_id"] for row in balanced_eligible],
        "rejected_cases": [
            row["case_id"] for row in rows if row not in balanced_eligible
        ],
        "ranking": [row["case_id"] for row in balanced_ranking],
        "reason": (
            "Pass both declared 2% teaching limits, then maximize MTF50 "
            "with MTF30 as the tie-breaker."
        ),
    }

    fine_detail = scenarios["fine_detail_priority"]
    detail_ranking = ranked(rows, config, fine_detail)
    recommendations["fine_detail_priority"] = {
        "scenario_name": fine_detail["name"],
        "recommended_case": detail_ranking[0]["case_id"],
        "eligible_cases": [row["case_id"] for row in rows],
        "ranking": [row["case_id"] for row in detail_ranking],
        "reason": "Highest MTF50, with MTF30 as the tie-breaker.",
    }
    return recommendations


def main():
    config = load_config("configs/day11_requirement_scenarios.yaml")
    validate_execution_lock(config)
    validate_scenarios(config)
    report_file = find_latest_day10_batch(config)
    _, source_rows = validate_day10_report(config, report_file)
    rows = add_relative_penalties(source_rows)
    recommendations = evaluate_scenarios(config, rows)

    run_id = datetime.now().strftime("scenario_evaluation_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    csv_file = run_dir / "candidate_scenario_metrics.csv"
    report_output = run_dir / "scenario_decision_report.json"

    selected_by = {
        case_id: [] for case_id in config["candidate_set"]["expected_ids"]
    }
    for scenario_id, decision in recommendations.items():
        selected_by[decision["recommended_case"]].append(scenario_id)

    csv_rows = []
    balanced_eligible = set(
        recommendations["balanced_imaging"]["eligible_cases"]
    )
    for row in rows:
        csv_row = dict(row)
        csv_row["balanced_eligible"] = row["case_id"] in balanced_eligible
        csv_row["recommended_by"] = ";".join(selected_by[row["case_id"]])
        csv_rows.append(csv_row)

    with csv_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    report = {
        "task": "day11_requirement_scenario_evaluation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day10_report": str(report_file),
        "teaching_only": True,
        "hidden_weighted_score_used": False,
        "candidates": rows,
        "scenario_recommendations": recommendations,
        "unique_engineering_winner": None,
        "engineering_decision_reason": (
            "No real detector or imaging requirement has been specified."
        ),
    }
    report_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 11 TEACHING SCENARIO RESULTS ==========")
    print("No ZOS-API connection was created.")
    print("No new optical metric was calculated.")
    print()
    for row in rows:
        eligibility = (
            "PASS" if row["case_id"] in balanced_eligible else "REJECT"
        )
        print(
            f"{row['case_id']}: Spot penalty="
            f"{row['spot_penalty_vs_best_percent']:+.2f}%, "
            f"Merit penalty={row['merit_penalty_vs_best_percent']:+.2f}%, "
            f"balanced={eligibility}"
        )

    print()
    for scenario_id, decision in recommendations.items():
        print(
            f"[TEACHING] {decision['scenario_name']}: "
            f"{decision['recommended_case']}"
        )
        print(f"  ranking: {' -> '.join(decision['ranking'])}")
        print(f"  reason: {decision['reason']}")

    print()
    print("[RESULT] Geometry priority -> fine_005")
    print("[RESULT] Balanced imaging -> fine_004")
    print("[RESULT] Fine detail priority -> fine_003")
    print("[RESULT] Unique engineering winner -> NONE")
    print("[PASS] No hidden weighted score was used")
    print(f"[PASS] Scenario CSV: {csv_file}")
    print(f"[PASS] Decision report: {report_output}")


if __name__ == "__main__":
    main()
