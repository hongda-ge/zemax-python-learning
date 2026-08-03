"""Day 6: focus and verify baseline and Case 002 model copies."""

import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.analysis_ops import export_standard_spot_text  # noqa: E402
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


def get_focus_bounds(config):
    """Read the approved Surface 6 thickness bounds from the YAML."""

    for variable in config["inner_variables"]["variables"]:
        if variable["surface"] == 6 and variable["property"] == "thickness":
            return variable["lower_bound"], variable["upper_bound"]

    raise ValueError("Surface 6 focus bounds are missing from the YAML.")


def run_case_002_focus_check(config, lower_bound, upper_bound):
    """Apply Case 002 in memory, then run the same Quick Focus rule."""

    parameter = config["outer_parameter"]
    baseline = parameter["baseline_value"]
    target = parameter["exploration"]["values"][1]
    source_file = PROJECT_ROOT / config["model"]["source_file"]
    source_hash_before = sha256_file(source_file)

    run_id = datetime.now().strftime("case_002_focus_check_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "outputs" / "day6_quick_focus" / run_id
    copy_info = copy_baseline_model(
        source_file,
        run_dir,
        working_name="working_model.zmx",
    )
    working_hash_before = sha256_file(copy_info["working_file"])

    print()
    print("========== DAY 6 CASE 002 QUICK FOCUS ==========")
    print(f"Working copy: {copy_info['working_file']}")
    print(f"Surface 2: {baseline:.7f} -> {target:.7f} mm")

    with StandaloneZemaxConnection() as connection:
        print("[PASS] ZOS-API connection")
        open_working_model(connection.system, copy_info["working_file"])
        print("[PASS] Case 002 working copy opened")

        set_surface_thickness(
            connection.system,
            parameter["surface"],
            target,
        )
        surface_2_after = read_surface(
            connection.system,
            parameter["surface"],
        )
        surface_6_before_focus = read_surface(connection.system, 6)

        focus_result = run_quick_focus(
            connection.system,
            connection.ZOSAPI,
            use_centroid=True,
        )
        surface_6_after_focus = read_surface(connection.system, 6)

        focused_thickness = focus_result["thickness_after_mm"]
        if not lower_bound <= focused_thickness <= upper_bound:
            raise ValueError(
                "Case 002 Quick Focus moved Surface 6 outside the "
                f"approved range: {focused_thickness} mm."
            )

        print(
            "Surface 2 after write: "
            f"{surface_2_after['thickness']:.7f} mm"
        )
        print(
            "Surface 6 radius before/after focus: "
            f"{surface_6_before_focus['radius']:.7f} -> "
            f"{surface_6_after_focus['radius']:.7f} mm"
        )
        print(
            "Image distance: "
            f"{focus_result['thickness_before_mm']:.7f} -> "
            f"{focus_result['thickness_after_mm']:.7f} mm"
        )
        print(f"Focus shift: {focus_result['focus_shift_mm']:+.7f} mm")
        print("[PASS] Case 002 Quick Focus completed in memory")

        saved_model = save_model_as(
            connection.system,
            run_dir / "case_002_surface2_5p508_focused.zmx",
            run_dir,
        )
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
            raise ValueError("Reloaded Case 002 thickness is incorrect.")

        if not math.isclose(
            surface_6_reloaded["thickness"],
            focused_thickness,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Reloaded Case 002 focus is incorrect.")

        print(f"Saved focused model: {saved_model}")
        print("[PASS] Case 002 focused model reloaded and verified")

        spot_text = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            run_dir / "case_002_standard_spot_raw.txt",
        )
        print(f"Standard Spot raw text: {spot_text}")
        print("[PASS] Case 002 Standard Spot raw text exported")

    if sha256_file(source_file) != source_hash_before:
        raise RuntimeError("Original model changed during Case 002 focus.")

    if sha256_file(copy_info["working_file"]) != working_hash_before:
        raise RuntimeError("Case 002 disk copy changed without SaveAs.")

    print("[PASS] Case 002 connection closed")
    print("[PASS] Case 002 disk working copy unchanged")
    print("[PASS] Focused Case 002 saved only under outputs")


def main():
    config = load_config("configs/baseline_case.yaml")

    validate_dry_run_mode(config)
    validate_scan_values(config["outer_parameter"])
    validate_source_model(config["model"])
    validate_model_path_protection(config["model"])

    source_file = PROJECT_ROOT / config["model"]["source_file"]
    source_hash_before = sha256_file(source_file)

    run_id = datetime.now().strftime("baseline_focus_check_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "outputs" / "day6_quick_focus" / run_id
    copy_info = copy_baseline_model(
        source_file,
        run_dir,
        working_name="working_model.zmx",
    )
    working_hash_before = sha256_file(copy_info["working_file"])
    lower_bound, upper_bound = get_focus_bounds(config)

    print("========== DAY 6 BASELINE QUICK FOCUS ==========")
    print(f"Working copy: {copy_info['working_file']}")
    print(f"Approved focus range: [{lower_bound}, {upper_bound}] mm")

    with StandaloneZemaxConnection() as connection:
        print("[PASS] ZOS-API connection")
        open_working_model(connection.system, copy_info["working_file"])
        print("[PASS] Baseline working copy opened")

        focus_result = run_quick_focus(
            connection.system,
            connection.ZOSAPI,
            use_centroid=True,
        )

        focused_thickness = focus_result["thickness_after_mm"]
        if not lower_bound <= focused_thickness <= upper_bound:
            raise ValueError(
                "Quick Focus moved Surface 6 outside the approved range: "
                f"{focused_thickness} mm."
            )

        print(f"Focus surface: {focus_result['focus_surface_id']}")
        print(
            "Image distance: "
            f"{focus_result['thickness_before_mm']:.7f} -> "
            f"{focus_result['thickness_after_mm']:.7f} mm"
        )
        print(f"Focus shift: {focus_result['focus_shift_mm']:+.7f} mm")
        print("[PASS] Baseline Quick Focus completed in memory")

        saved_model = save_model_as(
            connection.system,
            run_dir / "case_003_baseline_focused.zmx",
            run_dir,
        )
        open_working_model(connection.system, saved_model)
        surface_6_reloaded = read_surface(connection.system, 6)

        if not math.isclose(
            surface_6_reloaded["thickness"],
            focused_thickness,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Reloaded baseline focus is incorrect.")

        print(f"Saved focused model: {saved_model}")
        print("[PASS] Baseline focused model reloaded and verified")

        spot_text = export_standard_spot_text(
            connection.system,
            connection.ZOSAPI,
            run_dir / "case_003_standard_spot_raw.txt",
        )
        print(f"Standard Spot raw text: {spot_text}")
        print("[PASS] Baseline Standard Spot raw text exported")

    source_hash_after = sha256_file(source_file)
    working_hash_after = sha256_file(copy_info["working_file"])

    if source_hash_after != source_hash_before:
        raise RuntimeError("Original model changed during Quick Focus.")

    if working_hash_after != working_hash_before:
        raise RuntimeError("Disk working copy changed without SaveAs.")

    print("[PASS] ZOS-API connection closed")
    print("[PASS] Original model unchanged")
    print("[PASS] Disk working copy unchanged")
    print("[PASS] Focused baseline saved only under outputs")

    run_case_002_focus_check(config, lower_bound, upper_bound)


if __name__ == "__main__":
    main()
