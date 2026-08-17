"""Day 45 step 2: generate the isolated Day 22 candidate and pre-execution manifest."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day45_isolated_day22_candidate_plan import (  # noqa: E402
    build_preview,
    load_approval,
    semantic_differences,
    sha256_file,
    validate_candidate_policy,
    validate_change_boundary,
    validate_execution_boundaries,
    validate_official_source,
)


def sha256_text(text):
    """Calculate the uppercase SHA256 of UTF-8 candidate text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def resolve_output_dir(config, approval):
    """Create a timestamped directory strictly inside the approved candidate root."""

    approved_root = (PROJECT_ROOT / approval["candidate_boundary"]["root"]).resolve()
    configured_root = (PROJECT_ROOT / config["outputs"]["root_from_approval"]).resolve()
    if configured_root != approved_root:
        raise ValueError("The Day 45 candidate root differs from Day 44 approval.")
    stamp = datetime.now().astimezone().strftime(
        config["outputs"]["directory_prefix"] + "_%Y%m%d_%H%M%S"
    )
    output_dir = (approved_root / stamp).resolve()
    if output_dir.parent != approved_root:
        raise ValueError("The Day 45 output directory escaped the approved root.")
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def build_manifest(config, approval_path, official_path, candidate_path, preview, candidate_sha256):
    """Build a frozen pre-execution manifest for later manual approval."""

    change = config["change"]
    return {
        "task": "day45_isolated_day22_candidate_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day44_approval": {
            "path": str(approval_path),
            "sha256": config["source"]["day44_approval_sha256"],
            "decision_status": config["source"]["expected_decision_status"],
            "verified": True,
        },
        "official_source": {
            "path": str(official_path),
            "sha256": config["source"]["official_day22_sha256"],
            "modified": False,
        },
        "candidate": {
            "path": str(candidate_path),
            "sha256": candidate_sha256,
            "official_baseline": False,
            "isolated_under_outputs": True,
        },
        "declared_change": {
            "field": change["canonical_field"],
            "source_value": float(change["current_value"]),
            "candidate_value": float(change["proposed_value"]),
            "unit": change["unit"],
            "changed_source_line": int(preview["changed_line"]),
            "text_line_replacement_count": 1,
            "semantic_difference_count": len(preview["semantic_differences"]),
            "semantic_differences": preview["semantic_differences"],
        },
        "authorization": {
            "candidate_preparation_released": True,
            "candidate_fingerprint_generation_released": True,
            "pre_execution_manifest_generation_released": True,
            "source_modification_released": False,
            "slot_01_execution_released": False,
            "zosapi_execution_released": False,
            "optical_calculation_released": False,
            "downstream_slots_released": False,
        },
        "candidate_prepared": True,
        "candidate_file_written": True,
        "manifest_generated": True,
        "review_task_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
        "next_required_gate": "人工核对候选单字段差异和SHA256后，另行决定是否释放Slot 1离线复核。",
    }


def validate_written_candidate(config, official_path, candidate_path, manifest):
    """Reopen the candidate and prove the on-disk semantic difference is still unique."""

    if candidate_path.resolve() == official_path.resolve():
        raise ValueError("The Day 45 candidate path equals the official source path.")
    if not candidate_path.is_file():
        raise ValueError("The Day 45 candidate file was not written.")
    source_document = yaml.safe_load(official_path.read_text(encoding="utf-8"))
    candidate_document = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    differences = semantic_differences(source_document, candidate_document)
    expected_field = config["change"]["canonical_field"]
    if len(differences) != 1 or differences[0]["path"] != expected_field:
        raise ValueError("The written candidate contains an undeclared semantic difference.")
    if sha256_file(candidate_path) != manifest["candidate"]["sha256"]:
        raise ValueError("The written candidate SHA256 differs from the manifest.")
    if manifest["official_source"]["modified"] is not False:
        raise ValueError("The manifest incorrectly marks the official source as modified.")
    authorization = manifest["authorization"]
    locked = (
        "source_modification_released",
        "slot_01_execution_released",
        "zosapi_execution_released",
        "optical_calculation_released",
        "downstream_slots_released",
    )
    if any(authorization[key] is not False for key in locked):
        raise ValueError("The Day 45 manifest unexpectedly released execution.")
    false_fields = (
        "review_task_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "downstream_slots_released",
        "engineering_change_approved",
    )
    if any(manifest[key] is not False for key in false_fields):
        raise ValueError("The Day 45 manifest contains an unsupported action or claim.")


