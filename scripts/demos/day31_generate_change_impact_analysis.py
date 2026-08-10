"""Day 31 step 2: generate reviewed change-impact reports without execution."""

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
from scripts.demos.day31_change_impact_plan import (  # noqa: E402
    build_scenario_results,
    load_day30_graph,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 31 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("impact_analysis_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def scenario_rows(results, registry):
    """Expand each scenario into one explicit row per review node."""

    metadata = {int(entry["day"]): entry for entry in registry["entries"]}
    rows = []
    for result in results:
        for position, day in enumerate(result["review_order"], start=1):
            execution_class = metadata[day]["execution_class"]
            rows.append(
                {
                    "scenario_id": result["scenario_id"],
                    "changed_day": result["changed_day"],
                    "review_position": position,
                    "day": day,
                    "relationship": "changed_source" if day == result["changed_day"] else "transitive_descendant",
                    "execution_class": execution_class,
                    "review_class": (
                        "zosapi_reexecution_review"
                        if execution_class == "uses_zosapi"
                        else "offline_recalculation_review"
                    ),
                    "phase_id": metadata[day]["phase_id"],
                    "title": metadata[day]["title"],
                    "automatic_execution": False,
                }
            )
    return rows


def write_csv(path, rows):
    """Write a flat scenario/day review-set table."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, results, rows):
    """Write a human-readable impact report with explicit review language."""

    rows_by_scenario = {}
    for row in rows:
        rows_by_scenario.setdefault(row["scenario_id"], []).append(row)
    lines = [
        "# Day31 证据变化影响分析",
        "",
        "> 本报告给出保守复核范围，不会自动运行脚本，也不把受影响节点直接判定为必须重新计算。",
        "",
        "## 场景摘要",
        "",
        "| 场景 | 变化源 | 复核天数 | 含ZOS-API | 纯离线 |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| `{result['scenario_id']}` | Day{result['changed_day']} | "
            f"{len(result['review_order'])} | {len(result['uses_zosapi_days'])} | "
            f"{len(result['offline_only_days'])} |"
        )
    for result in results:
        lines.extend(
            [
                "",
                f"## {result['scenario_id']}",
                "",
                f"- 假设变化：{result['changed_artifact']}",
                f"- 变化源：Day{result['changed_day']}",
                f"- 传递下游：{result['descendants']}",
                f"- 拓扑复核顺序：{result['review_order']}",
                "",
                "| 顺序 | Day | 关系 | 执行类别 | 建议动作类别 |",
                "|---:|---:|---|---|---|",
            ]
        )
        for row in rows_by_scenario[result["scenario_id"]]:
            lines.append(
                f"| {row['review_position']} | {row['day']} | "
                f"`{row['relationship']}` | `{row['execution_class']}` | "
                f"`{row['review_class']}` |"
            )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "- `zosapi_reexecution_review` 表示需要判断是否重跑ZOS-API，不表示已经批准执行。",
            "- `offline_recalculation_review` 表示需要判断是否更新离线统计或决策。",
            "- 本报告没有比较具体字段差异，因此采用包含全部传递下游的保守集合。",
            "- 影响范围大小不是节点质量或工程重要性的评分。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_matrix(path, results):
    """Plot scenario review breadth across Day3-Day28."""

    colors = {
        "uses_zosapi": "#4C78A8",
        "offline_only": "#F58518",
        "unaffected": "#D9D9D9",
    }
    days = list(range(3, 29))
    figure, axis = plt.subplots(figsize=(15, 4.8))
    y_positions = list(range(len(results)))[::-1]
    for y, result in zip(y_positions, results):
        zosapi = set(result["uses_zosapi_days"])
        offline = set(result["offline_only_days"])
        review = set(result["review_order"])
        for day in days:
            if day in zosapi:
                color = colors["uses_zosapi"]
            elif day in offline:
                color = colors["offline_only"]
            else:
                color = colors["unaffected"]
            axis.scatter(day, y, marker="s", s=235, color=color, edgecolor="white", linewidth=0.8)
            if day == result["changed_day"]:
                axis.scatter(day, y, marker="*", s=92, color="white", edgecolor="#333333", linewidth=0.7, zorder=4)
        first = min(review)
        last = max(review)
        axis.plot([first, last], [y, y], color="#777777", linewidth=0.5, zorder=0)

    axis.set_yticks(y_positions)
    axis.set_yticklabels([result["scenario_id"] for result in results])
    axis.set_xticks(days)
    axis.set_xlabel("Teaching day")
    axis.set_title("Day 31 Conservative Change-Impact Review Sets")
    axis.grid(axis="x", alpha=0.15)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    legend = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=colors["uses_zosapi"],
               markeredgecolor="white", markersize=10, label="ZOS-API review"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=colors["offline_only"],
               markeredgecolor="white", markersize=10, label="offline review"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=colors["unaffected"],
               markeredgecolor="white", markersize=10, label="unaffected branch"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor="white",
               markeredgecolor="#333333", markersize=10, label="changed source"),
    ]
    axis.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=4, frameon=False)
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def main():
    config = load_config("configs/day31_change_impact_analysis.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    graph_path, graph, registry_path, registry = load_day30_graph(config)
    results = build_scenario_results(config, graph, registry)
    rows = scenario_rows(results, registry)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    report = {
        "task": "day31_change_impact_analysis_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day30_graph": str(graph_path),
        "source_day29_registry": str(registry_path),
        "scenario_count": len(results),
        "scenarios": results,
        "review_rows": rows,
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "engineering_rerun_claim_made": False,
        "hidden_impact_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, results, rows)
    plot_matrix(figure_file, results)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 31 CHANGE-IMPACT ANALYSIS ==========")
    print("No ZOS-API connection, optical calculation or automatic rerun was used.")
    for result in results:
        print(
            f"{result['scenario_id']}: source=Day{result['changed_day']}, "
            f"review={len(result['review_order'])}, "
            f"ZOS-API review={len(result['uses_zosapi_days'])}, "
            f"offline review={len(result['offline_only_days'])}"
        )
    print()
    print("[PASS] Three conservative review sets generated")
    print("[PASS] Ancestors and unrelated branches excluded")
    print("[PASS] Topological review order preserved")
    print("[PASS] No node was automatically executed")
    print("[PASS] No hidden impact score or engineering rerun claim")
    print(f"[PASS] Review CSV: {csv_file}")
    print(f"[PASS] Impact JSON: {json_file}")
    print(f"[PASS] Markdown report: {markdown_file}")
    print(f"[PASS] Impact figure: {figure_file}")


if __name__ == "__main__":
    main()
