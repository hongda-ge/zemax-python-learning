"""Day 33 step 1: plan resource-feasible review slots without execution."""

import hashlib
import json
import math
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
    """Allow reports while keeping Day 33 offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 33 execution switch must be Boolean.")
    if execution.get("allow_schedule_report_generation") is not True:
        raise ValueError("Day 33 schedule report generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_schedule_report_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 33 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate explicit capacity and interpretation boundaries."""

    resources = config["teaching_resources"]
    if int(resources["zosapi_capacity_per_slot"]) != 1:
        raise ValueError("Day 33 teaching ZOS-API capacity must be one.")
    if int(resources["offline_capacity_per_slot"]) != 2:
        raise ValueError("Day 33 teaching offline capacity must be two.")
    required_true = (
        "slot_is_order_group_not_duration",
        "capacity_is_teaching_assumption_not_benchmark",
        "manual_approval_required_before_execution",
    )
    if any(resources.get(key) is not True for key in required_true):
        raise ValueError("Day 33 resource interpretation boundary is incomplete.")
    policy = config["scheduling_policy"]
    if any(
        policy.get(key) is not True
        for key in (
            "preserve_scenario_independence",
            "preserve_day32_wave_order",
            "split_wave_when_resource_capacity_exceeded",
            "allow_zosapi_and_offline_in_same_slot",
            "deterministic_day_order_within_wave",
        )
    ):
        raise ValueError("Day 33 scheduling policy is incomplete.")
    forbidden = (
        config["validation"]["duration_claim_allowed"],
        config["validation"]["resource_benchmark_claim_allowed"],
        config["validation"]["hidden_priority_score_allowed"],
        config["validation"]["automatic_execution_allowed"],
        policy["automatic_execution_allowed"],
    )
    if any(value is not False for value in forbidden):
        raise ValueError("A forbidden Day 33 scheduling claim was enabled.")


def load_day32(config):
    """Load and verify the frozen Day 32 wave report."""

    source = config["source"]
    path = PROJECT_ROOT / source["day32_wave_report"]
    if not path.is_file():
        raise FileNotFoundError(f"Day 32 wave report not found: {path}")
    if sha256_file(path) != source["day32_wave_sha256"]:
        raise ValueError("The frozen Day 32 wave report SHA256 is incorrect.")
    report = json.loads(path.read_text(encoding="utf-8"))
    checks = (
        report["task"] == source["expected_task"],
        report["status"] == source["expected_status"],
        report["scenario_count"] == int(source["expected_scenario_count"]),
        report["task_row_count"] == int(source["expected_task_row_count"]),
        report["automatic_execution_performed"] is False,
        report["resource_concurrency_approved"] is False,
    )
    if not all(checks):
        raise ValueError("The frozen Day 32 wave metadata is incorrect.")
    return path, report


def chunks(values, capacity):
    """Split a sorted task list into deterministic capacity-sized pieces."""

    return [values[index:index + capacity] for index in range(0, len(values), capacity)]


def schedule_scenario(scenario, resources):
    """Split each dependency wave into resource-feasible ordered slots."""

    zosapi_capacity = int(resources["zosapi_capacity_per_slot"])
    offline_capacity = int(resources["offline_capacity_per_slot"])
    slots = []
    slot_number = 0
    for wave in scenario["waves"]:
        zosapi_chunks = chunks(sorted(wave["uses_zosapi_days"]), zosapi_capacity)
        offline_chunks = chunks(sorted(wave["offline_only_days"]), offline_capacity)
        subslot_count = max(len(zosapi_chunks), len(offline_chunks), 1)
        for subslot in range(subslot_count):
            slot_number += 1
            zosapi_days = zosapi_chunks[subslot] if subslot < len(zosapi_chunks) else []
            offline_days = offline_chunks[subslot] if subslot < len(offline_chunks) else []
            slots.append(
                {
                    "slot": slot_number,
                    "source_wave": int(wave["wave"]),
                    "subslot_within_wave": subslot + 1,
                    "days": sorted(zosapi_days + offline_days),
                    "uses_zosapi_days": zosapi_days,
                    "offline_only_days": offline_days,
                    "manual_approval_required": True,
                    "automatic_execution": False,
                }
            )
    return slots


