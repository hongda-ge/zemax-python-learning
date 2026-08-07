"""Day 18 step 1: audit the endpoint focus-compensation experiment plan."""

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
    """Keep the plan offline while retaining reviewed endpoint flags."""

    execution = config["execution"]
    locked = {
        "generic execution": execution["enabled"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in locked.items() if value is not False]
    if enabled:
        raise ValueError("Day 18 plan lock failed: " + ", ".join(enabled))

    reviewed = (
        "allow_zosapi_connection",
        "allow_surface2_in_memory_write",
        "allow_surface6_make_solve_fixed",
        "allow_uncompensated_standard_spot",
        "allow_quick_focus",
        "allow_compensated_standard_spot",
        "allow_endpoint_001_execution",
        "allow_endpoint_002_execution",
        "allow_offline_analysis",
    )
    for key in reviewed:
        if not isinstance(execution[key], bool):
            raise ValueError(f"{key} must be Boolean.")


def validate_source(config):
    """Verify the frozen model and outer-parameter definition."""

    baseline = load_config(config["source"]["baseline_config"])
    source_file = PROJECT_ROOT / baseline["model"]["source_file"]
    actual_hash = sha256_file(source_file).upper()
    expected_hash = str(config["source"]["expected_source_sha256"]).upper()
    baseline_hash = str(baseline["model"]["source_sha256"]).upper()
    if actual_hash != expected_hash or actual_hash != baseline_hash:
        raise ValueError("The Day 18 source-model fingerprint changed.")

    parameter = config["parameter"]
    outer = baseline["outer_parameter"]
    if int(parameter["surface_id"]) != int(outer["surface"]):
        raise ValueError("Day 18 uses the wrong outer-parameter surface.")
    if parameter["property"] != outer["property"]:
        raise ValueError("Day 18 uses the wrong outer-parameter property.")
    if not math.isclose(
        float(parameter["baseline_value_mm"]),
        float(outer["baseline_value"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Day 18 baseline thickness changed.")
    return baseline, source_file, actual_hash


def find_latest_day17_reports(config):
    """Find a matching completed Day 17 batch and offline analysis."""

    root = PROJECT_ROOT / config["source"]["day17_output_root"]
    batch_matches = list(root.glob("trend_batch_*/trend_batch_report.json"))
    if not batch_matches:
        raise FileNotFoundError("No Day 17 trend batch was found.")
    batch_file = max(batch_matches, key=lambda path: path.stat().st_mtime)
    analysis_file = batch_file.parent / config["source"][
        "day17_analysis_report_name"
    ]
    if not analysis_file.is_file():
        raise FileNotFoundError("The matching Day 17 analysis report is missing.")
    return batch_file, analysis_file


def validate_day17_evidence(config, batch_file, analysis_file):
    """Require complete endpoint, safety and offline-analysis evidence."""

    batch = json.loads(batch_file.read_text(encoding="utf-8"))
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "batch task": batch.get("task") == source["day17_expected_batch_task"],
        "batch status": batch.get("status") == "success",
        "four new cases": batch.get("new_case_count") == 4,
        "eight new branches": batch.get("new_branch_run_count") == 8,
        "batch no optimization": batch.get("optimization_used") is False,
        "batch no SaveAs": batch.get("save_as_used") is False,
        "batch no winner": batch.get("unique_engineering_winner") is None,
        "analysis task": (
            analysis.get("task") == source["day17_expected_analysis_task"]
        ),
        "analysis status": analysis.get("status") == "success",
        "analysis source": (
            Path(analysis.get("source_batch_report", "")).resolve()
            == batch_file.resolve()
        ),
        "analysis no ZOS-API": analysis.get("zosapi_connection_used") is False,
        "analysis no optical calculation": (
            analysis.get("new_optical_calculation_used") is False
        ),
        "analysis no hidden score": (
            analysis.get("hidden_weighted_score_used") is False
        ),
        "analysis no winner": analysis.get("unique_engineering_winner") is None,
    }
    for result in batch.get("new_results", []):
        case_id = result.get("case", {}).get("case_id", "unknown")
        for branch_name in ("preserve_solve", "freeze_radius"):
            branch = result.get(branch_name, {})
            checks[f"{case_id} {branch_name} success"] = (
                branch.get("status") == "success"
            )
            checks[f"{case_id} {branch_name} connection"] = (
                branch.get("connection_closed") is True
            )
            checks[f"{case_id} {branch_name} source"] = (
                branch.get("source_unchanged") is True
            )
            checks[f"{case_id} {branch_name} copy"] = (
                branch.get("working_copy_unchanged") is True
            )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 17 evidence failed: " + ", ".join(failed))

    endpoint_deltas = {
        round(float(value), 7) for value in config["parameter"]["endpoint_deltas_mm"]
    }
    rows = {
        round(float(row["delta_mm"]), 7): row for row in batch["trend_rows"]
    }
    missing = endpoint_deltas.difference(rows)
    if missing:
        raise ValueError(f"Day 17 endpoint evidence is missing: {sorted(missing)}.")
    return batch, analysis, [rows[delta] for delta in sorted(endpoint_deltas)]


def build_endpoint_plan(config):
    """Build two endpoints, four branches and eight paired Spot states."""

    parameter = config["parameter"]
    baseline = float(parameter["baseline_value_mm"])
    deltas = [float(value) for value in parameter["endpoint_deltas_mm"]]
    values = [float(value) for value in parameter["endpoint_values_mm"]]
    if len(deltas) != len(values):
        raise ValueError("Day 18 endpoint delta/value counts differ.")
    endpoints = []
    for index, (delta, value) in enumerate(zip(deltas, values), start=1):
        if not math.isclose(baseline + delta, value, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Day 18 endpoint {index} value does not match delta.")
        tag = f"{value:.3f}".replace("-", "m").replace(".", "p")
        endpoint_id = f"endpoint_{index:03d}"
        endpoints.append(
            {
                "endpoint_id": endpoint_id,
                "value_mm": value,
                "delta_mm": delta,
                "directory_name": f"{endpoint_id}_{tag}",
                "branches": ["preserve_solve", "freeze_radius"],
                "spot_states": ["uncompensated", "compensated"],
            }
        )
    comparison = config["comparison"]
    branch_count = sum(len(item["branches"]) for item in endpoints)
    spot_count = sum(
        len(item["branches"]) * len(item["spot_states"])
        for item in endpoints
    )
    if len(endpoints) != int(comparison["endpoint_count"]):
        raise ValueError("Day 18 endpoint count changed.")
    if branch_count != int(comparison["branch_model_count"]):
        raise ValueError("Day 18 branch-model count changed.")
    if spot_count != int(comparison["standard_spot_export_count"]):
        raise ValueError("Day 18 Spot export count changed.")
    if branch_count != int(comparison["quick_focus_run_count"]):
        raise ValueError("Day 18 Quick Focus count changed.")
    return endpoints


def validate_common_recipe(config, baseline):
    """Freeze image-plane states and the common Standard Spot recipe."""

    states = config["observation_states"]
    if states["uncompensated"]["quick_focus_used"] is not False:
        raise ValueError("Uncompensated state must not use Quick Focus.")
    if states["compensated"]["quick_focus_used"] is not True:
        raise ValueError("Compensated state must use Quick Focus.")
    if states["compensated"]["criterion"] != "spot_size_radial":
        raise ValueError("Day 18 Quick Focus criterion changed.")
    if states["compensated"]["use_centroid"] is not True:
        raise ValueError("Day 18 Quick Focus must use centroid.")
    if states["compensated"]["approved_thickness_range_mm"] != [40.0, 44.5]:
        raise ValueError("Day 18 focus range changed.")

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
            raise ValueError(f"Day 18 Spot setting changed: {key}.")
        if baseline["analysis"]["standard_spot"][key] != expected:
            raise ValueError(f"Baseline Spot setting differs: {key}.")
    if config["comparison"]["hidden_weighted_score"] is not False:
        raise ValueError("Day 18 hidden score must remain forbidden.")
    if config["comparison"]["allow_unique_engineering_winner"] is not False:
        raise ValueError("Day 18 must not declare an engineering winner.")


def main():
    config = load_config("configs/day18_focus_compensation_effect.yaml")
    validate_plan_lock(config)
    baseline, source_file, source_hash = validate_source(config)
    batch_file, analysis_file = find_latest_day17_reports(config)
    _, _, endpoint_rows = validate_day17_evidence(
        config,
        batch_file,
        analysis_file,
    )
    endpoints = build_endpoint_plan(config)
    validate_common_recipe(config, baseline)
    evidence_by_delta = {
        round(float(row["delta_mm"]), 7): row for row in endpoint_rows
    }

    print("========== DAY 18 FOCUS-COMPENSATION PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will be created.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Day 17 batch evidence: {batch_file}")
    print(f"Day 17 analysis evidence: {analysis_file}")
    print()
    print("Planned endpoint experiments:")
    for endpoint in endpoints:
        row = evidence_by_delta[round(endpoint["delta_mm"], 7)]
        print(
            f"  {endpoint['endpoint_id']}: {endpoint['value_mm']:.7f} mm, "
            f"delta {endpoint['delta_mm']:+.1f} mm"
        )
        print(
            "    Day 17 after-focus evidence: "
            f"radius diff={row['preserve_minus_frozen_radius_mm']:+.7f} mm, "
            f"focus diff={row['frozen_minus_preserve_focus_shift_mm']:+.7f} mm, "
            f"mean Spot diff={row['frozen_minus_preserve_mean_rms_um']:+.3f} um"
        )
        print("    preserve_solve: fixed-image Spot -> Quick Focus -> focused Spot")
        print("    freeze_radius: fixed-image Spot -> Quick Focus -> focused Spot")
    print()
    print("Planned workload after approval:")
    print("  independent branch models: 4")
    print("  Standard Spot exports: 8")
    print("  Quick Focus runs: 4")
    print()
    print("[PASS] Frozen source model verified")
    print("[PASS] Day 17 endpoint and safety evidence verified")
    print("[PASS] Fixed-image and focused observation states declared")
    print("[PASS] Identical Standard Spot recipe frozen for all observations")
    print("[PASS] Optimization, SaveAs, hidden score and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
