"""Day 49 step 2: generate the formal CP09 Slot 1 review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day49_cp09_slot1_result_review_plan import (  # noqa: E402
    build_plan,
    compare_results,
    load_frozen_json,
    sha256_file,
    validate_authorization_and_safety,
    validate_decision,
    validate_execution_lock,
    validate_files,
)


def build_record(config, plan):
    """Build a CP09 PASS record while retaining the Slot 2 lock."""

    return {
        "task": "day49_cp09_slot1_result_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day48_result": {
            "path": plan["day48_result_path"],
            "sha256": plan["day48_result_sha256"],
            "verified": True,
        },
        "source_day47_approval": {
            "path": plan["day47_approval_path"],
            "sha256": config["source"]["day47_approval_sha256"],
            "verified": True,
        },
        "baseline_day22_result": {
            "path": plan["baseline_path"],
            "sha256": config["source"]["baseline_day22_sha256"],
            "verified": True,
        },
        "frozen_inputs": {
            "official_path": plan["official_path"],
            "official_sha256": config["source"]["official_day22_sha256"],
            "candidate_path": plan["candidate_path"],
            "candidate_sha256": config["source"]["candidate_sha256"],
            "modified": False,
        },
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "slot": 1,
            "day": 22,
            "task_review_status": "PASS",
            "all_teaching_cases_passed": False,
            "teaching_case_pass_count": 4,
            "teaching_case_count": 6,
            "changed_error_sources": plan["changed_error_sources"],
            "numeric_comparisons": plan["comparisons"],
            "result_is_complete": True,
            "result_is_explainable": True,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": plan["released_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "slot_02_release_approved": False,
            "next_required_gate": "另行审批是否释放Slot 2 / Day23；本记录本身不得触发任何下游执行。",
        },
        "permissions": plan["permissions"],
        "review_record_generated": True,
        "slot1_rerun_performed": False,
        "slot2_execution_released": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Recheck task/case separation and every retained downstream lock."""

    if record["decision_status"] != "SLOT_01_RESULT_REVIEW_PASSED_WAITING_FOR_SLOT_02_RELEASE_APPROVAL":
        raise ValueError("The Day 49 record has an incorrect decision status.")
    review = record["cp09_review"]
    if review["task_review_status"] != "PASS" or review["all_teaching_cases_passed"] is not False:
        raise ValueError("The Day 49 record confused task PASS with case PASS.")
    if review["teaching_case_pass_count"] != 4 or review["teaching_case_count"] != 6:
        raise ValueError("The Day 49 teaching-case count is incorrect.")
    if record["decision"]["slot_02_release_approved"] is not False:
        raise ValueError("Day 49 incorrectly approved Slot 2 release.")
    false_fields = (
        "slot1_rerun_performed",
        "slot2_execution_released",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 49 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render a human-readable CP09 review record."""

    comparisons = "\n".join(
        "- `{}`：合成余量增加 `{:.7f} mm`，所需半行程增加 `{:.7f} mm`，失败案例 `{}`".format(
            row["combination_policy_id"],
            row["combined_allowance_increase_mm"],
            row["required_half_travel_increase_mm"],
            row["failed_case_ids"],
        )
        for row in record["cp09_review"]["numeric_comparisons"]
    )
    return f"""# Day49 CP09 Slot 1 结果审核记录

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 1 任务审核：`PASS`
- 所有教学案例通过：`False`（`4/6`）
- Slot 2 已释放：`False`

任务 PASS 表示 Day48 按批准契约正确完成，不表示所有教学案例满足行程条件。

## 新旧结果差分

{comparisons}

唯一变化来源为定位精度教学值 `0.010 -> 0.012 mm`。两种策略的所需半行程增量均能由合成余量增量完整解释。

## 安全状态

- 正式配置和候选未修改；
- 未连接 ZOS-API；
- 未计算新的光学指标；
- 未重复运行 Slot 1；
- 未释放 Slot 2-6；
- 未批准工程变化。

## 下一道门

{record['decision']['next_required_gate']}
"""


def main():
    config = load_config("configs/day49_cp09_slot1_result_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    result_path, result = load_frozen_json(
        config, "day48_result", "day48_result_sha256", "expected_day48_task"
    )
    approval_path, approval = load_frozen_json(
        config, "day47_approval", "day47_approval_sha256", "expected_day47_task"
    )
    baseline_path, baseline = load_frozen_json(
        config, "baseline_day22_result", "baseline_day22_sha256", "expected_baseline_task"
    )
    official_path, candidate_path = validate_files(config)
    validate_authorization_and_safety(config, approval, result)
    changed_sources, comparisons = compare_results(config, baseline, result)
    plan = build_plan(
        config, result_path, approval_path, baseline_path, official_path,
        candidate_path, changed_sources, comparisons,
    )
    record = build_record(config, plan)
    validate_record(record)

    frozen_hashes = {
        result_path: sha256_file(result_path),
        approval_path: sha256_file(approval_path),
        baseline_path: sha256_file(baseline_path),
        official_path: sha256_file(official_path),
        candidate_path: sha256_file(candidate_path),
    }
    root = PROJECT_ROOT / config["planned_outputs_after_review"]["root"]
    stamp = datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_review"]
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")

    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 49 input changed during review generation: {path}")

    print("========== DAY 49 CP09 SLOT-1 RESULT REVIEW RECORD ==========")
    print("No task execution, source modification, ZOS-API connection or downstream release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 1 task review: PASS")
    print("Teaching cases passed: 4/6 (not all cases pass)")
    for row in record["cp09_review"]["numeric_comparisons"]:
        print(
            f"{row['combination_policy_id']}: allowance increase="
            f"{row['combined_allowance_increase_mm']:+.7f} mm, required travel increase="
            f"{row['required_half_travel_increase_mm']:+.7f} mm"
        )
    print("Slot 2 release approved: False")
    print()
    print("[PASS] Day48 execution and Day47 authorization evidence verified")
    print("[PASS] Numeric changes are fully explained by 0.010 -> 0.012 mm")
    print("[PASS] Task-review PASS remains separate from 4/6 case coverage")
    print("[PASS] Official config, candidate and frozen evidence remained unchanged")
    print("[PASS] Slot 1 was not rerun and Slot 2-6 remain locked")
    print("[PASS] No engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
