"""Day 74 step 2: generate the CP09 recovery-retry review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day74_cp09_recovery_retry_review_plan import prepare_plan, sha256_file  # noqa: E402


def build_record(config, result, plan):
    audit = plan["audit"]
    return {
        "task": "day74_cp09_recovery_retry_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day73_result": {"path": str(plan["result_path"]), "sha256": config["source"]["day73_result_sha256"], "verified": True},
        "source_day72_approval": {"path": str(plan["approval_path"]), "sha256": config["source"]["day72_approval_sha256"], "verified": True},
        "source_day71_failure_review": {"path": str(plan["review_path"]), "sha256": config["source"]["day71_review_sha256"], "verified": True},
        "authorization_consumption": {
            "path": str(plan["marker_path"]),
            "sha256": config["source"]["authorization_marker_sha256"],
            "verified": True,
            "consumed_once": True,
            "reusable": False,
        },
        "cp09_review": {
            "checkpoint_id": "CP09_retry_gate",
            "day": 27,
            "task_review_status": "PASS",
            "case_id": result["case"]["case_id"],
            "offset_mm": float(result["case"]["offset_mm"]),
            "retry_number": int(result["case"]["retry_number"]),
            "license_recovery_status": "STANDALONE_ZOSAPI_REVERIFIED",
            "license_valid": True,
            "zosapi_version": result["connection"]["version"],
            "maximum_spot_reproduction_difference_um": audit["maximum_spot_difference_um"],
            "maximum_mtf_reproduction_difference": audit["maximum_mtf_difference"],
            "balanced_acceptance_pass": True,
            "balanced_acceptance_checks": dict(result["balanced_acceptance_checks"]),
            "spot_raw_text": {"path": str(audit["spot_text"]), "sha256": audit["spot_sha256"]},
            "mtf_raw_text": {"path": str(audit["mtf_text"]), "sha256": audit["mtf_sha256"]},
            "focused_model_sha256": config["source"]["focused_model_sha256"],
            "working_copy_sha256": sha256_file(audit["working_copy"]),
            "connection_closed": True,
            "result_is_complete": True,
            "result_is_reproducible": True,
            "safety_boundary_preserved": True,
        },
        "recovery_chain": {
            "day70_outcome": "PRE_ANALYSIS_ZOSAPI_LICENSE_CONNECTION_FAILURE",
            "day71_review": "PASS_RETRY_APPROVAL_REQUEST_ELIGIBLE",
            "day72_approval": "ONE_ZERO_CONTROL_RETRY_ATTEMPT",
            "day73_outcome": "SUCCESS_LICENSE_AND_OPTICAL_BASELINE_REVERIFIED",
            "day74_review": "PASS",
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": plan["released_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "seven_point_batch_execution_approved": False,
            "next_required_gate": "另行审批是否释放七个Day27证据恢复点；本审核记录不得自动连接ZOS-API或执行批次。",
        },
        "permissions": plan["permissions"],
        "review_record_generated": True,
        "day73_rerun_performed": False,
        "additional_retry_executed": False,
        "recovery_cases_executed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "day27_recalculated": False,
        "slot6_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    expected = "DAY73_RECOVERY_RETRY_RESULT_REVIEW_PASSED_WAITING_FOR_SEVEN_POINT_BATCH_APPROVAL"
    if record["decision_status"] != expected or record["cp09_review"]["task_review_status"] != "PASS":
        raise ValueError("The Day 74 CP09 decision is invalid.")
    if record["decision"]["seven_point_batch_execution_approved"] is not False:
        raise ValueError("Day 74 incorrectly released the recovery batch.")
    false_fields = (
        "day73_rerun_performed", "additional_retry_executed", "recovery_cases_executed",
        "new_zosapi_connection_created", "new_optical_metric_calculated",
        "existing_source_modified", "day27_recalculated", "slot6_released",
        "continuous_tolerance_claimed", "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 74 record contains an unsupported action or claim.")


def build_markdown(record):
    review = record["cp09_review"]
    return f"""# Day74 CP09 Day73 恢复重试审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Day73重试任务审核：`PASS`
- Standalone ZOS-API许可证：`REVERIFIED`
- 已执行案例：`{review['case_id']}`，retry `{review['retry_number']}`，offset `{review['offset_mm']:+.3f} mm`
- 七点恢复批次已释放：`False`

## 复现与安全证据

- ZOS-API版本：`{review['zosapi_version']}`
- 最大Spot差值：`{review['maximum_spot_reproduction_difference_um']:.9f} um`
- 最大MTF差值：`{review['maximum_mtf_reproduction_difference']:.9f}`
- 均衡四指标AND规则：`PASS`
- Spot文本SHA256：`{review['spot_raw_text']['sha256']}`
- FFT MTF文本SHA256：`{review['mtf_raw_text']['sha256']}`
- 模型与磁盘工作副本SHA256：一致
- ZOS-API连接关闭：`True`

## 恢复链

Day70许可证连接失败 → Day71安全审核 → Day72签发新授权 → Day73成功重试 → Day74 CP09审核通过。

## 权限边界

本记录只允许提出七点恢复批次审批申请。它没有释放批次执行、额外重试、ZOS-API、Day27重算、Slot 6、连续容差声明或工程变更权限。

## 下一道门

{record['decision']['next_required_gate']}
"""


def main():
    config = load_config("configs/day74_cp09_recovery_retry_review.yaml")
    result, plan = prepare_plan(config)
    record = build_record(config, result, plan)
    validate_record(record)
    audit = plan["audit"]
    frozen_paths = (
        plan["result_path"], plan["approval_path"], plan["marker_path"], plan["review_path"],
        audit["focused_model"], audit["historical_control"], audit["working_copy"],
        audit["spot_text"], audit["mtf_text"],
    )
    frozen_hashes = {Path(path): sha256_file(Path(path)) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 74 input changed during review generation: {path}")

    print("========== DAY 74 CP09 RECOVERY-RETRY REVIEW RECORD ==========")
    print("No rerun, ZOS-API connection, optical calculation or recovery-batch release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Day73 recovery retry task review: PASS")
    print("Standalone ZOS-API license reverified: True")
    print("Executed case: recovery_control_000 / retry 01 / +0.000 mm")
    print(
        "Maximum Spot/MTF reproduction difference: "
        f"{record['cp09_review']['maximum_spot_reproduction_difference_um']:.9f} um / "
        f"{record['cp09_review']['maximum_mtf_reproduction_difference']:.9f}"
    )
    print("Balanced four-metric acceptance: PASS")
    print("Seven-point recovery batch execution approved: False")
    print()
    print("[PASS] Day73 execution, Day72 approval and consumption marker verified")
    print("[PASS] Day70 failure through Day73 recovery chain verified")
    print("[PASS] Raw Spot/MTF evidence and fingerprints verified")
    print("[PASS] Historical reproduction and all safety boundaries passed")
    print("[PASS] Review PASS remains separate from recovery-batch approval")
    print("[PASS] No rerun, additional retry, new connection or downstream release")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
