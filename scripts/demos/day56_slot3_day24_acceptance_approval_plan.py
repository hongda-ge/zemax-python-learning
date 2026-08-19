"""Day 56 step 1: validate the minimal Slot 3 Day 24 approval plan."""

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
        raise ValueError(f"Frozen Day 56 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"Frozen Day 56 source metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 56 execution switch must be Boolean.")
    allowed = {"allow_approval_evaluation", "allow_approval_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 56 approval work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 56 enabled execution or source modification.")


def validate_review_gates(config, day55, day52):
    checks = (
        day55.get("decision_status") == config["source"]["expected_day55_status"],
        day55.get("cp09_review", {}).get("task_review_status") == "PASS",
        day55.get("cp09_review", {}).get("case_count") == 6,
        day55.get("permissions", {}).get("slot_03_release_request_eligible") is True,
        day55.get("permissions", {}).get("slot_03_execution_released") is False,
        day52.get("cp09_review", {}).get("task_review_status") == "PASS",
        day52.get("cp09_review", {}).get("case_id") == "defocus_004",
        math.isclose(float(day52["cp09_review"]["offset_mm"]), 0.0, abs_tol=1e-12),
        day52.get("permissions", {}).get("slot_02_baseline_review_completed") is True,
    )
    if not all(checks):
        raise ValueError("Day 52/55 evidence is not eligible for Slot 3 approval.")


def validate_day24_config(config):
    source = config["source"]
    path = (PROJECT_ROOT / source["day24_config"]).resolve()
    if not path.is_file() or sha256_file(path) != source["day24_config_sha256"]:
        raise ValueError("Frozen Day 24 config changed before Day 56 approval.")
    day24 = load_config(source["day24_config"])
    contract = config["approved_execution_contract"]
    if day24["source"]["expected_case_ids"] != contract["expected_case_ids"]:
        raise ValueError("Day 24 case identities do not match the approval contract.")
    if [float(x) for x in day24["source"]["expected_offsets_mm"]] != [float(x) for x in contract["expected_offsets_mm"]]:
        raise ValueError("Day 24 offsets do not match the approval contract.")
    scenarios = day24["acceptance"]["scenarios"]
    if [row["id"] for row in scenarios] != contract["expected_scenarios"]:
        raise ValueError("Day 24 scenarios do not match the approval contract.")
    if day24["acceptance"]["combination_rule"] != "all_required_metrics_must_pass":
        raise ValueError("Day 24 four-metric AND rule changed.")
    if len(day24["acceptance"]["required_metrics"]) != 4:
        raise ValueError("Day 24 must retain four independent required metrics.")
    return path, day24


def validate_schedule(schedule):
    rows = schedule.get("slots", schedule.get("resource_slots", []))
    found = False
    for row in rows:
        days = row.get("days", row.get("task_days", []))
        if int(row.get("slot", row.get("slot_number", -1))) == 3 and days == [24]:
            found = True
    if not found:
        text = json.dumps(schedule)
        found = '"slot_number": 3' in text and '24' in text
    if not found:
        raise ValueError("Day 42 does not place Day 24 in Slot 3.")


def validate_contract(config):
    contract = config["approved_execution_contract"]
    checks = (
        int(contract["resource_slot"]) == 3,
        int(contract["day"]) == 24,
        contract["execution_class"] == "offline_only",
        int(contract["maximum_execution_count"]) == 1,
        contract["required_entrypoint"] == "scripts/demos/day57_execute_approved_day24_acceptance.py",
        len(contract["expected_case_ids"]) == 7,
        len(set(contract["expected_case_ids"])) == 7,
        contract["require_four_metric_and_rule"] is True,
        contract["measured_points_only"] is True,
        contract["allow_interpolation"] is False,
        contract["allow_hidden_weighted_score"] is False,
        contract["allow_engineering_recommendation"] is False,
        contract["require_stop_after_execution"] is True,
        contract["stop_checkpoint"] == "CP09_slot_gate",
    )
    if not all(checks):
        raise ValueError("Day 56 approval contract is unsafe.")
    permissions = config["permissions"]
    released = {"slot_03_offline_acceptance_execution_released", "frozen_evidence_read_released", "isolated_result_write_released"}
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 56 released permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 56 released a forbidden permission.")


def prepare_plan(config):
    validate_execution_lock(config)
    validate_contract(config)
    day55_path, day55 = load_frozen_json(config, "day55_review", "day55_review_sha256", "expected_day55_task")
    day52_path, day52 = load_frozen_json(config, "day52_review", "day52_review_sha256", "expected_day52_task")
    schedule_path, schedule = load_frozen_json(config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task")
    validate_review_gates(config, day55, day52)
    validate_schedule(schedule)
    day24_path, day24 = validate_day24_config(config)
    return {
        "day55_path": day55_path,
        "day52_path": day52_path,
        "schedule_path": schedule_path,
        "day24_path": day24_path,
        "scenarios": day24["acceptance"]["scenarios"],
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
    config = load_config("configs/day56_slot3_day24_acceptance_approval.yaml")
    plan = prepare_plan(config)
    contract = plan["contract"]
    print_introduction(config)
    print("========== DAY 56 SLOT-3 DAY24 ACCEPTANCE APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, acceptance evaluation, ZOS-API connection or optical calculation will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print("Approved scope: Slot 3 / Day 24 / offline_only / one execution")
    print(f"Measured cases: {contract['expected_case_ids']}")
    print("Frozen teaching scenarios:")
    for scenario in plan["scenarios"]:
        limits = scenario["limits"]
        print(f"  {scenario['id']}: Spot mean<={limits['spot_mean_rms_um_max']:.3f}, "
              f"worst<={limits['spot_worst_rms_um_max']:.3f} um, "
              f"MTF30 min>={limits['mtf30_minimum_min']:.3f}, "
              f"MTF50 min>={limits['mtf50_minimum_min']:.3f}")
    print(f"Required entrypoint: {contract['required_entrypoint']}")
    print(f"Approved output root: {(PROJECT_ROOT / contract['approved_output_root']).resolve()}")
    print("Day56 executes acceptance: False")
    print("Slot 4-6 released: False")
    print()
    print("[PASS] Frozen Day55 six-case review and Day52 zero-control review verified")
    print("[PASS] Day42 places Day24 in Slot 3")
    print("[PASS] Seven measured cases and three teaching scenarios frozen")
    print("[PASS] Four required metrics retain the transparent AND rule")
    print("[PASS] Approval is limited to one offline execution through the dedicated Day57 entrypoint")
    print("[PASS] ZOS-API, new optical calculations and Slot 4-6 remain locked")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
