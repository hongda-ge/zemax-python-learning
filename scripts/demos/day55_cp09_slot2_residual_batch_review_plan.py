"""Day 55 step 1: audit the completed Day 54 six-case batch at CP09."""

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


def load_frozen_json(config, path_key, hash_key, expected_task_key, expected_status="success"):
    path = (PROJECT_ROOT / config["source"][path_key]).resolve()
    if not path.is_file() or sha256_file(path) != config["source"][hash_key]:
        raise ValueError(f"Frozen Day 55 evidence changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != config["source"][expected_task_key] or report.get("status") != expected_status:
        raise ValueError(f"Frozen Day 55 metadata is invalid: {path_key}")
    return path, report


def validate_execution_lock(config):
    execution = config["execution"]
    allowed = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 55 review work is not enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 55 enabled execution or source modification.")


def validate_approval_and_marker(config, approval, marker, result):
    checks = (
        approval.get("decision_id") == "AP-DAY53-001",
        approval.get("permissions", {}).get("residual_batch_execution_released") is True,
        approval.get("approved_batch_executed") is False,
        marker.get("approval_sha256") == config["source"]["day53_approval_sha256"],
        marker.get("decision_id") == approval.get("decision_id"),
        marker.get("maximum_batch_execution_count") == 1,
        marker.get("rerun_released") is False,
        Path(marker.get("run_directory", "")).resolve() == Path(result["case_reports"][0]).resolve().parents[1],
        result.get("approval", {}).get("consumed_once") is True,
        Path(result.get("approval", {}).get("consumption_marker", "")).resolve() == (PROJECT_ROOT / config["source"]["authorization_marker"]).resolve(),
    )
    if not all(checks):
        raise ValueError("The Day 54 authorization-consumption evidence is inconsistent.")


def frequency_map(summary):
    return {float(row["frequency_cyc_per_mm"]): row for row in summary["frequencies"]}


def validate_one_case(config, case_path, expected_id, expected_offset, batch_row, reproduction):
    if not case_path.is_file():
        raise FileNotFoundError(f"Day 54 case report is missing: {case_path}")
    report = json.loads(case_path.read_text(encoding="utf-8"))
    tolerance = float(config["review_criteria"]["numeric_tolerance"])
    checks = (
        report.get("task") == "day54_approved_day23_residual_case",
        report.get("status") == "success",
        report.get("case", {}).get("case_id") == expected_id,
        math.isclose(float(report["case"]["offset_mm"]), float(expected_offset), abs_tol=tolerance),
        report.get("case", {}).get("is_control") is False,
        report.get("approval", {}).get("consumed_once") is True,
        report.get("connection_closed") is True,
        report.get("input_model_unchanged") is True,
        report.get("working_copy_unchanged") is True,
        report.get("quick_focus_used") is False,
        report.get("optimization_used") is False,
        report.get("save_as_used") is False,
        report.get("downstream_slots_released") is False,
    )
    if not all(checks):
        raise ValueError(f"Day 54 case safety evidence failed: {expected_id}")
    spot = report["spot_summary"]
    mtf = frequency_map(report["mtf_summary"])
    comparisons = (
        (spot["equal_field_mean_rms_um"], batch_row["spot_mean_rms_um"]),
        (spot["worst_field_rms_um"], batch_row["spot_worst_rms_um"]),
        (mtf[30.0]["overall_mean_mtf"], batch_row["mtf30_mean"]),
        (mtf[30.0]["minimum_mtf"], batch_row["mtf30_minimum"]),
        (mtf[50.0]["overall_mean_mtf"], batch_row["mtf50_mean"]),
        (mtf[50.0]["minimum_mtf"], batch_row["mtf50_minimum"]),
    )
    if any(not math.isclose(float(left), float(right), abs_tol=tolerance) for left, right in comparisons):
        raise ValueError(f"Day 54 case metrics disagree with the batch summary: {expected_id}")
    spot_limit = float(config["review_criteria"]["maximum_spot_reproduction_difference_um"])
    mtf_limit = float(config["review_criteria"]["maximum_mtf_reproduction_difference"])
    if float(reproduction["maximum_spot_summary_difference_um"]) > spot_limit or float(reproduction["maximum_mtf_summary_difference"]) > mtf_limit:
        raise ValueError(f"Day 54 historical reproduction failed: {expected_id}")
    spot_path = Path(report["spot_text"]).resolve()
    mtf_path = Path(report["mtf_text"]).resolve()
    if not spot_path.is_file() or not mtf_path.is_file():
        raise FileNotFoundError(f"Raw Spot/MTF evidence is missing: {expected_id}")
    return {
        "case_id": expected_id,
        "offset_mm": float(expected_offset),
        "case_report_path": str(case_path),
        "case_report_sha256": sha256_file(case_path),
        "spot_raw_path": str(spot_path),
        "spot_raw_sha256": sha256_file(spot_path),
        "mtf_raw_path": str(mtf_path),
        "mtf_raw_sha256": sha256_file(mtf_path),
        "connection_closed": True,
        "input_model_unchanged": True,
        "working_copy_unchanged": True,
        "historical_spot_difference_um": float(reproduction["maximum_spot_summary_difference_um"]),
        "historical_mtf_difference": float(reproduction["maximum_mtf_summary_difference"]),
    }


def validate_batch(config, result):
    criteria = config["review_criteria"]
    ids = list(criteria["expected_case_ids"])
    offsets = [float(value) for value in criteria["expected_offsets_mm"]]
    checks = (
        result.get("resource_slot") == int(criteria["expected_slot"]),
        result.get("case_count") == int(criteria["expected_case_count"]),
        result.get("case_ids") == ids,
        [row["case_id"] for row in result["rows"]] == ids,
        [row["case_id"] for row in result["historical_reproduction"]] == ids,
        result.get("all_connections_closed") is True,
        result.get("all_input_models_unchanged") is True,
        result.get("all_working_copies_unchanged") is True,
        result.get("all_frozen_inputs_unchanged") is True,
        result.get("baseline_rerun_performed") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("downstream_slots_released") is False,
        result.get("cp09_manual_review_required") is True,
    )
    if not all(checks):
        raise ValueError("The Day 54 batch-level evidence is incomplete or unsafe.")
    if len(result["case_reports"]) != len(ids):
        raise ValueError("The Day 54 case-report count is incorrect.")
    audits = []
    for index, (case_id, offset) in enumerate(zip(ids, offsets)):
        row = result["rows"][index]
        if not math.isclose(float(row["offset_mm"]), offset, abs_tol=float(criteria["numeric_tolerance"])):
            raise ValueError(f"Day 54 offset mismatch: {case_id}")
        audits.append(validate_one_case(config, Path(result["case_reports"][index]).resolve(), case_id, offset, row, result["historical_reproduction"][index]))
    return audits


def validate_decision(config):
    permissions = config["permissions"]
    released = {"slot_02_residual_batch_review_completed", "slot_03_release_request_eligible"}
    if any(permissions.get(key) is not True for key in released):
        raise ValueError("Day 55 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in released):
        raise ValueError("Day 55 released execution or an engineering claim.")


def prepare_review(config):
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(config, "day54_batch_result", "day54_batch_sha256", "expected_day54_task")
    marker_path, marker = load_frozen_json(config, "authorization_marker", "authorization_marker_sha256", "expected_marker_task", "consumed_before_zosapi_execution")
    approval_path, approval = load_frozen_json(config, "day53_approval", "day53_approval_sha256", "expected_day53_task")
    model_path = (PROJECT_ROOT / config["source"]["focused_model"]).resolve()
    if not model_path.is_file() or sha256_file(model_path) != config["source"]["focused_model_sha256"]:
        raise ValueError("The frozen focused model changed before Day 55 review.")
    validate_approval_and_marker(config, approval, marker, result)
    audits = validate_batch(config, result)
    return {"result_path": result_path, "result": result, "marker_path": marker_path, "approval_path": approval_path, "model_path": model_path, "case_audits": audits}


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
    config = load_config("configs/day55_cp09_slot2_residual_batch_review.yaml")
    review = prepare_review(config)
    print_introduction(config)
    print("========== DAY 55 CP09 SLOT-2 RESIDUAL-BATCH REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No review record, ZOS-API connection, optical calculation or Slot 3 release will occur.")
    print(f"Decision: {config['decision']['decision_id']} -> {config['decision']['decision_status']}")
    print(f"Day54 batch result: {review['result_path']}")
    print(f"Day54 batch SHA256: {config['source']['day54_batch_sha256']}")
    print("Batch task review: PASS")
    print("Case reports / raw Spot / raw MTF files: 6 / 6 / 6")
    for audit in review["case_audits"]:
        print(f"  {audit['case_id']} ({audit['offset_mm']:+.3f} mm): Spot diff={audit['historical_spot_difference_um']:.9f} um, MTF diff={audit['historical_mtf_difference']:.9f}")
    print("Slot 3 execution approved: False")
    print()
    print("[PASS] Day53 approval and pre-execution consumption marker verified")
    print("[PASS] Six case identities, offsets and batch-summary metrics verified")
    print("[PASS] Six case JSON files and twelve raw analysis files fingerprinted")
    print("[PASS] Historical optical evidence reproduced at every case")
    print("[PASS] All connections closed and all model/copy hashes unchanged")
    print("[PASS] Review PASS remains separate from Slot 3 execution approval")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
