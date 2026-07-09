"""
D38 Tool Registry

This module provides a simple tool registry for the Zemax-Agent workflow.

D38 goal:
- Do not implement a full MCP server yet.
- Do not connect to Zemax yet.
- First simulate how tools can be registered, listed, inspected, and called.

Main functions:
- list_tools()
- get_tool_spec(tool_name)
- call_tool(tool_name, args)
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from modules.input_validator import validate_tool_input


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def _resolve_project_path(path_text: str) -> Path:
    """
    Resolve a path relative to the project root.

    This keeps all file operations inside the current project.
    """
    path = Path(path_text)

    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (PROJECT_ROOT / path).resolve()

    return resolved


def _is_inside_project(path: Path) -> bool:
    """
    Check whether a resolved path is inside the current project root.
    """
    try:
        path.relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def _standard_success(tool_name: str, message: str, **extra: Any) -> Dict[str, Any]:
    """
    Return a standard success result.
    """
    result = {
        "status": "success",
        "tool": tool_name,
        "message": message,
    }
    result.update(extra)
    return result


def _standard_error(tool_name: str, message: str, **extra: Any) -> Dict[str, Any]:
    """
    Return a standard error result.
    """
    result = {
        "status": "error",
        "tool": tool_name,
        "message": message,
    }
    result.update(extra)
    return result


# ----------------------------------------------------------------------
# Mock tool handlers
# ----------------------------------------------------------------------

def load_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of load_task.

    It checks whether the task file exists.
    It does not parse YAML deeply in D38.
    """
    tool_name = "load_task"
    task_file = args.get("task_file")

    if not task_file:
        return _standard_error(tool_name, "Missing required input: task_file")

    task_path = _resolve_project_path(task_file)

    if not _is_inside_project(task_path):
        return _standard_error(tool_name, "Task file path is outside project.", task_file=str(task_path))

    if not task_path.exists():
        return _standard_error(tool_name, "Task file not found.", task_file=str(task_path))

    return _standard_success(
        tool_name,
        "Task file loaded in simulation mode.",
        task_file=str(task_path.relative_to(PROJECT_ROOT)),
        simulation_mode=True,
    )


def validate_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of validate_task.

    D38 only checks whether task file and schema file exist.
    Real schema validation was handled in D30 and can be integrated later.
    """
    tool_name = "validate_task"

    task_file = args.get("task_file", "configs/config_D31_from_task.yaml")
    schema_file = args.get("schema_file", "configs/task_schema.json")

    task_path = _resolve_project_path(task_file)
    schema_path = _resolve_project_path(schema_file)

    for path in [task_path, schema_path]:
        if not _is_inside_project(path):
            return _standard_error(tool_name, "Path is outside project.", path=str(path))

    missing = []
    if not task_path.exists():
        missing.append(str(task_path.relative_to(PROJECT_ROOT)))
    if not schema_path.exists():
        missing.append(str(schema_path.relative_to(PROJECT_ROOT)))

    if missing:
        return _standard_error(tool_name, "Required file missing.", missing_files=missing)

    return _standard_success(
        tool_name,
        "Task validation simulated successfully.",
        task_file=str(task_path.relative_to(PROJECT_ROOT)),
        schema_file=str(schema_path.relative_to(PROJECT_ROOT)),
        valid=True,
        simulation_mode=True,
    )


def check_safety(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of check_safety.

    D38 only checks whether safety policy exists.
    Real safety checking was handled in D33 and can be integrated later.
    """
    tool_name = "check_safety"

    task_file = args.get("task_file", "configs/config_D31_from_task.yaml")
    safety_policy_file = args.get("safety_policy_file", "configs/safety_policy.yaml")

    task_path = _resolve_project_path(task_file)
    policy_path = _resolve_project_path(safety_policy_file)

    for path in [task_path, policy_path]:
        if not _is_inside_project(path):
            return _standard_error(tool_name, "Path is outside project.", path=str(path))

    missing = []
    if not task_path.exists():
        missing.append(str(task_path.relative_to(PROJECT_ROOT)))
    if not policy_path.exists():
        missing.append(str(policy_path.relative_to(PROJECT_ROOT)))

    if missing:
        return _standard_error(tool_name, "Required file missing.", missing_files=missing)

    return _standard_success(
        tool_name,
        "Safety check simulated successfully.",
        task_file=str(task_path.relative_to(PROJECT_ROOT)),
        safety_policy_file=str(policy_path.relative_to(PROJECT_ROOT)),
        safe=True,
        estimated_runs=1,
        simulation_mode=True,
    )


