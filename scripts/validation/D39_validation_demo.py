"""
D39 Validation Demo

Run this script from the project root:

    python scripts/D39_validation_demo.py

This demo tests whether invalid tool inputs are rejected before handler execution.
"""

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.tool_registry import call_tool


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    print_section("D39 Input Validation Demo")
    print("This demo tests JSON Schema input validation before tool execution.")
    print("It does not launch Zemax.")

    # Case 1: Valid run_analysis
    print_section("Case 1: Valid input - run_analysis")
    result = call_tool(
        "run_analysis",
        {
            "analysis_type": "fft_mtf",
            "output_dir": "results/D39_valid_analysis"
        }
    )
    print_json(result)

    # Case 2: Invalid analysis_type
    print_section("Case 2: Invalid enum - run_analysis")
    result = call_tool(
        "run_analysis",
        {
            "analysis_type": "ray_fan",
            "output_dir": "results/D39_invalid_analysis"
        }
    )
    print_json(result)

    # Case 3: Missing required input
    print_section("Case 3: Missing required input - set_parameter")
    result = call_tool(
        "set_parameter",
        {
            "surface": 6,
            "parameter": "thickness"
        }
    )
    print_json(result)

    # Case 4: Invalid surface number
    print_section("Case 4: Invalid range - set_parameter")
    result = call_tool(
        "set_parameter",
        {
            "surface": 0,
            "parameter": "thickness",
            "value": 1.25,
            "unit": "mm"
        }
    )
    print_json(result)

    # Case 5: Unsupported parameter
    print_section("Case 5: Invalid enum - set_parameter")
    result = call_tool(
        "set_parameter",
        {
            "surface": 6,
            "parameter": "glass",
            "value": "N-BK7",
            "unit": "mm"
        }
    )
    print_json(result)

    # Case 6: Too many sweep runs
    print_section("Case 6: Invalid max_runs - run_sweep")
    result = call_tool(
        "run_sweep",
        {
            "task_file": "configs/config_D31_from_task.yaml",
            "dry_run": True,
            "max_runs": 999
        }
    )
    print_json(result)

    # Case 7: Extra unexpected field
    print_section("Case 7: Extra field - run_sweep")
    result = call_tool(
        "run_sweep",
        {
            "task_file": "configs/config_D31_from_task.yaml",
            "dry_run": True,
            "max_runs": 50,
            "dangerous_extra_field": "should_not_be_allowed"
        }
    )
    print_json(result)

    # Case 8: Dangerous path
    print_section("Case 8: Dangerous path - load_task")
    result = call_tool(
        "load_task",
        {
            "task_file": "../../secret_config.yaml"
        }
    )
    print_json(result)

    print_section("D39 Demo Finished")
    print("If valid input succeeds and invalid inputs are rejected, D39 core demo passed.")


if __name__ == "__main__":
    main()