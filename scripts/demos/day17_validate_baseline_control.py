"""Day 17 step 2: run only the zero-delta two-branch control."""

import copy
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import copy_baseline_model  # noqa: E402
from scripts.demos.day16_run_solve_branch_spot_comparison import (  # noqa: E402
    compare_results,
    execute_branch,
    print_branch,
)
from scripts.demos.day17_solve_branch_trend_plan import (  # noqa: E402
    build_case_plan,
    newest_report,
    validate_common_recipe,
    validate_day16_evidence,
    validate_day8_evidence,
    validate_plan_lock,
    validate_source,
)


def require_control_approval(config):
    """Allow the center control but keep the full trend batch locked."""

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
        "baseline control": execution["allow_baseline_control_execution"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 17 control action not approved: " + ", ".join(missing))
    forbidden = {
        "full trend evaluation": execution["allow_trend_evaluation"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 17 control action: " + ", ".join(enabled))


def build_execution_config(config, source_file, control):
    """Adapt the Day 17 control to the reviewed Day 16 branch executor."""

    execution = copy.deepcopy(config)
    execution["_source_file"] = str(source_file)
    execution["parameter"].update(
        {
            "nominal_value_mm": float(config["parameter"]["baseline_value_mm"]),
            "test_delta_mm": float(control["delta_mm"]),
            "test_value_mm": float(control["value_mm"]),
        }
    )
    return execution


def validate_control_result(config, preserve, frozen, comparison):
    """Require a near-zero branch difference at the nominal geometry."""

    guardrails = config["guardrails"]
    radius_difference = abs(
        float(comparison["surface6_radius_difference_after_write_mm"])
    )
    focus_difference = abs(
        float(comparison["focus_shift_difference_frozen_minus_preserve_mm"])
    )
    field_differences = [
        abs(float(field["frozen_minus_preserve_rms_um"]))
        for field in comparison["field_comparison"]
    ]
    maximum_field_difference = max(field_differences)
    checks = {
        "radius difference": (
            radius_difference
            <= float(guardrails["baseline_control_max_radius_difference_mm"])
        ),
        "focus difference": (
            focus_difference
            <= float(guardrails["baseline_control_max_focus_difference_mm"])
        ),
        "field RMS difference": (
            maximum_field_difference
            <= float(guardrails["baseline_control_max_field_rms_difference_um"])
        ),
        "preserve connection": preserve["connection_closed"] is True,
        "frozen connection": frozen["connection_closed"] is True,
        "preserve source": preserve["source_unchanged"] is True,
        "frozen source": frozen["source_unchanged"] is True,
        "preserve copy": preserve["working_copy_unchanged"] is True,
        "frozen copy": frozen["working_copy_unchanged"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 17 baseline control failed: " + ", ".join(failed))
    return {
        "radius_difference_mm": radius_difference,
        "focus_difference_mm": focus_difference,
        "maximum_field_rms_difference_um": maximum_field_difference,
        "checks": checks,
    }


def main():
    config = load_config("configs/day17_solve_branch_trend.yaml")
    validate_plan_lock(config)
    require_control_approval(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_common_recipe(config, baseline)

    day8_file = newest_report(
        config["source"]["day8_output_root"],
        "fine_scan_*",
        config["source"]["day8_report_name"],
    )
    validate_day8_evidence(config, day8_file)
    day16_file = newest_report(
        config["source"]["day16_output_root"],
        "spot_comparison_*",
        config["source"]["day16_report_name"],
    )
    validate_day16_evidence(config, day16_file)

    controls = [case for case in build_case_plan(config) if case["is_baseline"]]
    if len(controls) != 1:
        raise ValueError("Day 17 baseline control is not unique.")
    control = controls[0]
    execution_config = build_execution_config(config, source_file, control)
    run_id = datetime.now().strftime("baseline_control_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    case_dir = run_dir / control["directory_name"]
    results = {}

    print("========== DAY 17 BASELINE BRANCH CONTROL ==========")
    print("Only the zero-delta control will run.")
    print("The other four thickness points remain locked.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(
        f"Control: {control['case_id']}, Surface 2 = "
        f"{control['value_mm']:.7f} mm (delta {control['delta_mm']:+.1f} mm)"
    )
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        branch_dir = case_dir / branch_name
        working_name = (
            f"{control['case_id']}_"
            f"{config['branches'][branch_name]['working_suffix']}"
        )
        copy_info = copy_baseline_model(
            source_file,
            branch_dir,
            working_name,
        )
        print(f"\nRunning {branch_name} control...")
        results[branch_name] = execute_branch(
            execution_config,
            branch_name,
            Path(copy_info["working_file"]),
            branch_dir,
            task_name="day17_baseline_branch_control",
        )
        print("[PASS] Branch completed; connection closed and hashes unchanged")

    comparison = compare_results(
        results["preserve_solve"],
        results["freeze_radius"],
    )
    validation = validate_control_result(
        config,
        results["preserve_solve"],
        results["freeze_radius"],
        comparison,
    )
    report = {
        "task": "day17_baseline_branch_control",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day8_report": str(day8_file),
        "source_day16_report": str(day16_file),
        "control_case": control,
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "comparison": comparison,
        "control_validation": validation,
        "optimization_used": False,
        "save_as_used": False,
    }
    report_file = run_dir / "baseline_control_report.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 17 CONTROL RESULT ==========")
    print_branch(results["preserve_solve"])
    print_branch(results["freeze_radius"])
    print(
        "Maximum absolute field RMS difference: "
        f"{validation['maximum_field_rms_difference_um']:.6f} um"
    )
    print(
        "Absolute focus-shift difference: "
        f"{validation['focus_difference_mm']:.10f} mm"
    )
    print("[PASS] Zero-delta branch control is equivalent")
    print("[PASS] Remaining eight branch runs were not executed")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
