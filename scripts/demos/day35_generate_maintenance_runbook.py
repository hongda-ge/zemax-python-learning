"""Day 35 step 2: generate the audited project maintenance runbook."""

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day35_maintenance_runbook_plan import (  # noqa: E402
    load_and_validate_sources,
    validate_checkpoints,
    validate_execution_lock,
    validate_policies,
)


CHINA_TIME = timezone(timedelta(hours=8))


def make_output_dir(config):
    """Create one timestamped Day 35 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("maintenance_runbook_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def checkpoint_rows(checkpoints):
    """Create explicit auditable checkpoint rows."""

    rows = []
    for order, checkpoint in enumerate(checkpoints, start=1):
        rows.append(
            {
                "order": order,
                "checkpoint_id": checkpoint["id"],
                "stage": checkpoint["stage"],
                "title": checkpoint["title"],
                "evidence_role": checkpoint["evidence_role"],
                "pass_condition": checkpoint["pass_condition"],
                "fail_action": checkpoint["fail_action"],
                "manual_decision_required": checkpoint["stage"] in {
                    "approval", "execution_gate", "recovery"
                },
                "automatic_execution": False,
            }
        )
    return rows


def write_csv(path, rows):
    """Write the maintenance checkpoint table."""

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, sources, rows):
    """Write the complete operator-facing maintenance runbook."""

    lines = [
        "# 项目维护运行手册（Day35）",
        "",
        "> 适用范围：本项目 Day3-Day28 教学实验的证据维护。手册提供复核顺序与安全门，不自动执行 ZOS-API 或离线科学任务，也不构成工程批准。",
        "",
        "## 1. 什么时候使用本手册",
        "",
        "出现以下任一情况时进入维护流程：模型、配置、分析配方、结果报告、教学阈值或依赖关系发生变化；已有报告 SHA256 不再匹配；某次复核无法复现；准备在新电脑或新版本 OpticStudio 上重建证据。",
        "",
        "## 2. 冻结维护证据",
        "",
        "| Day | 角色 | 文件 | SHA256 |",
        "|---:|---|---|---|",
    ]
    for source in sources:
        lines.append(
            f"| {source['day']} | `{source['role']}` | `{source['path']}` | "
            f"`{source['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## 3. 十个维护检查点",
            "",
            "任何检查点 FAIL 时，立即执行对应停止动作；未经人工批准，不得跳过检查点。",
            "",
            "| 顺序 | 检查点 | 阶段 | 操作 | 通过条件 | 失败动作 | 人工决定 |",
            "|---:|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['order']} | `{row['checkpoint_id']}` | `{row['stage']}` | "
            f"{row['title']} | {row['pass_condition']} | {row['fail_action']} | "
            f"{'是' if row['manual_decision_required'] else '否'} |"
        )
    lines.extend(
        [
            "",
            "## 4. 标准维护操作流程",
            "",
            "1. 记录变化的文件、原因、操作者和时间，不先运行任何实验。",
            "2. 在 Day29 注册表中定位对应 Day、配置、脚本与学习笔记。",
            "3. 验证所引用报告的 SHA256；不匹配时停止解释旧结果。",
            "4. 使用 Day30 图追踪直接和传递下游。",
            "5. 使用 Day31 形成保守复核集合，并由维护者批准实际范围。",
            "6. 使用 Day32 把批准集合转换为依赖安全波次。",
            "7. 使用 Day33 应用单 ZOS-API、双离线通道的教学容量。",
            "8. 每个资源槽结束后检查状态、输出、指纹和连接关闭证据。",
            "9. 全部通过才释放依赖它的下一槽；失败则进入 Day34 分区。",
            "10. 修复 FAIL 上游、重验指纹、重算影响范围并人工批准后，才能恢复 BLOCKED 节点。",
            "",
            "## 5. 状态与动作",
            "",
            "| 状态 | 含义 | 允许动作 |",
            "|---|---|---|",
            "| PASS | 本次复核证据可信 | 可释放依赖它的后续任务 |",
            "| FAIL | 当前节点复核失败 | 停止其下游并调查原因 |",
            "| BLOCKED | 依赖失败证据 | 禁止执行，等待上游修复 |",
            "| REVIEWABLE | 不依赖失败证据 | 人工批准后可重新排程 |",
            "",
            "## 6. 恢复条件",
            "",
            "BLOCKED 节点不能直接改成 PASS。必须先修复 FAIL 节点，重新生成可信证据，验证新指纹，重新执行影响分析和资源排程，并由维护者批准恢复范围。",
            "",
            "## 7. 禁止事项",
            "",
            "- 禁止用 `git add -A` 混入无关运行结果；",
            "- 禁止在来源指纹不匹配时沿用旧结论；",
            "- 禁止把受影响节点直接等同于必须自动重跑；",
            "- 禁止同时安排多个 ZOS-API 教学任务；",
            "- 禁止未经人工审批释放后续槽；",
            "- 禁止把本手册称为最终工程验收流程。",
            "",
            "## 8. 本次生成状态",
            "",
            "本手册由六份冻结审计报告离线生成；未连接 ZOS-API、未计算新光学指标、未执行历史实验、未修改原始模型。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_runbook(path, rows):
    """Draw a compact ten-checkpoint maintenance flow with a failure branch."""

    stage_colors = {
        "intake": "#72B7B2",
        "provenance": "#59A14F",
        "scope": "#4C78A8",
        "approval": "#B279A2",
        "ordering": "#F28E2B",
        "scheduling": "#EDC948",
        "execution_gate": "#E15759",
        "recovery": "#9D755D",
    }
    short_titles = {
        "CP01_change_intake": "Record\nchange",
        "CP02_registry_lookup": "Find\nassets",
        "CP03_fingerprint_gate": "Verify\nSHA256",
        "CP04_dependency_trace": "Trace\ndependencies",
        "CP05_impact_scope": "Build\nreview set",
        "CP06_scope_approval": "Approve\nscope",
        "CP07_dependency_waves": "Create\nwaves",
        "CP08_resource_schedule": "Apply\ncapacity",
        "CP09_slot_gate": "Review\neach slot",
        "CP10_failure_recovery": "Isolate &\nrecover",
    }
    positions = {}
    for index, row in enumerate(rows):
        if index < 5:
            positions[row["checkpoint_id"]] = (1 + index * 2.1, 3.2)
        else:
            positions[row["checkpoint_id"]] = (1 + (9 - index) * 2.1, 1.2)

    figure, axis = plt.subplots(figsize=(15.5, 6.5))
    axis.set_xlim(0, 11)
    axis.set_ylim(-0.2, 4.5)
    axis.axis("off")

    ordered_ids = [row["checkpoint_id"] for row in rows]
    for first, second in zip(ordered_ids, ordered_ids[1:]):
        x1, y1 = positions[first]
        x2, y2 = positions[second]
        arrow = FancyArrowPatch(
            (x1 + (0.8 if y1 == y2 and x2 > x1 else -0.8 if y1 == y2 else 0), y1),
            (x2 - (0.8 if y1 == y2 and x2 > x1 else -0.8 if y1 == y2 else 0), y2),
            arrowstyle="-|>", mutation_scale=13, linewidth=1.4, color="#555555",
            connectionstyle="arc3,rad=0" if y1 == y2 else "arc3,rad=-0.15",
        )
        axis.add_patch(arrow)

    for row in rows:
        x, y = positions[row["checkpoint_id"]]
        box = FancyBboxPatch(
            (x - 0.82, y - 0.42), 1.64, 0.84,
            boxstyle="round,pad=0.06,rounding_size=0.08",
            facecolor=stage_colors[row["stage"]], edgecolor="white", linewidth=1.2,
        )
        axis.add_patch(box)
        axis.text(x, y + 0.10, row["checkpoint_id"].split("_")[0], ha="center", va="center",
                  color="white", fontsize=10, fontweight="bold")
        axis.text(
            x, y - 0.16, short_titles[row["checkpoint_id"]],
            ha="center", va="center", color="white", fontsize=8,
        )

    cp09 = positions["CP09_slot_gate"]
    cp10 = positions["CP10_failure_recovery"]
    axis.text(cp09[0], cp09[1] - 0.72, "FAIL -> isolate descendants", ha="center",
              color="#E15759", fontsize=9, fontweight="bold")
    axis.text(cp10[0], cp10[1] - 0.72, "repair + revalidate + approve", ha="center",
              color="#9D755D", fontsize=9, fontweight="bold")
    axis.text(5.5, 4.15, "Day 35 Evidence-Driven Project Maintenance Runbook", ha="center",
              fontsize=17, fontweight="bold")
    axis.text(5.5, 3.75, "10 gated checkpoints | no automatic scientific rerun", ha="center",
              fontsize=11, color="#555555")
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def validate_rows(sources, rows):
    """Recheck checkpoint safety and complete evidence usage."""

    if len(rows) != 10:
        raise ValueError("Generated Day 35 checkpoint-row count is incorrect.")
    if len({row["checkpoint_id"] for row in rows}) != len(rows):
        raise ValueError("A Day 35 checkpoint appears more than once.")
    if {row["evidence_role"] for row in rows} != {source["role"] for source in sources}:
        raise ValueError("Generated Day 35 rows lost an evidence role.")
    if any(row["automatic_execution"] for row in rows):
        raise ValueError("Day 35 accidentally enabled automatic execution.")
    manual_ids = {row["checkpoint_id"] for row in rows if row["manual_decision_required"]}
    if manual_ids != {"CP06_scope_approval", "CP09_slot_gate", "CP10_failure_recovery"}:
        raise ValueError("Day 35 manual decision checkpoints changed.")


def main():
    config = load_config("configs/day35_maintenance_runbook.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    sources = load_and_validate_sources(config)
    checkpoints = validate_checkpoints(config, sources)
    rows = checkpoint_rows(checkpoints)
    validate_rows(sources, rows)

    output_dir = make_output_dir(config)
    names = config["planned_outputs_after_approval"]
    json_file = output_dir / names["json"]
    csv_file = output_dir / names["csv"]
    markdown_file = output_dir / names["markdown"]
    figure_file = output_dir / names["figure"]

    source_manifest = [
        {
            "day": source["day"],
            "role": source["role"],
            "path": str(source["path"]),
            "sha256": source["sha256"],
            "verified": True,
        }
        for source in sources
    ]
    report = {
        "task": "day35_maintenance_runbook_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_count": len(source_manifest),
        "checkpoint_count": len(rows),
        "sources": source_manifest,
        "checkpoints": rows,
        "manual_decision_checkpoint_ids": [
            row["checkpoint_id"] for row in rows if row["manual_decision_required"]
        ],
        "automatic_execution_performed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_scientific_source_modified": False,
        "engineering_approval_claim_made": False,
        "hidden_completion_score_used": False,
    }
    write_csv(csv_file, rows)
    write_markdown(markdown_file, source_manifest, rows)
    plot_runbook(figure_file, rows)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========== DAY 35 PROJECT MAINTENANCE RUNBOOK ==========")
    print("No ZOS-API connection, optical calculation or historical task execution was used.")
    print("The runbook is a teaching maintenance control, not an engineering approval.")
    print(f"Verified frozen sources: {len(source_manifest)} (Day29-Day34)")
    print(f"Maintenance checkpoints: {len(rows)}")
    print("Manual decision gates: CP06, CP09, CP10")
    print()
    print("[PASS] All six source fingerprints and metadata verified")
    print("[PASS] Intake, provenance, scope, ordering, scheduling, gate and recovery covered")
    print("[PASS] Every evidence role used by at least one checkpoint")
    print("[PASS] Automatic execution and engineering approval claims remain false")
    print(f"[PASS] Checkpoint CSV: {csv_file}")
    print(f"[PASS] Runbook JSON: {json_file}")
    print(f"[PASS] Maintenance manual: {markdown_file}")
    print(f"[PASS] Runbook figure: {figure_file}")


if __name__ == "__main__":
    main()
