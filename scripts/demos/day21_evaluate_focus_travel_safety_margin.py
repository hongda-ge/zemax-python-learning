"""Day 21 step 2: evaluate sampled focus-travel safety margins offline."""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MPL_CONFIG_DIR = PROJECT_ROOT / "outputs" / ".matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day21_focus_travel_safety_margin_plan import (  # noqa: E402
    envelope_map,
    find_latest_day20_report,
    full_coverage_requirement,
    validate_day20_report,
    validate_execution_lock,
    validate_mechanism,
    validate_policies,
)


def require_offline_authorization(config):
    """Allow only the reviewed offline safety-margin evaluation."""

    execution = config["execution"]
    if execution["allow_offline_evaluation"] is not True:
        raise ValueError("Day 21 offline evaluation is not approved.")
    enabled = [
        key
        for key, value in execution.items()
        if key != "allow_offline_evaluation" and value is not False
    ]
    if enabled:
        raise ValueError("Day 21 forbidden action is enabled: " + ", ".join(enabled))


def extract_cases(config, report):
    """Recover one unique measured-case set per Day 20 evidence policy."""

    cases_by_policy = {}
    for policy in config["source"]["expected_policies"]:
        rows = [
            row
            for row in report["details"]
            if row["policy"] == policy
            and abs(float(row["half_travel_limit_mm"]) - 1.0) <= 1e-12
        ]
        expected = int(config["source"]["expected_case_counts"][policy])
        if len(rows) != expected:
            raise ValueError(f"Day 20 case recovery failed for {policy}.")
        identifiers = [row["case_id"] for row in rows]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"Duplicate Day 20 cases found for {policy}.")
        cases_by_policy[policy] = sorted(
            (
                {
                    "case_id": row["case_id"],
                    "delta_mm": float(row["delta_mm"]),
                    "surface2_value_mm": float(row["surface2_value_mm"]),
                    "required_half_travel_mm": float(
                        row["required_half_travel_mm"]
                    ),
                }
                for row in rows
            ),
            key=lambda row: row["delta_mm"],
        )
    return cases_by_policy


def evaluate_case(case, evidence_policy, margin_policy, half_travel):
    """Apply one explicit margin rule to one measured focus requirement."""

    requirement = float(case["required_half_travel_mm"])
    remaining = half_travel - requirement
    utilization = requirement / half_travel
    if margin_policy["type"] == "minimum_remaining_margin":
        threshold = float(margin_policy["minimum_remaining_margin_mm"])
        passed = remaining + 1e-12 >= threshold
        rule_value = threshold
        rule_unit = "mm_minimum_remaining_margin"
    else:
        threshold = float(margin_policy["maximum_utilization_fraction"])
        passed = utilization <= threshold + 1e-12
        rule_value = threshold
        rule_unit = "maximum_utilization_fraction"
    return {
        "evidence_policy": evidence_policy,
        "margin_policy_id": margin_policy["id"],
        "margin_policy_name": margin_policy["name"],
        "rule_type": margin_policy["type"],
        "rule_value": rule_value,
        "rule_unit": rule_unit,
        **case,
        "available_half_travel_mm": half_travel,
        "remaining_margin_mm": remaining,
        "travel_utilization_fraction": utilization,
        "travel_utilization_percent": utilization * 100.0,
        "passed": passed,
    }


def evaluate_all(cases_by_policy, margin_policies, half_travel):
    """Evaluate every measured case under every teaching rule."""

    details = []
    summaries = []
    for evidence_policy, cases in cases_by_policy.items():
        maximum_requirement = max(
            float(case["required_half_travel_mm"]) for case in cases
        )
        for margin_policy in margin_policies:
            policy_rows = [
                evaluate_case(
                    case,
                    evidence_policy,
                    margin_policy,
                    half_travel,
                )
                for case in cases
            ]
            details.extend(policy_rows)
            passed = [row["case_id"] for row in policy_rows if row["passed"]]
            failed = [row["case_id"] for row in policy_rows if not row["passed"]]
            summaries.append(
                {
                    "evidence_policy": evidence_policy,
                    "margin_policy_id": margin_policy["id"],
                    "margin_policy_name": margin_policy["name"],
                    "sampled_case_count": len(cases),
                    "passed_case_count": len(passed),
                    "pass_percent": len(passed) / len(cases) * 100.0,
                    "passed_case_ids": passed,
                    "failed_case_ids": failed,
                    "current_half_travel_mm": half_travel,
                    "required_half_travel_for_full_sampled_coverage_mm": (
                        full_coverage_requirement(
                            maximum_requirement,
                            margin_policy,
                        )
                    ),
                }
            )
    return details, summaries


