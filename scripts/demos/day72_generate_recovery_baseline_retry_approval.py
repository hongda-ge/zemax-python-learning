"""Day 72 step 2: generate the one-attempt recovery retry approval."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day72_recovery_baseline_retry_approval_plan import prepare_plan, sha256_file  # noqa: E402


def source_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, plan):
    source = config["source"]
    contract = dict(plan["contract"])
    contract["approved_output_root"] = str((PROJECT_ROOT / contract["approved_output_root"]).resolve())
    return {
        "task": "day72_recovery_baseline_retry_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day71_review": source_record(plan["review_path"], source["day71_review_sha256"]),
        "source_day70_failure": source_record(plan["failure_path"], source["day70_failure_sha256"]),
        "original_authorization_consumption": {
            **source_record(plan["marker_path"], source["original_authorization_marker_sha256"]),
            "consumed_once": True,
            "reusable": False,
        },
        "day70_config": source_record(plan["day70_path"], source["day70_config_sha256"]),
        "focused_model": source_record(plan["model_path"], source["focused_model_sha256"]),
        "historical_zero_control": source_record(plan["historical_path"], source["historical_zero_control_sha256"]),
        "approved_execution_contract": contract,
        "license_state_at_approval": {
            "operator_gui_recovery_observed": True,
            "standalone_zosapi_license_reverified": False,
            "day73_retry_is_the_authorized_api_verification_attempt": True,
        },
        "decision": {
            "approved_capabilities": list(config["decision"]["approved_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "Day73只可执行一次新零偏移重试；无论成功或再次失败，均须停在CP09接受人工审核。",
        },
        "permissions": dict(config["permissions"]),
        "approval_record_generated": True,
        "approved_retry_executed_by_day72": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "seven_recovery_cases_released": False,
        "day27_recalculated": False,
        "slot6_released": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    contract = record["approved_execution_contract"]
    return f"""# Day72 Day27 零偏移控制重试审批

## 审批结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 范围：`{contract['recovery_stage']}` / `{contract['approved_case_id']}` / 一次尝试
- 专用入口：`{contract['required_entrypoint']}`

## 为什么必须是新审批

Day69授权已在Day70连接前消费，不可复用。Day71仅确认失败安全并允许申请重试，因此本记录以新的决策编号和新输出边界签发一次重试权限。

## 获准内容

Day73可以创建一个隔离工作副本并尝试建立一个Standalone ZOS-API连接。连接成功后，仅可导出一次Standard Spot和一次FFT MTF；连接再次失败时必须写入失败证据并立即停止。

## 仍然禁止

- 重用Day69授权或进行第二次重试；
- 执行七个证据恢复点；
- Quick Focus、优化或SaveAs；
- 重算Day27或释放Slot 6；
- 在Day73成功前声称许可证已经恢复。

## 下一道门

Day73无论成功或失败，都必须停在CP09接受人工审核。七点恢复批次仍需单独审批。
"""


def main():
    config = load_config("configs/day72_recovery_baseline_retry_approval.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    frozen_paths = (
        plan["review_path"], plan["failure_path"], plan["marker_path"],
        plan["day70_path"], plan["model_path"], plan["historical_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(record), encoding="utf-8")
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 72 input changed during approval generation: {path}")

    print("========== DAY 72 RECOVERY-BASELINE RETRY APPROVAL RECORD ==========")
    print("No retry execution, ZOS-API connection, optical analysis or source modification was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Approved scope: Day27 recovery stage 01 / zero offset / retry 01 / one attempt")
    print(f"Focused model SHA256: {record['focused_model']['sha256']}")
    print(f"Required entrypoint: {record['approved_execution_contract']['required_entrypoint']}")
    print("Original Day69 authorization consumed/reusable: True/False")
    print("Standalone ZOS-API license reverified by Day72: False")
    print("One new retry attempt released: True")
    print("Approved retry executed by Day72: False")
    print("Seven-point recovery batch, Day27 recalculation and Slot 6 released: False")
    print()
    print("[PASS] Approval bound to frozen Day71 review and Day70 failure evidence")
    print("[PASS] Original consumed authorization remains non-reusable")
    print("[PASS] Exactly one new zero-offset connection attempt released")
    print("[PASS] Dedicated Day73 entrypoint and isolated output root frozen")
    print("[PASS] Day72 performed no ZOS-API connection or optical analysis")
    print("[PASS] Success and failure paths both retain the CP09 stop")
    print(f"[PASS] JSON approval record: {json_path}")
    print(f"[PASS] Markdown approval record: {markdown_path}")


if __name__ == "__main__":
    main()
