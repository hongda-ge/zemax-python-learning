"""Day 33 step 2: generate the reviewed resource-feasible schedule."""

import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MATPLOTLIB_CACHE = PROJECT_ROOT / "outputs" / ".matplotlib_cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day33_resource_schedule_plan import (  # noqa: E402
    build_schedule_results,
    load_day32,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 33 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("resource_schedule_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def flatten_rows(results):
    """Expand every scheduled task into an explicit CSV row."""

    rows = []
    for result in results:
        for slot in result["slots"]:
            for day in slot["days"]:
                execution_class = (
                    "uses_zosapi"
                    if day in slot["uses_zosapi_days"]
                    else "offline_only"
                )
                rows.append(
                    {
                        "scenario_id": result["scenario_id"],
                        "changed_day": result["changed_day"],
                        "resource_slot": slot["slot"],
                        "source_wave": slot["source_wave"],
                        "subslot_within_wave": slot["subslot_within_wave"],
                        "day": day,
                        "execution_class": execution_class,
                        "manual_approval_required": True,
                        "automatic_execution": False,
                        "duration_estimate": "",
                    }
                )
    return rows


def write_csv(path, rows):
    """Write the task-level resource schedule."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, results, capacities):
    """Write a readable resource schedule and its interpretation boundary."""

    lines = [
        "# Day33 资源可行的教学复核调度",
        "",
        "> 本报告把依赖就绪波次转换为教学资源槽。它不是自动执行脚本，也不是带有真实耗时的项目甘特图。",
        "",
        "## 教学资源假设",
        "",
        f"- 每槽最多 {capacities['zosapi_capacity_per_slot']} 个 ZOS-API 任务；",
        f"- 每槽最多 {capacities['offline_capacity_per_slot']} 个离线任务；",
        "- 每个槽开始前仍需人工审批；",
        "- 槽编号只表示顺序，不表示时长。",
        "",
        "## 场景摘要",
        "",
        "| 变化场景 | 任务数 | Day32 波次 | Day33 槽位 | 资源拆分新增槽 | 最大槽宽 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| `{result['scenario_id']}` | {result['task_count']} | "
            f"{result['theoretical_wave_count']} | {result['resource_slot_count']} | "
            f"{result['extra_slots_due_to_zosapi_capacity']} | {result['maximum_slot_width']} |"
        )
    for result in results:
        lines.extend(
            [
                "",
                f"## {result['scenario_id']}",
                "",
                "| 资源槽 | 来源波次 | 子槽 | 全部 Day | ZOS-API | 离线 |",
                "|---:|---:|---:|---|---|---|",
            ]
        )
        for slot in result["slots"]:
            lines.append(
                f"| {slot['slot']} | {slot['source_wave']} | "
                f"{slot['subslot_within_wave']} | {slot['days']} | "
                f"{slot['uses_zosapi_days']} | {slot['offline_only_days']} |"
            )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "- 同一槽中的任务只表示满足声明的教学容量，不表示已经批准运行。",
            "- 同一来源波次被拆成多个槽，是资源串行化，不是新增科学依赖。",
            "- 没有真实运行时长，因此不能从槽位数量推算小时数或完成日期。",
            "- 本报告未连接 ZOS-API、未重新计算光学指标、未执行历史任务。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_schedule(path, results):
    """Plot resource slots and annotate their Day32 source waves."""

    colors = {"uses_zosapi": "#4C78A8", "offline_only": "#F58518"}
    figure, axes = plt.subplots(len(results), 1, figsize=(16, 9))
    if len(results) == 1:
        axes = [axes]
    for axis, result in zip(axes, results):
        previous_wave = None
        for slot in result["slots"]:
            x = slot["slot"]
            if previous_wave is not None and slot["source_wave"] != previous_wave:
                axis.axvline(x - 0.5, color="#BBBBBB", linewidth=0.8, linestyle="--")
            previous_wave = slot["source_wave"]
            for index, day in enumerate(slot["days"]):
                execution_class = (
                    "uses_zosapi" if day in slot["uses_zosapi_days"] else "offline_only"
                )
                y = index - (len(slot["days"]) - 1) / 2
                axis.scatter(
                    x, y, s=500, color=colors[execution_class],
                    edgecolor="white", linewidth=1.2, zorder=3,
                )
                axis.text(x, y, f"D{day}", ha="center", va="center", color="white", fontsize=9)
            axis.text(
                x, 1.45, f"W{slot['source_wave']}.{slot['subslot_within_wave']}",
                ha="center", va="center", fontsize=8, color="#555555",
            )
        axis.set_xlim(0.5, result["resource_slot_count"] + 0.5)
        axis.set_xticks(range(1, result["resource_slot_count"] + 1))
        axis.set_xlabel("Resource-feasible order slot")
        axis.set_yticks([])
        axis.set_ylim(-1.8, 1.8)
        axis.grid(axis="x", alpha=0.15)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.set_title(
            f"{result['scenario_id']}  |  Day32 waves {result['theoretical_wave_count']} "
            f"-> Day33 slots {result['resource_slot_count']}"
        )
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=colors["uses_zosapi"],
               markeredgecolor="white", markersize=11, label="ZOS-API channel"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=colors["offline_only"],
               markeredgecolor="white", markersize=11, label="offline channel"),
    ]
    figure.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2, frameon=False)
    figure.suptitle("Day 33 Resource-Feasible Review Schedule\n(order slots, not duration)", fontsize=15)
    figure.tight_layout(rect=(0, 0.06, 1, 0.94))
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def validate_rows(results, rows):
    """Revalidate schedule membership and execution locks."""

    expected = sum(result["task_count"] for result in results)
    if len(rows) != expected:
        raise ValueError("Generated Day 33 task-row count is incorrect.")
    identities = {(row["scenario_id"], row["day"]) for row in rows}
    if len(identities) != len(rows):
        raise ValueError("A Day 33 scenario/day appears more than once.")
    if any(not row["manual_approval_required"] or row["automatic_execution"] for row in rows):
        raise ValueError("Day 33 approval or execution state is incorrect.")
    if any(row["duration_estimate"] for row in rows):
        raise ValueError("Day 33 generated an unsupported duration estimate.")


def main():
    config = load_config("configs/day33_resource_feasible_review_schedule.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    source_path, report = load_day32(config)
    results = build_schedule_results(config, report)
    rows = flatten_rows(results)
    validate_rows(results, rows)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    report_out = {
        "task": "day33_resource_feasible_schedule_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day32_wave_report": str(source_path),
        "teaching_resources": config["teaching_resources"],
        "scenario_count": len(results),
        "task_row_count": len(rows),
        "scenarios": results,
        "task_rows": rows,
        "manual_approval_required": True,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "duration_estimate_created": False,
        "resource_benchmark_claim_made": False,
        "hidden_priority_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, results, config["teaching_resources"])
    plot_schedule(figure_file, results)
    json_file.write_text(json.dumps(report_out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 33 RESOURCE-FEASIBLE SCHEDULE ==========")
    print("No ZOS-API connection, optical calculation or task execution was used.")
    print("Slots are order groups; no duration or resource benchmark was inferred.")
    for result in results:
        print(
            f"{result['scenario_id']}: {result['theoretical_wave_count']} waves -> "
            f"{result['resource_slot_count']} slots; extra={result['extra_slots_due_to_zosapi_capacity']}"
        )
    print()
    print(f"[PASS] Scenarios generated: {len(results)}")
    print(f"[PASS] Explicit scheduled task rows: {len(rows)}")
    print("[PASS] ZOS-API capacity 1 and offline capacity 2 respected")
    print("[PASS] Manual approval remains required for every task")
    print("[PASS] No automatic execution or unsupported duration estimate")
    print(f"[PASS] Schedule CSV: {csv_file}")
    print(f"[PASS] Schedule JSON: {json_file}")
    print(f"[PASS] Markdown report: {markdown_file}")
    print(f"[PASS] Schedule figure: {figure_file}")


if __name__ == "__main__":
    main()
