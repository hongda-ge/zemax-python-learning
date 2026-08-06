"""Day 15 step 1: audit the two-branch in-memory validation plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_execution_lock(config):
    """Keep Day 15 planning fully offline and mutation-free."""

    execution = config["execution"]
    locked_false = {
        "generic execution": execution["enabled"],
        "Quick Focus": execution["allow_quick_focus"],
        "optical analysis": execution["allow_optical_analysis"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in locked_false.items() if value is not False]
    if enabled:
        raise ValueError("Day 15 plan lock failed: " + ", ".join(enabled))

    reviewed_flags = (
        "allow_zosapi_connection",
        "allow_surface2_in_memory_write",
        "allow_surface6_make_solve_fixed",
    )
    for key in reviewed_flags:
        if not isinstance(execution[key], bool):
            raise ValueError(f"{key} must be Boolean.")


def validate_source_model(config):
    """Verify the frozen source model and Day 15 nominal parameter."""

    baseline = load_config(config["source"]["baseline_config"])
    model = baseline["model"]
    source_file = PROJECT_ROOT / model["source_file"]
    actual_hash = sha256_file(source_file).upper()
    expected_hash = str(model["source_sha256"]).upper()
    if actual_hash != expected_hash:
        raise ValueError("The baseline model fingerprint changed.")
    nominal = float(config["parameter"]["nominal_value_mm"])
    baseline_value = float(baseline["outer_parameter"]["baseline_value"])
    if not math.isclose(nominal, baseline_value, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("The Day 15 nominal value differs from the baseline.")
    expected_test = nominal + float(config["parameter"]["test_delta_mm"])
    if not math.isclose(
        expected_test,
        float(config["parameter"]["test_value_mm"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("The Day 15 test value does not match its delta.")
    return source_file, actual_hash


def find_latest_day14_report(config):
    """Find the newest successful Day 14 Solve audit."""

    source = config["source"]
    root = PROJECT_ROOT / source["day14_output_root"]
    matches = list(root.glob("solve_audit_*/" + source["day14_report_name"]))
    if not matches:
        raise FileNotFoundError("No Day 14 Solve audit report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day14_evidence(config, report_file):
    """Require the reviewed Surface 6 MarginalRayAngle evidence."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "task": report.get("task") == source["day14_expected_task"],
        "status": report.get("status") == "success",
        "source unchanged": report.get("source_unchanged") is True,
        "working unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
        "no write": report.get("model_write_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 14 evidence failed: " + ", ".join(failed))

    matching = [
        cell
        for cell in report.get("active_cells", [])
        if cell.get("surface_id") == config["dependent_cell"]["surface_id"]
        and cell.get("cell") == config["dependent_cell"]["cell"]
    ]
    if len(matching) != 1:
        raise ValueError("Surface 6 radius Solve evidence is not unique.")
    cell = matching[0]
    if cell.get("solve_type") != source["expected_surface6_radius_solve"]:
        raise ValueError("The Surface 6 radius Solve type changed.")
    angle = float(cell.get("solve_properties", {}).get("Angle"))
    if not math.isclose(
        angle,
        float(source["expected_surface6_angle"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("The MarginalRayAngle target changed.")
    radius = float(cell["value"])
    if not math.isclose(
        radius,
        float(config["dependent_cell"]["nominal_radius_mm"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("The nominal Surface 6 radius changed.")
    return report, cell


def validate_branch_plan(config):
    """Require two independent branches with one deliberate difference."""

    branches = config["branches"]
    if list(branches) != ["preserve_solve", "freeze_radius"]:
        raise ValueError("Day 15 requires exactly the two reviewed branches.")
    names = [branch["working_name"] for branch in branches.values()]
    if len(names) != len(set(names)):
        raise ValueError("Branch working-copy names must be unique.")
    preserve = branches["preserve_solve"]
    freeze = branches["freeze_radius"]
    if preserve["expected_solve_before"] != preserve["expected_solve_after"]:
        raise ValueError("The preserve branch must retain its Solve.")
    if freeze["expected_solve_before"] != "MarginalRayAngle":
        raise ValueError("The freeze branch must start from MarginalRayAngle.")
    if freeze["expected_solve_after"] != "Fixed":
        raise ValueError("The freeze branch must end with a Fixed radius.")


def main():
    config = load_config("configs/day15_solve_branch_validation.yaml")
    validate_execution_lock(config)
    source_file, source_hash = validate_source_model(config)
    day14_file = find_latest_day14_report(config)
    _, solve_cell = validate_day14_evidence(config, day14_file)
    validate_branch_plan(config)

    parameter = config["parameter"]
    print("========== DAY 15 SOLVE BRANCH PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection or model copy will be created in this step.")
    print("No Quick Focus, Spot, MTF, optimization or SaveAs is allowed.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Day 14 evidence: {day14_file}")
    print()
    print(
        "Audited dependent cell: Surface 6 radius = "
        f"{solve_cell['solve_type']}, "
        f"Angle={solve_cell['solve_properties']['Angle']}"
    )
    print(
        f"Surface 2 test: {parameter['nominal_value_mm']:.7f} -> "
        f"{parameter['test_value_mm']:.7f} mm "
        f"({parameter['test_delta_mm']:+.1f} mm)"
    )
    print()
    print("Planned independent branches:")
    print("  preserve_solve: keep Surface 6 MarginalRayAngle in memory")
    print("  freeze_radius: convert Surface 6 radius to Fixed in memory")
    print("  then write the same Surface 2 test thickness in each branch")
    print("  compare only Surface 6 radius and Solve type")
    print()
    print("[PASS] Frozen baseline model verified")
    print("[PASS] Reviewed Day 14 Solve evidence verified")
    print("[PASS] Two independent working-copy names verified")
    print("[PASS] Exactly one deliberate branch difference declared")
    print("[PASS] This plan step created no connection or model mutation")
    print("[PASS] Quick Focus, optical analyses, optimization and SaveAs locked")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
