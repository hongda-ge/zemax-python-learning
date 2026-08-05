"""Day 14 step 2: read LDE Radius/Thickness Solve definitions safely."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.model_ops import (  # noqa: E402
    copy_baseline_model,
    open_working_model,
    sha256_file,
)
from scripts.demos.day14_lde_solve_audit_plan import (  # noqa: E402
    validate_execution_lock,
    validate_source_model,
)


INACTIVE_SOLVE_TYPES = {"None", "Fixed"}

# ZOSAPI's pythonnet proxy exposes properties from unrelated Solve variants.
# Read only fields that belong to the active interface documented by the
# installed ZOSAPI_Interfaces assembly.
SOLVE_DETAIL_FIELDS = {
    "SurfacePickup": [
        "Surface",
        "Column",
        "ScaleFactor",
        "Offset",
        "SupportsScale",
        "SupportsOffset",
    ],
    "ZPLMacro": ["Macro"],
    "MarginalRayAngle": ["Angle"],
    "MarginalRayHeight": ["Height", "PupilZone"],
    "ChiefRayAngle": ["Angle"],
    "ElementPower": ["Power"],
    "CocentricSurface": ["AboutSurface"],
    "ConcentricSurface": ["AboutSurface"],
    "CocentricRadius": ["WithSurface"],
    "ConcentricRadius": ["WithSurface"],
    "FNumber": ["FNumber"],
    "ChiefRayHeight": ["Height"],
    "EdgeThickness": ["Thickness", "RadialHeight"],
    "OpticalPathDifference": ["OPD", "PupilZone"],
    "Position": ["FromSurface", "Length"],
    "Compensator": ["RefSurface", "Sum"],
    "CenterOfCurvature": ["RefSurface"],
    "MaterialModel": [
        "IndexNd",
        "VaryIndex",
        "AbbeVd",
        "VaryAbbe",
        "dPgF",
        "VarydPgF",
    ],
    "MaterialSubstitute": ["Catalog"],
    "MaterialOffset": ["NdOffset", "VdOffset"],
    "PickupChiefRay": ["Field", "Wavelength"],
    "DuplicateSag": ["Surface"],
    "InvertSag": ["Surface"],
}


def require_reviewed_audit(config):
    """Allow the connection only for the reviewed read-only audit."""

    execution = config["execution"]
    if execution["allow_zosapi_connection"] is not True:
        raise ValueError("The Day 14 ZOS-API audit connection is not approved.")
    if execution["allow_read_only_solve_audit"] is not True:
        raise ValueError("The Day 14 Solve audit is not approved.")
    forbidden = {
        "model write": execution["allow_model_write"],
        "optimization": execution["allow_optimization"],
        "Quick Focus": execution["allow_quick_focus"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 14 action enabled: " + ", ".join(enabled))


def build_solve_type_names(zosapi):
    """Build the installed-version numeric-to-name SolveType mapping."""

    import clr
    import System

    enum_type = clr.GetClrType(zosapi.Editors.SolveType)
    names = list(System.Enum.GetNames(enum_type))
    values = list(System.Enum.GetValues(enum_type))
    mapping = {}
    for name, value in zip(names, values):
        mapping.setdefault(int(value), str(name))
    return mapping


def enum_name(value, solve_type_names):
    """Translate pythonnet's numeric Solve enum using installed metadata."""

    try:
        numeric = int(value)
    except Exception:
        numeric = None
    if numeric in solve_type_names:
        return solve_type_names[numeric]
    try:
        return str(value.ToString())
    except Exception:
        return str(value)


def json_scalar(value):
    """Convert a readable .NET property to a JSON-safe scalar."""

    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value) if math.isfinite(value) else str(value)
    if isinstance(value, str):
        return value
    try:
        text = value.ToString()
    except Exception:
        return None
    return str(text)


def read_variant_properties(solve_data, solve_type):
    """Read scalar properties from the active typed Solve interface."""

    variant_name = "_S_" + solve_type
    try:
        variant = getattr(solve_data, variant_name)
    except Exception:
        return {}
    if variant is None:
        return {}

    properties = {}
    for name in SOLVE_DETAIL_FIELDS.get(solve_type, []):
        try:
            value = getattr(variant, name)
        except Exception:
            continue
        scalar = json_scalar(value)
        if scalar is not None:
            properties[name] = scalar
    return properties


def finite_or_text(value):
    """Keep finite optical values numeric and represent infinity as text."""

    numeric = float(value)
    return numeric if math.isfinite(numeric) else str(numeric)


