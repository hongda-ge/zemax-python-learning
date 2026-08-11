"""Day 37 step 2: generate a reviewable maintenance change request."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day37_change_request_plan import (  # noqa: E402
    find_registry_entry,
    load_runbook_and_registry,
    sha256_file,
    validate_approval_and_claims,
    validate_execution_lock,
    validate_request_fields,
    validate_target_fingerprint_and_value,
)


def build_report(config, runbook_path, registry_path, entry, target_path, actual_value):
    """Build a request record without altering its target or running impact analysis."""

    request = config["change_request"]
    approval = config["approval"]
    return {
        "task": "day37_maintenance_change_request_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "request_id": request["request_id"],
        "input_request_status": request["request_status"],
        "request_status": "WAITING_FOR_APPROVAL",
        "request_is_hypothetical": True,
        "source_day35_runbook": {
            "path": str(runbook_path),
            "sha256": config["source"]["day35_runbook_sha256"],
            "verified": True,
        },
        "source_day29_registry": {
            "path": str(registry_path),
            "verified": True,
        },
        "registered_target": {
            "day": int(entry["day"]),
            "title": entry["title"],
            "phase_id": entry["phase_id"],
            "execution_class": entry["execution_class"],
            "primary_config": entry["primary_config"],
            "scripts": entry["scripts"],
            "learning_note": entry["learning_note"],
            "artifact_coverage_status": entry["artifact_coverage_status"],
        },
        "change": {
            "change_type": request["change_type"],
            "target_artifact": str(target_path),
            "target_artifact_sha256": config["source"]["target_config_sha256"],
            "target_field": request["target_field"],
            "current_value": actual_value,
            "proposed_value": float(request["proposed_value"]),
            "unit": request["unit"],
            "change_reason": request["change_reason"],
            "expected_benefit": request["expected_benefit"],
            "risk_hypotheses": request["risk_hypotheses"],
            "rollback_description": request["rollback_description"],
            "change_written_to_target": False,
        },
        "requester_estimate": {
            "review_days": [int(day) for day in request["requester_estimated_impact_days"]],
            "scope_is_unverified": True,
            "may_replace_dependency_analysis": False,
        },
        "approval": {
            "manual_approval_required": approval["manual_approval_required"],
            "approval_status": approval["approval_status"],
            "approved_by": approval["approved_by"],
            "approved_at": approval["approved_at"],
            "execution_released": approval["execution_released"],
        },
        "change_impact_analysis_performed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "real_change_claim_made": False,
        "engineering_impact_claim_made": False,
    }


def build_markdown(report):
    """Render the request record as a human-readable review form."""

    change = report["change"]
    target = report["registered_target"]
    estimate = report["requester_estimate"]
    approval = report["approval"]
    risk_lines = "\n".join(f"- {item}" for item in change["risk_hypotheses"])
    script_lines = "\n".join(f"- `{item}`" for item in target["scripts"])
    return f"""# Day37 维护变化申请

> 本申请是教学维护事件。状态为 `{report['request_status']}`，没有修改 Day22、没有执行影响分析，也没有释放任何历史任务。

## 1. 申请状态

- 申请编号：`{report['request_id']}`
- 输入状态：`{report['input_request_status']}`
- 当前状态：`{report['request_status']}`
- 人工审批：`{approval['approval_status']}`
- 已释放执行：`{approval['execution_released']}`
- 假想变化：`{report['request_is_hypothetical']}`

## 2. 变化对象

- 登记 Day：Day{target['day']} - {target['title']}
- 阶段：`{target['phase_id']}`
- 执行类型：`{target['execution_class']}`
- 目标文件：`{change['target_artifact']}`
- 当前 SHA256：`{change['target_artifact_sha256']}`
- 目标字段：`{change['target_field']}`
- 教学值：`{change['current_value']:.3f} -> {change['proposed_value']:.3f} {change['unit']}`
- 已写入目标文件：`{change['change_written_to_target']}`

## 3. 变化原因与预期价值

**原因：** {change['change_reason']}

**预期价值：** {change['expected_benefit']}

## 4. 风险假设

{risk_lines}

这些是申请阶段的风险提示，不是已经测得的影响。

## 5. 申请人预估范围

- 预估复核 Day：{estimate['review_days']}
- 范围已核实：`{not estimate['scope_is_unverified']}`
- 可以替代依赖分析：`{estimate['may_replace_dependency_analysis']}`

正式影响范围必须重新使用 Day30 依赖图和 Day31 影响分析计算。

## 6. Day22 登记资产

- 主配置：`{target['primary_config']}`
- 学习笔记：`{target['learning_note']}`
- 覆盖状态：`{target['artifact_coverage_status']}`
- 脚本：
{script_lines}

## 7. 回滚方式

{change['rollback_description']}

## 8. 审批门

本申请当前只是等待审核。维护者需要先确认变化理由和初始风险，再决定是否允许进入正式影响分析。即使申请获得批准，也不等于允许自动修改 Day22 或运行 Day23-Day28。

## 9. 本次安全状态

- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 新计算光学指标：`{report['new_optical_metric_calculated']}`
- 执行影响分析：`{report['change_impact_analysis_performed']}`
- 自动执行历史任务：`{report['automatic_execution_performed']}`
- 修改现有科学来源：`{report['existing_source_modified']}`
- 宣称真实变化或工程影响：`False`
"""


def main():
    config = load_config("configs/day37_change_request.yaml")
    validate_execution_lock(config)
    runbook_path, registry_path, registry = load_runbook_and_registry(config)
    entry = find_registry_entry(config, registry)
    target_path, actual_value = validate_target_fingerprint_and_value(config)
    validate_request_fields(config, registry)
    validate_approval_and_claims(config)

    hash_before = sha256_file(target_path)
    report = build_report(
        config,
        runbook_path,
        registry_path,
        entry,
        target_path,
        actual_value,
    )
    output_root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / f"change_request_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["planned_outputs_after_approval"]["json"]
    markdown_path = output_dir / config["planned_outputs_after_approval"]["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(report), encoding="utf-8")
    hash_after = sha256_file(target_path)
    if hash_before != hash_after or hash_after != config["source"]["target_config_sha256"]:
        raise ValueError("The Day 22 target changed while generating the request.")

    print("========== DAY 37 MAINTENANCE CHANGE REQUEST ==========")
    print("No ZOS-API connection, optical calculation, source modification or impact analysis was used.")
    print(f"Request: {report['request_id']}")
    print(f"Status: {report['input_request_status']} -> {report['request_status']}")
    print(f"Target: Day{entry['day']} / {target_path}")
    print(f"Target SHA256: {hash_after}")
    print(
        "Teaching value: "
        f"{report['change']['current_value']:.3f} -> "
        f"{report['change']['proposed_value']:.3f} {report['change']['unit']}"
    )
    print(f"Requester-estimated Days: {report['requester_estimate']['review_days']} (UNVERIFIED)")
    print(f"Approval: {report['approval']['approval_status']}")
    print(f"Execution released: {report['approval']['execution_released']}")
    print()
    print("[PASS] Request advanced to WAITING_FOR_APPROVAL without changing Day 22")
    print("[PASS] Registered assets, target fingerprint and current value preserved")
    print("[PASS] Requester estimate remains separate from formal impact analysis")
    print("[PASS] No ZOS-API, optical metric, automatic execution or engineering claim")
    print(f"[PASS] JSON request: {json_path}")
    print(f"[PASS] Markdown request: {markdown_path}")


if __name__ == "__main__":
    main()