def build_markdown(manifest):
    """Render a human-readable candidate review sheet."""

    change = manifest["declared_change"]
    auth_lines = "\n".join(
        f"- `{key}`：`{value}`" for key, value in manifest["authorization"].items()
    )
    return f"""# Day45 Day22 隔离候选审核单

## 候选身份

- 正式来源：`{manifest['official_source']['path']}`
- 来源 SHA256：`{manifest['official_source']['sha256']}`
- 候选文件：`{manifest['candidate']['path']}`
- 候选 SHA256：`{manifest['candidate']['sha256']}`
- 候选是正式基线：`{manifest['candidate']['official_baseline']}`

## 唯一声明变化

- 字段：`{change['field']}`
- 数值：`{change['source_value']:.3f} -> {change['candidate_value']:.3f} {change['unit']}`
- 来源行号：`{change['changed_source_line']}`
- 文本替换行数：`{change['text_line_replacement_count']}`
- YAML 语义差异数：`{change['semantic_difference_count']}`

## 权限矩阵

{auth_lines}

## 当前状态

- 候选已准备：`{manifest['candidate_prepared']}`
- 候选文件已写入：`{manifest['candidate_file_written']}`
- Day22 复核已执行：`{manifest['review_task_executed']}`
- 正式来源已修改：`{manifest['existing_source_modified']}`
- 工程变化已批准：`{manifest['engineering_change_approved']}`

## 下一道人工门

{manifest['next_required_gate']}

本候选不能由原 Day22 脚本直接运行，除非后续步骤提供明确的候选输入接口并获得单独执行批准。
"""


def main():
    config = load_config("configs/day45_isolated_day22_candidate.yaml")
    validate_execution_boundaries(config)
    validate_candidate_policy(config)
    approval_path, approval = load_approval(config)
    official_path = validate_official_source(config, approval)
    validate_change_boundary(config, approval)
    preview = build_preview(config, approval_path, official_path)

    official_hash_before = sha256_file(official_path)
    approval_hash_before = sha256_file(approval_path)
    output_dir = resolve_output_dir(config, approval)
    candidate_path = output_dir / config["outputs"]["candidate_yaml"]
    manifest_path = output_dir / config["outputs"]["manifest_json"]
    markdown_path = output_dir / config["outputs"]["review_markdown"]
    candidate_sha256 = sha256_text(preview["candidate_text"])
    # 直接写入 UTF-8 字节，避免 Windows 自动转换换行符后造成候选 SHA256 不一致。
    candidate_path.write_bytes(preview["candidate_text"].encode("utf-8"))
    manifest = build_manifest(
        config, approval_path, official_path, candidate_path, preview, candidate_sha256
    )
    validate_written_candidate(config, official_path, candidate_path, manifest)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(manifest), encoding="utf-8")

    if sha256_file(official_path) != official_hash_before:
        raise ValueError("The official Day 22 config changed during candidate generation.")
    if sha256_file(approval_path) != approval_hash_before:
        raise ValueError("The Day 44 approval changed during candidate generation.")

    print("========== DAY 45 ISOLATED DAY22 CANDIDATE ==========")
    print("No Day22 review calculation, ZOS-API connection or official-source modification was used.")
    print(f"Official source: {official_path}")
    print(f"Official SHA256: {official_hash_before}")
    print(f"Candidate file: {candidate_path}")
    print(f"Candidate SHA256: {candidate_sha256}")
    print(
        "Declared change: "
        f"{config['change']['canonical_field']} "
        f"{float(config['change']['current_value']):.3f} -> "
        f"{float(config['change']['proposed_value']):.3f} mm"
    )
    print()
    print("[PASS] Candidate created only under the approved outputs root")
    print("[PASS] Exactly one text line and one semantic field changed")
    print("[PASS] Source and candidate SHA256 fingerprints recorded")
    print("[PASS] Official Day 22 config remained unchanged")
    print("[PASS] Slot 1 execution, ZOS-API and downstream slots remain locked")
    print("[PASS] No Day22 result or engineering-change claim was produced")
    print(f"[PASS] Pre-execution manifest: {manifest_path}")
    print(f"[PASS] Candidate review sheet: {markdown_path}")


if __name__ == "__main__":
    main()
