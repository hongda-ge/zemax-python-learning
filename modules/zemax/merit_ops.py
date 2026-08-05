"""Read-only helpers for evaluating an existing Zemax Merit Function."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def _cell_text(row: Any, column: Any) -> str:
    """Return one operand-definition cell as stable text."""

    cell = row.GetOperandCell(column)
    if cell is None or not bool(cell.IsActive):
        return ""
    return str(cell.Value)


def read_merit_definition(system: Any, zosapi: Any) -> Dict[str, Any]:
    """Read operand definitions without changing or calculating the MFE."""

    editor = system.MFE
    columns = zosapi.Editors.MFE.MeritColumn
    parameter_columns = [
        columns.Param1,
        columns.Param2,
        columns.Param3,
        columns.Param4,
        columns.Param5,
        columns.Param6,
        columns.Param7,
        columns.Param8,
    ]

    operands: List[Dict[str, Any]] = []
    for operand_number in range(1, int(editor.NumberOfOperands) + 1):
        row = editor.GetOperandAt(operand_number)
        operands.append(
            {
                "operand_number": int(row.OperandNumber),
                "type": str(row.Type),
                "type_name": str(row.TypeName),
                "is_active": bool(row.IsActive),
                "comment": _cell_text(row, columns.Comment),
                "parameters": [
                    _cell_text(row, column) for column in parameter_columns
                ],
                "target": float(row.Target),
                "weight": float(row.Weight),
            }
        )

    canonical = json.dumps(
        operands,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "operand_count": len(operands),
        "definition_sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest().upper(),
        "operands": operands,
    }


def calculate_existing_merit_function(
    system: Any,
    zosapi: Any,
) -> Dict[str, Any]:
    """Calculate the current MFE once and prove its definition did not change."""

    before = read_merit_definition(system, zosapi)
    if before["operand_count"] <= 0:
        raise ValueError("The saved model contains no Merit Function operands.")

    merit_value = float(system.MFE.CalculateMeritFunction())
    after = read_merit_definition(system, zosapi)
    definition_unchanged = (
        before["definition_sha256"] == after["definition_sha256"]
        and before["operand_count"] == after["operand_count"]
    )
    if not definition_unchanged:
        raise RuntimeError("Merit Function definition changed during calculation.")

    return {
        "merit_value": merit_value,
        "operand_count": before["operand_count"],
        "definition_sha256": before["definition_sha256"],
        "definition_unchanged": definition_unchanged,
        "operands": after["operands"],
    }


def load_merit_recipe(
    system: Any,
    zosapi: Any,
    recipe_file: Any,
    expected_operand_count: int,
    expected_definition_sha256: str,
    strict_definition: bool = True,
) -> Dict[str, Any]:
    """Load one frozen .MF recipe in memory and verify its definition."""

    recipe_path = Path(recipe_file).expanduser().resolve()
    if not recipe_path.is_file():
        raise FileNotFoundError(f"Merit Function recipe not found: {recipe_path}")

    before = read_merit_definition(system, zosapi)
    system.MFE.LoadMeritFunction(str(recipe_path))
    loaded = read_merit_definition(system, zosapi)

    if loaded["operand_count"] != int(expected_operand_count):
        raise ValueError("Loaded Merit Function operand count is incorrect.")
    definition_matches_expected = (
        loaded["definition_sha256"].upper()
        == expected_definition_sha256.upper()
    )
    if strict_definition and not definition_matches_expected:
        raise ValueError("Loaded Merit Function definition SHA256 is incorrect.")

    return {
        "original_operand_count": before["operand_count"],
        "original_definition_sha256": before["definition_sha256"],
        "loaded_operand_count": loaded["operand_count"],
        "loaded_definition_sha256": loaded["definition_sha256"],
        "expected_definition_sha256": expected_definition_sha256.upper(),
        "definition_matches_expected": definition_matches_expected,
    }


__all__ = [
    "calculate_existing_merit_function",
    "load_merit_recipe",
    "read_merit_definition",
]
