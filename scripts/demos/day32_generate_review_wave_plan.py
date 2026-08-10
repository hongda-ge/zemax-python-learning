"""Day 32 step 2: generate dependency-safe review-wave reports."""

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
from scripts.demos.day32_review_wave_plan import (  # noqa: E402
    build_wave_results,
    load_sources,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 32 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("wave_plan_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def flatten_wave_rows(results):
    """Create one explicit task row for every scenario/day membership."""

    rows = []
    for result in results:
        for wave in result["waves"]:
            for day in wave["days"]:
                execution_class = (
                    "uses_zosapi"
                    if day in wave["uses_zosapi_days"]
                    else "offline_only"
                )
                rows.append(
                    {
                        "scenario_id": result["scenario_id"],
                        "changed_day": result["changed_day"],
                        "wave": wave["wave"],
                        "day": day,
                        "execution_class": execution_class,
                        "dependency_ready": True,
                        "automatic_execution": False,
                        "resource_concurrency_approved": False,
                    }
                )
    return rows


def write_csv(path, rows):
    """Write a UTF-8 wave membership table."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, results):
    """Write a readable report that preserves the concurrency boundary."""

    lines = [
        "# Day32 依赖安全的复核波次",
        "",
        "> 本报告只描述依赖关系上的就绪顺序，不批准任务运行，也不证明同一波次可以占用同一份 Zemax 许可证并行执行。",
        "",
        "## 结果摘要",
        "",
        "| 变化场景 | 复核节点 | 波次数 | 最大波宽 | 受影响依赖边 |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| `{result['scenario_id']}` | {result['review_node_count']} | "
            f"{result['wave_count']} | {result['maximum_wave_width']} | "
            f"{result['affected_edge_count']} |"
        )
    for result in results:
        lines.extend(
            [
                "",
                f"## {result['scenario_id']}",
                "",
                f"变化源：Day{result['changed_day']}。",
                "",
                "| 波次 | 全部节点 | ZOS-API 节点 | 离线节点 |",
                "|---:|---|---|---|",
            ]
        )
        for wave in result["waves"]:
            lines.append(
                f"| {wave['wave']} | {wave['days']} | "
                f"{wave['uses_zosapi_days']} | {wave['offline_only_days']} |"
            )
    lines.extend(
        [
            "",
            "## 如何阅读",
            "",
            "- 同一波次中的节点不存在当前复核集合内部的直接或间接待完成上游。",
            "- 下一波次只能在上一波次的证据复核完成后进入依赖就绪状态。",
            "- `uses_zosapi` 与 `offline_only` 是执行类型标签，不是自动运行指令。",
            "- 同一波次允许理论并行，不代表许可证、CPU、内存或人工审批允许真实并行。",
            "- 本报告没有自动执行任何节点，也没有用隐藏分数决定优先级。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_waves(path, results):
    """Plot wave lanes, separating ZOS-API and offline task classes."""

    colors = {"uses_zosapi": "#4C78A8", "offline_only": "#F58518"}
    figure, axes = plt.subplots(len(results), 1, figsize=(15, 9))
    if len(results) == 1:
        axes = [axes]
    for axis, result in zip(axes, results):
        for wave in result["waves"]:
            x = wave["wave"]
            for index, day in enumerate(wave["days"]):
                execution_class = (
                    "uses_zosapi" if day in wave["uses_zosapi_days"] else "offline_only"
                )
                y = index - (len(wave["days"]) - 1) / 2
                axis.scatter(
                    x, y, s=520, color=colors[execution_class],
                    edgecolor="white", linewidth=1.2, zorder=3,
                )
                axis.text(x, y, f"D{day}", ha="center", va="center", color="white", fontsize=9)
        axis.set_xlim(0.5, result["wave_count"] + 0.5)
        axis.set_xticks(range(1, result["wave_count"] + 1))
        axis.set_xlabel("Dependency-ready wave")
        axis.set_yticks([])
        axis.set_ylim(-1.8, 1.8)
        axis.grid(axis="x", alpha=0.2)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.set_title(
            f"{result['scenario_id']}  |  {result['review_node_count']} nodes, "
            f"{result['wave_count']} waves"
        )
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=colors["uses_zosapi"],
               markeredgecolor="white", markersize=11, label="ZOS-API review"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=colors["offline_only"],
               markeredgecolor="white", markersize=11, label="offline review"),
    ]
    figure.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2, frameon=False)
    figure.suptitle("Day 32 Dependency-Ready Review Waves\n(not a resource-concurrency schedule)", fontsize=15)
    figure.tight_layout(rect=(0, 0.06, 1, 0.94))
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def validate_generated_rows(results, rows):
    """Recheck membership and the absence of execution approval."""

    expected_count = sum(result["review_node_count"] for result in results)
    if len(rows) != expected_count:
        raise ValueError("Generated Day 32 task-row count is incorrect.")
    identities = {(row["scenario_id"], row["day"]) for row in rows}
    if len(identities) != len(rows):
        raise ValueError("A Day 32 scenario/day task appears more than once.")
    if any(row["automatic_execution"] or row["resource_concurrency_approved"] for row in rows):
        raise ValueError("Day 32 accidentally approved task execution or resource concurrency.")


def main():
    config = load_config("configs/day32_review_wave_planning.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    impact_path, impact, graph_path, graph = load_sources(config)
    results = build_wave_results(config, impact, graph)
    rows = flatten_wave_rows(results)
    validate_generated_rows(results, rows)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    report = {
        "task": "day32_review_wave_plan_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day31_impact_report": str(impact_path),
        "source_day30_dependency_graph": str(graph_path),
        "scenario_count": len(results),
        "task_row_count": len(rows),
        "scenarios": results,
        "task_rows": rows,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "resource_concurrency_approved": False,
        "hidden_priority_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, results)
    plot_waves(figure_file, results)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 32 REVIEW-WAVE REPORT ==========")
    print("No ZOS-API connection, optical calculation or task execution was used.")
    print("Waves express dependency readiness only; resource concurrency is not approved.")
    for result in results:
        print(
            f"{result['scenario_id']}: nodes={result['review_node_count']}, "
            f"waves={result['wave_count']}, max width={result['maximum_wave_width']}"
        )
    print()
    print(f"[PASS] Scenarios generated: {len(results)}")
    print(f"[PASS] Explicit task rows generated: {len(rows)}")
    print("[PASS] Every scenario/day appears in exactly one dependency wave")
    print("[PASS] Execution classes retained without automatic execution")
    print("[PASS] Resource-concurrency approval remains false")
    print(f"[PASS] Task CSV: {csv_file}")
    print(f"[PASS] Wave JSON: {json_file}")
    print(f"[PASS] Markdown report: {markdown_file}")
    print(f"[PASS] Wave figure: {figure_file}")


if __name__ == "__main__":
    main()
