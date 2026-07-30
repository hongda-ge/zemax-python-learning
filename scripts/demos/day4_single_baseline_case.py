"""Day 4: write one baseline value only to a safe ZOS-API model copy."""

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


def main():
    config = load_config("configs/baseline_case.yaml")

    validate_dry_run_mode(config)
    validate_scan_values(config["outer_parameter"])
    validate_source_model(config["model"])
    validate_model_path_protection(config["model"])

    source_file = PROJECT_ROOT / config["model"]["source_file"]
    source_hash_before = sha256_file(source_file)

    run_id = datetime.now().strftime("single_baseline_case_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "outputs" / "day4_single_case" / run_id
    copy_info = copy_baseline_model(
        source_file,
        run_dir,
        working_name="working_model.zmx",
    )

    surface_id = config["outer_parameter"]["surface"]
    expected_thickness = config["outer_parameter"]["baseline_value"]

    print("========== DAY 4 SINGLE BASELINE CASE ==========")
    print(f"Source model: {source_file}")
    print(f"Working copy: {copy_info['working_file']}")

    with StandaloneZemaxConnection() as connection:
        connection_info = connection.info()
        print("[PASS] ZOS-API connection")
        open_working_model(connection.system, copy_info["working_file"])
        print("[PASS] Working copy opened")

        surface_data = read_surface(connection.system, surface_id)
        actual_thickness = surface_data["thickness"]

        print(f"Surface: {surface_data['surface_id']}")
        print(f"Radius: {surface_data['radius']:.6f} mm")
        print(f"Thickness: {actual_thickness:.6f} mm")
        print(f"Material: {surface_data['material']}")

        if not math.isclose(
            actual_thickness,
            expected_thickness,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Surface 2 thickness does not match the YAML baseline."
            )

        print("[PASS] Surface 2 baseline thickness")

        thickness_change = set_surface_thickness(
            connection.system,
            surface_id,
            expected_thickness,
        )
        print(
            "Thickness write: "
            f"{thickness_change['old_thickness']:.7f} -> "
            f"{thickness_change['actual_thickness']:.7f} mm"
        )

        if not math.isclose(
            thickness_change["actual_thickness"],
            expected_thickness,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Zemax did not accept the baseline thickness.")

        print("[PASS] Baseline thickness written to working copy")

        saved_model = save_model_as(
            connection.system,
            run_dir / "case_003_baseline_6p008.zmx",
            run_dir,
        )
        print(f"Saved model: {saved_model}")
        print("[PASS] Working model saved as a new file")

        open_working_model(connection.system, saved_model)
        reloaded_surface = read_surface(connection.system, surface_id)

        if not math.isclose(
            reloaded_surface["thickness"],
            expected_thickness,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Reloaded model thickness does not match the baseline."
            )

        print("[PASS] Saved thickness verified after reload")

    source_hash_after = sha256_file(source_file)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Source model changed during the read-only check.")

    print("[PASS] ZOS-API connection closed")
    print("[PASS] Original model unchanged")
    print("Only the output working copy was written.")

    result = {
        "task": "day4_single_baseline_case",
        "run_id": run_id,
        "time_local": datetime.now().astimezone().isoformat(),
        "status": "success",
        "backend": config["backend"],
        "connection": connection_info,
        "source_model": str(source_file),
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "source_unchanged": source_hash_before == source_hash_after,
        "working_copy": copy_info["working_file"],
        "saved_model": str(saved_model),
        "saved_model_sha256": sha256_file(saved_model),
        "surface_before": surface_data,
        "thickness_write": thickness_change,
        "surface_reloaded": reloaded_surface,
        "connection_closed": connection.closed,
    }

    result_file = run_dir / "result.json"
    result_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[PASS] Result report saved: {result_file}")


if __name__ == "__main__":
    main()
