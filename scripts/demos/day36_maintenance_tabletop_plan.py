"""Day 36 step 1: plan an end-to-end maintenance tabletop drill."""

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Allow reports while keeping Day 36 offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 36 execution switch must be Boolean.")
    if execution.get("allow_tabletop_report_generation") is not True:
        raise ValueError("Day 36 tabletop report generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_tabletop_report_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 36 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate tabletop-only semantics and manual gates."""

    policy = config["tabletop_policy"]
    required_true = (
        "use_day35_checkpoints_in_order",
        "use_frozen_day31_impact_scenario",
        "use_frozen_day33_resource_slots",
        "use_frozen_day34_failure_partition",
        "label_every_route_state_simulated",
        "require_manual_decision_at_cp06_cp09_cp10",
        "do_not_resume_blocked_without_repair",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise ValueError("Day 36 tabletop policy is incomplete.")
    if policy.get("real_task_execution_allowed") is not False:
        raise ValueError("Day 36 real task execution must remain forbidden.")
    validation = config["validation"]
    forbidden = (
        "real_result_claim_allowed",
        "automatic_execution_allowed",
        "hidden_readiness_score_allowed",
        "engineering_approval_claim_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden):
        raise ValueError("A forbidden Day 36 claim was enabled.")


def load_runbook_and_sources(config):
    """Verify Day 35 and reload its embedded frozen source manifest."""

    source = config["source"]
    runbook_path = PROJECT_ROOT / source["day35_runbook"]
    if not runbook_path.is_file():
        raise FileNotFoundError(f"Day 35 runbook not found: {runbook_path}")
    if sha256_file(runbook_path) != source["day35_runbook_sha256"]:
        raise ValueError("The frozen Day 35 runbook SHA256 is incorrect.")
    runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
    checks = (
        runbook["task"] == source["expected_task"],
        runbook["status"] == source["expected_status"],
        runbook["source_count"] == int(source["expected_source_count"]),
        runbook["checkpoint_count"] == int(source["expected_checkpoint_count"]),
        runbook["automatic_execution_performed"] is False,
    )
    if not all(checks):
        raise ValueError("The frozen Day 35 runbook metadata is incorrect.")

    reports = {}
    for item in runbook["sources"]:
        path = Path(item["path"])
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Embedded Day 35 source changed: {item['role']}")
        reports[item["role"]] = json.loads(path.read_text(encoding="utf-8"))
    return runbook_path, runbook, reports


def find_impact_scenario(config, reports):
    """Reproduce the selected Day 31 review set."""

    scenario_id = config["drill_scenario"]["selected_impact_scenario"]
    scenario = next(
        (item for item in reports["change_impact_analysis"]["scenarios"]
         if item["scenario_id"] == scenario_id),
        None,
    )
    if scenario is None:
        raise ValueError(f"Day 36 impact scenario not found: {scenario_id}")
    expected = [int(day) for day in config["drill_scenario"]["expected_review_days"]]
    if sorted(int(day) for day in scenario["review_order"]) != expected:
        raise ValueError("Day 36 review set no longer matches Day 31.")
    return scenario


def find_schedule_scenario(config, reports):
    """Reproduce the selected Day 33 resource slots."""

    scenario_id = config["drill_scenario"]["selected_impact_scenario"]
    scenario = next(
        (item for item in reports["resource_feasible_schedule"]["scenarios"]
         if item["scenario_id"] == scenario_id),
        None,
    )
    if scenario is None:
        raise ValueError(f"Day 36 schedule scenario not found: {scenario_id}")
    actual = [
        {"slot": int(item["slot"]), "days": [int(day) for day in item["days"]]}
        for item in scenario["slots"]
    ]
    expected = [
        {"slot": int(item["slot"]), "days": [int(day) for day in item["days"]]}
        for item in config["drill_scenario"]["expected_resource_slots"]
    ]
    if actual != expected:
        raise ValueError("Day 36 resource slots no longer match Day 33.")
    return scenario


def find_failure_drill(config, reports):
    """Reproduce the selected Day 34 failure partition."""

    route = config["routes"]["failure_route"]
    drill = next(
        (item for item in reports["failure_gate_propagation"]["drills"]
         if int(item["failed_day"]) == int(route["failed_day"])
         and item["schedule_scenario"] == config["drill_scenario"]["selected_impact_scenario"]),
        None,
    )
    if drill is None:
        raise ValueError("Day 36 failure drill not found in Day 34 evidence.")
    checks = (
        int(drill["failed_slot"]) == int(route["failed_slot"]),
        drill["pass_days"] == [int(day) for day in route["expected_pass_days"]],
        drill["blocked_days"] == [int(day) for day in route["expected_blocked_days"]],
        drill["reviewable_days"] == [int(day) for day in route["expected_reviewable_days"]],
    )
    if not all(checks):
        raise ValueError("Day 36 failure partition no longer matches Day 34.")
    return drill


def build_tabletop_plan(config, runbook, impact, schedule, failure):
    """Create two explicitly simulated route summaries."""

    checkpoints = runbook["checkpoints"]
    normal = config["routes"]["normal_route"]
    failure_route = config["routes"]["failure_route"]
    if len(checkpoints) != int(normal["expected_checkpoint_count"]):
        raise ValueError("Day 36 normal route does not cover all checkpoints.")
    normal_states = [
        {
            "order": row["order"],
            "checkpoint_id": row["checkpoint_id"],
            "simulated_status": normal["checkpoint_status"],
            "manual_decision_required": row["manual_decision_required"],
            "actually_executed": False,
        }
        for row in checkpoints
    ]
    failure_states = []
    for row in checkpoints:
        if int(row["order"]) < 9:
            status = "SIMULATED_PASS"
        elif int(row["order"]) == 9:
            status = failure_route["failed_status"]
        else:
            status = failure_route["recovery_status"]
        failure_states.append(
            {
                "order": row["order"],
                "checkpoint_id": row["checkpoint_id"],
                "simulated_status": status,
                "manual_decision_required": row["manual_decision_required"],
                "actually_executed": False,
            }
        )
    if any(not state["simulated_status"].startswith("SIMULATED_") for state in normal_states + failure_states):
        raise ValueError("A Day 36 route state lacks the SIMULATED label.")
    return {
        "changed_day": int(config["drill_scenario"]["changed_day"]),
        "review_days": [int(day) for day in impact["review_order"]],
        "resource_slots": [
            {"slot": int(item["slot"]), "days": [int(day) for day in item["days"]]}
            for item in schedule["slots"]
        ],
        "normal_route": {
            "route_id": normal["id"],
            "checkpoint_states": normal_states,
            "final_status": "SIMULATED_COMPLETE",
            "actually_executed": False,
        },
        "failure_route": {
            "route_id": failure_route["id"],
            "failed_day": int(failure["failed_day"]),
            "failed_slot": int(failure["failed_slot"]),
            "pass_days": failure["pass_days"],
            "blocked_days": failure["blocked_days"],
            "reviewable_days": failure["reviewable_days"],
            "checkpoint_states": failure_states,
            "final_status": "SIMULATED_WAITING_FOR_REPAIR_AND_APPROVAL",
            "actually_executed": False,
        },
    }


def print_introduction(config):
    """Print the fixed teaching introduction."""

    intro = config["teaching_introduction"]
    print("========== TODAY'S INTRODUCTION ==========")
    print(f"Why today: {intro['why_today']}")
    print(f"Link to yesterday: {intro['relation_to_previous_day']}")
    print("Core concepts:")
    for concept in intro["concepts"]:
        print(f"  - {concept}")
    print(f"Completion standard: {intro['completion_standard']}")
    print()


def main():
    config = load_config("configs/day36_maintenance_tabletop_drill.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    runbook_path, runbook, reports = load_runbook_and_sources(config)
    impact = find_impact_scenario(config, reports)
    schedule = find_schedule_scenario(config, reports)
    failure = find_failure_drill(config, reports)
    plan = build_tabletop_plan(config, runbook, impact, schedule, failure)

    print_introduction(config)
    print("========== DAY 36 MAINTENANCE TABLETOP PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, optical calculation or historical task execution will occur.")
    print("Every route state is simulated and must not be interpreted as a measured result.")
    print(f"Day 35 runbook: {runbook_path}")
    print(f"Hypothetical change: Day{plan['changed_day']} error-budget values")
    print(f"Review set: {plan['review_days']}")
    print("Resource slots:")
    for slot in plan["resource_slots"]:
        print(f"  Slot {slot['slot']}: {slot['days']}")
    print()
    print("Normal route:")
    print("  CP01-CP10 -> SIMULATED_PASS")
    print(f"  final: {plan['normal_route']['final_status']}")
    print("Failure route:")
    print(f"  Day{plan['failure_route']['failed_day']} -> SIMULATED_FAIL at Slot {plan['failure_route']['failed_slot']}")
    print(f"  PASS days: {plan['failure_route']['pass_days']}")
    print(f"  BLOCKED days: {plan['failure_route']['blocked_days']}")
    print(f"  REVIEWABLE days: {plan['failure_route']['reviewable_days']}")
    print(f"  final: {plan['failure_route']['final_status']}")
    print()
    print("[PASS] Frozen Day 35 runbook and six embedded sources verified")
    print("[PASS] Day31 review set and Day33 resource slots reproduced")
    print("[PASS] Day34 Day23-failure partition reproduced")
    print("[PASS] Both routes cover all ten checkpoints")
    print("[PASS] CP06, CP09 and CP10 remain manual decision gates")
    print("[PASS] All states simulated; no real result or execution claim")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
