"""
D39 Input Validator

This module validates tool inputs before tool execution.

D39 goal:
- Use JSON Schema to check tool input types, required fields, enum values, and ranges.
- Add simple path safety checks.
- Reject illegal parameters before calling the actual tool handler.

Python compatibility:
- Written for Python 3.8.
"""

from pathlib import Path
from typing import Any, Dict, List

import json
from jsonschema import Draft7Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = PROJECT_ROOT / "configs" / "schema_D39_tool_inputs.json"


def load_tool_input_schemas(schema_file: Path = SCHEMA_FILE) -> Dict[str, Any]:
    """
    Load all tool input schemas from configs/schema_D39_tool_inputs.json.
    """
    if not schema_file.exists():
        raise FileNotFoundError("Tool input schema file not found: {}".format(schema_file))

    with schema_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("tool_schemas", {})


def _resolve_project_path(path_text: str) -> Path:
    """
    Resolve a path relative to the project root.
    """
    path = Path(path_text)

    if path.is_absolute():
        return path.resolve()

    return (PROJECT_ROOT / path).resolve()


def _is_inside_project(path: Path) -> bool:
    """
    Check whether a path is inside the project root.
    """
    try:
        path.relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def _looks_like_path_field(field_name: str) -> bool:
    """
    Identify fields that should be treated as file or directory paths.
    """
    path_keywords = [
        "_file",
        "_dir",
        "file",
        "dir",
        "path",
        "output",
    ]

    return any(keyword in field_name for keyword in path_keywords)


def check_path_safety(args: Dict[str, Any]) -> List[str]:
    """
    Check whether file/path-like input values stay inside the project directory.

    This is not a replacement for D33 safety policy.
    It is a lightweight D39 input-level path check.
    """
    errors = []

    for key, value in args.items():
        if not isinstance(value, str):
            continue

        if not _looks_like_path_field(key):
            continue

        resolved = _resolve_project_path(value)

        if not _is_inside_project(resolved):
            errors.append(
                "{} points outside project directory: {}".format(key, value)
            )

    return errors


def format_jsonschema_error(error: Any) -> str:
    """
    Convert a jsonschema error into a readable message.
    """
    path = ".".join(str(part) for part in error.path)

    if path:
        return "{}: {}".format(path, error.message)

    return error.message


def validate_tool_input(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate one tool call's input arguments.

    Return format:
    {
        "valid": true/false,
        "tool": "...",
        "errors": [...]
    }
    """
    schemas = load_tool_input_schemas()

    if tool_name not in schemas:
        return {
            "valid": False,
            "tool": tool_name,
            "errors": [
                "No input schema found for tool: {}".format(tool_name)
            ],
        }

    schema = schemas[tool_name]
    validator = Draft7Validator(schema)

    schema_errors = sorted(
        validator.iter_errors(args),
        key=lambda e: e.path
    )

    errors = [format_jsonschema_error(error) for error in schema_errors]

    path_errors = check_path_safety(args)
    errors.extend(path_errors)

    if errors:
        return {
            "valid": False,
            "tool": tool_name,
            "errors": errors,
        }

    return {
        "valid": True,
        "tool": tool_name,
        "errors": [],
    }