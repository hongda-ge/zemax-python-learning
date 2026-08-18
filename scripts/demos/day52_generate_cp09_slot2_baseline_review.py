"""Day 52 step 2: generate the formal CP09 Slot 2 baseline review."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day52_cp09_slot2_baseline_review_plan import (  # noqa: E402
    build_plan,
    load_frozen_json,
    sha256_file,
    validate_approval,
    validate_decision,
    validate_execution_lock,
    validate_files_and_metrics,
    validate_result_safety,
)


def build_record(config, plan, result):
    """Build a PASS record while retaining every execution lock."""

    audit = plan["audit"]
    return {
        "task": "day52_cp09_slot2_baseline_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day51_result": {
            "path": plan["result_path"],
            "sha256": plan["result_sha256"],
            "verified": True,
        },
        "source_day50_approval": {
            "path": plan["approval_path"],
            "sha256": config["source"]["day50_approval_sha256"],
            "verified": True,
        },
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 2,
            "day": 23,
            "task_review_status": "PASS",
            "case_id": result["case"]["case_id"],
            "offset_mm": float(result["case"]["offset_mm"]),
            "authorization_consumed_once": True,
            "positioning_accuracy_mm": float(
                result["change_specific_evidence"]["positioning_accuracy_mm"]
            ),
            "positioning_accuracy_is_optical_input": False,
            "maximum_spot_reproduction_difference_um": audit[
                "maximum_spot_difference_um"
            ],
            "maximum_mtf_reproduction_difference": audit["maximum_mtf_difference"],
            "spot_raw_text": {
                "path": str(audit["spot_text"]),
                "sha256": audit["spot_sha256"],
            },
            "mtf_raw_text": {
                "path": str(audit["mtf_text"]),
                "sha256": audit["mtf_sha256"],
            },
            "focused_model_sha256": config["source"]["focused_model_sha256"],
            "working_copy_sha256": sha256_file(audit["working_copy"]),
            "connection_closed": True,
            "result_is_complete": True,
            "result_is_reproducible": True,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": plan["released_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "residual_batch_release_approved": False,
            "next_required_gate": (
                "另行审批是否释放六个非零残余离焦案例；本审核记录不得自动连接ZOS-API或执行批次。"
            ),
        },
        "permissions": plan["permissions"],
        "review_record_generated": True,
        "day51_rerun_performed": False,
        "residual_cases_executed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Recheck review/execution separation before writing evidence."""

    if record["decision_status"] != "SLOT_02_BASELINE_RESULT_REVIEW_PASSED_WAITING_FOR_RESIDUAL_BATCH_APPROVAL":
        raise ValueError("The Day 52 review status is incorrect.")
    if record["cp09_review"]["task_review_status"] != "PASS":
        raise ValueError("The Day 52 baseline task review did not pass.")
    if record["decision"]["residual_batch_release_approved"] is not False:
        raise ValueError("Day 52 incorrectly approved the residual batch.")
    false_fields = (
        "day51_rerun_performed",
        "residual_cases_executed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 52 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render the human-readable CP09 Slot 2 review."""

    review = record["cp09_review"]
    return f"""# Day52 CP09 Slot 2 基线结果审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 2 基线任务审核：`PASS`
- 已执行案例：`{review['case_id']}`，offset = `{review['offset_mm']:+.3f} mm`
- 非零残余批次已释放：`False`

## 复现证据

- 最大 Spot 差值：`{review['maximum_spot_reproduction_difference_um']:.9f} um`
- 最大 MTF 差值：`{review['maximum_mtf_reproduction_difference']:.9f}`
- Spot 文本 SHA256：`{review['spot_raw_text']['sha256']}`
- FFT MTF 文本 SHA256：`{review['mtf_raw_text']['sha256']}`
- 模型与磁盘工作副本 SHA256：一致
- ZOS-API 连接关闭：`True`

## 对 0.012 mm 的解释

定位精度 `+/-0.012 mm` 是变化专用机构误差证据，并未作为 Zemax 模型参数写入。零离焦基线完整复现，说明本次维护流程没有意外改变光学输入或分析配方。

## 权限边界

本记录只允许提出六个非零残余案例的执行审批申请。它没有释放批次执行、ZOS-API、源文件修改、Slot 3-6 或工程变更权限。

## 下一道门

{record['decision']['next_required_gate']}
"""


def main():
    config = load_config("configs/day52_cp09_slot2_baseline_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(
        config, "day51_result", "day51_result_sha256", "expected_day51_task"
    )
    approval_path, approval = load_frozen_json(
        config, "day50_approval", "day50_approval_sha256", "expected_day50_task"
    )
    validate_approval(config, approval, result)
    validate_result_safety(config, result)
    audit = validate_files_and_metrics(config, result)
    plan = build_plan(config, result_path, approval_path, audit)
    record = build_record(config, plan, result)
    validate_record(record)

    frozen_paths = (
        result_path,
        approval_path,
        audit["focused_model"],
        audit["previous_control"],
        audit["working_copy"],
        audit["spot_text"],
        audit["mtf_text"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    names = config["output"]
    root = PROJECT_ROOT / names["root"]
    stamp = datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")

    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 52 input changed during review generation: {path}")

    print("========== DAY 52 CP09 SLOT-2 BASELINE REVIEW RECORD ==========")
    print("No ZOS-API connection, optical calculation, rerun or residual-case release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 2 baseline task review: PASS")
    print(f"Executed case: {review_case(record)}")
    print(
        "Maximum Spot/MTF reproduction difference: "
        f"{record['cp09_review']['maximum_spot_reproduction_difference_um']:.9f} um / "
        f"{record['cp09_review']['maximum_mtf_reproduction_difference']:.9f}"
    )
    print("Residual six-case execution approved: False")
    print()
    print("[PASS] Day51 execution and Day50 one-time authorization verified")
    print("[PASS] Raw Spot/MTF evidence and fingerprints verified")
    print("[PASS] Baseline reproduction and all safety boundaries passed")
    print("[PASS] Review PASS remains separate from residual-batch approval")
    print("[PASS] Day51 was not rerun and no new ZOS-API connection was created")
    print("[PASS] No downstream slot or engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


def review_case(record):
    """Format the reviewed case for console teaching output."""

    review = record["cp09_review"]
    return f"{review['case_id']} ({review['offset_mm']:+.3f} mm)"


if __name__ == "__main__":
    main()
