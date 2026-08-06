"""Day 15 step 2: validate preserve/freeze Solve behavior in memory."""

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
    set_surface_thickness,
    sha256_file,
)
from scripts.demos.day14_run_lde_solve_audit import (  # noqa: E402
    build_solve_type_names,
    enum_name,
)
from scripts.demos.day15_solve_branch_plan import (  # noqa: E402
    validate_branch_plan,
    validate_day14_evidence,
    validate_execution_lock,
    validate_source_model,
    find_latest_day14_report,
)


def require_reviewed_execution(config):
    """Permit only the three explicitly reviewed in-memory actions."""

    execution = config["execution"]
    required_true = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 in-memory write": execution[
            "allow_surface2_in_memory_write"
        ],
        "Surface 6 MakeSolveFixed": execution[
            "allow_surface6_make_solve_fixed"
        ],
    }
    missing = [name for name, value in required_true.items() if value is not True]
    if missing:
        raise ValueError("Day 15 action not approved: " + ", ".join(missing))

    forbidden = {
        "Quick Focus": execution["allow_quick_focus"],
        "optical analysis": execution["allow_optical_analysis"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 15 action enabled: " + ", ".join(enabled))


def solve_name(cell, solve_type_names):
    """Return the installed-version label for one editor-cell Solve."""

    return enum_name(cell.Solve, solve_type_names)


def read_branch_state(system, config, solve_type_names):
    """Read the two surfaces needed for the structural comparison."""

    changed_id = int(config["parameter"]["changed_surface_id"])
    dependent_id = int(config["dependent_cell"]["surface_id"])
    changed = system.LDE.GetSurfaceAt(changed_id)
    dependent = system.LDE.GetSurfaceAt(dependent_id)
    return {
        "surface2_thickness_mm": float(changed.Thickness),
        "surface6_radius_mm": float(dependent.Radius),
        "surface6_radius_solve": solve_name(
            dependent.RadiusCell,
            solve_type_names,
        ),
        "surface6_thickness_mm": float(dependent.Thickness),
    }


def validate_initial_state(config, state, branch):
    """Require both independent copies to start from the same baseline."""

    if not math.isclose(
        state["surface2_thickness_mm"],
        float(config["parameter"]["nominal_value_mm"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{branch} Surface 2 did not start at nominal.")
    if not math.isclose(
        state["surface6_radius_mm"],
        float(config["dependent_cell"]["nominal_radius_mm"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{branch} Surface 6 radius did not start at nominal.")
    expected = config["branches"][branch]["expected_solve_before"]
    if state["surface6_radius_solve"] != expected:
        raise ValueError(f"{branch} started with the wrong Surface 6 Solve.")


def run_preserve_branch(system, config, solve_type_names, working_file):
    """Change Surface 2 while leaving MarginalRayAngle active."""

    open_working_model(system, working_file)
    before = read_branch_state(system, config, solve_type_names)
    validate_initial_state(config, before, "preserve_solve")
    write = set_surface_thickness(
        system,
        int(config["parameter"]["changed_surface_id"]),
        float(config["parameter"]["test_value_mm"]),
    )
    after = read_branch_state(system, config, solve_type_names)
    expected = config["branches"]["preserve_solve"]["expected_solve_after"]
    if after["surface6_radius_solve"] != expected:
        raise ValueError("The preserve branch lost MarginalRayAngle.")
    return {
        "branch": "preserve_solve",
        "working_copy": str(working_file),
        "before": before,
        "surface2_write": write,
        "after": after,
        "surface6_radius_change_mm": (
            after["surface6_radius_mm"] - before["surface6_radius_mm"]
        ),
        "surface6_thickness_change_mm": (
            after["surface6_thickness_mm"] - before["surface6_thickness_mm"]
        ),
        "make_solve_fixed_used": False,
    }


def run_freeze_branch(system, config, solve_type_names, working_file):
    """Freeze Surface 6 radius before applying the same Surface 2 change."""

    open_working_model(system, working_file)
    before = read_branch_state(system, config, solve_type_names)
    validate_initial_state(config, before, "freeze_radius")
    surface6 = system.LDE.GetSurfaceAt(int(config["dependent_cell"]["surface_id"]))
    fixed_status = bool(surface6.RadiusCell.MakeSolveFixed())
    after_freeze = read_branch_state(system, config, solve_type_names)
    expected = config["branches"]["freeze_radius"]["expected_solve_after"]
    if after_freeze["surface6_radius_solve"] != expected:
        raise ValueError("Surface 6 radius did not become Fixed.")
    if not math.isclose(
        after_freeze["surface6_radius_mm"],
        before["surface6_radius_mm"],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Freezing the Solve changed the current radius value.")

    write = set_surface_thickness(
        system,
        int(config["parameter"]["changed_surface_id"]),
        float(config["parameter"]["test_value_mm"]),
    )
    after = read_branch_state(system, config, solve_type_names)
    if after["surface6_radius_solve"] != expected:
        raise ValueError("The frozen branch lost its Fixed Solve state.")
    return {
        "branch": "freeze_radius",
        "working_copy": str(working_file),
        "before": before,
        "make_solve_fixed_returned": fixed_status,
        "after_freeze": after_freeze,
        "surface2_write": write,
        "after": after,
        "surface6_radius_change_mm": (
            after["surface6_radius_mm"] - before["surface6_radius_mm"]
        ),
        "surface6_thickness_change_mm": (
            after["surface6_thickness_mm"] - before["surface6_thickness_mm"]
        ),
        "make_solve_fixed_used": True,
    }


def validate_comparison(config, preserve, frozen):
    """Require the expected structural contrast and no focus movement."""

    minimum = float(
        config["guardrails"]["minimum_expected_preserve_radius_change_mm"]
    )
    maximum = float(
        config["guardrails"]["maximum_allowed_frozen_radius_change_mm"]
    )
    if abs(preserve["surface6_radius_change_mm"]) < minimum:
        raise ValueError("The preserved Solve did not produce a radius response.")
    if abs(frozen["surface6_radius_change_mm"]) > maximum:
        raise ValueError("The frozen Surface 6 radius changed unexpectedly.")
    for result in (preserve, frozen):
        if not math.isclose(
            result["surface2_write"]["actual_thickness"],
            float(config["parameter"]["test_value_mm"]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(f"{result['branch']} Surface 2 write is incorrect.")
        if abs(result["surface6_thickness_change_mm"]) > 1e-12:
            raise ValueError(f"{result['branch']} moved the image plane.")
    return {
        "surface6_radius_difference_between_branches_mm": (
            preserve["after"]["surface6_radius_mm"]
            - frozen["after"]["surface6_radius_mm"]
        )
    }


def main():
    config = load_config("configs/day15_solve_branch_validation.yaml")
    validate_execution_lock(config)
    require_reviewed_execution(config)
    validate_branch_plan(config)
    source_file, source_hash_before = validate_source_model(config)
    day14_file = find_latest_day14_report(config)
    validate_day14_evidence(config, day14_file)

    run_id = datetime.now().strftime("solve_branch_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    preserve_dir = run_dir / "preserve_solve"
    freeze_dir = run_dir / "freeze_radius"
    preserve_copy = copy_baseline_model(
        source_file,
        preserve_dir,
        config["branches"]["preserve_solve"]["working_name"],
    )
    freeze_copy = copy_baseline_model(
        source_file,
        freeze_dir,
        config["branches"]["freeze_radius"]["working_name"],
    )
    preserve_file = Path(preserve_copy["working_file"])
    freeze_file = Path(freeze_copy["working_file"])
    preserve_hash_before = sha256_file(preserve_file)
    freeze_hash_before = sha256_file(freeze_file)

    print("========== DAY 15 SOLVE BRANCH VALIDATION ==========")
    print(f"Source model: {source_file}")
    print(f"Preserve branch: {preserve_file}")
    print(f"Freeze branch: {freeze_file}")
    print("No Quick Focus, optical analysis, optimization or SaveAs will be used.")

    with StandaloneZemaxConnection() as connection:
        connection_info = connection.info()
        solve_type_names = build_solve_type_names(connection.ZOSAPI)
        print("[PASS] ZOS-API connection")
        preserve = run_preserve_branch(
            connection.system,
            config,
            solve_type_names,
            preserve_file,
        )
        print("[PASS] Preserve-Solve branch completed in memory")
        frozen = run_freeze_branch(
            connection.system,
            config,
            solve_type_names,
            freeze_file,
        )
        print("[PASS] Freeze-radius branch completed in memory")
        comparison = validate_comparison(config, preserve, frozen)

    source_hash_after = sha256_file(source_file).upper()
    preserve_hash_after = sha256_file(preserve_file)
    freeze_hash_after = sha256_file(freeze_file)
    source_unchanged = source_hash_after == source_hash_before
    preserve_disk_unchanged = preserve_hash_after == preserve_hash_before
    freeze_disk_unchanged = freeze_hash_after == freeze_hash_before
    if not source_unchanged:
        raise RuntimeError("The baseline source changed during Day 15.")
    if not preserve_disk_unchanged or not freeze_disk_unchanged:
        raise RuntimeError("A Day 15 disk working copy changed.")

    report = {
        "task": "day15_solve_branch_validation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "source_unchanged": source_unchanged,
        "source_day14_report": str(day14_file),
        "connection": connection_info,
        "connection_closed": connection.closed,
        "quick_focus_used": False,
        "optical_analysis_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "preserve_branch": preserve,
        "freeze_branch": frozen,
        "comparison": comparison,
        "preserve_working_copy_unchanged": preserve_disk_unchanged,
        "freeze_working_copy_unchanged": freeze_disk_unchanged,
    }
    report_file = run_dir / "solve_branch_validation.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("Preserve-Solve branch:")
    print(
        f"  Surface 6 radius: {preserve['before']['surface6_radius_mm']:.10f} "
        f"-> {preserve['after']['surface6_radius_mm']:.10f} mm"
    )
    print(
        f"  Solve: {preserve['before']['surface6_radius_solve']} "
        f"-> {preserve['after']['surface6_radius_solve']}"
    )
    print("Freeze-radius branch:")
    print(
        f"  Surface 6 radius: {frozen['before']['surface6_radius_mm']:.10f} "
        f"-> {frozen['after']['surface6_radius_mm']:.10f} mm"
    )
    print(
        f"  Solve: {frozen['before']['surface6_radius_solve']} "
        f"-> {frozen['after']['surface6_radius_solve']}"
    )
    print(
        "Radius difference after the same Surface 2 change: "
        f"{comparison['surface6_radius_difference_between_branches_mm']:+.10f} mm"
    )
    print()
    print(f"[PASS] Connection closed: {connection.closed}")
    print(f"[PASS] Original model unchanged: {source_unchanged}")
    print(f"[PASS] Preserve disk copy unchanged: {preserve_disk_unchanged}")
    print(f"[PASS] Freeze disk copy unchanged: {freeze_disk_unchanged}")
    print("[PASS] Changes existed only in Zemax memory")
    print("[PASS] No Quick Focus, optical analysis, optimization or SaveAs")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
