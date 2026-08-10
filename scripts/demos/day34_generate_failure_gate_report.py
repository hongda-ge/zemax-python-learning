"""Day 34 step 2: generate hypothetical failure-gate propagation reports."""

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
from scripts.demos.day34_failure_gate_plan import (  # noqa: E402
    build_drill_results,
    load_sources,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 34 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("failure_gate_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def flatten_rows(results):
    """Create one explicit state row for every drill/scenario task."""

    rows = []
    for result in results:
        for state in result["states"]:
            rows.append(
                {
                    "drill_id": result["drill_id"],
                    "schedule_scenario": result["schedule_scenario"],
                    "failed_day": result["failed_day"],
                    "failed_slot": result["failed_slot"],
                    "day": state["day"],
                    "resource_slot": state["resource_slot"],
                    "hypothetical_status": state["status"],
                    "actually_executed": False,
                    "real_failure_observed": False,
                    "manual_approval_required_to_resume": state["status"] == "REVIEWABLE",
                }
            )
    return rows


def write_csv(path, rows):
    """Write task-level hypothetical gate states."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, results):
    """Write a human-readable failure-propagation report."""

    lines = [
        "# Day34 失败传播与人工审批门",
        "",
        "> 本报告中的失败和状态均为离线教学演练，不是实际实验结果，也没有自动执行任何历史任务。",
        "",
        "## 状态定义",
        "",
        "- `PASS`：假想审批门前已经完成且未失败；",
        "- `FAIL`：本次演练指定的失败节点；",
        "- `BLOCKED`：依赖失败证据的传递下游；",
        "- `REVIEWABLE`：不依赖失败证据，人工审批后仍可复核。",
        "",
        "## 演练摘要",
        "",
        "| 演练 | 失败节点 | 失败槽 | PASS | FAIL | BLOCKED | REVIEWABLE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        counts = result["state_counts"]
        lines.append(
            f"| `{result['drill_id']}` | Day{result['failed_day']} | "
            f"{result['failed_slot']} | {counts['PASS']} | {counts['FAIL']} | "
            f"{counts['BLOCKED']} | {counts['REVIEWABLE']} |"
        )
    for result in results:
        lines.extend(
            [
                "",
                f"## {result['drill_id']}",
                "",
                f"- 调度场景：`{result['schedule_scenario']}`",
                f"- 假想失败：Day{result['failed_day']}，资源槽 {result['failed_slot']}",
                f"- PASS：{result['pass_days']}",
                f"- BLOCKED：{result['blocked_days']}",
                f"- REVIEWABLE：{result['reviewable_days']}",
                "",
                "| Day | 资源槽 | 假想状态 | 实际执行 |",
                "|---:|---:|---|---|",
            ]
        )
        for state in sorted(result["states"], key=lambda item: (item["resource_slot"], item["day"])):
            lines.append(
                f"| {state['day']} | {state['resource_slot']} | "
                f"`{state['status']}` | 否 |"
            )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "- BLOCKED 是依赖关系造成的安全锁定，不表示该任务本身有错误。",
            "- REVIEWABLE 不是自动继续指令，恢复前仍需人工审批。",
            "- 排在失败槽后面的任务只有在依赖失败证据时才会变为 BLOCKED。",
            "- 本报告未观察到真实失败，未连接 ZOS-API，也未重新计算光学指标。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_propagation(path, results):
    """Plot every hypothetical state against the Day 33 resource slots."""

    colors = {
        "PASS": "#54A24B",
        "FAIL": "#E45756",
        "BLOCKED": "#9D9D9D",
        "REVIEWABLE": "#4C78A8",
    }
    figure, axes = plt.subplots(len(results), 1, figsize=(16, 11))
    if len(results) == 1:
        axes = [axes]
    for axis, result in zip(axes, results):
        states_by_slot = {}
        for state in result["states"]:
            states_by_slot.setdefault(state["resource_slot"], []).append(state)
        for slot, states in sorted(states_by_slot.items()):
            for index, state in enumerate(sorted(states, key=lambda item: item["day"])):
                y = index - (len(states) - 1) / 2
                axis.scatter(
                    slot, y, s=480, color=colors[state["status"]],
                    edgecolor="white", linewidth=1.2, zorder=3,
                )
                axis.text(
                    slot, y, f"D{state['day']}", ha="center", va="center",
                    color="white", fontsize=9,
                )
        axis.axvline(result["failed_slot"] + 0.5, color="#E45756", linestyle="--", linewidth=1)
        max_slot = max(state["resource_slot"] for state in result["states"])
        axis.set_xlim(0.5, max_slot + 0.5)
        axis.set_xticks(range(1, max_slot + 1))
        axis.set_xlabel("Day 33 resource slot")
        axis.set_yticks([])
        axis.set_ylim(-1.7, 1.7)
        axis.grid(axis="x", alpha=0.15)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.set_title(
            f"{result['drill_id']}  |  hypothetical D{result['failed_day']} FAIL at slot {result['failed_slot']}"
        )
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
               markeredgecolor="white", markersize=11, label=status)
        for status, color in colors.items()
    ]
    figure.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=4, frameon=False)
    figure.suptitle("Day 34 Hypothetical Failure-Gate Propagation\n(no real task was executed)", fontsize=15)
    figure.tight_layout(rect=(0, 0.055, 1, 0.95))
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def validate_rows(results, rows):
    """Recheck each drill partition and all non-execution claims."""

    expected = sum(sum(result["state_counts"].values()) for result in results)
    if len(rows) != expected:
        raise ValueError("Generated Day 34 state-row count is incorrect.")
    identities = {(row["drill_id"], row["day"]) for row in rows}
    if len(identities) != len(rows):
        raise ValueError("A Day 34 drill/day state appears more than once.")
    if any(row["actually_executed"] or row["real_failure_observed"] for row in rows):
        raise ValueError("Day 34 accidentally claimed execution or a real failure.")
    allowed = {"PASS", "FAIL", "BLOCKED", "REVIEWABLE"}
    if {row["hypothetical_status"] for row in rows} != allowed:
        raise ValueError("Day 34 generated an incomplete status vocabulary.")


def main():
    config = load_config("configs/day34_failure_gate_propagation.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    schedule_path, schedule, graph_path, graph = load_sources(config)
    results = build_drill_results(config, schedule, graph)
    rows = flatten_rows(results)
    validate_rows(results, rows)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    report = {
        "task": "day34_failure_gate_propagation_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day33_schedule": str(schedule_path),
        "source_day30_dependency_graph": str(graph_path),
        "drill_count": len(results),
        "state_row_count": len(rows),
        "drills": results,
        "state_rows": rows,
        "all_states_hypothetical": True,
        "automatic_execution_performed": False,
        "real_failure_observed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "global_stop_claim_made": False,
        "hidden_priority_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, results)
    plot_propagation(figure_file, results)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 34 FAILURE-GATE PROPAGATION ==========")
    print("No real failure, ZOS-API connection or historical task execution was used.")
    print("All PASS/FAIL/BLOCKED/REVIEWABLE states are hypothetical teaching states.")
    for result in results:
        counts = result["state_counts"]
        print(
            f"{result['drill_id']}: PASS={counts['PASS']}, FAIL={counts['FAIL']}, "
            f"BLOCKED={counts['BLOCKED']}, REVIEWABLE={counts['REVIEWABLE']}"
        )
    print()
    print(f"[PASS] Failure drills generated: {len(results)}")
    print(f"[PASS] Explicit hypothetical state rows: {len(rows)}")
    print("[PASS] All transitive descendants blocked without unrelated-branch overblocking")
    print("[PASS] No actual task execution or real failure claim")
    print("[PASS] Global-stop and hidden-priority claims remain false")
    print(f"[PASS] State CSV: {csv_file}")
    print(f"[PASS] Gate JSON: {json_file}")
    print(f"[PASS] Markdown report: {markdown_file}")
    print(f"[PASS] Propagation figure: {figure_file}")


if __name__ == "__main__":
    main()
