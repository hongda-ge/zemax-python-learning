"""Day 23 step 1: audit and print the residual-defocus experiment plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_execution_lock(config):
    """Guarantee that planning cannot authorize Zemax or model actions."""

    execution = config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 23 execution must remain disabled.")
    flags = (
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_focus_surface_in_memory_write",
        "allow_standard_spot",
        "allow_fft_mtf",
        "allow_baseline_control",
        "allow_residual_cases",
        "allow_offline_analysis",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_recommendation",
    )
    invalid = [key for key in flags if not isinstance(execution[key], bool)]
    if invalid:
        raise ValueError("Day 23 execution flag is not Boolean: " + ", ".join(invalid))
    permanently_forbidden = (
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in permanently_forbidden if execution[key] is not False]
    if enabled:
        raise ValueError("Day 23 plan action is enabled: " + ", ".join(enabled))


def validate_input_model(config):
    """Verify the frozen Day 8 focused baseline model."""

    source = config["source"]
    model_file = PROJECT_ROOT / source["focused_model"]
    if not model_file.is_file():
        raise FileNotFoundError(f"Focused model not found: {model_file}")
    actual_hash = sha256_file(model_file).upper()
    expected_hash = source["focused_model_sha256"].upper()
    if actual_hash != expected_hash:
        raise ValueError("The frozen Day 23 input model changed.")
    return model_file, actual_hash


def validate_day8_evidence(config, model_file, model_hash):
    """Require the successful baseline row and immutable focused-model evidence."""

    source = config["source"]
    batch_file = PROJECT_ROOT / source["day8_batch_report"]
    case_file = PROJECT_ROOT / source["day8_case_report"]
    batch = json.loads(batch_file.read_text(encoding="utf-8"))
    case = json.loads(case_file.read_text(encoding="utf-8"))
    expected_case = source["expected_case_id"]
    rows = [row for row in batch.get("rows", []) if row.get("case_id") == expected_case]
    reference = config["reference_state"]
    checks = {
        "batch task": batch.get("task") == source["expected_day8_task"],
        "batch status": batch.get("status") == "success",
        "nine successes": batch.get("success_count") == 9,
        "one baseline row": len(rows) == 1 and rows[0].get("is_baseline") is True,
        "case task": case.get("task") == source["expected_day8_task"],
        "case status": case.get("status") == "success",
        "case identity": case.get("case", {}).get("case_id") == expected_case,
        "saved path": Path(case.get("saved_model", "")).resolve() == model_file.resolve(),
        "saved hash": case.get("saved_model_sha256", "").upper() == model_hash,
        "connection closed": case.get("connection_closed") is True,
        "source unchanged": case.get("source_unchanged") is True,
        "working copy unchanged": case.get("working_copy_unchanged") is True,
    }
    if len(rows) == 1:
        checks["surface 2 value"] = math.isclose(
            float(rows[0]["value_mm"]),
            float(reference["surface2_thickness_mm"]),
            abs_tol=1e-12,
        )
        checks["focused image distance"] = math.isclose(
            float(rows[0]["focused_image_distance_mm"]),
            float(reference["focused_image_distance_mm"]),
            abs_tol=1e-12,
        )
        checks["surface 6 radius"] = math.isclose(
            float(rows[0]["surface_6_radius_mm"]),
            float(reference["surface6_radius_mm"]),
            abs_tol=1e-12,
        )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 8 evidence failed: " + ", ".join(failed))
    return batch_file, case_file


def find_latest_day22_report(config):
    """Find the latest successful Day 22 error-budget report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day22_output_root"]
    matches = list(root.glob(f"**/{source['day22_report_name']}"))
    if not matches:
        raise FileNotFoundError("No Day 22 error-budget report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day22_evidence(config, report_file):
    """Verify provenance and the teaching allowances used to choose offsets."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    allowances = sorted(
        {
            float(item["symmetric_allowance_mm"])
            for item in report.get("teaching_error_sources", [])
        }
    )
    expected_components = sorted(
        float(value)
        for value in config["residual_defocus"]["relationship_to_day22"][
            "component_allowances_mm"
        ]
    )
    checks = {
        "task": report.get("task") == source["expected_day22_task"],
        "status": report.get("status") == "success",
        "component allowances": allowances == expected_components,
        "measured only": report.get("measured_cases_only") is True,
        "no RSS statistical claim": report.get("rss_statistical_claim") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated") is False,
        "no recommendation": report.get("engineering_recommendation") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 22 evidence failed: " + ", ".join(failed))


def validate_analysis_recipes(config):
    """Require the frozen Standard Spot and FFT MTF definitions."""

    baseline = load_config(config["source"]["baseline_config"])
    mismatches = []
    for analysis_name in ("standard_spot", "fft_mtf"):
        planned = config["analysis"][analysis_name]
        frozen = baseline["analysis"][analysis_name]
        for key, value in planned.items():
            if key not in frozen or frozen[key] != value:
                mismatches.append(f"{analysis_name}.{key}")
    if mismatches:
        raise ValueError("Day 23 analysis recipe mismatch: " + ", ".join(mismatches))


def build_cases(config):
    """Build seven symmetric residual-defocus cases including one control."""

    residual = config["residual_defocus"]
    offsets = [float(value) for value in residual["offsets_mm"]]
    baseline_offset = float(residual["baseline_offset_mm"])
    if len(offsets) != int(config["comparison"]["case_count"]):
        raise ValueError("Day 23 case count is incorrect.")
    if len(offsets) != len(set(offsets)) or offsets != sorted(offsets):
        raise ValueError("Day 23 offsets must be unique and ordered.")
    controls = [value for value in offsets if math.isclose(value, baseline_offset)]
    if len(controls) != int(config["comparison"]["baseline_control_count"]):
        raise ValueError("Day 23 requires exactly one baseline control.")
    if residual["symmetric_about_baseline"] is not True:
        raise ValueError("Day 23 offsets must be declared symmetric.")
    if any(-value not in offsets for value in offsets):
        raise ValueError("Day 23 offsets are not symmetric.")
    if residual["refocus_each_case"] is not False:
        raise ValueError("Day 23 must not refocus residual-defocus cases.")

    reference = float(config["reference_state"]["focused_image_distance_mm"])
    lower, upper = config["guardrails"]["approved_focus_surface_thickness_range_mm"]
    cases = []
    for index, offset in enumerate(offsets, start=1):
        target = reference + offset
        if not float(lower) <= target <= float(upper):
            raise ValueError("Day 23 target image distance is outside the approved range.")
        cases.append(
            {
                "case_id": f"defocus_{index:03d}",
                "offset_mm": offset,
                "target_image_distance_mm": target,
                "is_control": math.isclose(offset, baseline_offset, abs_tol=1e-12),
            }
        )
    return cases


def validate_guardrails(config):
    """Keep all interpretation and mutation boundaries explicit."""

    guardrails = config["guardrails"]
    required_true = (
        "run_sequentially",
        "stop_on_first_unexpected_failure",
        "use_independent_working_copy_per_case",
        "preserve_input_model_hash",
        "preserve_every_disk_working_copy_hash",
        "require_every_connection_closed",
        "require_day8_evidence_success",
        "require_day22_evidence_success",
        "forbid_quick_focus",
        "forbid_optimization",
        "forbid_save_as",
    )
    invalid = [key for key in required_true if guardrails[key] is not True]
    comparison = config["comparison"]
    if comparison["hidden_weighted_score"] is not False:
        invalid.append("hidden_weighted_score")
    if comparison["allow_unique_engineering_winner"] is not False:
        invalid.append("allow_unique_engineering_winner")
    if invalid:
        raise ValueError("Day 23 guardrail failed: " + ", ".join(invalid))


def main():
    config = load_config("configs/day23_residual_defocus_optical_impact.yaml")
    validate_execution_lock(config)
    model_file, model_hash = validate_input_model(config)
    batch_file, case_file = validate_day8_evidence(config, model_file, model_hash)
    day22_file = find_latest_day22_report(config)
    validate_day22_evidence(config, day22_file)
    validate_analysis_recipes(config)
    validate_guardrails(config)
    cases = build_cases(config)

    print("========== DAY 23 RESIDUAL-DEFOCUS OPTICAL-IMPACT PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will be created.")
    print(f"Focused input model: {model_file}")
    print(f"Focused model SHA256: {model_hash}")
    print(f"Day 8 batch evidence: {batch_file}")
    print(f"Day 8 baseline evidence: {case_file}")
    print(f"Day 22 error-budget evidence: {day22_file}")
    print(
        "Reference image distance: "
        f"{float(config['reference_state']['focused_image_distance_mm']):.10f} mm"
    )
    print("Quick Focus is forbidden after the residual offset is written.")
    print()
    print("Planned residual-defocus cases:")
    for case in cases:
        control = " <- baseline control" if case["is_control"] else ""
        print(
            f"  {case['case_id']}: offset={case['offset_mm']:+.3f} mm, "
            f"image distance={case['target_image_distance_mm']:.10f} mm{control}"
        )
        print("    Standard Spot + FFT MTF at 30/50 cycles/mm")
    print()
    print("Planned workload after approval:")
    print(f"  independent working copies: {config['comparison']['independent_working_copy_count']}")
    print(f"  Standard Spot exports: {config['comparison']['standard_spot_export_count']}")
    print(f"  FFT MTF exports: {config['comparison']['fft_mtf_export_count']}")
    print(f"  Quick Focus runs: {config['comparison']['quick_focus_run_count']}")
    print()
    print("[PASS] Frozen Day 8 focused baseline model verified")
    print("[PASS] Day 8 provenance and safety evidence verified")
    print("[PASS] Day 22 teaching error-budget evidence verified")
    print("[PASS] Seven unique symmetric offsets and one control verified")
    print("[PASS] Standard Spot and FFT MTF recipes match the frozen baseline")
    print("[PASS] Quick Focus, optimization, SaveAs and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
