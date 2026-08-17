"""Day 43 step 1: plan hypothetical failure gates for the Day 42 schedule."""

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
    """Allow offline simulation/reporting while keeping real actions locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 43 execution switch must be Boolean.")
    allowed_true = {"allow_failure_simulation", "allow_failure_report_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 43 failure simulation and reporting must be allowed.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 43 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate the gate vocabulary, branch isolation and forbidden claims."""

    policy = config["gate_policy"]
    required_true = (
        "evaluate_after_entire_slot_finishes",
        "assume_nonfailed_tasks_in_completed_slot_pass",
        "blocked_and_reviewable_are_not_run",
        "stop_failed_branch_not_global_schedule",
        "same_slot_is_not_dependency",
        "manual_approval_required_to_resume",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise ValueError("Day 43 gate policy is incomplete.")
    statuses = {
        policy["fail_node_status"],
        policy["transitive_descendant_status"],
        policy["unaffected_future_status"],
        policy["completed_nonfailed_status"],
    }
    if statuses != {"FAIL", "BLOCKED", "REVIEWABLE", "PASS"}:
        raise ValueError("The Day 43 status vocabulary changed.")
    if policy["simulated_state_label"] != "SIMULATED":
        raise ValueError("Day 43 states must be explicitly simulated.")
    validation = config["validation"]
    forbidden = (
        "real_failure_claim_allowed",
        "global_stop_claim_allowed",
        "hidden_priority_score_allowed",
        "automatic_execution_allowed",
        "source_modification_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden):
        raise ValueError("A forbidden Day 43 claim was enabled.")


def load_sources(config):
    """Load and fingerprint-check the Day 42 schedule and Day 30 graph."""

    source = config["source"]
    schedule_path = PROJECT_ROOT / source["day42_schedule_report"]
    if not schedule_path.is_file() or sha256_file(schedule_path) != source["day42_schedule_sha256"]:
        raise ValueError("The frozen Day 42 schedule changed.")
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    schedule_checks = (
        schedule.get("task") == source["expected_day42_task"],
        schedule.get("status") == "success",
        schedule.get("resource_schedule_generated") is True,
        schedule.get("review_tasks_approved_for_execution") is False,
        schedule.get("review_tasks_executed") is False,
        schedule.get("automatic_execution_performed") is False,
        schedule.get("existing_source_modified") is False,
    )
    if not all(schedule_checks):
        raise ValueError("The Day 42 schedule is not a safe Day 43 input.")
    graph_path = PROJECT_ROOT / source["day30_graph_report"]
    if not graph_path.is_file() or sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The frozen Day 30 dependency graph changed.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if graph.get("task") != source["expected_day30_task"] or graph.get("status") != "success":
        raise ValueError("The Day 30 dependency graph metadata is incorrect.")
    return schedule_path, schedule, graph_path, graph


def validate_target_unchanged(config, schedule):
    """Verify that the Day 22 teaching config remains unchanged."""

    source = config["source"]
    path = PROJECT_ROOT / source["target_config"]
    if not path.is_file() or sha256_file(path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target changed before Day 43 planning.")
    target = schedule["target_under_review"]
    if Path(target["path"]).resolve() != path.resolve():
        raise ValueError("The Day 42 target path does not match Day 43.")
    if target["sha256"] != source["target_config_sha256"] or target["modified"] is not False:
        raise ValueError("The Day 42 target state is inconsistent.")
    return path


def transitive_descendants(start, graph):
    """Return every graph node reachable downstream from one failed Day."""

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


def simulate_drill(drill, schedule, graph):
    """Partition all seven tasks after one explicitly hypothetical failure."""

    failed_day = int(drill["failed_day"])
    all_days = {int(day) for slot in schedule["slots"] for day in slot["days"]}
    if failed_day not in all_days:
        raise ValueError(f"Failed Day{failed_day} is outside the Day 42 schedule.")
    failed_slot = next(
        int(slot["slot"]) for slot in schedule["slots"] if failed_day in slot["days"]
    )
    completed_through_gate = {
        int(day)
        for slot in schedule["slots"]
        if int(slot["slot"]) <= failed_slot
        for day in slot["days"]
    }
    blocked = transitive_descendants(failed_day, graph) & all_days
    passed = completed_through_gate - {failed_day} - blocked
    reviewable = all_days - passed - {failed_day} - blocked
    partitions = [passed, {failed_day}, blocked, reviewable]
    if set().union(*partitions) != all_days or sum(len(part) for part in partitions) != len(all_days):
        raise ValueError(f"Drill {drill['id']} has an incomplete or overlapping partition.")
    checks = (
        failed_slot == int(drill["expected_failed_slot"]),
        sorted(passed) == [int(day) for day in drill["expected_pass_days"]],
        sorted(blocked) == [int(day) for day in drill["expected_blocked_days"]],
        sorted(reviewable) == [int(day) for day in drill["expected_reviewable_days"]],
    )
    if not all(checks):
        raise ValueError(f"Drill {drill['id']} propagation expectations changed.")
    states = []
    for slot in schedule["slots"]:
        for day in slot["days"]:
            day = int(day)
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
                    "state_origin": "SIMULATED",
                    "actually_executed": False,
                    "execution_released": False,
                }
            )
    return {
        "drill_id": drill["id"],
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
        "simulation_only": True,
    }


def build_drill_results(config, schedule, graph):
    """Build all representative Day 43 failure-gate drills."""

    seen_ids = set()
    results = []
    for drill in config["failure_drills"]:
        if drill["id"] in seen_ids:
            raise ValueError(f"Duplicate Day 43 drill id: {drill['id']}")
        seen_ids.add(drill["id"])
        results.append(simulate_drill(drill, schedule, graph))
    return results


def print_introduction(config):
    """Print today's four-part teaching introduction."""

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
    config = load_config("configs/day43_change_specific_failure_gates.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    schedule_path, schedule, graph_path, graph = load_sources(config)
    target_path = validate_target_unchanged(config, schedule)
    results = build_drill_results(config, schedule, graph)

    print_introduction(config)
    print("========== DAY 43 CHANGE-SPECIFIC FAILURE-GATE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No real failure, source change, ZOS-API connection or review task execution will occur.")
    print("Every PASS/FAIL/BLOCKED/REVIEWABLE state below is SIMULATED.")
    print(f"Day 42 schedule: {schedule_path}")
    print(f"Day 30 dependency graph: {graph_path}")
    print(f"Unchanged target: {target_path}")
    print()
    for result in results:
        counts = result["state_counts"]
        print(f"{result['drill_id']}: Day{result['failed_day']} SIMULATED_FAIL at Slot {result['failed_slot']}")
        print(f"  PASS: {result['pass_days']}")
        print(f"  BLOCKED: {result['blocked_days']}")
        print(f"  REVIEWABLE: {result['reviewable_days']}")
        print(
            f"  counts: PASS={counts['PASS']}, FAIL=1, "
            f"BLOCKED={counts['BLOCKED']}, REVIEWABLE={counts['REVIEWABLE']}"
        )
    print()
    print("[PASS] Frozen Day 42 schedule, Day 30 graph and Day 22 target verified")
    print("[PASS] Four simulated failure drills partition all seven review nodes")
    print("[PASS] Every failed node and its transitive descendants classified")
    print("[PASS] Day26/Day27 same-slot branch isolation verified")
    print("[PASS] Unaffected future work remains REVIEWABLE")
    print("[PASS] No real task, failure, source modification or global-stop claim")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
