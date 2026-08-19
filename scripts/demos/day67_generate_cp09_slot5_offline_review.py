"""Day 67 step 2: generate the CP09 Slot 5 offline review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day67_cp09_slot5_offline_review_plan import (  # noqa: E402
    prepare_review,
    sha256_file,
)


def source_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, review):
    source = config["source"]
    day27 = review["day27"]
    return {
        "task": "day67_cp09_slot5_offline_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day66_package": source_record(review["package_path"], source["day66_package_sha256"]),
        "source_day65_approval": source_record(review["approval_path"], source["day65_approval_sha256"]),
        "authorization_consumption": {
            **source_record(review["marker_path"], source["authorization_marker_sha256"]),
            "consumed_once": True,
        },
        "day26_result": source_record(review["day26_path"], source["day26_result_sha256"]),
        "day26_detail_csv": source_record(review["day26_detail_path"], source["day26_detail_csv_sha256"]),
        "day26_summary_csv": source_record(review["day26_summary_path"], source["day26_summary_csv_sha256"]),
        "day27_result": source_record(review["day27_path"], source["day27_result_sha256"]),
        "day27_availability_csv": source_record(review["day27_csv_path"], source["day27_availability_csv_sha256"]),
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 5,
            "days": [26, 27],
            "package_execution_review_status": "PASS",
            "day26_task_state": "COMPLETED",
            "day26_result_review_status": "ACCEPTED",
            "day26_detail_count": 6,
            "day26_summary_count": 3,
            "day27_task_state": day27["task_state"],
            "day27_scientific_review_completed": False,
            "day27_blocked_is_failure": False,
            "day27_required_state_count": day27["required_state_count"],
            "day27_available_state_count": day27["available_state_count"],
            "day27_missing_state_count": day27["missing_state_count"],
            "day27_missing_unique_offsets_mm": day27["missing_unique_offsets_mm"],
            "sibling_isolation_preserved": True,
            "slot6_release_condition_met": False,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "evidence_recovery_plan_request_eligible": True,
            "evidence_recovery_execution_approved": False,
            "slot6_release_approved": False,
            "next_required_gate": "先为Day27缺失精确状态制定证据恢复计划并单独审批；补测、Day27重算和Slot 6均未获准。",
        },
        "permissions": dict(config["permissions"]),
        "review_record_generated": True,
        "day66_rerun_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "interpolation_used": False,
        "evidence_recovery_executed": False,
        "existing_source_modified": False,
        "slot6_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    checks = (
        record["decision_status"] == "SLOT_05_EXECUTION_REVIEW_PASSED_DAY27_EVIDENCE_BLOCKED_SLOT_06_LOCKED",
        record["cp09_review"]["package_execution_review_status"] == "PASS",
        record["cp09_review"]["day26_result_review_status"] == "ACCEPTED",
        record["cp09_review"]["day27_task_state"] == "BLOCKED_BY_MISSING_EXACT_MEASURED_STATES",
        record["cp09_review"]["day27_blocked_is_failure"] is False,
        record["cp09_review"]["slot6_release_condition_met"] is False,
        record["decision"]["evidence_recovery_plan_request_eligible"] is True,
        record["decision"]["evidence_recovery_execution_approved"] is False,
        record["decision"]["slot6_release_approved"] is False,
    )
    if not all(checks):
        raise ValueError("Day 67 CP09 record is invalid.")
    false_fields = (
        "day66_rerun_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "interpolation_used",
        "evidence_recovery_executed",
        "existing_source_modified",
        "slot6_released",
        "continuous_tolerance_claimed",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("Day 67 record contains an unsupported action or claim.")


def markdown(record):
    review = record["cp09_review"]
    return f"""# Day67 CP09 Slot 5 离线复核审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 5执行包审核：`PASS`
- Day26：`COMPLETED / ACCEPTED`
- Day27：`{review['day27_task_state']}`
- Slot 6已释放：`False`

## Day26结果

Day26使用新的 ±0.012 mm 定位精度完成重算。六条策略明细和三条策略汇总完整，结果不因Day27证据不足而失效。

## Day27证据状态

- 所需精确状态：`{review['day27_required_state_count']}`
- 已有状态：`{review['day27_available_state_count']}`
- 缺失状态：`{review['day27_missing_state_count']}`
- 缺失偏移：`{review['day27_missing_unique_offsets_mm']}` mm

Day27是证据不足导致的BLOCKED，不是执行失败，也不能生成PASS/FAIL候选结论。

## 下游门控

Day28依赖Day27，因此Slot 6释放条件尚未满足。本记录只允许申请证据恢复计划，不批准补测、Day27重算或Slot 6执行。

## 安全边界

- 未重跑Day66；
- 未连接ZOS-API；
- 未插值或计算新光学指标；
- 未修改冻结来源；
- 未批准连续公差或工程变更。
"""


def main():
    config = load_config("configs/day67_cp09_slot5_offline_review.yaml")
    review = prepare_review(config)
    record = build_record(config, review)
    validate_record(record)
    frozen_paths = (
        review["package_path"], review["marker_path"], review["approval_path"],
        review["day26_path"], review["day26_detail_path"], review["day26_summary_path"],
        review["day27_path"], review["day27_csv_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(record), encoding="utf-8")
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 67 input changed during review generation: {path}")

    print("========== DAY 67 CP09 SLOT-5 OFFLINE REVIEW RECORD ==========")
    print("No rerun, ZOS-API connection, optical calculation, evidence recovery or Slot 6 release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 5 package execution review: PASS")
    print("Day26 result review: COMPLETED / ACCEPTED")
    print(f"Day27 result review: {review['day27']['task_state']}")
    print(f"Day27 exact states: {review['day27']['available_state_count']}/{review['day27']['required_state_count']} available")
    print(f"Missing offsets: {review['day27']['missing_unique_offsets_mm']}")
    print("Evidence-recovery plan request eligible: True")
    print("Evidence-recovery execution approved: False")
    print("Slot 6 release approved: False")
    print()
    print("[PASS] Day66 execution, Day65 approval and one-time consumption verified")
    print("[PASS] Day26 JSON and both CSV files verified and accepted")
    print("[PASS] Day27 JSON and twelve-state availability CSV verified")
    print("[PASS] Package PASS remains separate from Day27 scientific blocking")
    print("[PASS] Day26 sibling result retained without overblocking")
    print("[PASS] No rerun, interpolation, new optical calculation or downstream release")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
