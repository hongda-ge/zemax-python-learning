"""Day 22 step 1: audit and print the focus-position error-budget plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep the first Day 22 step strictly read-only and offline."""

    execution = config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 22 execution must remain disabled.")
    reviewed_flags = (
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_model_copy",
        "allow_offline_evaluation",
        "allow_engineering_recommendation",
    )
    invalid = [
        key for key in reviewed_flags if not isinstance(execution[key], bool)
    ]
    if invalid:
        raise ValueError("Day 22 execution flag is not Boolean: " + ", ".join(invalid))
    forbidden = (
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_model_copy",
        "allow_engineering_recommendation",
    )
    enabled = [key for key in forbidden if execution[key] is not False]
    if enabled:
        raise ValueError("Day 22 forbidden action is enabled: " + ", ".join(enabled))


def find_latest_day21_report(config):
    """Find the newest reviewed Day 21 safety-margin report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day21_output_root"]
    matches = list(root.glob(f"**/{source['day21_report_name']}"))
    if not matches:
        raise FileNotFoundError("No Day 21 safety-margin report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day21_report(config, report_file):
    """Require complete Day 21 provenance and safety evidence."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    details = report.get("details", [])
    summaries = report.get("summaries", [])
    expected_summary_count = 2 * int(source["expected_margin_policy_count"])
    expected_detail_count = (9 + int(source["expected_case_count"])) * int(
        source["expected_margin_policy_count"]
    )
    checks = {
        "task": report.get("task") == source["day21_expected_task"],
        "status": report.get("status") == "success",
        "summary count": len(summaries) == expected_summary_count,
        "detail count": len(details) == expected_detail_count,
        "measured cases only": report.get("measured_cases_only") is True,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated")
        is False,
        "no recommendation": report.get("engineering_recommendation") is None,
    }
    selected = source["selected_evidence_policy"]
    bare = [
        row
        for row in summaries
        if row.get("evidence_policy") == selected
        and row.get("margin_policy_id") == "bare_coverage"
    ]
    checks["one selected bare-coverage summary"] = len(bare) == 1
    if len(bare) == 1:
        checks["selected case count"] = (
            int(bare[0]["sampled_case_count"])
            == int(source["expected_case_count"])
        )
        checks["selected bare coverage"] = (
            int(bare[0]["passed_case_count"])
            == int(source["expected_case_count"])
        )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 21 evidence failed: " + ", ".join(failed))
    return report, bare[0]


def validate_mechanism(config, report):
    """Require one internally consistent teaching mechanism."""

    mechanism = config["teaching_mechanism"]
    half_travel = float(mechanism["symmetric_half_travel_mm"])
    total_travel = float(mechanism["total_travel_mm"])
    if half_travel <= 0.0:
        raise ValueError("Day 22 half travel must be positive.")
    if not math.isclose(total_travel, 2.0 * half_travel, abs_tol=1e-12):
        raise ValueError("Day 22 half travel and total travel are inconsistent.")
    if not math.isclose(
        half_travel,
        float(report["teaching_half_travel_mm"]),
        abs_tol=1e-12,
    ):
        raise ValueError("Day 22 mechanism differs from the reviewed Day 21 mechanism.")
    if mechanism["is_real_mechanism_specification"] is not False:
        raise ValueError("The teaching mechanism cannot be a real specification.")
    return half_travel


def validate_error_sources(config):
    """Require four unique positive teaching error allowances."""

    sources = config["teaching_error_sources"]
    identifiers = [item["id"] for item in sources]
    if len(sources) != 4 or len(identifiers) != len(set(identifiers)):
        raise ValueError("Day 22 requires four unique teaching error sources.")
    for item in sources:
        allowance = float(item["symmetric_allowance_mm"])
        if allowance <= 0.0:
            raise ValueError(f"Invalid error allowance: {item['id']}.")
        if not item.get("physical_meaning"):
            raise ValueError(f"Missing physical meaning: {item['id']}.")
    return sources


