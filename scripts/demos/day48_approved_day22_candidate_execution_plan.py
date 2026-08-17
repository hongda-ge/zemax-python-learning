"""Day 48 step 1: validate the approved one-time Day 22 candidate execution."""

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day22_focus_position_error_budget_plan import (  # noqa: E402
    validate_combination_policies,
    validate_day21_report,
    validate_error_sources,
    validate_mechanism,
)
from scripts.demos.day22_evaluate_focus_position_error_budget import (  # noqa: E402
    selected_bare_details,
    validate_offline_execution,
)


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_switches(config):
    """Allow the reviewed offline action and prohibit every broader capability."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 48 execution switch must be Boolean.")
    required_true = {
        "allow_plan_validation",
        "allow_approved_offline_execution",
        "allow_isolated_output",
    }
    if any(execution.get(key) is not True for key in required_true):
        raise ValueError("The approved Day 48 offline capabilities are incomplete.")
    if any(value is not False for key, value in execution.items() if key not in required_true):
        raise ValueError("Day 48 enabled a forbidden capability.")


def load_and_validate_approval(config):
    """Load the exact Day 47 approval and reproduce the execution contract."""

    source = config["source"]
    path = (PROJECT_ROOT / source["day47_approval_record"]).resolve()
    if not path.is_file() or sha256_file(path) != source["day47_approval_sha256"]:
        raise ValueError("The Day 47 approval changed before Day 48.")
    approval = json.loads(path.read_text(encoding="utf-8"))
    expected = config["approved_execution"]
    contract = approval["execution_contract"]
    checks = (
        approval.get("task") == source["expected_day47_task"],
        approval.get("status") == "success",
        approval.get("decision_status") == source["expected_day47_decision"],
        approval.get("permissions", {}).get("slot_01_offline_execution_released") is True,
        approval.get("permissions", {}).get("zosapi_execution_released") is False,
        approval.get("permissions", {}).get("downstream_slots_released") is False,
        approval.get("approved_task_executed") is False,
        int(contract["resource_slot"]) == int(expected["resource_slot"]),
        int(contract["day"]) == int(expected["day"]),
        contract["execution_class"] == expected["execution_class"],
        int(contract["maximum_execution_count"]) == int(expected["maximum_execution_count"]),
        contract["required_dedicated_entrypoint"] == expected["required_entrypoint"],
        Path(contract["input_config"]).resolve()
        == (PROJECT_ROOT / source["candidate_config"]).resolve(),
        contract["input_sha256"] == source["candidate_sha256"],
        Path(contract["approved_output_root"]).resolve()
        == (PROJECT_ROOT / expected["approved_output_root"]).resolve(),
        contract["require_stop_after_slot1"] is True,
        contract["require_cp09_review_after_execution"] is True,
    )
    if not all(checks):
        raise ValueError("The Day 47 execution contract does not match Day 48.")
    return path, approval


def validate_frozen_inputs(config):
    """Validate official, candidate and exact Day 21 evidence fingerprints."""

    source = config["source"]
    official_path = (PROJECT_ROOT / source["official_day22_config"]).resolve()
    candidate_path = (PROJECT_ROOT / source["candidate_config"]).resolve()
    day21_path = (PROJECT_ROOT / source["day21_report"]).resolve()
    expected = (
        (official_path, source["official_day22_sha256"], "official Day 22 config"),
        (candidate_path, source["candidate_sha256"], "Day 22 candidate"),
        (day21_path, source["day21_report_sha256"], "Day 21 evidence"),
    )
    for path, fingerprint, label in expected:
        if not path.is_file() or sha256_file(path) != fingerprint:
            raise ValueError(f"The frozen {label} changed before Day 48.")
    report = json.loads(day21_path.read_text(encoding="utf-8"))
    if report.get("task") != source["expected_day21_task"] or report.get("status") != "success":
        raise ValueError("The frozen Day 21 report metadata is incorrect.")
    return official_path, candidate_path, day21_path, report


def validate_candidate(config, candidate_path, day21_path, day21_report):
    """Validate the candidate using the original reviewed Day 22 functions."""

    candidate = load_config(candidate_path)
    validate_offline_execution(candidate)
    _, _ = validate_day21_report(candidate, day21_path)
    validate_mechanism(candidate, day21_report)
    sources = validate_error_sources(candidate)
    policies = validate_combination_policies(candidate)
    cases = selected_bare_details(candidate, day21_report)
    expected = config["candidate_expectation"]
    positioning = next(item for item in sources if item["id"] == "positioning_accuracy")
    checks = (
        float(positioning["symmetric_allowance_mm"]) == float(expected["approved_value_mm"]),
        len(sources) == int(expected["error_source_count"]),
        len(policies) == int(expected["combination_policy_count"]),
        len(cases) == int(expected["measured_case_count"]),
        candidate["source"]["selected_evidence_policy"] == expected["selected_evidence_policy"],
    )
    if not all(checks):
        raise ValueError("The candidate does not match the approved Day 48 expectation.")
    return candidate, sources, policies, cases


def ensure_execution_not_consumed(config):
    """Reject reuse when an earlier result already consumed the one-time approval."""

    approved = config["approved_execution"]
    root = (PROJECT_ROOT / approved["approved_output_root"]).resolve()
    result_name = approved["result_report_name"]
    existing = list(root.glob(f"**/{result_name}")) if root.exists() else []
    if existing:
        raise ValueError(
            "The Day 47 one-time approval has already been consumed: " + str(existing[0])
        )
    return root


def build_plan(config, approval_path, official_path, candidate_path, day21_path, sources, policies, cases, output_root):
    """Build the one-time execution plan without performing the evaluation."""

    return {
        "approval_path": str(approval_path),
        "approval_sha256": config["source"]["day47_approval_sha256"],
        "official_path": str(official_path),
        "official_sha256": config["source"]["official_day22_sha256"],
        "candidate_path": str(candidate_path),
        "candidate_sha256": config["source"]["candidate_sha256"],
        "day21_path": str(day21_path),
        "day21_sha256": config["source"]["day21_report_sha256"],
        "positioning_accuracy_mm": float(
            next(item for item in sources if item["id"] == "positioning_accuracy")["symmetric_allowance_mm"]
        ),
        "error_source_count": len(sources),
        "policy_ids": [item["id"] for item in policies],
        "case_ids": [item["case_id"] for item in cases],
        "output_root": str(output_root),
        "stop_at_checkpoint": config["approved_execution"]["stop_at_checkpoint"],
        "execution_count_planned": 1,
        "task_executed": False,
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
    config = load_config("configs/day48_approved_day22_candidate_execution.yaml")
    validate_execution_switches(config)
    approval_path, _ = load_and_validate_approval(config)
    official_path, candidate_path, day21_path, day21_report = validate_frozen_inputs(config)
    _, sources, policies, cases = validate_candidate(
        config, candidate_path, day21_path, day21_report
    )
    output_root = ensure_execution_not_consumed(config)
    plan = build_plan(
        config, approval_path, official_path, candidate_path, day21_path,
        sources, policies, cases, output_root,
    )

    print_introduction(config)
    print("========== DAY 48 APPROVED DAY22 CANDIDATE EXECUTION PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No Day22 result, output directory, source change or ZOS-API connection will occur.")
    print("Approved scope: Slot 1 / Day 22 / offline_only / one execution")
    print(f"Candidate: {plan['candidate_path']}")
    print(f"Candidate SHA256: {plan['candidate_sha256']}")
    print(f"Positioning accuracy: +/-{plan['positioning_accuracy_mm']:.3f} mm")
    print(f"Frozen Day 21 evidence: {plan['day21_path']}")
    print(f"Policies: {plan['policy_ids']}")
    print(f"Measured cases: {plan['case_ids']}")
    print(f"Isolated output root: {plan['output_root']}")
    print(f"Stop after execution: {plan['stop_at_checkpoint']}")
    print()
    print("[PASS] Frozen Day47 approval and one-time execution contract verified")
    print("[PASS] Official, candidate and Day21 evidence fingerprints verified")
    print("[PASS] Candidate 0.012 mm value and offline safety settings verified")
    print("[PASS] No prior result has consumed this approval")
    print("[PASS] Output will be redirected in memory without modifying the candidate")
    print("[PASS] ZOS-API, optical calculation and Slot 2-6 remain locked")
    print("PLAN ONLY finished. No output or calculation was created.")


if __name__ == "__main__":
    main()
