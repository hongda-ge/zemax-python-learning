"""Day 8 step 1: validate and print a nine-point local scan plan."""

import math
import sys
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


def value_tag(value):
    """Convert a millimetre value into a short filesystem-safe tag."""

    return f"{value:.3f}".replace("-", "m").replace(".", "p")


def build_fine_case_plan(scan_config):
    """Create explicit records for the nine planned Day 8 cases."""

    center = scan_config["parameter"]["center_value"]
    values = scan_config["scan"]["values_mm"]
    deltas = scan_config["scan"]["deltas_mm"]
    cases = []

    for case_number, (value, delta) in enumerate(
        zip(values, deltas),
        start=1,
    ):
        case_id = f"fine_{case_number:03d}"
        tag = value_tag(value)
        cases.append(
            {
                "case_number": case_number,
                "case_id": case_id,
                "value_mm": value,
                "delta_mm": delta,
                "is_baseline": math.isclose(value, center, abs_tol=1e-9),
                "directory_name": f"{case_id}_{tag}",
                "focused_model_name": (
                    f"{case_id}_surface2_{tag}_focused.zmx"
                ),
                "spot_text_name": f"{case_id}_standard_spot.txt",
                "result_name": "result.json",
            }
        )

    return cases


def validate_execution_lock(scan_config):
    """Guarantee that this first Day 8 step cannot authorize Zemax."""

    execution = scan_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Day 8 plan requires execution.enabled=false.")
    if execution["plan_allow_zosapi_connection"] is not False:
        raise ValueError("Day 8 plan must not allow a ZOS-API connection.")


def validate_parameter_identity(scan_config, baseline_config):
    """Confirm that Day 8 still studies the approved Day 7 parameter."""

    planned = scan_config["parameter"]
    baseline = baseline_config["outer_parameter"]
    keys = ("surface", "property", "unit")

    for key in keys:
        if planned[key] != baseline[key]:
            raise ValueError(f"Parameter mismatch for {key}.")

    if not math.isclose(
        planned["center_value"],
        baseline["baseline_value"],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Day 8 center does not match the approved baseline.")


def validate_local_values(scan_config, baseline_config):
    """Check point count, spacing, hard limits, and the Day 7 bracket."""

    scan = scan_config["scan"]
    guardrails = scan_config["guardrails"]
    parameter = baseline_config["outer_parameter"]
    center = scan_config["parameter"]["center_value"]
    values = scan["values_mm"]
    deltas = scan["deltas_mm"]

    if len(values) != scan["expected_case_count"]:
        raise ValueError("Day 8 case count does not match the YAML plan.")
    if len(values) != len(deltas):
        raise ValueError("Each value must have exactly one delta.")
    if len(values) != len(set(values)):
        raise ValueError("Day 8 scan values are not unique.")
    if sum(math.isclose(value, center, abs_tol=1e-9) for value in values) != 1:
        raise ValueError("Day 8 requires exactly one center case.")

    for index, (value, delta) in enumerate(zip(values, deltas)):
        if not math.isclose(value, center + delta, abs_tol=1e-9):
            raise ValueError(f"Value/delta mismatch at case {index + 1}.")
        if not parameter["safety"]["hard_minimum"] <= value <= parameter[
            "safety"
        ]["hard_maximum"]:
            raise ValueError(f"Unsafe Day 8 thickness: {value} mm.")

    for left, right in zip(values, values[1:]):
        if right <= left:
            raise ValueError("Day 8 values must be strictly increasing.")
        if not math.isclose(
            right - left,
            scan["step_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Day 8 values do not use the declared step.")

    if guardrails["stay_inside_day7_successful_bracket"]:
        lower, upper = guardrails["day7_successful_bracket_mm"]
        if values[0] < lower or values[-1] > upper:
            raise ValueError("Day 8 extends outside the successful Day 7 bracket.")

    return values, deltas


def main():
    scan_config = load_config("configs/day8_local_fine_scan.yaml")
    baseline_config = load_config(scan_config["source"]["baseline_config"])

    validate_execution_lock(scan_config)
    validate_dry_run_mode(baseline_config)
    validate_parameter_identity(scan_config, baseline_config)
    values, deltas = validate_local_values(scan_config, baseline_config)
    cases = build_fine_case_plan(scan_config)
    source_path, source_hash = validate_source_model(baseline_config["model"])
    validate_model_path_protection(baseline_config["model"])

    parameter = scan_config["parameter"]
    center = parameter["center_value"]

    print("========== DAY 8 LOCAL FINE-SCAN PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print(
        f"Parameter: Surface {parameter['surface']} "
        f"{parameter['property']} ({parameter['unit']})"
    )
    print(f"Center: {center:.7f} mm")
    print(
        f"Range: [{values[0]:.7f}, {values[-1]:.7f}] mm, "
        f"step {scan_config['scan']['step_mm']:.1f} mm"
    )
    print()

    for case in cases:
        center_mark = " <- center/baseline" if case["is_baseline"] else ""
        print(
            f"{case['case_id']}: {case['value_mm']:.7f} mm, "
            f"delta {case['delta_mm']:+.1f} mm{center_mark}"
        )

    print()
    print(f"[PASS] {len(values)} unique local cases planned")
    print("[PASS] Exactly one center case")
    print("[PASS] All cases stay inside the successful Day 7 bracket")
    print(f"[PASS] Source model: {source_path}")
    print(f"[PASS] Source SHA256: {source_hash}")
    print("PLAN ONLY finished. No model or output was created.")


if __name__ == "__main__":
    main()
