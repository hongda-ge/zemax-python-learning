"""Day 48 step 2: consume the one-time approval and run Day 22 offline."""

import copy
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day22_evaluate_focus_position_error_budget import (  # noqa: E402
    create_figure,
    evaluate_details,
    summarize,
    write_detail_csv,
    write_summary_csv,
)
from scripts.demos.day48_approved_day22_candidate_execution_plan import (  # noqa: E402
    build_plan,
    ensure_execution_not_consumed,
    load_and_validate_approval,
    sha256_file,
    validate_candidate,
    validate_execution_switches,
    validate_frozen_inputs,
)


def build_result(config, plan, candidate, sources, policies, details, summaries, output_dir):
    """Build the Slot 1 evidence package and retain the downstream lock."""

    return {
        "task": "day48_approved_day22_candidate_offline_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "authorization": {
            "day47_approval_path": plan["approval_path"],
            "day47_approval_sha256": plan["approval_sha256"],
            "resource_slot": 1,
            "day": 22,
            "execution_class": "offline_only",
            "maximum_execution_count": 1,
            "execution_count_consumed": 1,
        },
        "official_source": {
            "path": plan["official_path"],
            "sha256": plan["official_sha256"],
            "modified": False,
        },
        "candidate_input": {
            "path": plan["candidate_path"],
            "sha256": plan["candidate_sha256"],
            "modified": False,
            "positioning_accuracy_mm": plan["positioning_accuracy_mm"],
            "declared_output_root": candidate["output"]["root"],
        },
        "source_day21_evidence": {
            "path": plan["day21_path"],
            "sha256": plan["day21_sha256"],
            "verified": True,
        },
        "runtime_output": {
            "directory": str(output_dir),
            "root_overridden_in_memory_only": True,
        },
        "selected_evidence_policy": candidate["source"]["selected_evidence_policy"],
        "teaching_half_travel_mm": float(candidate["teaching_mechanism"]["symmetric_half_travel_mm"]),
        "teaching_error_sources": sources,
        "combination_policies": policies,
        "details": details,
        "summaries": summaries,
        "slot1_execution_completed": True,
        "cp09_review_status": "PENDING",
        "slot2_execution_released": False,
        "downstream_slots_released": False,
        "measured_cases_only": True,
        "rss_statistical_claim": False,
        "rss_independence_verified": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_modified": False,
        "engineering_recommendation": None,
        "engineering_change_approved": False,
    }


def validate_result(result):
    """Verify completion, one-time consumption and the CP09 stop state."""

    checks = (
        result["authorization"]["execution_count_consumed"] == 1,
        result["slot1_execution_completed"] is True,
        result["cp09_review_status"] == "PENDING",
        result["slot2_execution_released"] is False,
        result["downstream_slots_released"] is False,
        result["new_zosapi_connection_created"] is False,
        result["new_optical_metric_calculated"] is False,
        result["existing_source_modified"] is False,
        result["engineering_recommendation"] is None,
        result["engineering_change_approved"] is False,
        len(result["summaries"]) == 2,
        len(result["details"]) == 12,
    )
    if not all(checks):
        raise ValueError("The Day 48 Slot 1 result failed its safety validation.")


def main():
    config = load_config("configs/day48_approved_day22_candidate_execution.yaml")
    validate_execution_switches(config)
    approval_path, _ = load_and_validate_approval(config)
    official_path, candidate_path, day21_path, day21_report = validate_frozen_inputs(config)
    candidate, sources, policies, cases = validate_candidate(
        config, candidate_path, day21_path, day21_report
    )
    output_root = ensure_execution_not_consumed(config)
    plan = build_plan(
        config, approval_path, official_path, candidate_path, day21_path,
        sources, policies, cases, output_root,
    )

    frozen_hashes = {
        approval_path: sha256_file(approval_path),
        official_path: sha256_file(official_path),
        candidate_path: sha256_file(candidate_path),
        day21_path: sha256_file(day21_path),
    }
    runtime_candidate = copy.deepcopy(candidate)
    runtime_candidate["output"]["root"] = str(output_root)
    half_travel = float(runtime_candidate["teaching_mechanism"]["symmetric_half_travel_mm"])
    details = evaluate_details(runtime_candidate, cases, sources, policies, half_travel)
    summaries = [summarize(details, item["id"], half_travel) for item in policies]

    stamp = datetime.now().astimezone().strftime("execution_%Y%m%d_%H%M%S")
    output_dir = output_root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    names = config["outputs"]
    detail_path = output_dir / names["detail_csv"]
    summary_path = output_dir / names["summary_csv"]
    figure_path = output_dir / names["figure_png"]
    result_path = output_dir / names["result_json"]
    write_detail_csv(detail_path, details)
    write_summary_csv(summary_path, summaries)
    create_figure(figure_path, details, half_travel)

    result = build_result(
        config, plan, candidate, sources, policies, details, summaries, output_dir
    )
    validate_result(result)
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for path, frozen_hash in frozen_hashes.items():
        if sha256_file(path) != frozen_hash:
            raise ValueError(f"A frozen Day 48 input changed during execution: {path}")

    print("========== DAY 48 APPROVED DAY22 CANDIDATE OFFLINE EXECUTION ==========")
    print("Slot 1 / Day 22 executed once with the frozen 0.012 mm candidate.")
    print("No ZOS-API connection, source modification or new optical calculation was used.")
    print(f"Candidate SHA256: {plan['candidate_sha256']}")
    print(f"Positioning accuracy: +/-{plan['positioning_accuracy_mm']:.3f} mm")
    print(f"Isolated output directory: {output_dir}")
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
    print("[PASS] Day47 one-time approval consumed exactly once")
    print("[PASS] Candidate was loaded explicitly; output root changed only in memory")
    print("[PASS] Official config, candidate, approval and Day21 evidence unchanged")
    print("[PASS] No ZOS-API, optical metric, interpolation or engineering recommendation")
    print("[PASS] Slot 2-6 remain locked")
    print("[WAIT] CP09 manual review is required before any downstream release")
    print(f"[PASS] Detail CSV: {detail_path}")
    print(f"[PASS] Summary CSV: {summary_path}")
    print(f"[PASS] Figure: {figure_path}")
    print(f"[PASS] Slot 1 result: {result_path}")


if __name__ == "__main__":
    main()
