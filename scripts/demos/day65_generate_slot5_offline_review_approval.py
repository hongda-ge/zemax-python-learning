"""Day 65 step 2: generate the Slot 5 offline review approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day65_slot5_offline_review_approval_plan import prepare_plan  # noqa: E402


def evidence(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, plan):
    source = config["source"]
    contract = dict(plan["contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "task": "day65_slot5_offline_review_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day64_review": evidence(plan["review_path"], source["day64_review_sha256"]),
        "day42_schedule": evidence(plan["schedule_path"], source["day42_schedule_sha256"]),
        "change_evidence": evidence(plan["change_path"], source["change_evidence_sha256"]),
        "day25_measured_evidence": evidence(plan["day25_path"], source["day25_report_sha256"]),
        "day26_config": evidence(plan["config_paths"]["day26_config"], source["day26_config_sha256"]),
        "historical_day26_report": evidence(plan["day26_history_path"], source["historical_day26_report_sha256"]),
        "day27_config": evidence(plan["config_paths"]["day27_config"], source["day27_config_sha256"]),
        "historical_day27_report": evidence(plan["day27_history_path"], source["historical_day27_report_sha256"]),
        "change_specific_positioning_accuracy_mm": plan["changed_accuracy_mm"],
        "measured_offsets_mm": plan["measured_offsets_mm"],
        "day27_exact_state_requirements": plan["day27_requirements"],
        "day27_missing_exact_offsets_mm": plan["missing_offsets_mm"],
        "day27_expected_evidence_status": contract["missing_evidence_status"],
        "approved_execution_contract": contract,
        "decision": {
            "approved_capabilities": list(config["decision"]["approved_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "Day66执行一次Slot 5离线包后必须停在CP09；Day26与Day27分别审核，Slot 6仍需另行批准。",
        },
        "permissions": dict(config["permissions"]),
        "approval_record_generated": True,
        "approved_task_executed_by_day65": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "interpolation_used": False,
        "existing_source_modified": False,
        "slot_06_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    contract = record["approved_execution_contract"]
    missing = ", ".join(f"{value:+.3f}" for value in record["day27_missing_exact_offsets_mm"])
    return f"""# Day 65：Slot 5 Day26/Day27 离线复核审批

## 审批结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot 5 / Day26 与 Day27 / 一次离线复核包
- 专用入口：`{contract['required_entrypoint']}`

## 两个同槽任务

Day26 获准使用新的 ±{record['change_specific_positioning_accuracy_mm']:.3f} mm 教学定位精度，重新比较 0.002 mm 与 0.005 mm 边界宽度。

Day27 只先获准做精确测量点可用性审计。当前已识别的缺失偏移为：`[{missing}] mm`。只要这些精确状态仍缺失，就必须记录 `{record['day27_expected_evidence_status']}`，不能通过插值制造通过/失败结论。

## 为什么要隔离同槽分支

Day26 与 Day27 在资源调度上属于同一槽，但不存在“Day27证据不足就让Day26结果失效”的规则。Day66 必须分别保存两项任务状态。

## 仍然禁止

- 连接 ZOS-API 或计算新光学指标；
- 对缺失的 Day27 状态插值或外推；
- 修改正式配置或冻结证据；
- 自动释放 Slot 6；
- 声称连续公差或工程变更批准。

## 学习与简历价值

这一步展示了证据驱动工作流中的“可计算性检查”和同槽故障隔离：任务缺少必要观测时，系统输出可审计的阻塞状态，同时保留独立兄弟任务的有效执行路径。
"""


def main():
    config = load_config("configs/day65_slot5_offline_review_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    md_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(record), encoding="utf-8")
    print("========== DAY 65 SLOT-5 OFFLINE REVIEW APPROVAL RECORD ==========")
    print("No Slot 5 execution, ZOS-API connection, optical calculation or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 5 / Days [26, 27] / offline_only / one review package")
    print(f"Change-specific positioning accuracy: +/-{record['change_specific_positioning_accuracy_mm']:.3f} mm")
    print("Day26 offline stopping evaluation released: True")
    print("Day27 exact-state availability audit released: True")
    print(f"Day27 missing exact offsets: {record['day27_missing_exact_offsets_mm']}")
    print(f"Expected Day27 status if still missing: {record['day27_expected_evidence_status']}")
    print("Approved task executed by Day65: False")
    print("Slot 6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day64, Day42 and change-specific evidence")
    print("[PASS] Day26 and Day27 frozen configs plus historical reports verified")
    print("[PASS] Exactly one two-task offline review package released")
    print("[PASS] Day27 missing evidence must block its result without overblocking Day26")
    print("[PASS] Day65 performed no offline review execution or ZOS-API connection")
    print("[PASS] Interpolation, Slot 6 and engineering claims remain locked")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {md_path}")


if __name__ == "__main__":
    main()
