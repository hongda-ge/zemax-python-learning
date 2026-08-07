"""Day 26 step 1: audit and print the resolution-stopping plan."""

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
    """Keep Day 26 planning offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 26 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_additional_boundary_scan",
        "allow_continuous_tolerance_claim",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 26 forbidden plan action enabled: " + ", ".join(enabled))


def load_frozen_report(source, path_key, hash_key):
    """Load one exact upstream report after checking its fingerprint."""

    report_file = PROJECT_ROOT / source[path_key]
    if not report_file.is_file():
        raise FileNotFoundError(f"Frozen report not found: {report_file}")
    if sha256_file(report_file) != source[hash_key]:
        raise ValueError(f"Frozen report changed: {report_file}")
    return report_file, json.loads(report_file.read_text(encoding="utf-8"))


def validate_day25(config, report):
    """Require the reviewed two boundary brackets and all safety statements."""

    source = config["source"]
    checks = {
        "task": report.get("task") == source["day25_expected_task"],
        "status": report.get("status") == "success",
        "sixteen measured points": report.get("measured_point_count") == 16,
        "measured only": report.get("measured_points_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no curve fit": report.get("curve_fit_used") is False,
        "no tolerance": report.get("continuous_tolerance_claimed") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no new optical metric": report.get("new_optical_metric_calculated") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 25 evidence failed: " + ", ".join(failed))

    transitions = report.get("sampled_state_transitions", [])
    if len(transitions) != 2:
        raise ValueError("Day 25 must contain exactly two opposing-state brackets.")
    return transitions


def validate_boundaries(config, transitions):
    """Match the config to the exact measured Day 25 brackets."""

    observed = {
        "negative_side": transitions[0],
        "positive_side": transitions[1],
    }
    for side, expected in config["boundary_evidence"].items():
        item = observed[side]
        expected_offsets = sorted(
            [float(expected["pass_offset_mm"]), float(expected["fail_offset_mm"])]
        )
        observed_offsets = sorted(
            [float(item["left_offset_mm"]), float(item["right_offset_mm"])]
        )
        if expected_offsets != observed_offsets:
            raise ValueError(f"Day 26 {side} anchors do not match Day 25.")
        if not math.isclose(
            float(expected["unresolved_width_mm"]),
            float(item["unmeasured_width_mm"]),
            abs_tol=1e-12,
        ):
            raise ValueError(f"Day 26 {side} width does not match Day 25.")
        failed_metrics = {
            item.get("left_failed_metrics", ""),
            item.get("right_failed_metrics", ""),
        }
        if expected["limiting_metric"] not in failed_metrics:
            raise ValueError(f"Day 26 {side} limiting metric changed.")


def validate_day22(config, report):
    """Extract the reviewed teaching error scales without engineering claims."""

    source = config["source"]
    checks = {
        "task": report.get("task") == source["day22_expected_task"],
        "status": report.get("status") == "success",
        "measured only": report.get("measured_cases_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no new optical metric": report.get("new_optical_metric_calculated") is False,
        "no recommendation": report.get("engineering_recommendation") is None,
        "RSS independence unverified": report.get("rss_independence_verified") is False,
        "no RSS statistical claim": report.get("rss_statistical_claim") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 22 evidence failed: " + ", ".join(failed))
    scales = {
        item["id"]: float(item["symmetric_allowance_mm"])
        for item in report.get("teaching_error_sources", [])
    }
    expected = {
        "positioning_accuracy": 0.010,
        "repeatability": 0.010,
        "backlash": 0.020,
        "thermal_drift": 0.020,
    }
    if scales != expected:
        raise ValueError("Day 22 teaching error scales changed.")
    return scales


def validate_policies(config, scales):
    """Require explicit, ordered and non-combined teaching policies."""

    policies = config["teaching_stopping_policies"]
    if [item["id"] for item in policies] != [
        "numerical_1um",
        "positioning_accuracy_matched",
        "backlash_matched",
    ]:
        raise ValueError("Day 26 teaching policies changed.")
    thresholds = [float(item["maximum_unresolved_width_mm"]) for item in policies]
    if thresholds != sorted(thresholds) or thresholds[0] <= 0.0:
        raise ValueError("Day 26 policy thresholds must be positive and increasing.")
    if not math.isclose(thresholds[1], scales["positioning_accuracy"], abs_tol=1e-12):
        raise ValueError("Positioning-matched policy does not match Day 22.")
    if not math.isclose(thresholds[2], scales["backlash"], abs_tol=1e-12):
        raise ValueError("Backlash-matched policy does not match Day 22.")
    evaluation = config["evaluation"]
    required_true = (
        "compare_each_side_independently",
        "report_width_to_positioning_accuracy_ratio",
        "report_required_bisection_count",
        "bisection_is_planning_only",
        "measured_points_only",
    )
    forbidden_true = (
        "interpolation_allowed",
        "extrapolation_allowed",
        "optical_curve_fit_allowed",
        "hidden_weighted_score_allowed",
        "unique_stopping_rule_allowed",
        "engineering_tolerance_claim_allowed",
    )
    invalid = [key for key in required_true if evaluation.get(key) is not True]
    invalid += [key for key in forbidden_true if evaluation.get(key) is not False]
    if invalid:
        raise ValueError("Day 26 evaluation guardrail failed: " + ", ".join(invalid))
    return policies


def planned_bisections(width, target):
    """Return planning-only halvings needed for width <= target."""

    if width <= target:
        return 0
    return math.ceil(math.log2(width / target))


def main():
    config = load_config("configs/day26_simulation_resolution_stopping.yaml")
    validate_execution_lock(config)
    source = config["source"]
    day25_file, day25 = load_frozen_report(
        source, "day25_report", "day25_report_sha256"
    )
    day22_file, day22 = load_frozen_report(
        source, "day22_report", "day22_report_sha256"
    )
    transitions = validate_day25(config, day25)
    validate_boundaries(config, transitions)
    scales = validate_day22(config, day22)
    policies = validate_policies(config, scales)

    print("========== DAY 26 SIMULATION-RESOLUTION STOPPING PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("No additional boundary point will be executed in this step.")
    print("All mechanism values and stopping policies are teaching examples.")
    print(f"Day 25 boundary evidence: {day25_file}")
    print(f"Day 22 error-scale evidence: {day22_file}")
    print()
    print("Reviewed unresolved measured brackets:")
    for side, item in config["boundary_evidence"].items():
        print(
            f"  {side}: width={float(item['unresolved_width_mm']):.3f} mm, "
            f"limiting metric={item['limiting_metric']}"
        )
    print()
    print("Teaching mechanical error scales:")
    for key, value in scales.items():
        print(f"  {key}: +/-{value:.3f} mm")
    print()
    print("Planned stopping-policy comparison:")
    for policy in policies:
        target = float(policy["maximum_unresolved_width_mm"])
        print(f"  {policy['id']}: unresolved width <= {target:.3f} mm")
        for side, item in config["boundary_evidence"].items():
            width = float(item["unresolved_width_mm"])
            decision = "STOP" if width <= target else "CONTINUE"
            halvings = planned_bisections(width, target)
            print(
                f"    {side}: {decision}; planning-only additional bisections={halvings}"
            )
    print()
    print("[PASS] Frozen Day 25 boundary report and SHA256 verified")
    print("[PASS] Frozen Day 22 teaching error report and SHA256 verified")
    print("[PASS] Two boundary widths and limiting metrics reproduced")
    print("[PASS] Three explicit stopping policies verified")
    print("[PASS] ZOS-API, interpolation and engineering claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
