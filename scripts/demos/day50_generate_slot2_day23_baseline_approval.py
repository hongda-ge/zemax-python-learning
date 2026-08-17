"""Day 50 step 2: generate the minimal Slot 2 baseline-control approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day50_slot2_day23_baseline_approval_plan import (  # noqa: E402
    build_plan,
    load_frozen_json,
    sha256_file,
    validate_contract_and_decision,
    validate_day48_change_evidence,
    validate_day49_gate,
    validate_execution_lock,
    validate_optical_inputs,
    validate_slot2,
)


def build_record(config, plan):
    """Build an approval record without opening Zemax or executing Day 23."""

    return {
        "task": "day50_slot2_day23_baseline_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day49_review": {
            "path": plan["source_day49_review"],
            "sha256": config["source"]["day49_review_sha256"],
            "verified": True,
        },
        "source_day48_change_evidence": {
            "path": plan["source_day48_result"],
            "sha256": config["source"]["day48_result_sha256"],
            "positioning_accuracy_mm": config["change_specific_evidence"]["positioning_accuracy_mm"],
            "is_optical_input": False,
            "verified": True,
        },
        "source_day42_schedule": {
            "path": plan["source_day42_schedule"],
            "sha256": config["source"]["day42_schedule_sha256"],
            "slot": 2,
            "verified": True,
        },
        "day23_optical_inputs": {
            "config_path": plan["day23_config"],
            "config_sha256": config["source"]["day23_config_sha256"],
            "focused_model_path": plan["focused_model"],
            "focused_model_sha256": plan["focused_model_sha256"],
            "modified": False,
        },
        "previous_baseline_control": {
            "path": plan["previous_control"],
            "sha256": config["source"]["previous_day23_control_sha256"],
            "case_id": "defocus_004",
            "offset_mm": 0.0,
            "verified": True,
        },
        "approved_scope": {
            "resource_slot": 2,
            "days": [23],
            "execution_class": "uses_zosapi",
            "case_ids": ["defocus_004"],
            "maximum_execution_count": 1,
        },
        "execution_contract": plan["execution_contract"],
        "decision": {
            "approver_role": config["decision"]["approver_role"],
            "approved_capabilities": plan["approved_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "next_required_gate": (
                "Day51只执行一次零离焦基线控制并立即停止；基线证据须经CP09人工审核，"
                "不得自动执行六个非零残余离焦案例。"
            ),
        },
        "permissions": plan["permissions"],
        "approval_record_generated": True,
        "approved_task_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "model_copy_created": False,
        "existing_source_modified": False,
        "residual_cases_released": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Ensure the record releases exactly one baseline control and nothing more."""

    expected_scope = {
        "resource_slot": 2,
        "days": [23],
        "execution_class": "uses_zosapi",
        "case_ids": ["defocus_004"],
        "maximum_execution_count": 1,
    }
    if record["approved_scope"] != expected_scope:
        raise ValueError("The Day 50 approval scope is broader than one baseline control.")
    if record["decision_status"] != "SLOT_02_APPROVED_FOR_DAY23_BASELINE_CONTROL_EXECUTION":
        raise ValueError("The Day 50 approval status is incorrect.")
    if record["permissions"]["day23_baseline_control_execution_released"] is not True:
        raise ValueError("The Day 50 record did not release the baseline control.")
    locked_permissions = (
        "residual_case_execution_released",
        "quick_focus_released",
        "optimization_released",
        "save_as_released",
        "source_modification_released",
        "downstream_slots_released",
        "engineering_change_released",
    )
    if any(record["permissions"][key] is not False for key in locked_permissions):
        raise ValueError("The Day 50 record released a forbidden capability.")
    false_fields = (
        "approved_task_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "model_copy_created",
        "existing_source_modified",
        "residual_cases_released",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 50 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render a concise Chinese review sheet for the maintainer."""

    approved = "\n".join(f"- `{item}`" for item in record["decision"]["approved_capabilities"])
    forbidden = "\n".join(f"- `{item}`" for item in record["decision"]["forbidden_capabilities"])
    contract = record["execution_contract"]
    return f"""# Day50 Slot 2 / Day23 基线控制审批

## 审批结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot `2` / Day `23` / `defocus_004` / 一次执行
- 审批生成时已连接ZOS-API：`False`
- 审批生成时已执行光学分析：`False`

## 冻结输入

- Day23 配置：`{record['day23_optical_inputs']['config_path']}`
- 配置 SHA256：`{record['day23_optical_inputs']['config_sha256']}`
- 聚焦模型：`{record['day23_optical_inputs']['focused_model_path']}`
- 模型 SHA256：`{record['day23_optical_inputs']['focused_model_sha256']}`
- 变化专用 Day22 证据中的定位精度：`+/-{record['source_day48_change_evidence']['positioning_accuracy_mm']:.3f} mm`

## 运行契约

- 专用入口：`{contract['required_entrypoint']}`
- 输出根目录：`{contract['approved_output_root']}`
- 允许案例：`defocus_004`，offset = `0.000 mm`
- 最大执行次数：`1`
- 执行后停止门：`{contract['post_execution_gate']}`

## 已批准能力

{approved}

## 仍禁止能力

{forbidden}

## 下一步

{record['decision']['next_required_gate']}

本记录批准的是一次基线复现，不是六点残余离焦批次，也不是工程变更批准。
"""


def main():
    config = load_config("configs/day50_slot2_day23_baseline_approval.yaml")
    validate_execution_lock(config)
    validate_contract_and_decision(config)
    review_path, review = load_frozen_json(
        config, "day49_review_record", "day49_review_sha256", "expected_day49_task"
    )
    result_path, result = load_frozen_json(
        config, "day48_result", "day48_result_sha256", "expected_day48_task"
    )
    schedule_path, schedule = load_frozen_json(
        config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task"
    )
    control_path, previous_control = load_frozen_json(
        config,
        "previous_day23_control",
        "previous_day23_control_sha256",
        "expected_previous_control_task",
    )
    validate_day49_gate(config, review)
    slot2 = validate_slot2(config, schedule)
    validate_day48_change_evidence(config, result)
    day23_config_path, model_path = validate_optical_inputs(config, previous_control)
    plan = build_plan(
        config,
        review_path,
        result_path,
        schedule_path,
        day23_config_path,
        model_path,
        control_path,
        slot2,
    )
    record = build_record(config, plan)
    validate_record(record)

    frozen_paths = (
        review_path,
        result_path,
        schedule_path,
        control_path,
        day23_config_path,
        model_path,
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    names = config["planned_outputs_after_approval"]
    root = PROJECT_ROOT / names["root"]
    stamp = datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")

    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 50 input changed during approval generation: {path}")

    print("========== DAY 50 SLOT-2 DAY23 BASELINE APPROVAL RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 2 / Day 23 / defocus_004 / one execution")
    print(f"Focused model SHA256: {record['day23_optical_inputs']['focused_model_sha256']}")
    print(f"Required entrypoint: {record['execution_contract']['required_entrypoint']}")
    print("Day23 baseline control execution released: True")
    print("Approved task executed by Day50: False")
    print("Six nonzero residual cases released: False")
    print()
    print("[PASS] Approval bound to frozen Day49, Day48, Day42 and Day23 evidence")
    print("[PASS] Exactly one zero-defocus baseline control released")
    print("[PASS] Spot and FFT MTF recipes retained without Quick Focus")
    print("[PASS] Day50 performed no ZOS-API connection or optical analysis")
    print("[PASS] Residual cases, model save and downstream slots remain locked")
    print("[PASS] No engineering change was approved")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
