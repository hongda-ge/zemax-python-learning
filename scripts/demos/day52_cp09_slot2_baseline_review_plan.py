"""Day 52 step 1: audit the Day 51 Slot 2 baseline result at CP09."""

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
    """Allow review/report generation only and lock every execution action."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 52 execution switch must be Boolean.")
    allowed_true = {"allow_review_evaluation", "allow_review_record_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 52 review evaluation and reporting must be allowed.")
    if any(value is not False for key, value in execution.items() if key not in allowed_true):
        raise ValueError("Day 52 enabled an execution or modification capability.")


def load_frozen_json(config, path_key, hash_key, expected_task_key):
    """Load one exact JSON source with verified identity and status."""

    source = config["source"]
    path = (PROJECT_ROOT / source[path_key]).resolve()
    if not path.is_file() or sha256_file(path) != source[hash_key]:
        raise ValueError(f"The frozen Day 52 source changed: {path_key}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != source[expected_task_key] or report.get("status") != "success":
        raise ValueError(f"The Day 52 source metadata is incorrect: {path_key}")
    return path, report


def validate_approval(config, approval, result):
    """Prove Day 51 consumed the exact Day 50 one-time authorization."""

    criteria = config["review_criteria"]
    checks = (
        approval.get("decision_status")
        == "SLOT_02_APPROVED_FOR_DAY23_BASELINE_CONTROL_EXECUTION",
        approval.get("approved_scope", {}).get("resource_slot") == int(criteria["expected_slot"]),
        approval.get("approved_scope", {}).get("case_ids") == [criteria["expected_case_id"]],
        approval.get("approved_scope", {}).get("maximum_execution_count") == 1,
        approval.get("approved_task_executed") is False,
        result.get("resource_slot") == int(criteria["expected_slot"]),
        result.get("approval", {}).get("sha256") == config["source"]["day50_approval_sha256"],
        result.get("approval", {}).get("decision_id") == approval.get("decision_id"),
        result.get("approval", {}).get("consumed_once")
        is criteria["require_approval_consumed_once"],
    )
    if not all(checks):
        raise ValueError("Day 51 did not consume the exact Day 50 authorization.")


def validate_result_safety(config, result):
    """Require the single approved case and every post-execution safety flag."""

    criteria = config["review_criteria"]
    case = result.get("case", {})
    checks = (
        case.get("case_id") == criteria["expected_case_id"],
        math.isclose(float(case["offset_mm"]), float(criteria["expected_offset_mm"]), abs_tol=1e-12),
        case.get("is_control") is True,
        math.isclose(
            float(result["change_specific_evidence"]["positioning_accuracy_mm"]),
            float(criteria["expected_positioning_accuracy_mm"]),
            abs_tol=1e-12,
        ),
        result["change_specific_evidence"].get("changed_optical_input") is False,
        result.get("slot2_baseline_control_completed") is True,
        result.get("connection_closed") is criteria["require_connection_closed"],
        result.get("input_model_unchanged") is criteria["require_input_model_unchanged"],
        result.get("working_copy_unchanged") is criteria["require_working_copy_unchanged"],
        result.get("all_frozen_inputs_unchanged") is criteria["require_all_frozen_inputs_unchanged"],
        result.get("residual_cases_executed") is False,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        result.get("downstream_slots_released") is False,
        result.get("engineering_change_approved") is False,
        result.get("cp09_manual_review_required") is criteria["require_cp09_pending"],
        result.get("post_execution_gate") == "CP09_slot_gate",
    )
    if not all(checks):
        raise ValueError("The Day 51 result failed the CP09 safety audit.")


def validate_files_and_metrics(config, result):
    """Verify the model, working copy, raw analyses and reproduction metrics."""

    criteria = config["review_criteria"]
    source = config["source"]
    model_path = (PROJECT_ROOT / source["focused_model"]).resolve()
    previous_path = (PROJECT_ROOT / source["previous_day23_control"]).resolve()
    if not model_path.is_file() or sha256_file(model_path) != source["focused_model_sha256"]:
        raise ValueError("The focused model changed before Day 52 review.")
    if not previous_path.is_file() or sha256_file(previous_path) != source["previous_day23_control_sha256"]:
        raise ValueError("The previous Day 23 baseline changed before Day 52 review.")
    working_path = Path(result["working_copy"])
    spot_path = Path(result["spot_text"])
    mtf_path = Path(result["mtf_text"])
    if not all(path.is_file() for path in (working_path, spot_path, mtf_path)):
        raise ValueError("A required Day 51 working or raw analysis file is missing.")
    if sha256_file(working_path) != source["focused_model_sha256"]:
        raise ValueError("The Day 51 disk working copy does not match the frozen model.")
    if result["input_sha256_before"] != source["focused_model_sha256"]:
        raise ValueError("The Day 51 input fingerprint is incorrect.")
    if result["input_sha256_after"] != source["focused_model_sha256"]:
        raise ValueError("The Day 51 input model changed during execution.")
    if int(result["spot_metrics"]["field_count"]) != int(criteria["expected_spot_field_count"]):
        raise ValueError("The Day 51 Spot field count is incomplete.")
    if len(result["mtf_summary"]["frequencies"]) != int(criteria["expected_mtf_frequency_count"]):
        raise ValueError("The Day 51 MTF frequency count is incomplete.")
    spot_differences = (
        float(result["spot_reproduction_vs_day8"]["maximum_absolute_difference_um"]),
        float(result["spot_reproduction_vs_previous_day23"]["maximum_absolute_difference_um"]),
    )
    mtf_differences = (
        float(result["mtf_reproduction_vs_day9"]["maximum_absolute_difference"]),
        float(result["mtf_reproduction_vs_previous_day23"]["maximum_absolute_difference"]),
    )
    if max(spot_differences) > float(criteria["maximum_spot_reproduction_difference_um"]):
        raise ValueError("Day 51 did not reproduce the frozen Spot baseline.")
    if max(mtf_differences) > float(criteria["maximum_mtf_reproduction_difference"]):
        raise ValueError("Day 51 did not reproduce the frozen MTF baseline.")
    return {
        "focused_model": model_path,
        "previous_control": previous_path,
        "working_copy": working_path,
        "spot_text": spot_path,
        "spot_sha256": sha256_file(spot_path),
        "mtf_text": mtf_path,
        "mtf_sha256": sha256_file(mtf_path),
        "maximum_spot_difference_um": max(spot_differences),
        "maximum_mtf_difference": max(mtf_differences),
    }


def validate_decision(config):
    """Pass the baseline review without releasing the residual batch."""

    decision = config["decision"]
    if decision["decision_status"] != "SLOT_02_BASELINE_RESULT_REVIEW_PASSED_WAITING_FOR_RESIDUAL_BATCH_APPROVAL":
        raise ValueError("The Day 52 decision status is incorrect.")
    permissions = config["permissions"]
    true_permissions = {
        "slot_02_baseline_review_completed",
        "residual_batch_release_request_eligible",
    }
    if any(permissions.get(key) is not True for key in true_permissions):
        raise ValueError("The Day 52 review permissions are incomplete.")
    if any(value is not False for key, value in permissions.items() if key not in true_permissions):
        raise ValueError("Day 52 unexpectedly released execution or change authority.")


def build_plan(config, result_path, approval_path, audit):
    """Build the CP09 plan without writing a record or releasing the batch."""

    return {
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "result_path": str(result_path),
        "result_sha256": config["source"]["day51_result_sha256"],
        "approval_path": str(approval_path),
        "audit": audit,
        "released_capabilities": list(config["decision"]["released_capabilities"]),
        "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
        "permissions": dict(config["permissions"]),
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
    config = load_config("configs/day52_cp09_slot2_baseline_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(
        config, "day51_result", "day51_result_sha256", "expected_day51_task"
    )
    approval_path, approval = load_frozen_json(
        config, "day50_approval", "day50_approval_sha256", "expected_day50_task"
    )
    validate_approval(config, approval, result)
    validate_result_safety(config, result)
    audit = validate_files_and_metrics(config, result)
    plan = build_plan(config, result_path, approval_path, audit)

    print_introduction(config)
    print("========== DAY 52 CP09 SLOT-2 BASELINE REVIEW PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, optical analysis, rerun or residual-case release will occur.")
    print(f"Decision: {plan['decision_id']} -> {plan['decision_status']}")
    print("Slot 2 baseline task review: PASS")
    print("Approved case executed: defocus_004 only")
    print(f"Maximum Spot reproduction difference: {audit['maximum_spot_difference_um']:.9f} um")
    print(f"Maximum MTF reproduction difference: {audit['maximum_mtf_difference']:.9f}")
    print(f"Spot raw text SHA256: {audit['spot_sha256']}")
    print(f"FFT MTF raw text SHA256: {audit['mtf_sha256']}")
    print("Residual six-case execution approved: False")
    print("Still forbidden:")
    for capability in plan["forbidden_capabilities"]:
        print(f"  - {capability}")
    print()
    print("[PASS] Frozen Day51 result and Day50 authorization verified")
    print("[PASS] One-time authorization, case identity and 0.012 mm provenance verified")
    print("[PASS] Spot/MTF raw files and reproduction metrics are complete")
    print("[PASS] Input model and disk working copy fingerprints remain unchanged")
    print("[PASS] Connection closed; Quick Focus, optimization and SaveAs were not used")
    print("[PASS] Review PASS remains separate from residual-batch execution approval")
    print("PLAN ONLY finished. No output, execution or downstream release was created.")


if __name__ == "__main__":
    main()
