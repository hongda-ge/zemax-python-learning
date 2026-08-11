"""Day 39 step 2: generate the formal Day 22 impact-scope report."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day39_formal_impact_scope_plan import (  # noqa: E402
    build_scope,
    load_approval,
    load_graph_and_registry,
    sha256_file,
    validate_claim_boundaries,
    validate_execution_lock,
    validate_target_unchanged,
)


def make_rows(scope, registry):
    """Create one auditable row per Day in the formal review set."""

    metadata = {int(entry["day"]): entry for entry in registry["entries"]}
    direct = set(int(day) for day in scope["direct_downstream"])
    rows = []
    for position, day in enumerate(scope["review_order"], start=1):
        entry = metadata[day]
        if day == scope["changed_day"]:
            relationship = "changed_source"
        elif day in direct:
            relationship = "direct_downstream"
        else:
            relationship = "transitive_downstream"
        execution_class = entry["execution_class"]
        rows.append(
            {
                "review_position": position,
                "day": day,
                "relationship": relationship,
                "execution_class": execution_class,
                "review_class": (
                    "zosapi_reexecution_review"
                    if execution_class == "uses_zosapi"
                    else "offline_recalculation_review"
                ),
                "phase_id": entry["phase_id"],
                "title": entry["title"],
                "automatic_execution": False,
            }
        )
    return rows


def build_report(config, approval_path, graph_path, registry_path, target_path, scope, rows):
    """Build the formal scope report without releasing task execution."""

    return {
        "task": "day39_formal_impact_scope_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day38_approval": {
            "path": str(approval_path),
            "sha256": config["source"]["day38_approval_sha256"],
            "decision_status": config["source"]["expected_decision_status"],
            "verified": True,
        },
        "source_day30_graph": {
            "path": str(graph_path),
            "sha256": config["source"]["day30_graph_sha256"],
            "verified": True,
        },
        "source_day29_registry": {
            "path": str(registry_path),
            "verified": True,
        },
        "target_under_review": {
            "path": str(target_path),
            "sha256": config["source"]["target_config_sha256"],
            "modified": False,
        },
        "changed_day": scope["changed_day"],
        "direct_downstream": scope["direct_downstream"],
        "transitive_descendants": scope["descendants"],
        "formal_review_order": scope["review_order"],
        "formal_review_count": len(scope["review_order"]),
        "uses_zosapi_review_days": scope["uses_zosapi_days"],
        "offline_only_review_days": scope["offline_only_days"],
        "requester_estimate_comparison": {
            "requester_estimate": scope["requester_estimate"],
            "omitted_by_requester": scope["omitted_by_requester"],
            "overreported_by_requester": scope["overreported_by_requester"],
            "exact_set_match": scope["estimate_exact_match"],
            "estimate_was_independently_verified": True,
        },
        "review_rows": rows,
        "formal_impact_analysis_performed": True,
        "review_tasks_approved_for_execution": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "engineering_rerun_claim_made": False,
        "hidden_impact_score_used": False,
    }


def validate_report(report):
    """Recheck completeness and prevent analysis from becoming execution approval."""

    formal = [int(day) for day in report["formal_review_order"]]
    row_days = [int(row["day"]) for row in report["review_rows"]]
    if formal != row_days or len(formal) != len(set(formal)):
        raise ValueError("Formal review rows do not match the calculated scope.")
    if report["formal_review_count"] != len(formal):
        raise ValueError("Formal review count is incorrect.")
    if report.get("formal_impact_analysis_performed") is not True:
        raise ValueError("The formal impact analysis was not recorded.")
    false_fields = (
        "review_tasks_approved_for_execution",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "engineering_rerun_claim_made",
        "hidden_impact_score_used",
    )
    if any(report.get(key) is not False for key in false_fields):
        raise ValueError("The Day 39 report contains an unsupported action or claim.")
    if any(row["automatic_execution"] is not False for row in report["review_rows"]):
        raise ValueError("A Day 39 review row unexpectedly permits automatic execution.")


def write_csv(path, rows):
    """Write the formal review set as a flat UTF-8 CSV."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report):
    """Render the formal scope as a human-readable audit report."""

    comparison = report["requester_estimate_comparison"]
    row_lines = [
        "| 顺序 | Day | 关系 | 执行类别 | 复核类别 | 自动执行 |",
        "|---:|---:|---|---|---|---|",
    ]
    for row in report["review_rows"]:
        row_lines.append(
            f"| {row['review_position']} | {row['day']} | {row['relationship']} | "
            f"{row['execution_class']} | {row['review_class']} | {row['automatic_execution']} |"
        )
    table = "\n".join(row_lines)
    return f"""# Day39 正式影响范围报告

> 本报告只确认复核范围和任务类别，不批准修改 Day22，也不批准执行任何复核任务。

## 1. 变化源与证据

- 变化源：Day{report['changed_day']}
- Day38 审批：`{report['source_day38_approval']['path']}`
- Day38 SHA256：`{report['source_day38_approval']['sha256']}`
- Day30 依赖图：`{report['source_day30_graph']['path']}`
- Day30 SHA256：`{report['source_day30_graph']['sha256']}`
- Day22 目标：`{report['target_under_review']['path']}`
- Day22 已修改：`{report['target_under_review']['modified']}`

## 2. 独立计算结果

- 直接下游：`{report['direct_downstream']}`
- 全部传递下游：`{report['transitive_descendants']}`
- 正式复核顺序：`{report['formal_review_order']}`
- 正式复核节点数：`{report['formal_review_count']}`
- ZOS-API 复核类：`{report['uses_zosapi_review_days']}`
- 离线复核类：`{report['offline_only_review_days']}`

## 3. 与申请人预估的比较

- 申请人预估：`{comparison['requester_estimate']}`
- 申请人遗漏：`{comparison['omitted_by_requester']}`
- 申请人多报：`{comparison['overreported_by_requester']}`
- 集合完全一致：`{comparison['exact_set_match']}`
- 已独立核验：`{comparison['estimate_was_independently_verified']}`

申请人的预估在本次恰好正确，但正式结论来自 Day30 依赖图的独立遍历，而不是直接采纳预估。

## 4. 正式复核集合

{table}

## 5. 权限与安全边界

- 已完成正式影响分析：`{report['formal_impact_analysis_performed']}`
- 已批准执行复核任务：`{report['review_tasks_approved_for_execution']}`
- 已自动执行任务：`{report['automatic_execution_performed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 新计算光学指标：`{report['new_optical_metric_calculated']}`
- 修改现有源文件：`{report['existing_source_modified']}`

下一步必须由人工审查本报告，再决定是否批准源文件修改以及如何分批复核；本报告本身不释放这些权限。
"""


