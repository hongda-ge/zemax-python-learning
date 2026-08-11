"""Day 40 step 1: validate a review-scope approval plan."""

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
    """Permit approval-record generation while all planning/execution remains locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 40 execution switch must be Boolean.")
    if execution.get("allow_scope_approval_record_generation") is not True:
        raise ValueError("Day 40 approval-record generation must be explicitly allowed.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_scope_approval_record_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 40 prohibited action enabled: " + ", ".join(prohibited))


def load_and_validate_day39(config):
    """Verify the exact formal scope proposed for manual approval."""

    source = config["source"]
    scope_path = PROJECT_ROOT / source["day39_scope_report"]
    if not scope_path.is_file() or sha256_file(scope_path) != source["day39_scope_sha256"]:
        raise ValueError("The frozen Day 39 formal-scope report changed.")
    report = json.loads(scope_path.read_text(encoding="utf-8"))
    expected_scope = [int(day) for day in source["expected_formal_review_order"]]
    expected_zosapi = [int(day) for day in source["expected_zosapi_review_days"]]
    expected_offline = [int(day) for day in source["expected_offline_review_days"]]
    checks = (
        report.get("task") == source["expected_day39_task"],
        report.get("status") == "success",
        int(report.get("changed_day", -1)) == int(source["expected_changed_day"]),
        report.get("formal_review_order") == expected_scope,
        report.get("formal_review_count") == len(expected_scope),
        report.get("uses_zosapi_review_days") == expected_zosapi,
        report.get("offline_only_review_days") == expected_offline,
        report.get("formal_impact_analysis_performed") is True,
        report.get("review_tasks_approved_for_execution") is False,
        report.get("automatic_execution_performed") is False,
        report.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 39 formal scope is incomplete or unsafe for approval.")
    row_days = [int(row["day"]) for row in report["review_rows"]]
    if row_days != expected_scope or any(row["automatic_execution"] is not False for row in report["review_rows"]):
        raise ValueError("The Day 39 review rows are inconsistent.")
    comparison = report["requester_estimate_comparison"]
    if (
        comparison.get("estimate_was_independently_verified") is not True
        or comparison.get("omitted_by_requester") != []
        or comparison.get("overreported_by_requester") != []
    ):
        raise ValueError("The Day 39 requester-scope comparison is incomplete.")
    return scope_path, report


def validate_manual_gate(config):
    """Verify the Day 35 CP06 manual scope-approval checkpoint."""

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
    if (
        checkpoint is None
        or checkpoint.get("manual_decision_required") is not True
        or checkpoint.get("automatic_execution") is not False
    ):
        raise ValueError("The Day 35 CP06 manual scope gate is missing or unsafe.")
    return runbook_path


def validate_target_unchanged(config, scope_report):
    """Confirm that scope approval still targets the unchanged Day 22 config."""

    source = config["source"]
    target_path = PROJECT_ROOT / source["target_config"]
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target changed before scope approval.")
    target = scope_report["target_under_review"]
    if Path(target["path"]).resolve() != target_path.resolve():
        raise ValueError("The Day 39 target path does not match Day 40.")
    if target["sha256"] != source["target_config_sha256"] or target.get("modified") is not False:
        raise ValueError("The Day 39 target version is inconsistent.")
    return target_path


def validate_decision_boundary(config, scope_report):
    """Ensure scope approval releases planning only."""

    decision = config["approval_decision"]
    if decision.get("decision_status") != "REVIEW_SCOPE_APPROVED_FOR_PLANNING":
        raise ValueError("Day 40 may approve review planning only.")
    if decision.get("decision_is_teaching_record") is not True:
        raise ValueError("The Day 40 decision must remain a teaching record.")
    required_text = ("decision_id", "approver_role", "decision_date", "decision_reason", "next_required_gate")
    missing = [key for key in required_text if not str(decision.get(key, "")).strip()]
    if missing:
        raise ValueError("Day 40 decision fields are empty: " + ", ".join(missing))
    approved_scope = [int(day) for day in decision.get("approved_scope", [])]
    if approved_scope != scope_report["formal_review_order"]:
        raise ValueError("The approved scope differs from the Day 39 formal scope.")
    approved = set(decision.get("approved_capabilities", []))
    if approved != {
        "plan_dependency_review_waves",
        "plan_resource_feasible_slots",
        "plan_failure_gates",
    }:
        raise ValueError("The Day 40 approved capability set is incomplete or too broad.")
    forbidden = set(decision.get("forbidden_capabilities", []))
    if forbidden != {
        "modify_day22_config",
        "connect_zosapi",
        "calculate_optical_metrics",
        "execute_review_tasks",
        "claim_engineering_change_approval",
    }:
        raise ValueError("The Day 40 forbidden capability set is incomplete.")
    validation = config["validation"]
    false_flags = (
        "scope_approval_may_imply_source_change",
        "scope_approval_may_imply_task_execution",
        "automatic_approval_allowed",
        "automatic_execution_allowed",
        "engineering_change_claim_allowed",
    )
    if any(validation.get(key) is not False for key in false_flags):
        raise ValueError("A forbidden Day 40 implication or claim was enabled.")


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
    config = load_config("configs/day40_review_scope_approval.yaml")
    validate_execution_lock(config)
    scope_path, scope_report = load_and_validate_day39(config)
    runbook_path = validate_manual_gate(config)
    target_path = validate_target_unchanged(config, scope_report)
    validate_decision_boundary(config, scope_report)

    decision = config["approval_decision"]
    print_introduction(config)
    print("========== DAY 40 REVIEW-SCOPE APPROVAL PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No approval record, review plan, source change or review task execution will occur.")
    print(f"Day 39 formal scope: {scope_path}")
    print(f"Day 39 SHA256: {config['source']['day39_scope_sha256']}")
    print(f"Day 35 runbook: {runbook_path}")
    print(f"Unchanged target: {target_path}")
    print()
    print(f"Decision: {decision['decision_id']} -> {decision['decision_status']}")
    print(f"Approved scope: {decision['approved_scope']}")
    print(f"ZOS-API review class: {scope_report['uses_zosapi_review_days']}")
    print(f"Offline review class: {scope_report['offline_only_review_days']}")
    print("Approved capabilities:")
    for item in decision["approved_capabilities"]:
        print(f"  - {item}")
    print("Still forbidden:")
    for item in decision["forbidden_capabilities"]:
        print(f"  - {item}")
    print()
    print("[PASS] Frozen Day 39 formal scope and Day 22 target verified")
    print("[PASS] Seven-node review scope and execution classes verified")
    print("[PASS] Day 35 CP06 manual scope-approval gate verified")
    print("[PASS] Approval is limited to review-plan generation")
    print("[PASS] Source modification, ZOS-API and review execution remain forbidden")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
