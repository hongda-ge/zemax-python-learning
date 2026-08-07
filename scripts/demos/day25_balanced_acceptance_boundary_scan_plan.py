"""Day 25 step 1: audit the balanced-acceptance boundary-scan plan."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    """Return an uppercase SHA256 fingerprint without changing the file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Forbid all execution during the Day 25 planning step."""

    execution = config["execution"]
    non_boolean = [key for key, value in execution.items() if not isinstance(value, bool)]
    if non_boolean:
        raise ValueError("Day 25 execution switch is not Boolean: " + ", ".join(non_boolean))
    permanently_forbidden = (
        "enabled",
        "allow_quick_focus",
        "allow_optimization",
        "allow_save_as",
        "allow_engineering_tolerance_claim",
    )
    enabled = [key for key in permanently_forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 25 forbidden plan action enabled: " + ", ".join(enabled))


def validate_source_files(config):
    """Verify the exact Day 24 report and focused Zemax input model."""

    source = config["source"]
    report_file = PROJECT_ROOT / source["day24_report"]
    model_file = PROJECT_ROOT / source["focused_model"]
    if not report_file.is_file():
        raise FileNotFoundError(f"Day 24 report not found: {report_file}")
    if not model_file.is_file():
        raise FileNotFoundError(f"Focused model not found: {model_file}")
    report_hash = sha256_file(report_file)
    model_hash = sha256_file(model_file)
    if report_hash != source["day24_report_sha256"]:
        raise ValueError("The frozen Day 24 acceptance report changed.")
    if model_hash != source["focused_model_sha256"]:
        raise ValueError("The frozen focused input model changed.")
    return report_file, model_file


def validate_day24_evidence(config, report_file):
    """Require the reviewed balanced scenario and its four boundary anchors."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    checks = {
        "task": report.get("task") == source["expected_day24_task"],
        "status": report.get("status") == "success",
        "teaching only": report.get("teaching_thresholds_only") is True,
        "AND rule": report.get("combination_rule")
        == "all_required_metrics_must_pass",
        "measured only": report.get("measured_points_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no curve fit": report.get("curve_fit_used") is False,
        "no hidden score": report.get("hidden_weighted_score_used") is False,
        "no new ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no new metric": report.get("new_optical_metric_calculated") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 24 evidence failed: " + ", ".join(failed))

    scenario_id = source["expected_scenario_id"]
    details = [
        item for item in report.get("details", []) if item.get("scenario_id") == scenario_id
    ]
    if len(details) != 7:
        raise ValueError("The Day 24 balanced scenario does not contain seven points.")
    indexed = {round(float(item["offset_mm"]), 9): item for item in details}
    expected = {
        -0.01: False,
        0.0: True,
        0.02: True,
        0.05: False,
    }
    for offset, passed in expected.items():
        item = indexed.get(offset)
        if item is None or item.get("all_required_metrics_pass") is not passed:
            raise ValueError(f"Day 24 boundary anchor changed at {offset:+.3f} mm.")
    if indexed[-0.01].get("failed_metrics") != "mtf50_minimum":
        raise ValueError("The reviewed negative-side limiting metric changed.")
    return report, indexed


def validate_thresholds(config, report):
    """Require exact reuse of the Day 24 balanced thresholds."""

    expected = config["balanced_acceptance"]["limits"]
    details = [
        item
        for item in report["details"]
        if item["scenario_id"] == config["source"]["expected_scenario_id"]
    ]
    observed = {
        "spot_mean_rms_um_max": details[0]["spot_mean_limit"],
        "spot_worst_rms_um_max": details[0]["spot_worst_limit"],
        "mtf30_minimum_min": details[0]["mtf30_minimum_limit"],
        "mtf50_minimum_min": details[0]["mtf50_minimum_limit"],
    }
    if observed != expected:
        raise ValueError("Day 25 thresholds do not match Day 24 balanced acceptance.")


def validate_new_offsets(config):
    """Require unique new points strictly inside the two unknown brackets."""

    scan = config["boundary_scan"]
    negative = scan["negative_side"]
    positive = scan["positive_side"]
    negative_values = [float(value) for value in negative["new_offsets_mm"]]
    positive_values = [float(value) for value in positive["new_offsets_mm"]]
    if negative_values != sorted(negative_values):
        raise ValueError("Negative-side offsets must be increasing.")
    if positive_values != sorted(positive_values):
        raise ValueError("Positive-side offsets must be increasing.")
    if not all(
        float(negative["known_fail_offset_mm"]) < value
        < float(negative["known_pass_offset_mm"])
        for value in negative_values
    ):
        raise ValueError("A negative-side point is outside the reviewed bracket.")
    if not all(
        float(positive["known_pass_offset_mm"]) < value
        < float(positive["known_fail_offset_mm"])
        for value in positive_values
    ):
        raise ValueError("A positive-side point is outside the reviewed bracket.")
    values = negative_values + positive_values
    if len(values) != int(scan["new_case_count"]) or len(values) != len(set(values)):
        raise ValueError("Day 25 requires nine unique new boundary points.")
    old_offsets = {-0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05}
    if old_offsets.intersection(values):
        raise ValueError("A Day 25 point duplicates a Day 23 measured point.")
    return negative_values, positive_values


def validate_guardrails(config):
    """Keep the experiment discrete, immutable and non-optimizing."""

    guardrails = config["guardrails"]
    required_true = (
        "use_independent_working_copy_per_case",
        "run_sequentially",
        "stop_on_first_unexpected_failure",
        "preserve_input_model_hash",
        "preserve_every_disk_working_copy_hash",
        "require_every_connection_closed",
        "forbid_quick_focus",
        "forbid_optimization",
        "forbid_save_as",
        "evaluate_full_precision",
        "measured_points_only",
    )
    missing = [key for key in required_true if guardrails.get(key) is not True]
    forbidden = (
        "interpolation_allowed",
        "extrapolation_allowed",
        "curve_fit_allowed",
        "hidden_weighted_score_allowed",
        "continuous_tolerance_claim_allowed",
    )
    enabled = [key for key in forbidden if guardrails.get(key) is not False]
    if missing or enabled:
        raise ValueError("Day 25 guardrail failed: " + ", ".join(missing + enabled))


def main():
    config = load_config("configs/day25_balanced_acceptance_boundary_scan.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    report_file, model_file = validate_source_files(config)
    report, indexed = validate_day24_evidence(config, report_file)
    validate_thresholds(config, report)
    negative_values, positive_values = validate_new_offsets(config)
    limits = config["balanced_acceptance"]["limits"]

    print("========== DAY 25 BALANCED-ACCEPTANCE BOUNDARY PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will be created.")
    print("No continuous tolerance will be claimed in this step.")
    print(f"Day 24 report: {report_file}")
    print(f"Focused source model: {model_file}")
    print()
    print("Frozen balanced teaching thresholds (all four must pass):")
    print(
        f"  Spot mean <= {limits['spot_mean_rms_um_max']:.3f} um; "
        f"worst Spot <= {limits['spot_worst_rms_um_max']:.3f} um; "
        f"MTF30 min >= {limits['mtf30_minimum_min']:.3f}; "
        f"MTF50 min >= {limits['mtf50_minimum_min']:.3f}"
    )
    print("\nReviewed boundary anchors:")
    for offset in (-0.01, 0.0, 0.02, 0.05):
        item = indexed[offset]
        print(
            f"  {offset:+.3f} mm: "
            f"{'PASS' if item['all_required_metrics_pass'] else 'FAIL'}"
            + (f" ({item['failed_metrics']})" if item["failed_metrics"] else "")
        )
    print("\nPlanned new negative-side points:")
    print("  " + ", ".join(f"{value:+.3f} mm" for value in negative_values))
    print("Planned new positive-side points:")
    print("  " + ", ".join(f"{value:+.3f} mm" for value in positive_values))
    print("\nPlanned workload after separate baseline approval:")
    print("  zero-offset reproducibility control: 1")
    print("  new independent boundary cases: 9")
    print("  Standard Spot exports: 10")
    print("  FFT MTF exports: 10")
    print("  Quick Focus runs: 0")
    print("[PASS] Day 24 report and focused-model fingerprints verified")
    print("[PASS] Balanced thresholds and four boundary anchors verified")
    print("[PASS] Nine unique points lie strictly inside the unknown brackets")
    print("[PASS] Quick Focus, optimization, SaveAs and interpolation forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
