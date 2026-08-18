"""Day 53 step 2: generate the Slot 2 six-case residual-batch approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day53_slot2_residual_batch_approval_plan import prepare_plan, sha256_file  # noqa: E402


def build_record(config, plan):
    contract = plan["execution_contract"]
    return {
        "task": "day53_slot2_residual_batch_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day52_review": {"path": plan["source_day52_review"], "sha256": config["source"]["day52_review_sha256"], "verified": True},
        "source_day51_result": {"path": plan["source_day51_result"], "sha256": config["source"]["day51_result_sha256"], "verified": True},
        "historical_residual_batch": {"path": plan["historical_residual_batch"], "sha256": config["source"]["historical_residual_batch_sha256"], "verified": True},
        "day23_optical_inputs": {
            "config_path": plan["day23_config"],
            "config_sha256": config["source"]["day23_config_sha256"],
            "focused_model_path": plan["focused_model"],
            "focused_model_sha256": config["source"]["focused_model_sha256"],
            "modified": False,
        },
        "approved_scope": {
            "resource_slot": 2,
            "days": [23],
            "execution_class": "uses_zosapi",
            "case_ids": list(contract["approved_case_ids"]),
            "offsets_mm": list(contract["approved_offsets_mm"]),
            "maximum_batch_execution_count": 1,
            "maximum_case_execution_count": 6,
        },
        "execution_contract": contract,
        "decision": {
            "approver_role": config["decision"]["approver_role"],
            "approved_capabilities": plan["approved_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "next_required_gate": "Day54只执行一次六案例批次并立即停止在CP09；不得自动释放Day24或Slot 3-6。",
        },
        "permissions": plan["permissions"],
        "approval_record_generated": True,
        "approved_batch_executed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "model_copy_created": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    if record["decision_status"] != "SLOT_02_APPROVED_FOR_SIX_CASE_RESIDUAL_BATCH_EXECUTION":
        raise ValueError("Day 53 decision status is incorrect.")
    scope = record["approved_scope"]
    if len(scope["case_ids"]) != 6 or 0.0 in [float(value) for value in scope["offsets_mm"]]:
        raise ValueError("Day 53 scope is not exactly six nonzero cases.")
    if record["permissions"]["residual_batch_execution_released"] is not True:
        raise ValueError("Day 53 did not release the residual batch.")
    locked = ("baseline_rerun_released", "quick_focus_released", "optimization_released", "save_as_released", "source_modification_released", "downstream_slots_released", "engineering_change_released")
    if any(record["permissions"][key] is not False for key in locked):
        raise ValueError("Day 53 released a forbidden capability.")
    actions = ("approved_batch_executed", "new_zosapi_connection_created", "new_optical_metric_calculated", "model_copy_created", "existing_source_modified", "downstream_slots_released", "engineering_change_approved")
    if any(record[key] is not False for key in actions):
        raise ValueError("Day 53 approval generation performed an unsupported action.")


def build_markdown(record):
    rows = "\n".join(f"- `{case_id}`：`{float(offset):+.3f} mm`" for case_id, offset in zip(record["approved_scope"]["case_ids"], record["approved_scope"]["offsets_mm"]))
    return f"""# Day53 Slot 2 六案例残余离焦批次审批

## 审批结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot 2 / Day23 / 六个非零案例 / 一次批次
- 审批生成时连接 ZOS-API：`False`
- 审批生成时执行光学分析：`False`

## 获批案例

{rows}

## 冻结运行契约

- 专用入口：`{record['execution_contract']['required_entrypoint']}`
- 输出根目录：`{record['execution_contract']['approved_output_root']}`
- 执行方式：串行，每次最多一个 Standalone 连接
- 每案例：独立工作副本、Standard Spot、FFT MTF
- 禁止：基线重跑、Quick Focus、优化、SaveAs
- 批次后停止门：`{record['execution_contract']['post_execution_gate']}`

## 重要区别

API、文件或分析异常会停止批次；某个案例的光学性能较差只会被记录，不等于程序执行失败。

## 下一步

{record['decision']['next_required_gate']}

本记录不是 Day24 执行许可，也不是工程变更批准。
"""


def main():
    config = load_config("configs/day53_slot2_residual_batch_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    validate_record(record)
    frozen = [Path(plan[key]) for key in ("source_day52_review", "source_day51_result", "historical_residual_batch", "day23_config", "focused_model")]
    before = {path: sha256_file(path) for path in frozen}
    names = config["planned_outputs_after_approval"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    if any(sha256_file(path) != digest for path, digest in before.items()):
        raise ValueError("A frozen Day 53 input changed during approval generation.")
    print("========== DAY 53 SLOT-2 RESIDUAL-BATCH APPROVAL RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 2 / Day 23 / six nonzero residual cases / one batch")
    print(f"Cases: {record['approved_scope']['case_ids']}")
    print(f"Offsets: {record['approved_scope']['offsets_mm']} mm")
    print(f"Required entrypoint: {record['execution_contract']['required_entrypoint']}")
    print("Residual six-case batch execution released: True")
    print("Approved batch executed by Day53: False")
    print("Slot 3-6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day52, Day51 and Day23 evidence")
    print("[PASS] Exactly six nonzero cases and one batch execution released")
    print("[PASS] Sequential single-channel execution and independent copies frozen")
    print("[PASS] Day53 performed no ZOS-API connection or optical analysis")
    print("[PASS] Baseline rerun, Quick Focus, optimization, SaveAs and Slot 3-6 remain locked")
    print("[PASS] No engineering change was approved")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
