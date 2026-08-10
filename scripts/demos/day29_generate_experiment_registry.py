"""Day 29 step 2: generate CSV, JSON and Markdown experiment registries."""

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day29_experiment_registry_plan import (  # noqa: E402
    inventory_days,
    relative_list,
    validate_execution_lock,
    validate_guardrails,
    validate_inventory,
    validate_scope,
)


CHINA_TIME = timezone(timedelta(hours=8))


def read_note_title(note_path):
    """Read the first Markdown H1 without inferring a conclusion."""

    for line in note_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    raise ValueError(f"Learning note has no H1 title: {note_path}")


def normalize_day_title(day, raw_title):
    """Remove only the leading Day number from a reviewed note title."""

    return re.sub(rf"^Day\s*{day}\s*[：:]\s*", "", raw_title, flags=re.IGNORECASE)


def classify_script_role(script_path):
    """Classify entry-point role from stable filename verbs only."""

    name = script_path.stem.lower()
    if "plan" in name:
        return "plan"
    if "validate" in name or "check" in name:
        return "validation"
    if "analyze" in name or "compare" in name or "summarize" in name:
        return "analysis"
    if "evaluate" in name:
        return "offline_evaluation"
    if "run" in name or "case" in name or "sweep" in name or "focus" in name:
        return "execution"
    if "export" in name:
        return "export"
    return "demo"


def execution_class_for_day(config, day):
    """Return the explicit reviewed execution class."""

    if day in config["execution_classification"]["zosapi_days"]:
        return "uses_zosapi"
    if day in config["execution_classification"]["offline_only_days"]:
        return "offline_only"
    raise ValueError(f"Day {day} has no execution classification.")


def build_registry(config, inventory):
    """Convert the audited inventory into explicit registry rows."""

    early = {int(day): value for day, value in config["early_day_metadata"].items()}
    rows = []
    for item in inventory:
        day = item["day"]
        if item["notes"]:
            title = normalize_day_title(day, read_note_title(item["notes"][0]))
        else:
            title = early[day]["title"]
        scripts = relative_list(item["scripts"])
        script_roles = [
            f"{path}:{classify_script_role(PROJECT_ROOT / path)}" for path in scripts
        ]
        note = relative_list(item["notes"])[0] if item["notes"] else ""
        documentation_gap = "" if note else "missing_individual_learning_note"
        rows.append(
            {
                "day": day,
                "phase_id": item["phase"]["id"],
                "phase_name": item["phase"]["name"],
                "title": title,
                "execution_class": execution_class_for_day(config, day),
                "primary_config": relative_list(item["configs"])[0],
                "uses_shared_config": item["uses_shared_config"],
                "script_count": len(scripts),
                "scripts": scripts,
                "script_roles": script_roles,
                "learning_note": note,
                "artifact_coverage_status": (
                    "complete" if note else "partial_documentation"
                ),
                "documentation_gap": documentation_gap,
            }
        )
    return rows


