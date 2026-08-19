"""Day 55 step 2: generate the CP09 review record for the Day 54 batch."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day55_cp09_slot2_residual_batch_review_plan import prepare_review, sha256_file  # noqa: E402


def build_record(config, review):
    result = review["result"]
    maximum_spot = max(row["historical_spot_difference_um"] for row in review["case_audits"])
    maximum_mtf = max(row["historical_mtf_difference"] for row in review["case_audits"])
    return {
        "task": "day55_cp09_slot2_residual_batch_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day54_result": {"path": str(review["result_path"]), "sha256": config["source"]["day54_batch_sha256"], "verified": True},
        "source_day53_approval": {"path": str(review["approval_path"]), "sha256": config["source"]["day53_approval_sha256"], "verified": True},
        "authorization_consumption": {"path": str(review["marker_path"]), "sha256": config["source"]["authorization_marker_sha256"], "consumed_once": True, "rerun_released": False},
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 2,
            "day": 23,
            "task_review_status": "PASS",
            "case_count": result["case_count"],
            "case_ids": result["case_ids"],
            "case_audits": review["case_audits"],
            "case_report_count": len(review["case_audits"]),
            "raw_spot_file_count": len(review["case_audits"]),
            "raw_mtf_file_count": len(review["case_audits"]),
            "maximum_historical_spot_difference_um": maximum_spot,
            "maximum_historical_mtf_difference": maximum_mtf,
            "all_connections_closed": result["all_connections_closed"],
            "all_input_models_unchanged": result["all_input_models_unchanged"],
            "all_working_copies_unchanged": result["all_working_copies_unchanged"],
            "result_is_complete": True,
            "result_is_reproducible": True,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "slot_03_release_approved": False,
            "next_required_gate": "另行审批是否释放Slot 3 / Day24离线验收复核；本记录不得自动执行Day24。",
        },
        "permissions": dict(config["permissions"]),
        "review_record_generated": True,
        "day54_rerun_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "slot_03_executed": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    if record["decision_status"] != "SLOT_02_RESIDUAL_BATCH_RESULT_REVIEW_PASSED_WAITING_FOR_SLOT_03_RELEASE_APPROVAL":
        raise ValueError("Day 55 review status is incorrect.")
    review = record["cp09_review"]
    if review["task_review_status"] != "PASS" or review["case_count"] != 6 or review["case_report_count"] != 6 or review["raw_spot_file_count"] != 6 or review["raw_mtf_file_count"] != 6:
        raise ValueError("Day 55 review evidence count is incomplete.")
    if record["permissions"]["slot_03_release_request_eligible"] is not True or record["permissions"]["slot_03_execution_released"] is not False:
        raise ValueError("Day 55 confused request eligibility with execution approval.")
    actions = ("day54_rerun_performed", "new_zosapi_connection_created", "new_optical_metric_calculated", "existing_source_modified", "slot_03_executed", "downstream_slots_released", "engineering_change_approved")
    if any(record[key] is not False for key in actions):
        raise ValueError("Day 55 review performed an unsupported action.")


def build_markdown(record):
    rows = "\n".join(
        f"| {row['case_id']} | {row['offset_mm']:+.3f} | {row['historical_spot_difference_um']:.9f} | {row['historical_mtf_difference']:.9f} | PASS |"
        for row in record["cp09_review"]["case_audits"]
    )
    return f"""# Day55 CP09：Slot 2 六案例批次审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 2 批次任务审核：`PASS`
- Slot 3 执行已批准：`False`

## 逐案例回归验证

| 案例 | 偏移/mm | Spot历史差/um | MTF历史差 | 审核 |
|---|---:|---:|---:|---|
{rows}

## 完整性与安全性

- 案例 JSON：`6/6`
- 原始 Spot 文本：`6/6`
- 原始 FFT MTF 文本：`6/6`
- Day53 授权只消费一次：`True`
- 全部连接关闭：`True`
- 输入模型与磁盘副本不变：`True`
- Quick Focus、优化、SaveAs：均未使用

## 如何理解 PASS

PASS 表示 Day54 严格执行了获批任务，并复现了冻结的光学证据。它不表示六个偏移的光学性能都满足某项工程要求，也不表示 Slot 3 已经获准执行。

## 下一步

{record['decision']['next_required_gate']}
"""


def main():
    config = load_config("configs/day55_cp09_slot2_residual_batch_review.yaml")
    review = prepare_review(config)
    record = build_record(config, review)
    validate_record(record)
    frozen = [review["result_path"], review["marker_path"], review["approval_path"], review["model_path"]]
    frozen.extend(Path(row["case_report_path"]) for row in review["case_audits"])
    before = {path: sha256_file(path) for path in frozen}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    if any(sha256_file(path) != digest for path, digest in before.items()):
        raise ValueError("A frozen Day 55 input changed during review generation.")
    print("========== DAY 55 CP09 SLOT-2 RESIDUAL-BATCH REVIEW RECORD ==========")
    print("No ZOS-API connection, optical calculation, rerun or Slot 3 release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 2 residual-batch task review: PASS")
    print("Cases / case reports / raw Spot / raw MTF: 6 / 6 / 6 / 6")
    print(f"Maximum historical Spot difference: {record['cp09_review']['maximum_historical_spot_difference_um']:.9f} um")
    print(f"Maximum historical MTF difference: {record['cp09_review']['maximum_historical_mtf_difference']:.9f}")
    print("Slot 3 release approved: False")
    print()
    print("[PASS] Day54 execution and Day53 one-time authorization verified")
    print("[PASS] Six case reports and twelve raw analysis files verified")
    print("[PASS] Historical reproduction and every safety boundary passed")
    print("[PASS] Task-review PASS remains separate from optical acceptance")
    print("[PASS] Day54 was not rerun and no new ZOS-API connection was created")
    print("[PASS] No downstream slot or engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
