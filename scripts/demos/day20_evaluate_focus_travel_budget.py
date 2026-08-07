"""Day 20 step 2: evaluate sampled focus-travel coverage offline."""

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
from scripts.demos.day20_focus_travel_budget_plan import (  # noqa: E402
    find_latest_report,
    validate_day17,
    validate_day19,
    validate_day8,
    validate_execution_lock,
    validate_limits,
)


def require_offline_authorization(config):
    """Allow only the reviewed offline evaluation."""

    execution = config["execution"]
    if execution["allow_offline_evaluation"] is not True:
        raise ValueError("Day 20 offline evaluation is not approved.")
    forbidden = {
        key: value
        for key, value in execution.items()
        if key != "allow_offline_evaluation"
    }
    enabled = [key for key, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Day 20 forbidden action is enabled: " + ", ".join(enabled))


def build_preserve_cases(day8_rows):
    """Convert Day 8 rows to absolute preserve-Solve travel requirements."""

    return [
        {
            "case_id": row["case_id"],
            "delta_mm": float(row["delta_mm"]),
            "surface2_value_mm": float(row["value_mm"]),
            "preserve_focus_shift_mm": float(row["focus_shift_mm"]),
            "frozen_focus_shift_mm": None,
            "required_half_travel_mm": abs(float(row["focus_shift_mm"])),
        }
        for row in day8_rows
    ]


def build_dual_branch_cases(day17_rows):
    """Use the larger measured branch magnitude as the robust requirement."""

    cases = []
    for row in day17_rows:
        preserve = float(row["preserve_focus_shift_mm"])
        frozen = float(row["frozen_focus_shift_mm"])
        cases.append(
            {
                "case_id": row["case_id"],
                "delta_mm": float(row["delta_mm"]),
                "surface2_value_mm": float(row["value_mm"]),
                "preserve_focus_shift_mm": preserve,
                "frozen_focus_shift_mm": frozen,
                "required_half_travel_mm": max(abs(preserve), abs(frozen)),
            }
        )
    return cases


def evaluate_policy(policy_name, cases, limits):
    """Evaluate every measured case against every symmetric half travel."""

    details = []
    summaries = []
    for limit in limits:
        covered_cases = []
        uncovered_cases = []
        for case in cases:
            requirement = float(case["required_half_travel_mm"])
            margin = float(limit) - requirement
            covered = margin >= -1e-12
            row = {
                "policy": policy_name,
                "half_travel_limit_mm": float(limit),
                **case,
                "remaining_margin_mm": margin,
                "covered": covered,
            }
            details.append(row)
            if covered:
                covered_cases.append(case["case_id"])
            else:
                uncovered_cases.append(case["case_id"])
        summaries.append(
            {
                "policy": policy_name,
                "half_travel_limit_mm": float(limit),
                "sampled_case_count": len(cases),
                "covered_case_count": len(covered_cases),
                "coverage_percent": len(covered_cases) / len(cases) * 100.0,
                "covered_case_ids": covered_cases,
                "uncovered_case_ids": uncovered_cases,
            }
        )
    return details, summaries


def observed_travel_envelope(policy_name, cases):
    """Describe the measured directional and symmetric travel needs."""

    shifts = []
    for case in cases:
        shifts.append(float(case["preserve_focus_shift_mm"]))
        if case["frozen_focus_shift_mm"] is not None:
            shifts.append(float(case["frozen_focus_shift_mm"]))
    return {
        "policy": policy_name,
        "largest_positive_shift_mm": max(shifts),
        "most_negative_shift_mm": min(shifts),
        "minimum_sampled_symmetric_half_travel_mm": max(
            abs(value) for value in shifts
        ),
        "sampled_only": True,
    }


def write_csv(rows, output_file):
    """Write a list of dictionaries as UTF-8 CSV."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite CSV: {output_file}")
    serializable = []
    for row in rows:
        serializable.append(
            {
                key: ";".join(value) if isinstance(value, list) else value
                for key, value in row.items()
            }
        )
    with output_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(serializable[0]))
        writer.writeheader()
        writer.writerows(serializable)


def save_figure(preserve_cases, dual_cases, summaries, output_file):
    """Plot sampled travel requirements and coverage counts."""

    if output_file.exists():
        raise FileExistsError(f"Refusing to overwrite figure: {output_file}")
    figure, axes = plt.subplots(2, 1, figsize=(10, 9))
    axes[0].plot(
        [case["delta_mm"] for case in preserve_cases],
        [case["required_half_travel_mm"] for case in preserve_cases],
        "o-",
        label="Day 8 preserve-Solve grid",
    )
    axes[0].plot(
        [case["delta_mm"] for case in dual_cases],
        [case["required_half_travel_mm"] for case in dual_cases],
        "s-",
        label="Day 17 dual-branch robust",
    )
    axes[0].set_xlabel("Surface 2 thickness delta (mm)")
    axes[0].set_ylabel("Required symmetric half travel (mm)")
    axes[0].set_title("Measured focus-travel requirements")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    policies = sorted(set(row["policy"] for row in summaries))
    width = 0.34
    limits = sorted(set(row["half_travel_limit_mm"] for row in summaries))
    x_values = list(range(len(limits)))
    for policy_index, policy in enumerate(policies):
        policy_rows = [row for row in summaries if row["policy"] == policy]
        policy_rows.sort(key=lambda row: row["half_travel_limit_mm"])
        offset = (policy_index - (len(policies) - 1) / 2.0) * width
        axes[1].bar(
            [value + offset for value in x_values],
            [row["coverage_percent"] for row in policy_rows],
            width,
            label=policy,
        )
    axes[1].set_xticks(x_values, [f"+/-{value:.2f}" for value in limits])
    axes[1].set_xlabel("Symmetric half-travel limit (mm)")
    axes[1].set_ylabel("Measured-case coverage (%)")
    axes[1].set_ylim(0.0, 105.0)
    axes[1].set_title("Coverage applies only to sampled cases")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(output_file, dpi=180)
    plt.close(figure)


def main():
    config = load_config("configs/day20_focus_travel_budget.yaml")
    validate_execution_lock(config)
    require_offline_authorization(config)
    source = config["source"]
    day8_file = find_latest_report(
        source["day8_output_root"], source["day8_report_name"]
    )
    day17_file = find_latest_report(
        source["day17_output_root"], source["day17_report_name"]
    )
    day19_file = find_latest_report(
        source["day19_output_root"], source["day19_report_name"]
    )
    _, day8_rows = validate_day8(config, day8_file)
    _, day17_rows = validate_day17(config, day17_file, day8_file)
    validate_day19(config, day19_file)
    limits = validate_limits(config)

    preserve_cases = build_preserve_cases(day8_rows)
    dual_cases = build_dual_branch_cases(day17_rows)
    preserve_details, preserve_summaries = evaluate_policy(
        "preserve_solve_grid", preserve_cases, limits
    )
    dual_details, dual_summaries = evaluate_policy(
        "dual_branch_robust", dual_cases, limits
    )
    details = preserve_details + dual_details
    summaries = preserve_summaries + dual_summaries
    envelopes = [
        observed_travel_envelope("preserve_solve_grid", preserve_cases),
        observed_travel_envelope("dual_branch_robust", dual_cases),
    ]

    output_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("budget_evaluation_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    detail_csv = output_dir / "focus_travel_case_details.csv"
    summary_csv = output_dir / "focus_travel_coverage_summary.csv"
    figure_file = output_dir / "day20_focus_travel_budget.png"
    report_file = output_dir / "focus_travel_budget_report.json"
    write_csv(details, detail_csv)
    write_csv(summaries, summary_csv)
    save_figure(preserve_cases, dual_cases, summaries, figure_file)

    report = {
        "task": "day20_focus_travel_budget_evaluation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_day8_report": str(day8_file),
        "source_day17_report": str(day17_file),
        "source_day19_report": str(day19_file),
        "teaching_limits_mm": limits,
        "details": details,
        "summaries": summaries,
        "observed_travel_envelopes": envelopes,
        "interpolation_used": False,
        "extrapolation_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "engineering_recommendation": None,
    }
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("========== DAY 20 OFFLINE FOCUS-TRAVEL BUDGET ==========")
    print("No ZOS-API connection, model copy or new optical calculation was used.")
    print("Teaching limits are evaluated only at measured points.")
    for limit in limits:
        preserve = next(
            row
            for row in preserve_summaries
            if row["half_travel_limit_mm"] == limit
        )
        dual = next(
            row
            for row in dual_summaries
            if row["half_travel_limit_mm"] == limit
        )
        print(f"\nHalf travel +/-{limit:.2f} mm:")
        print(
            f"  Preserve grid: {preserve['covered_case_count']}/"
            f"{preserve['sampled_case_count']} covered; "
            f"uncovered={preserve['uncovered_case_ids']}"
        )
        print(
            f"  Dual-branch audit: {dual['covered_case_count']}/"
            f"{dual['sampled_case_count']} covered; "
            f"uncovered={dual['uncovered_case_ids']}"
        )
    print("\nObserved minimum symmetric half travel for full sampled coverage:")
    for envelope in envelopes:
        print(
            f"  {envelope['policy']}: "
            f"{envelope['minimum_sampled_symmetric_half_travel_mm']:.7f} mm"
        )
    print("[RESULT] Coverage applies to measured points only")
    print("[RESULT] No interpolation, extrapolation or engineering recommendation")
    print("[PASS] Day 8, Day 17 and Day 19 evidence verified")
    print(f"[PASS] Detail CSV: {detail_csv}")
    print(f"[PASS] Summary CSV: {summary_csv}")
    print(f"[PASS] Figure: {figure_file}")
    print(f"[PASS] Report: {report_file}")


if __name__ == "__main__":
    main()
