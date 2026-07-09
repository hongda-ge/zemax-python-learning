"""
D40 Long Task Demo

Run this script from the project root:

    python scripts/D40_long_task_demo.py

This demo:
- Creates a run_id.
- Creates results/runs/<run_id>/status.json.
- Creates results/runs/<run_id>/events.jsonl.
- Calls existing mock tools through tool_registry.
- Updates progress after each step.

It does not launch Zemax.
"""

from pathlib import Path
import json
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.run_manager import (
    append_event,
    create_run,
    mark_failed,
    mark_success,
    read_status,
    update_status,
)
from modules.tool_registry import call_tool


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def call_tool_checked(tool_name, args):
    """
    Call a tool and raise an error if it fails.

    This lets D40 demonstrate how a long task can stop
    when one step fails.
    """
    result = call_tool(tool_name, args)

    if result.get("status") != "success":
        raise RuntimeError(
            "Tool call failed: {} | {}".format(
                tool_name,
                result.get("message", "")
            )
        )

    return result


def main() -> None:
    print_section("D40 Long Task Management Demo")
    print("This demo tracks a pseudo long-running Zemax-Agent workflow.")
    print("It does not launch Zemax.")

    steps = [
        {
            "step_name": "validate_task",
            "tool_name": "validate_task",
            "args": {
                "task_file": "configs/config_D31_from_task.yaml",
                "schema_file": "configs/task_schema.json"
            }
        },
        {
            "step_name": "check_safety",
            "tool_name": "check_safety",
            "args": {
                "task_file": "configs/config_D31_from_task.yaml",
                "safety_policy_file": "configs/safety_policy.yaml"
            }
        },
        {
            "step_name": "run_sweep",
            "tool_name": "run_sweep",
            "args": {
                "task_file": "configs/config_D31_from_task.yaml",
                "dry_run": True,
                "max_runs": 50
            }
        },
        {
            "step_name": "run_analysis",
            "tool_name": "run_analysis",
            "args": {
                "analysis_type": "fft_mtf",
                "output_dir": "results/D40_mock_analysis"
            }
        },
        {
            "step_name": "prepare_summary_input",
            "tool_name": "prepare_summary_input",
            "args": {
                "results_file": "results/D38_mock_sweep/sweep_results.csv",
                "figures_dir": "figures/",
                "log_file": "logs/weekly_log_06.md"
            }
        },
        {
            "step_name": "generate_report",
            "tool_name": "generate_report",
            "args": {
                "report_title": "D40 Long Task Demo Report",
                "output_file": "reports/D40_long_task_demo_report.md"
            }
        }
    ]

    total_steps = len(steps)

    status = create_run(
        task_name="D40 tracked pseudo Zemax-Agent workflow",
        tool_name="tool_registry_workflow",
        args={"demo": "D40_long_task_demo"},
        total_steps=total_steps,
        prefix="D40"
    )

    run_id = status["run_id"]

    print_section("Run created")
    print_json(status)

    try:
        update_status(
            run_id,
            state="running",
            current_step="starting",
            completed_steps=0,
            total_steps=total_steps,
            message="D40 demo started."
        )

        for index, step in enumerate(steps, start=1):
            step_name = step["step_name"]
            tool_name = step["tool_name"]
            args = step["args"]

            print_section("Step {}/{}: {}".format(index, total_steps, step_name))

            update_status(
                run_id,
                state="running",
                current_step=step_name,
                completed_steps=index - 1,
                total_steps=total_steps,
                message="Starting step: {}".format(step_name)
            )

            append_event(
                run_id,
                "info",
                "Starting step: {}".format(step_name),
                {"tool_name": tool_name, "args": args}
            )

            result = call_tool_checked(tool_name, args)

            append_event(
                run_id,
                "info",
                "Finished step: {}".format(step_name),
                {"tool_name": tool_name, "result": result}
            )

            update_status(
                run_id,
                state="running",
                current_step=step_name,
                completed_steps=index,
                total_steps=total_steps,
                message="Finished step: {}".format(step_name),
                extra={
                    "last_tool": tool_name,
                    "last_result": result
                }
            )

            print_json(result)

            # Simulate a long-running task.
            time.sleep(0.4)

        final_status = mark_success(run_id, "D40 demo completed successfully.")

    except Exception as exc:
        final_status = mark_failed(run_id, "D40 demo failed.", exc)

    print_section("Final status")
    print_json(final_status)

    print_section("Output files")
    run_dir = PROJECT_ROOT / final_status["run_dir"]
    print("Run directory:", run_dir)
    print("Status file:", run_dir / "status.json")
    print("Events file:", run_dir / "events.jsonl")

    print_section("D40 Demo Finished")
    print("If status.json exists and state is success, D40 core demo passed.")


if __name__ == "__main__":
    main()