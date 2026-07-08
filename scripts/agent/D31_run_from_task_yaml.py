from pathlib import Path
import argparse
import json
import yaml
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "configs" / "task_schema.json"
DEFAULT_TASK_PATH = PROJECT_ROOT / "examples" / "D30_task_example.yaml"
DEFAULT_OUTPUT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config_D31_from_task.yaml"


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    """Safely load a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML file is empty: {path}")

    if not isinstance(data, dict):
        raise TypeError("The YAML task must be a dictionary/object at the top level.")

    return data


def save_yaml(data: dict, path: Path) -> None:
    """Save a dictionary as a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False
        )


def validate_task_with_schema(task: dict, schema: dict) -> list:
    """Validate task using JSON Schema."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(task), key=lambda e: e.path)
    return errors


def estimate_values(start: float, end: float, step: float) -> list:
    """Generate sweep values while avoiding floating point display noise."""
    if step <= 0:
        raise ValueError("Step must be greater than 0.")

    if end < start:
        raise ValueError("End value must be greater than or equal to start value.")

    values = []
    current = start

    # 加一个很小的容差，避免 0.2 这种小数导致最后一个点丢失
    eps = abs(step) * 1e-9

    while current <= end + eps:
        values.append(round(current, 10))
        current += step

    return values


def extra_safety_check(task: dict) -> list:
    """Return a list of safety warnings/errors."""
    messages = []

    target = task["target"]
    safety = task["safety"]

    values = estimate_values(
        target["start"],
        target["end"],
        target["step"]
    )

    run_count = len(values)
    max_runs = safety["max_runs"]

    if run_count > max_runs:
        messages.append(
            f"Too many runs: {run_count}. Current max_runs is {max_runs}."
        )

    output_dir = safety["output_dir"]
    if not output_dir.startswith("results/"):
        messages.append("Output directory must be inside results/.")

    if safety["read_only_original_model"] is not True:
        messages.append("Original model must be read-only.")

    if safety["dry_run_first"] is not True:
        messages.append("AI-generated task must use dry_run_first: true.")

    return messages


def print_schema_errors(errors: list) -> None:
    """Print JSON Schema validation errors."""
    print("【ERROR】 Task failed JSON Schema validation.")
    print("-" * 70)

    for error in errors:
        field_path = ".".join(str(x) for x in error.path)
        field_path = field_path if field_path else "<root>"
        print(f"Field: {field_path}")
        print(f"Reason: {error.message}")
        print("-" * 70)


def print_task_preview(task: dict) -> None:
    """Print a dry-run preview of the task."""
    target = task["target"]
    safety = task["safety"]

    values = estimate_values(
        target["start"],
        target["end"],
        target["step"]
    )

    print("【OK】 Task passed validation.")
    print("=" * 70)
    print("D31 Dry-run Preview")
    print("=" * 70)
    print(f"Software: {task['software']}")
    print(f"Task type: {task['task_type']}")
    print(f"Model file: {task['model_file']}")
    print(
        "Target: "
        f"surface {target['surface']} / "
        f"{target['parameter']} / "
        f"{target['unit']}"
    )
    print(
        "Sweep range: "
        f"{target['start']} to {target['end']}, "
        f"step = {target['step']}"
    )
    print(f"Estimated run count: {len(values)}")
    print(f"Sweep values: {values}")
    print(f"Metrics: {', '.join(task['metrics'])}")
    print(f"Outputs: {', '.join(task['outputs'])}")
    print(f"Output directory: {safety['output_dir']}")
    print(f"Read-only original model: {safety['read_only_original_model']}")
    print(f"Dry-run first: {safety['dry_run_first']}")
    print("=" * 70)


def convert_task_to_legacy_config(task: dict) -> dict:
    """
    Convert AI task YAML to a more traditional workflow config.

    这个函数的目的：
    1. 不直接修改你原来的 config_zemax.yaml。
    2. 生成一个 config_D31_from_task.yaml。
    3. 后面 D32/D33 再让 workflow_runner.py 读取它。
    """
    target = task["target"]
    safety = task["safety"]

    values = estimate_values(
        target["start"],
        target["end"],
        target["step"]
    )

    legacy_config = {
        "task_info": {
            "source": "AI-generated YAML task",
            "generated_by": "scripts/D31_run_from_task_yaml.py",
            "task_type": task["task_type"]
        },
        "zemax": {
            "model_file": task["model_file"],
            "read_only_original_model": safety["read_only_original_model"]
        },
        "sweep": {
            "surface": target["surface"],
            "parameter": target["parameter"],
            "unit": target["unit"],
            "start": target["start"],
            "end": target["end"],
            "step": target["step"],
            "values": values
        },
        "analysis": {
            "metrics": task["metrics"]
        },
        "outputs": {
            "output_dir": safety["output_dir"],
            "items": task["outputs"]
        },
        "safety": {
            "dry_run_first": safety["dry_run_first"],
            "max_runs": safety["max_runs"],
            "estimated_runs": len(values)
        }
    }

    return legacy_config


def try_execute_workflow(config_path: Path) -> None:
    """
    Placeholder for executing the real workflow.

    现在先不强行接你的 workflow_runner.py，因为我们还需要确认
    workflow_runner.py 里面的函数名和参数格式。

    D31 的任务先做到：
    - task YAML 可以读取
    - schema 可以校验
    - dry-run 可以预览
    - 可以生成旧版 workflow config
    """
    print("【WARN】 Execute mode is reserved for the next step.")
    print(f"Generated config path: {config_path}")
    print("Next step: connect this config to modules/workflow_runner.py or main.py.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="D31: Run or preview a Zemax workflow from an AI-generated YAML task."
    )

    parser.add_argument(
        "--task",
        type=str,
        default=str(DEFAULT_TASK_PATH),
        help="Path to the AI-generated YAML task file."
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to the JSON Schema file."
    )

    parser.add_argument(
        "--out-config",
        type=str,
        default=str(DEFAULT_OUTPUT_CONFIG_PATH),
        help="Path to save the converted workflow config YAML."
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute workflow. Default is dry-run only."
    )

    args = parser.parse_args()

    task_path = Path(args.task)
    schema_path = Path(args.schema)
    out_config_path = Path(args.out_config)

    try:
        schema = load_json(schema_path)
        task = load_yaml(task_path)

        schema_errors = validate_task_with_schema(task, schema)
        if schema_errors:
            print_schema_errors(schema_errors)
            return

        safety_errors = extra_safety_check(task)
        if safety_errors:
            print("【ERROR】 Task failed extra safety checks.")
            print("-" * 70)
            for msg in safety_errors:
                print(f"- {msg}")
            print("-" * 70)
            return

        print_task_preview(task)

        legacy_config = convert_task_to_legacy_config(task)
        save_yaml(legacy_config, out_config_path)

        print(f"【OK】 Converted workflow config saved to: {out_config_path}")

        if args.execute:
            try_execute_workflow(out_config_path)
        else:
            print("【INFO】 Dry-run only. No Zemax model was opened or modified.")

    except Exception as e:
        print("【ERROR】 D31 task failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()