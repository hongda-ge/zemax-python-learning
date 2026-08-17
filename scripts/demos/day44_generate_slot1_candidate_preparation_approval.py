"""Day 44 step 2: generate the formal least-privilege candidate-preparation approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day44_slot1_candidate_preparation_approval_plan import (  # noqa: E402
    build_plan,
    load_json_source,
    sha256_file,
    validate_decision,
    validate_execution_lock,
    validate_gate_and_slot,
    validate_request_and_target,
    validate_runbook,
)


def build_record(config, plan, gate_path, request_path, runbook_path, target_path):
    """Build an approval record that releases preparation but not execution."""

    decision = config["decision"]
    boundary = config["candidate_boundary"]
    return {
        "task": "day44_slot1_candidate_preparation_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": decision["decision_id"],
        "decision_status": decision["decision_status"],
        "decision_is_teaching_record": decision["decision_is_teaching_record"],
        "source_day43_gate": {
            "path": str(gate_path),
            "sha256": config["source"]["day43_gate_report_sha256"],
            "verified": True,
        },
        "source_day37_request": {
            "path": str(request_path),
            "sha256": config["source"]["day37_change_request_sha256"],
            "request_id": "CR-DAY37-001",
            "verified": True,
        },
        "source_day35_runbook": {
            "path": str(runbook_path),
            "sha256": config["source"]["day35_runbook_sha256"],
            "checkpoint_id": "CP09_slot_gate",
            "verified": True,
        },
        "target_under_review": {
            "path": str(target_path),
            "sha256": config["source"]["target_config_sha256"],
            "modified": False,
        },
        "approved_scope": {
            "resource_slot": plan["approved_slot"],
            "days": plan["approved_days"],
            "execution_class": plan["execution_class"],
        },
        "change_under_preparation": {
            "field": boundary["target_field"],
            "current_value": float(boundary["current_value"]),
            "proposed_value": float(boundary["proposed_value"]),
            "unit": boundary["unit"],
        },
        "candidate_boundary": {
            "root": boundary["candidate_root"],
            "copy_official_config_before_edit": boundary["copy_official_config_before_edit"],
            "edit_candidate_only": boundary["edit_candidate_only"],
            "require_exactly_one_declared_value_change": boundary["require_exactly_one_declared_value_change"],
            "require_candidate_sha256": boundary["require_candidate_sha256"],
            "require_pre_execution_manifest": boundary["require_pre_execution_manifest"],
            "future_execution_requires_separate_approval": boundary["future_execution_requires_separate_approval"],
        },
        "decision": {
            "approver_role": decision["approver_role"],
            "decision_reason": decision["decision_reason"],
            "approved_capabilities": plan["approved_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "next_required_gate": "隔离候选、单字段差异和SHA256完成后，必须再次人工审批才能执行Slot 1。",
        },
        "permissions": plan["permissions"],
        "approval_record_generated": True,
        "candidate_prepared": False,
        "candidate_file_written": False,
        "review_task_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Revalidate approval scope and every retained execution lock."""

    if record["decision_status"] != "SLOT_01_APPROVED_FOR_ISOLATED_CANDIDATE_PREPARATION":
        raise ValueError("The Day 44 record has an incorrect decision status.")
    scope = record["approved_scope"]
    if scope != {"resource_slot": 1, "days": [22], "execution_class": "offline_only"}:
        raise ValueError("The Day 44 record exceeds Slot 1 / Day 22.")
    permissions = record["permissions"]
    if permissions["candidate_preparation_released"] is not True:
        raise ValueError("Day 44 did not release candidate preparation.")
    locked_permissions = (
        "source_modification_released",
        "slot_01_execution_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "downstream_slots_released",
    )
    if any(permissions[key] is not False for key in locked_permissions):
        raise ValueError("Day 44 unexpectedly released execution or source modification.")
    if record.get("approval_record_generated") is not True:
        raise ValueError("The Day 44 approval record was not marked as generated.")
    false_fields = (
        "candidate_prepared",
        "candidate_file_written",
        "review_task_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record.get(key) is not False for key in false_fields):
        raise ValueError("The Day 44 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render a concise human-readable approval record."""

    approved = "\n".join(f"- `{item}`" for item in record["decision"]["approved_capabilities"])
    forbidden = "\n".join(f"- `{item}`" for item in record["decision"]["forbidden_capabilities"])
    permissions = "\n".join(
        f"- `{key}`：`{value}`" for key, value in record["permissions"].items()
    )
    change = record["change_under_preparation"]
    return f"""# Day44 Slot 1 隔离候选准备审批记录

## 审批结论

- 决策编号：`{record['decision_id']}`
- 决策状态：`{record['decision_status']}`
- 教学审批记录：`{record['decision_is_teaching_record']}`
- 范围：Slot `{record['approved_scope']['resource_slot']}` / Day `{record['approved_scope']['days']}` / `{record['approved_scope']['execution_class']}`

本记录只批准准备隔离候选，不批准运行 Day22。

## 变化边界

- 字段：`{change['field']}`
- 当前值：`{change['current_value']:.3f} {change['unit']}`
- 候选值：`{change['proposed_value']:.3f} {change['unit']}`
- 正式配置：`{record['target_under_review']['path']}`
- 正式配置已修改：`{record['target_under_review']['modified']}`

## 已批准能力

{approved}

## 仍禁止能力

{forbidden}

## 权限矩阵

{permissions}

## 下一道门

{record['decision']['next_required_gate']}

候选必须位于 `outputs`，只改变一个声明字段，并记录来源与候选 SHA256。候选完成不等于 Slot 1 获准执行。
"""


def main():
    config = load_config("configs/day44_slot1_candidate_preparation_approval.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    gate_path, gate_report = load_json_source(
        config, "day43_gate_report", "day43_gate_report_sha256", "expected_day43_task"
    )
    request_path, request = load_json_source(
        config, "day37_change_request", "day37_change_request_sha256", "expected_day37_task"
    )
    runbook_path, runbook = load_json_source(
        config, "day35_runbook", "day35_runbook_sha256", "expected_day35_task"
    )
    validate_runbook(config, runbook)
    target_path = validate_request_and_target(config, request)
    _, slot1 = validate_gate_and_slot(config, gate_report)
    plan = build_plan(config, gate_path, request_path, runbook_path, target_path, slot1)
    record = build_record(config, plan, gate_path, request_path, runbook_path, target_path)
    validate_record(record)

    gate_hash_before = sha256_file(gate_path)
    request_hash_before = sha256_file(request_path)
    runbook_hash_before = sha256_file(runbook_path)
    target_hash_before = sha256_file(target_path)
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")

    if sha256_file(gate_path) != gate_hash_before:
        raise ValueError("The Day 43 gate report changed during Day 44 generation.")
    if sha256_file(request_path) != request_hash_before:
        raise ValueError("The Day 37 request changed during Day 44 generation.")
    if sha256_file(runbook_path) != runbook_hash_before:
        raise ValueError("The Day 35 runbook changed during Day 44 generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The official Day 22 config changed during Day 44 generation.")

    print("========== DAY 44 SLOT-1 CANDIDATE-PREPARATION APPROVAL RECORD ==========")
    print("No candidate file, source modification, ZOS-API connection or review execution was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 1 / Day 22 / offline_only")
    print("Candidate preparation released: True")
    print("Slot 1 execution released: False")
    print("Downstream slots released: False")
    print()
    print("[PASS] Approval is bound to Day 43, Day 37, Day 35 and the unchanged Day 22 target")
    print("[PASS] Permission advanced only to isolated candidate preparation")
    print("[PASS] Official Day 22 config remained unchanged")
    print("[PASS] Slot 1 execution, ZOS-API and Slot 2-6 remain locked")
    print("[PASS] No candidate was created and no engineering change was claimed")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
