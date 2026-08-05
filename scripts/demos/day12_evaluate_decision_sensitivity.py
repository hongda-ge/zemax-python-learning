"""Day 12 step 2: evaluate the transparent teaching-limit sensitivity."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day12_decision_sensitivity_plan import (  # noqa: E402
    find_latest_day11_report,
    validate_day11_report,
    validate_execution_lock,
    validate_sensitivity_plan,
)


def require_reviewed_execution(config):
    """Allow only the reviewed, read-only sensitivity calculation."""

    execution = config["execution"]
    if execution["allow_sensitivity_evaluation"] is not True:
        raise ValueError("Day 12 sensitivity evaluation has not been approved.")
    if execution["allow_zosapi_connection"] is not False:
        raise ValueError("Day 12 must not connect to ZOS-API.")
    if execution["allow_new_optical_calculation"] is not False:
        raise ValueError("Day 12 must not calculate new optical metrics.")


def required_limit(row):
    """Return the smallest shared limit that makes one candidate eligible."""

    return max(
        float(row["spot_penalty_vs_best_percent"]),
        float(row["merit_penalty_vs_best_percent"]),
    )


def rank_by_mtf(rows, config):
    """Rank eligible candidates by the two declared MTF metrics."""

    ranking = config["sensitivity"]["ranking"]
    primary = ranking["primary"]
    secondary = ranking["secondary"]
    return sorted(
        rows,
        key=lambda row: (
            -float(row[primary]),
            -float(row[secondary]),
            row["case_id"],
        ),
    )


def evaluate_thresholds(config, source_rows, thresholds):
    """Apply filter-first, rank-second logic at every reviewed limit."""

    rows = []
    for threshold in thresholds:
        eligible = [
            row for row in source_rows if required_limit(row) <= threshold
        ]
        if not eligible and config["guardrails"][
            "require_at_least_one_eligible_candidate"
        ]:
            raise ValueError(f"No candidate is eligible at {threshold:.1f}%.")
        ranking = rank_by_mtf(eligible, config)
        rows.append(
            {
                "threshold_percent": threshold,
                "eligible_cases": [row["case_id"] for row in eligible],
                "ranking": [row["case_id"] for row in ranking],
                "recommended_case": ranking[0]["case_id"] if ranking else None,
            }
        )
    return rows


def build_recommendation_regions(rows):
    """Group adjacent sampled thresholds with the same recommendation."""

    regions = []
    for row in rows:
        recommendation = row["recommended_case"]
        if regions and regions[-1]["recommended_case"] == recommendation:
            regions[-1]["maximum_sampled_threshold_percent"] = row[
                "threshold_percent"
            ]
            regions[-1]["sample_count"] += 1
        else:
            regions.append(
                {
                    "minimum_sampled_threshold_percent": row[
                        "threshold_percent"
                    ],
                    "maximum_sampled_threshold_percent": row[
                        "threshold_percent"
                    ],
                    "recommended_case": recommendation,
                    "sample_count": 1,
                }
            )
    return regions


def main():
    config = load_config("configs/day12_decision_sensitivity.yaml")
    validate_execution_lock(config)
    require_reviewed_execution(config)
    report_file = find_latest_day11_report(config)
    _, source_rows = validate_day11_report(config, report_file)
    thresholds = validate_sensitivity_plan(config)
    results = evaluate_thresholds(config, source_rows, thresholds)

    day11_threshold = float(config["source"]["expected_day11_threshold_percent"])
    day11_row = next(
        row for row in results if row["threshold_percent"] == day11_threshold
    )
    expected = config["source"]["expected_day11_balanced_recommendation"]
    if day11_row["recommended_case"] != expected:
        raise ValueError("The 2.0% result does not reproduce Day 11.")

    run_id = datetime.now().strftime("sensitivity_evaluation_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    csv_file = run_dir / "threshold_sensitivity.csv"
    report_file_output = run_dir / "decision_sensitivity_report.json"

    csv_rows = [
        {
            "threshold_percent": row["threshold_percent"],
            "eligible_cases": ";".join(row["eligible_cases"]),
            "ranking": ";".join(row["ranking"]),
            "recommended_case": row["recommended_case"],
        }
        for row in results
    ]
    with csv_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    candidate_entry_limits = {
        row["case_id"]: required_limit(row) for row in source_rows
    }
    regions = build_recommendation_regions(results)
    report = {
        "task": "day12_decision_threshold_sensitivity",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day11_report": str(report_file),
        "teaching_only": True,
        "zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "hidden_weighted_score_used": False,
        "unique_engineering_winner": None,
        "candidate_entry_limits_percent": candidate_entry_limits,
        "threshold_results": results,
        "sampled_recommendation_regions": regions,
    }
    report_file_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 12 DECISION SENSITIVITY RESULTS ==========")
    print("No ZOS-API connection was created.")
    print("No new optical metric was calculated.")
    print()
    print("Smallest shared limit required by each candidate:")
    for case_id, limit in candidate_entry_limits.items():
        print(f"  {case_id}: {limit:.2f}%")

    print()
    for row in results:
        eligible = ", ".join(row["eligible_cases"])
        print(
            f"Limit {row['threshold_percent']:.1f}%: "
            f"eligible=[{eligible}] -> {row['recommended_case']}"
        )

    print()
    print("Sampled recommendation regions:")
    for region in regions:
        low = region["minimum_sampled_threshold_percent"]
        high = region["maximum_sampled_threshold_percent"]
        print(
            f"  {low:.1f}% to {high:.1f}% -> "
            f"{region['recommended_case']}"
        )

    print()
    print(f"[PASS] Day 11 2.0% result reproduced: {expected}")
    print("[PASS] Filter-first and MTF-rank-second logic applied")
    print("[PASS] No hidden weighted score or engineering winner")
    print(f"[PASS] Sensitivity CSV: {csv_file}")
    print(f"[PASS] Decision report: {report_file_output}")


if __name__ == "__main__":
    main()