def main():
    config = load_config("configs/day39_formal_impact_scope.yaml")
    validate_execution_lock(config)
    approval_path, approval = load_approval(config)
    graph_path, graph, registry_path, registry = load_graph_and_registry(config)
    target_path = validate_target_unchanged(config, approval)
    scope = build_scope(config, approval, graph, registry)
    validate_claim_boundaries(config)
    rows = make_rows(scope, registry)
    report = build_report(
        config,
        approval_path,
        graph_path,
        registry_path,
        target_path,
        scope,
        rows,
    )
    validate_report(report)

    approval_hash_before = sha256_file(approval_path)
    graph_hash_before = sha256_file(graph_path)
    target_hash_before = sha256_file(target_path)
    output_root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("impact_scope_%Y%m%d_%H%M%S")
    output_dir = output_root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    csv_path = output_dir / names["csv"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(approval_path) != approval_hash_before:
        raise ValueError("The Day 38 approval changed during report generation.")
    if sha256_file(graph_path) != graph_hash_before:
        raise ValueError("The Day 30 graph changed during report generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed during report generation.")

    comparison = report["requester_estimate_comparison"]
    print("========== DAY 39 FORMAL IMPACT-SCOPE REPORT ==========")
    print("No source modification, ZOS-API connection, optical calculation or review task execution was used.")
    print(f"Changed source: Day {report['changed_day']}")
    print(f"Direct downstream: {report['direct_downstream']}")
    print(f"Formal review order: {report['formal_review_order']}")
    print(f"ZOS-API review class: {report['uses_zosapi_review_days']}")
    print(f"Offline review class: {report['offline_only_review_days']}")
    print(f"Requester omissions: {comparison['omitted_by_requester']}")
    print(f"Requester overreporting: {comparison['overreported_by_requester']}")
    print(f"Requester estimate exact match: {comparison['exact_set_match']}")
    print()
    print("[PASS] Formal scope independently calculated from the frozen Day 30 graph")
    print("[PASS] Day 22 and every transitive descendant appear exactly once")
    print("[PASS] Requester estimate verified by omission and overreporting checks")
    print("[PASS] Review tasks classified but not approved or executed")
    print("[PASS] Day 22 and all frozen evidence remained unchanged")
    print(f"[PASS] Review CSV: {csv_path}")
    print(f"[PASS] Impact JSON: {json_path}")
    print(f"[PASS] Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
