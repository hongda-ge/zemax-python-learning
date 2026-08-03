"""Day 7 step 1: build and validate a five-case real-Zemax plan."""

import csv
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
    read_surface,
    save_model_as,
    set_surface_thickness,
    sha256_file,
)
from scripts.demos.day3_baseline_dry_run import (  # noqa: E402
    validate_dry_run_mode,
    validate_model_path_protection,
    validate_scan_values,
    validate_source_model,
)


class FocusRangeRejected(ValueError):
    """The optical case ran, but its focused image distance is not approved."""


def value_tag(value):
    """Convert one millimetre value into a filesystem-safe short tag."""

    return f"{value:.3f}".replace("-", "m").replace(".", "p")


def build_case_plan(config):
    """Create one explicit task record for every YAML scan value."""

    parameter = config["outer_parameter"]
    baseline = parameter["baseline_value"]
    cases = []

    for case_number, value in enumerate(
        parameter["exploration"]["values"],
        start=1,
    ):
        tag = value_tag(value)
        case_id = f"case_{case_number:03d}"
        cases.append(
            {
                "case_number": case_number,
                "case_id": case_id,
                "value_mm": value,
                "delta_mm": value - baseline,
                "is_baseline": value == baseline,
                "directory_name": f"{case_id}_{tag}",
                "focused_model_name": (
                    f"{case_id}_surface2_{tag}_focused.zmx"
                ),
                "spot_text_name": f"{case_id}_standard_spot.txt",
                "result_name": "result.json",
            }
        )

    return cases


def validate_case_plan(cases):
    """Reject ambiguous identifiers, filenames, or baseline definitions."""

    if not cases:
        raise ValueError("The batch plan contains no cases.")

    case_ids = [case["case_id"] for case in cases]
    directories = [case["directory_name"] for case in cases]
    baseline_count = sum(case["is_baseline"] for case in cases)

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Case identifiers are not unique.")

    if len(directories) != len(set(directories)):
        raise ValueError("Case output directories are not unique.")

    if baseline_count != 1:
        raise ValueError(
            f"Exactly one baseline case is required; found {baseline_count}."
        )


def get_focus_bounds(config):
    """Return the approved Surface 6 image-distance range."""

    for variable in config["inner_variables"]["variables"]:
        if variable["surface"] == 6 and variable["property"] == "thickness":
            return variable["lower_bound"], variable["upper_bound"]

    raise ValueError("Surface 6 focus bounds are missing from the YAML.")


