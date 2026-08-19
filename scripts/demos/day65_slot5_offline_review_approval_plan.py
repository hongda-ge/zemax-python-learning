"""Day 65 step 1: validate the minimal Slot 5 offline review approval."""

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
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"Frozen Day 65 evidence changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 65 source metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 65 execution switch must be Boolean.")
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 65 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 65 enabled execution or source modification.")


def validate_day64_gate(config, review):
    checks = (
        review.get("decision_status") == config["source"]["expected_day64_status"],
        review.get("cp09_review", {}).get("task_review_status") == "PASS",
        review.get("permissions", {}).get("slot_04_boundary_batch_review_completed") is True,
        review.get("permissions", {}).get("slot_05_release_request_eligible") is True,
        review.get("permissions", {}).get("slot_05_execution_released") is False,
        review.get("new_zosapi_connection_created") is False,
        review.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError("Day 64 is not eligible for Slot 5 approval.")


def validate_schedule(schedule):
    slots = [slot for slot in schedule.get("slots", []) if int(slot.get("slot", -1)) == 5]
    if len(slots) != 1:
        raise ValueError("Day 42 Slot 5 is missing or duplicated.")
    slot = slots[0]
    checks = (
        slot.get("days") == [26, 27],
        slot.get("uses_zosapi_days") == [],
        slot.get("offline_only_days") == [26, 27],
        slot.get("manual_approval_required") is True,
        slot.get("execution_released") is False,
        slot.get("automatic_execution") is False,
    )
    if not all(checks):
        raise ValueError("Day 42 does not place Day 26 and Day 27 in offline Slot 5.")


def positioning_accuracy(change_report):
    rows = change_report.get("teaching_error_sources", [])
    matches = [row for row in rows if row.get("id") == "positioning_accuracy"]
    if len(matches) != 1:
        raise ValueError("Changed positioning-accuracy evidence is missing or duplicated.")
    return float(matches[0]["symmetric_allowance_mm"])


def validate_configs_and_history(config, historical_day26, historical_day27):
    source = config["source"]
    paths = {}
    for name in ("day26_config", "day27_config"):
        path = (PROJECT_ROOT / source[name]).resolve()
        if not path.is_file() or sha256_file(path) != source[f"{name}_sha256"]:
            raise ValueError(f"Frozen config changed: {name}")
        paths[name] = path
    day26 = load_config(source["day26_config"])
    day27 = load_config(source["day27_config"])
    checks = (
        historical_day26.get("task") == source["expected_day26_task"],
        historical_day27.get("task") == source["expected_day27_task"],
        day26["evaluation"]["interpolation_allowed"] is False,
        day26["evaluation"]["extrapolation_allowed"] is False,
        day27["envelope_sampling"]["require_exact_existing_measurements"] is True,
        day27["evaluation"]["interpolation_allowed"] is False,
        day27["evaluation"]["extrapolation_allowed"] is False,
    )
    if not all(checks):
        raise ValueError("Day 26/27 frozen offline rules are invalid.")
    return paths, day26, day27


def derive_day27_evidence(config, day25, changed_accuracy):
    measured = sorted(float(row["offset_mm"]) for row in day25["combined_measured_points"])
    if len(measured) != int(config["change_specific_input"]["measured_point_count"]):
        raise ValueError("Day 25 measured-point count changed.")
    commands = [float(value) for value in config["change_specific_input"]["day27_command_offsets_mm"]]
    requirements = []
    missing = []
    for command in commands:
        required = [command - changed_accuracy, command, command + changed_accuracy]
        missing_for_command = [
            value for value in required
            if not any(math.isclose(value, sample, abs_tol=1e-12) for sample in measured)
        ]
        requirements.append({
            "command_offset_mm": command,
            "required_offsets_mm": required,
            "missing_offsets_mm": missing_for_command,
        })
        missing.extend(missing_for_command)
    unique_missing = sorted(set(round(value, 12) for value in missing))
    return measured, requirements, unique_missing


def validate_contract(config):
    contract = config["approved_execution_contract"]
    checks = (
        int(contract["resource_slot"]) == 5,
        contract["days"] == [26, 27],
        contract["execution_class"] == "offline_only",
        int(contract["maximum_execution_count"]) == 1,
        contract["required_entrypoint"] == "scripts/demos/day66_execute_approved_slot5_offline_reviews.py",
        contract["allow_day26_stopping_evaluation"] is True,
        contract["allow_day27_exact_evidence_audit"] is True,
        contract["allow_day27_envelope_evaluation_only_if_complete"] is True,
        contract["missing_evidence_status"] == "BLOCKED_BY_MISSING_EXACT_MEASURED_STATES",
        contract["require_sibling_isolation"] is True,
        contract["allow_interpolation"] is False,
        contract["allow_extrapolation"] is False,
        contract["allow_new_optical_calculation"] is False,
        contract["require_stop_after_execution"] is True,
    )
    if not all(checks):
        raise ValueError("Day 65 Slot 5 contract is unsafe.")
    released = {
        "slot_05_offline_review_package_execution_released",
        "day26_offline_evaluation_released",
        "day27_exact_evidence_availability_audit_released",
        "day27_exact_envelope_evaluation_conditionally_released",
        "sibling_isolation_required",
    }
    permissions = config["permissions"]
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 65 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 65 released a forbidden permission.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    review_path, review = load_frozen_json(config, "day64_review", "day64_review_sha256", "expected_day64_task")
    schedule_path, schedule = load_frozen_json(config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task")
    change_path, change = load_frozen_json(config, "change_evidence", "change_evidence_sha256", "expected_change_task")
    day25_path, day25 = load_frozen_json(config, "day25_report", "day25_report_sha256", "expected_day25_task")
    day26_path, day26_history = load_frozen_json(config, "historical_day26_report", "historical_day26_report_sha256", "expected_day26_task")
    day27_path, day27_history = load_frozen_json(config, "historical_day27_report", "historical_day27_report_sha256", "expected_day27_task")
    validate_day64_gate(config, review)
    validate_schedule(schedule)
    changed_accuracy = positioning_accuracy(change)
    if not math.isclose(changed_accuracy, float(config["change_specific_input"]["positioning_accuracy_mm"]), abs_tol=1e-12):
        raise ValueError("Changed positioning accuracy is not the approved 0.012 mm value.")
    config_paths, day26, day27 = validate_configs_and_history(config, day26_history, day27_history)
    measured, requirements, missing = derive_day27_evidence(config, day25, changed_accuracy)
    if not missing:
        raise ValueError("Day 65 expected a Day 27 exact-measurement evidence gap, but none was found.")
    return {
        "review_path": review_path,
        "schedule_path": schedule_path,
        "change_path": change_path,
        "day25_path": day25_path,
        "day26_history_path": day26_path,
        "day27_history_path": day27_path,
        "config_paths": config_paths,
        "day26": day26,
        "day27": day27,
        "changed_accuracy_mm": changed_accuracy,
        "measured_offsets_mm": measured,
        "day27_requirements": requirements,
        "missing_offsets_mm": missing,
        "contract": config["approved_execution_contract"],
    }


def print_introduction(config):
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
    config = load_config("configs/day65_slot5_offline_review_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["contract"]
    print_introduction(config)
    print("========== DAY 65 SLOT-5 OFFLINE REVIEW APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, offline review execution, ZOS-API connection or optical calculation will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Approved scope: Slot 5 / Days [26, 27] / offline_only / one review package")
    print(f"Change-specific positioning accuracy: +/-{plan['changed_accuracy_mm']:.3f} mm")
    print("Day26: stopping-policy evaluation released using boundary widths [0.002, 0.005] mm")
    print("Day27: exact measured-state availability audit released")
    for row in plan["day27_requirements"]:
        required = ", ".join(f"{value:+.3f}" for value in row["required_offsets_mm"])
        missing = ", ".join(f"{value:+.3f}" for value in row["missing_offsets_mm"]) or "none"
        print(f"  command {row['command_offset_mm']:+.3f} mm: required=[{required}] mm; missing=[{missing}] mm")
    print(f"Expected Day27 evidence status: {contract['missing_evidence_status']}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {(PROJECT_ROOT / contract['approved_output_root']).resolve()}")
    print("Slot 6 released: False")
    print()
    print("[PASS] Frozen Day64 CP09 review and Day42 Slot 5 verified")
    print("[PASS] Changed 0.012 mm positioning evidence and sixteen measured points verified")
    print("[PASS] Day26 and Day27 configs plus historical reports verified")
    print("[PASS] Day26 execution and Day27 exact-evidence audit are isolated sibling tasks")
    print("[PASS] Missing Day27 exact states must be reported as BLOCKED, not interpolated")
    print("[PASS] Day65 itself executes nothing; ZOS-API and Slot 6 remain locked")
    print("PLAN ONLY finished. No output, execution or source modification was created.")


if __name__ == "__main__":
    main()
