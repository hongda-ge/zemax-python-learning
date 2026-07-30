"""Day 5 step 1: select one non-baseline scan case from the YAML."""

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


CASE_NUMBER = 2


def main():
    config = load_config("configs/baseline_case.yaml")

    validate_dry_run_mode(config)
    validate_scan_values(config["outer_parameter"])
    validate_source_model(config["model"])
    validate_model_path_protection(config["model"])

    parameter = config["outer_parameter"]
    values = parameter["exploration"]["values"]
    list_index = CASE_NUMBER - 1

    if list_index < 0 or list_index >= len(values):
        raise IndexError(
            f"Case {CASE_NUMBER:03d} does not exist; "
            f"the YAML defines {len(values)} cases."
        )

    baseline = parameter["baseline_value"]
    target = values[list_index]
    delta = target - baseline

    if target == baseline:
        raise ValueError("Day 5 requires a non-baseline scan case.")

    print("========== DAY 5 CASE SELECTION ==========")
    print(f"Selected case: Case {CASE_NUMBER:03d}")
    print(f"Surface: {parameter['surface']}")
    print(f"Property: {parameter['property']}")
    print(f"Baseline: {baseline:.7f} {parameter['unit']}")
    print(f"Target: {target:.7f} {parameter['unit']}")
    print(f"Delta: {delta:+.7f} {parameter['unit']}")
    print("[PASS] One non-baseline case selected from the YAML")

    source_file = PROJECT_ROOT / config["model"]["source_file"]
    source_hash_before = sha256_file(source_file)
    run_id = datetime.now().strftime("case_002_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "outputs" / "day5_single_offset" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    result_file = run_dir / "result.json"
    result = {
        "task": "day5_single_offset_case",
        "run_id": run_id,
        "time_local": datetime.now().astimezone().isoformat(),
        "status": "failed",
        "case_number": CASE_NUMBER,
        "surface_id": parameter["surface"],
        "baseline_thickness_mm": baseline,
        "target_thickness_mm": target,
        "delta_mm": delta,
        "source_model": str(source_file),
        "source_sha256_before": source_hash_before,
        "connection_closed": False,
    }
    connection = None
    caught_error = None
    copy_info = None
    working_hash_before = None
    saved_model = None

    try:
        copy_info = copy_baseline_model(
            source_file,
            run_dir,
            working_name="working_model.zmx",
        )
        working_hash_before = sha256_file(copy_info["working_file"])
        result["working_copy"] = copy_info["working_file"]
        result["working_sha256_before"] = working_hash_before
        print(f"Working copy: {copy_info['working_file']}")

        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        print("[PASS] ZOS-API connection")
        open_working_model(connection.system, copy_info["working_file"])
        print("[PASS] Working copy opened")

        surface_2_before = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_before = read_surface(connection.system, 6)

        if not math.isclose(
            surface_2_before["thickness"],
            baseline,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Surface 2 does not start from the YAML baseline."
            )

        print(
            "Surface 2 before: "
            f"thickness = {surface_2_before['thickness']:.7f} mm"
        )
        print(
            "Surface 6 before: "
            f"radius = {surface_6_before['radius']:.7f} mm, "
            f"thickness = {surface_6_before['thickness']:.7f} mm"
        )
        print("[PASS] Pre-write surface snapshot captured")

        thickness_change = set_surface_thickness(
            connection.system,
            parameter["surface"],
            target,
        )
        surface_2_after = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_after = read_surface(connection.system, 6)

        if not math.isclose(
            surface_2_after["thickness"],
            target,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Zemax did not accept the Case 002 thickness.")

        print(
            "Surface 2 after: "
            f"thickness = {surface_2_after['thickness']:.7f} mm"
        )
        print(
            "Surface 6 after: "
            f"radius = {surface_6_after['radius']:.7f} mm, "
            f"thickness = {surface_6_after['thickness']:.7f} mm"
        )
        print(
            "Surface 6 radius delta: "
            f"{surface_6_after['radius'] - surface_6_before['radius']:+.7f} mm"
        )
        print("[PASS] Case 002 thickness written in Zemax memory")

        saved_model = save_model_as(
            connection.system,
            run_dir / "case_002_surface2_5p508.zmx",
            run_dir,
        )
        print(f"Saved model: {saved_model}")
        print("[PASS] Case 002 saved as a new file")

        open_working_model(connection.system, saved_model)
        surface_2_reloaded = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_reloaded = read_surface(connection.system, 6)

        if not math.isclose(
            surface_2_reloaded["thickness"],
            target,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Reloaded Case 002 thickness does not match the target."
            )

        if not math.isclose(
            surface_6_reloaded["radius"],
            surface_6_after["radius"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Reloaded Surface 6 radius does not match the Solve result."
            )

        print(
            "Reloaded Surface 2: "
            f"thickness = {surface_2_reloaded['thickness']:.7f} mm"
        )
        print(
            "Reloaded Surface 6: "
            f"radius = {surface_6_reloaded['radius']:.7f} mm, "
            f"thickness = {surface_6_reloaded['thickness']:.7f} mm"
        )
        print("[PASS] Saved Case 002 verified after reload")

        result.update(
            {
                "surface_2_before": surface_2_before,
                "surface_6_before": surface_6_before,
                "thickness_write": thickness_change,
                "surface_2_after": surface_2_after,
                "surface_6_after": surface_6_after,
                "surface_6_radius_delta_mm": (
                    surface_6_after["radius"]
                    - surface_6_before["radius"]
                ),
                "saved_model": str(saved_model),
                "saved_model_sha256": sha256_file(saved_model),
                "surface_2_reloaded": surface_2_reloaded,
                "surface_6_reloaded": surface_6_reloaded,
                "status": "success",
            }
        )

    except Exception as exc:
        caught_error = exc
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        print("Day 5 Case 002 FAILED")
        print(f"Error type: {type(exc).__name__}")
        print(f"Error message: {exc}")

    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed

        source_hash_after = sha256_file(source_file)
        source_unchanged = source_hash_after == source_hash_before
        result["source_sha256_after"] = source_hash_after
        result["source_unchanged"] = source_unchanged

        working_unchanged = None
        if copy_info is not None and working_hash_before is not None:
            working_hash_after = sha256_file(copy_info["working_file"])
            working_unchanged = working_hash_after == working_hash_before
            result["working_sha256_after"] = working_hash_after
            result["working_copy_unchanged"] = working_unchanged

        if not source_unchanged and caught_error is None:
            caught_error = RuntimeError("Source model changed during Day 5.")
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }

        if working_unchanged is False and caught_error is None:
            caught_error = RuntimeError(
                "Disk working copy changed without SaveAs."
            )
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }

        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"Connection closed: {result['connection_closed']}")
        print(f"Original model unchanged: {source_unchanged}")
        print(f"Disk working copy unchanged: {working_unchanged}")
        print(f"Result report: {result_file}")

    if caught_error is not None:
        raise caught_error

    print("[PASS] Day 5 Case 002 completed")
    print(f"[PASS] Saved model SHA256: {result['saved_model_sha256']}")


if __name__ == "__main__":
    main()
