"""Day 46 step 2: generate the formal candidate pre-execution review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day46_candidate_pre_execution_review_plan import (  # noqa: E402
    build_plan,
    load_frozen_json,
    sha256_file,
    validate_day44_approval,
    validate_decision,
    validate_execution_lock,
    validate_files_and_manifest,
)


def build_record(config, plan):
    """Build a review record that proves eligibility without releasing execution."""

    difference = plan["semantic_differences"][0]
    return {
        "task": "day46_candidate_pre_execution_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": plan["decision_id"],
        "decision_status": plan["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day44_approval": {
            "path": plan["source_day44_approval"],
            "sha256": config["source"]["day44_approval_sha256"],
            "verified": True,
        },
        "source_day45_manifest": {
            "path": plan["source_day45_manifest"],
            "sha256": config["source"]["day45_manifest_sha256"],
            "verified": True,
        },
        "official_source": {
            "path": plan["official_path"],
            "sha256": plan["official_sha256"],
            "modified": False,
        },
        "candidate": {
            "path": plan["candidate_path"],
            "sha256": plan["candidate_sha256"],
            "official_baseline": False,
            "identity_verified": True,
        },
        "verified_change": {
            "field": difference["path"],
            "source_value": float(difference["source"]),
            "candidate_value": float(difference["candidate"]),
            "unit": config["review_boundary"]["unit"],
            "semantic_difference_count": len(plan["semantic_differences"]),
        },
        "review_scope": plan["scope"],
        "review_decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": plan["released_capabilities"],
            "forbidden_capabilities": plan["forbidden_capabilities"],
            "candidate_eligible_for_execution_approval_request": True,
            "slot_01_execution_approved": False,
            "next_required_gate": "另行人工审批是否允许使用该候选执行Slot 1的Day22离线复核。",
        },
        "permissions": plan["permissions"],
        "review_record_generated": True,
        "candidate_review_completed": True,
        "review_task_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
    }


def validate_record(record):
    """Recheck the decision boundary and all retained locks."""

    if record["decision_status"] != "CANDIDATE_VERIFIED_WAITING_FOR_SLOT_01_EXECUTION_APPROVAL":
        raise ValueError("The Day 46 record has an incorrect decision status.")
    if record["review_scope"] != {
        "resource_slot": 1,
        "day": 22,
        "execution_class": "offline_only",
    }:
        raise ValueError("The Day 46 record exceeds Slot 1 / Day 22.")
    if record["verified_change"]["semantic_difference_count"] != 1:
        raise ValueError("The Day 46 record does not contain one semantic difference.")
    if record["review_decision"]["candidate_eligible_for_execution_approval_request"] is not True:
        raise ValueError("The Day 46 candidate was not marked eligible for an approval request.")
    if record["review_decision"]["slot_01_execution_approved"] is not False:
        raise ValueError("Day 46 incorrectly approved Slot 1 execution.")
    locked_permissions = (
        "source_modification_released",
        "slot_01_execution_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "downstream_slots_released",
    )
    if any(record["permissions"][key] is not False for key in locked_permissions):
        raise ValueError("The Day 46 record unexpectedly released execution.")
    false_fields = (
        "review_task_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(record[key] is not False for key in false_fields):
        raise ValueError("The Day 46 record contains an unsupported action or claim.")


def build_markdown(record):
    """Render a human-readable candidate review record."""

    change = record["verified_change"]
    forbidden = "\n".join(
        f"- `{item}`" for item in record["review_decision"]["forbidden_capabilities"]
    )
    return f"""# Day46 候选执行前审核记录

## 审核结论

- 决策编号：`{record['decision_id']}`
- 决策状态：`{record['decision_status']}`
- 候选可提交执行审批申请：`True`
- Slot 1 已获准执行：`False`

本记录证明候选身份和差异已经通过审核，但不批准运行 Day22。

## 双指纹

- 正式配置：`{record['official_source']['path']}`
- 正式 SHA256：`{record['official_source']['sha256']}`
- 候选配置：`{record['candidate']['path']}`
- 候选 SHA256：`{record['candidate']['sha256']}`

## 唯一差异

- 字段：`{change['field']}`
- 数值：`{change['source_value']:.3f} -> {change['candidate_value']:.3f} {change['unit']}`
- YAML 语义差异数：`{change['semantic_difference_count']}`

## 仍禁止能力

{forbidden}

## 下一道人工门

{record['review_decision']['next_required_gate']}

审核通过只表示候选具备申请执行许可的资格，不表示执行已经获得批准。
"""


def main():
    config = load_config("configs/day46_candidate_pre_execution_review.yaml")
    validate_execution_lock(config)
    validate_decision(config)
    source = config["source"]
    approval_path, approval = load_frozen_json(
        config, "day44_approval_record", "day44_approval_sha256", source["expected_day44_task"]
    )
    manifest_path, manifest = load_frozen_json(
        config, "day45_manifest", "day45_manifest_sha256", source["expected_day45_task"]
    )
    approved_root = validate_day44_approval(config, approval)
    official_path, candidate_path, differences = validate_files_and_manifest(
        config, manifest, approved_root
    )
    plan = build_plan(
        config, approval_path, manifest_path, official_path, candidate_path, differences
    )
    record = build_record(config, plan)
    validate_record(record)

    frozen_hashes = {
        approval_path: sha256_file(approval_path),
        manifest_path: sha256_file(manifest_path),
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
            raise ValueError(f"A frozen Day 46 input changed during review generation: {path}")

    print("========== DAY 46 CANDIDATE PRE-EXECUTION REVIEW RECORD ==========")
    print("No source modification, Day22 calculation, ZOS-API connection or review execution was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Scope: Slot 1 / Day 22 / offline_only")
    print(f"Official SHA256: {record['official_source']['sha256']}")
    print(f"Candidate SHA256: {record['candidate']['sha256']}")
    print("Candidate eligible for execution-approval request: True")
    print("Slot 1 execution approved: False")
    print()
    print("[PASS] Day 44 approval, Day 45 manifest and both file fingerprints verified")
    print("[PASS] Exactly one declared semantic difference independently verified")
    print("[PASS] Candidate review completed without running Day 22")
    print("[PASS] Official config and candidate remained unchanged")
    print("[PASS] Slot 1 execution, ZOS-API and Slot 2-6 remain locked")
    print("[PASS] No engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {markdown_path}")


if __name__ == "__main__":
    main()
