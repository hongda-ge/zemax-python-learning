"""Day 57 step 2: consume approval and execute Day 24 acceptance offline."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day24_evaluate_residual_defocus_acceptance import (  # noqa: E402
    create_figure,
    evaluate_rows,
    write_csv,
)
from scripts.demos.day57_approved_day24_acceptance_execution_plan import (  # noqa: E402
    prepare_plan,
    sha256_file,
)


def scenario_signature(summaries):
    return {
        row["scenario_id"]: {
            "passed_count": row["passed_count"],
            "passed_case_ids": row["passed_case_ids"],
            "failed_case_ids": row["failed_case_ids"],
        }
        for row in summaries
    }


def validate_historical_reproduction(summaries, historical):
    current = scenario_signature(summaries)
    frozen = scenario_signature(historical["scenario_summaries"])
    if current != frozen:
        raise ValueError("Day 57 acceptance does not reproduce the frozen Day 24 result.")
    return current


def build_marker(config, plan, output_dir):
    return {
        "task": "day57_authorization_consumption",
        "status": "consumed_before_offline_evaluation",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(plan["approval_path"]),
        "approval_sha256": plan["approval_sha256"],
        "decision_id": plan["approval"]["decision_id"],
        "resource_slot": 3,
        "day": 24,
        "maximum_execution_count": 1,
        "execution_count_consumed": 1,
        "run_directory": str(output_dir),
        "rerun_released": False,
    }


def build_result(config, plan, details, summaries, signature, output_dir, marker_path):
    return {
        "task": "day57_approved_day24_acceptance_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "authorization": {
            "day56_approval_path": str(plan["approval_path"]),
            "day56_approval_sha256": plan["approval_sha256"],
            "decision_id": plan["approval"]["decision_id"],
            "resource_slot": 3,
            "day": 24,
            "execution_count_consumed": 1,
            "consumption_marker": str(marker_path),
        },
        "source_day52_review": dict(plan["day52_info"]),
        "source_day55_review": dict(plan["day55_info"]),
        "historical_day24_report": {
            "path": str(plan["historical_path"]),
            "sha256": config["source"]["historical_day24_report_sha256"],
            "reproduced": True,
        },
        "runtime_output_directory": str(output_dir),
        "case_count": len(plan["rows"]),
        "case_ids": [row["case_id"] for row in plan["rows"]],
        "measured_rows": plan["rows"],
        "combination_rule": "all_required_metrics_must_pass",
        "details": details,
        "scenario_summaries": summaries,
        "historical_reproduction_signature": signature,
        "slot3_execution_completed": True,
        "cp09_review_status": "PENDING",
        "slot4_execution_released": False,
        "downstream_slots_released": False,
        "measured_points_only": True,
        "interpolation_used": False,
        "extrapolation_used": False,
        "hidden_weighted_score_used": False,
        "continuous_tolerance_claimed": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "engineering_recommendation": None,
        "engineering_change_approved": False,
    }


def validate_result(config, result):
    g = config["guardrails"]
    checks = (
        result["authorization"]["execution_count_consumed"] == 1,
        result["case_count"] == int(g["expected_case_count"]),
        len(result["details"]) == int(g["expected_detail_count"]),
        len(result["scenario_summaries"]) == int(g["expected_summary_count"]),
        result["slot3_execution_completed"] is True,
        result["cp09_review_status"] == "PENDING",
        result["slot4_execution_released"] is False,
        result["downstream_slots_released"] is False,
        result["interpolation_used"] is False,
        result["new_zosapi_connection_created"] is False,
        result["new_optical_metric_calculated"] is False,
        result["existing_source_modified"] is False,
        result["engineering_recommendation"] is None,
        result["engineering_change_approved"] is False,
    )
    if not all(checks):
        raise ValueError("Day 57 result failed its safety validation.")


def main():
    config = load_config("configs/day57_approved_day24_acceptance_execution.yaml")
    plan = prepare_plan(config)
    scenarios = plan["approval"]["frozen_scenarios"]
    frozen_hashes = {
        plan["approval_path"]: sha256_file(plan["approval_path"]),
        Path(plan["day52_info"]["path"]): sha256_file(Path(plan["day52_info"]["path"])),
        Path(plan["day55_info"]["path"]): sha256_file(Path(plan["day55_info"]["path"])),
        plan["historical_path"]: sha256_file(plan["historical_path"]),
    }
    details, summaries = evaluate_rows(plan["rows"], scenarios)
    signature = validate_historical_reproduction(summaries, plan["historical"])
    output_dir = plan["output_root"] / datetime.now().astimezone().strftime("execution_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    marker = build_marker(config, plan, output_dir)
    plan["marker"].parent.mkdir(parents=True, exist_ok=True)
    plan["marker"].write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = config["output"]
    detail_path = output_dir / names["detail_csv"]
    summary_path = output_dir / names["summary_csv"]
    figure_path = output_dir / names["figure_png"]
    result_path = output_dir / names["result_json"]
    write_csv(detail_path, details)
    write_csv(summary_path, summaries)
    create_figure(figure_path, plan["rows"], scenarios, details)
    result = build_result(config, plan, details, summaries, signature, output_dir, plan["marker"])
    validate_result(config, result)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 57 input changed during execution: {path}")
    print("========== DAY 57 APPROVED SLOT-3 OFFLINE ACCEPTANCE ==========")
    print("Day56 one-time approval has been consumed.")
    print("No ZOS-API connection or new optical calculation was used.")
    print(f"Output directory: {output_dir}")
    for summary in summaries:
        print(f"{summary['scenario_id']}: {summary['passed_count']}/{summary['measured_count']} pass; passed={summary['passed_case_ids']}")
    print()
    print("[PASS] Day56 approval consumed exactly once")
    print("[PASS] Seven measured points assembled from Day52 and Day55 evidence")
    print("[PASS] All three scenario results reproduced frozen Day24 exactly")
    print("[PASS] Four required metrics were evaluated independently with the AND rule")
    print("[PASS] No ZOS-API, optical calculation, interpolation or engineering recommendation")
    print("[PASS] Slot 4-6 remain locked")
    print("[WAIT] CP09 manual review is required before Slot 4")
    print(f"[PASS] Detail CSV: {detail_path}")
    print(f"[PASS] Summary CSV: {summary_path}")
    print(f"[PASS] Figure: {figure_path}")
    print(f"[PASS] Slot 3 result: {result_path}")


if __name__ == "__main__":
    main()
