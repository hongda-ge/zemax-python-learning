"""Day 9 step 1: audit and print the Day 8 FFT MTF candidate plan."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day3_baseline_dry_run import (  # noqa: E402
    calculate_sha256,
    validate_dry_run_mode,
    validate_source_model,
)


def validate_execution_lock(day9_config):
    """Guarantee that the Day 9 planning step cannot authorize Zemax."""

    execution = day9_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 9 execution must remain disabled.")
    if execution["plan_allow_zosapi_connection"] is not False:
        raise ValueError("The Day 9 plan must not allow a ZOS-API connection.")


def find_latest_day8_report(day9_config):
    """Find the newest local-robustness report produced by Day 8."""

    source = day9_config["source"]
    search_root = PROJECT_ROOT / source["day8_output_root"]
    candidates = list(
        search_root.glob(f"fine_scan_*/{source['day8_report_name']}")
    )
    if not candidates:
        raise FileNotFoundError("No Day 8 robustness report was found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_analysis_settings(day9_config, baseline_config):
    """Confirm that Day 9 uses the frozen baseline FFT MTF definition."""

    planned = day9_config["analysis"]
    baseline = baseline_config["analysis"]["fft_mtf"]
    comparisons = {
        "type": baseline["type"],
        "evaluation_frequencies_cyc_per_mm": baseline[
            "evaluation_frequencies_cyc_per_mm"
        ],
        "components": baseline["components"],
        "fields": baseline["fields"],
        "wavelengths": baseline["wavelengths"],
        "surface": baseline["surface"],
        "polarization": baseline["polarization"],
    }
    for key, baseline_value in comparisons.items():
        if planned[key] != baseline_value:
            raise ValueError(f"Day 9 FFT MTF setting mismatch: {key}.")


def load_day8_case_report(batch_dir, case_id):
    """Load exactly one Day 8 case result by its stable case identifier."""

    matches = list(batch_dir.glob(f"{case_id}_*/result.json"))
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Day 8 result for {case_id}, found {len(matches)}."
        )
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8"))


def validate_candidate_result(case_id, result_file, result):
    """Require a successful, immutable, hash-verified Day 8 focused model."""

    if result.get("task") != "day8_local_fine_scan":
        raise ValueError(f"{case_id} did not come from the Day 8 fine scan.")
    if result.get("status") != "success":
        raise ValueError(f"{case_id} was not successful in Day 8.")
    if result.get("case", {}).get("case_id") != case_id:
        raise ValueError(f"{case_id} result identity is inconsistent.")

    safety_checks = {
        "source unchanged": result.get("source_unchanged") is True,
        "working copy unchanged": result.get("working_copy_unchanged") is True,
        "connection closed": result.get("connection_closed") is True,
    }
    failed = [name for name, passed in safety_checks.items() if not passed]
    if failed:
        raise ValueError(f"{case_id} failed: {', '.join(failed)}.")

    model_path = Path(result["saved_model"]).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Focused model not found: {model_path}")
    try:
        model_path.relative_to(OUTPUT_ROOT.resolve())
    except ValueError:
        raise ValueError(f"{case_id} focused model is outside outputs.")

    expected_hash = result["saved_model_sha256"].upper()
    actual_hash = calculate_sha256(model_path)
    if actual_hash != expected_hash:
        raise ValueError(f"{case_id} focused model SHA256 changed.")

    return {
        "case_id": case_id,
        "value_mm": result["case"]["value_mm"],
        "delta_mm": result["case"]["delta_mm"],
        "is_baseline": result["case"]["is_baseline"],
        "day8_result_file": str(result_file),
        "focused_model": str(model_path),
        "focused_model_sha256": actual_hash,
        "mtf_text_name": f"{case_id}_fft_mtf.txt",
        "mtf_result_name": "mtf_result.json",
    }


def build_candidate_plan(day9_config, report_file):
    """Build the four-candidate plan from the Day 8 plateau report."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("task") != "day8_local_robustness_analysis":
        raise ValueError("Unexpected Day 8 report type.")

    case_ids = report["plateau_case_ids"]
    expected_count = day9_config["selection"]["expected_candidate_count"]
    if len(case_ids) != expected_count or len(case_ids) != len(set(case_ids)):
        raise ValueError("Day 8 plateau candidate count is invalid.")
    if (
        day9_config["selection"]["require_best_sampled_case"]
        and report["best_sampled_case"] not in case_ids
    ):
        raise ValueError("The Day 8 best sampled case is missing.")

    batch_dir = report_file.parent
    candidates = []
    for case_id in case_ids:
        result_file, result = load_day8_case_report(batch_dir, case_id)
        candidates.append(
            validate_candidate_result(case_id, result_file, result)
        )
    return report, candidates


def main():
    day9_config = load_config("configs/day9_fft_mtf_validation.yaml")
    baseline_config = load_config(day9_config["source"]["baseline_config"])

    validate_execution_lock(day9_config)
    validate_dry_run_mode(baseline_config)
    validate_source_model(baseline_config["model"])
    validate_analysis_settings(day9_config, baseline_config)

    report_file = find_latest_day8_report(day9_config)
    report, candidates = build_candidate_plan(day9_config, report_file)
    analysis = day9_config["analysis"]

    print("========== DAY 9 FFT MTF CANDIDATE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection will be created.")
    print(f"Day 8 report: {report_file}")
    print(f"Selection rule: {day9_config['selection']['source_rule']}")
    print(
        "Frequencies: "
        + ", ".join(
            f"{frequency:.0f} cycles/mm"
            for frequency in analysis[
                "evaluation_frequencies_cyc_per_mm"
            ]
        )
    )
    print("Components: tangential and sagittal")
    print("Fields/wavelengths: all")
    print("The Day 8 focused models will not be refocused or overwritten.")
    print()

    for candidate in candidates:
        baseline_mark = " <- Day 8 best/baseline" if candidate[
            "case_id"
        ] == report["best_sampled_case"] else ""
        print(
            f"{candidate['case_id']}: "
            f"thickness={candidate['value_mm']:.7f} mm{baseline_mark}"
        )
        print(f"  model: {candidate['focused_model']}")
        print(f"  SHA256: {candidate['focused_model_sha256']}")
        print(f"  planned MTF text: {candidate['mtf_text_name']}")

    print()
    print(f"[PASS] {len(candidates)} Day 8 plateau candidates selected")
    print("[PASS] Best sampled Day 8 case included")
    print("[PASS] All focused-model hashes verified")
    print("[PASS] All Day 8 safety audits verified")
    print("[PASS] FFT MTF settings match the frozen baseline config")
    print("PLAN ONLY finished. No Zemax analysis or output was created.")


if __name__ == "__main__":
    main()
