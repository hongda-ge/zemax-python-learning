"""Day 43 step 2: generate formal evidence for simulated failure gates."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day43_change_specific_failure_gate_plan import (  # noqa: E402
    build_drill_results,
    load_sources,
    sha256_file,
    validate_execution_lock,
    validate_policies,
    validate_target_unchanged,
)


def flatten_rows(results):
    """Expand all drills into explicit task-state rows."""

    rows = []
    for result in results:
        for state in result["states"]:
            rows.append(
                {
                    "drill_id": result["drill_id"],
                    "simulated_failed_day": result["failed_day"],
                    "simulated_failed_slot": result["failed_slot"],
                    "day": state["day"],
                    "resource_slot": state["resource_slot"],
                    "status": state["status"],
                    "state_origin": state["state_origin"],
                    "actually_executed": state["actually_executed"],
                    "execution_released": state["execution_released"],
                }
            )
    return rows


def build_report(config, schedule_path, graph_path, target_path, results, rows):
    """Build the formal simulation report without claiming a real failure."""

    return {
        "task": "day43_change_specific_failure_gate_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day42_schedule": {
            "path": str(schedule_path),
            "sha256": config["source"]["day42_schedule_sha256"],
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
        "simulation_only": True,
        "drill_count": len(results),
        "state_row_count": len(rows),
        "drills": results,
        "state_rows": rows,
        "failure_gate_report_generated": True,
        "real_failure_occurred": False,
        "review_tasks_approved_for_execution": False,
        "review_tasks_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "global_stop_claim_made": False,
        "hidden_priority_score_used": False,
    }


def validate_report(report):
    """Recheck simulated origins, partitions and locked actions."""

    if report["drill_count"] != 4 or report["state_row_count"] != 28:
        raise ValueError("The Day 43 drill or state-row count is incorrect.")
    identities = {(row["drill_id"], int(row["day"])) for row in report["state_rows"]}
    if len(identities) != report["state_row_count"]:
        raise ValueError("A Day 43 drill/day state is missing or duplicated.")
    allowed_statuses = {"PASS", "FAIL", "BLOCKED", "REVIEWABLE"}
    if any(
        row["status"] not in allowed_statuses
        or row["state_origin"] != "SIMULATED"
        or row["actually_executed"] is not False
        or row["execution_released"] is not False
        for row in report["state_rows"]
    ):
        raise ValueError("A Day 43 row contains a real or invalid state.")
    if any(sum(1 for row in report["state_rows"] if row["drill_id"] == drill["drill_id"] and row["status"] == "FAIL") != 1 for drill in report["drills"]):
        raise ValueError("Each Day 43 drill must contain exactly one simulated FAIL.")
    if report.get("failure_gate_report_generated") is not True or report.get("simulation_only") is not True:
        raise ValueError("The Day 43 report is not marked as a simulation.")
    false_fields = (
        "real_failure_occurred",
        "review_tasks_approved_for_execution",
        "review_tasks_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "global_stop_claim_made",
        "hidden_priority_score_used",
    )
    if any(report.get(key) is not False for key in false_fields):
        raise ValueError("The Day 43 report contains an unsupported action or claim.")


def write_csv(path, rows):
    """Write one row per drill/task state."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report):
    """Create a readable failure-gate simulation report."""

    sections = []
    for drill in report["drills"]:
        counts = drill["state_counts"]
        sections.extend(
            [
                f"## {drill['drill_id']}",
                "",
                f"- 注入状态：Day{drill['failed_day']} 在 Slot {drill['failed_slot']} `SIMULATED_FAIL`；",
                f"- PASS：`{drill['pass_days']}`；",
                f"- BLOCKED：`{drill['blocked_days']}`；",
                f"- REVIEWABLE：`{drill['reviewable_days']}`；",
                f"- 计数：PASS={counts['PASS']}，FAIL=1，BLOCKED={counts['BLOCKED']}，REVIEWABLE={counts['REVIEWABLE']}。",
                "",
            ]
        )
    sections_text = "\n".join(sections)
    return f"""# Day43 变化专用失败门推演报告

> 本报告中的所有状态均为 SIMULATED。没有真实复核任务被执行，也没有发生真实失败。

## 冻结来源

- Day42 调度：`{report['source_day42_schedule']['path']}`
- Day42 SHA256：`{report['source_day42_schedule']['sha256']}`
- Day30 依赖图：`{report['source_day30_graph']['path']}`
- Day30 SHA256：`{report['source_day30_graph']['sha256']}`
- Day22 目标：`{report['target_under_review']['path']}`
- Day22 已修改：`{report['target_under_review']['modified']}`

## 状态解释

- PASS：假想审批门前已经完成且未失败；
- FAIL：本次演练注入的单个假想失败；
- BLOCKED：依赖失败证据的传递下游；
- REVIEWABLE：不依赖失败节点、仍可等待人工决定的未来工作。

{sections_text}
## 同槽分支隔离结论

Day26 与 Day27 同处 Slot 5，但二者不是互相依赖。Day26 失败不会自动锁定 Day27 或 Day28；Day27 失败则必须锁定它的下游 Day28。

## 安全边界

- 仅为模拟：`{report['simulation_only']}`
- 真实失败发生：`{report['real_failure_occurred']}`
- 已批准任务执行：`{report['review_tasks_approved_for_execution']}`
- 已执行复核任务：`{report['review_tasks_executed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 修改源文件：`{report['existing_source_modified']}`
- 声称全局停止：`{report['global_stop_claim_made']}`

任何真实任务的释放仍需要新的、单独的人工审批。
"""


def main():
    config = load_config("configs/day43_change_specific_failure_gates.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    schedule_path, schedule, graph_path, graph = load_sources(config)
    target_path = validate_target_unchanged(config, schedule)
    results = build_drill_results(config, schedule, graph)
    rows = flatten_rows(results)
    report = build_report(config, schedule_path, graph_path, target_path, results, rows)
    validate_report(report)

    schedule_hash_before = sha256_file(schedule_path)
    graph_hash_before = sha256_file(graph_path)
    target_hash_before = sha256_file(target_path)
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("failure_gates_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    csv_path = output_dir / names["csv"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(schedule_path) != schedule_hash_before:
        raise ValueError("The Day 42 schedule changed during Day 43 generation.")
    if sha256_file(graph_path) != graph_hash_before:
        raise ValueError("The Day 30 graph changed during Day 43 generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed during Day 43 generation.")

    print("========== DAY 43 CHANGE-SPECIFIC FAILURE GATES ==========")
    print("No real failure, source modification, ZOS-API connection or review task execution was used.")
    print("Every reported task state is SIMULATED.")
    for result in results:
        counts = result["state_counts"]
        print(
            f"{result['drill_id']}: PASS={counts['PASS']}, FAIL=1, "
            f"BLOCKED={counts['BLOCKED']}, REVIEWABLE={counts['REVIEWABLE']}"
        )
    print()
    print("[PASS] Four simulated failure drills generated")
    print("[PASS] Explicit simulated state rows: 28")
    print("[PASS] All transitive descendants blocked without same-slot overblocking")
    print("[PASS] Day26/Day27 branch isolation preserved")
    print("[PASS] No actual execution, real failure or global-stop claim")
    print("[PASS] Day 22 and all frozen evidence remained unchanged")
    print(f"[PASS] State CSV: {csv_path}")
    print(f"[PASS] Gate JSON: {json_path}")
    print(f"[PASS] Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
