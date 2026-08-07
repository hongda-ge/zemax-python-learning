"""Day 18 step 2: validate paired Spot states at the negative endpoint."""

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
)
from scripts.demos.day16_run_solve_branch_spot_comparison import (  # noqa: E402
    read_state,
    summarize_spot,
    validate_initial_state,
    validate_spot_fields,
)
from scripts.demos.day18_focus_compensation_plan import (  # noqa: E402
    build_endpoint_plan,
    find_latest_day17_reports,
    validate_common_recipe,
    validate_day17_evidence,
    validate_plan_lock,
    validate_source,
)


def require_negative_endpoint_approval(config):
    """Allow endpoint 001 while endpoint 002 remains locked."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 write": execution["allow_surface2_in_memory_write"],
        "MakeSolveFixed": execution["allow_surface6_make_solve_fixed"],
        "uncompensated Spot": execution[
            "allow_uncompensated_standard_spot"
        ],
        "Quick Focus": execution["allow_quick_focus"],
        "compensated Spot": execution[
            "allow_compensated_standard_spot"
        ],
        "endpoint 001": execution["allow_endpoint_001_execution"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 18 validation not approved: " + ", ".join(missing))
    forbidden = {
        "endpoint 002": execution["allow_endpoint_002_execution"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 18 validation action: " + ", ".join(enabled))


def compare_spot(first, second):
    """Return second-minus-first RMS differences for matching fields."""

    first_fields = {
        float(field["field_y_degree"]): float(field["rms_radius_um"])
        for field in first["fields"]
    }
    second_fields = {
        float(field["field_y_degree"]): float(field["rms_radius_um"])
        for field in second["fields"]
    }
    if first_fields.keys() != second_fields.keys():
        raise ValueError("Spot observations contain different fields.")
    fields = []
    for angle in sorted(first_fields):
        before = first_fields[angle]
        after = second_fields[angle]
        fields.append(
            {
                "field_y_degree": angle,
                "first_rms_um": before,
                "second_rms_um": after,
                "second_minus_first_rms_um": after - before,
                "second_vs_first_percent": (after / before - 1.0) * 100.0,
            }
        )
    return {
        "fields": fields,
        "mean_difference_um": (
            float(second["equal_field_mean_rms_um"])
            - float(first["equal_field_mean_rms_um"])
        ),
        "worst_difference_um": (
            float(second["worst_field_rms_um"])
            - float(first["worst_field_rms_um"])
        ),
    }


def execute_paired_branch(config, endpoint, branch_name, branch_dir, source_file):
    """Export fixed-image Spot, then Quick Focus and focused Spot."""

    working_name = (
        f"{endpoint['endpoint_id']}_"
        f"{config['branches'][branch_name]['working_suffix']}"
    )
    copy_info = copy_baseline_model(source_file, branch_dir, working_name)
    working_file = Path(copy_info["working_file"])
    source_hash_before = sha256_file(source_file).upper()
    working_hash_before = sha256_file(working_file).upper()
    result_file = branch_dir / "result.json"
    result = {
        "task": "day18_negative_endpoint_validation",
        "status": "failed",
        "endpoint": endpoint,
        "branch": branch_name,
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
        execution_config = {
            "parameter": {
                "surface_id": int(config["parameter"]["surface_id"]),
                "nominal_value_mm": float(config["parameter"]["baseline_value_mm"]),
            },
            "dependent_cell": config["dependent_cell"],
        }
        validate_initial_state(execution_config, before)
        result["before"] = before

        surface6 = connection.system.LDE.GetSurfaceAt(
            int(config["dependent_cell"]["surface_id"])
        )
        if branch_name == "freeze_radius":
            result["make_solve_fixed_returned"] = bool(
                surface6.RadiusCell.MakeSolveFixed()
            )
        after_setup = read_state(connection.system, config, solve_type_names)
        expected_solve = config["branches"][branch_name][
            "expected_radius_solve"
        ]
        if after_setup["surface6_radius_solve"] != expected_solve:
            raise ValueError(f"{branch_name} has the wrong Solve after setup.")
        if not math.isclose(
            after_setup["surface6_radius_mm"],
            before["surface6_radius_mm"],
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("Branch setup changed the current radius value.")
        result["after_branch_setup"] = after_setup

        result["surface2_write"] = set_surface_thickness(
            connection.system,
            int(config["parameter"]["surface_id"]),
            float(endpoint["value_mm"]),
        )
        after_write = read_state(connection.system, config, solve_type_names)
        if after_write["surface6_radius_solve"] != expected_solve:
            raise ValueError(f"{branch_name} lost its Solve after thickness write.")
        if not math.isclose(
            after_write["surface6_thickness_mm"],
            float(config["observation_states"]["uncompensated"]["image_distance_mm"]),
            rel_tol=0.0,
            abs_tol=float(
                config["guardrails"][
                    "uncompensated_image_distance_tolerance_mm"
                ]
            ),
        ):
            raise ValueError("The uncompensated image plane moved unexpectedly.")
        result["after_surface2_write"] = after_write

        uncompensated_file = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            branch_dir / f"{branch_name}_uncompensated_standard_spot.txt",
        )
        uncompensated_metrics = parse_standard_spot_text(uncompensated_file)
        validate_spot_fields(config, uncompensated_metrics)
        uncompensated_summary = summarize_spot(uncompensated_metrics)
        result["uncompensated_spot_text"] = str(uncompensated_file)
        result["uncompensated_spot_metrics"] = uncompensated_metrics
        result["uncompensated_spot_summary"] = uncompensated_summary

        focus = run_quick_focus(
            connection.system,
            connection.ZOSAPI,
            use_centroid=True,
        )
        lower, upper = config["observation_states"]["compensated"][
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

        compensated_file = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            branch_dir / f"{branch_name}_compensated_standard_spot.txt",
        )
        compensated_metrics = parse_standard_spot_text(compensated_file)
        validate_spot_fields(config, compensated_metrics)
        compensated_summary = summarize_spot(compensated_metrics)
        result["compensated_spot_text"] = str(compensated_file)
        result["compensated_spot_metrics"] = compensated_metrics
        result["compensated_spot_summary"] = compensated_summary
        result["compensation_effect"] = compare_spot(
            uncompensated_summary,
            compensated_summary,
        )
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
            caught_error = RuntimeError("Day 18 changed the source model.")
        if not result["working_copy_unchanged"] and caught_error is None:
            caught_error = RuntimeError("Day 18 changed a disk working copy.")
        if not result["connection_closed"] and caught_error is None:
            caught_error = RuntimeError("Day 18 connection did not close.")
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


def validate_day17_reproduction(config, endpoint_evidence, branch_results):
    """Require compensated results to reproduce Day 17 at this endpoint."""

    guardrails = config["guardrails"]
    reproduction = {}
    for branch_name, result in branch_results.items():
        expected_branch = endpoint_evidence[branch_name]
        focus_difference = abs(
            float(result["focus"]["focus_shift_mm"])
            - float(expected_branch["focus"]["focus_shift_mm"])
        )
        fields = {
            float(field["field_y_degree"]): float(field["rms_radius_um"])
            for field in result["compensated_spot_summary"]["fields"]
        }
        expected_fields = {
            float(field["field_y_degree"]): float(field["rms_radius_um"])
            for field in expected_branch["spot_summary"]["fields"]
        }
        field_differences = {
            angle: fields[angle] - expected_fields[angle]
            for angle in expected_fields
        }
        maximum_field_difference = max(
            abs(value) for value in field_differences.values()
        )
        if focus_difference > float(
            guardrails["compensated_reproduction_max_focus_difference_mm"]
        ):
            raise ValueError(f"{branch_name} did not reproduce Day 17 focus.")
        if maximum_field_difference > float(
            guardrails["compensated_reproduction_max_field_rms_difference_um"]
        ):
            raise ValueError(f"{branch_name} did not reproduce Day 17 Spot.")
        reproduction[branch_name] = {
            "focus_shift_difference_mm": focus_difference,
            "field_rms_differences_um": field_differences,
            "maximum_field_rms_difference_um": maximum_field_difference,
        }
    return reproduction


def print_paired_branch(result):
    """Print uncompensated and compensated Spot for one branch."""

    print(f"{result['branch']}:")
    print(
        "  Surface 6 radius/Solve: "
        f"{result['after_surface2_write']['surface6_radius_mm']:.10f} mm / "
        f"{result['after_surface2_write']['surface6_radius_solve']}"
    )
    before_fields = result["uncompensated_spot_summary"]["fields"]
    after_fields = result["compensated_spot_summary"]["fields"]
    for before, after in zip(before_fields, after_fields):
        print(
            f"  Field {before['field_y_degree']:.1f} deg RMS: "
            f"fixed image {before['rms_radius_um']:.3f} -> "
            f"focused {after['rms_radius_um']:.3f} um"
        )
    print(
        "  Mean RMS: "
        f"{result['uncompensated_spot_summary']['equal_field_mean_rms_um']:.3f} "
        f"-> {result['compensated_spot_summary']['equal_field_mean_rms_um']:.3f} um"
    )
    print(
        f"  Quick Focus shift: {result['focus']['focus_shift_mm']:+.7f} mm"
    )


def main():
    config = load_config("configs/day18_focus_compensation_effect.yaml")
    validate_plan_lock(config)
    require_negative_endpoint_approval(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_common_recipe(config, baseline)
    batch_file, analysis_file = find_latest_day17_reports(config)
    _, _, endpoint_rows = validate_day17_evidence(
        config,
        batch_file,
        analysis_file,
    )
    endpoints = build_endpoint_plan(config)
    endpoint = endpoints[0]
    if not math.isclose(endpoint["delta_mm"], -0.4, abs_tol=1e-12):
        raise ValueError("The Day 18 validation endpoint is not -0.4 mm.")
    evidence_by_delta = {
        round(float(row["delta_mm"]), 7): row for row in endpoint_rows
    }
    endpoint_row = evidence_by_delta[round(endpoint["delta_mm"], 7)]
    day17_batch = json.loads(batch_file.read_text(encoding="utf-8"))
    endpoint_evidence = next(
        result
        for result in day17_batch["new_results"]
        if math.isclose(
            float(result["case"]["delta_mm"]),
            endpoint["delta_mm"],
            abs_tol=1e-12,
        )
    )

    run_id = datetime.now().strftime("negative_endpoint_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    endpoint_dir = run_dir / endpoint["directory_name"]
    results = {}

    print("========== DAY 18 NEGATIVE-ENDPOINT VALIDATION ==========")
    print("Only endpoint_001 will run; endpoint_002 remains locked.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(
        f"Endpoint: {endpoint['value_mm']:.7f} mm "
        f"(delta {endpoint['delta_mm']:+.1f} mm)"
    )
    print("Each branch exports fixed-image Spot, then Quick Focus and focused Spot.")
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        print(f"\nRunning {branch_name}...")
        results[branch_name] = execute_paired_branch(
            config,
            endpoint,
            branch_name,
            endpoint_dir / branch_name,
            source_file,
        )
        print("[PASS] Paired branch completed; connection closed and hashes unchanged")

    reproduction = validate_day17_reproduction(
        config,
        endpoint_evidence,
        results,
    )
    uncompensated_branch_difference = compare_spot(
        results["preserve_solve"]["uncompensated_spot_summary"],
        results["freeze_radius"]["uncompensated_spot_summary"],
    )
    compensated_branch_difference = compare_spot(
        results["preserve_solve"]["compensated_spot_summary"],
        results["freeze_radius"]["compensated_spot_summary"],
    )
    report = {
        "task": "day18_negative_endpoint_validation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day17_batch_report": str(batch_file),
        "source_day17_analysis_report": str(analysis_file),
        "endpoint": endpoint,
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "day17_reproduction": reproduction,
        "uncompensated_branch_difference": uncompensated_branch_difference,
        "compensated_branch_difference": compensated_branch_difference,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file = run_dir / "negative_endpoint_validation_report.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 18 PAIRED RESULT ==========")
    print_paired_branch(results["preserve_solve"])
    print_paired_branch(results["freeze_radius"])
    print("\nFrozen minus preserve mean RMS difference:")
    print(
        "  Fixed image: "
        f"{uncompensated_branch_difference['mean_difference_um']:+.3f} um"
    )
    print(
        "  After Quick Focus: "
        f"{compensated_branch_difference['mean_difference_um']:+.3f} um"
    )
    print("[PASS] Both focused results reproduced Day 17")
    print("[PASS] Positive endpoint was not executed")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
