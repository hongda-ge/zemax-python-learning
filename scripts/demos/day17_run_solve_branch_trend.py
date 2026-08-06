"""Day 17 step 3: run four remaining thicknesses in two Solve branches."""

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
from modules.zemax.model_ops import copy_baseline_model  # noqa: E402
from scripts.demos.day16_run_solve_branch_spot_comparison import (  # noqa: E402
    compare_results,
    execute_branch,
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
from scripts.demos.day17_validate_baseline_control import (  # noqa: E402
    build_execution_config,
)


def require_trend_approval(config):
    """Require explicit approval for the eight remaining branch runs."""

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
        "passed baseline control": execution[
            "allow_baseline_control_execution"
        ],
        "trend evaluation": execution["allow_trend_evaluation"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 17 trend action not approved: " + ", ".join(missing))
    forbidden = {
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 17 trend action: " + ", ".join(enabled))


def find_latest_control_report(config):
    """Find the newest successful zero-delta branch-control report."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(root.glob("baseline_control_*/baseline_control_report.json"))
    if not matches:
        raise FileNotFoundError("No Day 17 baseline-control report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_control_evidence(report_file):
    """Require exact control equivalence and complete safety evidence."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "task": report.get("task") == "day17_baseline_branch_control",
        "status": report.get("status") == "success",
        "zero delta": math.isclose(
            float(report.get("control_case", {}).get("delta_mm", math.nan)),
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "radius equivalent": math.isclose(
            float(
                report.get("control_validation", {}).get(
                    "radius_difference_mm", math.nan
                )
            ),
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "focus equivalent": math.isclose(
            float(
                report.get("control_validation", {}).get(
                    "focus_difference_mm", math.nan
                )
            ),
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "Spot equivalent": math.isclose(
            float(
                report.get("control_validation", {}).get(
                    "maximum_field_rms_difference_um", math.nan
                )
            ),
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
    }
    for branch_name in ("preserve_solve", "freeze_radius"):
        branch = report.get(branch_name, {})
        checks[f"{branch_name} success"] = branch.get("status") == "success"
        checks[f"{branch_name} connection"] = branch.get("connection_closed") is True
        checks[f"{branch_name} source"] = branch.get("source_unchanged") is True
        checks[f"{branch_name} copy"] = branch.get("working_copy_unchanged") is True
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 17 control evidence failed: " + ", ".join(failed))
    return report


def validate_preserve_reproduction(config, day8_row, preserve):
    """Require each preserve branch to reproduce its Day 8 evidence."""

    guardrails = config["guardrails"]
    focus_difference = abs(
        float(preserve["focus"]["focus_shift_mm"])
        - float(day8_row["focus_shift_mm"])
    )
    fields = {
        round(float(field["field_y_degree"]), 1): float(field["rms_radius_um"])
        for field in preserve["spot_summary"]["fields"]
    }
    expected = {
        0.0: float(day8_row["rms_0deg_um"]),
        14.0: float(day8_row["rms_14deg_um"]),
        20.0: float(day8_row["rms_20deg_um"]),
    }
    field_differences = {
        angle: fields[angle] - expected[angle] for angle in expected
    }
    maximum_field_difference = max(abs(value) for value in field_differences.values())
    if focus_difference > float(
        guardrails["preserve_reproduction_max_focus_difference_mm"]
    ):
        raise ValueError("Preserve branch did not reproduce the Day 8 focus shift.")
    if maximum_field_difference > float(
        guardrails["preserve_reproduction_max_field_rms_difference_um"]
    ):
        raise ValueError("Preserve branch did not reproduce the Day 8 Spot result.")
    return {
        "focus_shift_difference_mm": focus_difference,
        "field_rms_differences_um": field_differences,
        "maximum_field_rms_difference_um": maximum_field_difference,
    }


def make_summary_row(case, preserve, frozen, comparison, evidence_source):
    """Flatten one thickness comparison for CSV and trend inspection."""

    field_differences = {
        float(field["field_y_degree"]): float(
            field["frozen_minus_preserve_rms_um"]
        )
        for field in comparison["field_comparison"]
    }
    return {
        "case_id": case["case_id"],
        "evidence_source": evidence_source,
        "value_mm": float(case["value_mm"]),
        "delta_mm": float(case["delta_mm"]),
        "preserve_radius_mm": float(
            preserve["after_surface2_write"]["surface6_radius_mm"]
        ),
        "frozen_radius_mm": float(
            frozen["after_surface2_write"]["surface6_radius_mm"]
        ),
        "preserve_minus_frozen_radius_mm": float(
            comparison["surface6_radius_difference_after_write_mm"]
        ),
        "preserve_focus_shift_mm": float(preserve["focus"]["focus_shift_mm"]),
        "frozen_focus_shift_mm": float(frozen["focus"]["focus_shift_mm"]),
        "frozen_minus_preserve_focus_shift_mm": float(
            comparison["focus_shift_difference_frozen_minus_preserve_mm"]
        ),
        "preserve_mean_rms_um": float(
            preserve["spot_summary"]["equal_field_mean_rms_um"]
        ),
        "frozen_mean_rms_um": float(
            frozen["spot_summary"]["equal_field_mean_rms_um"]
        ),
        "frozen_minus_preserve_mean_rms_um": float(
            comparison["mean_rms_difference_frozen_minus_preserve_um"]
        ),
        "preserve_worst_rms_um": float(
            preserve["spot_summary"]["worst_field_rms_um"]
        ),
        "frozen_worst_rms_um": float(
            frozen["spot_summary"]["worst_field_rms_um"]
        ),
        "frozen_minus_preserve_worst_rms_um": float(
            comparison["worst_rms_difference_frozen_minus_preserve_um"]
        ),
        "frozen_minus_preserve_rms_0deg_um": field_differences[0.0],
        "frozen_minus_preserve_rms_14deg_um": field_differences[14.0],
        "frozen_minus_preserve_rms_20deg_um": field_differences[20.0],
    }


def report_to_case_row(report, case_id, evidence_source):
    """Convert an existing Day 16/control report into a trend row."""

    parameter = report.get("parameter")
    if parameter is not None:
        case = {
            "case_id": case_id,
            "value_mm": float(parameter["test_value_mm"]),
            "delta_mm": float(parameter["test_delta_mm"]),
        }
    else:
        control = report["control_case"]
        case = {
            "case_id": case_id,
            "value_mm": float(control["value_mm"]),
            "delta_mm": float(control["delta_mm"]),
        }
    return make_summary_row(
        case,
        report["preserve_solve"],
        report["freeze_radius"],
        report["comparison"],
        evidence_source,
    )


def write_csv(path, rows):
    """Write one transparent comparison table."""

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = load_config("configs/day17_solve_branch_trend.yaml")
    validate_plan_lock(config)
    require_trend_approval(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_common_recipe(config, baseline)
    day8_file = newest_report(
        config["source"]["day8_output_root"],
        "fine_scan_*",
        config["source"]["day8_report_name"],
    )
    _, day8_rows = validate_day8_evidence(config, day8_file)
    day8_by_value = {
        round(float(row["value_mm"]), 7): row for row in day8_rows
    }
    day16_file = newest_report(
        config["source"]["day16_output_root"],
        "spot_comparison_*",
        config["source"]["day16_report_name"],
    )
    day16_report = validate_day16_evidence(config, day16_file)
    control_file = find_latest_control_report(config)
    control_report = validate_control_evidence(control_file)

    cases = build_case_plan(config)
    remaining = [case for case in cases if not case["is_baseline"]]
    if len(remaining) != 4:
        raise ValueError("Day 17 must run exactly four remaining thickness points.")
    run_id = datetime.now().strftime("trend_batch_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    new_results = []
    rows = [
        report_to_case_row(day16_report, "day16_anchor", "reused_day16"),
        report_to_case_row(control_report, "trend_003", "reused_day17_control"),
    ]

    print("========== DAY 17 REVIEWED SOLVE-BRANCH TREND ==========")
    print(f"Approved baseline control: {control_file}")
    print(f"Batch directory: {run_dir}")
    print("Four remaining thickness points will run sequentially.")
    print("Each point uses independent preserve/freeze working copies.")
    print("The batch stops on the first unexpected failure.")
    print("No optimization or SaveAs will be used.")

    for case in remaining:
        print(
            f"\nRunning {case['case_id']} at {case['value_mm']:.7f} mm "
            f"(delta {case['delta_mm']:+.1f} mm)..."
        )
        execution_config = build_execution_config(config, source_file, case)
        branch_results = {}
        case_dir = run_dir / case["directory_name"]
        for branch_name in ("preserve_solve", "freeze_radius"):
            branch_dir = case_dir / branch_name
            working_name = (
                f"{case['case_id']}_"
                f"{config['branches'][branch_name]['working_suffix']}"
            )
            copy_info = copy_baseline_model(
                source_file,
                branch_dir,
                working_name,
            )
            branch_results[branch_name] = execute_branch(
                execution_config,
                branch_name,
                Path(copy_info["working_file"]),
                branch_dir,
                task_name="day17_solve_branch_trend",
            )
            print(f"  [PASS] {branch_name}")

        reproduction = validate_preserve_reproduction(
            config,
            day8_by_value[round(float(case["value_mm"]), 7)],
            branch_results["preserve_solve"],
        )
        comparison = compare_results(
            branch_results["preserve_solve"],
            branch_results["freeze_radius"],
        )
        case_result = {
            "case": case,
            "preserve_solve": branch_results["preserve_solve"],
            "freeze_radius": branch_results["freeze_radius"],
            "day8_reproduction": reproduction,
            "comparison": comparison,
        }
        new_results.append(case_result)
        rows.append(
            make_summary_row(
                case,
                branch_results["preserve_solve"],
                branch_results["freeze_radius"],
                comparison,
                "new_day17_run",
            )
        )
        print(
            "  [PASS] Day 8 reproduced; frozen-preserve mean RMS: "
            f"{comparison['mean_rms_difference_frozen_minus_preserve_um']:+.3f} um"
        )

    rows.sort(key=lambda row: float(row["delta_mm"]))
    batch_report = {
        "task": "day17_solve_branch_trend",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day8_report": str(day8_file),
        "source_day16_report": str(day16_file),
        "source_control_report": str(control_file),
        "new_case_count": len(new_results),
        "new_branch_run_count": len(new_results) * 2,
        "reused_evidence_count": 2,
        "new_results": new_results,
        "trend_rows": rows,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file = run_dir / "trend_batch_report.json"
    csv_file = run_dir / "solve_branch_trend.csv"
    report_file.write_text(
        json.dumps(batch_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(csv_file, rows)

    print("\n========== DAY 17 TREND SUMMARY ==========")
    for row in rows:
        print(
            f"delta {row['delta_mm']:+.1f} mm: "
            f"radius diff={row['preserve_minus_frozen_radius_mm']:+.7f} mm, "
            f"focus diff={row['frozen_minus_preserve_focus_shift_mm']:+.7f} mm, "
            f"mean RMS diff={row['frozen_minus_preserve_mean_rms_um']:+.3f} um"
        )
    print("[PASS] Four new thicknesses and eight branches completed")
    print("[PASS] All preserve branches reproduced Day 8")
    print("[PASS] All connections closed and disk models remained unchanged")
    print("[RESULT] Unique engineering winner: NONE")
    print(f"[PASS] Trend CSV: {csv_file}")
    print(f"[PASS] Batch report: {report_file}")


if __name__ == "__main__":
    main()
