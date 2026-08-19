"""Day 59 step 2: generate the Slot 4 Day 25 control approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day59_slot4_day25_baseline_approval_plan import prepare_plan  # noqa: E402


def build_record(config, plan):
    contract = dict(plan["contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    limits = dict(plan["day25"]["balanced_acceptance"]["limits"])
    return {
        "task": "day59_slot4_day25_baseline_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day58_review": {"path": str(plan["review_path"]), "sha256": config["source"]["day58_review_sha256"], "verified": True},
        "day25_config": {"path": str(plan["day25_path"]), "sha256": config["source"]["day25_config_sha256"], "verified": True},
        "historical_baseline_control": {"path": str(plan["historical_path"]), "sha256": config["source"]["historical_baseline_control_sha256"], "verified": True},
        "day42_schedule": {"path": str(plan["schedule_path"]), "sha256": config["source"]["day42_schedule_sha256"], "verified": True},
        "focused_model": {"path": str(plan["model_path"]), "sha256": config["source"]["focused_model_sha256"], "verified": True},
        "balanced_acceptance_limits": limits,
        "approved_execution_contract": contract,
        "decision": {
            "approved_capabilities": list(config["decision"]["approved_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "Day60只可运行一次零偏移控制；完成后必须停在CP09，九点边界批次需要另行审批。",
        },
        "permissions": dict(config["permissions"]),
        "approval_record_generated": True,
        "approved_task_executed_by_day59": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "boundary_cases_executed": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    c = record["approved_execution_contract"]
    return f"""# Day 59：Slot 4 Day25 零偏移控制审批

## 审批结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot {c['resource_slot']} / Day {c['day']} / `{c['approved_case_id']}` / 一次执行
- 专用入口：`{c['required_entrypoint']}`

## 获准内容

Day60 可以创建一个隔离工作副本，建立一个 Standalone ZOS-API 连接，并在零偏移状态导出一次 Standard Spot 和一次 FFT MTF。

## 仍然禁止

- 执行九个边界案例；
- Quick Focus、优化或 SaveAs；
- 修改正式配置或冻结模型；
- 自动释放 Slot 5-6；
- 声称连续公差或工程变更批准。

## 学习与简历价值

这一步体现了高风险光学批次的分段放行：先用控制组验证模型和分析配方，再决定是否批准实验组，降低批量运行错误传播风险。
"""


def main():
    config = load_config("configs/day59_slot4_day25_baseline_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    md_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(record), encoding="utf-8")
    print("========== DAY 59 SLOT-4 DAY25 BASELINE APPROVAL RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 4 / Day 25 / boundary_control_000 / one execution")
    print(f"Focused model SHA256: {record['focused_model']['sha256']}")
    print(f"Required entrypoint: {record['approved_execution_contract']['required_entrypoint']}")
    print("Zero-offset control execution released: True")
    print("Approved task executed by Day59: False")
    print("Nine boundary cases released: False")
    print("Slot 5-6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day58, Day42 and Day25 evidence")
    print("[PASS] Exactly one zero-offset control execution released")
    print("[PASS] Spot and FFT MTF recipes retained without Quick Focus")
    print("[PASS] Day59 performed no ZOS-API connection or optical analysis")
    print("[PASS] Nine boundary cases, model save and Slot 5-6 remain locked")
    print("[PASS] No continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {md_path}")


if __name__ == "__main__":
    main()
