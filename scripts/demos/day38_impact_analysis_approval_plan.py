"""Day 38 step 1: validate a narrowly scoped approval plan."""

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
    """Permit approval-record generation while keeping all science locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 38 execution switch must be Boolean.")
    if execution.get("allow_approval_record_generation") is not True:
        raise ValueError("Approval-record generation must be explicitly allowed.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_approval_record_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 38 prohibited action enabled: " + ", ".join(prohibited))


def load_and_validate_day37(config):
    """Verify that the exact Day 37 request is awaiting review."""

    source = config["source"]
    request_path = PROJECT_ROOT / source["day37_request_report"]
    if not request_path.is_file():
        raise FileNotFoundError(f"Day 37 request not found: {request_path}")
    if sha256_file(request_path) != source["day37_request_sha256"]:
        raise ValueError("The frozen Day 37 request SHA256 is incorrect.")
    report = json.loads(request_path.read_text(encoding="utf-8"))
    expected = (
        report.get("task") == source["expected_day37_task"],
        report.get("status") == "success",
        report.get("request_id") == source["expected_request_id"],
        report.get("request_status") == source["expected_request_status"],
        report.get("request_is_hypothetical") is True,
        report.get("existing_source_modified") is False,
        report.get("change_impact_analysis_performed") is False,
        report.get("automatic_execution_performed") is False,
    )
    if not all(expected):
        raise ValueError("The Day 37 request state is not eligible for this review.")
    approval = report["approval"]
    if approval.get("approval_status") != "NOT_REVIEWED" or approval.get("execution_released") is not False:
        raise ValueError("Day 37 already contains an incompatible approval state.")
    estimate = report["requester_estimate"]
    if estimate.get("scope_is_unverified") is not True or estimate.get("may_replace_dependency_analysis") is not False:
        raise ValueError("The requester estimate must remain unverified.")
    return request_path, report


def validate_target_unchanged(config, report):
    """Confirm that approval is still bound to the reviewed Day 22 version."""

    source = config["source"]
    target_path = PROJECT_ROOT / source["target_config"]
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target config changed after the request was created.")
    change = report["change"]
    if Path(change["target_artifact"]).resolve() != target_path.resolve():
        raise ValueError("The Day 37 target path does not match Day 38.")
    if change["target_artifact_sha256"] != source["target_config_sha256"]:
        raise ValueError("The Day 37 target fingerprint does not match Day 38.")
    if change.get("change_written_to_target") is not False:
        raise ValueError("The proposed change was already written unexpectedly.")
    return target_path


def validate_manual_gate(config):
    """Verify that the Day 35 runbook requires a manual scope gate."""

    source = config["source"]
    runbook_path = PROJECT_ROOT / source["day35_runbook"]
    if not runbook_path.is_file() or sha256_file(runbook_path) != source["day35_runbook_sha256"]:
        raise ValueError("The frozen Day 35 runbook changed.")
    runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
    checkpoint = next(
        (item for item in runbook["checkpoints"]
         if item["checkpoint_id"] == source["required_manual_checkpoint"]),
        None,
    )
    if checkpoint is None or checkpoint.get("manual_decision_required") is not True:
        raise ValueError("The required Day 35 manual approval gate is missing.")
    if checkpoint.get("automatic_execution") is not False:
        raise ValueError("The Day 35 manual gate unexpectedly permits automatic execution.")
    return runbook_path


def validate_decision_boundary(config):
    """Ensure the proposed approval grants analysis permission only."""

    decision = config["approval_decision"]
    if decision.get("decision_status") != "APPROVED_FOR_IMPACT_ANALYSIS":
        raise ValueError("Day 38 may approve impact analysis only.")
    if decision.get("decision_is_teaching_record") is not True:
        raise ValueError("The Day 38 decision must remain a teaching record.")
    required_text = ("decision_id", "approver_role", "decision_date", "decision_reason", "next_required_gate")
    missing = [key for key in required_text if not str(decision.get(key, "")).strip()]
    if missing:
        raise ValueError("Day 38 decision fields are empty: " + ", ".join(missing))
    approved = set(decision.get("approved_capabilities", []))
    required_approved = {
        "read_frozen_dependency_evidence",
        "calculate_formal_review_scope",
        "generate_impact_analysis_report",
    }
    if approved != required_approved:
        raise ValueError("The approved capability set is incomplete or too broad.")
    forbidden = set(decision.get("forbidden_capabilities", []))
    required_forbidden = {
        "modify_day22_config",
        "connect_zosapi",
        "calculate_optical_metrics",
        "execute_day22_to_day28",
        "treat_requester_scope_as_final",
    }
    if forbidden != required_forbidden:
        raise ValueError("The forbidden capability set is incomplete.")
    validation = config["validation"]
    false_flags = (
        "impact_analysis_permission_may_imply_source_change",
        "impact_analysis_permission_may_imply_task_execution",
        "automatic_approval_allowed",
        "automatic_task_execution_allowed",
        "engineering_change_claim_allowed",
    )
    if any(validation.get(key) is not False for key in false_flags):
        raise ValueError("A forbidden Day 38 implication or claim was enabled.")


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
    config = load_config("configs/day38_impact_analysis_approval.yaml")
    validate_execution_lock(config)
    request_path, report = load_and_validate_day37(config)
    target_path = validate_target_unchanged(config, report)
    runbook_path = validate_manual_gate(config)
    validate_decision_boundary(config)

    decision = config["approval_decision"]
    change = report["change"]
    print_introduction(config)
    print("========== DAY 38 IMPACT-ANALYSIS APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, impact analysis, source change or historical execution will occur.")
    print(f"Day 37 request: {request_path}")
    print(f"Day 37 request SHA256: {config['source']['day37_request_sha256']}")
    print(f"Day 35 runbook: {runbook_path}")
    print()
    print(f"Request: {report['request_id']} ({report['request_status']})")
    print(f"Decision: {decision['decision_id']} -> {decision['decision_status']}")
    print(f"Target: {target_path}")
    print(f"Target SHA256: {config['source']['target_config_sha256']}")
    print(
        "Teaching value under review: "
        f"{change['current_value']:.3f} -> {change['proposed_value']:.3f} {change['unit']}"
    )
    print(f"Requester estimate: {report['requester_estimate']['review_days']} (still UNVERIFIED)")
    print("Approved capabilities:")
    for item in decision["approved_capabilities"]:
        print(f"  - {item}")
    print("Still forbidden:")
    for item in decision["forbidden_capabilities"]:
        print(f"  - {item}")
    print()
    print("[PASS] Frozen Day 37 request and Day 22 target fingerprints verified")
    print("[PASS] Day 37 request is still WAITING_FOR_APPROVAL")
    print("[PASS] Day 35 manual approval gate verified")
    print("[PASS] Approval is limited to formal impact analysis")
    print("[PASS] Requester-estimated scope remains unverified")
    print("[PASS] Day 22 modification, ZOS-API and historical execution remain forbidden")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
