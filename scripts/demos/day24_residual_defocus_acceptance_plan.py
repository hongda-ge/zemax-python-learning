"""Day 24 step 1: audit the residual-defocus acceptance plan."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep the plan step offline and prevent premature evaluation."""

    execution = config["execution"]
    locked_false = {
        "generic execution": execution["enabled"],
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "new optical calculation": execution["allow_new_optical_calculation"],
        "engineering recommendation": execution["allow_engineering_recommendation"],
    }
    enabled = [name for name, value in locked_false.items() if value is not False]
    if enabled:
        raise ValueError("Day 24 plan lock failed: " + ", ".join(enabled))
    if not isinstance(execution["allow_acceptance_evaluation"], bool):
        raise ValueError("The acceptance-evaluation switch must be Boolean.")


def find_latest_day23_report(config):
    """Locate the newest completed Day 23 offline analysis report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day23_output_root"]
    matches = list(root.glob("offline_analysis_*/" + source["day23_report_name"]))
    if not matches:
        raise FileNotFoundError("No Day 23 offline analysis report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day23_report(config, report_file):
    """Require the exact seven measured, immutable Day 23 observations."""

    report_bytes = report_file.read_bytes()
    report_hash = hashlib.sha256(report_bytes).hexdigest().upper()
    report = json.loads(report_bytes.decode("utf-8"))
    source = config["source"]
    checks = {
        "report hash": report_hash == source["expected_report_sha256"],
        "task": report.get("task") == source["expected_task"],
        "status": report.get("status") == "success",
        "source hash": report.get("source_sha256", "").upper()
        == source["expected_source_sha256"],
        "measured only": report.get("measured_points_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no curve fit": report.get("curve_fit_used") is False,
        "no new ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no new optical metric": report.get("new_optical_metric_calculated") is False,
        "no engineering winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 23 evidence failed: " + ", ".join(failed))

    rows = report.get("rows", [])
    actual_ids = [row.get("case_id") for row in rows]
    actual_offsets = [float(row.get("offset_mm")) for row in rows]
    if actual_ids != source["expected_case_ids"]:
        raise ValueError("The Day 23 case identities or order changed.")
    expected_offsets = [float(value) for value in source["expected_offsets_mm"]]
    if actual_offsets != expected_offsets:
        raise ValueError("The Day 23 measured offsets changed.")
    controls = [value for value in actual_offsets if math.isclose(value, 0.0)]
    if len(rows) != 7 or len(controls) != 1:
        raise ValueError("Day 24 requires seven points and one zero-offset control.")

    required = {
        "spot_mean_rms_um",
        "spot_worst_rms_um",
        "mtf30_mean",
        "mtf30_minimum",
        "mtf50_mean",
        "mtf50_minimum",
    }
    for row in rows:
        missing = required.difference(row)
        if missing:
            raise ValueError(
                f"{row['case_id']} is missing metrics: " + ", ".join(sorted(missing))
            )
    return report, rows


def validate_guardrails(config):
    """Reject interpolation, scores and engineering claims."""

    guardrails = config["guardrails"]
    required_true = (
        "require_seven_measured_points",
        "require_zero_offset_control",
        "measured_points_only",
        "label_thresholds_as_teaching_only",
        "preserve_mean_and_minimum_mtf_separation",
    )
    missing = [key for key in required_true if guardrails.get(key) is not True]
    forbidden = (
        "interpolation_allowed",
        "extrapolation_allowed",
        "curve_fit_allowed",
        "hidden_weighted_score_allowed",
        "unique_engineering_winner_allowed",
    )
    enabled = [key for key in forbidden if guardrails.get(key) is not False]
    if missing or enabled:
        raise ValueError(
            "Day 24 guardrail failed: " + ", ".join(missing + enabled)
        )


def validate_scenarios(config):
    """Require three ordered, transparently nested threshold scenarios."""

    acceptance = config["acceptance"]
    if acceptance["combination_rule"] != "all_required_metrics_must_pass":
        raise ValueError("Every required Day 24 metric must pass independently.")
    expected_required = {
        "spot_mean_rms_um": "maximum",
        "spot_worst_rms_um": "maximum",
        "mtf30_minimum": "minimum",
        "mtf50_minimum": "minimum",
    }
    if acceptance["required_metrics"] != expected_required:
        raise ValueError("The Day 24 required metrics changed.")
    if acceptance["diagnostic_only_metrics"] != ["mtf30_mean", "mtf50_mean"]:
        raise ValueError("Mean MTF must remain diagnostic-only in Day 24.")

    scenarios = acceptance["scenarios"]
    expected_ids = ["strict_protection", "balanced_acceptance", "relaxed_teaching"]
    if [item.get("id") for item in scenarios] != expected_ids:
        raise ValueError("Day 24 requires the three reviewed scenarios in order.")

    previous = None
    for scenario in scenarios:
        limits = scenario["limits"]
        values = tuple(float(value) for value in limits.values())
        if any(value <= 0.0 for value in values):
            raise ValueError(f"{scenario['id']} contains a non-positive threshold.")
        if previous is not None:
            if limits["spot_mean_rms_um_max"] < previous["spot_mean_rms_um_max"]:
                raise ValueError("Spot mean limits must relax in scenario order.")
            if limits["spot_worst_rms_um_max"] < previous["spot_worst_rms_um_max"]:
                raise ValueError("Worst Spot limits must relax in scenario order.")
            if limits["mtf30_minimum_min"] > previous["mtf30_minimum_min"]:
                raise ValueError("MTF30 limits must relax in scenario order.")
            if limits["mtf50_minimum_min"] > previous["mtf50_minimum_min"]:
                raise ValueError("MTF50 limits must relax in scenario order.")
        previous = limits
    return scenarios


def main():
    config = load_config("configs/day24_residual_defocus_acceptance.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    report_file = find_latest_day23_report(config)
    _, rows = validate_day23_report(config, report_file)
    scenarios = validate_scenarios(config)

    print("========== DAY 24 RESIDUAL-DEFOCUS ACCEPTANCE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection or new optical calculation will be created.")
    print("No case will be marked pass or fail in this step.")
    print("All thresholds are teaching examples, not detector requirements.")
    print(f"Day 23 report: {report_file}")
    print()
    print("Seven frozen measured offsets:")
    for row in rows:
        print(
            f"  {row['case_id']}: offset={row['offset_mm']:+.3f} mm, "
            f"Spot mean/worst={row['spot_mean_rms_um']:.3f}/"
            f"{row['spot_worst_rms_um']:.3f} um, "
            f"MTF30 min={row['mtf30_minimum']:.4f}, "
            f"MTF50 min={row['mtf50_minimum']:.4f}"
        )

    print("\nPlanned teaching acceptance scenarios:")
    for scenario in scenarios:
        limits = scenario["limits"]
        print(f"  {scenario['id']} ({scenario['name']}):")
        print(
            "    require all: "
            f"Spot mean <= {limits['spot_mean_rms_um_max']:.3f} um, "
            f"worst Spot <= {limits['spot_worst_rms_um_max']:.3f} um, "
            f"MTF30 min >= {limits['mtf30_minimum_min']:.3f}, "
            f"MTF50 min >= {limits['mtf50_minimum_min']:.3f}"
        )
    print("\nMTF30/MTF50 means will be reported as diagnostics, not pass criteria.")
    print("[PASS] Reviewed Day 23 seven-point evidence verified")
    print("[PASS] Three explicit and progressively relaxed scenarios verified")
    print("[PASS] Four required metrics remain independent")
    print("[PASS] ZOS-API, interpolation, hidden score and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
