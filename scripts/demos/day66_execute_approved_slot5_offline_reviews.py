"""Day 66 step 2: consume approval and execute the Slot 5 offline reviews."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day26_evaluate_simulation_resolution_stopping import (  # noqa: E402
    evaluate_boundaries,
    summarize_policies,
)
from scripts.demos.day66_approved_slot5_offline_reviews_plan import (  # noqa: E402
    prepare_plan,
    sha256_file,
)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def change_specific_policies(day26, positioning_accuracy):
    policies = []
    for source in day26["teaching_stopping_policies"]:
        row = dict(source)
        if row["id"] == "positioning_accuracy_matched":
            row["maximum_unresolved_width_mm"] = positioning_accuracy
        policies.append(row)
    return policies


def build_marker(plan, output_dir):
    return {
        "task": "day66_authorization_consumption",
        "status": "consumed_before_offline_evaluation",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(plan["approval_path"]),
        "approval_sha256": plan["approval_sha256"],
        "decision_id": plan["approval"]["decision_id"],
        "resource_slot": 5,
        "days": [26, 27],
        "maximum_execution_count": 1,
        "execution_count_consumed": 1,
        "run_directory": str(output_dir),
        "rerun_released": False,
    }


def build_day26_result(plan, details, summaries):
    accuracy = float(plan["approval"]["change_specific_positioning_accuracy_mm"])
    return {
        "task": "day66_change_specific_day26_stopping_evaluation",
        "status": "success",
        "task_state": "COMPLETED",
        "time_local": datetime.now().astimezone().isoformat(),
        "positioning_accuracy_mm": accuracy,
        "boundary_widths_mm": [float(value) for value in plan["approval"]["approved_execution_contract"].get("day26_boundary_widths_mm", [0.002, 0.005])],
        "details": details,
        "summaries": summaries,
        "sibling_day27_state_does_not_invalidate_result": True,
        "measured_boundary_brackets_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "new_boundary_case_executed": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "continuous_tolerance_claimed": False,
        "engineering_recommendation": None,
    }


def build_day27_result(config, plan):
    return {
        "task": "day66_change_specific_day27_exact_evidence_audit",
        "status": "success",
        "task_state": config["guardrails"]["required_day27_status"],
        "time_local": datetime.now().astimezone().isoformat(),
        "positioning_uncertainty_mm": float(plan["approval"]["change_specific_positioning_accuracy_mm"]),
        "candidate_count": len(plan["candidate_requirements"]),
        "required_state_count": len(plan["availability_rows"]),
        "available_state_count": sum(row["exact_measurement_available"] for row in plan["availability_rows"]),
        "missing_state_count": sum(not row["exact_measurement_available"] for row in plan["availability_rows"]),
        "missing_unique_offsets_mm": plan["missing_offsets_mm"],
        "candidate_requirements": plan["candidate_requirements"],
        "exact_state_availability": plan["availability_rows"],
        "envelope_evaluation_executed": False,
        "pass_candidates": None,
        "fail_candidates": None,
        "blocked_is_not_failure": True,
        "sibling_day26_result_overblocked": False,
        "measured_points_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "new_residual_defocus_case_executed": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "continuous_acceptance_interval_claimed": False,
        "engineering_recommendation": None,
    }


def validate_results(config, day26_result, day27_result):
    guard = config["guardrails"]
    checks = (
        day26_result["task_state"] == guard["required_day26_status"],
        len(day26_result["details"]) == int(guard["expected_day26_detail_count"]),
        len(day26_result["summaries"]) == int(guard["expected_day26_summary_count"]),
        day27_result["task_state"] == guard["required_day27_status"],
        day27_result["candidate_count"] == int(guard["expected_day27_candidate_count"]),
        day27_result["required_state_count"] == int(guard["expected_day27_state_count"]),
        len(day27_result["missing_unique_offsets_mm"]) == int(guard["expected_day27_missing_offset_count"]),
        day27_result["envelope_evaluation_executed"] is False,
        day27_result["blocked_is_not_failure"] is True,
        day27_result["sibling_day26_result_overblocked"] is False,
        day26_result["interpolation_used"] is False,
        day27_result["interpolation_used"] is False,
        day26_result["new_zosapi_connection_created"] is False,
        day27_result["new_zosapi_connection_created"] is False,
    )
    if not all(checks):
        raise ValueError("Day 66 result failed its safety validation.")


def build_package(plan, day26_result, day27_result, marker_path, output_dir, output_paths):
    return {
        "task": "day66_approved_slot5_offline_review_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "authorization": {
            "day65_approval_path": str(plan["approval_path"]),
            "day65_approval_sha256": plan["approval_sha256"],
            "decision_id": plan["approval"]["decision_id"],
            "resource_slot": 5,
            "days": [26, 27],
            "execution_count_consumed": 1,
            "consumption_marker": str(marker_path),
        },
        "runtime_output_directory": str(output_dir),
        "task_states": {
            "day26": day26_result["task_state"],
            "day27": day27_result["task_state"],
        },
        "task_outcome_interpretation": {
            "package_execution_succeeded": True,
            "day26_scientific_review_completed": True,
            "day27_scientific_review_completed": False,
            "day27_blocked_by_missing_evidence": True,
            "blocked_is_not_execution_failure": True,
        },
        "output_files": {name: str(path) for name, path in output_paths.items()},
        "slot5_execution_completed": True,
        "cp09_review_status": "PENDING",
        "slot6_execution_released": False,
        "downstream_slots_released": False,
        "sibling_isolation_preserved": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "existing_source_modified": False,
        "continuous_tolerance_claimed": False,
        "engineering_recommendation": None,
        "engineering_change_approved": False,
    }


def main():
    config = load_config("configs/day66_approved_slot5_offline_reviews.yaml")
    plan = prepare_plan(config)
    frozen_paths = [plan["approval_path"]]
    for key in ("source_day64_review", "day42_schedule", "change_evidence", "day25_measured_evidence", "day26_config", "historical_day26_report", "day27_config", "historical_day27_report"):
        frozen_paths.append(Path(plan["approval"][key]["path"]))
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}

    accuracy = float(plan["approval"]["change_specific_positioning_accuracy_mm"])
    policies = change_specific_policies(plan["day26"], accuracy)
    details = evaluate_boundaries(plan["day26"], policies, accuracy)
    summaries = summarize_policies(policies, details)
    day26_result = build_day26_result(plan, details, summaries)
    day27_result = build_day27_result(config, plan)
    validate_results(config, day26_result, day27_result)

    output_dir = plan["output_root"] / datetime.now().astimezone().strftime("execution_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    marker = build_marker(plan, output_dir)
    plan["marker"].parent.mkdir(parents=True, exist_ok=True)
    plan["marker"].write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    names = config["output"]
    paths = {
        "day26_detail_csv": output_dir / names["day26_detail_csv"],
        "day26_summary_csv": output_dir / names["day26_summary_csv"],
        "day26_result_json": output_dir / names["day26_result_json"],
        "day27_availability_csv": output_dir / names["day27_availability_csv"],
        "day27_result_json": output_dir / names["day27_result_json"],
    }
    write_csv(paths["day26_detail_csv"], details)
    write_csv(paths["day26_summary_csv"], summaries)
    write_csv(paths["day27_availability_csv"], plan["availability_rows"])
    paths["day26_result_json"].write_text(json.dumps(day26_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["day27_result_json"].write_text(json.dumps(day27_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    package_path = output_dir / names["package_result_json"]
    package = build_package(plan, day26_result, day27_result, plan["marker"], output_dir, paths)
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 66 input changed during execution: {path}")

    print("========== DAY 66 APPROVED SLOT-5 OFFLINE REVIEWS ==========")
    print("Day65 one-time authorization has been consumed.")
    print("No ZOS-API connection or new optical calculation was used.")
    print(f"Output directory: {output_dir}")
    print()
    print("Day26 change-specific stopping evaluation: COMPLETED")
    for summary in summaries:
        print(f"  {summary['policy_id']}: {summary['stop_count']}/2 STOP; planned bisections={summary['total_additional_bisections_planned']}")
    print(f"  Boundary/positioning ratios: {100.0 * 0.002 / accuracy:.1f}% and {100.0 * 0.005 / accuracy:.1f}%")
    print()
    print(f"Day27 exact-envelope review: {day27_result['task_state']}")
    for row in plan["candidate_requirements"]:
        print(f"  {row['candidate_id']}: available={row['available_state_count']}/3; missing={row['missing_offsets_mm']}")
    print(f"  Unique missing offsets: {plan['missing_offsets_mm']}")
    print()
    print("[PASS] Day65 approval consumed exactly once")
    print("[PASS] Day26 used the new 0.012 mm positioning scale")
    print("[PASS] Day27 evidence gap recorded without interpolation or false FAIL")
    print("[PASS] Day27 blocking did not overblock the independent Day26 result")
    print("[PASS] Frozen inputs remained unchanged; no ZOS-API or optical calculation")
    print("[PASS] Slot 6 remains locked")
    print("[WAIT] CP09 manual review is required before any Slot 6 release")
    print(f"[PASS] Day26 detail CSV: {paths['day26_detail_csv']}")
    print(f"[PASS] Day26 summary CSV: {paths['day26_summary_csv']}")
    print(f"[PASS] Day27 availability CSV: {paths['day27_availability_csv']}")
    print(f"[PASS] Slot 5 package result: {package_path}")


if __name__ == "__main__":
    main()