def audit_cell(cell, cell_name, numeric_value, solve_type_names):
    """Read one editor cell without calling any mutation method."""

    solve_type = enum_name(cell.Solve, solve_type_names)
    details = {}
    solve_data_valid = None
    try:
        solve_data = cell.GetSolveData()
        solve_data_valid = bool(solve_data.IsValid)
        data_type = enum_name(solve_data.Type, solve_type_names)
        if data_type != solve_type:
            raise ValueError(
                f"{cell_name} Solve/Data type mismatch: {solve_type}/{data_type}"
            )
        details = read_variant_properties(solve_data, solve_type)
    except ValueError:
        raise
    except Exception as error:
        details = {"read_warning": f"{type(error).__name__}: {error}"}

    if solve_type in INACTIVE_SOLVE_TYPES:
        category = "inactive"
    elif solve_type == "Variable":
        category = "optimization_variable"
    else:
        category = "dependent_solve"
    return {
        "cell": cell_name,
        "value": finite_or_text(numeric_value),
        "solve_type": solve_type,
        "category": category,
        "solve_data_valid": solve_data_valid,
        "solve_properties": details,
    }


def audit_lde(system, solve_type_names):
    """Read Radius and Thickness cells on every sequential surface."""

    rows = []
    surface_count = int(system.LDE.NumberOfSurfaces)
    for surface_id in range(surface_count):
        surface = system.LDE.GetSurfaceAt(surface_id)
        try:
            comment = str(surface.Comment)
        except Exception:
            comment = ""
        cells = [
            audit_cell(
                surface.RadiusCell,
                "radius",
                surface.Radius,
                solve_type_names,
            ),
            audit_cell(
                surface.ThicknessCell,
                "thickness",
                surface.Thickness,
                solve_type_names,
            ),
        ]
        rows.append(
            {
                "surface_id": surface_id,
                "comment": comment,
                "cells": cells,
            }
        )
    return rows


def active_cells(rows):
    """Return variables and dependent Solves for concise reporting."""

    result = []
    for surface in rows:
        for cell in surface["cells"]:
            if cell["category"] != "inactive":
                result.append(
                    {
                        "surface_id": surface["surface_id"],
                        "comment": surface["comment"],
                        **cell,
                    }
                )
    return result


def main():
    config = load_config("configs/day14_lde_solve_audit.yaml")
    validate_execution_lock(config)
    require_reviewed_audit(config)
    source_file, source_hash_before = validate_source_model(config)

    run_id = datetime.now().strftime("solve_audit_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    copy_info = copy_baseline_model(source_file, run_dir, "working_model.zmx")
    working_file = Path(copy_info["working_file"])
    working_hash_before = sha256_file(working_file)

    print("========== DAY 14 LDE SOLVE AUDIT ==========")
    print(f"Source model: {source_file}")
    print(f"Working copy: {working_file}")
    print("Read-only operations: open model, read values, read Solve definitions")

    with StandaloneZemaxConnection() as connection:
        connection_info = connection.info()
        solve_type_names = build_solve_type_names(connection.ZOSAPI)
        print("[PASS] ZOS-API connection")
        open_working_model(connection.system, working_file)
        print("[PASS] Working copy opened")
        rows = audit_lde(connection.system, solve_type_names)
        print("[PASS] RadiusCell and ThicknessCell audited")

    source_hash_after = sha256_file(source_file).upper()
    working_hash_after = sha256_file(working_file)
    source_unchanged = source_hash_after == source_hash_before
    working_unchanged = working_hash_after == working_hash_before
    if not source_unchanged:
        raise RuntimeError("The frozen baseline model changed during Day 14.")
    if not working_unchanged:
        raise RuntimeError("The Day 14 working copy changed on disk.")

    active = active_cells(rows)
    report = {
        "task": "day14_lde_solve_audit",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "source_unchanged": source_unchanged,
        "working_copy": str(working_file),
        "working_sha256_before": working_hash_before,
        "working_sha256_after": working_hash_after,
        "working_copy_unchanged": working_unchanged,
        "connection": connection_info,
        "solve_type_names": solve_type_names,
        "connection_closed": connection.closed,
        "model_write_used": False,
        "optimization_used": False,
        "quick_focus_used": False,
        "save_as_used": False,
        "surface_count": len(rows),
        "surface_audit": rows,
        "active_cells": active,
    }
    report_file = run_dir / "lde_solve_audit.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("Active variables and dependent Solves:")
    if not active:
        print("  NONE")
    for cell in active:
        properties = cell["solve_properties"]
        property_text = (
            ", ".join(f"{key}={value}" for key, value in properties.items())
            if properties
            else "no scalar properties"
        )
        print(
            f"  Surface {cell['surface_id']} {cell['cell']}: "
            f"{cell['solve_type']} ({cell['category']}), {property_text}"
        )

    print()
    print(f"[PASS] Surfaces audited: {len(rows)}")
    print(f"[PASS] Active cells found: {len(active)}")
    print(f"[PASS] Connection closed: {connection.closed}")
    print(f"[PASS] Original model unchanged: {source_unchanged}")
    print(f"[PASS] Disk working copy unchanged: {working_unchanged}")
    print("[PASS] No model write, optimization, Quick Focus or SaveAs was used")
    print(f"[PASS] Audit report: {report_file}")


if __name__ == "__main__":
    main()
