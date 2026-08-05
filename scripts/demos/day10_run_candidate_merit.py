"""Day 10 step 3: compare the three reviewed Pareto candidates with one MFE."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day10_merit_function_plan import (  # noqa: E402
    build_merit_candidate_plan,
    find_latest_day9_tradeoff_report,
    validate_execution_lock,
    validate_merit_definition,
)
from scripts.demos.day10_validate_baseline_merit import (  # noqa: E402
    execute_baseline_merit,
)


def validate_batch_authorization(config):
    """Require the reviewed three-candidate execution permission."""

    execution = config["execution"]
    guardrails = config["guardrails"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 10 execution must remain disabled.")
    if execution["allow_reviewed_candidate_execution"] is not True:
        raise ValueError("Day 10 candidate execution is not approved.")
    if guardrails["allow_in_memory_recipe_load"] is not True:
        raise ValueError("In-memory recipe loading is not approved.")
    if guardrails["do_not_run_optimization"] is not True:
        raise ValueError("The optimization guardrail is not active.")


def find_latest_baseline_report(config):
    """Find the newest successful fine_005 recipe-load validation."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(root.glob("baseline_check_*/fine_005/merit_result.json"))
    if not matches:
        raise FileNotFoundError("No Day 10 baseline Merit report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_baseline_report(config, report_file):
    """Use the baseline run as explicit approval for the three-case batch."""

    result = json.loads(report_file.read_text(encoding="utf-8"))
    source = config["source"]
    required = {
        "task": result.get("task") == "day10_baseline_merit_validation",
        "status": result.get("status") == "success",
        "operand count": result.get("operand_count")
        == source["merit_recipe_operand_count"],
        "definition": result.get("merit_definition_sha256")
        == source["merit_recipe_loaded_definition_sha256"],
        "recipe": result.get("recipe_sha256")
        == source["merit_recipe_sha256"],
        "input unchanged": result.get("input_model_unchanged") is True,
        "working unchanged": result.get("working_copy_unchanged") is True,
        "connection closed": result.get("connection_closed") is True,
        "no optimization": result.get("optimization_run") is False,
    }
    failed = [name for name, passed in required.items() if not passed]
    if failed:
        raise ValueError(
            "Day 10 baseline approval failed: " + ", ".join(failed)
        )
    return result


def build_summary_row(candidate, result):
    """Flatten one candidate result for CSV and terminal comparison."""

    return {
        "case_id": candidate["case_id"],
        "value_mm": candidate["value_mm"],
        "spot_mean_rms_um": candidate["spot_mean_rms_um"],
        "mtf_30_overall_mean": candidate["mtf_30_overall_mean"],
        "mtf_50_overall_mean": candidate["mtf_50_overall_mean"],
        "merit_value": result["merit_value"],
        "operand_count": result["operand_count"],
        "definition_sha256": result["merit_definition_sha256"],
        "input_model_unchanged": result["input_model_unchanged"],
        "working_copy_unchanged": result["working_copy_unchanged"],
        "connection_closed": result["connection_closed"],
        "optimization_run": result["optimization_run"],
    }


def main():
    config = load_config("configs/day10_merit_function_validation.yaml")
    baseline_config = load_config(config["source"]["baseline_config"])
    validate_execution_lock(config)
    validate_batch_authorization(config)
    validate_merit_definition(config, baseline_config)

    baseline_report_file = find_latest_baseline_report(config)
    baseline_result = validate_baseline_report(config, baseline_report_file)
    tradeoff_report_file = find_latest_day9_tradeoff_report(config)
    _, _, candidates = build_merit_candidate_plan(
        config,
        tradeoff_report_file,
    )

    run_id = datetime.now().strftime("candidate_batch_%Y%m%d_%H%M%S")
    batch_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    batch_dir.mkdir(parents=True, exist_ok=False)

    print("========== DAY 10 REVIEWED CANDIDATE MERIT ==========")
    print(f"Approved by baseline report: {baseline_report_file}")
    print(f"Batch directory: {batch_dir}")
    print("Three candidates run sequentially and stop on the first failure.")
    print("The same frozen 1602-operand recipe is loaded in memory.")
    print("No optimization, refocus or model save will be used.")

    rows = []
    for candidate in candidates:
        case_id = candidate["case_id"]
        print()
        print(f"Running {case_id} ({candidate['value_mm']:.7f} mm)...")
        result, _ = execute_baseline_merit(
            config,
            candidate,
            batch_dir / case_id,
            task_name="day10_candidate_merit_validation",
        )
        if (
            result["merit_definition_sha256"]
            != config["source"]["merit_recipe_loaded_definition_sha256"]
        ):
            raise ValueError(f"{case_id} used a different Merit Function.")
        row = build_summary_row(candidate, result)
        rows.append(row)
        print(f"[PASS] Merit Function value: {row['merit_value']:.12g}")
        print(
            f"[PASS] Operands/fingerprint: {row['operand_count']} / "
            f"{row['definition_sha256']}"
        )
        print("[PASS] Input/working hashes unchanged; connection closed")

    baseline_merit = baseline_result["merit_value"]
    for row in rows:
        row["change_vs_fine_005_percent"] = (
            (row["merit_value"] / baseline_merit) - 1.0
        ) * 100.0
    ranking = sorted(rows, key=lambda row: row["merit_value"])

    csv_file = batch_dir / "candidate_merit_comparison.csv"
    with csv_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary_file = batch_dir / "batch_summary.json"
    summary = {
        "task": "day10_candidate_merit_batch",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "approved_by_baseline_report": str(baseline_report_file),
        "recipe_sha256": config["source"]["merit_recipe_sha256"],
        "loaded_definition_sha256": config["source"][
            "merit_recipe_loaded_definition_sha256"
        ],
        "operand_count": config["source"]["merit_recipe_operand_count"],
        "rows": rows,
        "ranking_low_to_high": [row["case_id"] for row in ranking],
        "best_merit_candidate": ranking[0]["case_id"],
    }
    summary_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("========== DAY 10 MERIT SUMMARY ==========")
    for rank, row in enumerate(ranking, start=1):
        print(
            f"{rank}. {row['case_id']}: thickness={row['value_mm']:.7f} mm, "
            f"merit={row['merit_value']:.12g}, "
            f"vs fine_005={row['change_vs_fine_005_percent']:+.2f}%"
        )
    print(f"[RESULT] Lowest Merit Function: {ranking[0]['case_id']}")
    print("[PASS] All candidates used the identical loaded definition fingerprint")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Comparison CSV: {csv_file}")
    print(f"[PASS] Batch JSON: {summary_file}")


if __name__ == "__main__":
    main()
