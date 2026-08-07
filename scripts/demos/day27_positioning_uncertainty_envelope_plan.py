"""Day 27 step 1: audit the positioning-uncertainty envelope plan."""

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
    """Return an uppercase SHA256 fingerprint without modifying the file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_frozen_report(source, path_key, hash_key):
    """Load one exact upstream report after checking its hash."""

    report_file = PROJECT_ROOT / source[path_key]
    if not report_file.is_file():
        raise FileNotFoundError(f"Frozen report not found: {report_file}")
    if sha256_file(report_file) != source[hash_key]:
        raise ValueError(f"Frozen report changed: {report_file}")
    return report_file, json.loads(report_file.read_text(encoding="utf-8"))


def validate_execution_lock(config):
    """Keep the planning step offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 27 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_new_boundary_case",
        "allow_continuous_interval_claim",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 27 forbidden plan action enabled: " + ", ".join(enabled))


def validate_day25(config, report):
    """Require the reviewed 16-point balanced-acceptance evidence."""

    source = config["source"]
    checks = {
        "task": report.get("task") == source["day25_expected_task"],
        "status": report.get("status") == "success",
        "point count": report.get("measured_point_count")
        == source["expected_measured_point_count"],
        "measured only": report.get("measured_points_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no curve fit": report.get("curve_fit_used") is False,
        "no continuous tolerance": report.get("continuous_tolerance_claimed") is False,
        "no new ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no new metric": report.get("new_optical_metric_calculated") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 25 evidence failed: " + ", ".join(failed))
    points = report.get("combined_measured_points", [])
    if len(points) != source["expected_measured_point_count"]:
        raise ValueError("Day 25 combined measured-point table is incomplete.")
    return {round(float(item["offset_mm"]), 9): item for item in points}


def validate_day22(config, report):
    """Require the exact teaching positioning-accuracy scale."""

    source = config["source"]
    checks = {
        "task": report.get("task") == source["day22_expected_task"],
        "status": report.get("status") == "success",
        "measured only": report.get("measured_cases_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated") is False,
        "no recommendation": report.get("engineering_recommendation") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 22 evidence failed: " + ", ".join(failed))
    error_id = config["teaching_positioning_uncertainty"]["source_error_id"]
    matches = [item for item in report["teaching_error_sources"] if item["id"] == error_id]
    if len(matches) != 1:
        raise ValueError("Day 22 positioning-accuracy evidence is missing.")
    observed = float(matches[0]["symmetric_allowance_mm"])
    expected = float(
        config["teaching_positioning_uncertainty"]["symmetric_allowance_mm"]
    )
    if not math.isclose(observed, expected, abs_tol=1e-12):
        raise ValueError("Day 27 positioning uncertainty differs from Day 22.")
    if config["teaching_positioning_uncertainty"]["is_real_mechanism_specification"] is not False:
        raise ValueError("Teaching positioning uncertainty cannot be a real specification.")
    return observed


def validate_thresholds(config, points):
    """Require exact reuse of the balanced acceptance rule."""

    limits = config["balanced_acceptance"]["limits"]
    if config["balanced_acceptance"]["combination_rule"] != "all_required_metrics_must_pass":
        raise ValueError("Day 27 requires the frozen AND acceptance rule.")
    required_keys = {
        "spot_mean_rms_um_max",
        "spot_worst_rms_um_max",
        "mtf30_minimum_min",
        "mtf50_minimum_min",
    }
    if set(limits) != required_keys:
        raise ValueError("Day 27 balanced limits are incomplete.")
    # Recalculate every stored state to make sure its recorded PASS/FAIL is consistent.
    for offset, item in points.items():
        recalculated = (
            float(item["spot_mean_rms_um"]) <= float(limits["spot_mean_rms_um_max"])
            and float(item["spot_worst_rms_um"]) <= float(limits["spot_worst_rms_um_max"])
            and float(item["mtf30_minimum"]) >= float(limits["mtf30_minimum_min"])
            and float(item["mtf50_minimum"]) >= float(limits["mtf50_minimum_min"])
        )
        if recalculated is not item["balanced_acceptance_pass"]:
            raise ValueError(f"Day 25 stored acceptance changed at {offset:+.3f} mm.")


def build_candidate_plan(config, points):
    """Map each command position to three exact existing measurements."""

    candidates = [float(value) for value in config["candidate_command_offsets_mm"]]
    if candidates != sorted(candidates) or len(candidates) != len(set(candidates)):
        raise ValueError("Day 27 command offsets must be unique and increasing.")
    relative = config["envelope_sampling"]["relative_positions"]
    if [float(item["relative_offset_mm"]) for item in relative] != [-0.01, 0.0, 0.01]:
        raise ValueError("Day 27 envelope must contain negative, center and positive states.")
    plan = []
    for index, center in enumerate(candidates, start=1):
        states = []
        for position in relative:
            absolute = round(center + float(position["relative_offset_mm"]), 9)
            if absolute not in points:
                raise ValueError(
                    f"No exact measured evidence for command {center:+.3f}, state {absolute:+.3f}."
                )
            states.append(
                {
                    "state_id": position["id"],
                    "relative_offset_mm": float(position["relative_offset_mm"]),
                    "measured_offset_mm": absolute,
                    "source_case_id": points[absolute]["case_id"],
                }
            )
        plan.append(
            {
                "candidate_id": f"command_{index:03d}",
                "command_offset_mm": center,
                "states": states,
            }
        )
    return plan


def validate_guardrails(config):
    """Forbid continuous or score-based interpretations."""

    sampling = config["envelope_sampling"]
    if sampling["require_all_three_sampled_states_pass"] is not True:
        raise ValueError("All three sampled states must be required.")
    if sampling["require_exact_existing_measurements"] is not True:
        raise ValueError("Day 27 requires exact existing measurements.")
    evaluation = config["evaluation"]
    required_true = (
        "measured_points_only",
        "compare_candidates_independently",
        "report_failed_sampled_states",
        "report_failed_metrics",
    )
    forbidden_true = (
        "interpolation_allowed",
        "extrapolation_allowed",
        "optical_curve_fit_allowed",
        "assume_unmeasured_interior_passes",
        "hidden_weighted_score_allowed",
        "unique_engineering_winner_allowed",
        "continuous_acceptance_interval_claim_allowed",
    )
    invalid = [key for key in required_true if evaluation.get(key) is not True]
    invalid += [key for key in forbidden_true if evaluation.get(key) is not False]
    if invalid:
        raise ValueError("Day 27 guardrail failed: " + ", ".join(invalid))


def main():
    config = load_config("configs/day27_positioning_uncertainty_envelope.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    source = config["source"]
    day25_file, day25 = load_frozen_report(
        source, "day25_report", "day25_report_sha256"
    )
    day22_file, day22 = load_frozen_report(
        source, "day22_report", "day22_report_sha256"
    )
    points = validate_day25(config, day25)
    uncertainty = validate_day22(config, day22)
    validate_thresholds(config, points)
    plan = build_candidate_plan(config, points)

    print("========== DAY 27 POSITIONING-UNCERTAINTY ENVELOPE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("No new residual-defocus point will be executed.")
    print("The positioning uncertainty is a teaching value, not a mechanism specification.")
    print(f"Day 25 measured evidence: {day25_file}")
    print(f"Day 22 positioning evidence: {day22_file}")
    print(f"Teaching positioning uncertainty: +/-{uncertainty:.3f} mm")
    print()
    print("Planned candidate command envelopes:")
    for candidate in plan:
        print(
            f"  {candidate['candidate_id']}: command={candidate['command_offset_mm']:+.3f} mm"
        )
        for state in candidate["states"]:
            print(
                f"    {state['state_id']}: measured={state['measured_offset_mm']:+.3f} mm "
                f"({state['source_case_id']})"
            )
    print()
    print("Planned offline rule:")
    print("  A candidate passes only if all three exact sampled states pass.")
    print("  Failed sampled states and their individual failed metrics will be reported.")
    print("  Passing endpoints will NOT be interpreted as a continuous passing interval.")
    print()
    print("[PASS] Frozen Day 25 report and 16 measured points verified")
    print("[PASS] Frozen Day 22 +/-0.010 mm teaching positioning scale verified")
    print("[PASS] Four candidates and twelve exact sampled-state references verified")
    print("[PASS] Balanced four-metric AND rule reproduced at full precision")
    print("[PASS] ZOS-API, interpolation, hidden score and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