def build_schedule_results(config, report):
    """Create and audit all three resource-feasible teaching schedules."""

    resources = config["teaching_resources"]
    expected = config["expected_scenarios"]
    results = []
    for scenario in report["scenarios"]:
        scenario_id = scenario["scenario_id"]
        if scenario_id not in expected:
            raise ValueError(f"Unexpected Day 32 scenario: {scenario_id}")
        slots = schedule_scenario(scenario, resources)
        flat_days = [day for slot in slots for day in slot["days"]]
        source_days = [day for wave in scenario["waves"] for day in wave["days"]]
        if sorted(flat_days) != sorted(source_days) or len(flat_days) != len(set(flat_days)):
            raise ValueError(f"Scenario {scenario_id} lost or duplicated a task.")
        if any(
            len(slot["uses_zosapi_days"]) > int(resources["zosapi_capacity_per_slot"])
            or len(slot["offline_only_days"]) > int(resources["offline_capacity_per_slot"])
            for slot in slots
        ):
            raise ValueError(f"Scenario {scenario_id} exceeds a resource capacity.")
        if any(
            slots[index]["source_wave"] > slots[index + 1]["source_wave"]
            for index in range(len(slots) - 1)
        ):
            raise ValueError(f"Scenario {scenario_id} reverses Day 32 wave order.")
        rule = expected[scenario_id]
        maximum_width = max(len(slot["days"]) for slot in slots)
        extra_slots = len(slots) - int(scenario["wave_count"])
        checks = (
            len(flat_days) == int(rule["task_count"]),
            int(scenario["wave_count"]) == int(rule["theoretical_wave_count"]),
            len(slots) == int(rule["resource_slot_count"]),
            extra_slots == int(rule["extra_slots_due_to_zosapi_capacity"]),
            maximum_width == int(rule["maximum_slot_width"]),
        )
        if not all(checks):
            raise ValueError(f"Scenario {scenario_id} schedule expectations changed.")
        results.append(
            {
                "scenario_id": scenario_id,
                "changed_day": int(scenario["changed_day"]),
                "task_count": len(flat_days),
                "theoretical_wave_count": int(scenario["wave_count"]),
                "resource_slot_count": len(slots),
                "extra_slots_due_to_zosapi_capacity": extra_slots,
                "maximum_slot_width": maximum_width,
                "slots": slots,
            }
        )
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
    config = load_config("configs/day33_resource_feasible_review_schedule.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    source_path, report = load_day32(config)
    results = build_schedule_results(config, report)

    print_introduction(config)
    print("========== DAY 33 RESOURCE-FEASIBLE SCHEDULE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, optical calculation or task execution will occur.")
    print("Slots express order groups, not task durations or a resource benchmark.")
    print(f"Day 32 wave report: {source_path}")
    print("Teaching capacities: ZOS-API=1 task/slot; offline=2 tasks/slot")
    print()
    for result in results:
        print(
            f"{result['scenario_id']}: waves={result['theoretical_wave_count']} -> "
            f"slots={result['resource_slot_count']}, extra={result['extra_slots_due_to_zosapi_capacity']}"
        )
        for slot in result["slots"]:
            print(
                f"  Slot {slot['slot']:02d} (Wave {slot['source_wave']:02d}.{slot['subslot_within_wave']}): "
                f"days={slot['days']}; ZOS-API={slot['uses_zosapi_days']}; "
                f"offline={slot['offline_only_days']}"
            )
    print()
    print("[PASS] Frozen Day 32 fingerprint verified")
    print("[PASS] Every review task appears in exactly one resource slot")
    print("[PASS] Day 32 dependency-wave order preserved")
    print("[PASS] At most one ZOS-API and two offline tasks per slot")
    print("[PASS] Manual approval retained; no task was executed")
    print("[PASS] Duration, benchmark and hidden-priority claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
