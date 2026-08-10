"""Day 35 step 1: audit the complete maintenance runbook plan offline."""

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
    """Allow runbook reports while keeping Day 35 offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 35 execution switch must be Boolean.")
    if execution.get("allow_runbook_generation") is not True:
        raise ValueError("Day 35 runbook generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_runbook_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 35 prohibited action enabled: " + ", ".join(prohibited))


def validate_policies(config):
    """Validate the declared maintenance and safety policy."""

    policy = config["maintenance_policy"]
    required_true = (
        "registry_is_entrypoint",
        "fingerprints_checked_before_interpretation",
        "impact_scope_approved_before_rerun",
        "dependency_order_preserved",
        "resource_capacity_applied_after_dependency_order",
        "manual_gate_after_each_resource_slot",
        "failure_blocks_only_transitive_descendants",
        "reviewable_branch_requires_manual_resume",
        "blocked_nodes_require_repaired_upstream_evidence",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise ValueError("Day 35 maintenance policy is incomplete.")
    if policy.get("automatic_scientific_rerun_allowed") is not False:
        raise ValueError("Day 35 automatic scientific rerun must remain forbidden.")
    validation = config["validation"]
    forbidden = (
        "real_execution_claim_allowed",
        "automatic_rerun_allowed",
        "hidden_completion_score_allowed",
        "engineering_approval_claim_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden):
        raise ValueError("A forbidden Day 35 claim was enabled.")


def load_and_validate_sources(config):
    """Load all six frozen maintenance artifacts and verify provenance."""

    roles = set()
    loaded = []
    for source in config["sources"]:
        role = source["role"]
        if role in roles:
            raise ValueError(f"Duplicate Day 35 source role: {role}")
        roles.add(role)
        path = PROJECT_ROOT / source["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Day 35 source not found: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != source["sha256"]:
            raise ValueError(f"Day {source['day']} source SHA256 is incorrect.")
        report = json.loads(path.read_text(encoding="utf-8"))
        checks = (
            report["task"] == source["expected_task"],
            report["status"] == "success",
            int(report[source["expected_count_key"]]) == int(source["expected_count"]),
            report.get("new_zosapi_connection_created") is False,
        )
        if not all(checks):
            raise ValueError(f"Day {source['day']} source metadata is incorrect.")
        loaded.append(
            {
                "day": int(source["day"]),
                "role": role,
                "path": path,
                "sha256": actual_hash,
                "report": report,
            }
        )
    return loaded


def validate_checkpoints(config, sources):
    """Validate checkpoint coverage, order and manual safety gates."""

    checkpoints = config["checkpoints"]
    validation = config["validation"]
    if len(checkpoints) != int(validation["require_exact_checkpoint_count"]):
        raise ValueError("Day 35 checkpoint count is incorrect.")
    ids = [item["id"] for item in checkpoints]
    if len(ids) != len(set(ids)):
        raise ValueError("Day 35 checkpoint ids are not unique.")
    source_roles = {item["role"] for item in sources}
    used_roles = {item["evidence_role"] for item in checkpoints}
    if source_roles != used_roles:
        raise ValueError("Day 35 does not use every frozen source role.")
    expected_stages = [
        "intake", "intake", "provenance", "scope", "scope",
        "approval", "ordering", "scheduling", "execution_gate", "recovery",
    ]
    if [item["stage"] for item in checkpoints] != expected_stages:
        raise ValueError("Day 35 checkpoint stage order changed.")
    if "人工" not in checkpoints[5]["title"] or "人工" not in checkpoints[8]["title"]:
        raise ValueError("Day 35 manual approval gates are missing.")
    return checkpoints


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
    config = load_config("configs/day35_maintenance_runbook.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    sources = load_and_validate_sources(config)
    checkpoints = validate_checkpoints(config, sources)

    print_introduction(config)
    print("========== DAY 35 MAINTENANCE RUNBOOK PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, optical calculation or historical task execution will occur.")
    print("The runbook documents gates and recovery; it does not approve engineering reruns.")
    print()
    print("Frozen maintenance evidence:")
    for source in sources:
        print(f"  Day{source['day']}: {source['role']} -> SHA256 {source['sha256'][:12]}...")
    print()
    print("Planned checkpoints:")
    for index, checkpoint in enumerate(checkpoints, start=1):
        print(
            f"  {index:02d}. {checkpoint['id']} [{checkpoint['stage']}]: "
            f"{checkpoint['title']}"
        )
        print(f"      pass: {checkpoint['pass_condition']}")
        print(f"      fail: {checkpoint['fail_action']}")
    print()
    print("[PASS] Six frozen Day29-Day34 fingerprints verified")
    print("[PASS] Ten unique checkpoints cover intake through recovery")
    print("[PASS] Every maintenance evidence role is used")
    print("[PASS] Manual scope and per-slot approval gates retained")
    print("[PASS] Automatic rerun, hidden score and engineering approval claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
