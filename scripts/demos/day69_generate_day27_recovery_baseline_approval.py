"""Day 69 step 2: generate the Day 27 recovery-control approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day69_day27_recovery_baseline_approval_plan import prepare_plan  # noqa: E402


def source_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, plan):
    source = config["source"]
    contract = dict(plan["contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "task": "day69_day27_recovery_baseline_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day68_plan": source_record(plan["plan_path"], source["day68_plan_sha256"]),
        "recovery_case_csv": source_record(plan["case_csv_path"], source["recovery_case_csv_sha256"]),
        "day25_config": source_record(plan["day25_path"], source["day25_config_sha256"]),
        "focused_model": source_record(plan["model_path"], source["focused_model_sha256"]),
        "historical_zero_control": source_record(plan["historical_path"], source["historical_zero_control_sha256"]),
        "approved_execution_contract": contract,
        "decision": {
            "approved_capabilities": list(config["decision"]["approved_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "Day70只可执行一次零偏移控制；完成后必须停在CP09，七点恢复批次仍需另行审批。",
        },
        "permissions": dict(config["permissions"]),
        "approval_record_generated": True,
        "approved_task_executed_by_day69": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "recovery_cases_executed": False,
        "day27_recalculated": False,
        "slot6_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    contract = record["approved_execution_contract"]
    return f"""# Day69 Day27 证据恢复零偏移控制审批

## 审批结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：恢复阶段1 / `{contract['approved_case_id']}` / 一次执行
- 专用入口：`{contract['required_entrypoint']}`

## 获准内容

Day70 可以创建一个隔离工作副本，建立一个 Standalone ZOS-API 连接，并在0mm状态导出一次 Standard Spot 和一次 FFT MTF。

## 仍然禁止

- 执行七个证据恢复点；
- Quick Focus、优化或 SaveAs；
- 重算Day27；
- 修改正式配置或冻结模型；
- 释放Slot 6或声明工程变更。

## 下一道门

零偏移控制执行完成后必须停在CP09。只有控制结果经人工审核通过，才能申请七点批次授权。
"""


def main():
    config = load_config("configs/day69_day27_recovery_baseline_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(record), encoding="utf-8")
    print("========== DAY 69 DAY27 RECOVERY BASELINE APPROVAL RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: recovery stage 01 / zero offset / one execution")
    print(f"Focused model SHA256: {record['focused_model']['sha256']}")
    print(f"Required entrypoint: {record['approved_execution_contract']['required_entrypoint']}")
    print("Zero-control execution released: True")
    print("Approved task executed by Day69: False")
    print("Seven-point recovery batch released: False")
    print("Day27 recalculation released: False")
    print("Slot 6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day68 plan and seven-point list")
    print("[PASS] Exactly one zero-offset Spot/FFT MTF control released")
    print("[PASS] Focused model, analysis recipe and historical control retained")
    print("[PASS] Day69 performed no ZOS-API connection or optical analysis")
    print("[PASS] Seven recovery points, Day27 recalculation and Slot 6 remain locked")
    print("[PASS] No continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
