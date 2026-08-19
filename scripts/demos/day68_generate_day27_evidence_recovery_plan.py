"""Day 68 step 2: generate the formal Day 27 evidence-recovery plan."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day68_day27_evidence_recovery_plan import (  # noqa: E402
    prepare_plan,
    sha256_file,
)


def write_case_csv(path, rows):
    flat = []
    for row in rows:
        item = dict(row)
        item["required_by_candidates"] = ";".join(row["required_by_candidates"])
        flat.append(item)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def source_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, plan):
    source = config["source"]
    return {
        "task": "day68_day27_evidence_recovery_plan_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day67_review": source_record(plan["review_path"], source["day67_review_sha256"]),
        "source_day27_evidence_audit": source_record(plan["audit_path"], source["day27_evidence_audit_sha256"]),
        "source_day25_measured_report": source_record(plan["measured_path"], source["day25_measured_report_sha256"]),
        "source_day25_config": source_record(plan["config_path"], source["day25_config_sha256"]),
        "focused_model": source_record(plan["model_path"], source["focused_model_sha256"]),
        "recent_zero_control": source_record(plan["control_path"], source["recent_zero_control_sha256"]),
        "positioning_uncertainty_mm": float(config["recovery_scope"]["positioning_uncertainty_mm"]),
        "reference_image_distance_mm": float(config["recovery_scope"]["reference_image_distance_mm"]),
        "recovery_case_count": len(plan["cases"]),
        "recovery_cases": plan["cases"],
        "minimal_sufficient_set_verified": True,
        "staged_recovery": list(config["staged_recovery"]),
        "analysis_contract": dict(config["analysis_contract"]),
        "planned_workload_if_all_future_stages_are_approved": dict(config["planned_workload_if_all_future_stages_are_approved"]),
        "decision": {
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "next_required_gate": "另行审批一次零偏移控制；Day68本身不允许连接ZOS-API或执行任何恢复案例。",
        },
        "permissions": dict(config["permissions"]),
        "plan_record_generated": True,
        "new_zosapi_connection_created": False,
        "model_copy_created": False,
        "new_optical_metric_calculated": False,
        "recovery_case_executed": False,
        "interpolation_used": False,
        "existing_source_modified": False,
        "slot6_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    rows = "\n".join(
        f"- `{row['case_id']}`：`{row['offset_mm']:+.3f} mm`，像面 `{row['target_image_distance_mm']:.10f} mm`，服务 `{', '.join(row['required_by_candidates'])}`"
        for row in record["recovery_cases"]
    )
    return f"""# Day68 Day27 证据恢复计划

## 计划结论

- 决策：`{record['decision_id']}`
- 状态：`{record['decision_status']}`
- 新测量点：`{record['recovery_case_count']}`
- 当前执行权限：`False`
- Slot 6已释放：`False`

## 最小充分七点集

{rows}

七个点均未出现在现有16点证据中，且每个点都至少对应一个命令包络的缺失端点。若要完整复核四个命令候选，不能删除其中任何一点。

## 四阶段恢复路线

1. 零偏移控制：复现Spot和FFT MTF，完成后停在CP09；
2. 七点批次：逐点独立副本、独立连接、串行执行，完成后停在CP09；
3. Day27离线重算：合并23个精确测量点，重新应用三状态AND规则；
4. Slot 6释放审核：只有Day27科学复核完成后才重新评估。

## 计划工作量

- ZOS-API连接：`8`
- 独立工作副本：`8`
- Standard Spot：`8`
- FFT MTF：`8`
- Quick Focus：`0`

这些数字是未来分阶段全部获批时的计划量，不代表Day68已经执行或批准。

## 安全边界

不允许插值、Quick Focus、优化、SaveAs、源文件修改、连续公差声明或自动释放Slot 6。
"""


def main():
    config = load_config("configs/day68_day27_evidence_recovery_plan.yaml")
    plan = prepare_plan(config)
    record = build_record(config, plan)
    frozen_paths = (plan["review_path"], plan["audit_path"], plan["measured_path"], plan["control_path"], plan["config_path"], plan["model_path"])
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("plan_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / config["output"]["case_csv"]
    json_path = output_dir / config["output"]["json"]
    markdown_path = output_dir / config["output"]["markdown"]
    write_case_csv(csv_path, plan["cases"])
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(record), encoding="utf-8")
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 68 input changed during plan generation: {path}")

    print("========== DAY 68 DAY27 EVIDENCE-RECOVERY PLAN RECORD ==========")
    print("No ZOS-API connection, model copy, optical analysis or recovery execution was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print(f"Recovery cases: {record['recovery_case_count']}")
    for row in record["recovery_cases"]:
        print(f"  {row['case_id']}: offset={row['offset_mm']:+.3f} mm, image={row['target_image_distance_mm']:.10f} mm, required_by={row['required_by_candidates']}")
    print("Future staged workload: 8 connections / 8 copies / 8 Spot / 8 FFT MTF / 0 Quick Focus")
    print("Zero-control execution released: False")
    print("Seven-point batch released: False")
    print("Day27 recalculation released: False")
    print("Slot 6 released: False")
    print()
    print("[PASS] Day67 review and Day66 evidence gap verified")
    print("[PASS] Seven-point set is unique, unmeasured and minimally sufficient")
    print("[PASS] Focused model, analysis recipe and recent zero control verified")
    print("[PASS] Four recovery stages retain separate approval gates")
    print("[PASS] Day68 performed no ZOS-API connection or optical calculation")
    print("[PASS] Interpolation, source modification and downstream release remain locked")
    print(f"[PASS] Case-plan CSV: {csv_path}")
    print(f"[PASS] Recovery-plan JSON: {json_path}")
    print(f"[PASS] Recovery-plan Markdown: {markdown_path}")


if __name__ == "__main__":
    main()