def execute_one_case(config, case, batch_dir):
    """Execute one isolated real-Zemax case and always write a report."""

    source_file = PROJECT_ROOT / config["model"]["source_file"]
    source_hash_before = sha256_file(source_file)
    case_dir = batch_dir / case["directory_name"]
    case_dir.mkdir(parents=True, exist_ok=False)
    result_file = case_dir / case["result_name"]
    lower_focus, upper_focus = get_focus_bounds(config)

    result = {
        "task": "day7_five_case_sweep",
        "status": "failed",
        "case": case,
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256_before": source_hash_before,
        "connection_closed": False,
    }
    connection = None
    copy_info = None
    working_hash_before = None
    caught_error = None

    try:
        copy_info = copy_baseline_model(
            source_file,
            case_dir,
            working_name="working_model.zmx",
        )
        working_hash_before = sha256_file(copy_info["working_file"])
        result["working_copy"] = copy_info["working_file"]
        result["working_sha256_before"] = working_hash_before

        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        open_working_model(connection.system, copy_info["working_file"])

        parameter = config["outer_parameter"]
        surface_before = read_surface(
            connection.system,
            parameter["surface"],
        )
        if not math.isclose(
            surface_before["thickness"],
            parameter["baseline_value"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("The case did not start from the baseline model.")

        thickness_write = set_surface_thickness(
            connection.system,
            parameter["surface"],
            case["value_mm"],
        )
        surface_after_write = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_before_focus = read_surface(connection.system, 6)

        focus_result = run_quick_focus(
            connection.system,
            connection.ZOSAPI,
            use_centroid=True,
        )
        # Keep the physical state even when the engineering gate rejects it.
        result.update(
            {
                "surface_before": surface_before,
                "thickness_write": thickness_write,
                "surface_after_write": surface_after_write,
                "surface_6_before_focus": surface_6_before_focus,
                "focus": focus_result,
            }
        )
        if not lower_focus <= focus_result["thickness_after_mm"] <= upper_focus:
            raise FocusRangeRejected(
                "Quick Focus result is outside the approved range: "
                f"{focus_result['thickness_after_mm']} mm."
            )

        saved_model = save_model_as(
            connection.system,
            case_dir / case["focused_model_name"],
            case_dir,
        )
        open_working_model(connection.system, saved_model)
        surface_reloaded = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_reloaded = read_surface(connection.system, 6)

        if not math.isclose(
            surface_reloaded["thickness"],
            case["value_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Reloaded case thickness is incorrect.")

        if not math.isclose(
            surface_6_reloaded["thickness"],
            focus_result["thickness_after_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Reloaded focus distance is incorrect.")

        spot_text = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            case_dir / case["spot_text_name"],
        )
        spot_metrics = parse_standard_spot_text(spot_text)
        if spot_metrics["reference"] != "质心":
            raise ValueError("Standard Spot did not use the centroid reference.")

        result.update(
            {
                "status": "success",
                "saved_model": str(saved_model),
                "saved_model_sha256": sha256_file(saved_model),
                "surface_reloaded": surface_reloaded,
                "surface_6_reloaded": surface_6_reloaded,
                "spot_text": str(spot_text),
                "spot_metrics": spot_metrics,
            }
        )

    except Exception as exc:
        caught_error = exc
        result["status"] = (
            "rejected" if isinstance(exc, FocusRangeRejected) else "failed"
        )
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed

        source_hash_after = sha256_file(source_file)
        result["source_sha256_after"] = source_hash_after
        source_unchanged = source_hash_after == source_hash_before
        result["source_unchanged"] = source_unchanged

        working_unchanged = None
        if copy_info is not None and working_hash_before is not None:
            working_hash_after = sha256_file(copy_info["working_file"])
            result["working_sha256_after"] = working_hash_after
            working_unchanged = working_hash_after == working_hash_before
            result["working_copy_unchanged"] = working_unchanged

        if not source_unchanged and caught_error is None:
            caught_error = RuntimeError("Original model changed during Day 7.")

        if working_unchanged is False and caught_error is None:
            caught_error = RuntimeError(
                "Initial working copy changed during Day 7."
            )

        if caught_error is not None:
            if not isinstance(caught_error, FocusRangeRejected):
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


def load_case_report(batch_dir, case):
    """Read the report that execute_one_case always leaves on disk."""

    result_file = batch_dir / case["directory_name"] / case["result_name"]
    return json.loads(result_file.read_text(encoding="utf-8"))


def result_to_summary_row(result):
    """Flatten one successful or rejected result for CSV comparison."""

    fields = {
        field["field_y_degree"]: field
        for field in result.get("spot_metrics", {}).get("fields", [])
    }
    focus = result.get("focus", {})
    surface_6 = result.get("surface_6_before_focus", {})
    error = result.get("error", {})

    def metric(field_angle, name):
        return fields.get(field_angle, {}).get(name)

    return {
        "case_id": result["case"]["case_id"],
        "status": result["status"],
        "value_mm": result["case"]["value_mm"],
        "delta_mm": result["case"]["delta_mm"],
        "is_baseline": result["case"]["is_baseline"],
        "focus_shift_mm": focus.get("focus_shift_mm"),
        "focused_image_distance_mm": focus.get("thickness_after_mm"),
        "surface_6_radius_mm": surface_6.get("radius"),
        "rms_0deg_um": metric(0.0, "rms_radius_um"),
        "rms_14deg_um": metric(14.0, "rms_radius_um"),
        "rms_20deg_um": metric(20.0, "rms_radius_um"),
        "maximum_0deg_um": metric(0.0, "maximum_radius_um"),
        "maximum_14deg_um": metric(14.0, "maximum_radius_um"),
        "maximum_20deg_um": metric(20.0, "maximum_radius_um"),
        "rejection_reason": error.get("message", ""),
    }


def write_batch_summary(batch_dir, batch_id, results):
    """Write a complete summary, including safely rejected design points."""

    for result in results:
        error_message = result.get("error", {}).get("message", "")
        legacy_focus_rejection = (
            result.get("status") == "failed"
            and error_message.startswith(
                "Quick Focus result is outside the approved range:"
            )
        )
        if legacy_focus_rejection:
            safety_ok = (
                result.get("source_unchanged") is True
                and result.get("working_copy_unchanged") is True
                and result.get("connection_closed") is True
            )
            if not safety_ok:
                raise RuntimeError(
                    "A legacy focus rejection failed its safety audit."
                )
            result["status"] = "rejected"
            focused_distance = float(
                error_message.rsplit(":", 1)[1].strip().split()[0]
            )
            result.setdefault("focus", {})[
                "thickness_after_mm"
            ] = focused_distance

    summary_rows = [result_to_summary_row(result) for result in results]
    success_count = sum(row["status"] == "success" for row in summary_rows)
    rejected_count = sum(row["status"] == "rejected" for row in summary_rows)
    batch_status = (
        "completed_with_rejections" if rejected_count else "success"
    )
    batch_summary = {
        "task": "day7_five_case_sweep",
        "batch_id": batch_id,
        "time_local": datetime.now().astimezone().isoformat(),
        "status": batch_status,
        "case_count": len(summary_rows),
        "success_count": success_count,
        "rejected_count": rejected_count,
        "rows": summary_rows,
    }
    batch_dir.mkdir(parents=True, exist_ok=True)
    summary_json = batch_dir / "batch_summary.json"
    summary_csv = batch_dir / "sweep_results.csv"
    summary_json.write_text(
        json.dumps(batch_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(summary_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    return batch_summary, summary_json, summary_csv


def main():
    config = load_config("configs/baseline_case.yaml")

    validate_dry_run_mode(config)
    validate_scan_values(config["outer_parameter"])
    validate_source_model(config["model"])
    validate_model_path_protection(config["model"])

    cases = build_case_plan(config)
    validate_case_plan(cases)

    parameter = config["outer_parameter"]
    print("========== DAY 7 FIVE-CASE PLAN ==========")
    print("Mode: REVIEWED FIVE-CASE EXECUTION")
    print("Cases run sequentially; approved-range rejections remain reportable.")
    print(
        f"Parameter: Surface {parameter['surface']} "
        f"{parameter['property']} ({parameter['unit']})"
    )
    print()

    for case in cases:
        baseline_mark = " <- baseline" if case["is_baseline"] else ""
        print(
            f"{case['case_id']}: {case['value_mm']:.7f} mm, "
            f"delta {case['delta_mm']:+.7f} mm{baseline_mark}"
        )
        print(f"  directory: {case['directory_name']}")
        print(f"  model: {case['focused_model_name']}")
        print(f"  spot: {case['spot_text_name']}")
        print(f"  report: {case['result_name']}")

    print()
    print(f"[PASS] {len(cases)} unique cases planned")
    print("[PASS] Exactly one baseline case identified")

    batch_id = datetime.now().strftime("five_case_%Y%m%d_%H%M%S")
    batch_dir = (
        PROJECT_ROOT / "outputs" / "day7_five_case_sweep" / batch_id
    )

    print()
    print("========== DAY 7 FIVE-CASE EXECUTION ==========")
    print(f"Batch directory: {batch_dir}")

    results = []
    for case in cases:
        print()
        print(
            f"Running {case['case_id']} "
            f"({case['value_mm']:.7f} mm)..."
        )
        try:
            result = execute_one_case(config, case, batch_dir)
        except FocusRangeRejected:
            result = load_case_report(batch_dir, case)
            safety_ok = (
                result.get("source_unchanged") is True
                and result.get("working_copy_unchanged") is True
                and result.get("connection_closed") is True
            )
            if not safety_ok:
                raise RuntimeError(
                    f"{case['case_id']} was rejected and its safety audit failed."
                )
            results.append(result)
            print(
                f"[REJECTED] {case['case_id']}: "
                f"{result['error']['message']}"
            )
            continue
        results.append(result)

        print(
            f"[PASS] {case['case_id']} focus shift: "
            f"{result['focus']['focus_shift_mm']:+.7f} mm"
        )
        for field in result["spot_metrics"]["fields"]:
            print(
                f"  Field {field['field_y_degree']:.1f} deg RMS: "
                f"{field['rms_radius_um']:.3f} um"
            )

    batch_summary, summary_json, summary_csv = write_batch_summary(
        batch_dir,
        batch_id,
        results,
    )
    summary_rows = batch_summary["rows"]

    print()
    print("========== DAY 7 BATCH SUMMARY ==========")
    for row in summary_rows:
        if row["status"] == "rejected":
            print(
                f"{row['case_id']}: REJECTED, "
                f"image distance={row['focused_image_distance_mm']:.4f} mm"
            )
            continue
        print(
            f"{row['case_id']}: delta={row['delta_mm']:+.3f} mm, "
            f"focus={row['focus_shift_mm']:+.4f} mm, "
            f"RMS=[{row['rms_0deg_um']:.3f}, "
            f"{row['rms_14deg_um']:.3f}, "
            f"{row['rms_20deg_um']:.3f}] um"
        )
    print(f"[PASS] Batch JSON: {summary_json}")
    print(f"[PASS] Sweep CSV: {summary_csv}")
    print(
        f"[PASS] Successful: {batch_summary['success_count']}, "
        f"rejected by constraints: {batch_summary['rejected_count']}"
    )


if __name__ == "__main__":
    main()
