"""
D41 Agent Tool Demo

Run from project root:

    python scripts/D41_agent_tool_demo.py

This script integrates:
- D38 tool_registry
- D39 input validation
- D40 run_manager

It demonstrates three typical cases:
1. Normal pseudo Zemax-Agent workflow
2. Invalid parameter rejected by input validation
3. Dangerous path rejected by path safety check

This demo does not launch Zemax.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.tool_registry import call_tool
from modules.run_manager import (
    append_event,
    create_run,
    mark_failed,
    mark_success,
    update_status,
)


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def run_case(
    case_name: str,
    case_description: str,
    steps: List[Dict[str, Any]],
    expected_success: bool
) -> Dict[str, Any]:
    """
    Run one D41 case.

    Parameters:
        case_name:
            Short name of this case.
        case_description:
            Human-readable case description.
        steps:
            Tool call steps.
        expected_success:
            True means all steps should succeed.
            False means this case is expected to be rejected by validation/safety.

    Returns:
        final run status.
    """
    print_section(case_name)
    print(case_description)

    total_steps = len(steps)

    status = create_run(
        task_name=case_name,
        tool_name="D41_agent_tool_demo",
        args={
            "case_description": case_description,
            "expected_success": expected_success
        },
        total_steps=total_steps,
        prefix="D41"
    )

    run_id = status["run_id"]

    print("\nRun created:")
    print_json(status)

    try:
        update_status(
            run_id,
            state="running",
            current_step="starting",
            completed_steps=0,
            total_steps=total_steps,
            message="D41 case started: {}".format(case_name)
        )

        case_failed_as_expected = False

        for index, step in enumerate(steps, start=1):
            step_name = step["step_name"]
            tool_name = step["tool_name"]
            args = step.get("args", {})
            expect_error = step.get("expect_error", False)

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
                {
                    "tool_name": tool_name,
                    "args": args,
                    "expect_error": expect_error
                }
            )

            result = call_tool(tool_name, args)
            print_json(result)

            is_success = result.get("status") == "success"

            if expect_error:
                if is_success:
                    raise RuntimeError(
                        "Expected this step to fail, but it succeeded: {}".format(step_name)
                    )

                case_failed_as_expected = True

                append_event(
                    run_id,
                    "warning",
                    "Step rejected as expected: {}".format(step_name),
                    {
                        "tool_name": tool_name,
                        "result": result
                    }
                )

                update_status(
                    run_id,
                    state="running",
                    current_step=step_name,
                    completed_steps=index,
                    total_steps=total_steps,
                    message="Step rejected as expected: {}".format(step_name),
                    extra={
                        "last_tool": tool_name,
                        "last_result": result
                    }
                )

                # For an expected error case, we stop after the rejection.
                break

            if not is_success:
                raise RuntimeError(
                    "Unexpected tool failure in step {}: {}".format(
                        step_name,
                        result.get("message", "")
                    )
                )

            append_event(
                run_id,
                "info",
                "Finished step: {}".format(step_name),
                {
                    "tool_name": tool_name,
                    "result": result
                }
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

            time.sleep(0.2)

        if expected_success:
            final_status = mark_success(
                run_id,
                "D41 case completed successfully: {}".format(case_name)
            )
        else:
            if case_failed_as_expected:
                final_status = mark_success(
                    run_id,
                    "D41 case passed: invalid input was rejected as expected."
                )
            else:
                final_status = mark_failed(
                    run_id,
                    "D41 case failed: expected rejection did not happen."
                )

    except Exception as exc:
        final_status = mark_failed(
            run_id,
            "D41 case failed unexpectedly: {}".format(case_name),
            exc
        )

    print_section("Final status for {}".format(case_name))
    print_json(final_status)

    run_dir = PROJECT_ROOT / final_status["run_dir"]
    print("\nOutput files:")
    print("Run directory:", run_dir)
    print("Status file:", run_dir / "status.json")
    print("Events file:", run_dir / "events.jsonl")

    return final_status


def build_cases() -> List[Dict[str, Any]]:
    """
    Build three typical D41 demo cases.
    """
    case_1 = {
        "case_name": "Case 1 - Normal pseudo Zemax-Agent workflow",
        "case_description": (
            "This case simulates a normal tool-based workflow: "
            "validate task, check safety, run sweep, run analysis, "
            "prepare summary input, and generate report."
        ),
        "expected_success": True,
        "steps": [
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
                    "output_dir": "results/D41_case1_analysis"
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
                    "report_title": "D41 Normal Tool Workflow Report",
                    "output_file": "reports/D41_case1_tool_workflow_report.md"
                }
            }
        ]
    }

    case_2 = {
        "case_name": "Case 2 - Invalid analysis parameter rejected",
        "case_description": (
            "This case intentionally sends an unsupported analysis_type "
            "to prove that D39 input validation blocks invalid parameters."
        ),
        "expected_success": False,
        "steps": [
            {
                "step_name": "run_analysis_invalid_enum",
                "tool_name": "run_analysis",
                "expect_error": True,
                "args": {
                    "analysis_type": "ray_fan",
                    "output_dir": "results/D41_case2_invalid_analysis"
                }
            }
        ]
    }

    case_3 = {
        "case_name": "Case 3 - Dangerous path rejected",
        "case_description": (
            "This case intentionally sends a path outside the project directory "
            "to prove that path safety checking blocks dangerous file access."
        ),
        "expected_success": False,
        "steps": [
            {
                "step_name": "load_task_dangerous_path",
                "tool_name": "load_task",
                "expect_error": True,
                "args": {
                    "task_file": "../../secret_config.yaml"
                }
            }
        ]
    }

    return [case_1, case_2, case_3]


def main() -> None:
    print_section("D41 Agent Tool Demo")
    print("This demo integrates D38, D39, and D40.")
    print("It does not launch Zemax.")
    print("It prepares three interview-friendly cases.")

    cases = build_cases()
    final_statuses = []

    for case in cases:
        final_status = run_case(
            case_name=case["case_name"],
            case_description=case["case_description"],
            steps=case["steps"],
            expected_success=case["expected_success"]
        )
        final_statuses.append(final_status)

    print_section("D41 Summary")
    summary = {
        "total_cases": len(final_statuses),
        "case_statuses": [
            {
                "run_id": item.get("run_id"),
                "task_name": item.get("task_name"),
                "state": item.get("state"),
                "message": item.get("last_message"),
                "run_dir": item.get("run_dir")
            }
            for item in final_statuses
        ]
    }
    print_json(summary)

    print_section("D41 Demo Finished")
    print("If all cases have state = success, D41 core demo passed.")
    print("Case 2 and Case 3 are expected to be rejected, so their run state can still be success if rejection was correctly handled.")


if __name__ == "__main__":
    main()