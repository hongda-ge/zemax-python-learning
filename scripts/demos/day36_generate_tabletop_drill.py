"""Day 36 step 2: generate the maintenance tabletop drill reports."""

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
from scripts.demos.day36_maintenance_tabletop_plan import (  # noqa: E402
    build_tabletop_plan,
    find_failure_drill,
    find_impact_scenario,
    find_schedule_scenario,
    load_runbook_and_sources,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 36 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("tabletop_drill_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def checkpoint_rows(plan):
    """Flatten both simulated checkpoint routes into CSV rows."""

    rows = []
    for route_name in ("normal_route", "failure_route"):
        route = plan[route_name]
        for state in route["checkpoint_states"]:
            rows.append(
                {
                    "route": route_name,
                    "route_id": route["route_id"],
                    "checkpoint_order": state["order"],
                    "checkpoint_id": state["checkpoint_id"],
                    "simulated_status": state["simulated_status"],
                    "manual_decision_required": state["manual_decision_required"],
                    "actually_executed": False,
                    "real_result_observed": False,
                }
            )
    return rows


def write_csv(path, rows):
    """Write two explicit checkpoint routes."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, runbook_path, plan, rows):
    """Write a readable distinction between process and evidence-node states."""

    rows_by_route = {}
    for row in rows:
        rows_by_route.setdefault(row["route"], []).append(row)
    lines = [
        "# Day36 项目维护桌面推演",
        "",
        "> 本报告的全部状态均为 `SIMULATED_*`。没有连接 ZOS-API、没有执行历史实验，也没有观察到真实 PASS 或 FAIL。",
        "",
        "## 1. 推演输入",
        "",
        f"- Day35 手册：`{runbook_path}`",
        f"- 假想变化源：Day{plan['changed_day']} 教学定位误差预算",
        f"- 保守复核集合：{plan['review_days']}",
        "- 人工决策门：CP06、CP09、CP10",
        "",
        "## 2. 资源槽",
        "",
        "| 资源槽 | 计划复核 Day |",
        "|---:|---|",
    ]
    for slot in plan["resource_slots"]:
        lines.append(f"| {slot['slot']} | {slot['days']} |")
    lines.extend(
        [
            "",
            "## 3. 正常路线",
            "",
            f"最终状态：`{plan['normal_route']['final_status']}`。这表示流程结构可以走完，不表示真实实验通过。",
            "",
            "| 顺序 | 检查点 | 模拟状态 | 人工决定 | 实际执行 |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in rows_by_route["normal_route"]:
        lines.append(
            f"| {row['checkpoint_order']} | `{row['checkpoint_id']}` | "
            f"`{row['simulated_status']}` | "
            f"{'是' if row['manual_decision_required'] else '否'} | 否 |"
        )
    lines.extend(
        [
            "",
            "## 4. Day23 失败路线",
            "",
            f"- 假想失败：Day{plan['failure_route']['failed_day']}，Slot {plan['failure_route']['failed_slot']}；",
            f"- 假想通过节点：{plan['failure_route']['pass_days']}；",
            f"- 锁定节点：{plan['failure_route']['blocked_days']}；",
            f"- 可独立复核节点：{plan['failure_route']['reviewable_days']}；",
            f"- 最终状态：`{plan['failure_route']['final_status']}`。",
            "",
            "| 顺序 | 检查点 | 模拟状态 | 人工决定 | 实际执行 |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in rows_by_route["failure_route"]:
        lines.append(
            f"| {row['checkpoint_order']} | `{row['checkpoint_id']}` | "
            f"`{row['simulated_status']}` | "
            f"{'是' if row['manual_decision_required'] else '否'} | 否 |"
        )
    lines.extend(
        [
            "",
            "## 5. 流程状态与节点状态不能混淆",
            "",
            "CP09 的 `SIMULATED_FAIL` 表示槽后审批未通过；Day23 是假想失败证据节点；Day24-Day28 是因此被锁定的下游。检查点和实验节点属于两个不同层次。",
            "",
            "## 6. 恢复要求",
            "",
            "失败路线停在 CP10 的 `SIMULATED_NOT_APPROVED`。只有修复 Day23、验证新证据指纹、重新计算影响范围和资源槽，并获得人工批准，才允许恢复 Day24-Day28。",
            "",
            "## 7. 推演结论",
            "",
            "Day35 手册能够完整表达正常通过和中途失败两条路线；人工门未被跳过；失败下游未被提前释放；所有状态都保留模拟标识。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_route(axis, states, title, colors):
    """Plot one ten-checkpoint simulated route."""

    axis.plot(range(1, 11), [0] * 10, color="#BBBBBB", linewidth=2, zorder=1)
    for state in states:
        order = int(state["order"])
        status = state["simulated_status"]
        axis.scatter(order, 0, s=600, color=colors[status], edgecolor="white", linewidth=1.4, zorder=3)
        axis.text(order, 0, f"CP{order:02d}", ha="center", va="center", color="white", fontsize=8.5)
        if state["manual_decision_required"]:
            axis.text(order, 0.38, "MANUAL", ha="center", va="center", fontsize=7.5,
                      color="#7A5195", fontweight="bold")
    axis.set_xlim(0.5, 10.5)
    axis.set_ylim(-0.7, 0.7)
    axis.set_xticks(range(1, 11))
    axis.set_xlabel("Day 35 checkpoint order")
    axis.set_yticks([])
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.set_title(title)


def plot_drill(path, plan):
    """Plot normal/failure checkpoints and the failed evidence-node schedule."""

    colors = {
        "SIMULATED_PASS": "#54A24B",
        "SIMULATED_FAIL": "#E45756",
        "SIMULATED_NOT_APPROVED": "#9D9D9D",
    }
    figure, axes = plt.subplots(3, 1, figsize=(15, 9))
    plot_route(
        axes[0], plan["normal_route"]["checkpoint_states"],
        "Normal route: all ten gates simulated PASS", colors,
    )
    plot_route(
        axes[1], plan["failure_route"]["checkpoint_states"],
        "Failure route: CP09 simulated FAIL, CP10 recovery not approved", colors,
    )

    node_colors = {22: "#54A24B", 23: "#E45756"}
    blocked = set(plan["failure_route"]["blocked_days"])
    for slot in plan["resource_slots"]:
        for index, day in enumerate(slot["days"]):
            y = index - (len(slot["days"]) - 1) / 2
            color = node_colors.get(day, "#9D9D9D" if day in blocked else "#4C78A8")
            axes[2].scatter(slot["slot"], y, s=600, color=color, edgecolor="white", linewidth=1.4)
            axes[2].text(slot["slot"], y, f"D{day}", ha="center", va="center", color="white", fontsize=9)
    axes[2].axvline(2.5, color="#E45756", linestyle="--", linewidth=1)
    axes[2].set_xlim(0.5, 6.5)
    axes[2].set_ylim(-1, 1)
    axes[2].set_xticks(range(1, 7))
    axes[2].set_xlabel("Day 33 resource slot")
    axes[2].set_yticks([])
    axes[2].spines[["top", "right", "left"]].set_visible(False)
    axes[2].set_title("Failure-route evidence nodes: D22 pass, D23 fail, D24-D28 blocked")

    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
               markeredgecolor="white", markersize=10, label=status)
        for status, color in colors.items()
    ]
    figure.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=3, frameon=False)
    figure.suptitle("Day 36 Maintenance Tabletop Drill\n(all states simulated; no task executed)", fontsize=15)
    figure.tight_layout(rect=(0, 0.06, 1, 0.94))
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def validate_rows(plan, rows):
    """Recheck complete routes, labels and execution boundaries."""

    if len(rows) != 20:
        raise ValueError("Day 36 must generate exactly twenty checkpoint rows.")
    identities = {(row["route"], row["checkpoint_id"]) for row in rows}
    if len(identities) != 20:
        raise ValueError("A Day 36 route/checkpoint appears more than once.")
    if any(not row["simulated_status"].startswith("SIMULATED_") for row in rows):
        raise ValueError("A Day 36 CSV state lacks the SIMULATED label.")
    if any(row["actually_executed"] or row["real_result_observed"] for row in rows):
        raise ValueError("Day 36 accidentally claimed execution or a real result.")
    manual_by_route = {
        route: {row["checkpoint_id"] for row in rows if row["route"] == route and row["manual_decision_required"]}
        for route in ("normal_route", "failure_route")
    }
    expected_manual = {"CP06_scope_approval", "CP09_slot_gate", "CP10_failure_recovery"}
    if any(value != expected_manual for value in manual_by_route.values()):
        raise ValueError("Day 36 manual decision gates changed.")
    if plan["failure_route"]["blocked_days"] != [24, 25, 26, 27, 28]:
        raise ValueError("Day 36 failure-route blocked nodes changed.")


def main():
    config = load_config("configs/day36_maintenance_tabletop_drill.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    runbook_path, runbook, reports = load_runbook_and_sources(config)
    impact = find_impact_scenario(config, reports)
    schedule = find_schedule_scenario(config, reports)
    failure = find_failure_drill(config, reports)
    plan = build_tabletop_plan(config, runbook, impact, schedule, failure)
    rows = checkpoint_rows(plan)
    validate_rows(plan, rows)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    report = {
        "task": "day36_maintenance_tabletop_drill_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_day35_runbook": str(runbook_path),
        "scenario_id": config["drill_scenario"]["id"],
        "all_states_simulated": True,
        "checkpoint_row_count": len(rows),
        "plan": plan,
        "checkpoint_rows": rows,
        "automatic_execution_performed": False,
        "real_result_observed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "engineering_approval_claim_made": False,
        "hidden_readiness_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, runbook_path, plan, rows)
    plot_drill(figure_file, plan)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 36 MAINTENANCE TABLETOP DRILL ==========")
    print("No ZOS-API connection, optical calculation or historical task execution was used.")
    print("All route and evidence-node states are simulated.")
    print("Normal route: CP01-CP10 -> SIMULATED_COMPLETE")
    print("Failure route: Day23/CP09 -> SIMULATED_FAIL")
    print("  Day22: simulated pass")
    print("  Day24-Day28: blocked")
    print("  CP10: SIMULATED_NOT_APPROVED")
    print()
    print(f"[PASS] Explicit checkpoint rows: {len(rows)} (10 per route)")
    print("[PASS] Day31 scope, Day33 slots and Day34 failure partition reproduced")
    print("[PASS] CP06, CP09 and CP10 remain manual gates in both routes")
    print("[PASS] No actual execution, real result or engineering approval claim")
    print(f"[PASS] Checkpoint CSV: {csv_file}")
    print(f"[PASS] Drill JSON: {json_file}")
    print(f"[PASS] Markdown report: {markdown_file}")
    print(f"[PASS] Route figure: {figure_file}")


if __name__ == "__main__":
    main()
