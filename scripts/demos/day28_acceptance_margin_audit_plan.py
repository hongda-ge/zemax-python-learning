"""Day 28 step 1: audit and print the acceptance-margin plan."""

import hashlib
import json
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
    """Keep Day 28 planning offline and score-free."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 28 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_hidden_weighted_score",
        "allow_unique_engineering_winner",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 28 forbidden plan action enabled: " + ", ".join(enabled))


def load_day27_report(config):
    """Load the exact reviewed Day 27 report."""

    source = config["source"]
    report_file = PROJECT_ROOT / source["day27_report"]
    if not report_file.is_file():
        raise FileNotFoundError(f"Day 27 report not found: {report_file}")
    if sha256_file(report_file) != source["day27_report_sha256"]:
        raise ValueError("The frozen Day 27 report changed.")
    return report_file, json.loads(report_file.read_text(encoding="utf-8"))


def validate_day27(config, report):
    """Require complete Day 27 provenance, results and safety evidence."""

    source = config["source"]
    checks = {
        "task": report.get("task") == source["day27_expected_task"],
        "status": report.get("status") == "success",
        "detail count": len(report.get("details", [])) == source["expected_detail_count"],
        "summary count": len(report.get("summaries", []))
        == source["expected_summary_count"],
        "passing candidates": report.get("sampled_envelope_pass_candidates")
        == source["expected_passing_candidates"],
        "measured only": report.get("measured_points_only") is True,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated") is False,
        "no new defocus case": report.get("new_residual_defocus_case_executed") is False,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no curve fit": report.get("optical_curve_fit_used") is False,
        "no interior assumption": report.get("unmeasured_interior_assumed_to_pass") is False,
        "no hidden score": report.get("hidden_weighted_score_used") is False,
        "no continuous interval": report.get("continuous_acceptance_interval_claimed") is False,
        "no winner": report.get("unique_engineering_winner") is None,
        "no recommendation": report.get("engineering_recommendation") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 27 evidence failed: " + ", ".join(failed))
    return report["details"], report["summaries"]


def validate_limits(config, report):
    """Require exact reuse of the Day 27 balanced thresholds."""

    limits = config["balanced_acceptance"]["limits"]
    if config["balanced_acceptance"]["combination_rule"] != "all_required_metrics_must_pass":
        raise ValueError("Day 28 requires the frozen four-metric AND rule.")
    if limits != report.get("balanced_acceptance_limits"):
        raise ValueError("Day 28 thresholds differ from Day 27.")
    expected_metrics = {
        "spot_mean_rms_um",
        "spot_worst_rms_um",
        "mtf30_minimum",
        "mtf50_minimum",
    }
    if set(config["margin_definitions"]) != expected_metrics:
        raise ValueError("Day 28 margin definitions are incomplete.")
    for definition in config["margin_definitions"].values():
        if definition["positive_is_passing"] is not True:
            raise ValueError("Every Day 28 margin must use positive as passing.")
    return limits


def validate_candidates(config, details, summaries):
    """Select only passing candidates with three passing sampled states."""

    expected = config["source"]["expected_passing_candidates"]
    summary_index = {item["candidate_id"]: item for item in summaries}
    selected = []
    for candidate_id in expected:
        summary = summary_index.get(candidate_id)
        if summary is None or summary["sampled_envelope_pass"] is not True:
            raise ValueError(f"Day 27 passing candidate changed: {candidate_id}.")
        rows = [item for item in details if item["candidate_id"] == candidate_id]
        if len(rows) != 3 or any(item["sampled_state_pass"] is not True for item in rows):
            raise ValueError(f"Day 28 requires three passing states: {candidate_id}.")
        selected.append((summary, rows))
    return selected


def validate_guardrails(config):
    """Forbid cross-unit aggregation and continuous claims."""

    evaluation = config["candidate_evaluation"]
    required_true = (
        "include_only_day27_sampled_envelope_pass_candidates",
        "require_three_sampled_states_per_candidate",
        "candidate_margin_is_minimum_across_three_states",
        "report_limiting_state_per_metric",
        "compare_each_metric_separately",
    )
    forbidden_true = (
        "cross_unit_margin_sum_allowed",
        "normalized_margin_score_allowed",
        "rank_candidates_by_one_total_score",
    )
    invalid = [key for key in required_true if evaluation.get(key) is not True]
    invalid += [key for key in forbidden_true if evaluation.get(key) is not False]
    guardrails = config["guardrails"]
    if guardrails.get("measured_points_only") is not True:
        invalid.append("measured_points_only")
    for key in (
        "interpolation_allowed",
        "extrapolation_allowed",
        "optical_curve_fit_allowed",
        "continuous_interval_claim_allowed",
        "hidden_weighted_score_allowed",
        "unique_engineering_winner_allowed",
    ):
        if guardrails.get(key) is not False:
            invalid.append(key)
    if invalid:
        raise ValueError("Day 28 guardrail failed: " + ", ".join(invalid))


def main():
    config = load_config("configs/day28_acceptance_margin_audit.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    report_file, report = load_day27_report(config)
    details, summaries = validate_day27(config, report)
    limits = validate_limits(config, report)
    selected = validate_candidates(config, details, summaries)

    print("========== DAY 28 ACCEPTANCE-MARGIN AUDIT PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("Only the two Day 27 sampled-envelope PASS candidates will be compared.")
    print("Margins with different units will remain separate.")
    print(f"Day 27 source report: {report_file}")
    print()
    print("Frozen balanced thresholds and signed-margin definitions:")
    print(
        f"  Spot mean: {limits['spot_mean_rms_um_max']:.3f} - measured value (um)"
    )
    print(
        f"  Spot worst: {limits['spot_worst_rms_um_max']:.3f} - measured value (um)"
    )
    print(f"  MTF30 minimum: measured value - {limits['mtf30_minimum_min']:.3f}")
    print(f"  MTF50 minimum: measured value - {limits['mtf50_minimum_min']:.3f}")
    print("  Positive margin means the sampled state passes that metric.")
    print()
    print("Planned candidates:")
    for summary, rows in selected:
        offsets = ", ".join(f"{float(item['measured_offset_mm']):+.3f}" for item in rows)
        print(
            f"  {summary['candidate_id']}: command={float(summary['command_offset_mm']):+.3f} mm, "
            f"sampled offsets=[{offsets}] mm"
        )
    print()
    print("Planned offline comparison:")
    print("  1. Calculate four signed margins for every sampled state")
    print("  2. Keep the minimum sampled margin for each candidate and metric")
    print("  3. Report the limiting state and separate leader for each metric")
    print("  4. Do not sum Spot and MTF margins or select one total-score winner")
    print()
    print("[PASS] Frozen Day 27 report and SHA256 verified")
    print("[PASS] Two passing candidates and six passing sampled states verified")
    print("[PASS] Four balanced thresholds reproduced")
    print("[PASS] Four independent signed-margin definitions verified")
    print("[PASS] ZOS-API, cross-unit score and engineering winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
