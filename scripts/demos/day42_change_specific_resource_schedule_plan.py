"""Day 42 step 1: plan resource-feasible slots for the approved Day 22 review scope."""

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
    """Allow offline scheduling/reporting while keeping all real actions locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 42 execution switch must be Boolean.")
    allowed_true = {"allow_schedule_calculation", "allow_schedule_report_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 42 schedule calculation and reporting must be allowed.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 42 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate declared capacities and interpretation boundaries."""

    resources = config["teaching_resources"]
    if int(resources["zosapi_capacity_per_slot"]) != 1:
        raise ValueError("Day 42 teaching ZOS-API capacity must be one.")
    if int(resources["offline_capacity_per_slot"]) != 2:
        raise ValueError("Day 42 teaching offline capacity must be two.")
    required_resource_flags = (
        "slot_is_order_group_not_duration",
        "capacity_is_teaching_assumption_not_benchmark",
        "manual_approval_required_before_execution",
    )
    if any(resources.get(key) is not True for key in required_resource_flags):
        raise ValueError("Day 42 resource interpretation boundary is incomplete.")
    policy = config["scheduling_policy"]
    required_policy_flags = (
        "preserve_day41_wave_order",
        "split_wave_when_resource_capacity_exceeded",
        "allow_zosapi_and_offline_in_same_slot",
        "deterministic_day_order_within_wave",
        "preserve_execution_class_labels",
    )
    if any(policy.get(key) is not True for key in required_policy_flags):
        raise ValueError("Day 42 scheduling policy is incomplete.")
    forbidden = (
        policy["automatic_execution_allowed"],
        config["validation"]["duration_claim_allowed"],
        config["validation"]["resource_benchmark_claim_allowed"],
        config["validation"]["hidden_priority_score_allowed"],
        config["validation"]["automatic_execution_allowed"],
        config["validation"]["source_modification_allowed"],
    )
    if any(value is not False for value in forbidden):
        raise ValueError("A forbidden Day 42 scheduling claim was enabled.")


