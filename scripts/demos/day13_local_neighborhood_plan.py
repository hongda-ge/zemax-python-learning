"""Day 13 step 1: audit the read-only local-neighborhood plan."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep Day 13 planning independent of Zemax and new calculations."""

    execution = config["execution"]
    metrics = config["metrics"]
    guardrails = config["guardrails"]
    locked_false = {
        "generic execution": execution["enabled"],
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "new optical calculation": execution["allow_new_optical_calculation"],
        "hidden weighted score": metrics["hidden_weighted_score_allowed"],
        "unique engineering winner": guardrails[
            "unique_engineering_winner_allowed"
        ],
    }
    enabled = [name for name, value in locked_false.items() if value is not False]
    if enabled:
        raise ValueError("Day 13 plan lock failed: " + ", ".join(enabled))

    if not isinstance(execution["allow_neighborhood_evaluation"], bool):
        raise ValueError("The neighborhood evaluation switch must be Boolean.")


def find_latest_file(root, pattern, description):
    """Return the newest file matching one reviewed output pattern."""

    matches = list((PROJECT_ROOT / root).glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No {description} was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def load_day8_batch(config):
    """Require the successful, ordered nine-point Day 8 scan."""

    source = config["source"]
    report_file = find_latest_file(
        source["day8_output_root"],
        "fine_scan_*/" + source["day8_batch_report_name"],
        "Day 8 batch report",
    )
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("task") != source["day8_expected_task"]:
        raise ValueError("Unexpected Day 8 report type.")
    if report.get("status") != "success":
        raise ValueError("The Day 8 batch was not successful.")
    rows = report.get("rows", [])
    expected_count = source["day8_expected_case_count"]
    if len(rows) != expected_count or report.get("success_count") != expected_count:
        raise ValueError("Day 8 does not contain nine successful cases.")
    values = [float(row["value_mm"]) for row in rows]
    if values != sorted(values):
        raise ValueError("Day 8 thickness values are not increasing.")
    if any(row.get("status") != "success" for row in rows):
        raise ValueError("At least one Day 8 case was unsuccessful.")
    return report_file, report, rows


def load_day11_candidates(config):
    """Require the three reviewed candidate identities from Day 11."""

    source = config["source"]
    report_file = find_latest_file(
        source["day11_output_root"],
        "scenario_evaluation_*/" + source["day11_report_name"],
        "Day 11 decision report",
    )
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("task") != source["day11_expected_task"]:
        raise ValueError("Unexpected Day 11 report type.")
    if report.get("status") != "success" or report.get("teaching_only") is not True:
        raise ValueError("The Day 11 teaching decision was not successful.")
    if report.get("unique_engineering_winner") is not None:
        raise ValueError("Day 11 unexpectedly declared an engineering winner.")
    actual_ids = [row["case_id"] for row in report.get("candidates", [])]
    if actual_ids != source["expected_candidate_ids"]:
        raise ValueError("The reviewed candidate identities changed.")
    return report_file, actual_ids


def build_neighborhoods(config, rows, candidate_ids):
    """Select left, center and right Day 8 samples for every candidate."""

    by_id = {row["case_id"]: row for row in rows}
    row_order = [row["case_id"] for row in rows]
    half_width = float(config["neighborhood"]["half_width_mm"])
    expected_points = config["neighborhood"]["expected_points_per_candidate"]
    neighborhoods = []
    for candidate_id in candidate_ids:
        center_index = row_order.index(candidate_id)
        if center_index == 0 or center_index == len(rows) - 1:
            raise ValueError(f"{candidate_id} has no complete neighborhood.")
        point_ids = row_order[center_index - 1 : center_index + 2]
        points = [by_id[case_id] for case_id in point_ids]
        if len(points) != expected_points:
            raise ValueError(f"{candidate_id} neighborhood size is incorrect.")
        center_value = float(by_id[candidate_id]["value_mm"])
        offsets = [float(row["value_mm"]) - center_value for row in points]
        expected_offsets = [-half_width, 0.0, half_width]
        if any(
            abs(actual - expected) > 1e-9
            for actual, expected in zip(offsets, expected_offsets)
        ):
            raise ValueError(f"{candidate_id} neighbor spacing changed.")
        neighborhoods.append(
            {
                "candidate_id": candidate_id,
                "center_value_mm": center_value,
                "point_ids": point_ids,
                "points": points,
            }
        )
    return neighborhoods


def validate_individual_safety(config, batch_file, neighborhoods):
    """Audit the original Day 8 case reports used by all neighborhoods."""

    if not config["guardrails"]["require_individual_case_safety_checks"]:
        return []
    required_ids = sorted(
        {case_id for group in neighborhoods for case_id in group["point_ids"]}
    )
    batch_dir = batch_file.parent
    reports = list(batch_dir.glob("fine_*_*/result.json"))
    by_case = {}
    for report_file in reports:
        report = json.loads(report_file.read_text(encoding="utf-8"))
        case_id = report.get("case", {}).get("case_id")
        if case_id:
            by_case[case_id] = (report_file, report)

    for case_id in required_ids:
        if case_id not in by_case:
            raise FileNotFoundError(f"No individual report for {case_id}.")
        _, report = by_case[case_id]
        checks = {
            "success": report.get("status") == "success",
            "source unchanged": report.get("source_unchanged") is True,
            "working unchanged": report.get("working_copy_unchanged") is True,
            "connection closed": report.get("connection_closed") is True,
            "three fields": report.get("spot_metrics", {}).get("field_count") == 3,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(f"{case_id} failed: " + ", ".join(failed))
    return required_ids


def main():
    config = load_config("configs/day13_local_neighborhood_robustness.yaml")
    validate_execution_lock(config)
    day8_file, _, rows = load_day8_batch(config)
    day11_file, candidate_ids = load_day11_candidates(config)
    neighborhoods = build_neighborhoods(config, rows, candidate_ids)
    audited_ids = validate_individual_safety(config, day8_file, neighborhoods)

    print("========== DAY 13 LOCAL NEIGHBORHOOD PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print("No new optical metric will be calculated.")
    print("The existing Day 8 Quick-Focused Spot results will be reused.")
    print(f"Day 8 batch: {day8_file}")
    print(f"Day 11 candidates: {day11_file}")
    print()
    print("Teaching assembly error: +/-0.1 mm on Surface 2 air gap")
    print("Quick Focus is treated as an available compensator.")
    print()
    for group in neighborhoods:
        print(
            f"{group['candidate_id']} center="
            f"{group['center_value_mm']:.7f} mm: "
            + " -> ".join(group["point_ids"])
        )

    print()
    print("Planned descriptive outputs:")
    print("  neighborhood mean of equal-field mean RMS")
    print("  worst sampled equal-field mean RMS")
    print("  worst individual field RMS")
    print("  required focus-compensation span")
    print()
    print("[PASS] Nine-point Day 8 batch verified")
    print("[PASS] Three Day 11 candidate identities verified")
    print(f"[PASS] Individual safety reports audited: {', '.join(audited_ids)}")
    print("[PASS] Three complete and equally spaced neighborhoods built")
    print("[PASS] ZOS-API and new optical calculations locked")
    print("[PASS] Hidden weighted score and engineering winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
