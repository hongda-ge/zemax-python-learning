"""Day 16 step 2: compare focused Spot performance for two Solve branches."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.analysis_ops import (  # noqa: E402
    export_standard_spot_text,
    parse_standard_spot_text,
)
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.focus_ops import run_quick_focus  # noqa: E402
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
from scripts.demos.day16_solve_branch_spot_plan import (  # noqa: E402
    find_latest_day15_report,
    validate_branch_plan,
    validate_common_analysis,
    validate_day15_evidence,
    validate_plan_lock,
    validate_source,
)


def require_reviewed_execution(config):
    """Permit only the five actions approved after plan review."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 in-memory write": execution[
            "allow_surface2_in_memory_write"
        ],
        "Surface 6 MakeSolveFixed": execution[
            "allow_surface6_make_solve_fixed"
        ],
        "Quick Focus": execution["allow_quick_focus"],
        "Standard Spot": execution["allow_standard_spot"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 16 action not approved: " + ", ".join(missing))
    forbidden = {
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 16 action enabled: " + ", ".join(enabled))


def read_state(system, config, solve_type_names):
    """Read the structural state shared by both branches."""

    surface2 = system.LDE.GetSurfaceAt(int(config["parameter"]["surface_id"]))
    surface6 = system.LDE.GetSurfaceAt(
        int(config["dependent_cell"]["surface_id"])
    )
    return {
        "surface2_thickness_mm": float(surface2.Thickness),
        "surface6_radius_mm": float(surface6.Radius),
        "surface6_radius_solve": enum_name(
            surface6.RadiusCell.Solve,
            solve_type_names,
        ),
        "surface6_thickness_mm": float(surface6.Thickness),
    }


def validate_initial_state(config, state):
    """Require a fresh copy of the frozen baseline model."""

    checks = (
        (
            state["surface2_thickness_mm"],
            float(config["parameter"]["nominal_value_mm"]),
            "Surface 2 thickness",
        ),
        (
            state["surface6_radius_mm"],
            float(config["dependent_cell"]["nominal_radius_mm"]),
            "Surface 6 radius",
        ),
    )
    for actual, expected, label in checks:
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Initial {label} differs from the baseline.")
    if state["surface6_radius_solve"] != "MarginalRayAngle":
        raise ValueError("Initial Surface 6 radius Solve is not MarginalRayAngle.")


def validate_spot_fields(config, spot_metrics):
    """Require the frozen centroid reference and three expected fields."""

    if spot_metrics["reference"] != "质心":
        raise ValueError("Standard Spot did not use the centroid reference.")
    actual = sorted(
        round(float(field["field_y_degree"]), 9)
        for field in spot_metrics["fields"]
    )
    expected = sorted(
        round(float(value), 9)
        for value in config["analysis"]["expected_field_y_degrees"]
    )
    if actual != expected:
        raise ValueError(f"Unexpected Standard Spot fields: {actual}.")


def summarize_spot(spot_metrics):
    """Build transparent equal-field descriptive metrics."""

    fields = sorted(
        spot_metrics["fields"],
        key=lambda item: float(item["field_y_degree"]),
    )
    rms_values = [float(field["rms_radius_um"]) for field in fields]
    return {
        "fields": fields,
        "equal_field_mean_rms_um": sum(rms_values) / len(rms_values),
        "worst_field_rms_um": max(rms_values),
    }


def execute_branch(
    config,
    branch_name,
    working_file,
    branch_dir,
    task_name="day16_solve_branch_spot_comparison",
):
    """Execute one isolated branch and always leave an audit report."""

    source_file = Path(config["_source_file"])
    source_hash_before = sha256_file(source_file).upper()
    working_hash_before = sha256_file(working_file).upper()
    result_file = branch_dir / "result.json"
    result = {
        "task": task_name,
        "status": "failed",
        "branch": branch_name,
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "working_copy": str(working_file),
        "source_sha256_before": source_hash_before,
        "working_sha256_before": working_hash_before,
        "connection_closed": False,
        "optimization_used": False,
        "save_as_used": False,
    }
    connection = None
    caught_error = None

    try:
        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        solve_type_names = build_solve_type_names(connection.ZOSAPI)
        open_working_model(connection.system, working_file)
        before = read_state(connection.system, config, solve_type_names)
        validate_initial_state(config, before)
        result["before"] = before

        if branch_name == "freeze_radius":
            surface6 = connection.system.LDE.GetSurfaceAt(
                int(config["dependent_cell"]["surface_id"])
            )
            result["make_solve_fixed_returned"] = bool(
                surface6.RadiusCell.MakeSolveFixed()
            )
            after_branch_setup = read_state(
                connection.system,
                config,
                solve_type_names,
            )
            if after_branch_setup["surface6_radius_solve"] != "Fixed":
                raise ValueError("Freeze branch did not make Surface 6 Fixed.")
            if not math.isclose(
                after_branch_setup["surface6_radius_mm"],
                before["surface6_radius_mm"],
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError("MakeSolveFixed changed the radius value.")
        else:
            after_branch_setup = before.copy()
        result["after_branch_setup"] = after_branch_setup

        result["surface2_write"] = set_surface_thickness(
            connection.system,
            int(config["parameter"]["surface_id"]),
            float(config["parameter"]["test_value_mm"]),
        )
        after_write = read_state(connection.system, config, solve_type_names)
        expected_solve = config["branches"][branch_name][
            "expected_radius_solve"
        ]
        if after_write["surface6_radius_solve"] != expected_solve:
            raise ValueError(f"{branch_name} has the wrong Solve after write.")
        if not math.isclose(
            after_write["surface2_thickness_mm"],
            float(config["parameter"]["test_value_mm"]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(f"{branch_name} has the wrong Surface 2 value.")
        if branch_name == "freeze_radius" and not math.isclose(
            after_write["surface6_radius_mm"],
            before["surface6_radius_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Frozen Surface 6 radius changed after write.")
        result["after_surface2_write"] = after_write

        focus = run_quick_focus(
            connection.system,
            connection.ZOSAPI,
            use_centroid=True,
        )
        lower, upper = config["compensation"][
            "approved_thickness_range_mm"
        ]
        if not float(lower) <= focus["thickness_after_mm"] <= float(upper):
            raise ValueError(
                "Quick Focus result is outside the approved range: "
                f"{focus['thickness_after_mm']} mm."
            )
        after_focus = read_state(connection.system, config, solve_type_names)
        if after_focus["surface6_radius_solve"] != expected_solve:
            raise ValueError(f"{branch_name} lost its Solve after Quick Focus.")
        result["focus"] = focus
        result["after_focus"] = after_focus

        spot_file = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            branch_dir / f"{branch_name}_standard_spot.txt",
        )
        spot_metrics = parse_standard_spot_text(spot_file)
        validate_spot_fields(config, spot_metrics)
        result["spot_text"] = str(spot_file)
        result["spot_metrics"] = spot_metrics
        result["spot_summary"] = summarize_spot(spot_metrics)
        result["status"] = "success"

    except Exception as exc:
        caught_error = exc
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed
        source_hash_after = sha256_file(source_file).upper()
        working_hash_after = sha256_file(working_file).upper()
        result["source_sha256_after"] = source_hash_after
        result["working_sha256_after"] = working_hash_after
        result["source_unchanged"] = source_hash_after == source_hash_before
        result["working_copy_unchanged"] = (
            working_hash_after == working_hash_before
        )
        if not result["source_unchanged"] and caught_error is None:
            caught_error = RuntimeError("Day 16 changed the source model.")
        if not result["working_copy_unchanged"] and caught_error is None:
            caught_error = RuntimeError("Day 16 changed a disk working copy.")
        if not result["connection_closed"] and caught_error is None:
            caught_error = RuntimeError("Day 16 connection did not close.")
        if caught_error is not None:
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }
        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if caught_error is not None:
        raise caught_error
    return result


def compare_results(preserve, frozen):
    """Compare matching fields without creating a hidden score."""

    preserve_fields = {
        float(field["field_y_degree"]): float(field["rms_radius_um"])
        for field in preserve["spot_summary"]["fields"]
    }
    frozen_fields = {
        float(field["field_y_degree"]): float(field["rms_radius_um"])
        for field in frozen["spot_summary"]["fields"]
    }
    if preserve_fields.keys() != frozen_fields.keys():
        raise ValueError("The two branches do not contain matching fields.")
    field_comparison = []
    for angle in sorted(preserve_fields):
        preserve_rms = preserve_fields[angle]
        frozen_rms = frozen_fields[angle]
        field_comparison.append(
            {
                "field_y_degree": angle,
                "preserve_rms_um": preserve_rms,
                "frozen_rms_um": frozen_rms,
                "frozen_minus_preserve_rms_um": frozen_rms - preserve_rms,
                "frozen_vs_preserve_percent": (
                    (frozen_rms / preserve_rms - 1.0) * 100.0
                ),
            }
        )
    preserve_summary = preserve["spot_summary"]
    frozen_summary = frozen["spot_summary"]
    return {
        "field_comparison": field_comparison,
        "surface6_radius_difference_after_write_mm": (
            preserve["after_surface2_write"]["surface6_radius_mm"]
            - frozen["after_surface2_write"]["surface6_radius_mm"]
        ),
        "focus_shift_difference_frozen_minus_preserve_mm": (
            frozen["focus"]["focus_shift_mm"]
            - preserve["focus"]["focus_shift_mm"]
        ),
        "mean_rms_difference_frozen_minus_preserve_um": (
            frozen_summary["equal_field_mean_rms_um"]
            - preserve_summary["equal_field_mean_rms_um"]
        ),
        "worst_rms_difference_frozen_minus_preserve_um": (
            frozen_summary["worst_field_rms_um"]
            - preserve_summary["worst_field_rms_um"]
        ),
        "unique_engineering_winner": None,
    }


def print_branch(result):
    """Print one branch in an optics-first form."""

    state = result["after_surface2_write"]
    focus = result["focus"]
    summary = result["spot_summary"]
    print(f"{result['branch']}:")
    print(
        f"  Surface 6 radius/Solve: {state['surface6_radius_mm']:.10f} mm / "
        f"{state['surface6_radius_solve']}"
    )
    print(
        f"  Quick Focus: {focus['thickness_before_mm']:.7f} -> "
        f"{focus['thickness_after_mm']:.7f} mm "
        f"({focus['focus_shift_mm']:+.7f} mm)"
    )
    for field in summary["fields"]:
        print(
            f"  Field {field['field_y_degree']:.1f} deg RMS: "
            f"{field['rms_radius_um']:.3f} um"
        )
    print(
        f"  Mean/worst RMS: {summary['equal_field_mean_rms_um']:.3f} / "
        f"{summary['worst_field_rms_um']:.3f} um"
    )


def main():
    config = load_config("configs/day16_solve_branch_spot_comparison.yaml")
    validate_plan_lock(config)
    require_reviewed_execution(config)
    validate_branch_plan(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_common_analysis(config, baseline)
    day15_file = find_latest_day15_report(config)
    validate_day15_evidence(config, day15_file)
    config["_source_file"] = str(source_file)

    run_id = datetime.now().strftime("spot_comparison_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    results = {}

    print("========== DAY 16 SOLVE-BRANCH SPOT COMPARISON ==========")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Approved Day 15 evidence: {day15_file}")
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        branch_dir = run_dir / branch_name
        copy_info = copy_baseline_model(
            source_file,
            branch_dir,
            config["branches"][branch_name]["working_name"],
        )
        print(f"\nRunning {branch_name}...")
        result = execute_branch(
            config,
            branch_name,
            Path(copy_info["working_file"]),
            branch_dir,
        )
        results[branch_name] = result
        print("[PASS] Branch completed; connection closed and hashes unchanged")

    comparison = compare_results(
        results["preserve_solve"],
        results["freeze_radius"],
    )
    report = {
        "task": "day16_solve_branch_spot_comparison",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day15_report": str(day15_file),
        "parameter": config["parameter"],
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "comparison": comparison,
        "optimization_used": False,
        "save_as_used": False,
    }
    report_file = run_dir / "solve_branch_spot_comparison.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 16 COMPARISON ==========")
    print_branch(results["preserve_solve"])
    print_branch(results["freeze_radius"])
    print("\nFrozen minus preserve Spot difference:")
    for field in comparison["field_comparison"]:
        print(
            f"  Field {field['field_y_degree']:.1f} deg: "
            f"{field['frozen_minus_preserve_rms_um']:+.3f} um "
            f"({field['frozen_vs_preserve_percent']:+.2f}%)"
        )
    print(
        "  Mean RMS difference: "
        f"{comparison['mean_rms_difference_frozen_minus_preserve_um']:+.3f} um"
    )
    print(
        "  Worst RMS difference: "
        f"{comparison['worst_rms_difference_frozen_minus_preserve_um']:+.3f} um"
    )
    print("[RESULT] Unique engineering winner: NONE (single teaching case)")
    print("[PASS] No hidden score, optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
