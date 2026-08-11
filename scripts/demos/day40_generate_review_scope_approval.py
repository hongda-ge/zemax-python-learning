"""Day 40 step 2: generate a planning-only review-scope approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day40_review_scope_approval_plan import (  # noqa: E402
    load_and_validate_day39,
    sha256_file,
    validate_decision_boundary,
    validate_execution_lock,
    validate_manual_gate,
    validate_target_unchanged,
)


def build_report(config, scope_path, scope_report, runbook_path, target_path):
    """Build an approval record that releases review planning only."""

    decision = config["approval_decision"]
    return {
        "task": "day40_review_scope_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": decision["decision_id"],
        "decision_status": decision["decision_status"],
        "decision_is_teaching_record": True,
        "source_day39_scope": {
            "path": str(scope_path),
            "sha256": config["source"]["day39_scope_sha256"],
            "changed_day": int(scope_report["changed_day"]),
            "formal_impact_analysis_performed": True,
            "verified": True,
        },
        "source_manual_gate": {
            "path": str(runbook_path),
            "sha256": config["source"]["day35_runbook_sha256"],
            "checkpoint_id": config["source"]["required_manual_checkpoint"],
            "verified": True,
        },
        "target_under_review": {
            "path": str(target_path),
            "sha256": config["source"]["target_config_sha256"],
            "modified": False,
        },
        "approved_review_scope": [int(day) for day in decision["approved_scope"]],
        "uses_zosapi_review_days": [int(day) for day in scope_report["uses_zosapi_review_days"]],
        "offline_only_review_days": [int(day) for day in scope_report["offline_only_review_days"]],
        "decision": {
            "approver_role": decision["approver_role"],
            "decision_date": decision["decision_date"],
            "decision_reason": decision["decision_reason"],
            "approved_capabilities": list(decision["approved_capabilities"]),
            "forbidden_capabilities": list(decision["forbidden_capabilities"]),
            "next_required_gate": decision["next_required_gate"],
        },
        "permissions": {
            "review_plan_generation_released": True,
            "source_modification_released": False,
            "zosapi_execution_released": False,
            "optical_calculation_released": False,
            "review_task_execution_released": False,
        },
        "review_plan_generated": False,
        "review_tasks_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "engineering_change_approved": False,
    }


def validate_report_boundary(report):
    """Prevent a planning approval from being interpreted as execution approval."""

    permissions = report["permissions"]
    if permissions.get("review_plan_generation_released") is not True:
        raise ValueError("Review-plan generation was not released.")
    false_permissions = (
        "source_modification_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "review_task_execution_released",
    )
    if any(permissions.get(key) is not False for key in false_permissions):
        raise ValueError("The Day 40 record releases excessive permissions.")
    false_states = (
        "review_plan_generated",
        "review_tasks_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "engineering_change_approved",
    )
    if any(report.get(key) is not False for key in false_states):
        raise ValueError("The Day 40 record contains an unsupported action or claim.")
    scope = report["approved_review_scope"]
    classified = report["uses_zosapi_review_days"] + report["offline_only_review_days"]
    if set(scope) != set(classified) or len(scope) != len(set(classified)):
        raise ValueError("The approved scope is not classified exactly once.")


def build_markdown(report):
    """Render the scope approval as a human-readable record."""

    decision = report["decision"]
    permissions = report["permissions"]
    approved_lines = "\n".join(f"- `{item}`" for item in decision["approved_capabilities"])
    forbidden_lines = "\n".join(f"- `{item}`" for item in decision["forbidden_capabilities"])
    return f"""# Day40 正式复核范围审批记录

> 本记录批准 Day22-Day28 进入复核方案规划，但不批准修改 Day22 或执行任何复核任务。

## 1. 审批状态

- 审批编号：`{report['decision_id']}`
- 审批状态：`{report['decision_status']}`
- 教学记录：`{report['decision_is_teaching_record']}`
- 审批角色：`{decision['approver_role']}`
- 审批日期：`{decision['decision_date']}`
- 审批理由：{decision['decision_reason']}

## 2. 来源证据

- Day39 报告：`{report['source_day39_scope']['path']}`
- Day39 SHA256：`{report['source_day39_scope']['sha256']}`
- Day35 人工门：`{report['source_manual_gate']['checkpoint_id']}`
- Day22 目标：`{report['target_under_review']['path']}`
- Day22 已修改：`{report['target_under_review']['modified']}`

## 3. 获批的正式范围

- 正式复核顺序：`{report['approved_review_scope']}`
- ZOS-API 复核类：`{report['uses_zosapi_review_days']}`
- 离线复核类：`{report['offline_only_review_days']}`

## 4. 本次允许的能力

{approved_lines}

## 5. 本次仍然禁止的能力

{forbidden_lines}

## 6. 权限释放状态

- 生成复核方案：`{permissions['review_plan_generation_released']}`
- 修改源文件：`{permissions['source_modification_released']}`
- ZOS-API 执行：`{permissions['zosapi_execution_released']}`
- 光学计算：`{permissions['optical_calculation_released']}`
- 复核任务执行：`{permissions['review_task_execution_released']}`

## 7. 下一道人工门

{decision['next_required_gate']}

## 8. 本次安全状态

- 已生成复核方案：`{report['review_plan_generated']}`
- 已执行复核任务：`{report['review_tasks_executed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 新计算光学指标：`{report['new_optical_metric_calculated']}`
- 修改现有源文件：`{report['existing_source_modified']}`
- 已批准工程变更：`{report['engineering_change_approved']}`
"""


def main():
    config = load_config("configs/day40_review_scope_approval.yaml")
    validate_execution_lock(config)
    scope_path, scope_report = load_and_validate_day39(config)
    runbook_path = validate_manual_gate(config)
    target_path = validate_target_unchanged(config, scope_report)
    validate_decision_boundary(config, scope_report)

    scope_hash_before = sha256_file(scope_path)
    target_hash_before = sha256_file(target_path)
    report = build_report(config, scope_path, scope_report, runbook_path, target_path)
    validate_report_boundary(report)

    output_root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("scope_approval_%Y%m%d_%H%M%S")
    output_dir = output_root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(scope_path) != scope_hash_before:
        raise ValueError("The Day 39 formal-scope report changed during approval generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed during approval generation.")

    permissions = report["permissions"]
    print("========== DAY 40 REVIEW-SCOPE APPROVAL RECORD ==========")
    print("No review plan, source modification, ZOS-API connection or review task execution was used.")
    print(f"Decision: {report['decision_id']} -> {report['decision_status']}")
    print(f"Approved review scope: {report['approved_review_scope']}")
    print(f"ZOS-API review class: {report['uses_zosapi_review_days']}")
    print(f"Offline review class: {report['offline_only_review_days']}")
    print(f"Review-plan generation released: {permissions['review_plan_generation_released']}")
    print(f"Source modification released: {permissions['source_modification_released']}")
    print(f"Review-task execution released: {permissions['review_task_execution_released']}")
    print()
    print("[PASS] Approval is bound to the frozen Day 39 formal scope")
    print("[PASS] Seven review nodes are classified exactly once")
    print("[PASS] Permission advanced only to review-plan generation")
    print("[PASS] Day 22 remained unchanged")
    print("[PASS] ZOS-API, optical calculation and review execution remain locked")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
