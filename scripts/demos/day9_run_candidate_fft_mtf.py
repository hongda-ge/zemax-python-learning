"""Day 9 step 3: run FFT MTF for the four reviewed plateau candidates."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day9_fft_mtf_plan import (  # noqa: E402
    build_candidate_plan,
    find_latest_day8_report,
    validate_analysis_settings,
    validate_execution_lock,
)
from scripts.demos.day9_validate_baseline_fft_mtf import (  # noqa: E402
    execute_fft_mtf_candidate,
)


def validate_candidate_authorization(day9_config):
    """Authorize only the reviewed four-candidate Day 9 batch."""

    execution = day9_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 9 execution must remain disabled.")
    if execution["allow_reviewed_candidate_execution"] is not True:
        raise ValueError("The reviewed Day 9 candidate batch is not approved.")


def find_latest_baseline_report(day9_config):
    """Find the newest successful single-candidate FFT MTF report."""

    root = PROJECT_ROOT / day9_config["output"]["root"]
    candidates = list(
        root.glob("baseline_check_*/fine_005/mtf_result.json")
    )
    if not candidates:
        raise FileNotFoundError(
            "Run day9_validate_baseline_fft_mtf.py before the candidate batch."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_baseline_report(report_file):
    """Require successful parsing plus all model and connection safeguards."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "task": report.get("task") == "day9_baseline_fft_mtf_validation",
        "status": report.get("status") == "success",
        "three fields": report.get("mtf_metrics", {}).get("field_count") == 3,
        "input unchanged": report.get("input_model_unchanged") is True,
        "working copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            "Baseline FFT MTF report did not approve the batch: "
            + ", ".join(failed)
        )
    return report


def flatten_result(result):
    """Create one comparison row while preserving T/S and each field."""

    candidate = result["candidate"]
    row = {
        "case_id": candidate["case_id"],
        "value_mm": candidate["value_mm"],
        "delta_mm": candidate["delta_mm"],
        "is_baseline": candidate["is_baseline"],
    }
    frequency_samples = {}

    for field in result["mtf_metrics"]["fields"]:
        field_tag = int(round(field["field_y_degree"]))
        for evaluation in field["evaluations"]:
            frequency = int(
                round(evaluation["target_frequency_cyc_per_mm"])
            )
            prefix = f"field_{field_tag}_mtf_{frequency}"
            row[f"{prefix}_tangential"] = evaluation["tangential_mtf"]
            row[f"{prefix}_sagittal"] = evaluation["sagittal_mtf"]
            row[f"{prefix}_mean"] = evaluation["mean_mtf"]
            row[f"{prefix}_direction_gap"] = evaluation["direction_gap"]
            frequency_samples.setdefault(frequency, []).append(evaluation)

    for frequency, evaluations in frequency_samples.items():
        all_directions = []
        for evaluation in evaluations:
            all_directions.extend(
                [
                    evaluation["tangential_mtf"],
                    evaluation["sagittal_mtf"],
                ]
            )
        row[f"mtf_{frequency}_overall_mean"] = sum(all_directions) / len(
            all_directions
        )
        row[f"mtf_{frequency}_minimum"] = min(all_directions)
        row[f"mtf_{frequency}_maximum_direction_gap"] = max(
            evaluation["direction_gap"] for evaluation in evaluations
        )

    return row


def write_batch_summary(batch_dir, batch_id, baseline_report_file, results):
    """Write nested JSON plus one flat candidate-comparison CSV."""

    rows = [flatten_result(result) for result in results]
    summary = {
        "task": "day9_candidate_fft_mtf",
        "batch_id": batch_id,
        "time_local": datetime.now().astimezone().isoformat(),
        "status": "success",
        "candidate_count": len(results),
        "approved_by_baseline_report": str(baseline_report_file),
        "rows": rows,
    }
    summary_json = batch_dir / "batch_summary.json"
    summary_csv = batch_dir / "candidate_mtf_comparison.csv"
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with summary_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return summary, summary_json, summary_csv


def main():
    day9_config = load_config("configs/day9_fft_mtf_validation.yaml")
    baseline_config = load_config(day9_config["source"]["baseline_config"])
    validate_execution_lock(day9_config)
    validate_candidate_authorization(day9_config)
    validate_analysis_settings(day9_config, baseline_config)

    baseline_report_file = find_latest_baseline_report(day9_config)
    validate_baseline_report(baseline_report_file)
    day8_report_file = find_latest_day8_report(day9_config)
    _, candidates = build_candidate_plan(day9_config, day8_report_file)
    batch_id = datetime.now().strftime("candidate_batch_%Y%m%d_%H%M%S")
    batch_dir = PROJECT_ROOT / day9_config["output"]["root"] / batch_id

    print("========== DAY 9 REVIEWED CANDIDATE FFT MTF ==========")
    print(f"Approved by baseline report: {baseline_report_file}")
    print(f"Batch directory: {batch_dir}")
    print("Candidates run sequentially and stop on the first unexpected failure.")

    results = []
    for candidate in candidates:
        print()
        print(
            f"Running {candidate['case_id']} "
            f"({candidate['value_mm']:.7f} mm)..."
        )
        case_dir = batch_dir / candidate["case_id"]
        result, _ = execute_fft_mtf_candidate(
            day9_config,
            baseline_config,
            candidate,
            case_dir,
            task_name="day9_candidate_fft_mtf",
        )
        results.append(result)
        row = flatten_result(result)
        print(
            f"[PASS] MTF 30 overall mean/min: "
            f"{row['mtf_30_overall_mean']:.4f} / "
            f"{row['mtf_30_minimum']:.4f}"
        )
        print(
            f"[PASS] MTF 50 overall mean/min: "
            f"{row['mtf_50_overall_mean']:.4f} / "
            f"{row['mtf_50_minimum']:.4f}"
        )
        print("[PASS] Input/working hashes unchanged; connection closed")

    summary, summary_json, summary_csv = write_batch_summary(
        batch_dir,
        batch_id,
        baseline_report_file,
        results,
    )

    print()
    print("========== DAY 9 CANDIDATE SUMMARY ==========")
    for row in summary["rows"]:
        print(
            f"{row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"MTF30 mean/min={row['mtf_30_overall_mean']:.4f}/"
            f"{row['mtf_30_minimum']:.4f}, "
            f"MTF50 mean/min={row['mtf_50_overall_mean']:.4f}/"
            f"{row['mtf_50_minimum']:.4f}"
        )
    print(f"[PASS] Successful candidates: {summary['candidate_count']}")
    print(f"[PASS] Batch JSON: {summary_json}")
    print(f"[PASS] Comparison CSV: {summary_csv}")
    print("[PASS] Day 9 candidate FFT MTF batch completed.")


if __name__ == "__main__":
    main()
