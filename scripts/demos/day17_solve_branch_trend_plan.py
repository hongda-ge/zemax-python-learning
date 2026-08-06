"""Day 17 step 1: audit a five-point, two-branch trend plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_plan_lock(config):
    """Keep the plan offline while retaining reviewed control flags."""

    execution = config["execution"]
    locked = {
        "generic execution": execution["enabled"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in locked.items() if value is not False]
    if enabled:
        raise ValueError("Day 17 plan lock failed: " + ", ".join(enabled))

    reviewed = (
        "allow_zosapi_connection",
        "allow_surface2_in_memory_write",
        "allow_surface6_make_solve_fixed",
        "allow_quick_focus",
        "allow_standard_spot",
        "allow_baseline_control_execution",
        "allow_trend_evaluation",
    )
    for key in reviewed:
        if not isinstance(execution[key], bool):
            raise ValueError(f"{key} must be Boolean.")


def validate_source(config):
    """Verify the frozen baseline model and outer parameter."""

    baseline = load_config(config["source"]["baseline_config"])
    source_file = PROJECT_ROOT / baseline["model"]["source_file"]
    actual_hash = sha256_file(source_file).upper()
    expected = str(config["source"]["expected_source_sha256"]).upper()
    baseline_hash = str(baseline["model"]["source_sha256"]).upper()
    if actual_hash != expected or actual_hash != baseline_hash:
        raise ValueError("The Day 17 source-model fingerprint changed.")

    parameter = config["parameter"]
    outer = baseline["outer_parameter"]
    if int(parameter["surface_id"]) != int(outer["surface"]):
        raise ValueError("Day 17 uses the wrong outer-parameter surface.")
    if parameter["property"] != outer["property"]:
        raise ValueError("Day 17 uses the wrong outer-parameter property.")
    if not math.isclose(
        float(parameter["baseline_value_mm"]),
        float(outer["baseline_value"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Day 17 baseline thickness changed.")
    return baseline, source_file, actual_hash


def newest_report(root, pattern, report_name):
    """Return the newest report below one reviewed output root."""

    matches = list((PROJECT_ROOT / root).glob(f"{pattern}/{report_name}"))
    if not matches:
        raise FileNotFoundError(f"No reviewed report found below {root}.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day8_evidence(config, report_file):
    """Require all five planned values to be successful Day 8 cases."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "task": report.get("task") == source["day8_expected_task"],
        "status": report.get("status") == "success",
        "case count": report.get("case_count") == source["day8_expected_case_count"],
        "success count": report.get("success_count") == source["day8_expected_case_count"],
        "no rejection": report.get("rejected_count") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 8 evidence failed: " + ", ".join(failed))

    successful = {
        round(float(row["value_mm"]), 7): row
        for row in report["rows"]
        if row["status"] == "success"
    }
    selected = [float(value) for value in config["parameter"]["selected_values_mm"]]
    rows = []
    for value in selected:
        key = round(value, 7)
        if key not in successful:
            raise ValueError(f"Day 8 did not approve {value:.7f} mm.")
        rows.append(successful[key])
    return report, rows


