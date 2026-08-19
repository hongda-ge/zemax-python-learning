"""Day 62 step 2: generate the Slot 4 nine-case boundary approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day62_slot4_day25_boundary_batch_approval_plan import (  # noqa: E402
    prepare_plan,
    sha256_file,
)


def build_record(config, plan):
    contract = plan["execution_contract"]
    return {
        "task": "day62_slot4_day25_boundary_batch_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day61_review": {"path": plan["source_day61_review"], "sha256": config["source"]["day61_review_sha256"], "verified": True},
        "source_day60_result": {"path": plan["source_day60_result"], "sha256": config["source"]["day60_result_sha256"], "verified": True},
        "historical_boundary_batch": {"path": plan["historical_boundary_batch"], "sha256": config["source"]["historical_boundary_batch_sha256"], "verified": True},
        "day25_optical_inputs": {
            "config_path": plan["day25_config"],
            "config_sha256": config["source"]["day25_config_sha256"],
            "focused_model_path": plan["focused_model"],
            "focused_model_sha256": config["source"]["focused_model_sha256"],
            "modified": False,
        },
        "approved_scope": {
            "resource_slot": 4,
            "days": [25],
            "execution_class": "uses_zosapi",
            "case_ids": list(contract["approved_case_ids"]),
            "offsets_mm": list(contract["approved_offsets_mm"]),
            "maximum_batch_execution_count": 1,
            "maximum_case_execution_count": 9,
        },
        "execution_contract": contract,
        "decision": {
            "approver_role": config["decision"]["approver_role"],
            "approved_capabilities": plan["approved_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "next_required_gate": "Day63只执行一次九案例批次并立即停止在CP09；不得自动释放Slot5-6。",
        },
        "permissions": plan["permissions"],
        "approval_record_generated": True,
        "approved_batch_executed_by_day62": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "model_copy_created": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    if record["decision_status"] != "SLOT_04_APPROVED_FOR_NINE_CASE_BOUNDARY_BATCH_EXECUTION":
        raise ValueError("Day 62 decision status is incorrect.")
    scope = record["approved_scope"]
    if len(scope["case_ids"]) != 9 or any(math_value == 0.0 for math_value in map(float, scope["offsets_mm"])):
        raise ValueError("Day 62 scope is not exactly nine nonzero cases.")
    if record["permissions"]["boundary_batch_execution_released"] is not True:
        raise ValueError("Day 62 did not release the boundary batch.")
    false_fields = (
        "approved_batch_executed_by_day62",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "model_copy_created",
        "existing_source_modified",
        "downstream_slots_released",
        "continuous_tolerance_claimed",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("Day 62 approval generation performed an unsupported action.")


def build_markdown(record):
    rows = "\n".join(
        f"- `{case_id}`：`{float(offset):+.3f} mm`"
        for case_id, offset in zip(record["approved_scope"]["case_ids"], record["approved_scope"]["offsets_mm"])
    )
    return f"""# Day62 Slot 4 九点边界扫描批次审批

## 审批结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot 4 / Day25 / 九个非零案例 / 一次批次
- 审批生成时连接ZOS-API：`False`
- 审批生成时执行光学分析：`False`

## 获批案例

{rows}

## 冻结运行契约

- 专用入口：`{record['execution_contract']['required_entrypoint']}`
- 输出根目录：`{record['execution_contract']['approved_output_root']}`
- 执行方式：串行，每次最多一个Standalone连接
- 每案例：独立工作副本、Standard Spot、FFT MTF、均衡验收
- 禁止：零偏移重跑、Quick Focus、优化、SaveAs
- 批次后停止门：`{record['execution_contract']['post_execution_gate']}`

## 重要区别

API、文件或指纹异常会停止批次；某案例不通过均衡教学阈值只会记录为验收FAIL，不等于程序执行失败。

## 下一步

{record['decision']['next_required_gate']}

本记录不释放Slot5-6，也不构成连续容差或工程变更批准。
"""


def main():
    config = load_config("configs/day62_slot4_day25_boundary_batch_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    validate_record(record)
    frozen = [
        Path(plan[key])
        for key in (
            "source_day61_review",
            "source_day60_result",
            "historical_boundary_batch",
            "day25_config",
            "focused_model",
        )
    ]
    before = {path: sha256_file(path) for path in frozen}
    names = config["planned_outputs_after_approval"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    if any(sha256_file(path) != digest for path, digest in before.items()):
        raise ValueError("A frozen Day 62 input changed during approval generation.")

    print("========== DAY 62 SLOT-4 BOUNDARY-BATCH APPROVAL RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 4 / Day 25 / nine nonzero boundary cases / one batch")
    print(f"Cases: {record['approved_scope']['case_ids']}")
    print(f"Offsets: {record['approved_scope']['offsets_mm']} mm")
    print(f"Required entrypoint: {record['execution_contract']['required_entrypoint']}")
    print("Nine-case boundary batch execution released: True")
    print("Approved batch executed by Day62: False")
    print("Slot 5-6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day61, Day60 and Day25 evidence")
    print("[PASS] Exactly nine nonzero cases and one batch execution released")
    print("[PASS] Sequential single-channel execution and independent copies frozen")
    print("[PASS] Day62 performed no ZOS-API connection or optical analysis")
    print("[PASS] Control rerun, Quick Focus, optimization, SaveAs and Slot 5-6 remain locked")
    print("[PASS] No continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
