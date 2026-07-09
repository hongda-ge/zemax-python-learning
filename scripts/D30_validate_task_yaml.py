from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = PROJECT_ROOT / "configs" / "task_schema.json"
TASK_PATH = PROJECT_ROOT / "examples" / "D30_task_example.yaml"


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    """Load a YAML file safely."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML file is empty: {path}")

    if not isinstance(data, dict):
        raise TypeError("The YAML task file must be a dictionary/object at the top level.")

    return data


def estimate_run_count(task: dict) -> int:
    """Estimate the number of sweep points."""
    target = task["target"]

    start = target["start"]
    end = target["end"]
    step = target["step"]

    if step <= 0:
        raise ValueError("Step must be greater than 0.")

    if end < start:
        raise ValueError("End value must be greater than or equal to start value.")

    run_count = int(round((end - start) / step)) + 1

    return run_count


def extra_safety_check(task: dict) -> None:
    """Project-specific safety checks."""
    run_count = estimate_run_count(task)
    max_runs = task["safety"]["max_runs"]

    if run_count > max_runs:
        raise ValueError(
            f"Too many runs: {run_count}. "
            f"The current max_runs is {max_runs}."
        )

    output_dir = task["safety"]["output_dir"]

    if not output_dir.startswith("results/"):
        raise ValueError("Output directory must be inside the results/ folder.")

    if task["safety"]["read_only_original_model"] is not True:
        raise ValueError("Original Zemax model must be read-only for AI-generated tasks.")

    if task["safety"]["dry_run_first"] is not True:
        raise ValueError("AI-generated tasks must use dry_run_first: true.")


def validate_task(schema: dict, task: dict) -> list:
    """Validate task with JSON Schema and return sorted errors."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(task), key=lambda e: e.path)
    return errors


def print_task_summary(task: dict) -> None:
    """Print a readable summary of the task."""
    run_count = estimate_run_count(task)
    target = task["target"]

    print("✅ YAML task is valid.")
    print("-" * 60)
    print(f"Software: {task['software']}")
    print(f"Task type: {task['task_type']}")
    print(f"Model file: {task['model_file']}")
    print(
        "Sweep target: "
        f"surface {target['surface']} / {target['parameter']}"
    )
    print(
        "Sweep range: "
        f"{target['start']} to {target['end']} {target['unit']}, "
        f"step = {target['step']}"
    )
    print(f"Estimated run count: {run_count}")
    print(f"Metrics: {', '.join(task['metrics'])}")
    print(f"Outputs: {', '.join(task['outputs'])}")
    print(f"Output directory: {task['safety']['output_dir']}")
    print("-" * 60)


def main() -> None:
    try:
        schema = load_json(SCHEMA_PATH)
        task = load_yaml(TASK_PATH)

        schema_errors = validate_task(schema, task)

        if schema_errors:
            print("❌ YAML task failed JSON Schema validation.")
            print("-" * 60)
            for error in schema_errors:
                field_path = ".".join(str(x) for x in error.path)
                field_path = field_path if field_path else "<root>"
                print(f"Field: {field_path}")
                print(f"Reason: {error.message}")
                print("-" * 60)
            return

        extra_safety_check(task)
        print_task_summary(task)

    except Exception as e:
        print("❌ Task validation failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()