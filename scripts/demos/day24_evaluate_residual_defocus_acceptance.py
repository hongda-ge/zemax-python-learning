"""Day 24 step 2: evaluate measured residual-defocus acceptance offline."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day24_residual_defocus_acceptance_plan import (  # noqa: E402
    find_latest_day23_report,
    validate_day23_report,
    validate_guardrails,
    validate_scenarios,
)


CHECKS = (
    ("spot_mean", "spot_mean_rms_um", "spot_mean_rms_um_max", "maximum"),
    ("spot_worst", "spot_worst_rms_um", "spot_worst_rms_um_max", "maximum"),
    ("mtf30_minimum", "mtf30_minimum", "mtf30_minimum_min", "minimum"),
    ("mtf50_minimum", "mtf50_minimum", "mtf50_minimum_min", "minimum"),
)


def require_evaluation_authorization(config):
    """Allow only the reviewed offline acceptance evaluation."""

    execution = config["execution"]
    if execution.get("allow_acceptance_evaluation") is not True:
        raise ValueError("Day 24 acceptance evaluation is not approved.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 24 forbidden action enabled: " + ", ".join(enabled))


def evaluate_check(value, limit, direction):
    """Return a transparent Boolean result and signed margin."""

    if direction == "maximum":
        return value <= limit, limit - value
    if direction == "minimum":
        return value >= limit, value - limit
    raise ValueError(f"Unknown acceptance direction: {direction}")


def evaluate_rows(rows, scenarios):
    """Evaluate every required metric independently for every measured case."""

    details = []
    summaries = []
    for scenario in scenarios:
        limits = scenario["limits"]
        passed_cases = []
        failed_cases = []
        for row in rows:
            result = {
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "case_id": row["case_id"],
                "offset_mm": float(row["offset_mm"]),
                "mtf30_mean_diagnostic": float(row["mtf30_mean"]),
                "mtf50_mean_diagnostic": float(row["mtf50_mean"]),
            }
            failed_metrics = []
            for label, metric, limit_key, direction in CHECKS:
                value = float(row[metric])
                limit = float(limits[limit_key])
                passed, margin = evaluate_check(value, limit, direction)
                result[f"{label}_value"] = value
                result[f"{label}_limit"] = limit
                result[f"{label}_margin"] = margin
                result[f"{label}_pass"] = passed
                if not passed:
                    failed_metrics.append(label)
            result["all_required_metrics_pass"] = not failed_metrics
            result["failed_metrics"] = ";".join(failed_metrics)
            details.append(result)
            if result["all_required_metrics_pass"]:
                passed_cases.append(row["case_id"])
            else:
                failed_cases.append(row["case_id"])
        summaries.append(
            {
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "passed_count": len(passed_cases),
                "measured_count": len(rows),
                "passed_case_ids": passed_cases,
                "failed_case_ids": failed_cases,
                "passed_offsets_mm": [
                    row["offset_mm"] for row in rows if row["case_id"] in passed_cases
                ],
            }
        )
    return details, summaries


def write_csv(path, rows):
    """Write dictionaries, serializing lists for spreadsheet readability."""

    serializable = []
    for row in rows:
        item = {}
        for key, value in row.items():
            item[key] = ";".join(map(str, value)) if isinstance(value, list) else value
        serializable.append(item)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(serializable[0].keys()))
        writer.writeheader()
        writer.writerows(serializable)


def create_figure(path, rows, scenarios, details):
    """Plot the measured pass matrix without implying continuous tolerance."""

    indexed = {
        (item["scenario_id"], item["case_id"]): item["all_required_metrics_pass"]
        for item in details
    }
    matrix = [
        [1 if indexed[(scenario["id"], row["case_id"])] else 0 for row in rows]
        for scenario in scenarios
    ]
    figure, axis = plt.subplots(figsize=(10.0, 3.8))
    image = axis.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    del image
    axis.set_xticks(range(len(rows)))
    axis.set_xticklabels([f"{row['offset_mm']:+.2f}" for row in rows])
    axis.set_yticks(range(len(scenarios)))
    axis.set_yticklabels([scenario["id"] for scenario in scenarios])
    axis.set_xlabel("Measured residual offset (mm)")
    axis.set_title("Day 24 measured-point acceptance matrix")
    for row_index, scenario in enumerate(scenarios):
        for column_index, row in enumerate(rows):
            passed = indexed[(scenario["id"], row["case_id"])]
            axis.text(
                column_index,
                row_index,
                "PASS" if passed else "FAIL",
                ha="center",
                va="center",
                color="black",
                fontsize=9,
            )
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def print_failure_detail(detail):
    """Explain exactly which independent metrics rejected one case."""

    failed = detail["failed_metrics"].split(";") if detail["failed_metrics"] else []
    if not failed:
        return "all four required metrics passed"
    return "failed: " + ", ".join(failed)


def main():
    config = load_config("configs/day24_residual_defocus_acceptance.yaml")
    require_evaluation_authorization(config)
    validate_guardrails(config)
    report_file = find_latest_day23_report(config)
    day23_report, rows = validate_day23_report(config, report_file)
    scenarios = validate_scenarios(config)
    details, summaries = evaluate_rows(rows, scenarios)

    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("acceptance_evaluation_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    detail_file = output_dir / "residual_defocus_acceptance_details.csv"
    summary_file = output_dir / "residual_defocus_acceptance_summary.csv"
    figure_file = output_dir / "day24_acceptance_matrix.png"
    report_output = output_dir / "residual_defocus_acceptance_report.json"
    write_csv(detail_file, details)
    write_csv(summary_file, summaries)
    create_figure(figure_file, rows, scenarios, details)

    report = {
        "task": "day24_residual_defocus_acceptance_evaluation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day23_report": str(report_file),
        "source_day23_sha256": config["source"]["expected_report_sha256"],
        "source_model_sha256": day23_report["source_sha256"],
        "teaching_thresholds_only": True,
        "combination_rule": "all_required_metrics_must_pass",
        "required_metrics": list(config["acceptance"]["required_metrics"]),
        "diagnostic_only_metrics": config["acceptance"]["diagnostic_only_metrics"],
        "details": details,
        "scenario_summaries": summaries,
        "measured_points_only": True,
        "interpolation_used": False,
        "extrapolation_used": False,
        "curve_fit_used": False,
        "hidden_weighted_score_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "unique_engineering_winner": None,
    }
    report_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("========== DAY 24 OFFLINE ACCEPTANCE RESULTS ==========")
    print("No ZOS-API connection or new optical calculation was used.")
    print("All four required metrics must pass independently.")
    print("Thresholds are teaching examples, not detector requirements.")
    for scenario, summary in zip(scenarios, summaries):
        print(f"\n{scenario['id']} ({scenario['name']}):")
        scenario_details = [
            item for item in details if item["scenario_id"] == scenario["id"]
        ]
        for detail in scenario_details:
            print(
                f"  {detail['case_id']} ({detail['offset_mm']:+.3f} mm): "
                f"{'PASS' if detail['all_required_metrics_pass'] else 'FAIL'}; "
                f"{print_failure_detail(detail)}"
            )
        print(
            f"  [RESULT] {summary['passed_count']}/{summary['measured_count']} "
            f"measured points passed: {summary['passed_case_ids']}"
        )
    boundary = next(
        item
        for item in details
        if item["scenario_id"] == "balanced_acceptance"
        and item["case_id"] == "defocus_003"
    )
    print("\n[TEACHING] defocus_003 displayed MTF50 min as 0.0500, but")
    print(
        "[TEACHING] full precision "
        f"{boundary['mtf50_minimum_value']:.6f} is below "
        f"{boundary['mtf50_minimum_limit']:.6f}."
    )
    print("[RESULT] Passing measured points do not define a continuous tolerance band")
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] No interpolation, hidden score or engineering recommendation")
    print(f"[PASS] Detail CSV: {detail_file}")
    print(f"[PASS] Summary CSV: {summary_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_output}")


if __name__ == "__main__":
    main()
