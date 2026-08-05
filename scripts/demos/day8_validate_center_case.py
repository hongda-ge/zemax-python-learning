"""Day 8 step 2: reproduce the Day 7 baseline with one Zemax case."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day3_baseline_dry_run import (  # noqa: E402
    validate_dry_run_mode,
    validate_model_path_protection,
    validate_source_model,
)
from scripts.demos.day7_five_case_sweep import execute_one_case  # noqa: E402
from scripts.demos.day8_local_fine_scan_plan import (  # noqa: E402
    build_fine_case_plan,
    validate_execution_lock,
    validate_local_values,
    validate_parameter_identity,
)


def select_center_case(cases):
    """Require exactly one center/baseline case."""

    center_cases = [case for case in cases if case["is_baseline"]]
    if len(center_cases) != 1:
        raise ValueError(
            f"Expected exactly one center case, found {len(center_cases)}."
        )
    return center_cases[0]


def validate_center_authorization(scan_config):
    """Permit one center case while the full nine-case batch stays locked."""

    execution = scan_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("The full Day 8 batch must remain disabled.")
    if execution["allow_single_center_validation"] is not True:
        raise ValueError("The single Day 8 center validation is not approved.")


def compare_with_day7_reference(result, reference):
    """Verify that the Day 8 center reproduces the frozen Day 7 values."""

    focus_actual = result["focus"]["thickness_after_mm"]
    focus_expected = reference["focused_image_distance_mm"]
    if not math.isclose(
        focus_actual,
        focus_expected,
        rel_tol=0.0,
        abs_tol=reference["focus_tolerance_mm"],
    ):
        raise ValueError(
            "Day 8 center focus does not reproduce the Day 7 reference."
        )

    expected_rms = {
        0.0: reference["rms_radius_um"]["field_0_deg"],
        14.0: reference["rms_radius_um"]["field_14_deg"],
        20.0: reference["rms_radius_um"]["field_20_deg"],
    }
    comparisons = []
    for field in result["spot_metrics"]["fields"]:
        angle = field["field_y_degree"]
        actual = field["rms_radius_um"]
        expected = expected_rms[angle]
        difference = actual - expected
        if not math.isclose(
            actual,
            expected,
            rel_tol=0.0,
            abs_tol=reference["rms_tolerance_um"],
        ):
            raise ValueError(
                f"Field {angle:.1f} deg RMS does not reproduce Day 7."
            )
        comparisons.append(
            {
                "field_y_degree": angle,
                "day7_rms_um": expected,
                "day8_rms_um": actual,
                "difference_um": difference,
            }
        )

    return {
        "status": "pass",
        "reference_batch": reference["source_batch"],
        "focus_expected_mm": focus_expected,
        "focus_actual_mm": focus_actual,
        "focus_difference_mm": focus_actual - focus_expected,
        "field_comparisons": comparisons,
    }


def main():
    scan_config = load_config("configs/day8_local_fine_scan.yaml")
    baseline_config = load_config(scan_config["source"]["baseline_config"])

    validate_execution_lock(scan_config)
    validate_center_authorization(scan_config)
    validate_dry_run_mode(baseline_config)
    validate_parameter_identity(scan_config, baseline_config)
    validate_local_values(scan_config, baseline_config)
    validate_source_model(baseline_config["model"])
    validate_model_path_protection(baseline_config["model"])

    cases = build_fine_case_plan(scan_config)
    center_case = select_center_case(cases)
    run_id = datetime.now().strftime("center_check_%Y%m%d_%H%M%S")
    batch_dir = PROJECT_ROOT / scan_config["output"]["root"] / run_id

    print("========== DAY 8 CENTER REPRODUCIBILITY CHECK ==========")
    print("Only fine_005 will run; the other eight cases stay unexecuted.")
    print(
        f"Center case: {center_case['value_mm']:.7f} mm "
        f"({center_case['case_id']})"
    )
    print(f"Output directory: {batch_dir}")
    print()

    result = execute_one_case(
        baseline_config,
        center_case,
        batch_dir,
        task_name="day8_center_reproducibility_check",
    )
    comparison = compare_with_day7_reference(
        result,
        scan_config["reference"],
    )

    result["day7_reproducibility"] = comparison
    result_file = (
        batch_dir / center_case["directory_name"] / center_case["result_name"]
    )
    result_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        f"[PASS] Focus distance reproduced: "
        f"{comparison['focus_actual_mm']:.7f} mm"
    )
    for field in comparison["field_comparisons"]:
        print(
            f"[PASS] Field {field['field_y_degree']:.1f} deg RMS: "
            f"Day 7 {field['day7_rms_um']:.6f} um -> "
            f"Day 8 {field['day8_rms_um']:.6f} um"
        )
    print("[PASS] Original model unchanged")
    print("[PASS] Initial working copy unchanged")
    print("[PASS] ZOS-API connection closed")
    print(f"[PASS] Result report: {result_file}")
    print("Day 8 center case reproduced the Day 7 baseline.")


if __name__ == "__main__":
    main()
