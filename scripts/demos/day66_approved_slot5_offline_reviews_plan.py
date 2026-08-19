"""Day 66 step 1: validate the approved Slot 5 offline review plan."""

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


def load_json(path, expected_hash, expected_task):
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise ValueError(f"Frozen Day 66 evidence changed: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != expected_task or report.get("status") != "success":
        raise ValueError(f"Frozen Day 66 evidence metadata is invalid: {path}")
    return report


def validate_switches(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 66 execution switch must be Boolean.")
    allowed = {
        "enabled",
        "allow_day26_offline_evaluation",
        "allow_day27_exact_evidence_audit",
        "allow_isolated_output_write",
    }
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 66 offline execution is not fully enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 66 enabled a forbidden action.")


def verify_embedded_evidence(approval, key, expected_task):
    info = approval[key]
    path = Path(info["path"])
    report = load_json(path, info["sha256"], expected_task)
    if info.get("verified") is not True:
        raise ValueError(f"Day 65 did not mark evidence verified: {key}")
    return path, report


def verify_embedded_config(approval, key):
    info = approval[key]
    path = Path(info["path"])
    if not path.is_file() or sha256_file(path) != info["sha256"] or info.get("verified") is not True:
        raise ValueError(f"Frozen Day 66 config changed: {key}")
    return path, load_config(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))


def validate_approval(config):
    source = config["source"]
    path = (PROJECT_ROOT / source["day65_approval"]).resolve()
    approval = load_json(path, source["day65_approval_sha256"], source["expected_day65_task"])
    contract = approval["approved_execution_contract"]
    checks = (
        approval.get("decision_id") == source["expected_decision_id"],
        approval.get("decision_status") == source["expected_decision_status"],
        approval.get("permissions", {}).get("slot_05_offline_review_package_execution_released") is True,
        approval.get("permissions", {}).get("day26_offline_evaluation_released") is True,
        approval.get("permissions", {}).get("day27_exact_evidence_availability_audit_released") is True,
        approval.get("permissions", {}).get("zosapi_execution_released") is False,
        approval.get("approved_task_executed_by_day65") is False,
        int(contract["resource_slot"]) == 5,
        contract["days"] == [26, 27],
        contract["execution_class"] == "offline_only",
        int(contract["maximum_execution_count"]) == 1,
        contract["required_entrypoint"] == "scripts/demos/day66_execute_approved_slot5_offline_reviews.py",
        contract["require_sibling_isolation"] is True,
        contract["allow_interpolation"] is False,
        contract["allow_new_optical_calculation"] is False,
    )
    if not all(checks):
        raise ValueError("Day 65 approval does not release this Day 66 execution.")
    return path, approval


def build_day27_availability(approval, day25):
    measured = {round(float(row["offset_mm"]), 12): row for row in day25["combined_measured_points"]}
    if sorted(measured) != [round(float(value), 12) for value in approval["measured_offsets_mm"]]:
        raise ValueError("Day 25 measured offsets no longer match the Day 65 approval.")
    rows = []
    requirements = []
    uncertainty = float(approval["change_specific_positioning_accuracy_mm"])
    state_defs = (("negative_endpoint", -uncertainty), ("command_center", 0.0), ("positive_endpoint", uncertainty))
    for index, approved in enumerate(approval["day27_exact_state_requirements"], start=1):
        command = float(approved["command_offset_mm"])
        candidate_id = f"command_{index:03d}"
        missing = []
        for state_id, relative in state_defs:
            required = round(command + relative, 12)
            available = required in measured
            item = measured.get(required)
            rows.append({
                "candidate_id": candidate_id,
                "command_offset_mm": command,
                "state_id": state_id,
                "relative_offset_mm": relative,
                "required_offset_mm": required,
                "exact_measurement_available": available,
                "source_case_id": item["case_id"] if item else "",
                "source_day": item["source_day"] if item else "",
            })
            if not available:
                missing.append(required)
        approved_missing = sorted(round(float(value), 12) for value in approved["missing_offsets_mm"])
        if sorted(missing) != approved_missing:
            raise ValueError(f"Day 27 evidence gap changed for {candidate_id}.")
        requirements.append({
            "candidate_id": candidate_id,
            "command_offset_mm": command,
            "required_state_count": 3,
            "available_state_count": 3 - len(missing),
            "missing_state_count": len(missing),
            "missing_offsets_mm": missing,
            "envelope_evaluation_eligible": not missing,
        })
    return rows, requirements


def validate_frozen_inputs(approval):
    _, day25 = verify_embedded_evidence(approval, "day25_measured_evidence", "day25_boundary_scan_offline_analysis")
    verify_embedded_evidence(approval, "source_day64_review", "day64_cp09_slot4_boundary_batch_review_generation")
    verify_embedded_evidence(approval, "day42_schedule", "day42_change_specific_resource_schedule_generation")
    _, change = verify_embedded_evidence(approval, "change_evidence", "day48_approved_day22_candidate_offline_execution")
    verify_embedded_evidence(approval, "historical_day26_report", "day26_simulation_resolution_stopping_evaluation")
    verify_embedded_evidence(approval, "historical_day27_report", "day27_positioning_uncertainty_envelope_evaluation")
    _, day26 = verify_embedded_config(approval, "day26_config")
    _, day27 = verify_embedded_config(approval, "day27_config")
    changed = [row for row in change["teaching_error_sources"] if row["id"] == "positioning_accuracy"]
    if len(changed) != 1 or not math.isclose(float(changed[0]["symmetric_allowance_mm"]), 0.012, abs_tol=1e-12):
        raise ValueError("Day 66 change-specific positioning accuracy is invalid.")
    if day26["evaluation"]["interpolation_allowed"] is not False or day27["evaluation"]["interpolation_allowed"] is not False:
        raise ValueError("Day 26/27 interpolation lock changed.")
    return day25, day26, day27


def ensure_not_consumed(config):
    root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    marker = root / f"{config['authorization']['marker_prefix']}.json"
    if marker.exists() or list(root.glob("execution_*/slot5_offline_review_result.json")):
        raise ValueError("The Day 65 one-time approval has already been consumed.")
    return root, marker


def prepare_plan(config):
    validate_switches(config)
    approval_path, approval = validate_approval(config)
    day25, day26, day27 = validate_frozen_inputs(approval)
    availability, requirements = build_day27_availability(approval, day25)
    missing = sorted({row["required_offset_mm"] for row in availability if not row["exact_measurement_available"]})
    expected = sorted(round(float(value), 12) for value in approval["day27_missing_exact_offsets_mm"])
    if missing != expected or len(missing) != int(config["guardrails"]["expected_day27_missing_offset_count"]):
        raise ValueError("Day 27 aggregate evidence gap changed.")
    root, marker = ensure_not_consumed(config)
    return {
        "approval_path": approval_path,
        "approval_sha256": config["source"]["day65_approval_sha256"],
        "approval": approval,
        "day25": day25,
        "day26": day26,
        "day27": day27,
        "availability_rows": availability,
        "candidate_requirements": requirements,
        "missing_offsets_mm": missing,
        "output_root": root,
        "marker": marker,
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
    config = load_config("configs/day66_approved_slot5_offline_reviews.yaml")
    plan = prepare_plan(config)
    print_introduction(config)
    print("========== DAY 66 APPROVED SLOT-5 OFFLINE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No authorization will be consumed and no offline result will be created.")
    print("Approved scope: Slot 5 / Days [26, 27] / one offline review package")
    print("Day26 planned state: COMPLETED after three-policy recalculation")
    print("Day27 exact-state audit:")
    for row in plan["candidate_requirements"]:
        print(f"  {row['candidate_id']}: command={row['command_offset_mm']:+.3f} mm, available={row['available_state_count']}/3, missing={row['missing_offsets_mm']}")
    print("Day27 planned state: BLOCKED_BY_MISSING_EXACT_MEASURED_STATES")
    print(f"Authorization marker: {plan['marker']}")
    print(f"Isolated output root: {plan['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day65 one-time approval and all embedded evidence verified")
    print("[PASS] Changed 0.012 mm positioning accuracy and sixteen measured points verified")
    print("[PASS] Day26 calculation and Day27 evidence audit are separate sibling tasks")
    print("[PASS] Seven missing exact offsets reproduced without interpolation")
    print("[PASS] No prior marker or result has consumed this approval")
    print("[PASS] ZOS-API, new optical calculation and Slot 6 remain locked")
    print("PLAN ONLY finished. No output, authorization consumption or calculation was created.")


if __name__ == "__main__":
    main()
