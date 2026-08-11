"""Day 38 step 2: generate a narrowly scoped impact-analysis approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day38_impact_analysis_approval_plan import (  # noqa: E402
    load_and_validate_day37,
    sha256_file,
    validate_decision_boundary,
    validate_execution_lock,
    validate_manual_gate,
    validate_target_unchanged,
)


def build_report(config, request_path, request_report, target_path, runbook_path):
    """Build an approval record that releases impact analysis only."""

    decision = config["approval_decision"]
    change = request_report["change"]
    estimate = request_report["requester_estimate"]
    return {
        "task": "day38_impact_analysis_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": decision["decision_id"],
        "decision_status": decision["decision_status"],
        "decision_is_teaching_record": True,
        "source_change_request": {
            "path": str(request_path),
            "sha256": config["source"]["day37_request_sha256"],
            "request_id": request_report["request_id"],
            "input_status": request_report["request_status"],
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
            "field": change["target_field"],
            "current_value": float(change["current_value"]),
            "proposed_value": float(change["proposed_value"]),
            "unit": change["unit"],
            "target_modified": False,
        },
        "decision": {
            "approver_role": decision["approver_role"],
            "decision_date": decision["decision_date"],
            "decision_reason": decision["decision_reason"],
            "approved_capabilities": list(decision["approved_capabilities"]),
            "forbidden_capabilities": list(decision["forbidden_capabilities"]),
            "next_required_gate": decision["next_required_gate"],
        },
        "requester_estimate": {
            "review_days": [int(day) for day in estimate["review_days"]],
            "scope_is_unverified": True,
            "may_replace_formal_impact_analysis": False,
        },
        "permissions": {
            "impact_analysis_released": True,
            "source_modification_released": False,
            "zosapi_execution_released": False,
            "optical_calculation_released": False,
            "historical_task_execution_released": False,
        },
        "impact_analysis_performed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "engineering_change_approved": False,
    }


def validate_report_boundary(report):
    """Recheck that the generated record cannot be read as broad approval."""

    permissions = report["permissions"]
    if permissions.get("impact_analysis_released") is not True:
        raise ValueError("The impact-analysis permission was not released.")
    forbidden_release_fields = (
        "source_modification_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "historical_task_execution_released",
    )
    if any(permissions.get(key) is not False for key in forbidden_release_fields):
        raise ValueError("The Day 38 approval record releases excessive permissions.")
    safety_false_fields = (
        "impact_analysis_performed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "engineering_change_approved",
    )
    if any(report.get(key) is not False for key in safety_false_fields):
        raise ValueError("The Day 38 record contains an unsupported action or claim.")


def build_markdown(report):
    """Render a human-readable approval record."""

    source = report["source_change_request"]
    target = report["target_under_review"]
    decision = report["decision"]
    estimate = report["requester_estimate"]
    permissions = report["permissions"]
    approved_lines = "\n".join(f"- `{item}`" for item in decision["approved_capabilities"])
    forbidden_lines = "\n".join(f"- `{item}`" for item in decision["forbidden_capabilities"])
    return f"""# Day38 影响分析审批记录

> 本记录只批准进入正式影响分析。它不批准修改 Day22，不批准连接 ZOS-API，也不批准运行 Day22-Day28。

## 1. 审批状态

- 审批编号：`{report['decision_id']}`
- 审批状态：`{report['decision_status']}`
- 教学记录：`{report['decision_is_teaching_record']}`
- 审批角色：`{decision['approver_role']}`
- 审批日期：`{decision['decision_date']}`
- 来源申请：`{source['request_id']}` / `{source['input_status']}`
- 来源申请 SHA256：`{source['sha256']}`

## 2. 审批理由

{decision['decision_reason']}

## 3. 本次允许的能力

{approved_lines}

## 4. 本次仍然禁止的能力

{forbidden_lines}

## 5. 审查中的目标

- 文件：`{target['path']}`
- SHA256：`{target['sha256']}`
- 字段：`{target['field']}`
- 教学值：`{target['current_value']:.3f} -> {target['proposed_value']:.3f} {target['unit']}`
- 已修改目标：`{target['target_modified']}`

## 6. 申请人的范围预估

- 预估复核 Day：`{estimate['review_days']}`
- 范围已核实：`{not estimate['scope_is_unverified']}`
- 可以替代正式影响分析：`{estimate['may_replace_formal_impact_analysis']}`

正式范围必须由冻结的依赖图重新计算。本记录没有确认 Day22-Day28 就是最终复核范围。

## 7. 权限释放状态

- 影响分析：`{permissions['impact_analysis_released']}`
- 修改源文件：`{permissions['source_modification_released']}`
- ZOS-API 执行：`{permissions['zosapi_execution_released']}`
- 光学计算：`{permissions['optical_calculation_released']}`
- 历史任务执行：`{permissions['historical_task_execution_released']}`

## 8. 下一道人工门

{decision['next_required_gate']}

## 9. 本次安全状态

- 已执行正式影响分析：`{report['impact_analysis_performed']}`
- 已自动执行任务：`{report['automatic_execution_performed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 新计算光学指标：`{report['new_optical_metric_calculated']}`
- 修改现有源文件：`{report['existing_source_modified']}`
- 已批准工程变更：`{report['engineering_change_approved']}`
"""


def main():
    config = load_config("configs/day38_impact_analysis_approval.yaml")
    validate_execution_lock(config)
    request_path, request_report = load_and_validate_day37(config)
    target_path = validate_target_unchanged(config, request_report)
    runbook_path = validate_manual_gate(config)
    validate_decision_boundary(config)

    request_hash_before = sha256_file(request_path)
    target_hash_before = sha256_file(target_path)
    report = build_report(config, request_path, request_report, target_path, runbook_path)
    validate_report_boundary(report)

    output_root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / f"approval_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["planned_outputs_after_approval"]["json"]
    markdown_path = output_dir / config["planned_outputs_after_approval"]["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(request_path) != request_hash_before:
        raise ValueError("The Day 37 request changed while generating approval.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed while generating approval.")

    print("========== DAY 38 IMPACT-ANALYSIS APPROVAL RECORD ==========")
    print("No impact analysis, source modification, ZOS-API connection or historical execution was used.")
    print(f"Request: {request_report['request_id']} ({request_report['request_status']})")
    print(f"Decision: {report['decision_id']} -> {report['decision_status']}")
    print(f"Approval record is teaching-only: {report['decision_is_teaching_record']}")
    print(f"Impact-analysis permission released: {report['permissions']['impact_analysis_released']}")
    print(f"Source modification released: {report['permissions']['source_modification_released']}")
    print(f"Historical task execution released: {report['permissions']['historical_task_execution_released']}")
    print(f"Requester-estimated Days: {report['requester_estimate']['review_days']} (still UNVERIFIED)")
    print()
    print("[PASS] Approval is bound to the frozen Day 37 request and Day 22 target")
    print("[PASS] Permission advanced only to formal impact analysis")
    print("[PASS] Day 22 remained unchanged")
    print("[PASS] ZOS-API, optical calculation and historical execution remain locked")
    print("[PASS] No impact analysis or engineering change was claimed")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
