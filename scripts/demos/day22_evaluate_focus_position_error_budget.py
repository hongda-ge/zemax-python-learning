"""Day 22 step 2: evaluate teaching focus-position error budgets offline."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from day22_focus_position_error_budget_plan import (  # noqa: E402
    combine_allowances,
    find_latest_day21_report,
    validate_combination_policies,
    validate_day21_report,
    validate_error_sources,
    validate_mechanism,
)


def validate_offline_execution(config):
    """Allow only the reviewed offline evaluation."""

    execution = config["execution"]
    expected = {
        "enabled": False,
        "allow_zosapi_connection": False,
        "allow_new_optical_calculation": False,
        "allow_model_copy": False,
        "allow_offline_evaluation": True,
        "allow_engineering_recommendation": False,
    }
    invalid = [key for key, value in expected.items() if execution.get(key) is not value]
    if invalid:
        raise ValueError("Day 22 offline execution lock failed: " + ", ".join(invalid))


def selected_bare_details(config, report):
    """Extract the six measured dual-branch cases before error allocation."""

    selected = config["source"]["selected_evidence_policy"]
    rows = [
        row
        for row in report["details"]
        if row.get("evidence_policy") == selected
        and row.get("margin_policy_id") == "bare_coverage"
    ]
    rows.sort(key=lambda row: float(row["delta_mm"]))
    expected_count = int(config["source"]["expected_case_count"])
    if len(rows) != expected_count:
        raise ValueError("Day 22 selected-case count is incorrect.")
    identifiers = [row["case_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Day 22 selected cases are not unique.")
    return rows


def evaluate_details(config, source_rows, sources, policies, half_travel):
    """Apply both explicit error combinations to every measured case."""

    details = []
    source_allowances = {
        item["id"]: float(item["symmetric_allowance_mm"]) for item in sources
    }
    for policy in policies:
        combined = combine_allowances(sources, policy["id"])
        for row in source_rows:
            measured = float(row["required_half_travel_mm"])
            total = measured + combined
            remaining_before = half_travel - measured
            remaining_after = half_travel - total
            details.append(
                {
                    "combination_policy_id": policy["id"],
                    "combination_policy_name": policy["name"],
                    "case_id": row["case_id"],
                    "delta_mm": float(row["delta_mm"]),
                    "surface2_value_mm": float(row["surface2_value_mm"]),
                    "measured_focus_requirement_mm": measured,
                    "available_half_travel_mm": half_travel,
                    "remaining_margin_before_budget_mm": remaining_before,
                    "error_source_allowances_mm": source_allowances,
                    "combined_error_allowance_mm": combined,
                    "total_requirement_after_budget_mm": total,
                    "remaining_margin_after_budget_mm": remaining_after,
                    "shortfall_mm": max(0.0, -remaining_after),
                    "passed": remaining_after >= -1e-12,
                }
            )
    return details


def summarize(details, policy_id, half_travel):
    """Summarize one explicit error-combination policy."""

    rows = [row for row in details if row["combination_policy_id"] == policy_id]
    passed = [row["case_id"] for row in rows if row["passed"]]
    failed = [row["case_id"] for row in rows if not row["passed"]]
    maximum_total = max(row["total_requirement_after_budget_mm"] for row in rows)
    limiting = [
        row["case_id"]
        for row in rows
        if math.isclose(
            row["total_requirement_after_budget_mm"],
            maximum_total,
            abs_tol=1e-12,
        )
    ]
    return {
        "combination_policy_id": policy_id,
        "sampled_case_count": len(rows),
        "passed_case_count": len(passed),
        "pass_percent": 100.0 * len(passed) / len(rows),
        "passed_case_ids": passed,
        "failed_case_ids": failed,
        "current_half_travel_mm": half_travel,
        "required_half_travel_for_full_sampled_coverage_mm": maximum_total,
        "additional_half_travel_needed_mm": max(0.0, maximum_total - half_travel),
        "limiting_case_ids": limiting,
    }


def write_detail_csv(path, details):
    """Write a flat, human-readable table of every policy and case."""

    fields = (
        "combination_policy_id",
        "case_id",
        "delta_mm",
        "surface2_value_mm",
        "measured_focus_requirement_mm",
        "available_half_travel_mm",
        "remaining_margin_before_budget_mm",
        "combined_error_allowance_mm",
        "total_requirement_after_budget_mm",
        "remaining_margin_after_budget_mm",
        "shortfall_mm",
        "passed",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(details)


def write_summary_csv(path, summaries):
    """Write one row per error-combination policy."""

    fields = (
        "combination_policy_id",
        "sampled_case_count",
        "passed_case_count",
        "pass_percent",
        "failed_case_ids",
        "current_half_travel_mm",
        "required_half_travel_for_full_sampled_coverage_mm",
        "additional_half_travel_needed_mm",
        "limiting_case_ids",
    )
    flat = []
    for summary in summaries:
        row = dict(summary)
        row["failed_case_ids"] = ";".join(row["failed_case_ids"])
        row["limiting_case_ids"] = ";".join(row["limiting_case_ids"])
        flat.append(row)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)


def create_figure(path, details, half_travel):
    """Plot remaining margin before and after each teaching budget."""

    policies = []
    for row in details:
        if row["combination_policy_id"] not in policies:
            policies.append(row["combination_policy_id"])
    baseline_rows = [
        row for row in details if row["combination_policy_id"] == policies[0]
    ]
    deltas = [row["delta_mm"] for row in baseline_rows]
    before = [row["remaining_margin_before_budget_mm"] for row in baseline_rows]

    fig, axis = plt.subplots(figsize=(9.0, 5.2))
    axis.plot(deltas, before, marker="o", linewidth=2, label="Before error budget")
    for policy_id in policies:
        rows = [row for row in details if row["combination_policy_id"] == policy_id]
        axis.plot(
            [row["delta_mm"] for row in rows],
            [row["remaining_margin_after_budget_mm"] for row in rows],
            marker="o",
            linewidth=2,
            label=policy_id,
        )
    axis.axhline(0.0, color="black", linewidth=1.2, linestyle="--")
    axis.set_xlabel("Surface 2 thickness delta (mm)")
    axis.set_ylabel("Remaining half-travel margin (mm)")
    axis.set_title(
        "Day 22 teaching focus-position error budget\n"
        f"available symmetric half travel = +/-{half_travel:.2f} mm"
    )
    axis.grid(True, alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    config = load_config("configs/day22_focus_position_error_budget.yaml")
    validate_offline_execution(config)
    report_file = find_latest_day21_report(config)
    report, _ = validate_day21_report(config, report_file)
    half_travel = validate_mechanism(config, report)
    sources = validate_error_sources(config)
    policies = validate_combination_policies(config)
    source_rows = selected_bare_details(config, report)

    details = evaluate_details(config, source_rows, sources, policies, half_travel)
    summaries = [summarize(details, item["id"], half_travel) for item in policies]

    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / config["output"]["root"] / f"error_budget_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    detail_file = output_dir / "focus_position_error_budget_details.csv"
    summary_file = output_dir / "focus_position_error_budget_summary.csv"
    figure_file = output_dir / "day22_focus_position_error_budget.png"
    report_file_out = output_dir / "focus_position_error_budget_report.json"

    write_detail_csv(detail_file, details)
    write_summary_csv(summary_file, summaries)
    create_figure(figure_file, details, half_travel)

    result = {
        "task": "day22_focus_position_error_budget_evaluation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day21_report": str(report_file.resolve()),
        "selected_evidence_policy": config["source"]["selected_evidence_policy"],
        "teaching_half_travel_mm": half_travel,
        "teaching_error_sources": sources,
        "combination_policies": policies,
        "details": details,
        "summaries": summaries,
        "measured_cases_only": True,
        "rss_statistical_claim": False,
        "rss_independence_verified": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "engineering_recommendation": None,
    }
    report_file_out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("========== DAY 22 OFFLINE FOCUS-POSITION ERROR BUDGET ==========")
    print("No ZOS-API connection, model copy or new optical calculation was used.")
    print(f"Teaching mechanism half travel: +/-{half_travel:.2f} mm")
    print("RSS is a teaching combination only; independence was not verified.")
    print()
    for summary in summaries:
        policy_id = summary["combination_policy_id"]
        allowance = next(
            row["combined_error_allowance_mm"]
            for row in details
            if row["combination_policy_id"] == policy_id
        )
        print(f"{policy_id}: combined allowance={allowance:.7f} mm")
        print(
            f"  {summary['passed_case_count']}/{summary['sampled_case_count']} pass; "
            f"failed={summary['failed_case_ids']}"
        )
        print(
            "  half travel for full sampled coverage: "
            f"{summary['required_half_travel_for_full_sampled_coverage_mm']:.7f} mm"
        )
        print(
            "  additional half travel beyond +/-1.00 mm: "
            f"{summary['additional_half_travel_needed_mm']:.7f} mm"
        )
    print()
    print("[RESULT] Error allowance consumes part of the measured travel margin")
    print("[RESULT] Endpoint failures are reported instead of hidden in a score")
    print("[RESULT] All results apply only to measured teaching cases")
    print("[RESULT] No Spot/MTF or engineering recommendation was produced")
    print("[PASS] No interpolation, extrapolation or statistical RSS claim")
    print(f"[PASS] Detail CSV: {detail_file}")
    print(f"[PASS] Summary CSV: {summary_file}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file_out}")


if __name__ == "__main__":
    main()
