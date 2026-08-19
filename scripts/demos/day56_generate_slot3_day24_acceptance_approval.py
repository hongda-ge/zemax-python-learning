"""Day 56 step 2: generate the Slot 3 Day 24 approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day56_slot3_day24_acceptance_approval_plan import prepare_plan  # noqa: E402


def build_record(config, plan):
    contract = dict(plan["contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "task": "day56_slot3_day24_acceptance_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day55_review": {"path": str(plan["day55_path"]), "sha256": config["source"]["day55_review_sha256"], "verified": True},
        "source_day52_review": {"path": str(plan["day52_path"]), "sha256": config["source"]["day52_review_sha256"], "verified": True},
        "day24_config": {"path": str(plan["day24_path"]), "sha256": config["source"]["day24_config_sha256"], "verified": True},
        "day42_schedule": {"path": str(plan["schedule_path"]), "sha256": config["source"]["day42_schedule_sha256"], "verified": True},
        "approved_execution_contract": contract,
        "frozen_scenarios": plan["scenarios"],
        "decision": {
            "approved_capabilities": list(config["decision"]["approved_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "Day57只可执行一次离线验收；完成后必须停在CP09，另行审核后才能考虑Slot 4。",
        },
        "permissions": dict(config["permissions"]),
        "approval_record_generated": True,
        "approved_task_executed_by_day56": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    c = record["approved_execution_contract"]
    return f"""# Day 56：Slot 3 Day24 离线验收审批记录

## 审批结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot {c['resource_slot']} / Day {c['day']} / `{c['execution_class']}` / 一次执行
- 专用入口：`{c['required_entrypoint']}`

## 获准内容

Day57 可以读取 Day52 的零偏移证据和 Day55 的六案例证据，对七个实测点执行一次 Day24 教学验收。三套阈值及四指标 AND 规则均已冻结。

## 仍然禁止

- 连接 ZOS-API 或重新计算 Spot/MTF；
- 修改正式配置或冻结证据；
- 插值并声称连续公差；
- 自动释放 Slot 4-6；
- 声称工程变更已经批准。

## 学习与简历价值

这一步展示了如何把批量光学证据、验收规则和最小权限审批绑定成可审计的离线质量门，而不是直接把脚本输出当作工程结论。
"""


def main():
    config = load_config("configs/day56_slot3_day24_acceptance_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    md_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown(record), encoding="utf-8")
    print("========== DAY 56 SLOT-3 DAY24 ACCEPTANCE APPROVAL RECORD ==========")
    print("No acceptance execution, ZOS-API connection, optical calculation or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 3 / Day 24 / offline_only / one execution")
    print(f"Cases: {record['approved_execution_contract']['expected_case_ids']}")
    print(f"Scenarios: {record['approved_execution_contract']['expected_scenarios']}")
    print(f"Required entrypoint: {record['approved_execution_contract']['required_entrypoint']}")
    print("Slot 3 offline execution released: True")
    print("Approved task executed by Day56: False")
    print("Slot 4-6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day55, Day52, Day42 and Day24 evidence")
    print("[PASS] Seven measured cases and three teaching scenarios frozen")
    print("[PASS] Exactly one dedicated offline execution released")
    print("[PASS] Day56 performed no acceptance calculation or ZOS-API connection")
    print("[PASS] Interpolation, engineering claims and Slot 4-6 remain locked")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {md_path}")


if __name__ == "__main__":
    main()