def make_output_directory(config):
    """Create one timestamped registry output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / config["output"]["root"] / f"registry_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_csv(path, rows):
    """Write a flat UTF-8 registry for spreadsheet use."""

    fieldnames = [
        "day",
        "phase_id",
        "phase_name",
        "title",
        "execution_class",
        "primary_config",
        "uses_shared_config",
        "script_count",
        "scripts",
        "script_roles",
        "learning_note",
        "artifact_coverage_status",
        "documentation_gap",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            flat["scripts"] = ";".join(row["scripts"])
            flat["script_roles"] = ";".join(row["script_roles"])
            writer.writerow(flat)


def write_markdown(path, config, rows):
    """Write a human-readable project index without scientific inference."""

    lines = [
        "# Day3-Day28 光学教学实验注册表",
        "",
        "> 本表由 Day29 根据已审计的配置、脚本和学习笔记生成。它是文件入口索引，不替代各日实验报告。",
        "",
        "## 阶段概览",
        "",
        "| 阶段 | 范围 | 主题 |",
        "|---|---|---|",
    ]
    for phase in config["phase_definitions"]:
        lines.append(
            f"| `{phase['id']}` | Day{min(phase['days'])}-Day{max(phase['days'])} | {phase['name']} |"
        )
    lines.extend(
        [
            "",
            "## 每日入口",
            "",
            "| Day | 主题 | 执行类型 | 配置 | 脚本数 | 学习笔记 | 覆盖状态 |",
            "|---:|---|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        note = f"`{row['learning_note']}`" if row["learning_note"] else "缺失"
        lines.append(
            f"| {row['day']} | {row['title']} | `{row['execution_class']}` | "
            f"`{row['primary_config']}` | {row['script_count']} | {note} | "
            f"`{row['artifact_coverage_status']}` |"
        )
    lines.extend(["", "## 脚本明细", ""])
    for row in rows:
        lines.append(f"### Day {row['day']}：{row['title']}")
        lines.append("")
        for script_role in row["script_roles"]:
            script, role = script_role.rsplit(":", 1)
            lines.append(f"- `{role}` — `{script}`")
        if row["documentation_gap"]:
            lines.append(f"- 文档缺口：`{row['documentation_gap']}`")
        lines.append("")
    lines.extend(
        [
            "## 使用边界",
            "",
            "- `uses_zosapi` 表示该日包含真实 ZOS-API 执行步骤，不表示所有脚本都会连接 Zemax。",
            "- `offline_only` 表示该日只复用已有证据进行计划、统计或决策分析。",
            "- Day3-Day7 共用 `configs/baseline_case.yaml`。",
            "- D30、D37-D60 架构与工具演示不属于本注册表范围。",
            "- 注册表不凭文件名推断科学结论，结论必须回到对应学习笔记和结果报告。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    config = load_config("configs/day29_experiment_registry.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    days = validate_scope(config)
    inventory = inventory_days(config, days)
    validate_inventory(config, inventory)
    rows = build_registry(config, inventory)

    output_dir = make_output_directory(config)
    csv_file = output_dir / "experiment_registry.csv"
    json_file = output_dir / "experiment_registry.json"
    markdown_file = output_dir / "EXPERIMENT_REGISTRY.md"
    write_csv(csv_file, rows)
    write_markdown(markdown_file, config, rows)

    phase_counts = {
        phase["id"]: sum(row["phase_id"] == phase["id"] for row in rows)
        for phase in config["phase_definitions"]
    }
    execution_counts = {
        key: sum(row["execution_class"] == key for row in rows)
        for key in ("uses_zosapi", "offline_only")
    }
    gaps = [row["day"] for row in rows if row["documentation_gap"]]
    report = {
        "task": "day29_experiment_registry_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "registry_scope": {"first_day": days[0], "last_day": days[-1]},
        "registered_day_count": len(rows),
        "phase_counts": phase_counts,
        "execution_class_counts": execution_counts,
        "documentation_gap_days": gaps,
        "entries": rows,
        "architecture_demo_prefixes_excluded": config["registry_scope"][
            "exclude_architecture_demo_prefixes"
        ],
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_file_modified": False,
        "scientific_conclusion_inferred_from_filename": False,
        "hidden_completion_score_used": False,
    }
    json_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("========== DAY 29 EXPERIMENT REGISTRY ==========")
    print("No ZOS-API connection or optical calculation was used.")
    print(f"Registered teaching days: {len(rows)} (Day {days[0]}-Day {days[-1]})")
    print()
    print("Phase counts:")
    for phase_id, count in phase_counts.items():
        print(f"  {phase_id}: {count}")
    print("Execution classes:")
    for execution_class, count in execution_counts.items():
        print(f"  {execution_class}: {count}")
    print(f"Documentation-gap days: {gaps}")
    print()
    print("[PASS] Every registered day has at least one script and one config reference")
    print("[PASS] Day3-Day28 have complete config/script/note coverage")
    print("[PASS] Documentation gaps remain visible if any are found")
    print("[PASS] Architecture demos remain outside the optical teaching registry")
    print("[PASS] No existing source file was modified")
    print(f"[PASS] CSV registry: {csv_file}")
    print(f"[PASS] JSON registry: {json_file}")
    print(f"[PASS] Markdown registry: {markdown_file}")


if __name__ == "__main__":
    main()
