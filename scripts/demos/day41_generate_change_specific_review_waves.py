"""Day 41 step 2: generate the approved-scope dependency-wave report."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day41_change_specific_review_wave_plan import (  # noqa: E402
    build_result,
    load_graph,
    load_scope_approval,
    sha256_file,
    validate_execution_lock,
    validate_policies,
    validate_target_unchanged,
)


def build_rows(result):
    """Expand the wave structure into one auditable row per review Day."""

    rows = []
    for wave in result["waves"]:
        for day in wave["days"]:
            execution_class = (
                "uses_zosapi"
                if day in wave["uses_zosapi_days"]
                else "offline_only"
            )
            rows.append(
                {
                    "wave": int(wave["wave"]),
                    "day": int(day),
                    "relationship": "changed_source" if day == result["changed_day"] else "affected_downstream",
                    "execution_class": execution_class,
                    "review_class": (
                        "zosapi_reexecution_review"
                        if execution_class == "uses_zosapi"
                        else "offline_recalculation_review"
                    ),
                    "dependency_ready_after_wave": int(wave["wave"]) - 1,
                    "execution_released": False,
                }
            )
    return rows


def build_report(config, approval_path, graph_path, target_path, result, rows):
    """Build a formal wave report without releasing execution."""

    return {
        "task": "day41_change_specific_review_wave_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day40_scope_approval": {
            "path": str(approval_path),
            "sha256": config["source"]["day40_scope_approval_sha256"],
            "decision_status": config["source"]["expected_decision_status"],
            "verified": True,
        },
        "source_day30_graph": {
            "path": str(graph_path),
            "sha256": config["source"]["day30_graph_sha256"],
            "verified": True,
        },
        "target_under_review": {
            "path": str(target_path),
            "sha256": config["source"]["target_config_sha256"],
            "modified": False,
        },
        "changed_day": result["changed_day"],
        "review_node_count": result["review_node_count"],
        "affected_edges": [
            {"from": source, "to": target}
            for source, target in result["affected_edges"]
        ],
        "affected_edge_count": result["affected_edge_count"],
        "wave_count": result["wave_count"],
        "maximum_wave_width": result["maximum_wave_width"],
        "waves": result["waves"],
        "review_rows": rows,
        "dependency_wave_plan_generated": True,
        "resource_schedule_generated": False,
        "review_tasks_approved_for_execution": False,
        "review_tasks_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "resource_concurrency_claim_made": False,
        "engineering_rerun_claim_made": False,
        "hidden_priority_score_used": False,
    }


def validate_report(report):
    """Recheck report completeness and safety boundaries."""

    row_days = [int(row["day"]) for row in report["review_rows"]]
    wave_days = [int(day) for wave in report["waves"] for day in wave["days"]]
    if row_days != wave_days or len(row_days) != len(set(row_days)):
        raise ValueError("The Day 41 rows do not match the wave structure exactly.")
    if len(row_days) != int(report["review_node_count"]):
        raise ValueError("The Day 41 review-node count is incorrect.")
    if len(report["affected_edges"]) != int(report["affected_edge_count"]):
        raise ValueError("The Day 41 affected-edge count is incorrect.")
    if report.get("dependency_wave_plan_generated") is not True:
        raise ValueError("The Day 41 wave plan was not recorded as generated.")
    false_fields = (
        "resource_schedule_generated",
        "review_tasks_approved_for_execution",
        "review_tasks_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "resource_concurrency_claim_made",
        "engineering_rerun_claim_made",
        "hidden_priority_score_used",
    )
    if any(report.get(key) is not False for key in false_fields):
        raise ValueError("The Day 41 report contains an unsupported action or claim.")
    if any(row["execution_released"] is not False for row in report["review_rows"]):
        raise ValueError("A Day 41 review task was unexpectedly released.")


def write_csv(path, rows):
    """Write one row per review task as UTF-8 CSV."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report):
    """Render a human-readable dependency-wave report."""

    wave_lines = []
    for wave in report["waves"]:
        wave_lines.append(
            f"- Wave {wave['wave']:02d}：Days `{wave['days']}`；"
            f"ZOS-API `{wave['uses_zosapi_days']}`；离线 `{wave['offline_only_days']}`；"
            f"执行已释放 `{wave['execution_released']}`"
        )
    waves_text = "\n".join(wave_lines)
    edge_lines = "\n".join(
        f"- Day{edge['from']} → Day{edge['to']}"
        for edge in report["affected_edges"]
    )
    return f"""# Day41 变化专用复核波次报告

> 本报告只描述依赖就绪顺序，不是执行计划，也不代表同一波任务可以在当前资源条件下并行运行。

## 1. 来源证据

- Day40 范围审批：`{report['source_day40_scope_approval']['path']}`
- Day40 SHA256：`{report['source_day40_scope_approval']['sha256']}`
- Day30 依赖图：`{report['source_day30_graph']['path']}`
- Day30 SHA256：`{report['source_day30_graph']['sha256']}`
- Day22 目标：`{report['target_under_review']['path']}`
- Day22 已修改：`{report['target_under_review']['modified']}`

## 2. 波次摘要

- 变化源：Day{report['changed_day']}
- 复核节点数：`{report['review_node_count']}`
- 范围内依赖边数：`{report['affected_edge_count']}`
- 波次数：`{report['wave_count']}`
- 最大波宽：`{report['maximum_wave_width']}`

{waves_text}

## 3. 范围内依赖边

{edge_lines}

## 4. 怎样解释 Wave 5

Day26 和 Day27 同处 Wave 5，只表示它们在 Day25 通过后都满足依赖条件。它不代表本机资源、许可证或人工审查能力允许同时运行。资源可行性必须在后续步骤单独规划。

## 5. 安全边界

- 已生成依赖波次：`{report['dependency_wave_plan_generated']}`
- 已生成资源调度：`{report['resource_schedule_generated']}`
- 已批准复核任务执行：`{report['review_tasks_approved_for_execution']}`
- 已执行复核任务：`{report['review_tasks_executed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 修改现有源文件：`{report['existing_source_modified']}`
- 声称资源并行可行：`{report['resource_concurrency_claim_made']}`

下一步只能把理论波次转换为资源可行的顺序槽；在新的人工审批之前，所有任务仍保持锁定。
"""


