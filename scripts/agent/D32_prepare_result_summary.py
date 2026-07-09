from pathlib import Path
import argparse
import json
import yaml
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "generated" / "config_D31_from_task.yaml"
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts" / "result_summary_prompt.md"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "workflow" / "D32_result_summary_input.md"


def load_yaml(path: Path) -> dict:
    """读取 YAML 文件。"""
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML file is empty: {path}")

    if not isinstance(data, dict):
        raise TypeError("YAML top level must be a dictionary/object.")

    return data


def load_text(path: Path) -> str:
    """读取普通文本文件。"""
    if not path.exists():
        return ""

    with path.open("r", encoding="utf-8") as f:
        return f.read()


def find_files(results_dir: Path) -> dict:
    """在结果目录中查找常见结果文件。"""
    file_groups = {
        "csv_files": [],
        "image_files": [],
        "json_files": [],
        "log_files": [],
        "text_files": []
    }

    if not results_dir.exists():
        return file_groups

    for path in results_dir.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix == ".csv":
            file_groups["csv_files"].append(path)
        elif suffix in [".png", ".jpg", ".jpeg", ".tif", ".tiff"]:
            file_groups["image_files"].append(path)
        elif suffix == ".json":
            file_groups["json_files"].append(path)
        elif suffix == ".log":
            file_groups["log_files"].append(path)
        elif suffix in [".txt", ".md"]:
            file_groups["text_files"].append(path)

    return file_groups


def make_relative(path: Path) -> str:
    """把绝对路径尽量转成相对项目根目录的路径。"""
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def summarize_csv(csv_path: Path, max_rows: int = 8) -> str:
    """读取 CSV 的列名、前几行和简单统计信息。"""
    try:
        df = pd.read_csv(csv_path)

        lines = []
        lines.append(f"### CSV 文件：`{make_relative(csv_path)}`")
        lines.append("")
        lines.append(f"- 行数：{len(df)}")
        lines.append(f"- 列数：{len(df.columns)}")
        lines.append(f"- 列名：{', '.join(str(c) for c in df.columns)}")
        lines.append("")
        lines.append("前几行数据：")
        lines.append("")
        lines.append("```text")
        lines.append(df.head(max_rows).to_string(index=False))
        lines.append("```")
        lines.append("")

        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if numeric_cols:
            lines.append("数值列简单统计：")
            lines.append("")
            lines.append("```text")
            lines.append(df[numeric_cols].describe().to_string())
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return (
            f"### CSV 文件：`{make_relative(csv_path)}`\n\n"
            f"读取失败：{e}\n"
        )


def summarize_json(json_path: Path) -> str:
    """读取 JSON 文件内容，适合 best_design.json。"""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        text = json.dumps(data, ensure_ascii=False, indent=2)

        return (
            f"### JSON 文件：`{make_relative(json_path)}`\n\n"
            "```json\n"
            f"{text}\n"
            "```\n"
        )

    except Exception as e:
        return (
            f"### JSON 文件：`{make_relative(json_path)}`\n\n"
            f"读取失败：{e}\n"
        )


def build_task_summary(config: dict) -> str:
    """根据 D31 生成的 workflow config 写任务摘要。"""
    lines = []

    lines.append("## 1. 任务配置摘要")
    lines.append("")

    task_info = config.get("task_info", {})
    zemax = config.get("zemax", {})
    sweep = config.get("sweep", {})
    analysis = config.get("analysis", {})
    outputs = config.get("outputs", {})
    safety = config.get("safety", {})

    lines.append(f"- 任务来源：{task_info.get('source', '未知')}")
    lines.append(f"- 任务类型：{task_info.get('task_type', '未知')}")
    lines.append(f"- Zemax 模型：{zemax.get('model_file', '未知')}")
    lines.append(f"- 扫描表面：Surface {sweep.get('surface', '未知')}")
    lines.append(f"- 扫描参数：{sweep.get('parameter', '未知')}")
    lines.append(f"- 参数单位：{sweep.get('unit', '未知')}")
    lines.append(
        f"- 扫描范围：{sweep.get('start', '未知')} 到 "
        f"{sweep.get('end', '未知')}，步长 {sweep.get('step', '未知')}"
    )
    lines.append(f"- 预计运行次数：{safety.get('estimated_runs', '未知')}")
    lines.append(f"- 评价指标：{', '.join(analysis.get('metrics', []))}")
    lines.append(f"- 输出内容：{', '.join(outputs.get('items', []))}")
    lines.append(f"- 输出目录：{outputs.get('output_dir', '未知')}")
    lines.append("")

    return "\n".join(lines)


def build_file_list_section(file_groups: dict) -> str:
    """生成结果文件列表。"""
    lines = []
    lines.append("## 2. 结果文件列表")
    lines.append("")

    labels = {
        "csv_files": "CSV 数据文件",
        "image_files": "图像文件",
        "json_files": "JSON 文件",
        "log_files": "日志文件",
        "text_files": "文本文件"
    }

    for key, label in labels.items():
        files = file_groups.get(key, [])
        lines.append(f"### {label}")
        lines.append("")

        if not files:
            lines.append("未找到。")
            lines.append("")
            continue

        for path in files:
            lines.append(f"- `{make_relative(path)}`")

        lines.append("")

    return "\n".join(lines)


