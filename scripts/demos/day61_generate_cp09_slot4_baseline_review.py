"""Day 61 step 2: generate the formal CP09 Slot 4 control review."""

import json
import sys
from datetime import datetime


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day61_cp09_slot4_baseline_review_plan import (  # noqa: E402
    prepare_plan,
    sha256_file,
)


def build_record(config, result, plan):
    audit = plan["audit"]
    return {
        "task": "day61_cp09_slot4_baseline_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day60_result": {
            "path": plan["result_path"],
            "sha256": plan["result_sha256"],
            "verified": True,
        },
        "source_day59_approval": {
            "path": plan["approval_path"],
            "sha256": config["source"]["day59_approval_sha256"],
            "verified": True,
        },
        "authorization_consumption": {
            "path": plan["marker_path"],
            "sha256": config["source"]["authorization_marker_sha256"],
            "verified": True,
            "consumed_once": True,
        },
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 4,
            "day": 25,
            "task_review_status": "PASS",
            "case_id": result["case"]["case_id"],
            "offset_mm": float(result["case"]["offset_mm"]),
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
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": plan["released_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "boundary_batch_release_approved": False,
            "next_required_gate": "另行审批是否释放九个边界案例；本审核记录不得自动连接ZOS-API或执行批次。",
        },
        "permissions": plan["permissions"],
        "review_record_generated": True,
        "day60_rerun_performed": False,
        "boundary_cases_executed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    expected = "SLOT_04_BASELINE_RESULT_REVIEW_PASSED_WAITING_FOR_BOUNDARY_BATCH_APPROVAL"
    if record["decision_status"] != expected or record["cp09_review"]["task_review_status"] != "PASS":
        raise ValueError("The Day 61 CP09 decision is invalid.")
    if record["decision"]["boundary_batch_release_approved"] is not False:
        raise ValueError("Day 61 incorrectly released the boundary batch.")
    false_fields = (
        "day60_rerun_performed",
        "boundary_cases_executed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "continuous_tolerance_claimed",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 61 record contains an unsupported action or claim.")


def build_markdown(record):
    review = record["cp09_review"]
    return f"""# Day61 CP09 Slot 4 零偏移控制审核

## 审核结论

- 决策编号：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- Slot 4 控制任务审核：`PASS`
- 已执行案例：`{review['case_id']}`，offset = `{review['offset_mm']:+.3f} mm`
- 九点边界批次已释放：`False`

## 复现与验收证据

- 最大 Spot 差值：`{review['maximum_spot_reproduction_difference_um']:.9f} um`
- 最大 MTF 差值：`{review['maximum_mtf_reproduction_difference']:.9f}`
- 均衡四指标 AND 规则：`PASS`
- Spot 文本 SHA256：`{review['spot_raw_text']['sha256']}`
- FFT MTF 文本 SHA256：`{review['mtf_raw_text']['sha256']}`
- 模型与磁盘工作副本 SHA256：一致
- ZOS-API 连接关闭：`True`

## 权限边界

本记录只允许提出九点边界批次的执行审批申请。它没有释放批次执行、ZOS-API、源文件修改、Slot 5-6、连续容差声明或工程变更权限。

## 下一道门

{record['decision']['next_required_gate']}
"""


def main():
    config = load_config("configs/day61_cp09_slot4_baseline_review.yaml")
    result, plan = prepare_plan(config)
    record = build_record(config, result, plan)
    validate_record(record)
    audit = plan["audit"]
    frozen_paths = (
        Path(plan["result_path"]),
        Path(plan["approval_path"]),
        Path(plan["marker_path"]),
        audit["focused_model"],
        audit["historical_control"],
        audit["working_copy"],
        audit["spot_text"],
        audit["mtf_text"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    root = PROJECT_ROOT / config["output"]["root"]
    stamp = datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 61 input changed during review generation: {path}")

    print("========== DAY 61 CP09 SLOT-4 BASELINE REVIEW RECORD ==========")
    print("No ZOS-API connection, optical calculation, rerun or boundary-batch release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 4 zero-offset control task review: PASS")
    print("Executed case: boundary_control_000 (+0.000 mm)")
    print(
        "Maximum Spot/MTF reproduction difference: "
        f"{record['cp09_review']['maximum_spot_reproduction_difference_um']:.9f} um / "
        f"{record['cp09_review']['maximum_mtf_reproduction_difference']:.9f}"
    )
    print("Balanced four-metric acceptance: PASS")
    print("Nine-case boundary execution approved: False")
    print()
    print("[PASS] Day60 execution, consumption marker and Day59 authorization verified")
    print("[PASS] Raw Spot/MTF evidence and fingerprints verified")
    print("[PASS] Historical reproduction, balanced acceptance and safety boundaries passed")
    print("[PASS] Review PASS remains separate from boundary-batch approval")
    print("[PASS] Day60 was not rerun and no new ZOS-API connection was created")
    print("[PASS] No downstream slot, continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
