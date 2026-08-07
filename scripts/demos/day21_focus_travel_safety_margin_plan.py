"""Day 21 step 1: audit and print the focus-travel margin plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Guarantee that planning cannot run Zemax or issue a recommendation."""

    execution = config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 21 execution must remain disabled.")
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
        raise ValueError("Day 21 execution flag is not Boolean: " + ", ".join(invalid))
    for forbidden in (
        "allow_zosapi_connection",
        "allow_new_optical_calculation",
        "allow_model_copy",
        "allow_engineering_recommendation",
    ):
        if execution[forbidden] is not False:
            raise ValueError(f"Day 21 forbidden action is enabled: {forbidden}.")


def find_latest_day20_report(config):
    """Find the newest Day 20 travel-budget report."""

    source = config["source"]
    root = PROJECT_ROOT / source["day20_output_root"]
    matches = list(root.glob(f"**/{source['day20_report_name']}"))
    if not matches:
        raise FileNotFoundError("No Day 20 travel-budget report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_day20_report(config, report_file):
    """Require complete sampled coverage and the full provenance safeguards."""

    report = json.loads(report_file.read_text(encoding="utf-8"))
    details = report.get("details", [])
    summaries = report.get("summaries", [])
    envelopes = report.get("observed_travel_envelopes", [])
    source = config["source"]
    checks = {
        "task": report.get("task") == source["day20_expected_task"],
        "status": report.get("status") == "success",
        "45 detail rows": len(details) == 45,
        "six summaries": len(summaries) == 6,
        "two envelopes": len(envelopes) == 2,
        "no interpolation": report.get("interpolation_used") is False,
        "no extrapolation": report.get("extrapolation_used") is False,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated")
        is False,
        "no recommendation": report.get("engineering_recommendation") is None,
    }
    expected_policies = set(source["expected_policies"])
    checks["envelope policies"] = {
        item.get("policy") for item in envelopes
    } == expected_policies
    for policy in expected_policies:
        expected_count = int(source["expected_case_counts"][policy])
        full = [
            row
            for row in summaries
            if row.get("policy") == policy
            and math.isclose(
                float(row.get("half_travel_limit_mm", -1.0)),
                1.0,
                abs_tol=1e-12,
            )
        ]
        checks[f"{policy} one full-travel summary"] = len(full) == 1
        if len(full) == 1:
            checks[f"{policy} count"] = (
                int(full[0]["sampled_case_count"]) == expected_count
            )
            checks[f"{policy} full sampled coverage"] = (
                int(full[0]["covered_case_count"]) == expected_count
            )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 20 safety-margin evidence failed: " + ", ".join(failed))
    return report


def validate_mechanism(config):
    """Require one internally consistent teaching mechanism."""

    mechanism = config["teaching_mechanism"]
    half_travel = float(mechanism["symmetric_half_travel_mm"])
    total_travel = float(mechanism["total_travel_mm"])
    if half_travel <= 0.0:
        raise ValueError("Day 21 half travel must be positive.")
    if not math.isclose(total_travel, 2.0 * half_travel, abs_tol=1e-12):
        raise ValueError("Day 21 half travel and total travel are inconsistent.")
    if mechanism["is_real_mechanism_specification"] is not False:
        raise ValueError("The teaching mechanism cannot be a real specification.")
    return half_travel


def validate_policies(config, half_travel):
    """Require unique and physically meaningful teaching policies."""

    policies = config["margin_policies"]
    identifiers = [policy["id"] for policy in policies]
    if len(policies) != 4 or len(identifiers) != len(set(identifiers)):
        raise ValueError("Day 21 requires four unique margin policies.")
    for policy in policies:
        policy_type = policy["type"]
        if policy_type == "minimum_remaining_margin":
            margin = float(policy["minimum_remaining_margin_mm"])
            if not 0.0 <= margin < half_travel:
                raise ValueError(f"Invalid margin policy: {policy['id']}.")
        elif policy_type == "maximum_utilization":
            utilization = float(policy["maximum_utilization_fraction"])
            if not 0.0 < utilization <= 1.0:
                raise ValueError(f"Invalid utilization policy: {policy['id']}.")
        else:
            raise ValueError(f"Unknown Day 21 policy type: {policy_type}.")
    evaluation = config["evaluation"]
    if evaluation["interpolation_allowed"] is not False:
        raise ValueError("Day 21 interpolation must remain forbidden.")
    if evaluation["extrapolation_allowed"] is not False:
        raise ValueError("Day 21 extrapolation must remain forbidden.")
    if evaluation["hidden_weighted_score"] is not False:
        raise ValueError("Day 21 hidden scores must remain forbidden.")
    if evaluation["unique_engineering_winner_allowed"] is not False:
        raise ValueError("Day 21 engineering winner must remain forbidden.")
    return policies


def envelope_map(report):
    """Index the two measured maximum requirements by evidence policy."""

    return {
        item["policy"]: item
        for item in report["observed_travel_envelopes"]
    }


def full_coverage_requirement(maximum_requirement, policy):
    """Calculate planned half travel needed to retain the policy margin."""

    if policy["type"] == "minimum_remaining_margin":
        return maximum_requirement + float(policy["minimum_remaining_margin_mm"])
    return maximum_requirement / float(policy["maximum_utilization_fraction"])


def main():
    config = load_config("configs/day21_focus_travel_safety_margin.yaml")
    validate_execution_lock(config)
    report_file = find_latest_day20_report(config)
    report = validate_day20_report(config, report_file)
    half_travel = validate_mechanism(config)
    policies = validate_policies(config, half_travel)
    envelopes = envelope_map(report)

    print("========== DAY 21 FOCUS-TRAVEL SAFETY-MARGIN PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or new optical calculation will occur.")
    print("All mechanism and margin values are teaching scenarios.")
    print(f"Day 20 source report: {report_file}")
    print(
        f"Teaching mechanism: +/-{half_travel:.2f} mm half travel, "
        f"{2.0 * half_travel:.2f} mm total travel"
    )
    print()
    print("Planned margin policies:")
    for policy in policies:
        if policy["type"] == "minimum_remaining_margin":
            rule = (
                "remaining margin >= "
                f"{float(policy['minimum_remaining_margin_mm']):.2f} mm"
            )
        else:
            rule = (
                "travel utilization <= "
                f"{float(policy['maximum_utilization_fraction']) * 100:.0f}%"
            )
        print(f"  {policy['id']}: {policy['name']} ({rule})")
    print()
    print("Observed full-sample requirements from Day 20:")
    for evidence_policy in config["source"]["expected_policies"]:
        maximum_requirement = float(
            envelopes[evidence_policy][
                "minimum_sampled_symmetric_half_travel_mm"
            ]
        )
        utilization = maximum_requirement / half_travel
        remaining = half_travel - maximum_requirement
        print(
            f"  {evidence_policy}: requirement={maximum_requirement:.7f} mm, "
            f"utilization={utilization * 100:.2f}%, "
            f"remaining={remaining:.7f} mm"
        )
        for policy in policies:
            required = full_coverage_requirement(maximum_requirement, policy)
            print(
                f"    {policy['id']} full-sample half travel: "
                f"{required:.7f} mm"
            )
    print()
    print("Planned offline evaluation:")
    print("  1. Recheck every measured case under all four margin policies")
    print("  2. Report failures, remaining margin and travel utilization")
    print("  3. Calculate half travel needed for full sampled coverage")
    print("  4. Keep preserve-grid and dual-branch evidence separate")
    print()
    print("[PASS] Day 20 report, provenance and safety state verified")
    print("[PASS] One teaching mechanism and four explicit policies verified")
    print("[PASS] Sample-only scope retained")
    print("[PASS] Interpolation, extrapolation and engineering claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
