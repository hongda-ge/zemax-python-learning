"""Day 8 step 3: execute the reviewed nine-point local Zemax scan."""

import json
import sys
from datetime import datetime
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
from scripts.demos.day7_five_case_sweep import (  # noqa: E402
    FocusRangeRejected,
    execute_one_case,
    load_case_report,
    write_batch_summary,
)
from scripts.demos.day8_local_fine_scan_plan import (  # noqa: E402
    build_fine_case_plan,
    validate_execution_lock,
    validate_local_values,
    validate_parameter_identity,
)


def validate_batch_authorization(scan_config):
    """Allow only this reviewed batch while generic automation stays locked."""

    execution = scan_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic automatic execution must remain disabled.")
    if execution["allow_reviewed_nine_case_execution"] is not True:
        raise ValueError("The reviewed Day 8 nine-case batch is not approved.")


def find_latest_center_report(scan_config):
    """Find the newest successful center reproducibility report."""

    output_root = PROJECT_ROOT / scan_config["output"]["root"]
    candidates = list(
        output_root.glob("center_check_*/fine_005_*/result.json")
    )
    if not candidates:
        raise FileNotFoundError(
            "Run day8_validate_center_case.py before the nine-case batch."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_center_report(report_file):
    """Require reproducibility and all three file/connection safety checks."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    checks = {
        "center status": report.get("status") == "success",
        "Day 7 reproduction": report.get("day7_reproducibility", {}).get(
            "status"
        )
        == "pass",
        "source unchanged": report.get("source_unchanged") is True,
        "working copy unchanged": report.get("working_copy_unchanged") is True,
        "connection closed": report.get("connection_closed") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            "Center report did not approve the batch: " + ", ".join(failed)
        )
    return report


def run_cases(baseline_config, cases, batch_dir):
    """Run cases sequentially and retain safe engineering rejections."""

    results = []
    for case in cases:
        print()
        print(
            f"Running {case['case_id']} "
            f"({case['value_mm']:.7f} mm)..."
        )
        try:
            result = execute_one_case(
                baseline_config,
                case,
                batch_dir,
                task_name="day8_local_fine_scan",
            )
        except FocusRangeRejected:
            result = load_case_report(batch_dir, case)
            safety_ok = (
                result.get("source_unchanged") is True
                and result.get("working_copy_unchanged") is True
                and result.get("connection_closed") is True
            )
            if not safety_ok:
                raise RuntimeError(
                    f"{case['case_id']} rejection failed its safety audit."
                )
            results.append(result)
            print(
                f"[REJECTED] {case['case_id']}: "
                f"{result['error']['message']}"
            )
            continue

        results.append(result)
        print(
            f"[PASS] Focus shift: "
            f"{result['focus']['focus_shift_mm']:+.7f} mm"
        )
        for field in result["spot_metrics"]["fields"]:
            print(
                f"  Field {field['field_y_degree']:.1f} deg RMS: "
                f"{field['rms_radius_um']:.3f} um"
            )

    return results


def main():
    scan_config = load_config("configs/day8_local_fine_scan.yaml")
    baseline_config = load_config(scan_config["source"]["baseline_config"])

    validate_execution_lock(scan_config)
    validate_batch_authorization(scan_config)
    validate_dry_run_mode(baseline_config)
    validate_parameter_identity(scan_config, baseline_config)
    validate_local_values(scan_config, baseline_config)
    validate_source_model(baseline_config["model"])
    validate_model_path_protection(baseline_config["model"])

    center_report_file = find_latest_center_report(scan_config)
    validate_center_report(center_report_file)
    cases = build_fine_case_plan(scan_config)
    batch_id = datetime.now().strftime("fine_scan_%Y%m%d_%H%M%S")
    batch_dir = PROJECT_ROOT / scan_config["output"]["root"] / batch_id

    print("========== DAY 8 REVIEWED NINE-CASE EXECUTION ==========")
    print("Cases run sequentially; unexpected failures stop the batch.")
    print(f"Approved by center report: {center_report_file}")
    print(f"Batch directory: {batch_dir}")
    print(
        f"Range: {cases[0]['value_mm']:.7f} to "
        f"{cases[-1]['value_mm']:.7f} mm"
    )

    results = run_cases(baseline_config, cases, batch_dir)
    summary, summary_json, summary_csv = write_batch_summary(
        batch_dir,
        batch_id,
        results,
        task_name="day8_local_fine_scan",
    )

    print()
    print("========== DAY 8 FINE-SCAN SUMMARY ==========")
    for row in summary["rows"]:
        if row["status"] == "rejected":
            print(f"{row['case_id']}: REJECTED by focus boundary")
            continue
        print(
            f"{row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"focus={row['focus_shift_mm']:+.4f} mm, "
            f"RMS=[{row['rms_0deg_um']:.3f}, "
            f"{row['rms_14deg_um']:.3f}, "
            f"{row['rms_20deg_um']:.3f}] um"
        )
    print(f"[PASS] Successful: {summary['success_count']}")
    print(f"[PASS] Constraint rejections: {summary['rejected_count']}")
    print(f"[PASS] Batch JSON: {summary_json}")
    print(f"[PASS] Sweep CSV: {summary_csv}")
    print("[PASS] Nine-case Day 8 scan completed with safety auditing.")


if __name__ == "__main__":
    main()
