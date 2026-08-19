"""Day 71 step 2: generate the Day 70 license-failure review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day71_day70_license_failure_review_plan import prepare_review, sha256_file  # noqa: E402


def source_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, review):
    source = config["source"]
    failure = review["failure"]
    return {
        "task": "day71_day70_license_failure_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day70_failure": source_record(review["failure_path"], source["day70_failure_sha256"]),
        "source_day69_approval": source_record(review["approval_path"], source["day69_approval_sha256"]),
        "authorization_consumption": {**source_record(review["marker_path"], source["authorization_marker_sha256"]), "consumed_once": True, "reusable": False},
        "day70_config": source_record(review["config_path"], source["day70_config_sha256"]),
        "focused_model": source_record(review["model_path"], source["focused_model_sha256"]),
        "working_copy": source_record(review["copy_path"], source["working_copy_sha256"]),
        "failure_review": {
            "classification": "PRE_ANALYSIS_ZOSAPI_LICENSE_CONNECTION_FAILURE",
            "execution_task_completed": False,
            "error_type": failure["error"]["type"],
            "error_message": failure["error"]["message"],
            "zosapi_connection_established": False,
            "connection_object_required_closure": False,
            "spot_output_created": False,
            "fft_mtf_output_created": False,
            "optical_metric_calculated": False,
            "input_model_unchanged": True,
            "working_copy_unchanged": True,
            "quick_focus_used": False,
            "optimization_used": False,
            "save_as_used": False,
            "safety_review_status": "PASS",
        },
        "license_recovery_observation": {
            "operator_confirmed_gui_reopened_successfully": True,
            "operator_confirmed_gui_closed_before_review": True,
            "matching_process_observed_during_pre_review_audit": False,
            "standalone_zosapi_license_reverified": False,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "retry_approval_request_eligible": True,
            "retry_execution_approved": False,
            "next_required_gate": "另行签发新的单次零偏移控制重试审批；不得复用Day69授权，也不得直接运行Day70。",
        },
        "permissions": dict(config["permissions"]),
        "review_record_generated": True,
        "day70_rerun_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "seven_recovery_cases_released": False,
        "slot6_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    review = record["failure_review"]
    return f"""# Day71 Day70 许可证失败审核

## 审核结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 分类：`{review['classification']}`
- 安全审核：`{review['safety_review_status']}`
- 新重试审批申请资格：`True`
- 重试执行已批准：`False`

## 失败事实

`{review['error_type']}: {review['error_message']}`

失败发生在Standalone连接建立阶段。没有运行Spot或FFT MTF，没有生成新光学指标，也没有修改输入模型或隔离副本。

## 授权状态

Day69一次性授权已经消费且不可复用。GUI重新打开成功并已关闭属于操作者恢复观察，但不等于Standalone ZOS-API许可证已经验证。

## 下一步

可以申请新的单次零偏移控制重试审批。审批签发前不得重跑Day70；七点恢复批次、Day27重算和Slot 6继续锁定。
"""


def main():
    config = load_config("configs/day71_day70_license_failure_review.yaml")
    review = prepare_review(config)
    record = build_record(config, review)
    frozen_paths = (review["failure_path"], review["marker_path"], review["approval_path"], review["config_path"], review["model_path"], review["copy_path"])
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(record), encoding="utf-8")
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 71 input changed during review generation: {path}")

    print("========== DAY 71 DAY70 LICENSE-FAILURE REVIEW RECORD ==========")
    print("No ZOS-API connection, retry execution, optical calculation or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print(f"Failure classification: {record['failure_review']['classification']}")
    print("Day70 execution task completed: False")
    print("Safety review: PASS")
    print("Input/working copy unchanged: True/True")
    print("Spot/FFT MTF outputs created: False/False")
    print("Original authorization consumed/reusable: True/False")
    print("Operator GUI recovery reported: True")
    print("Standalone ZOS-API license reverified: False")
    print("Retry approval request eligible: True")
    print("Retry execution approved: False")
    print("Seven-point batch and Slot 6 released: False")
    print()
    print("[PASS] Day70 failure, Day69 approval and consumption marker verified")
    print("[PASS] Failure occurred before optical analysis")
    print("[PASS] Model and working-copy fingerprints remained unchanged")
    print("[PASS] No residual process was observed before review")
    print("[PASS] Review separates GUI recovery report from API license verification")
    print("[PASS] Only a new retry-approval request was released")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
