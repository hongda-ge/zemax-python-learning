"""Day 11 step 1: audit and print the teaching requirement scenarios."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Guarantee that Day 11 planning cannot connect to Zemax."""

    execution = config["execution"]
    policy = config["decision_policy"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 11 execution must remain disabled.")
    if execution["allow_zosapi_connection"] is not False:
        raise ValueError("Day 11 must not allow a ZOS-API connection.")
    if policy["hidden_weighted_score_allowed"] is not False:
        raise ValueError("Hidden weighted scores are forbidden.")
    if (
        policy["unique_engineering_winner_allowed_without_real_requirements"]
        is not False
    ):
        raise ValueError("A unique engineering winner must remain forbidden.")


def find_latest_day10_batch(config):
    """Find the newest successful Day 10 three-candidate report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day10_output_root"]
    matches = list(
        root.glob("candidate_batch_*/" + source["day10_batch_report_name"])
    )
    if not matches:
        raise FileNotFoundError("No Day 10 candidate batch was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day10_report(config, report_file):
    """Require the reviewed Day 10 metrics and all safety evidence."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    if report.get("task") != "day10_candidate_merit_batch":
        raise ValueError("Unexpected Day 10 report type.")
    if report.get("status") != "success":
        raise ValueError("The Day 10 batch was not successful.")
    if (
        report.get("loaded_definition_sha256")
        != source["expected_loaded_definition_sha256"]
    ):
        raise ValueError("The Day 10 Merit Function fingerprint changed.")
    if report.get("operand_count") != source["expected_operand_count"]:
        raise ValueError("The Day 10 operand count changed.")

    rows = report.get("rows", [])
    actual_ids = [row["case_id"] for row in rows]
    expected_ids = config["candidate_set"]["expected_ids"]
    if actual_ids != expected_ids or len(set(actual_ids)) != len(actual_ids):
        raise ValueError("The Day 11 candidate identities are invalid.")

    if config["candidate_set"]["require_all_safety_checks"]:
        for row in rows:
            checks = {
                "input unchanged": row.get("input_model_unchanged") is True,
                "working unchanged": row.get("working_copy_unchanged") is True,
                "connection closed": row.get("connection_closed") is True,
                "no optimization": row.get("optimization_run") is False,
                "operand count": row.get("operand_count")
                == source["expected_operand_count"],
                "definition": row.get("definition_sha256")
                == source["expected_loaded_definition_sha256"],
            }
            failed = [name for name, passed in checks.items() if not passed]
            if failed:
                raise ValueError(
                    f"{row['case_id']} failed: " + ", ".join(failed)
                )
    return report, rows


def validate_scenarios(config):
    """Confirm every ranking metric exists and has a declared direction."""

    metrics = config["metrics"]
    scenarios = config["scenarios"]
    if len(scenarios) != 3:
        raise ValueError("Day 11 requires exactly three teaching scenarios.")
    for scenario_id, scenario in scenarios.items():
        for level in ("primary", "secondary"):
            metric = scenario["ranking"][level]
            if metric not in metrics:
                raise ValueError(
                    f"Unknown {scenario_id} ranking metric: {metric}"
                )


def main():
    config = load_config("configs/day11_requirement_scenarios.yaml")
    validate_execution_lock(config)
    validate_scenarios(config)
    report_file = find_latest_day10_batch(config)
    _, rows = validate_day10_report(config, report_file)

    print("========== DAY 11 REQUIREMENT SCENARIO PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print("No new optical result will be calculated.")
    print("These are teaching scenarios, not final engineering requirements.")
    print(f"Day 10 report: {report_file}")
    print()
    print("Candidate evidence:")
    for row in rows:
        print(
            f"  {row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"Spot={row['spot_mean_rms_um']:.3f} um, "
            f"MTF30={row['mtf_30_overall_mean']:.4f}, "
            f"MTF50={row['mtf_50_overall_mean']:.4f}, "
            f"Merit={row['merit_value']:.12g}"
        )

    print()
    print("Teaching scenarios:")
    for scenario_id, scenario in config["scenarios"].items():
        ranking = scenario["ranking"]
        print(f"  {scenario_id}: {scenario['name']}")
        print(f"    purpose: {scenario['purpose']}")
        print(
            f"    ranking: {ranking['primary']} -> "
            f"{ranking['secondary']}"
        )
        if "teaching_limits" in scenario:
            limits = scenario["teaching_limits"]
            print(
                "    eligibility: Spot penalty <= "
                f"{limits['maximum_spot_penalty_vs_best_percent']:.1f}%, "
                "Merit penalty <= "
                f"{limits['maximum_merit_penalty_vs_best_percent']:.1f}%"
            )

    print()
    print("[PASS] Three reviewed candidates loaded")
    print("[PASS] Day 10 safety evidence verified")
    print("[PASS] Three explicit teaching scenarios defined")
    print("[PASS] Hidden weighted score forbidden")
    print("[PASS] Unique engineering winner forbidden without real requirements")
    print("PLAN ONLY finished. No decision report or optical output was created.")


if __name__ == "__main__":
    main()
