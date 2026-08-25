"""Day 23 step 2: reproduce Spot and FFT MTF at zero residual defocus."""

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
    export_standard_spot_text,
    parse_fft_mtf_text,
    parse_standard_spot_text,
)
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.model_ops import (  # noqa: E402
    copy_baseline_model,
    copy_output_model,
    open_working_model,
    read_surface,
    set_surface_thickness,
    sha256_file,
)
from scripts.demos.day19_validate_negative_endpoint_mtf import (  # noqa: E402
    summarize_mtf,
)
from scripts.demos.day23_residual_defocus_optical_impact_plan import (  # noqa: E402
    build_cases,
    find_latest_day22_report,
    validate_analysis_recipes,
    validate_day22_evidence,
    validate_day8_evidence,
    validate_guardrails,
    validate_input_model,
)


def require_baseline_authorization(config):
    """Authorize the baseline control while all residual cases remain locked."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "model copy": execution["allow_model_copy"],
        "focus-surface memory write": execution[
            "allow_focus_surface_in_memory_write"
        ],
        "Standard Spot": execution["allow_standard_spot"],
        "FFT MTF": execution["allow_fft_mtf"],
        "baseline control": execution["allow_baseline_control"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 23 baseline control not approved: " + ", ".join(missing))
    forbidden = {
        "residual cases": execution["allow_residual_cases"],
        "Quick Focus": execution["allow_quick_focus"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
        "engineering recommendation": execution["allow_engineering_recommendation"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 23 action: " + ", ".join(enabled))


def validate_day9_baseline(config, model_file, model_hash):
    """Load the reviewed FFT MTF reference for this exact focused model."""

    source = config["source"]
    report_file = PROJECT_ROOT / source["day9_baseline_report"]
    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "task": report.get("task") == source["expected_day9_task"],
        "status": report.get("status") == "success",
        "input hash before": report.get("input_model_sha256_before", "").upper()
        == model_hash,
        "input unchanged": report.get("input_model_unchanged") is True,
        "working copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
        "model still exists": model_file.is_file(),
        "three fields": report.get("mtf_metrics", {}).get("field_count") == 3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 9 baseline evidence failed: " + ", ".join(failed))
    return report_file, report


def select_control(cases):
    """Select the unique zero-offset case."""

    controls = [case for case in cases if case["is_control"]]
    if len(controls) != 1:
        raise ValueError("Day 23 does not contain exactly one control case.")
    return controls[0]


def validate_spot_metrics(config, metrics):
    """Require three centroid-referenced fields."""

    actual = sorted(round(float(row["field_y_degree"]), 9) for row in metrics["fields"])
    expected = sorted(
        round(float(value), 9)
        for value in config["analysis"]["expected_field_y_degrees"]
    )
    if actual != expected:
        raise ValueError(f"Unexpected Standard Spot fields: {actual}.")
    if metrics["field_count"] != len(expected):
        raise ValueError("Standard Spot field count is incorrect.")


def summarize_spot(metrics):
    """Build transparent equal-field Spot summaries."""

    fields = sorted(metrics["fields"], key=lambda row: float(row["field_y_degree"]))
    values = [float(row["rms_radius_um"]) for row in fields]
    return {
        "fields": fields,
        "equal_field_mean_rms_um": sum(values) / len(values),
        "worst_field_rms_um": max(values),
    }


def validate_mtf_metrics(config, metrics):
    """Require the three fields and both frozen target frequencies."""

    expected_fields = {
        round(float(value), 9)
        for value in config["analysis"]["expected_field_y_degrees"]
    }
    actual_fields = {
        round(float(field["field_y_degree"]), 9) for field in metrics["fields"]
    }
    if actual_fields != expected_fields:
        raise ValueError("FFT MTF did not return the three planned fields.")
    expected_frequencies = {
        float(value)
        for value in config["analysis"]["fft_mtf"][
            "evaluation_frequencies_cyc_per_mm"
        ]
    }
    for field in metrics["fields"]:
        frequencies = {
            float(item["target_frequency_cyc_per_mm"])
            for item in field["evaluations"]
        }
        if frequencies != expected_frequencies:
            raise ValueError("FFT MTF target frequencies are incomplete.")


def compare_spot(reference, observed):
    """Compare field RMS radii with the frozen Day 8 evidence."""

    expected = {
        round(float(row["field_y_degree"]), 9): float(row["rms_radius_um"])
        for row in reference["fields"]
    }
    actual = {
        round(float(row["field_y_degree"]), 9): float(row["rms_radius_um"])
        for row in observed["fields"]
    }
    if expected.keys() != actual.keys():
        raise ValueError("Day 8 and Day 23 Spot fields do not match.")
    rows = []
    for field in sorted(expected):
        difference = actual[field] - expected[field]
        rows.append(
            {
                "field_y_degree": field,
                "day8_rms_radius_um": expected[field],
                "day23_rms_radius_um": actual[field],
                "difference_um": difference,
            }
        )
    return {
        "rows": rows,
        "maximum_absolute_difference_um": max(abs(row["difference_um"]) for row in rows),
    }


def flatten_mtf(metrics):
    """Index all target-frequency T/S values."""

    values = {}
    for field in metrics["fields"]:
        angle = round(float(field["field_y_degree"]), 9)
        for item in field["evaluations"]:
            frequency = float(item["target_frequency_cyc_per_mm"])
            values[(angle, frequency, "tangential")] = float(item["tangential_mtf"])
            values[(angle, frequency, "sagittal")] = float(item["sagittal_mtf"])
    return values


def compare_mtf(reference, observed):
    """Compare every field/frequency/direction with Day 9."""

    expected = flatten_mtf(reference)
    actual = flatten_mtf(observed)
    if expected.keys() != actual.keys():
        raise ValueError("Day 9 and Day 23 MTF samples do not match.")
    rows = []
    for field, frequency, direction in sorted(expected):
        difference = actual[(field, frequency, direction)] - expected[
            (field, frequency, direction)
        ]
        rows.append(
            {
                "field_y_degree": field,
                "frequency_cyc_per_mm": frequency,
                "direction": direction,
                "day9_mtf": expected[(field, frequency, direction)],
                "day23_mtf": actual[(field, frequency, direction)],
                "difference": difference,
            }
        )
    return {
        "rows": rows,
        "maximum_absolute_difference": max(abs(row["difference"]) for row in rows),
    }


def execute_case(
    config,
    baseline,
    case,
    case_dir,
    model_file,
    task_name,
    report_name,
    model_source_kind="output",
):
    """Run one isolated residual-defocus observation with a complete audit."""

    case_dir.mkdir(parents=True, exist_ok=False)
    result_file = case_dir / report_name
    input_hash_before = sha256_file(model_file).upper()
    copy_model = {
        "output": copy_output_model,
        "baseline": copy_baseline_model,
    }.get(model_source_kind)
    if copy_model is None:
        raise ValueError("Unsupported model_source_kind: {0}".format(model_source_kind))
    copy_info = copy_model(
        model_file,
        case_dir,
        working_name=f"{case['case_id']}_working.zmx",
    )
    working_file = Path(copy_info["working_file"])
    working_hash_before = sha256_file(working_file).upper()
    result = {
        "task": task_name,
        "status": "failed",
        "time_local": datetime.now().astimezone().isoformat(),
        "case": case,
        "input_model": str(model_file),
        "working_copy": str(working_file),
        "input_sha256_before": input_hash_before,
        "working_sha256_before": working_hash_before,
        "connection_closed": False,
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
    }
    connection = None
    caught_error = None
    try:
        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        open_working_model(connection.system, working_file)
        surface2_before = read_surface(connection.system, int(config["reference_state"]["surface2_id"]))
        surface6_before = read_surface(connection.system, int(config["reference_state"]["focus_surface_id"]))
        tolerance = float(config["guardrails"]["numeric_tolerance_mm"])
        if not math.isclose(
            surface2_before["thickness"],
            float(config["reference_state"]["surface2_thickness_mm"]),
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValueError("Control Surface 2 thickness is incorrect.")
        if not math.isclose(
            surface6_before["thickness"],
            float(config["reference_state"]["focused_image_distance_mm"]),
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValueError("Control image distance is not the focused reference.")
        result["surface2_before"] = surface2_before
        result["surface6_before"] = surface6_before

        result["focus_surface_write"] = set_surface_thickness(
            connection.system,
            int(config["reference_state"]["focus_surface_id"]),
            float(case["target_image_distance_mm"]),
        )
        surface6_after = read_surface(
            connection.system,
            int(config["reference_state"]["focus_surface_id"]),
        )
        if not math.isclose(
            surface6_after["thickness"],
            float(case["target_image_distance_mm"]),
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValueError("Control residual-defocus write is incorrect.")
        result["surface6_after"] = surface6_after

        spot_file = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            case_dir / f"{case['case_id']}_standard_spot.txt",
        )
        spot_metrics = parse_standard_spot_text(spot_file)
        validate_spot_metrics(config, spot_metrics)
        result["spot_text"] = str(spot_file)
        result["spot_metrics"] = spot_metrics
        result["spot_summary"] = summarize_spot(spot_metrics)

        mtf_file = export_fft_mtf_text(
            connection.system,
            connection.ZOSAPI,
            case_dir / f"{case['case_id']}_fft_mtf.txt",
            maximum_frequency=float(
                baseline["analysis"]["fft_mtf"]["maximum_frequency_cyc_per_mm"]
            ),
        )
        mtf_metrics = parse_fft_mtf_text(
            mtf_file,
            config["analysis"]["fft_mtf"]["evaluation_frequencies_cyc_per_mm"],
        )
        validate_mtf_metrics(config, mtf_metrics)
        result["mtf_text"] = str(mtf_file)
        result["mtf_metrics"] = mtf_metrics
        result["mtf_summary"] = summarize_mtf(mtf_metrics)
        result["status"] = "success"
    except Exception as exc:
        caught_error = exc
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed
        result["input_sha256_after"] = sha256_file(model_file).upper()
        result["working_sha256_after"] = sha256_file(working_file).upper()
        result["input_model_unchanged"] = (
            result["input_sha256_after"] == input_hash_before
        )
        result["working_copy_unchanged"] = (
            result["working_sha256_after"] == working_hash_before
        )
        if result["input_model_unchanged"] is not True and caught_error is None:
            caught_error = RuntimeError("Day 23 changed the focused input model.")
        if result["working_copy_unchanged"] is not True and caught_error is None:
            caught_error = RuntimeError("Day 23 changed the disk working copy.")
        if result["connection_closed"] is not True and caught_error is None:
            caught_error = RuntimeError("Day 23 connection did not close.")
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
    return result, result_file


def main():
    config = load_config("configs/day23_residual_defocus_optical_impact.yaml")
    require_baseline_authorization(config)
    model_file, model_hash = validate_input_model(config)
    _, day8_case_file = validate_day8_evidence(config, model_file, model_hash)
    day22_file = find_latest_day22_report(config)
    validate_day22_evidence(config, day22_file)
    validate_analysis_recipes(config)
    validate_guardrails(config)
    baseline = load_config(config["source"]["baseline_config"])
    day8_case = json.loads(day8_case_file.read_text(encoding="utf-8"))
    day9_file, day9 = validate_day9_baseline(config, model_file, model_hash)
    control = select_control(build_cases(config))

    run_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("baseline_control_%Y%m%d_%H%M%S")
    )
    case_dir = run_dir / control["case_id"]

    print("========== DAY 23 BASELINE OPTICAL CONTROL ==========")
    print("Only defocus_004 (0.000 mm) will run; six residual cases stay locked.")
    print(f"Focused input model: {model_file}")
    print(f"Output directory: {run_dir}")
    print("Quick Focus, optimization and SaveAs are forbidden.")

    result, result_file = execute_case(
        config,
        baseline,
        control,
        case_dir,
        model_file,
        task_name="day23_residual_defocus_baseline_control",
        report_name="baseline_control_report.json",
    )
    spot_comparison = compare_spot(day8_case["spot_metrics"], result["spot_metrics"])
    mtf_comparison = compare_mtf(day9["mtf_metrics"], result["mtf_metrics"])
    if spot_comparison["maximum_absolute_difference_um"] > float(
        config["guardrails"]["baseline_spot_max_absolute_difference_um"]
    ):
        raise ValueError("Day 23 baseline control did not reproduce Day 8 Spot.")
    if mtf_comparison["maximum_absolute_difference"] > float(
        config["guardrails"]["baseline_mtf_max_absolute_difference"]
    ):
        raise ValueError("Day 23 baseline control did not reproduce Day 9 MTF.")

    result["source_day8_case_report"] = str(day8_case_file)
    result["source_day9_mtf_report"] = str(day9_file)
    result["source_day22_error_budget_report"] = str(day22_file)
    result["spot_reproduction"] = spot_comparison
    result["mtf_reproduction"] = mtf_comparison
    result_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[PASS] ZOS-API connection and isolated working copy")
    print(
        f"[PASS] Image distance: {result['surface6_after']['thickness']:.10f} mm"
    )
    for row in result["spot_metrics"]["fields"]:
        print(
            f"[PASS] Field {float(row['field_y_degree']):.1f} deg Spot RMS: "
            f"{float(row['rms_radius_um']):.6f} um"
        )
    for row in result["mtf_summary"]["frequencies"]:
        print(
            f"[PASS] MTF {row['frequency_cyc_per_mm']:.0f} mean/min: "
            f"{row['overall_mean_mtf']:.6f}/{row['minimum_mtf']:.6f}"
        )
    print(
        "[PASS] Maximum Day 8 Spot reproduction difference: "
        f"{spot_comparison['maximum_absolute_difference_um']:.9f} um"
    )
    print(
        "[PASS] Maximum Day 9 MTF reproduction difference: "
        f"{mtf_comparison['maximum_absolute_difference']:.9f}"
    )
    print("[PASS] Input and disk working-copy hashes unchanged")
    print("[PASS] ZOS-API connection closed")
    print("[PASS] Six residual-defocus cases were not executed")
    print(f"[PASS] Result report: {result_file}")


if __name__ == "__main__":
    main()
