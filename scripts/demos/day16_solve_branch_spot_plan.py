"""Day 16 step 1: audit the two-branch Quick Focus and Spot plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_plan_lock(config):
    """Keep the plan offline while retaining reviewed action flags."""

    execution = config["execution"]
    locked = {
        "generic execution": execution["enabled"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in locked.items() if value is not False]
    if enabled:
        raise ValueError("Day 16 plan lock failed: " + ", ".join(enabled))

    reviewed = (
        "allow_zosapi_connection",
        "allow_surface2_in_memory_write",
        "allow_surface6_make_solve_fixed",
        "allow_quick_focus",
        "allow_standard_spot",
    )
    for key in reviewed:
        if not isinstance(execution[key], bool):
            raise ValueError(f"{key} must be Boolean.")


def validate_source(config):
    """Verify the frozen source model and parameter definition."""

    baseline = load_config(config["source"]["baseline_config"])
    source_file = PROJECT_ROOT / baseline["model"]["source_file"]
    actual_hash = sha256_file(source_file).upper()
    expected_hash = str(config["source"]["expected_source_sha256"]).upper()
    baseline_hash = str(baseline["model"]["source_sha256"]).upper()
    if actual_hash != expected_hash or actual_hash != baseline_hash:
        raise ValueError("The frozen source-model fingerprint changed.")

    parameter = config["parameter"]
    outer = baseline["outer_parameter"]
    if int(parameter["surface_id"]) != int(outer["surface"]):
        raise ValueError("Day 16 uses the wrong outer-parameter surface.")
    if parameter["property"] != outer["property"]:
        raise ValueError("Day 16 uses the wrong outer-parameter property.")
    if not math.isclose(
        float(parameter["nominal_value_mm"]),
        float(outer["baseline_value"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Day 16 nominal thickness differs from baseline.")
    calculated = float(parameter["nominal_value_mm"]) + float(
        parameter["test_delta_mm"]
    )
    if not math.isclose(
        calculated,
        float(parameter["test_value_mm"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Day 16 test thickness does not match its delta.")
    return baseline, source_file, actual_hash


def find_latest_day15_report(config):
    """Find the newest completed Day 15 structural comparison."""

    source = config["source"]
    root = PROJECT_ROOT / source["day15_output_root"]
    matches = list(root.glob("solve_branch_*/" + source["day15_report_name"]))
    if not matches:
        raise FileNotFoundError("No Day 15 structural report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day15_evidence(config, report_file):
    """Require the reviewed Day 15 causal evidence and safety audit."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "task": report.get("task") == source["day15_expected_task"],
        "status": report.get("status") == source["day15_expected_status"],
        "source unchanged": report.get("source_unchanged") is True,
        "preserve copy unchanged": (
            report.get("preserve_working_copy_unchanged") is True
        ),
        "freeze copy unchanged": (
            report.get("freeze_working_copy_unchanged") is True
        ),
        "connection closed": report.get("connection_closed") is True,
        "no Quick Focus": report.get("quick_focus_used") is False,
        "no optical analysis": report.get("optical_analysis_used") is False,
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 15 evidence failed: " + ", ".join(failed))

    parameter = config["parameter"]
    expected_target = float(parameter["test_value_mm"])
    branches = report["preserve_branch"], report["freeze_branch"]
    for branch in branches:
        actual = float(branch["surface2_write"]["actual_thickness"])
        if not math.isclose(actual, expected_target, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("A Day 15 branch used the wrong Surface 2 value.")

    preserve = report["preserve_branch"]
    frozen = report["freeze_branch"]
    if preserve["after"]["surface6_radius_solve"] != "MarginalRayAngle":
        raise ValueError("Day 15 preserve branch lost its Solve evidence.")
    if frozen["after"]["surface6_radius_solve"] != "Fixed":
        raise ValueError("Day 15 freeze branch lost its Fixed evidence.")
    if abs(float(preserve["surface6_radius_change_mm"])) <= 1e-6:
        raise ValueError("Day 15 preserve branch had no radius response.")
    if abs(float(frozen["surface6_radius_change_mm"])) > 1e-9:
        raise ValueError("Day 15 frozen radius changed unexpectedly.")
    return report


def validate_common_analysis(config, baseline):
    """Freeze one identical compensation and Spot recipe for both branches."""

    compensation = config["compensation"]
    if compensation != {
        "tool": "QuickFocus",
        "criterion": "spot_size_radial",
        "use_centroid": True,
        "focus_surface_id": 6,
        "approved_thickness_range_mm": [40.0, 44.5],
    }:
        raise ValueError("The Day 16 Quick Focus recipe changed.")

    expected_spot = {
        "type": "Standard_Spot",
        "ray_density": 6,
        "pattern": "hexapolar",
        "fields": "all",
        "wavelengths": "all",
        "surface": "image",
        "reference": "centroid",
        "polarization": False,
    }
    spot = config["analysis"]
    for key, value in expected_spot.items():
        if spot[key] != value:
            raise ValueError(f"Day 16 Standard Spot setting changed: {key}.")
        if baseline["analysis"]["standard_spot"][key] != value:
            raise ValueError(f"Baseline Standard Spot differs at {key}.")
    if [float(value) for value in spot["expected_field_y_degrees"]] != [
        0.0,
        14.0,
        20.0,
    ]:
        raise ValueError("Day 16 expected fields changed.")


def validate_branch_plan(config):
    """Require two independent branches and descriptive comparison only."""

    branches = config["branches"]
    if list(branches) != ["preserve_solve", "freeze_radius"]:
        raise ValueError("Day 16 requires exactly two reviewed branches.")
    names = [branch["working_name"] for branch in branches.values()]
    if len(names) != len(set(names)):
        raise ValueError("Day 16 working-copy names are not unique.")
    if branches["preserve_solve"]["expected_radius_solve"] != "MarginalRayAngle":
        raise ValueError("The preserve branch must keep MarginalRayAngle.")
    if branches["freeze_radius"]["expected_radius_solve"] != "Fixed":
        raise ValueError("The freeze branch must use Fixed radius.")
    if config["comparison"]["allow_unique_engineering_winner"] is not False:
        raise ValueError("Day 16 must not declare an engineering winner.")


def main():
    config = load_config("configs/day16_solve_branch_spot_comparison.yaml")
    validate_plan_lock(config)
    baseline, source_file, source_hash = validate_source(config)
    day15_file = find_latest_day15_report(config)
    day15 = validate_day15_evidence(config, day15_file)
    validate_common_analysis(config, baseline)
    validate_branch_plan(config)

    parameter = config["parameter"]
    preserve_change = day15["preserve_branch"]["surface6_radius_change_mm"]
    print("========== DAY 16 SOLVE-BRANCH SPOT PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection or model copy will be created.")
    print("No Quick Focus, Spot, optimization or SaveAs will run in this step.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Approved Day 15 evidence: {day15_file}")
    print()
    print(
        f"Common Surface 2 test: {parameter['nominal_value_mm']:.7f} -> "
        f"{parameter['test_value_mm']:.7f} mm"
    )
    print(
        "Day 15 verified preserve-branch radius response: "
        f"{preserve_change:+.10f} mm"
    )
    print()
    print("Planned independent branches:")
    print("  preserve_solve: keep Surface 6 MarginalRayAngle")
    print("  freeze_radius: convert Surface 6 radius to Fixed")
    print("  both: write the same Surface 2 thickness")
    print("  both: run radial-spot Quick Focus with centroid")
    print("  both: export the same centroid Standard Spot")
    print()
    print("Planned descriptive comparison:")
    print("  Surface 6 radius after the Surface 2 write")
    print("  Quick Focus shift and focused image distance")
    print("  RMS Spot at fields 0, 14 and 20 degrees")
    print("  equal-field mean RMS and worst-field RMS")
    print()
    print("[PASS] Frozen source model verified")
    print("[PASS] Reviewed Day 15 causal and safety evidence verified")
    print("[PASS] Two independent branch names verified")
    print("[PASS] Identical Quick Focus and Standard Spot recipes frozen")
    print("[PASS] Optimization, SaveAs and engineering winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