def validate_day16_evidence(config, report_file):
    """Require the reviewed single-point branch method and safety audit."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "task": report.get("task") == source["day16_expected_task"],
        "status": report.get("status") == "success",
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
    }
    for key in ("preserve_solve", "freeze_radius"):
        branch = report.get(key, {})
        checks[f"{key} success"] = branch.get("status") == "success"
        checks[f"{key} connection closed"] = branch.get("connection_closed") is True
        checks[f"{key} source unchanged"] = branch.get("source_unchanged") is True
        checks[f"{key} copy unchanged"] = branch.get("working_copy_unchanged") is True
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 16 evidence failed: " + ", ".join(failed))

    parameter = config["parameter"]
    actual_delta = float(report["parameter"]["test_delta_mm"])
    actual_value = float(report["parameter"]["test_value_mm"])
    if not math.isclose(
        actual_delta,
        float(parameter["day16_anchor_delta_mm"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("The Day 16 anchor delta changed.")
    if not math.isclose(
        actual_value,
        float(parameter["day16_anchor_value_mm"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("The Day 16 anchor value changed.")
    return report


def build_case_plan(config):
    """Build five explicit thickness cases and ten branch tasks."""

    parameter = config["parameter"]
    baseline = float(parameter["baseline_value_mm"])
    deltas = [float(value) for value in parameter["selected_deltas_mm"]]
    values = [float(value) for value in parameter["selected_values_mm"]]
    if len(deltas) != len(values):
        raise ValueError("Day 17 delta/value counts differ.")

    cases = []
    for index, (delta, value) in enumerate(zip(deltas, values), start=1):
        if not math.isclose(baseline + delta, value, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Day 17 case {index} value does not match delta.")
        tag = f"{value:.3f}".replace("-", "m").replace(".", "p")
        case_id = f"trend_{index:03d}"
        cases.append(
            {
                "case_id": case_id,
                "value_mm": value,
                "delta_mm": delta,
                "is_baseline": math.isclose(delta, 0.0, abs_tol=1e-12),
                "directory_name": f"{case_id}_{tag}",
                "branch_tasks": [
                    f"{case_id}/preserve_solve",
                    f"{case_id}/freeze_radius",
                ],
            }
        )
    if len({case["value_mm"] for case in cases}) != len(cases):
        raise ValueError("Day 17 thickness values are not unique.")
    if sum(case["is_baseline"] for case in cases) != 1:
        raise ValueError("Day 17 requires exactly one baseline control.")
    expected = config["comparison"]
    if len(cases) != int(expected["new_thickness_points"]):
        raise ValueError("Day 17 planned thickness count changed.")
    if sum(len(case["branch_tasks"]) for case in cases) != int(
        expected["new_branch_runs"]
    ):
        raise ValueError("Day 17 planned branch count changed.")
    return cases


def validate_common_recipe(config, baseline):
    """Freeze the Day 16 compensation and Standard Spot recipe."""

    compensation = config["compensation"]
    if compensation != {
        "tool": "QuickFocus",
        "criterion": "spot_size_radial",
        "use_centroid": True,
        "focus_surface_id": 6,
        "approved_thickness_range_mm": [40.0, 44.5],
    }:
        raise ValueError("Day 17 Quick Focus recipe changed.")
    expected_spot = {
        "type": "Standard_Spot",
        "ray_density": 6,
        "pattern": "hexapolar",
        "fields": "all",
        "wavelengths": "all",
        "surface": "image",
        "reference": "centroid",
        "polarization": False,
    }
    for key, expected in expected_spot.items():
        if config["analysis"][key] != expected:
            raise ValueError(f"Day 17 Spot setting changed: {key}.")
        if baseline["analysis"]["standard_spot"][key] != expected:
            raise ValueError(f"Baseline Spot setting differs: {key}.")
    if config["comparison"]["hidden_weighted_score"] is not False:
        raise ValueError("Day 17 hidden score must remain forbidden.")
    if config["comparison"]["allow_unique_engineering_winner"] is not False:
        raise ValueError("Day 17 must not declare an engineering winner.")


def main():
    config = load_config("configs/day17_solve_branch_trend.yaml")
    validate_plan_lock(config)
    baseline, source_file, source_hash = validate_source(config)
    day8_file = newest_report(
        config["source"]["day8_output_root"],
        "fine_scan_*",
        config["source"]["day8_report_name"],
    )
    _, day8_rows = validate_day8_evidence(config, day8_file)
    day16_file = newest_report(
        config["source"]["day16_output_root"],
        "spot_comparison_*",
        config["source"]["day16_report_name"],
    )
    validate_day16_evidence(config, day16_file)
    cases = build_case_plan(config)
    validate_common_recipe(config, baseline)

    print("========== DAY 17 SOLVE-BRANCH TREND PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will be created.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Day 8 successful-range evidence: {day8_file}")
    print(f"Day 16 branch-method evidence: {day16_file}")
    print()
    print("Five new thickness points, two independent branches per point:")
    day8_by_value = {round(float(row["value_mm"]), 7): row for row in day8_rows}
    for case in cases:
        evidence = day8_by_value[round(case["value_mm"], 7)]
        marker = " <- baseline control" if case["is_baseline"] else ""
        print(
            f"  {case['case_id']}: {case['value_mm']:.7f} mm, "
            f"delta {case['delta_mm']:+.1f} mm{marker}"
        )
        print(
            "    Day 8 preserve-Solve evidence: "
            f"focus={evidence['focus_shift_mm']:+.4f} mm, "
            f"RMS=[{evidence['rms_0deg_um']:.3f}, "
            f"{evidence['rms_14deg_um']:.3f}, "
            f"{evidence['rms_20deg_um']:.3f}] um"
        )
        print("    planned: preserve_solve + freeze_radius")
    print()
    print(
        "Reused Day 16 anchor: "
        f"{config['parameter']['day16_anchor_value_mm']:.7f} mm "
        f"(delta {config['parameter']['day16_anchor_delta_mm']:+.1f} mm)"
    )
    print("Total new Zemax branch runs after approval: 10")
    print()
    print("[PASS] Frozen source model verified")
    print("[PASS] Five values verified inside the successful Day 8 scan")
    print("[PASS] Day 16 branch method and safety audit verified")
    print("[PASS] Exactly one baseline control and ten unique branch tasks")
    print("[PASS] Identical Quick Focus and Standard Spot recipes frozen")
    print("[PASS] Optimization, SaveAs, hidden score and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