def validate_combination_policies(config):
    """Allow only explicit linear and teaching-RSS combinations."""

    policies = config["combination_policies"]
    expected = {"worst_case_linear", "rss_teaching"}
    if {item["id"] for item in policies} != expected:
        raise ValueError("Day 22 combination policies are incomplete.")
    for item in policies:
        if item["statistical_claim"] is not False:
            raise ValueError("Day 22 cannot make a statistical claim.")
    rss = next(item for item in policies if item["id"] == "rss_teaching")
    if rss["independence_verified"] is not False:
        raise ValueError("RSS independence must remain unverified.")
    evaluation = config["evaluation"]
    forbidden_true = (
        "convert_position_error_to_spot_or_mtf",
        "interpolation_allowed",
        "extrapolation_allowed",
        "hidden_weighted_score",
        "unique_engineering_winner_allowed",
    )
    invalid = [key for key in forbidden_true if evaluation[key] is not False]
    if invalid:
        raise ValueError("Day 22 forbidden evaluation enabled: " + ", ".join(invalid))
    return policies


def combine_allowances(sources, policy_id):
    """Combine the declared symmetric allowances by one explicit rule."""

    values = [float(item["symmetric_allowance_mm"]) for item in sources]
    if policy_id == "worst_case_linear":
        return sum(values)
    if policy_id == "rss_teaching":
        return math.sqrt(sum(value * value for value in values))
    raise ValueError(f"Unknown combination policy: {policy_id}.")


def main():
    config = load_config("configs/day22_focus_position_error_budget.yaml")
    validate_execution_lock(config)
    report_file = find_latest_day21_report(config)
    report, bare_summary = validate_day21_report(config, report_file)
    half_travel = validate_mechanism(config, report)
    sources = validate_error_sources(config)
    policies = validate_combination_policies(config)

    measured_requirement = float(
        bare_summary["required_half_travel_for_full_sampled_coverage_mm"]
    )
    observed_margin = half_travel - measured_requirement

    print("========== DAY 22 FOCUS-POSITION ERROR-BUDGET PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("All mechanism and error values are teaching scenarios.")
    print(f"Day 21 source report: {report_file}")
    print(
        f"Teaching mechanism: +/-{half_travel:.2f} mm half travel, "
        f"{2.0 * half_travel:.2f} mm total travel"
    )
    print(
        "Selected evidence: "
        f"{config['source']['selected_evidence_policy']} "
        f"({config['source']['expected_case_count']} measured points)"
    )
    print(f"Maximum measured focus requirement: {measured_requirement:.7f} mm")
    print(f"Remaining travel before error allocation: {observed_margin:.7f} mm")
    print()
    print("Teaching error sources:")
    for item in sources:
        print(
            f"  {item['id']}: +/-{float(item['symmetric_allowance_mm']):.3f} mm "
            f"({item['name']}; {item['physical_meaning']})"
        )
    print()
    print("Planned combination policies:")
    for policy in policies:
        allowance = combine_allowances(sources, policy["id"])
        total_requirement = measured_requirement + allowance
        remaining_after = half_travel - total_requirement
        state = "inside" if remaining_after >= 0.0 else "outside"
        print(
            f"  {policy['id']}: combined allowance={allowance:.7f} mm, "
            f"total requirement={total_requirement:.7f} mm, "
            f"remaining={remaining_after:+.7f} mm ({state} teaching travel)"
        )
    print()
    print("Planned offline evaluation after approval:")
    print("  1. Apply each combined error allowance to every measured dual-branch case")
    print("  2. Report remaining margin or shortfall for every case")
    print("  3. Calculate half travel needed after the teaching error budget")
    print("  4. Keep linear worst-case and RSS teaching results separate")
    print()
    print("[PASS] Day 21 report, provenance and safety state verified")
    print("[PASS] Four explicit teaching error sources verified")
    print("[PASS] Linear worst-case and non-statistical RSS policies verified")
    print("[PASS] Sample-only scope retained")
    print("[PASS] Optical interpretation and engineering claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