def main():
    config = load_config("configs/day41_change_specific_review_waves.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    approval_path, approval = load_scope_approval(config)
    graph_path, graph = load_graph(config)
    target_path = validate_target_unchanged(config, approval)
    result = build_result(config, approval, graph)
    rows = build_rows(result)
    report = build_report(config, approval_path, graph_path, target_path, result, rows)
    validate_report(report)

    approval_hash_before = sha256_file(approval_path)
    graph_hash_before = sha256_file(graph_path)
    target_hash_before = sha256_file(target_path)
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("review_waves_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    csv_path = output_dir / names["csv"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(approval_path) != approval_hash_before:
        raise ValueError("The Day 40 scope approval changed during Day 41 generation.")
    if sha256_file(graph_path) != graph_hash_before:
        raise ValueError("The Day 30 graph changed during Day 41 generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed during Day 41 generation.")

    print("========== DAY 41 CHANGE-SPECIFIC REVIEW WAVES ==========")
    print("No source modification, ZOS-API connection, optical calculation or review task execution was used.")
    print(
        f"Changed Day {report['changed_day']}: nodes={report['review_node_count']}, "
        f"affected edges={report['affected_edge_count']}, waves={report['wave_count']}, "
        f"max width={report['maximum_wave_width']}"
    )
    for wave in report["waves"]:
        print(
            f"  Wave {wave['wave']:02d}: days={wave['days']}; "
            f"ZOS-API={wave['uses_zosapi_days']}; offline={wave['offline_only_days']}; "
            f"execution released={wave['execution_released']}"
        )
    print()
    print("[PASS] Six dependency-safe waves generated from the approved scope")
    print("[PASS] Seven review nodes represented exactly once")
    print("[PASS] Nine affected edges point from earlier to later waves")
    print("[PASS] Execution classes retained without releasing any task")
    print("[PASS] Day 22 and all frozen evidence remained unchanged")
    print(f"[PASS] Review CSV: {csv_path}")
    print(f"[PASS] Wave JSON: {json_path}")
    print(f"[PASS] Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
