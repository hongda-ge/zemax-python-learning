from pathlib import Path
import argparse
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.task_safety import load_yaml, run_all_safety_checks, estimate_sweep_values


DEFAULT_TASK_PATH = PROJECT_ROOT / "configs" / "agent_tasks" / "D30_task_example.yaml"
DEFAULT_POLICY_PATH = PROJECT_ROOT / "configs" / "safety_policy.yaml"


def print_task_overview(task: dict) -> None:
    """Print task information before safety check."""
    target = task["target"]
    safety = task["safety"]

    values = estimate_sweep_values(
        target["start"],
        target["end"],
        target["step"]
    )

    print("=" * 70)
    print("D33 Safety Boundary Check")
    print("=" * 70)
    print(f"Model file: {task['model_file']}")
    print(f"Task type: {task['task_type']}")
    print(
        "Target: "
        f"Surface {target['surface']} / "
        f"{target['parameter']} / "
        f"{target['unit']}"
    )
    print(
        "Sweep: "
        f"{target['start']} to {target['end']}, "
        f"step = {target['step']}"
    )
    print(f"Estimated run count: {len(values)}")
    print(f"Output dir: {safety['output_dir']}")
    print(f"Read-only original model: {safety['read_only_original_model']}")
    print(f"Dry-run first: {safety['dry_run_first']}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="D33: Check safety boundary for AI-generated Zemax task YAML."
    )

    parser.add_argument(
        "--task",
        type=str,
        default=str(DEFAULT_TASK_PATH),
        help="Path to AI-generated task YAML."
    )

    parser.add_argument(
        "--policy",
        type=str,
        default=str(DEFAULT_POLICY_PATH),
        help="Path to safety policy YAML."
    )

    args = parser.parse_args()

    task_path = Path(args.task)
    policy_path = Path(args.policy)

    try:
        task = load_yaml(task_path)
        policy = load_yaml(policy_path)

        print_task_overview(task)

        errors = run_all_safety_checks(
            task=task,
            policy=policy,
            project_root=PROJECT_ROOT
        )

        if errors:
            print("【ERROR】 Task failed D33 safety checks.")
            print("-" * 70)
            for idx, error in enumerate(errors, start=1):
                print(f"{idx}. {error}")
            print("-" * 70)
            print("No Zemax workflow should be executed before these issues are fixed.")
            return

        print("【OK】 Task passed all D33 safety checks.")
        print("This task is allowed to enter the next workflow stage.")

    except Exception as e:
        print("【ERROR】 D33 safety check failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()