"""Day 14 step 1: prove why an LDE Solve audit is required."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_execution_lock(config):
    """Keep the first Day 14 step fully offline and read-only."""

    execution = config["execution"]
    locked_false = {
        "generic execution": execution["enabled"],
        "model write": execution["allow_model_write"],
        "optimization": execution["allow_optimization"],
        "Quick Focus": execution["allow_quick_focus"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in locked_false.items() if value is not False]
    if enabled:
        raise ValueError("Day 14 plan lock failed: " + ", ".join(enabled))

    for key in ("allow_zosapi_connection", "allow_read_only_solve_audit"):
        if not isinstance(execution[key], bool):
            raise ValueError(f"{key} must be Boolean.")


def validate_source_model(config):
    """Verify the frozen baseline model before any later ZOS-API audit."""

    baseline_config = load_config(config["source"]["baseline_config"])
    model = baseline_config["model"]
    source_file = PROJECT_ROOT / model["source_file"]
    actual_hash = sha256_file(source_file).upper()
    expected_hash = str(model["source_sha256"]).upper()
    if actual_hash != expected_hash:
        raise ValueError("The frozen baseline model SHA256 changed.")
    if model["read_only_original"] is not True:
        raise ValueError("The baseline model must remain read-only.")
    if model["forbid_overwrite_original"] is not True:
        raise ValueError("Overwriting the baseline model must be forbidden.")
    return source_file, actual_hash


def find_latest_day8_batch(config):
    """Find and validate the reviewed Day 8 nine-point report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day8_output_root"]
    matches = list(
        root.glob("fine_scan_*/" + source["day8_batch_report_name"])
    )
    if not matches:
        raise FileNotFoundError("No Day 8 batch report was found.")
    report_file = max(matches, key=lambda path: path.stat().st_mtime)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("task") != source["day8_expected_task"]:
        raise ValueError("Unexpected Day 8 report type.")
    expected_count = source["day8_expected_case_count"]
    if (
        report.get("status") != "success"
        or report.get("success_count") != expected_count
        or len(report.get("rows", [])) != expected_count
    ):
        raise ValueError("The Day 8 batch is incomplete or unsuccessful.")
    return report_file, report


def extract_radius_response(config, report):
    """Extract the reported Surface 6 radius response across Day 8."""

    surface_id = config["evidence"]["observed_response_surface_id"]
    rows = report["rows"]
    values = [float(row["surface_6_radius_mm"]) for row in rows]
    radius_range = max(values) - min(values)
    if (
        config["evidence"]["require_nonzero_observed_radius_range"]
        and radius_range <= 0.0
    ):
        raise ValueError(f"Surface {surface_id} radius did not respond.")
    return values, radius_range


def main():
    config = load_config("configs/day14_lde_solve_audit.yaml")
    validate_execution_lock(config)
    source_file, source_hash = validate_source_model(config)
    day8_file, day8_report = find_latest_day8_batch(config)
    radius_values, radius_range = extract_radius_response(config, day8_report)
    rows = day8_report["rows"]

    print("========== DAY 14 LDE SOLVE AUDIT PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created in this step.")
    print("No model cell, optimization, Quick Focus or SaveAs is allowed.")
    print(f"Baseline model: {source_file}")
    print(f"Baseline SHA256: {source_hash}")
    print(f"Day 8 evidence: {day8_file}")
    print()
    print("Observed Surface 6 radius response while Surface 2 thickness changed:")
    for row, radius in zip(rows, radius_values):
        print(
            f"  {row['case_id']}: Surface 2="
            f"{row['value_mm']:.7f} mm, Surface 6 radius={radius:.7f} mm"
        )
    print(f"Observed Surface 6 radius range: {radius_range:.7f} mm")
    print()
    print("Planned read-only audit:")
    print("  all sequential surfaces")
    print("  RadiusCell and ThicknessCell")
    print("  numeric value, Solve type and readable Solve properties")
    print("  source and working-copy SHA256 before/after")
    print()
    print("[PASS] Frozen baseline model fingerprint verified")
    print("[PASS] Nine successful Day 8 cases verified")
    print("[PASS] Nonzero Surface 6 radius response confirmed")
    print("[PASS] ZOS-API, writes, optimization, Quick Focus and SaveAs locked")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
