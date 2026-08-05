"""Day 13 step 2: compare three candidate neighborhoods without Zemax."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day13_local_neighborhood_plan import (  # noqa: E402
    build_neighborhoods,
    load_day11_candidates,
    load_day8_batch,
    validate_execution_lock,
    validate_individual_safety,
)


def require_reviewed_evaluation(config):
    """Permit only the reviewed read-only neighborhood calculation."""

    execution = config["execution"]
    if execution["allow_neighborhood_evaluation"] is not True:
        raise ValueError("Day 13 neighborhood evaluation is not approved.")
    if execution["allow_zosapi_connection"] is not False:
        raise ValueError("Day 13 must not connect to ZOS-API.")
    if execution["allow_new_optical_calculation"] is not False:
        raise ValueError("Day 13 must not calculate new optical metrics.")


def enrich_point(row):
    """Add transparent equal-field descriptors to one Day 8 sample."""

    point = dict(row)
    fields = [
        float(row["rms_0deg_um"]),
        float(row["rms_14deg_um"]),
        float(row["rms_20deg_um"]),
    ]
    point["equal_field_mean_rms_um"] = sum(fields) / len(fields)
    point["worst_field_rms_um"] = max(fields)
    return point


def calculate_neighborhood(group):
    """Calculate four independent descriptors for one candidate neighborhood."""

    points = [enrich_point(row) for row in group["points"]]
    center = points[1]
    mean_values = [point["equal_field_mean_rms_um"] for point in points]
    worst_fields = [point["worst_field_rms_um"] for point in points]
    focus_values = [float(point["focus_shift_mm"]) for point in points]
    focus_deltas = [
        abs(value - float(center["focus_shift_mm"])) for value in focus_values
    ]
    return {
        "candidate_id": group["candidate_id"],
        "center_value_mm": group["center_value_mm"],
        "neighbor_case_ids": group["point_ids"],
        "points": points,
        "center_equal_field_mean_rms_um": center["equal_field_mean_rms_um"],
        "neighborhood_average_mean_rms_um": sum(mean_values) / len(mean_values),
        "worst_sample_mean_rms_um": max(mean_values),
        "worst_individual_field_rms_um": max(worst_fields),
        "focus_compensation_span_mm": max(focus_values) - min(focus_values),
        "maximum_focus_change_from_center_mm": max(focus_deltas),
    }


def metric_rankings(rows):
    """Rank each declared metric separately; do not create a global score."""

    metric_names = [
        "neighborhood_average_mean_rms_um",
        "worst_sample_mean_rms_um",
        "worst_individual_field_rms_um",
        "focus_compensation_span_mm",
        "maximum_focus_change_from_center_mm",
    ]
    return {
        metric: [
            row["candidate_id"]
            for row in sorted(
                rows,
                key=lambda item: (float(item[metric]), item["candidate_id"]),
            )
        ]
        for metric in metric_names
    }


def write_csv(output_file, rows):
    """Write one compact comparison row per nominal candidate."""

    columns = [
        "candidate_id",
        "center_value_mm",
        "neighbor_case_ids",
        "center_equal_field_mean_rms_um",
        "neighborhood_average_mean_rms_um",
        "worst_sample_mean_rms_um",
        "worst_individual_field_rms_um",
        "focus_compensation_span_mm",
        "maximum_focus_change_from_center_mm",
    ]
    csv_rows = []
    for row in rows:
        csv_row = {key: row[key] for key in columns}
        csv_row["neighbor_case_ids"] = ";".join(row["neighbor_case_ids"])
        csv_rows.append(csv_row)
    with output_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(csv_rows)


def main():
    config = load_config("configs/day13_local_neighborhood_robustness.yaml")
    validate_execution_lock(config)
    require_reviewed_evaluation(config)
    day8_file, day8_report, source_rows = load_day8_batch(config)
    day11_file, candidate_ids = load_day11_candidates(config)
    neighborhoods = build_neighborhoods(config, source_rows, candidate_ids)
    audited_ids = validate_individual_safety(config, day8_file, neighborhoods)
    rows = [calculate_neighborhood(group) for group in neighborhoods]
    rankings = metric_rankings(rows)

    run_id = datetime.now().strftime("neighborhood_evaluation_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    csv_file = run_dir / "candidate_neighborhood_metrics.csv"
    report_file = run_dir / "local_neighborhood_report.json"
    write_csv(csv_file, rows)

    report = {
        "task": "day13_local_neighborhood_robustness",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day8_batch": str(day8_file),
        "source_day8_batch_id": day8_report["batch_id"],
        "source_day11_report": str(day11_file),
        "teaching_only": True,
        "error_model": {
            "parameter": "Surface 2 air-gap thickness",
            "offsets_mm": config["neighborhood"]["offsets_mm"],
            "quick_focus_compensator_available": True,
            "probability_distribution_assumed": False,
        },
        "zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "hidden_weighted_score_used": False,
        "unique_engineering_winner": None,
        "audited_day8_case_ids": audited_ids,
        "candidate_metrics": rows,
        "separate_metric_rankings": rankings,
        "spot_robustness_leader": rankings[
            "neighborhood_average_mean_rms_um"
        ][0],
        "minimum_focus_span_candidate": rankings[
            "focus_compensation_span_mm"
        ][0],
        "warning": (
            "This is a three-point teaching neighborhood with Quick Focus, "
            "not a fixed-image-plane tolerance or Monte Carlo analysis."
        ),
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========== DAY 13 LOCAL NEIGHBORHOOD RESULTS ==========")
    print("No ZOS-API connection was created.")
    print("No new optical metric was calculated.")
    print("Each +/-0.1 mm sample reuses a Day 8 Quick-Focused result.")
    print()
    for row in rows:
        print(
            f"{row['candidate_id']}: neighborhood mean="
            f"{row['neighborhood_average_mean_rms_um']:.3f} um, "
            f"worst sample mean={row['worst_sample_mean_rms_um']:.3f} um, "
            f"worst field={row['worst_individual_field_rms_um']:.3f} um, "
            f"focus span={row['focus_compensation_span_mm']:.6f} mm"
        )

    print()
    print("Separate metric leaders:")
    for metric, ranking in rankings.items():
        print(f"  {metric}: {' -> '.join(ranking)}")
    print()
    print(
        "[RESULT] Spot-neighborhood leader: "
        f"{report['spot_robustness_leader']}"
    )
    print(
        "[RESULT] Minimum focus-compensation span: "
        f"{report['minimum_focus_span_candidate']}"
    )
    print("[RESULT] Unique engineering winner: NONE")
    print("[PASS] Five individual Day 8 safety reports remained valid")
    print("[PASS] No hidden weighted score was used")
    print(f"[PASS] Comparison CSV: {csv_file}")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
