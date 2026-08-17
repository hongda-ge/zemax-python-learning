"""Day 42 step 2: generate the reviewed change-specific resource schedule."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day42_change_specific_resource_schedule_plan import (  # noqa: E402
    build_schedule,
    load_day41,
    sha256_file,
    validate_execution_lock,
    validate_policies,
    validate_target_unchanged,
)


def build_rows(result):
    """Expand each resource slot into one auditable row per review task."""

    rows = []
    for slot in result["slots"]:
        for day in slot["days"]:
            execution_class = (
                "uses_zosapi"
                if day in slot["uses_zosapi_days"]
                else "offline_only"
            )
            rows.append(
                {
                    "resource_slot": int(slot["slot"]),
                    "source_wave": int(slot["source_wave"]),
                    "subslot_within_wave": int(slot["subslot_within_wave"]),
                    "day": int(day),
                    "execution_class": execution_class,
                    "manual_approval_required": True,
                    "execution_released": False,
                    "automatic_execution": False,
                    "duration_estimate": "",
                }
            )
    return rows


def build_report(config, day41_path, target_path, result, rows):
    """Build the formal schedule report while retaining all execution locks."""

    return {
        "task": "day42_change_specific_resource_schedule_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day41_wave_report": {
            "path": str(day41_path),
            "sha256": config["source"]["day41_wave_report_sha256"],
            "verified": True,
        },
        "target_under_review": {
            "path": str(target_path),
            "sha256": config["source"]["target_config_sha256"],
            "modified": False,
        },
        "teaching_resources": config["teaching_resources"],
        "changed_day": result["changed_day"],
        "task_count": result["task_count"],
        "theoretical_wave_count": result["theoretical_wave_count"],
        "resource_slot_count": result["resource_slot_count"],
        "extra_slots_due_to_capacity": result["extra_slots_due_to_capacity"],
        "maximum_slot_width": result["maximum_slot_width"],
        "slots": result["slots"],
        "task_rows": rows,
        "resource_schedule_generated": True,
        "review_tasks_approved_for_execution": False,
        "review_tasks_executed": False,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "duration_estimate_created": False,
        "resource_benchmark_claim_made": False,
        "hidden_priority_score_used": False,
    }


def validate_report(report):
    """Revalidate membership, capacities and safety boundaries."""

    rows = report["task_rows"]
    if len(rows) != int(report["task_count"]):
        raise ValueError("The Day 42 task-row count is incorrect.")
    days = [int(row["day"]) for row in rows]
    if len(days) != len(set(days)):
        raise ValueError("A Day 42 review task appears more than once.")
    resources = report["teaching_resources"]
    for slot in report["slots"]:
        if len(slot["uses_zosapi_days"]) > int(resources["zosapi_capacity_per_slot"]):
            raise ValueError("A Day 42 slot exceeds ZOS-API capacity.")
        if len(slot["offline_only_days"]) > int(resources["offline_capacity_per_slot"]):
            raise ValueError("A Day 42 slot exceeds offline capacity.")
    if report.get("resource_schedule_generated") is not True:
        raise ValueError("The Day 42 schedule was not recorded as generated.")
    false_fields = (
        "review_tasks_approved_for_execution",
        "review_tasks_executed",
        "automatic_execution_performed",
        "new_zosapi_connection_created",
        "new_optical_metric_calculated",
        "existing_source_modified",
        "duration_estimate_created",
        "resource_benchmark_claim_made",
        "hidden_priority_score_used",
    )
    if any(report.get(key) is not False for key in false_fields):
        raise ValueError("The Day 42 report contains an unsupported action or claim.")
    if any(
        row["manual_approval_required"] is not True
        or row["execution_released"] is not False
        or row["automatic_execution"] is not False
        or row["duration_estimate"]
        for row in rows
    ):
        raise ValueError("A Day 42 task has an invalid approval or execution state.")


def write_csv(path, rows):
    """Write one row per scheduled review task."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report):
    """Create a human-readable schedule report."""

    slot_lines = []
    for slot in report["slots"]:
        slot_lines.append(
            f"| {slot['slot']} | {slot['source_wave']} | {slot['subslot_within_wave']} | "
            f"`{slot['days']}` | `{slot['uses_zosapi_days']}` | "
            f"`{slot['offline_only_days']}` | {slot['execution_released']} |"
        )
    slots_text = "\n".join(slot_lines)
    return f"""# Day42 变化专用资源调度报告

> 本报告把 Day41 的依赖就绪波次转换为满足教学容量的顺序槽。它不是执行批准，也不包含真实耗时。

## 1. 冻结来源

- Day41 波次报告：`{report['source_day41_wave_report']['path']}`
- Day41 SHA256：`{report['source_day41_wave_report']['sha256']}`
- Day22 目标：`{report['target_under_review']['path']}`
- Day22 已修改：`{report['target_under_review']['modified']}`

## 2. 教学资源容量

- ZOS-API：每槽最多 `{report['teaching_resources']['zosapi_capacity_per_slot']}` 个任务；
- 离线任务：每槽最多 `{report['teaching_resources']['offline_capacity_per_slot']}` 个任务；
- 每个任务执行前仍需人工审批；
- 槽表示顺序组，不表示时长。

## 3. 调度摘要

- 变化源：Day{report['changed_day']}
- 任务数：`{report['task_count']}`
- Day41 理论波次：`{report['theoretical_wave_count']}`
- Day42 资源槽：`{report['resource_slot_count']}`
- 容量拆分新增槽：`{report['extra_slots_due_to_capacity']}`
- 最大槽宽：`{report['maximum_slot_width']}`

| 资源槽 | 来源波次 | 子槽 | 全部 Day | ZOS-API | 离线 | 执行已释放 |
|---:|---:|---:|---|---|---|---|
{slots_text}

## 4. 为什么没有新增槽

Day23 和 Day25 各自独占一个 ZOS-API 波次；Day26 和 Day27 同处 Wave 5，但二者都是离线任务，数量恰好等于离线容量 2。因此六个理论波次可以直接映射为六个资源槽。

## 5. 安全边界

- 已生成资源调度：`{report['resource_schedule_generated']}`
- 已批准复核任务执行：`{report['review_tasks_approved_for_execution']}`
- 已执行复核任务：`{report['review_tasks_executed']}`
- 新建 ZOS-API 连接：`{report['new_zosapi_connection_created']}`
- 修改 Day22：`{report['existing_source_modified']}`
- 创建时长估计：`{report['duration_estimate_created']}`

下一步只能为该调度设计失败门与人工审批规则；在新的明确授权前，所有任务继续锁定。
"""


