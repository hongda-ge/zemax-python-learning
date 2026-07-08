"""
D38 Tool Registry Demo

Run this script from the project root:

    python scripts/D38_tool_registry_demo.py

This demo does not launch Zemax.
It only demonstrates how tools can be listed, inspected, and called.
"""

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.tool_registry import list_tools, get_tool_spec, call_tool


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    print_section("D38 Tool Registry Demo")

    print("This demo simulates a pseudo MCP-style tool registry.")
    print("It does not launch Zemax.")
    print("It only tests list_tools(), get_tool_spec(), and call_tool().")

    # Step 1: List tools
    print_section("Step 1: List registered tools")
    tools = list_tools()
    print_json(tools)

    # Step 2: Inspect one tool
    print_section("Step 2: Inspect tool spec: run_sweep")
    spec = get_tool_spec("run_sweep")
    print_json(spec)

    # Step 3: Call load_task
    print_section("Step 3: Call tool: load_task")
    result = call_tool(
        "load_task",
        {
            "task_file": "configs/config_D31_from_task.yaml",
        },
    )
    print_json(result)

    # Step 4: Call validate_task
    print_section("Step 4: Call tool: validate_task")
    result = call_tool(
        "validate_task",
        {
            "task_file": "configs/config_D31_from_task.yaml",
            "schema_file": "configs/task_schema.json",
        },
    )
    print_json(result)

    # Step 5: Call check_safety
    print_section("Step 5: Call tool: check_safety")
    result = call_tool(
        "check_safety",
        {
            "task_file": "configs/config_D31_from_task.yaml",
            "safety_policy_file": "configs/safety_policy.yaml",
        },
    )
    print_json(result)

    # Step 6: Call run_sweep in dry-run mode
    print_section("Step 6: Call tool: run_sweep")
    result = call_tool(
        "run_sweep",
        {
            "task_file": "configs/config_D31_from_task.yaml",
            "dry_run": True,
            "max_runs": 50,
        },
    )
    print_json(result)

    # Step 7: Call a simulated analysis tool
    print_section("Step 7: Call tool: run_analysis")
    result = call_tool(
        "run_analysis",
        {
            "analysis_type": "fft_mtf",
            "output_dir": "results/D38_mock_analysis",
        },
    )
    print_json(result)

    # Step 8: Test unknown tool
    print_section("Step 8: Test unknown tool")
    result = call_tool(
        "unknown_tool",
        {
            "anything": "test",
        },
    )
    print_json(result)

    print_section("D38 Demo Finished")
    print("If all steps above printed structured JSON-like results, D38 core demo passed.")


if __name__ == "__main__":
    main()