def open_model(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of open_model.

    D38 does not connect to Zemax.
    It only shows what a future open_model tool might return.
    """
    tool_name = "open_model"

    model_file = args.get("model_file", "models/example_model.zmx")
    mode = args.get("mode", "standalone")
    make_copy = args.get("make_copy", True)

    return _standard_success(
        tool_name,
        "Model opening simulated. Zemax was not launched in D38.",
        model_file=model_file,
        mode=mode,
        make_copy=make_copy,
        working_model_file="outputs/D38_mock_working_model.zmx",
        surface_count=None,
        simulation_mode=True,
    )


def set_parameter(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of set_parameter.

    D38 does not modify a real Zemax model.
    It only checks whether required inputs are present.
    """
    tool_name = "set_parameter"

    required = ["surface", "parameter", "value"]
    missing = [name for name in required if name not in args]

    if missing:
        return _standard_error(tool_name, "Missing required inputs.", missing_inputs=missing)

    return _standard_success(
        tool_name,
        "Parameter update simulated. No Zemax model was modified.",
        surface=args["surface"],
        parameter=args["parameter"],
        old_value=None,
        new_value=args["value"],
        unit=args.get("unit", "mm"),
        simulation_mode=True,
    )


def run_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of run_analysis.

    D38 does not run MTF or Spot analysis.
    It only returns simulated output files.
    """
    tool_name = "run_analysis"

    analysis_type = args.get("analysis_type")
    if not analysis_type:
        return _standard_error(tool_name, "Missing required input: analysis_type")

    supported = ["fft_mtf", "spot_diagram"]
    if analysis_type not in supported:
        return _standard_error(
            tool_name,
            "Unsupported analysis type in D38 mock registry.",
            analysis_type=analysis_type,
            supported=supported,
        )

    return _standard_success(
        tool_name,
        "Analysis simulated. Zemax analysis was not executed.",
        analysis_type=analysis_type,
        output_files=[f"results/D38_mock_{analysis_type}.txt"],
        simulation_mode=True,
    )


def run_sweep(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of run_sweep.

    It simulates a sweep task without launching Zemax.
    """
    tool_name = "run_sweep"

    task_file = args.get("task_file", "configs/config_D31_from_task.yaml")
    dry_run = args.get("dry_run", True)
    max_runs = args.get("max_runs", 50)

    return _standard_success(
        tool_name,
        "Sweep simulated. No Zemax sweep was executed.",
        task_file=task_file,
        dry_run=dry_run,
        max_runs=max_runs,
        run_count=1,
        results_dir="results/D38_mock_sweep",
        results_csv="results/D38_mock_sweep/sweep_results.csv",
        simulation_mode=True,
    )


def analyze_results(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of analyze_results.

    D38 only checks whether a results file path is given.
    """
    tool_name = "analyze_results"

    results_file = args.get("results_file")
    if not results_file:
        return _standard_error(tool_name, "Missing required input: results_file")

    return _standard_success(
        tool_name,
        "Result analysis simulated.",
        results_file=results_file,
        best_result={"mock_parameter": 1.0, "mock_score": 0.85},
        summary="This is a simulated result summary for D38.",
        simulation_mode=True,
    )


def prepare_summary_input(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of prepare_summary_input.

    It returns a simulated summary input file path.
    """
    tool_name = "prepare_summary_input"

    results_file = args.get("results_file")
    if not results_file:
        return _standard_error(tool_name, "Missing required input: results_file")

    return _standard_success(
        tool_name,
        "Summary input preparation simulated.",
        results_file=results_file,
        summary_input_file="reports/D38_mock_result_summary_input.md",
        included_files=[
            results_file,
            args.get("figures_dir", "figures/"),
            args.get("log_file", "logs/weekly_log_06.md"),
        ],
        simulation_mode=True,
    )


def generate_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock version of generate_report.

    It returns a simulated report file path.
    """
    tool_name = "generate_report"

    report_title = args.get("report_title", "D38 Tool Registry Demo Report")
    output_file = args.get("output_file", "reports/D38_tool_registry_demo_report.md")

    return _standard_success(
        tool_name,
        "Report generation simulated.",
        report_title=report_title,
        report_file=output_file,
        simulation_mode=True,
    )


# ----------------------------------------------------------------------
# Tool specifications
# ----------------------------------------------------------------------

TOOLS: Dict[str, Dict[str, Any]] = {
    "load_task": {
        "name": "load_task",
        "description": "Read a YAML task file from the project directory.",
        "inputs": {
            "task_file": "string, required, e.g. configs/config_D31_from_task.yaml",
        },
        "outputs": {
            "status": "string",
            "task_file": "string",
            "message": "string",
        },
        "handler": load_task,
    },
    "validate_task": {
        "name": "validate_task",
        "description": "Check whether a task file matches the expected task schema.",
        "inputs": {
            "task_file": "string, optional",
            "schema_file": "string, optional",
        },
        "outputs": {
            "status": "string",
            "valid": "bool",
            "message": "string",
        },
        "handler": validate_task,
    },
    "check_safety": {
        "name": "check_safety",
        "description": "Check whether a task is safe based on the safety policy.",
        "inputs": {
            "task_file": "string, optional",
            "safety_policy_file": "string, optional",
        },
        "outputs": {
            "status": "string",
            "safe": "bool",
            "estimated_runs": "int",
            "message": "string",
        },
        "handler": check_safety,
    },
    "open_model": {
        "name": "open_model",
        "description": "Open a Zemax model. D38 only simulates this behavior.",
        "inputs": {
            "model_file": "string, optional",
            "mode": "string, optional",
            "make_copy": "bool, optional",
        },
        "outputs": {
            "status": "string",
            "working_model_file": "string",
            "surface_count": "int or null",
            "message": "string",
        },
        "handler": open_model,
    },
    "set_parameter": {
        "name": "set_parameter",
        "description": "Set one LDE parameter. D38 only simulates this behavior.",
        "inputs": {
            "surface": "int, required",
            "parameter": "string, required",
            "value": "number or string, required",
            "unit": "string, optional",
        },
        "outputs": {
            "status": "string",
            "old_value": "number/string/null",
            "new_value": "number/string",
            "message": "string",
        },
        "handler": set_parameter,
    },
    "run_analysis": {
        "name": "run_analysis",
        "description": "Run a Zemax analysis. D38 only simulates fft_mtf and spot_diagram.",
        "inputs": {
            "analysis_type": "string, required",
            "output_dir": "string, optional",
        },
        "outputs": {
            "status": "string",
            "analysis_type": "string",
            "output_files": "list",
            "message": "string",
        },
        "handler": run_analysis,
    },
    "run_sweep": {
        "name": "run_sweep",
        "description": "Run a parameter sweep. D38 only simulates the sweep.",
        "inputs": {
            "task_file": "string, optional",
            "dry_run": "bool, optional",
            "max_runs": "int, optional",
        },
        "outputs": {
            "status": "string",
            "run_count": "int",
            "results_dir": "string",
            "results_csv": "string",
            "message": "string",
        },
        "handler": run_sweep,
    },
    "analyze_results": {
        "name": "analyze_results",
        "description": "Analyze result files and return best result. D38 only simulates analysis.",
        "inputs": {
            "results_file": "string, required",
        },
        "outputs": {
            "status": "string",
            "best_result": "dict",
            "summary": "string",
            "message": "string",
        },
        "handler": analyze_results,
    },
    "prepare_summary_input": {
        "name": "prepare_summary_input",
        "description": "Prepare an AI-readable summary input file. D38 only simulates this behavior.",
        "inputs": {
            "results_file": "string, required",
            "figures_dir": "string, optional",
            "log_file": "string, optional",
        },
        "outputs": {
            "status": "string",
            "summary_input_file": "string",
            "included_files": "list",
            "message": "string",
        },
        "handler": prepare_summary_input,
    },
    "generate_report": {
        "name": "generate_report",
        "description": "Generate a Markdown report. D38 only simulates this behavior.",
        "inputs": {
            "report_title": "string, optional",
            "output_file": "string, optional",
        },
        "outputs": {
            "status": "string",
            "report_file": "string",
            "message": "string",
        },
        "handler": generate_report,
    },
}


# ----------------------------------------------------------------------
# Registry API
# ----------------------------------------------------------------------

def list_tools() -> List[Dict[str, str]]:
    """
    Return a short list of registered tools.
    """
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
        }
        for spec in TOOLS.values()
    ]


def get_tool_spec(tool_name: str) -> Dict[str, Any]:
    """
    Return the specification of a single tool.
    """
    if tool_name not in TOOLS:
        return {
            "status": "error",
            "message": f"Tool not found: {tool_name}",
            "available_tools": list(TOOLS.keys()),
        }

    spec = TOOLS[tool_name].copy()
    spec.pop("handler", None)
    return spec


def call_tool(tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call a registered tool by name.

    D39 update:
    - Validate tool input before executing the actual handler.
    - Reject illegal parameters early.
    """
    if args is None:
        args = {}

    if tool_name not in TOOLS:
        return {
            "status": "error",
            "tool": tool_name,
            "message": "Tool not found: {}".format(tool_name),
            "available_tools": list(TOOLS.keys()),
        }

    validation = validate_tool_input(tool_name, args)

    if not validation["valid"]:
        return {
            "status": "error",
            "tool": tool_name,
            "message": "Tool input validation failed.",
            "validation_errors": validation["errors"],
        }

    handler: Callable[[Dict[str, Any]], Dict[str, Any]] = TOOLS[tool_name]["handler"]

    try:
        return handler(args)
    except Exception as exc:
        return {
            "status": "error",
            "tool": tool_name,
            "message": "Tool execution failed: {}".format(exc),
        }