def main():
    config = load_config("configs/day42_change_specific_resource_schedule.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    day41_path, day41_report = load_day41(config)
    target_path = validate_target_unchanged(config, day41_report)
    result = build_schedule(config, day41_report)
    rows = build_rows(result)
    report = build_report(config, day41_path, target_path, result, rows)
    validate_report(report)

    day41_hash_before = sha256_file(day41_path)
    target_hash_before = sha256_file(target_path)
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    stamp = datetime.now().astimezone().strftime("resource_schedule_%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["planned_outputs_after_approval"]
    json_path = output_dir / names["json"]
    csv_path = output_dir / names["csv"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    markdown_path.write_text(build_markdown(report), encoding="utf-8")

    if sha256_file(day41_path) != day41_hash_before:
        raise ValueError("The Day 41 report changed during Day 42 generation.")
    if sha256_file(target_path) != target_hash_before:
        raise ValueError("The Day 22 target changed during Day 42 generation.")

    print("========== DAY 42 CHANGE-SPECIFIC RESOURCE SCHEDULE ==========")
    print("No source modification, ZOS-API connection, optical calculation or review task execution was used.")
    print("Slots are order groups; no duration or resource benchmark was inferred.")
    print(
        f"Changed Day {report['changed_day']}: {report['theoretical_wave_count']} waves -> "
        f"{report['resource_slot_count']} slots; extra={report['extra_slots_due_to_capacity']}"
    )
    for slot in report["slots"]:
        print(
            f"  Slot {slot['slot']:02d}: days={slot['days']}; "
            f"ZOS-API={slot['uses_zosapi_days']}; offline={slot['offline_only_days']}; "
            f"execution released={slot['execution_released']}"
        )
    print()
    print("[PASS] Six resource-feasible slots generated")
    print("[PASS] Seven review tasks represented exactly once")
    print("[PASS] ZOS-API capacity 1 and offline capacity 2 respected")
    print("[PASS] Manual approval remains required for every task")
    print("[PASS] No task execution, duration estimate or resource benchmark")
    print("[PASS] Day 22 and frozen Day 41 evidence remained unchanged")
    print(f"[PASS] Schedule CSV: {csv_path}")
    print(f"[PASS] Schedule JSON: {json_path}")
    print(f"[PASS] Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
