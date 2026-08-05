"""Day 12 step 1: audit the teaching decision-sensitivity plan."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep the first Day 12 step read-only and independent of Zemax."""

    execution = config["execution"]
    guardrails = config["guardrails"]
    locked_false = {
        "generic execution": execution["enabled"],
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "new optical calculation": execution["allow_new_optical_calculation"],
        "hidden weighted score": guardrails["hidden_weighted_score_allowed"],
        "unique engineering winner": guardrails[
            "unique_engineering_winner_allowed"
        ],
    }
    enabled = [name for name, value in locked_false.items() if value is not False]
    if enabled:
        raise ValueError("Day 12 plan lock failed: " + ", ".join(enabled))

    if not isinstance(execution["allow_sensitivity_evaluation"], bool):
        raise ValueError("The sensitivity evaluation switch must be Boolean.")


def find_latest_day11_report(config):
    """Locate the newest reviewed Day 11 decision report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day11_output_root"]
    matches = list(root.glob("scenario_evaluation_*/" + source["day11_report_name"]))
    if not matches:
        raise FileNotFoundError("No Day 11 decision report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day11_report(config, report_file):
    """Require the reviewed Day 11 candidates and transparent decision evidence."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    if report.get("task") != source["expected_task"]:
        raise ValueError("Unexpected Day 11 report type.")
    if report.get("status") != "success":
        raise ValueError("The Day 11 report was not successful.")
    if report.get("teaching_only") is not True:
        raise ValueError("Day 11 results must remain labelled as teaching only.")
    if report.get("hidden_weighted_score_used") is not False:
        raise ValueError("A hidden weighted score was used in Day 11.")
    if report.get("unique_engineering_winner") is not None:
        raise ValueError("Day 11 unexpectedly declared an engineering winner.")

    rows = report.get("candidates", [])
    actual_ids = [row.get("case_id") for row in rows]
    if actual_ids != source["expected_candidate_ids"]:
        raise ValueError("The Day 11 candidate set or order changed.")

    balanced = report.get("scenario_recommendations", {}).get(
        "balanced_imaging", {}
    )
    if (
        balanced.get("recommended_case")
        != source["expected_day11_balanced_recommendation"]
    ):
        raise ValueError("The reviewed Day 11 balanced recommendation changed.")

    required_fields = {
        "spot_penalty_vs_best_percent",
        "merit_penalty_vs_best_percent",
        "mtf_30_overall_mean",
        "mtf_50_overall_mean",
    }
    for row in rows:
        missing = required_fields.difference(row)
        if missing:
            raise ValueError(
                f"{row['case_id']} is missing: " + ", ".join(sorted(missing))
            )
    return report, rows


def validate_sensitivity_plan(config):
    """Check that threshold values are unique, ordered and include Day 11."""

    values = [float(value) for value in config["sensitivity"]["values_percent"]]
    if not values:
        raise ValueError("The sensitivity threshold list is empty.")
    if values != sorted(values) or len(values) != len(set(values)):
        raise ValueError("Sensitivity thresholds must be unique and increasing.")
    if values[0] < 0.0:
        raise ValueError("A penalty threshold cannot be negative.")
    day11_value = float(config["source"]["expected_day11_threshold_percent"])
    if day11_value not in values:
        raise ValueError("The reviewed Day 11 threshold is missing.")

    ranking = config["sensitivity"]["ranking"]
    if ranking["direction"] != "maximize":
        raise ValueError("Day 12 MTF ranking must maximize the declared metrics.")
    return values


def main():
    config = load_config("configs/day12_decision_sensitivity.yaml")
    validate_execution_lock(config)
    report_file = find_latest_day11_report(config)
    _, rows = validate_day11_report(config, report_file)
    thresholds = validate_sensitivity_plan(config)

    print("========== DAY 12 DECISION SENSITIVITY PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print("No new optical metric will be calculated.")
    print("No sensitivity recommendation will be produced in this step.")
    print(f"Day 11 report: {report_file}")
    print()
    print("Candidate evidence frozen from Day 11:")
    for row in rows:
        print(
            f"  {row['case_id']}: Spot penalty="
            f"{row['spot_penalty_vs_best_percent']:+.2f}%, "
            f"Merit penalty={row['merit_penalty_vs_best_percent']:+.2f}%, "
            f"MTF30={row['mtf_30_overall_mean']:.4f}, "
            f"MTF50={row['mtf_50_overall_mean']:.4f}"
        )

    print()
    print("Planned shared Spot/Merit limits:")
    print("  " + ", ".join(f"{value:.1f}%" for value in thresholds))
    print("At each limit: filter candidates first, then maximize MTF50/MTF30.")
    print()
    print("[PASS] Reviewed Day 11 report loaded")
    print("[PASS] Three candidate identities and metrics verified")
    print("[PASS] Day 11 2.0% threshold included")
    print("[PASS] ZOS-API and new optical calculations locked")
    print("[PASS] Hidden weighted score and engineering winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
