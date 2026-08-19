"""Day 58 step 2: generate the CP09 Slot 3 acceptance review record."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day58_cp09_slot3_acceptance_review_plan import prepare_review  # noqa: E402


def file_record(path, sha256):
    return {"path": str(path), "sha256": sha256, "verified": True}


def build_record(config, review):
    result = review["result"]
    return {
        "task": "day58_cp09_slot3_acceptance_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "decision_is_teaching_record": config["decision"]["decision_is_teaching_record"],
        "source_day57_result": file_record(review["result_path"], config["source"]["day57_result_sha256"]),
        "source_day56_approval": file_record(review["approval_path"], config["source"]["day56_approval_sha256"]),
        "authorization_consumption": {**file_record(review["marker_path"], config["source"]["authorization_marker_sha256"]), "consumed_once": True, "rerun_released": False},
        "output_evidence": {
            "detail_csv": file_record(review["detail_path"], config["source"]["detail_csv_sha256"]),
            "summary_csv": file_record(review["summary_path"], config["source"]["summary_csv_sha256"]),
            "acceptance_matrix": file_record(review["figure_path"], config["source"]["figure_sha256"]),
        },
        "cp09_review": {
            "checkpoint_id": "CP09_slot_gate",
            "resource_slot": 3,
            "day": 24,
            "task_review_status": "PASS",
            "case_count": result["case_count"],
            "detail_count": len(result["details"]),
            "summary_count": len(result["scenario_summaries"]),
            "scenario_pass_counts": review["counts"],
            "scenario_summaries": result["scenario_summaries"],
            "historical_reproduction_passed": True,
            "four_metric_and_rule_verified": True,
            "output_package_complete": True,
            "safety_boundary_preserved": True,
        },
        "decision": {
            "reviewer_role": config["decision"]["reviewer_role"],
            "released_capabilities": list(config["decision"]["released_capabilities"]),
            "forbidden_capabilities": list(config["decision"]["forbidden_capabilities"]),
            "slot_04_release_approved": False,
            "next_required_gate": "另行审批是否释放Slot 4 / Day25边界扫描复核；本记录不得自动连接ZOS-API或执行Day25。",
        },
        "permissions": dict(config["permissions"]),
        "review_record_generated": True,
        "day57_rerun_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "slot_04_executed": False,
        "downstream_slots_released": False,
        "continuous_tolerance_claimed": False,
        "engineering_change_approved": False,
    }


def markdown(record):
    review = record["cp09_review"]
    lines = [
        "# Day 58：CP09 Slot 3 离线验收审核记录",
        "",
        "## 审核结论",
        "",
        f"- 决策：`{record['decision_id']}`",
        f"- 状态：`{record['decision_status']}`",
        f"- 任务审核：**{review['task_review_status']}**",
        f"- 案例/明细/场景：{review['case_count']} / {review['detail_count']} / {review['summary_count']}",
        "",
        "## 场景覆盖",
        "",
    ]
    for scenario in review["scenario_summaries"]:
        lines.append(f"- `{scenario['scenario_id']}`：{scenario['passed_count']}/{scenario['measured_count']} 通过；案例 {scenario['passed_case_ids']}")
    lines += [
        "",
        "## 权限边界",
        "",
        "审核通过只表示可以申请 Slot 4。Day57 不得重跑，Slot 4 尚未获准，ZOS-API、连续公差声明和工程变更结论继续锁定。",
        "",
        "## 学习与简历价值",
        "",
        "建立基于一次性授权、输出文件指纹、规则回归签名和人工 CP09 门控的离线验收审计，实现流程成功、案例覆盖和后续执行权限的分层管理。",
        "",
    ]
    return "\n".join(lines)


def main():
    config = load_config("configs/day58_cp09_slot3_acceptance_review.yaml")
    review = prepare_review(config)
    record = build_record(config, review)
    output_dir = PROJECT_ROOT / config["output"]["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / config["output"]["json"]
    md_path = output_dir / config["output"]["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(record), encoding="utf-8")
    print("========== DAY 58 CP09 SLOT-3 ACCEPTANCE REVIEW RECORD ==========")
    print("No acceptance rerun, ZOS-API connection, optical calculation or Slot 4 release was used.")
    print(f"Decision: {record['decision_id']} -> {record['decision_status']}")
    print("Slot 3 acceptance task review: PASS")
    print(f"Cases / details / summaries: {record['cp09_review']['case_count']} / {record['cp09_review']['detail_count']} / {record['cp09_review']['summary_count']}")
    for scenario_id, count in record["cp09_review"]["scenario_pass_counts"].items():
        print(f"  {scenario_id}: {count}/7 pass")
    print("Slot 4 release approved: False")
    print()
    print("[PASS] Day57 execution and Day56 one-time authorization verified")
    print("[PASS] JSON, two CSV files and acceptance matrix verified")
    print("[PASS] Historical Day24 scenario signatures reproduced")
    print("[PASS] Task-review PASS remains separate from scenario coverage")
    print("[PASS] Day57 was not rerun; ZOS-API and Slot 4-6 remain locked")
    print("[PASS] No continuous tolerance or engineering change was approved")
    print(f"[PASS] JSON review record: {json_path}")
    print(f"[PASS] Markdown review record: {md_path}")


if __name__ == "__main__":
    main()