def build_csv_section(csv_files: list) -> str:
    """生成 CSV 摘要部分。"""
    lines = []
    lines.append("## 3. CSV 数据摘要")
    lines.append("")

    if not csv_files:
        lines.append("未找到 CSV 文件。AI 不能编造具体趋势或数值。")
        lines.append("")
        return "\n".join(lines)

    for csv_path in csv_files:
        lines.append(summarize_csv(csv_path))

    return "\n".join(lines)


def build_json_section(json_files: list) -> str:
    """生成 JSON 摘要部分。"""
    lines = []
    lines.append("## 4. JSON / best_design 摘要")
    lines.append("")

    if not json_files:
        lines.append("未找到 JSON 文件。")
        lines.append("")
        return "\n".join(lines)

    for json_path in json_files:
        lines.append(summarize_json(json_path))

    return "\n".join(lines)


def build_image_section(image_files: list) -> str:
    """生成图像路径摘要。"""
    lines = []
    lines.append("## 5. 图像文件说明")
    lines.append("")

    if not image_files:
        lines.append("未找到图像文件。")
        lines.append("")
        return "\n".join(lines)

    lines.append("以下是已生成的图像文件路径。")
    lines.append("如果 AI 没有实际查看图像内容，只能说明这些图像可用于展示趋势，不能编造图中细节。")
    lines.append("")

    for path in image_files:
        lines.append(f"- `{make_relative(path)}`")

    lines.append("")

    return "\n".join(lines)


def build_missing_info_section(file_groups: dict) -> str:
    """检查缺失信息。"""
    lines = []
    lines.append("## 6. 缺失信息提醒")
    lines.append("")

    missing = []

    if not file_groups["csv_files"]:
        missing.append("缺少 CSV 文件，无法确认具体数值趋势。")

    if not file_groups["image_files"]:
        missing.append("缺少图像文件，无法展示曲线或优化前后对比。")

    if not file_groups["json_files"]:
        missing.append("缺少 best_design 或其他 JSON 文件，无法确认最优参数。")

    if not file_groups["log_files"]:
        missing.append("缺少日志文件，无法确认运行过程是否有报错。")

    if not missing:
        lines.append("未发现明显缺失文件。")
    else:
        for item in missing:
            lines.append(f"- {item}")

    lines.append("")

    return "\n".join(lines)


def build_report(config: dict, prompt_text: str, file_groups: dict) -> str:
    """生成最终给 AI 的 Markdown 输入材料。"""
    lines = []

    lines.append("# D32 Result Summary Input")
    lines.append("")
    lines.append("下面内容用于交给 AI 生成 Zemax 自动化仿真结果总结。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# A. 总结规则")
    lines.append("")
    lines.append(prompt_text.strip())
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# B. 本次仿真材料")
    lines.append("")
    lines.append(build_task_summary(config))
    lines.append(build_file_list_section(file_groups))
    lines.append(build_csv_section(file_groups["csv_files"]))
    lines.append(build_json_section(file_groups["json_files"]))
    lines.append(build_image_section(file_groups["image_files"]))
    lines.append(build_missing_info_section(file_groups))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="D32: Prepare result summary input for AI."
    )

    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to workflow config generated by D31."
    )

    parser.add_argument(
        "--prompt",
        type=str,
        default=str(DEFAULT_PROMPT_PATH),
        help="Path to result summary prompt file."
    )

    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_REPORT_PATH),
        help="Path to save generated summary input markdown."
    )

    parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Optional results directory. If not provided, read from config outputs.output_dir."
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    prompt_path = Path(args.prompt)
    report_path = Path(args.out)

    try:
        config = load_yaml(config_path)
        prompt_text = load_text(prompt_path)

        if args.results_dir is not None:
            results_dir = Path(args.results_dir)
            if not results_dir.is_absolute():
                results_dir = PROJECT_ROOT / results_dir
        else:
            output_dir = config.get("outputs", {}).get("output_dir")
            if not output_dir:
                raise ValueError("Cannot find outputs.output_dir in config.")
            results_dir = PROJECT_ROOT / output_dir

        file_groups = find_files(results_dir)
        report_text = build_report(config, prompt_text, file_groups)

        report_path.parent.mkdir(parents=True, exist_ok=True)

        with report_path.open("w", encoding="utf-8") as f:
            f.write(report_text)

        print("【OK】 D32 result summary input generated.")
        print(f"Results directory: {results_dir}")
        print(f"Output report: {report_path}")
        print(f"CSV files found: {len(file_groups['csv_files'])}")
        print(f"Image files found: {len(file_groups['image_files'])}")
        print(f"JSON files found: {len(file_groups['json_files'])}")
        print(f"Log files found: {len(file_groups['log_files'])}")

    except Exception as e:
        print("【ERROR】 D32 failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()