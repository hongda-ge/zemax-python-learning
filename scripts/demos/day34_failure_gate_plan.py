"""Day 34 step 1: plan hypothetical failure-gate propagation offline."""

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
    """Allow reports while keeping Day 34 offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 34 execution switch must be Boolean.")
    if execution.get("allow_failure_report_generation") is not True:
        raise ValueError("Day 34 failure report generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_failure_report_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 34 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate the explicit gate semantics and forbidden claims."""

    policy = config["gate_policy"]
    required_true = (
        "evaluate_after_entire_slot_finishes",
        "assume_nonfailed_tasks_in_completed_slot_pass",
        "blocked_and_reviewable_are_not_run",
        "stop_failed_branch_not_global_schedule",
        "manual_approval_required_to_resume",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise ValueError("Day 34 gate policy is incomplete.")
    expected_statuses = {
        policy["fail_node_status"],
        policy["transitive_descendant_status"],
        policy["unaffected_future_status"],
        policy["completed_nonfailed_status"],
    }
    if expected_statuses != {"FAIL", "BLOCKED", "REVIEWABLE", "PASS"}:
        raise ValueError("Day 34 status vocabulary changed.")
    validation = config["validation"]
    forbidden = (
        "real_failure_claim_allowed",
        "global_stop_claim_allowed",
        "hidden_priority_score_allowed",
        "automatic_execution_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden):
        raise ValueError("A forbidden Day 34 claim was enabled.")


def load_sources(config):
    """Load and fingerprint-check the Day 33 schedule and Day 30 DAG."""

    source = config["source"]
    schedule_path = PROJECT_ROOT / source["day33_schedule_report"]
    if not schedule_path.is_file():
        raise FileNotFoundError(f"Day 33 schedule not found: {schedule_path}")
    if sha256_file(schedule_path) != source["day33_schedule_sha256"]:
        raise ValueError("The frozen Day 33 schedule SHA256 is incorrect.")
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    checks = (
        schedule["task"] == source["day33_expected_task"],
        schedule["status"] == source["day33_expected_status"],
        schedule["scenario_count"] == int(source["day33_expected_scenario_count"]),
        schedule["task_row_count"] == int(source["day33_expected_task_row_count"]),
        schedule["automatic_execution_performed"] is False,
        schedule["manual_approval_required"] is True,
    )
    if not all(checks):
        raise ValueError("The frozen Day 33 schedule metadata is incorrect.")

    graph_path = PROJECT_ROOT / source["day30_graph_report"]
    if not graph_path.is_file():
        raise FileNotFoundError(f"Day 30 graph not found: {graph_path}")
    if sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The frozen Day 30 graph SHA256 is incorrect.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    return schedule_path, schedule, graph_path, graph


def transitive_descendants(start, graph):
    """Return all downstream nodes reachable from one failed day."""

    adjacency = {}
    for edge in graph["edges"]:
        adjacency.setdefault(int(edge["from"]), set()).add(int(edge["to"]))
    seen = set()
    pending = list(adjacency.get(start, set()))
    while pending:
        day = pending.pop()
        if day in seen:
            continue
        seen.add(day)
        pending.extend(adjacency.get(day, set()) - seen)
    return seen


def simulate_drill(drill, schedule_scenario, graph):
    """Partition one scenario after a hypothetical slot-gate failure."""

    failed_day = int(drill["failed_day"])
    all_days = {day for slot in schedule_scenario["slots"] for day in slot["days"]}
    if failed_day not in all_days:
        raise ValueError(f"Failed Day{failed_day} is outside the selected schedule.")
    failed_slot = next(
        int(slot["slot"]) for slot in schedule_scenario["slots"] if failed_day in slot["days"]
    )
    completed_through_gate = {
        day
        for slot in schedule_scenario["slots"]
        if int(slot["slot"]) <= failed_slot
        for day in slot["days"]
    }
    blocked = transitive_descendants(failed_day, graph) & all_days
    passed = completed_through_gate - {failed_day} - blocked
    reviewable = all_days - passed - {failed_day} - blocked
    partitions = [passed, {failed_day}, blocked, reviewable]
    if set().union(*partitions) != all_days or sum(len(part) for part in partitions) != len(all_days):
        raise ValueError(f"Drill {drill['id']} status partition is incomplete or overlapping.")
    checks = (
        failed_slot == int(drill["expected_failed_slot"]),
        len(passed) == int(drill["expected_pass_count"]),
        sorted(blocked) == [int(day) for day in drill["expected_blocked_days"]],
        sorted(reviewable) == [int(day) for day in drill["expected_reviewable_days"]],
    )
    if not all(checks):
        raise ValueError(f"Drill {drill['id']} propagation expectations changed.")
    states = []
    for slot in schedule_scenario["slots"]:
        for day in slot["days"]:
            if day == failed_day:
                status = "FAIL"
            elif day in passed:
                status = "PASS"
            elif day in blocked:
                status = "BLOCKED"
            else:
                status = "REVIEWABLE"
            states.append(
                {
                    "day": day,
                    "resource_slot": int(slot["slot"]),
                    "status": status,
                    "actually_executed": False,
                }
            )
    return {
        "drill_id": drill["id"],
        "schedule_scenario": drill["schedule_scenario"],
        "failed_day": failed_day,
        "failed_slot": failed_slot,
        "pass_days": sorted(passed),
        "blocked_days": sorted(blocked),
        "reviewable_days": sorted(reviewable),
        "state_counts": {
            "PASS": len(passed),
            "FAIL": 1,
            "BLOCKED": len(blocked),
            "REVIEWABLE": len(reviewable),
        },
        "states": states,
    }


def build_drill_results(config, schedule, graph):
    """Run all offline state-partition drills."""

    scenario_map = {item["scenario_id"]: item for item in schedule["scenarios"]}
    seen_ids = set()
    results = []
    for drill in config["failure_drills"]:
        if drill["id"] in seen_ids:
            raise ValueError(f"Duplicate Day 34 drill id: {drill['id']}")
        seen_ids.add(drill["id"])
        scenario_id = drill["schedule_scenario"]
        if scenario_id not in scenario_map:
            raise ValueError(f"Unknown Day 33 schedule scenario: {scenario_id}")
        results.append(simulate_drill(drill, scenario_map[scenario_id], graph))
    return results


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
    config = load_config("configs/day34_failure_gate_propagation.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    schedule_path, schedule, graph_path, graph = load_sources(config)
    results = build_drill_results(config, schedule, graph)

    print_introduction(config)
    print("========== DAY 34 FAILURE-GATE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No real task failure, ZOS-API connection or historical execution will occur.")
    print("Gate states are hypothetical teaching states, not measured experiment outcomes.")
    print(f"Day 33 schedule: {schedule_path}")
    print(f"Day 30 dependency graph: {graph_path}")
    print()
    for result in results:
        counts = result["state_counts"]
        print(
            f"{result['drill_id']}: Day{result['failed_day']} FAIL at Slot {result['failed_slot']}"
        )
        print(f"  PASS: {result['pass_days']}")
        print(f"  BLOCKED: {result['blocked_days']}")
        print(f"  REVIEWABLE: {result['reviewable_days']}")
        print(
            f"  counts: PASS={counts['PASS']}, FAIL=1, "
            f"BLOCKED={counts['BLOCKED']}, REVIEWABLE={counts['REVIEWABLE']}"
        )
    print()
    print("[PASS] Frozen Day 33 and Day 30 fingerprints verified")
    print("[PASS] Every failed node and all transitive descendants classified")
    print("[PASS] Unaffected future branches remain REVIEWABLE")
    print("[PASS] PASS/FAIL/BLOCKED/REVIEWABLE partitions are complete")
    print("[PASS] No real task was executed and no real failure was claimed")
    print("[PASS] Global-stop and hidden-priority claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
