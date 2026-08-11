"""Day 37 step 1: validate a maintenance change-request plan."""

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
    """Allow request-document generation while keeping science locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 37 execution switch must be Boolean.")
    if execution.get("allow_change_request_generation") is not True:
        raise ValueError("Day 37 request-document generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_change_request_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 37 prohibited action enabled: " + ", ".join(prohibited))


def load_runbook_and_registry(config):
    """Verify the Day 35 runbook and its embedded Day 29 registry."""

    source = config["source"]
    runbook_path = PROJECT_ROOT / source["day35_runbook"]
    if not runbook_path.is_file():
        raise FileNotFoundError(f"Day 35 runbook not found: {runbook_path}")
    if sha256_file(runbook_path) != source["day35_runbook_sha256"]:
        raise ValueError("The frozen Day 35 runbook SHA256 is incorrect.")
    runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
    if runbook["task"] != source["expected_runbook_task"] or runbook["status"] != "success":
        raise ValueError("The frozen Day 35 runbook metadata is incorrect.")
    checkpoint_ids = {item["checkpoint_id"] for item in runbook["checkpoints"]}
    required_checkpoints = {
        source["expected_change_intake_checkpoint"],
        source["expected_scope_approval_checkpoint"],
    }
    if not required_checkpoints.issubset(checkpoint_ids):
        raise ValueError("Day 35 no longer contains the required intake and approval gates.")

    registry_source = next(
        (item for item in runbook["sources"] if item["role"] == "experiment_registry"),
        None,
    )
    if registry_source is None:
        raise ValueError("Day 35 does not embed the Day 29 experiment registry.")
    registry_path = Path(registry_source["path"])
    if not registry_path.is_file() or sha256_file(registry_path) != registry_source["sha256"]:
        raise ValueError("The embedded Day 29 experiment registry changed.")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry["status"] != "success" or registry["registered_day_count"] != 26:
        raise ValueError("The Day 29 registry metadata is incorrect.")
    return runbook_path, registry_path, registry


def find_registry_entry(config, registry):
    """Map the proposed change to one registered teaching day."""

    request = config["change_request"]
    changed_day = int(request["changed_day"])
    entry = next((item for item in registry["entries"] if int(item["day"]) == changed_day), None)
    if entry is None:
        raise ValueError(f"Changed Day {changed_day} is not registered.")
    if entry["primary_config"] != request["target_artifact"]:
        raise ValueError("The change target does not match the Day 29 primary config.")
    required_assets = [entry["primary_config"], entry["learning_note"], *entry["scripts"]]
    missing = [path for path in required_assets if not (PROJECT_ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError("Registered Day assets are missing: " + ", ".join(missing))
    if entry["artifact_coverage_status"] != "complete":
        raise ValueError("The target Day registry coverage is incomplete.")
    return entry


def validate_target_fingerprint_and_value(config):
    """Verify the request points at the reviewed target version and value."""

    source = config["source"]
    request = config["change_request"]
    target_path = PROJECT_ROOT / source["target_config"]
    if request["target_artifact"] != source["target_config"]:
        raise ValueError("The request target and frozen source target differ.")
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target config fingerprint changed.")
    target_config = load_config(source["target_config"])
    positioning = next(
        (item for item in target_config["teaching_error_sources"]
         if item["id"] == "positioning_accuracy"),
        None,
    )
    if positioning is None:
        raise ValueError("Day 22 positioning_accuracy field was not found.")
    current = float(request["current_value"])
    actual = float(positioning["symmetric_allowance_mm"])
    proposed = float(request["proposed_value"])
    if not math.isclose(current, actual, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("The requested current value does not match Day 22.")
    if math.isclose(current, proposed, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("The proposed value must differ from the current value.")
    if current <= 0 or proposed <= 0:
        raise ValueError("Teaching error allowances must remain positive.")
    return target_path, actual


def validate_request_fields(config, registry):
    """Require a complete draft without treating estimates as conclusions."""

    request = config["change_request"]
    required_text = (
        "request_id",
        "request_status",
        "created_date",
        "requester_role",
        "change_type",
        "target_artifact",
        "target_field",
        "unit",
        "change_reason",
        "expected_benefit",
        "rollback_description",
    )
    missing = [key for key in required_text if not str(request.get(key, "")).strip()]
    if missing:
        raise ValueError("Day 37 required fields are empty: " + ", ".join(missing))
    if request["request_status"] != "DRAFT":
        raise ValueError("The first Day 37 step must remain DRAFT.")
    if request.get("change_is_hypothetical") is not True:
        raise ValueError("The Day 37 teaching change must remain hypothetical.")
    risks = request.get("risk_hypotheses")
    if not isinstance(risks, list) or len(risks) < 2 or any(not str(item).strip() for item in risks):
        raise ValueError("At least two non-empty risk hypotheses are required.")
    estimated_days = [int(day) for day in request.get("requester_estimated_impact_days", [])]
    registered_days = {int(item["day"]) for item in registry["entries"]}
    if len(estimated_days) != len(set(estimated_days)) or int(request["changed_day"]) not in estimated_days:
        raise ValueError("The requester estimate must be unique and include the changed Day.")
    if any(day not in registered_days for day in estimated_days):
        raise ValueError("The requester estimate contains an unregistered Day.")
    if request.get("requester_scope_is_unverified") is not True:
        raise ValueError("Requester scope must remain explicitly unverified.")
    return estimated_days


def validate_approval_and_claims(config):
    """Prevent draft completeness from becoming approval or execution."""

    approval = config["approval"]
    checks = (
        approval.get("manual_approval_required") is True,
        approval.get("approval_status") == "NOT_REVIEWED",
        approval.get("approved_by") is None,
        approval.get("approved_at") is None,
        approval.get("execution_released") is False,
    )
    if not all(checks):
        raise ValueError("The Day 37 draft approval state is incorrect.")
    validation = config["validation"]
    forbidden_true = (
        "requester_scope_may_be_treated_as_final",
        "automatic_approval_allowed",
        "automatic_execution_allowed",
        "real_change_claim_allowed",
        "engineering_impact_claim_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden_true):
        raise ValueError("A forbidden Day 37 claim or action was enabled.")


def print_introduction(config):
    """Print the fixed teaching introduction."""

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
    config = load_config("configs/day37_change_request.yaml")
    validate_execution_lock(config)
    runbook_path, registry_path, registry = load_runbook_and_registry(config)
    entry = find_registry_entry(config, registry)
    target_path, actual_value = validate_target_fingerprint_and_value(config)
    estimated_days = validate_request_fields(config, registry)
    validate_approval_and_claims(config)

    request = config["change_request"]
    approval = config["approval"]
    print_introduction(config)
    print("========== DAY 37 CHANGE-REQUEST PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No change-request output, ZOS-API connection or historical task execution will occur.")
    print("The proposed Day 22 value will not be written to the source config.")
    print(f"Day 35 runbook: {runbook_path}")
    print(f"Day 29 registry: {registry_path}")
    print()
    print(f"Request: {request['request_id']} ({request['request_status']})")
    print(f"Changed Day: {request['changed_day']} - {entry['title']}")
    print(f"Execution class: {entry['execution_class']}")
    print(f"Target: {target_path}")
    print(f"Target SHA256: {config['source']['target_config_sha256']}")
    print(f"Field: {request['target_field']}")
    print(f"Teaching value: {actual_value:.3f} -> {float(request['proposed_value']):.3f} {request['unit']}")
    print(f"Reason: {request['change_reason']}")
    print("Risk hypotheses:")
    for risk in request["risk_hypotheses"]:
        print(f"  - {risk}")
    print(f"Requester-estimated review Days: {estimated_days} (UNVERIFIED)")
    print(f"Approval: {approval['approval_status']}; execution released: {approval['execution_released']}")
    print()
    print("[PASS] Day 35 intake and manual scope-approval gates verified")
    print("[PASS] Day 22 maps to a complete Day 29 registry entry")
    print("[PASS] Target config SHA256 and current value verified")
    print("[PASS] Required change, reason, risk and rollback fields completed")
    print("[PASS] Requester scope retained as an unverified hypothesis")
    print("[PASS] Draft is not approved and no execution was released")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
