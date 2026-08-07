"""Day 19 step 2: compare FFT MTF before/after focus at -0.4 mm."""

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
    export_fft_mtf_text,
    parse_fft_mtf_text,
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
    validate_initial_state,
)
from scripts.demos.day19_focus_compensation_mtf_plan import (  # noqa: E402
    build_experiment_plan,
    find_day18_reports,
    validate_analysis_report,
    validate_endpoint_report,
    validate_execution_lock,
    validate_mtf_recipe,
    validate_source,
)


def require_negative_authorization(config):
    """Authorize all paired actions for endpoint 001 only."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 write": execution["allow_surface2_in_memory_write"],
        "MakeSolveFixed": execution["allow_surface6_make_solve_fixed"],
        "fixed-image FFT MTF": execution["allow_uncompensated_fft_mtf"],
        "Quick Focus": execution["allow_quick_focus"],
        "focused FFT MTF": execution["allow_compensated_fft_mtf"],
        "endpoint 001": execution["allow_endpoint_001_execution"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 19 negative endpoint not approved: " + ", ".join(missing))
    forbidden = {
        "endpoint 002": execution["allow_endpoint_002_execution"],
        "offline analysis": execution["allow_offline_analysis"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 19 action: " + ", ".join(enabled))


def validate_mtf_metrics(config, metrics):
    """Require all planned fields and target frequencies."""

    expected_fields = {0.0, 14.0, 20.0}
    actual_fields = {
        round(float(field["field_y_degree"]), 7) for field in metrics["fields"]
    }
    if actual_fields != expected_fields:
        raise ValueError("FFT MTF did not return the three planned fields.")
    expected_frequencies = {
        float(value)
        for value in config["analysis"]["evaluation_frequencies_cyc_per_mm"]
    }
    for field in metrics["fields"]:
        frequencies = {
            float(item["target_frequency_cyc_per_mm"])
            for item in field["evaluations"]
        }
        if frequencies != expected_frequencies:
            raise ValueError("FFT MTF target frequencies are incomplete.")


def summarize_mtf(metrics):
    """Preserve field data and summarize each frequency over T/S and fields."""

    by_frequency = {}
    for field in metrics["fields"]:
        for evaluation in field["evaluations"]:
            frequency = float(evaluation["target_frequency_cyc_per_mm"])
            by_frequency.setdefault(frequency, []).append(evaluation)
    frequencies = []
    for frequency in sorted(by_frequency):
        evaluations = by_frequency[frequency]
        directions = []
        for evaluation in evaluations:
            directions.extend(
                [evaluation["tangential_mtf"], evaluation["sagittal_mtf"]]
            )
        frequencies.append(
            {
                "frequency_cyc_per_mm": frequency,
                "overall_mean_mtf": sum(directions) / len(directions),
                "minimum_mtf": min(directions),
                "maximum_direction_gap": max(
                    item["direction_gap"] for item in evaluations
                ),
            }
        )
    return {"fields": metrics["fields"], "frequencies": frequencies}


def compare_mtf(first, second):
    """Return second-minus-first differences at every field/frequency/direction."""

    def flatten(summary):
        values = {}
        for field in summary["fields"]:
            angle = float(field["field_y_degree"])
            for item in field["evaluations"]:
                frequency = float(item["target_frequency_cyc_per_mm"])
                values[(angle, frequency)] = {
                    "tangential_mtf": float(item["tangential_mtf"]),
                    "sagittal_mtf": float(item["sagittal_mtf"]),
                    "mean_mtf": float(item["mean_mtf"]),
                }
        return values

    first_values = flatten(first)
    second_values = flatten(second)
    if first_values.keys() != second_values.keys():
        raise ValueError("FFT MTF observations do not have matching samples.")
    samples = []
    for angle, frequency in sorted(first_values):
        left = first_values[(angle, frequency)]
        right = second_values[(angle, frequency)]
        samples.append(
            {
                "field_y_degree": angle,
                "frequency_cyc_per_mm": frequency,
                "first_tangential_mtf": left["tangential_mtf"],
                "second_tangential_mtf": right["tangential_mtf"],
                "tangential_difference": right["tangential_mtf"]
                - left["tangential_mtf"],
                "first_sagittal_mtf": left["sagittal_mtf"],
                "second_sagittal_mtf": right["sagittal_mtf"],
                "sagittal_difference": right["sagittal_mtf"]
                - left["sagittal_mtf"],
                "mean_difference": right["mean_mtf"] - left["mean_mtf"],
            }
        )
    return {"samples": samples}


def execute_paired_branch(config, baseline, endpoint, branch_name, branch_dir, source_file):
    """Export fixed-image MTF, Quick Focus, then focused MTF."""

    working_name = f"{endpoint['endpoint_id']}_{config['branches'][branch_name]['working_suffix']}"
    copy_info = copy_baseline_model(source_file, branch_dir, working_name)
    working_file = Path(copy_info["working_file"])
    source_hash_before = sha256_file(source_file).upper()
    working_hash_before = sha256_file(working_file).upper()
    result_file = branch_dir / "result.json"
    result = {
        "task": "day19_negative_endpoint_mtf",
        "status": "failed",
        "time_local": datetime.now().astimezone().isoformat(),
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
        expected_solve = config["branches"][branch_name]["expected_radius_solve"]
        if after_setup["surface6_radius_solve"] != expected_solve:
            raise ValueError(f"{branch_name} has the wrong Solve after setup.")
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
            abs_tol=float(config["guardrails"]["uncompensated_image_distance_tolerance_mm"]),
        ):
            raise ValueError("The fixed image plane moved unexpectedly.")
        result["after_surface2_write"] = after_write

        fixed_file = export_fft_mtf_text(
            connection.system,
            connection.ZOSAPI,
            branch_dir / f"{branch_name}_fixed_image_fft_mtf.txt",
            maximum_frequency=float(
                baseline["analysis"]["fft_mtf"]["maximum_frequency_cyc_per_mm"]
            ),
        )
        fixed_metrics = parse_fft_mtf_text(
            fixed_file,
            config["analysis"]["evaluation_frequencies_cyc_per_mm"],
        )
        validate_mtf_metrics(config, fixed_metrics)
        result["fixed_image_mtf_text"] = str(fixed_file)
        result["fixed_image_mtf_metrics"] = fixed_metrics
        result["fixed_image_mtf_summary"] = summarize_mtf(fixed_metrics)

        focus = run_quick_focus(connection.system, connection.ZOSAPI, use_centroid=True)
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

        focused_file = export_fft_mtf_text(
            connection.system,
            connection.ZOSAPI,
            branch_dir / f"{branch_name}_focused_fft_mtf.txt",
            maximum_frequency=float(
                baseline["analysis"]["fft_mtf"]["maximum_frequency_cyc_per_mm"]
            ),
        )
        focused_metrics = parse_fft_mtf_text(
            focused_file,
            config["analysis"]["evaluation_frequencies_cyc_per_mm"],
        )
        validate_mtf_metrics(config, focused_metrics)
        result["focused_mtf_text"] = str(focused_file)
        result["focused_mtf_metrics"] = focused_metrics
        result["focused_mtf_summary"] = summarize_mtf(focused_metrics)
        result["focus_recovery"] = compare_mtf(
            result["fixed_image_mtf_summary"],
            result["focused_mtf_summary"],
        )
        result["status"] = "success"
    except Exception as exc:
        caught_error = exc
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed
        source_hash_after = sha256_file(source_file).upper()
        working_hash_after = sha256_file(working_file).upper()
        result["source_sha256_after"] = source_hash_after
        result["working_sha256_after"] = working_hash_after
        result["source_unchanged"] = source_hash_after == source_hash_before
        result["working_copy_unchanged"] = working_hash_after == working_hash_before
        if not result["source_unchanged"] and caught_error is None:
            caught_error = RuntimeError("Day 19 changed the source model.")
        if not result["working_copy_unchanged"] and caught_error is None:
            caught_error = RuntimeError("Day 19 changed a disk working copy.")
        if not result["connection_closed"] and caught_error is None:
            caught_error = RuntimeError("Day 19 connection did not close.")
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


def validate_day18_reproduction(config, day18_report, results):
    """Require the structural and focus states to reproduce Day 18."""

    reproduction = {}
    for branch_name, result in results.items():
        expected = day18_report[branch_name]
        radius_difference = abs(
            float(result["after_surface2_write"]["surface6_radius_mm"])
            - float(expected["after_surface2_write"]["surface6_radius_mm"])
        )
        focus_difference = abs(
            float(result["focus"]["focus_shift_mm"])
            - float(expected["focus"]["focus_shift_mm"])
        )
        if radius_difference > float(
            config["guardrails"]["day18_reproduction_max_radius_difference_mm"]
        ):
            raise ValueError(f"{branch_name} did not reproduce Day 18 radius.")
        if focus_difference > float(
            config["guardrails"]["day18_reproduction_max_focus_difference_mm"]
        ):
            raise ValueError(f"{branch_name} did not reproduce Day 18 focus.")
        reproduction[branch_name] = {
            "surface6_radius_difference_mm": radius_difference,
            "focus_shift_difference_mm": focus_difference,
        }
    return reproduction


def print_branch(result):
    """Print overall MTF before and after Quick Focus for one branch."""

    print(f"{result['branch']}:")
    print(
        "  Surface 6 radius/Solve: "
        f"{result['after_surface2_write']['surface6_radius_mm']:.10f} mm / "
        f"{result['after_surface2_write']['surface6_radius_solve']}"
    )
    fixed_by_frequency = {
        row["frequency_cyc_per_mm"]: row
        for row in result["fixed_image_mtf_summary"]["frequencies"]
    }
    for focused in result["focused_mtf_summary"]["frequencies"]:
        frequency = focused["frequency_cyc_per_mm"]
        fixed = fixed_by_frequency[frequency]
        print(
            f"  MTF {frequency:.0f} mean/min: "
            f"fixed {fixed['overall_mean_mtf']:.4f}/{fixed['minimum_mtf']:.4f} -> "
            f"focused {focused['overall_mean_mtf']:.4f}/{focused['minimum_mtf']:.4f}"
        )
    print(f"  Quick Focus shift: {result['focus']['focus_shift_mm']:+.7f} mm")


def main():
    config = load_config("configs/day19_focus_compensation_mtf.yaml")
    validate_execution_lock(config)
    require_negative_authorization(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_mtf_recipe(config, baseline)
    negative_file, positive_file, analysis_file = find_day18_reports(config)
    negative_report = json.loads(negative_file.read_text(encoding="utf-8"))
    positive_report = json.loads(positive_file.read_text(encoding="utf-8"))
    day18_analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    validate_endpoint_report(
        config,
        negative_report,
        config["source"]["expected_negative_task"],
        -0.4,
    )
    validate_endpoint_report(
        config,
        positive_report,
        config["source"]["expected_positive_task"],
        0.4,
    )
    validate_analysis_report(
        config,
        day18_analysis,
        negative_file,
        positive_file,
    )
    endpoint = build_experiment_plan(config)[0]
    run_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("negative_endpoint_%Y%m%d_%H%M%S")
    )
    endpoint_dir = run_dir / endpoint["directory_name"]
    results = {}

    print("========== DAY 19 NEGATIVE-ENDPOINT FFT MTF ==========")
    print("Only endpoint_001 will run; endpoint_002 remains locked.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(
        f"Endpoint: {endpoint['value_mm']:.7f} mm "
        f"(delta {endpoint['delta_mm']:+.1f} mm)"
    )
    print("Each branch exports fixed-image MTF, then Quick Focus and focused MTF.")
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        print(f"\nRunning {branch_name}...")
        results[branch_name] = execute_paired_branch(
            config,
            baseline,
            endpoint,
            branch_name,
            endpoint_dir / branch_name,
            source_file,
        )
        print("[PASS] Paired branch completed; connection closed and hashes unchanged")

    reproduction = validate_day18_reproduction(config, negative_report, results)
    fixed_branch_difference = compare_mtf(
        results["preserve_solve"]["fixed_image_mtf_summary"],
        results["freeze_radius"]["fixed_image_mtf_summary"],
    )
    focused_branch_difference = compare_mtf(
        results["preserve_solve"]["focused_mtf_summary"],
        results["freeze_radius"]["focused_mtf_summary"],
    )
    report = {
        "task": "day19_negative_endpoint_mtf",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day18_report": str(negative_file),
        "endpoint": endpoint,
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "day18_reproduction": reproduction,
        "fixed_image_branch_difference": fixed_branch_difference,
        "focused_branch_difference": focused_branch_difference,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file = run_dir / "negative_endpoint_mtf_report.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 19 NEGATIVE-ENDPOINT RESULT ==========")
    print_branch(results["preserve_solve"])
    print_branch(results["freeze_radius"])
    print("[PASS] Structural and focus states reproduced Day 18")
    print("[PASS] Positive endpoint was not executed")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
