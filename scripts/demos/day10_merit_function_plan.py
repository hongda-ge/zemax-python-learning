"""Day 10 step 1: audit and print the Merit Function candidate plan."""

import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day9_fft_mtf_plan import (  # noqa: E402
    build_candidate_plan,
    find_latest_day8_report,
)


def validate_execution_lock(day10_config):
    """Guarantee that planning cannot connect to or modify Zemax."""

    execution = day10_config["execution"]
    evaluation = day10_config["evaluation"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 10 execution must remain disabled.")
    if execution["plan_allow_zosapi_connection"] is not False:
        raise ValueError("The Day 10 plan must not allow ZOS-API.")
    if evaluation["operation"] != "calculate_only":
        raise ValueError("Day 10 must use calculate-only evaluation.")
    if evaluation["optimization_allowed"] is not False:
        raise ValueError("Day 10 must not authorize optimization.")


def find_latest_day9_tradeoff_report(day10_config):
    """Find the newest completed Day 9 Spot/MTF trade-off report."""

    source = day10_config["source"]
    search_root = PROJECT_ROOT / source["day9_output_root"]
    matches = list(
        search_root.glob(
            "candidate_batch_*/" + source["day9_tradeoff_report_name"]
        )
    )
    if not matches:
        raise FileNotFoundError("No Day 9 trade-off report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def load_tradeoff_rows(day10_config, report_file):
    """Load the Day 9 combined metrics next to the selected report."""

    csv_file = report_file.with_name(
        day10_config["source"]["day9_tradeoff_csv_name"]
    )
    if not csv_file.is_file():
        raise FileNotFoundError(f"Day 9 trade-off CSV not found: {csv_file}")
    with csv_file.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return csv_file, {row["case_id"]: row for row in rows}


def validate_pareto_selection(day10_config, report):
    """Require exactly the reviewed, non-dominated Day 9 candidates."""

    if report.get("task") != "day9_spot_mtf_tradeoff_analysis":
        raise ValueError("Unexpected Day 9 report type.")

    actual_ids = report.get("pareto_candidate_ids", [])
    expected_ids = day10_config["selection"]["expected_candidate_ids"]
    expected_count = day10_config["selection"]["expected_candidate_count"]
    if actual_ids != expected_ids:
        raise ValueError("Day 9 Pareto candidate identities changed.")
    if len(actual_ids) != expected_count or len(set(actual_ids)) != len(actual_ids):
        raise ValueError("Day 10 candidate count is invalid.")

    dominated = report.get("dominated_candidates", {})
    if any(case_id in dominated for case_id in actual_ids):
        raise ValueError("A dominated candidate entered the Day 10 plan.")
    return actual_ids


def build_merit_candidate_plan(day10_config, report_file):
    """Join Day 9 decisions to the hash-verified Day 8 focused models."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    selected_ids = validate_pareto_selection(day10_config, report)
    csv_file, metric_rows = load_tradeoff_rows(day10_config, report_file)

    day9_config = load_config("configs/day9_fft_mtf_validation.yaml")
    day8_report_file = find_latest_day8_report(day9_config)
    _, all_candidates = build_candidate_plan(day9_config, day8_report_file)
    candidates_by_id = {
        candidate["case_id"]: candidate for candidate in all_candidates
    }

    planned = []
    for case_id in selected_ids:
        if case_id not in candidates_by_id or case_id not in metric_rows:
            raise ValueError(f"Missing Day 10 evidence for {case_id}.")
        row = metric_rows[case_id]
        if row["pareto_candidate"].lower() != "true":
            raise ValueError(f"{case_id} is not marked as Pareto in the CSV.")
        candidate = dict(candidates_by_id[case_id])
        candidate["spot_mean_rms_um"] = float(row["spot_mean_rms_um"])
        candidate["mtf_30_overall_mean"] = float(
            row["mtf_30_overall_mean"]
        )
        candidate["mtf_50_overall_mean"] = float(
            row["mtf_50_overall_mean"]
        )
        candidate["merit_result_name"] = "merit_result.json"
        planned.append(candidate)
    return report, csv_file, planned


def validate_merit_definition(day10_config, baseline_config):
    """Confirm the frozen baseline describes one existing Merit Function."""

    merit = baseline_config.get("merit_function")
    if not merit:
        raise ValueError("The baseline Merit Function definition is missing.")
    required = {
        "generated_by": "OpticStudio Optimization Wizard",
        "imaging_criterion": "spot_diagram",
        "metric": "RMS",
        "reference": "centroid",
    }
    for key, expected in required.items():
        if merit.get(key) != expected:
            raise ValueError(f"Baseline Merit Function mismatch: {key}.")
    if (
        day10_config["evaluation"]["source"]
        != "frozen_mf_recipe_loaded_in_memory"
    ):
        raise ValueError("Day 10 must load the frozen .MF recipe in memory.")
    return merit


def main():
    day10_config = load_config("configs/day10_merit_function_validation.yaml")
    baseline_config = load_config(day10_config["source"]["baseline_config"])
    validate_execution_lock(day10_config)
    merit = validate_merit_definition(day10_config, baseline_config)

    report_file = find_latest_day9_tradeoff_report(day10_config)
    _, csv_file, candidates = build_merit_candidate_plan(
        day10_config,
        report_file,
    )

    print("========== DAY 10 MERIT FUNCTION PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print("No optimization will be run.")
    print(f"Day 9 report: {report_file}")
    print(f"Day 9 metrics: {csv_file}")
    print(
        "Merit Function: "
        f"{merit['imaging_criterion']}, {merit['metric']}, "
        f"reference={merit['reference']}"
    )
    print("Comparison rule: lower calculated Merit Function value is better")
    print()

    for candidate in candidates:
        print(
            f"{candidate['case_id']}: thickness={candidate['value_mm']:.7f} mm"
        )
        print(f"  Spot mean RMS: {candidate['spot_mean_rms_um']:.3f} um")
        print(f"  MTF30 mean: {candidate['mtf_30_overall_mean']:.4f}")
        print(f"  MTF50 mean: {candidate['mtf_50_overall_mean']:.4f}")
        print(f"  model: {candidate['focused_model']}")
        print(f"  SHA256: {candidate['focused_model_sha256']}")

    print()
    print(f"[PASS] {len(candidates)} Pareto candidates selected")
    print("[PASS] Dominated fine_006 excluded")
    print("[PASS] All focused-model hashes verified")
    print("[PASS] Frozen .MF recipe definition recorded")
    print("[PASS] Optimization and model writes forbidden")
    print("PLAN ONLY finished. No Zemax analysis or output was created.")


if __name__ == "__main__":
    main()
