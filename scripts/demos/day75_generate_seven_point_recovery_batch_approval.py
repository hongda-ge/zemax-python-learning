"""Generate the offline Day 75 one-shot seven-point batch approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.day75_seven_point_recovery_batch_approval_plan import (  # noqa: E402
    CONFIG_PATH,
    sha256_file,
    validate_plan,
)


APPROVED_DRAFT_SHA256 = "6003E5DDFAEECBE69F26D543F2933B82AE2466418A1649288499B302FFA12338"


def build_record(config, paths):
    contract = dict(config["proposed_execution_contract"])
    contract["approved_output_root"] = str(
        (PROJECT_ROOT / contract["approved_output_root"]).resolve()
    )
    return {
        "task": "day75_seven_point_recovery_batch_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["proposed_status"],
        "approval_scope": "one_seven_point_recovery_batch",
        "approval_draft": {
            "path": str(CONFIG_PATH),
            "sha256": APPROVED_DRAFT_SHA256,
            "manually_confirmed_by": "project_owner",
            "reusable": False,
        },
        "frozen_sources": {
            key: {"path": str(path), "sha256": config["source"][key + "_sha256"], "verified": True}
            for key, path in paths.items()
        },
        "approved_cases": list(config["approved_cases"]),
        "execution_contract": contract,
        "permissions": {
            "seven_point_batch_execution_released": True,
            "one_batch_execution_released": True,
            "seven_case_execution_released": True,
            "sequential_zosapi_execution_released": True,
            "standard_spot_and_fft_mtf_released": True,
            "zero_control_rerun_released": False,
            "additional_retry_released": False,
            "quick_focus_released": False,
            "optimization_released": False,
            "save_as_released": False,
            "day27_recalculation_released": False,
            "slot6_released": False,
            "source_modification_released": False,
            "engineering_change_released": False,
        },
        "approval_record_generated": True,
        "batch_executed_by_day75": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "model_copy_created": False,
        "next_gate": "A dedicated Day76 entrypoint may consume this approval once, execute seven cases, and must stop at CP09_recovery_batch_gate.",
    }


def validate_record(record):
    checks = (
        record["status"] == "success",
        record["decision_status"] == "DAY27_SEVEN_POINT_RECOVERY_BATCH_APPROVED_FOR_ONE_EXECUTION",
        len(record["approved_cases"]) == 7,
        record["permissions"]["seven_point_batch_execution_released"] is True,
        record["permissions"]["day27_recalculation_released"] is False,
        record["permissions"]["slot6_released"] is False,
        record["batch_executed_by_day75"] is False,
        record["new_zosapi_connection_created"] is False,
        record["new_optical_metric_calculated"] is False,
        record["model_copy_created"] is False,
    )
    if not all(checks):
        raise RuntimeError("Generated Day75 approval record is unsafe or incomplete.")


def build_markdown(record):
    cases = "\n".join(
        "- `{0}`: `{1:+.3f} mm` → `{2:.15f} mm`".format(
            case["case_id"], float(case["offset_mm"]), float(case["target_image_distance_mm"])
        )
        for case in record["approved_cases"]
    )
    return """# Day 75 七点恢复批次正式审批

## 审批结论

- 决策：`{decision_id}`
- 状态：`{decision_status}`
- 范围：一次批次、七个非零恢复点
- 本日连接 ZOS-API：`False`
- 本日执行光学分析：`False`

## 获批案例

{cases}

## 执行契约

- 专用入口：`{entrypoint}`
- 严格串行，同时最多一个 Standalone 连接
- 每案例独立工作副本、Standard Spot、FFT MTF
- 执行异常立即停止；教学验收 FAIL 仅记录
- 禁止零偏移重跑、Quick Focus、优化和 SaveAs
- 批次后停止在：`{gate}`

## 仍然锁定

Day 27 重算、Slot 6、额外重试、源模型修改和工程变更均未释放。
""".format(
        decision_id=record["decision_id"],
        decision_status=record["decision_status"],
        cases=cases,
        entrypoint=record["execution_contract"]["required_entrypoint"],
        gate=record["execution_contract"]["post_execution_gate"],
    )


def main():
    if sha256_file(CONFIG_PATH) != APPROVED_DRAFT_SHA256:
        raise RuntimeError("The manually approved Day75 draft hash changed.")
    config, paths, _ = validate_plan()
    before = {path: sha256_file(path) for path in paths.values()}
    record = build_record(config, paths)
    validate_record(record)
    names = config["output"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    if any(sha256_file(path) != digest for path, digest in before.items()):
        raise RuntimeError("A frozen Day75 input changed during approval generation.")
    print("========== DAY 75 FORMAL APPROVAL GENERATED ==========")
    print("Decision: {0} -> {1}".format(record["decision_id"], record["decision_status"]))
    print("Cases approved: 7; batch count approved: 1")
    print("ZOS-API connection created: False")
    print("Batch executed by Day75: False")
    print("Day27 recalculation released: False")
    print("Slot6 released: False")
    print("JSON: {0}".format(json_path))
    print("Markdown: {0}".format(markdown_path))


if __name__ == "__main__":
    main()
