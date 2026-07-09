from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import argparse
import json
import subprocess
import sys
import yaml
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TASK_PATH = PROJECT_ROOT / "configs" / "agent_tasks" / "D30_task_example.yaml"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "configs" / "task_schema.json"
DEFAULT_POLICY_PATH = PROJECT_ROOT / "configs" / "safety_policy.yaml"
DEFAULT_NL_REQUEST_PATH = PROJECT_ROOT / "examples" / "tasks" / "D30_natural_language_request.md"
DEFAULT_D31_CONFIG_PATH = PROJECT_ROOT / "configs" / "generated" / "config_D31_from_task.yaml"
DEFAULT_D32_SUMMARY_INPUT_PATH = PROJECT_ROOT / "reports" / "workflow" / "D32_result_summary_input.md"
DEFAULT_D34_REPORT_PATH = PROJECT_ROOT / "reports" / "agent" / "D34_agent_demo_report.md"


sys.path.insert(0, str(PROJECT_ROOT))

from modules.task_safety import load_yaml, run_all_safety_checks


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    """Load a text file. Return empty string if it does not exist."""
    if not path.exists():
        return ""

    with path.open("r", encoding="utf-8") as f:
        return f.read()


def make_relative(path: Path) -> str:
    """Convert an absolute path to a project-relative path when possible."""
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def validate_with_schema(task: dict, schema: dict) -> list:
    """Validate AI-generated YAML task with JSON Schema."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(task), key=lambda e: e.path)
    return errors


def format_schema_errors(errors: list) -> str:
    """Format schema errors into readable markdown text."""
    if not errors:
        return "通过。"

    lines = []

    for error in errors:
        field_path = ".".join(str(x) for x in error.path)
        field_path = field_path if field_path else "<root>"
        lines.append(f"- 字段 `{field_path}`：{error.message}")

    return "\n".join(lines)


def run_python_script(script_path: Path, extra_args: Optional[List[str]] = None) -> Dict:
    """
    Run a Python script and capture stdout/stderr.

    This function is used to call D31 and D32 scripts.
    """
    if extra_args is None:
        extra_args = []

    command = [
        sys.executable,
        str(script_path)
    ] + extra_args

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def build_task_overview(task: dict) -> str:
    """Build a short task overview for the demo report."""
    target = task.get("target", {})
    safety = task.get("safety", {})

    lines = []

    lines.append("## 2. YAML 任务摘要")
    lines.append("")
    lines.append(f"- 软件：{task.get('software', '未知')}")
    lines.append(f"- 任务类型：{task.get('task_type', '未知')}")
    lines.append(f"- 模型文件：`{task.get('model_file', '未知')}`")
    lines.append(f"- 扫描表面：Surface {target.get('surface', '未知')}")
    lines.append(f"- 扫描参数：{target.get('parameter', '未知')}")
    lines.append(f"- 单位：{target.get('unit', '未知')}")
    lines.append(
        f"- 扫描范围：{target.get('start', '未知')} 到 "
        f"{target.get('end', '未知')}，步长 {target.get('step', '未知')}"
    )
    lines.append(f"- 输出目录：`{safety.get('output_dir', '未知')}`")
    lines.append(f"- 最大运行次数：{safety.get('max_runs', '未知')}")
    lines.append(f"- 原始模型只读：{safety.get('read_only_original_model', '未知')}")
    lines.append(f"- 先 dry-run：{safety.get('dry_run_first', '未知')}")
    lines.append("")

    return "\n".join(lines)


def build_command_section(title: str, result: dict) -> str:
    """Build a markdown section for a subprocess result."""
    lines = []

    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"- 返回码：`{result['returncode']}`")
    lines.append("")
    lines.append("命令：")
    lines.append("")
    lines.append("```text")
    lines.append(result["command"])
    lines.append("```")
    lines.append("")

    lines.append("标准输出：")
    lines.append("")
    lines.append("```text")
    lines.append(result["stdout"].strip() if result["stdout"].strip() else "无")
    lines.append("```")
    lines.append("")

    lines.append("错误输出：")
    lines.append("")
    lines.append("```text")
    lines.append(result["stderr"].strip() if result["stderr"].strip() else "无")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def build_demo_report(
    natural_language_request: str,
    task: dict,
    schema_errors: list,
    safety_errors: list,
    d31_result: Optional[Dict],
    d32_result: Optional[Dict],
    output_path: Path
) -> str:
    """Build the D34 demo report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []

    lines.append("# D34 Agent Demo Report")
    lines.append("")
    lines.append(f"生成时间：{now}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Demo 目标")
    lines.append("")
    lines.append(
        "本 demo 用于展示低配版 AI Agent 工作流："
        "自然语言需求 → YAML 任务 → Schema 校验 → Safety 校验 → "
        "D31 工作流配置生成 → D32 结果总结材料生成。"
    )
    lines.append("")
    lines.append("本 demo 默认不直接运行 Zemax，不修改原始模型。")
    lines.append("")

    lines.append("### 自然语言需求")
    lines.append("")
    if natural_language_request.strip():
        lines.append("```markdown")
        lines.append(natural_language_request.strip())
        lines.append("```")
    else:
        lines.append("未找到自然语言需求文件。")
    lines.append("")

    lines.append(build_task_overview(task))

    lines.append("## 3. Schema 校验结果")
    lines.append("")
    lines.append(format_schema_errors(schema_errors))
    lines.append("")

    lines.append("## 4. Safety Policy 校验结果")
    lines.append("")
    if safety_errors:
        for error in safety_errors:
            lines.append(f"- {error}")
    else:
        lines.append("通过。")
    lines.append("")

    if d31_result is not None:
        lines.append(build_command_section("5. D31：YAML 任务转 workflow config", d31_result))

    if d32_result is not None:
        lines.append(build_command_section("6. D32：生成结果总结输入材料", d32_result))

    lines.append("## 7. Demo 产物")
    lines.append("")
    artifacts = [
        DEFAULT_TASK_PATH,
        DEFAULT_D31_CONFIG_PATH,
        DEFAULT_D32_SUMMARY_INPUT_PATH,
        output_path
    ]

    for item in artifacts:
        status = "存在" if item.exists() else "未生成"
        lines.append(f"- `{make_relative(item)}`：{status}")

    lines.append("")
    lines.append("## 8. 当前局限")
    lines.append("")
    lines.append(
        "当前 demo 只演示 Agent 工作流骨架。由于尚未运行真实 Zemax 参数扫描，"
        "结果目录中可能缺少 CSV、图像、best_design 和日志文件，因此 D32 只能生成缺失信息型总结。"
    )
    lines.append("")
    lines.append("## 9. 下一步")
    lines.append("")
    lines.append(
        "下一步可以在 D35 周复盘中整理 README，并在后续 Project-X 中扩展函数库、"
        "多参数 YAML、更多分析指标和真实 Zemax 执行能力。"
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="D34: Low-code AI Agent demo for Zemax automation workflow."
    )

    parser.add_argument(
        "--task",
        type=str,
        default=str(DEFAULT_TASK_PATH),
        help="Path to AI-generated YAML task."
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to JSON Schema file."
    )

    parser.add_argument(
        "--policy",
        type=str,
        default=str(DEFAULT_POLICY_PATH),
        help="Path to safety policy YAML."
    )

    parser.add_argument(
        "--nl-request",
        type=str,
        default=str(DEFAULT_NL_REQUEST_PATH),
        help="Path to natural language request markdown."
    )

    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_D34_REPORT_PATH),
        help="Path to save D34 demo report."
    )

    args = parser.parse_args()

    task_path = Path(args.task)
    schema_path = Path(args.schema)
    policy_path = Path(args.policy)
    nl_request_path = Path(args.nl_request)
    report_path = Path(args.out)

    try:
        task = load_yaml(task_path)
        schema = load_json(schema_path)
        policy = load_yaml(policy_path)
        natural_language_request = load_text(nl_request_path)

        print("=" * 70)
        print("D34 Agent Demo")
        print("=" * 70)
        print("Step 1: Load natural language request and YAML task.")

        schema_errors = validate_with_schema(task, schema)

        if schema_errors:
            print("【ERROR】 Step 2 failed: Schema validation failed.")
            print(format_schema_errors(schema_errors))
            safety_errors = []
            d31_result = None
            d32_result = None
        else:
            print("【OK】 Step 2 passed: Schema validation.")

            safety_errors = run_all_safety_checks(
                task=task,
                policy=policy,
                project_root=PROJECT_ROOT
            )

            if safety_errors:
                print("【ERROR】 Step 3 failed: Safety policy validation failed.")
                for error in safety_errors:
                    print(f"- {error}")
                d31_result = None
                d32_result = None
            else:
                print("【OK】 Step 3 passed: Safety policy validation.")

                print("Step 4: Run D31 to generate workflow config.")
                d31_result = run_python_script(
                    PROJECT_ROOT / "scripts" / "agent" / "D31_run_from_task_yaml.py",
                    extra_args=[
                        "--task",
                        str(task_path),
                        "--schema",
                        str(schema_path),
                        "--out-config",
                        str(DEFAULT_D31_CONFIG_PATH)
                    ]
                )

                if d31_result["returncode"] != 0:
                    print("【ERROR】 Step 4 failed: D31 script returned non-zero code.")
                    d32_result = None
                else:
                    print("【OK】 Step 4 passed: D31 workflow config generated.")

                    print("Step 5: Run D32 to generate result summary input.")
                    d32_result = run_python_script(
                        PROJECT_ROOT / "scripts" / "D32_prepare_result_summary.py",
                        extra_args=[
                            "--config",
                            str(DEFAULT_D31_CONFIG_PATH),
                            "--out",
                            str(DEFAULT_D32_SUMMARY_INPUT_PATH)
                        ]
                    )

                    if d32_result["returncode"] != 0:
                        print("【ERROR】 Step 5 failed: D32 script returned non-zero code.")
                    else:
                        print("【OK】 Step 5 passed: D32 summary input generated.")

        report_text = build_demo_report(
            natural_language_request=natural_language_request,
            task=task,
            schema_errors=schema_errors,
            safety_errors=safety_errors,
            d31_result=d31_result,
            d32_result=d32_result,
            output_path=report_path
        )

        report_path.parent.mkdir(parents=True, exist_ok=True)

        with report_path.open("w", encoding="utf-8") as f:
            f.write(report_text)

        print("=" * 70)
        print("【OK】 D34 demo report generated.")
        print(f"Report path: {report_path}")
        print("=" * 70)

    except Exception as e:
        print("【ERROR】 D34 demo failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()