def write_csv(rows, output_file):
    """Write list-valued fields using semicolon separators."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite CSV: {output_file}")
    serializable = [
        {
            key: ";".join(value) if isinstance(value, list) else value
            for key, value in row.items()
        }
        for row in rows
    ]
    with output_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(serializable[0]))
        writer.writeheader()
        writer.writerows(serializable)


def save_figure(cases_by_policy, summaries, half_travel, output_file):
    """Plot measured utilization and policy coverage."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite figure: {output_file}")
    figure, axes = plt.subplots(2, 1, figsize=(11, 9))
    for policy, cases in cases_by_policy.items():
        axes[0].plot(
            [case["delta_mm"] for case in cases],
            [
                case["required_half_travel_mm"] / half_travel * 100.0
                for case in cases
            ],
            marker="o",
            label=policy,
        )
    axes[0].axhline(80.0, color="tab:orange", linestyle="--", label="80% policy")
    axes[0].axhline(100.0, color="tab:red", linestyle="--", label="Travel limit")
    axes[0].set_xlabel("Surface 2 thickness delta (mm)")
    axes[0].set_ylabel("Half-travel utilization (%)")
    axes[0].set_title("Measured travel utilization for the teaching mechanism")
    axes[0].grid(alpha=0.3)
    axes[0].legend(ncol=2)

    evidence_policies = list(cases_by_policy)
    margin_ids = []
    for row in summaries:
        if row["margin_policy_id"] not in margin_ids:
            margin_ids.append(row["margin_policy_id"])
    x_values = list(range(len(margin_ids)))
    width = 0.34
    for index, evidence_policy in enumerate(evidence_policies):
        policy_rows = [
            next(
                row
                for row in summaries
                if row["evidence_policy"] == evidence_policy
                and row["margin_policy_id"] == margin_id
            )
            for margin_id in margin_ids
        ]
        offset = (index - (len(evidence_policies) - 1) / 2.0) * width
        axes[1].bar(
            [value + offset for value in x_values],
            [row["pass_percent"] for row in policy_rows],
            width,
            label=evidence_policy,
        )
    axes[1].set_xticks(x_values, margin_ids, rotation=15)
    axes[1].set_ylim(0.0, 105.0)
    axes[1].set_ylabel("Measured-case pass rate (%)")
    axes[1].set_title("Bare coverage versus safety-margin coverage")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(output_file, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day21_focus_travel_safety_margin.yaml")
    validate_execution_lock(config)
    require_offline_authorization(config)
    day20_file = find_latest_day20_report(config)
    day20_report = validate_day20_report(config, day20_file)
    half_travel = validate_mechanism(config)
    margin_policies = validate_policies(config, half_travel)
    cases_by_policy = extract_cases(config, day20_report)
    details, summaries = evaluate_all(
        cases_by_policy,
        margin_policies,
        half_travel,
    )
    envelopes = envelope_map(day20_report)

    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("margin_evaluation_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    detail_csv = output_dir / "focus_travel_margin_case_details.csv"
    summary_csv = output_dir / "focus_travel_margin_summary.csv"
    figure_file = output_dir / "day21_focus_travel_safety_margin.png"
    report_file = output_dir / "focus_travel_safety_margin_report.json"
    write_csv(details, detail_csv)
    write_csv(summaries, summary_csv)
    save_figure(cases_by_policy, summaries, half_travel, figure_file)

    report = {
        "task": "day21_focus_travel_safety_margin_evaluation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day20_report": str(day20_file),
        "teaching_half_travel_mm": half_travel,
        "margin_policies": margin_policies,
        "details": details,
        "summaries": summaries,
        "day20_observed_envelopes": envelopes,
        "measured_cases_only": True,
        "interpolation_used": False,
        "extrapolation_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "engineering_recommendation": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("========== DAY 21 OFFLINE FOCUS-TRAVEL SAFETY MARGIN ==========")
    print("No ZOS-API connection, model copy or new optical calculation was used.")
    print(f"Teaching mechanism half travel: +/-{half_travel:.2f} mm")
    for margin_policy in margin_policies:
        print(f"\n{margin_policy['id']} ({margin_policy['name']}):")
        for evidence_policy in cases_by_policy:
            summary = next(
                row
                for row in summaries
                if row["margin_policy_id"] == margin_policy["id"]
                and row["evidence_policy"] == evidence_policy
            )
            print(
                f"  {evidence_policy}: {summary['passed_case_count']}/"
                f"{summary['sampled_case_count']} pass; "
                f"failed={summary['failed_case_ids']}"
            )
            print(
                "    half travel for full sampled coverage: "
                f"{summary['required_half_travel_for_full_sampled_coverage_mm']:.7f} mm"
            )
    print("\n[RESULT] Bare coverage is not equivalent to margin-qualified coverage")
    print("[RESULT] Dual-branch endpoint samples expose the smallest reserve")
    print("[RESULT] All results apply only to measured teaching cases")
    print("[RESULT] No engineering recommendation was produced")
    print("[PASS] No interpolation, extrapolation or hidden score")
    print(f"[PASS] Detail CSV: {detail_csv}")
    print(f"[PASS] Summary CSV: {summary_csv}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
