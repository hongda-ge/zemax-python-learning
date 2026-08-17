"""Day 47 step 2: generate the Slot 1 offline execution approval record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day47_slot1_offline_execution_approval_plan import (  # noqa: E402
    build_plan,
    load_frozen_json,
    sha256_file,
    validate_day46_review,
    validate_decision,
    validate_execution_lock,
    validate_files_and_contract,
    validate_schedule_and_gate,
)


def build_record(config, plan):
    """Build an approval record that releases one task but does not run it."""

    return {
        "task": "day47_slot1_offline_execution_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day46_review": {
            "path": plan["source_day46_review"],
            "sha256": config["source"]["day46_review_sha256"],
            "verified": True,
        },
        "source_day42_schedule": {
            "path": plan["source_day42_schedule"],
            "sha256": config["source"]["day42_schedule_sha256"],
            "slot": 1,
            "verified": True,
        },
        "source_day35_runbook": {
            "path": plan["source_day35_runbook"],
            "sha256": config["source"]["day35_runbook_sha256"],
            "post_execution_gate": "CP09_slot_gate",
            "verified": True,
        },
        "official_source": {
            "path": plan["official_path"],
            "sha256": plan["official_sha256"],
            "modified": False,
        },
        "approved_candidate": {
            "path": plan["candidate_path"],
            "sha256": plan["candidate_sha256"],
            "modified": False,
        },
        "approved_scope": {
            "resource_slot": 1,
            "days": [22],
            "execution_class": "offline_only",
            "maximum_execution_count": 1,
        },
        "execution_contract": plan["execution_contract"],
        "decision": {
            "approver_role": config["decision"]["approver_role"],
            "decision_reason": config["decision"]["decision_reason"],
            "approved_capabilities": plan["approved_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "next_required_gate": "Day48执行一次Slot 1后必须停止，并由CP09人工审核结果；不得自动释放Slot 2。",
        },
        "permissions": plan["permissions"],
        "approval_record_generated": True,
        "approved_task_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Verify the one-task release and every retained safety lock."""

    if record["decision_status"] != "SLOT_01_APPROVED_FOR_CANDIDATE_OFFLINE_REVIEW_EXECUTION":
        raise ValueError("The Day 47 record has an incorrect decision status.")
    if record["approved_scope"] != {
        "resource_slot": 1,
        "days": [22],
        "execution_class": "offline_only",
        "maximum_execution_count": 1,
    }:
        raise ValueError("The Day 47 record exceeds one Slot 1 execution.")
    if record["permissions"]["slot_01_offline_execution_released"] is not True:
        raise ValueError("The Day 47 record did not release Slot 1 offline execution.")
    locked = (
        "source_modification_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "downstream_slots_released",
        "engineering_change_released",
    )
    if any(record["permissions"][key] is not False for key in locked):
        raise ValueError("The Day 47 record released a forbidden capability.")
    false_fields = (
        "approved_task_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 47 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render a human-readable Slot 1 execution approval."""

    approved = "\n".join(f"- `{item}`" for item in record["decision"]["approved_capabilities"])
    forbidden = "\n".join(f"- `{item}`" for item in record["decision"]["forbidden_capabilities"])
    contract = record["execution_contract"]
    return f"""# Day47 Slot 1 离线复核执行审批

## 审批结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：Slot `1` / Day `22` / `offline_only`
- 最大执行次数：`1`
- 审批记录生成时已执行：`False`

## 冻结输入与运行契约

- 候选：`{record['approved_candidate']['path']}`
- 候选 SHA256：`{record['approved_candidate']['sha256']}`
- 专用入口：`{contract['required_dedicated_entrypoint']}`
- 输出根目录：`{contract['approved_output_root']}`
- 执行后人工门：`CP09_slot_gate`

## 已批准能力

{approved}

## 仍禁止能力

{forbidden}

## 下一步

{record['decision']['next_required_gate']}

本审批只释放一次离线复核。它不批准修改正式配置、不批准ZOS-API、不批准下游槽，也不代表工程变化获批。
"""


def main():
    config = load_config("configs/day47_slot1_offline_execution_approval.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    review_path, review = load_frozen_json(
        config, "day46_review_record", "day46_review_sha256", "expected_day46_task"
    )
    schedule_path, schedule = load_frozen_json(
        config, "day42_schedule", "day42_schedule_sha256", "expected_day42_task"
    )
    runbook_path, runbook = load_frozen_json(
        config, "day35_runbook", "day35_runbook_sha256", "expected_day35_task"
    )
    validate_day46_review(config, review)
    slot1, _ = validate_schedule_and_gate(config, schedule, runbook)
    official_path, candidate_path = validate_files_and_contract(config)
    plan = build_plan(
        config, review_path, schedule_path, runbook_path, official_path, candidate_path, slot1
    )
    record = build_record(config, plan)
    validate_record(record)

    frozen_hashes = {
        review_path: sha256_file(review_path),
        schedule_path: sha256_file(schedule_path),
        runbook_path: sha256_file(runbook_path),
        official_path: sha256_file(official_path),
        candidate_path: sha256_file(candidate_path),
    }
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")

    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 47 input changed during approval generation: {path}")

    print("========== DAY 47 SLOT-1 OFFLINE EXECUTION APPROVAL RECORD ==========")
    print("No Day22 execution, source modification, ZOS-API connection or optical calculation was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Slot 1 / Day 22 / offline_only / one execution")
    print(f"Frozen candidate SHA256: {record['approved_candidate']['sha256']}")
    print(f"Required entrypoint: {record['execution_contract']['required_dedicated_entrypoint']}")
    print("Slot 1 offline execution released: True")
    print("Approved task executed by Day47: False")
    print("Downstream slots released: False")
    print()
    print("[PASS] Approval bound to frozen Day46, Day42 and Day35 evidence")
    print("[PASS] Official and candidate fingerprints remained unchanged")
    print("[PASS] Exactly one isolated Day22 offline execution released")
    print("[PASS] Dedicated entrypoint, output boundary and CP09 stop frozen")
    print("[PASS] Day47 performed no execution")
    print("[PASS] ZOS-API, official modification and Slot 2-6 remain locked")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