def load_day41(config):
    """Load and verify the exact Day 41 dependency-wave evidence."""

    source = config["source"]
    path = PROJECT_ROOT / source["day41_wave_report"]
    if not path.is_file() or sha256_file(path) != source["day41_wave_report_sha256"]:
        raise ValueError("The frozen Day 41 wave report changed.")
    report = json.loads(path.read_text(encoding="utf-8"))
    checks = (
        report.get("task") == source["expected_day41_task"],
        report.get("status") == "success",
        report.get("dependency_wave_plan_generated") is True,
        report.get("resource_schedule_generated") is False,
        report.get("review_tasks_approved_for_execution") is False,
        report.get("review_tasks_executed") is False,
        report.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 41 wave report is not a safe Day 42 input.")
    return path, report


def validate_target_unchanged(config, day41_report):
    """Verify that the Day 22 teaching config remains unchanged."""

    source = config["source"]
    path = PROJECT_ROOT / source["target_config"]
    if not path.is_file() or sha256_file(path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target changed before Day 42 planning.")
    target = day41_report["target_under_review"]
    if Path(target["path"]).resolve() != path.resolve():
        raise ValueError("The Day 41 target path does not match Day 42.")
    if target["sha256"] != source["target_config_sha256"] or target["modified"] is not False:
        raise ValueError("The Day 41 target state is inconsistent.")
    return path


def chunks(values, capacity):
    """Split sorted values into deterministic capacity-sized groups."""

    return [values[index:index + capacity] for index in range(0, len(values), capacity)]


def build_schedule(config, day41_report):
    """Convert Day 41 waves into resource-feasible ordered slots."""

    resources = config["teaching_resources"]
    zosapi_capacity = int(resources["zosapi_capacity_per_slot"])
    offline_capacity = int(resources["offline_capacity_per_slot"])
    slots = []
    slot_number = 0
    for wave in day41_report["waves"]:
        zosapi_groups = chunks(sorted(wave["uses_zosapi_days"]), zosapi_capacity)
        offline_groups = chunks(sorted(wave["offline_only_days"]), offline_capacity)
        subslot_count = max(len(zosapi_groups), len(offline_groups), 1)
        for subslot in range(subslot_count):
            slot_number += 1
            zosapi_days = zosapi_groups[subslot] if subslot < len(zosapi_groups) else []
            offline_days = offline_groups[subslot] if subslot < len(offline_groups) else []
            slots.append(
                {
                    "slot": slot_number,
                    "source_wave": int(wave["wave"]),
                    "subslot_within_wave": subslot + 1,
                    "days": sorted(zosapi_days + offline_days),
                    "uses_zosapi_days": zosapi_days,
                    "offline_only_days": offline_days,
                    "manual_approval_required": True,
                    "execution_released": False,
                    "automatic_execution": False,
                }
            )
    source_days = [int(day) for wave in day41_report["waves"] for day in wave["days"]]
    scheduled_days = [int(day) for slot in slots for day in slot["days"]]
    if sorted(source_days) != sorted(scheduled_days) or len(scheduled_days) != len(set(scheduled_days)):
        raise ValueError("A Day 42 review task was lost or duplicated.")
    if any(
        len(slot["uses_zosapi_days"]) > zosapi_capacity
        or len(slot["offline_only_days"]) > offline_capacity
        for slot in slots
    ):
        raise ValueError("A Day 42 slot exceeds a teaching resource capacity.")
    if any(
        slots[index]["source_wave"] > slots[index + 1]["source_wave"]
        for index in range(len(slots) - 1)
    ):
        raise ValueError("Day 42 reversed the Day 41 wave order.")
    expected = config["expected_result"]
    expected_slots = expected["slots"]
    checks = (
        int(day41_report["changed_day"]) == int(expected["changed_day"]),
        len(scheduled_days) == int(expected["task_count"]),
        int(day41_report["wave_count"]) == int(expected["theoretical_wave_count"]),
        len(slots) == int(expected["resource_slot_count"]),
        len(slots) - int(day41_report["wave_count"]) == int(expected["extra_slots_due_to_capacity"]),
        max(len(slot["days"]) for slot in slots) == int(expected["maximum_slot_width"]),
        [slot["days"] for slot in slots] == [item["days"] for item in expected_slots],
        [slot["source_wave"] for slot in slots] == [int(item["source_wave"]) for item in expected_slots],
    )
    if not all(checks):
        raise ValueError("The calculated Day 42 schedule changed from the reviewed expectation.")
    return {
        "changed_day": int(day41_report["changed_day"]),
        "task_count": len(scheduled_days),
        "theoretical_wave_count": int(day41_report["wave_count"]),
        "resource_slot_count": len(slots),
        "extra_slots_due_to_capacity": len(slots) - int(day41_report["wave_count"]),
        "maximum_slot_width": max(len(slot["days"]) for slot in slots),
        "slots": slots,
    }


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
    config = load_config("configs/day42_change_specific_resource_schedule.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    day41_path, day41_report = load_day41(config)
    target_path = validate_target_unchanged(config, day41_report)
    result = build_schedule(config, day41_report)

    print_introduction(config)
    print("========== DAY 42 CHANGE-SPECIFIC RESOURCE-SCHEDULE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No schedule report, source change, ZOS-API connection or review task execution will occur.")
    print("Slots are order groups, not task durations or execution approvals.")
    print(f"Day 41 wave report: {day41_path}")
    print(f"Unchanged target: {target_path}")
    print("Teaching capacities: ZOS-API=1 task/slot; offline=2 tasks/slot")
    print()
    print(
        f"Changed Day {result['changed_day']}: waves={result['theoretical_wave_count']} -> "
        f"slots={result['resource_slot_count']}, extra={result['extra_slots_due_to_capacity']}, "
        f"max width={result['maximum_slot_width']}"
    )
    for slot in result["slots"]:
        print(
            f"  Slot {slot['slot']:02d} (Wave {slot['source_wave']:02d}.{slot['subslot_within_wave']}): "
            f"days={slot['days']}; ZOS-API={slot['uses_zosapi_days']}; "
            f"offline={slot['offline_only_days']}; execution released={slot['execution_released']}"
        )
    print()
    print("[PASS] Frozen Day 41 wave-report fingerprint verified")
    print("[PASS] Every review task appears in exactly one resource slot")
    print("[PASS] Day 41 dependency-wave order preserved")
    print("[PASS] At most one ZOS-API and two offline tasks per slot")
    print("[PASS] Manual approval retained; no task was released or executed")
    print("[PASS] Duration, benchmark and hidden-priority claims forbidden")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
