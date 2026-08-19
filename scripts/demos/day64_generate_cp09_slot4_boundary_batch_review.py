"""Day 64 step 2: generate the formal CP09 Slot 4 batch review."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day64_cp09_slot4_boundary_batch_review_plan import (  # noqa: E402
    prepare_review,
    sha256_file,
)


def build_record(config, review):
    result = review["result"]
    maximum_spot = max(audit["historical_spot_difference_um"] for audit in review["case_audits"])
    maximum_mtf = max(audit["historical_mtf_difference"] for audit in review["case_audits"])
    return {
        "task": "day64_cp09_slot4_boundary_batch_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day63_result": {"path": str(review["result_path"]), "sha256": config["source"]["day63_batch_sha256"], "verified": True},
        "source_day62_approval": {"path": str(review["approval_path"]), "sha256": config["source"]["day62_approval_sha256"], "verified": True},
        "authorization_consumption": {"path": str(review["marker_path"]), "sha256": config["source"]["authorization_marker_sha256"], "verified": True, "consumed_once": True},
        "comparison_csv": {"path": str(review["csv_path"]), "sha256": config["source"]["comparison_csv_sha256"], "verified": True},
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 4,
            "day": 25,
            "task_review_status": "PASS",
            "case_count": 9,
            "case_report_count": 9,
            "raw_spot_file_count": 9,
            "raw_mtf_file_count": 9,
            "acceptance_pass_count": int(result["acceptance_pass_count"]),
            "acceptance_fail_count": 9 - int(result["acceptance_pass_count"]),
            "maximum_spot_reproduction_difference_um": maximum_spot,
            "maximum_mtf_reproduction_difference": maximum_mtf,
            "case_audits": review["case_audits"],
            "focused_model_sha256": config["source"]["focused_model_sha256"],
            "all_connections_closed": True,
            "all_model_hashes_unchanged": True,
            "historical_signatures_reproduced": True,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "slot5_release_approved": False,
            "next_required_gate": "另行审批是否释放Slot 5的Day26与Day27离线复核；本记录不得自动执行任何下游任务。",
        },
        "permissions": dict(config["permissions"]),
        "review_record_generated": True,
        "day63_rerun_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    expected = "SLOT_04_BOUNDARY_BATCH_RESULT_REVIEW_PASSED_WAITING_FOR_SLOT_05_RELEASE_APPROVAL"
    checks = (
        record["decision_status"] == expected,
        record["cp09_review"]["task_review_status"] == "PASS",
        record["cp09_review"]["case_count"] == 9,
        record["cp09_review"]["acceptance_pass_count"] == 7,
        record["decision"]["slot5_release_approved"] is False,
    )
    if not all(checks):
        raise ValueError("The Day 64 CP09 record is invalid.")
    false_fields = (
        "day63_rerun_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "continuous_tolerance_claimed",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 64 record contains an unsupported action or claim.")


def build_markdown(record):
    review = record["cp09_review"]
    rows = "\n".join(
        f"- `{audit['case_id']}` `{audit['offset_mm']:+.3f} mm`："
        + ("PASS" if audit["acceptance_pass"] else f"FAIL（{audit['failed_metrics']}）")
        for audit in review["case_audits"]
    )
    return f"""# Day64 CP09 Slot 4 九点边界批次审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 4批次任务审核：`PASS`
- 光学案例执行：`9/9`成功
- 均衡验收覆盖：`{review['acceptance_pass_count']}/9`
- Slot 5已释放：`False`

## 案例验收签名

{rows}

## 回归与文件证据

- 最大Spot差值：`{review['maximum_spot_reproduction_difference_um']:.9f} um`
- 最大MTF差值：`{review['maximum_mtf_reproduction_difference']:.9f}`
- 案例JSON：`9`
- 原始Spot文本：`9`
- 原始MTF文本：`9`
- 所有连接关闭：`True`
- 所有模型与工作副本指纹不变：`True`

## 重要区别

任务审核PASS表示自动化、文件和回归证据完整；7/9表示在冻结教学阈值下有两个实测点不通过。两者不能混为一谈。

## 下一道门

{record['decision']['next_required_gate']}

本记录不声明连续容差，也不批准工程变更。
"""


def main():
    config = load_config("configs/day64_cp09_slot4_boundary_batch_review.yaml")
    review = prepare_review(config)
    record = build_record(config, review)
    validate_record(record)
    frozen_paths = (
        review["result_path"],
        review["marker_path"],
        review["approval_path"],
        review["model_path"],
        review["historical_path"],
        review["csv_path"],
        *[Path(audit["case_report_path"]) for audit in review["case_audits"]],
        *[Path(audit["spot_raw_path"]) for audit in review["case_audits"]],
        *[Path(audit["mtf_raw_path"]) for audit in review["case_audits"]],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 64 input changed during review generation: {path}")

    print("========== DAY 64 CP09 SLOT-4 BOUNDARY-BATCH REVIEW RECORD ==========")
    print("No ZOS-API connection, optical calculation, rerun or Slot 5 release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 4 boundary-batch task review: PASS")
    print("Cases / case reports / raw Spot / raw MTF: 9 / 9 / 9 / 9")
    print("Balanced acceptance coverage: 7/9")
    print(f"Maximum historical Spot difference: {record['cp09_review']['maximum_spot_reproduction_difference_um']:.9f} um")
    print(f"Maximum historical MTF difference: {record['cp09_review']['maximum_mtf_reproduction_difference']:.9f}")
    print("Slot 5 release approved: False")
    print()
    print("[PASS] Day63 execution, consumption marker and Day62 approval verified")
    print("[PASS] Nine case reports and eighteen raw analysis files verified")
    print("[PASS] Historical optical metrics and acceptance signatures reproduced")
    print("[PASS] Task-review PASS remains separate from 7/9 acceptance coverage")
    print("[PASS] Day63 was not rerun and no new ZOS-API connection was created")
    print("[PASS] No downstream slot, continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
