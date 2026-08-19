"""Day 57 step 1: validate the approved offline acceptance execution plan."""

import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path, expected_hash, expected_task):
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise ValueError(f"Frozen Day 57 evidence changed: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("task") != expected_task or report.get("status") != "success":
        raise ValueError(f"Frozen Day 57 evidence metadata is invalid: {path}")
    return report


def validate_switches(config):
    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 57 execution switch must be Boolean.")
    allowed = {"enabled", "allow_offline_acceptance_evaluation", "allow_isolated_output_write"}
    if any(execution.get(key) is not True for key in allowed):
        raise ValueError("Day 57 offline execution is not fully enabled.")
    if any(value is not False for key, value in execution.items() if key not in allowed):
        raise ValueError("Day 57 enabled a forbidden action.")


def validate_approval(config):
    source = config["source"]
    path = (PROJECT_ROOT / source["day56_approval"]).resolve()
    approval = load_json(path, source["day56_approval_sha256"], source["expected_day56_task"])
    contract = approval["approved_execution_contract"]
    checks = (
        approval.get("decision_id") == source["expected_decision_id"],
        approval.get("decision_status") == source["expected_decision_status"],
        approval.get("permissions", {}).get("slot_03_offline_acceptance_execution_released") is True,
        approval.get("permissions", {}).get("zosapi_execution_released") is False,
        approval.get("approved_task_executed_by_day56") is False,
        int(contract["resource_slot"]) == 3,
        int(contract["day"]) == 24,
        contract["execution_class"] == "offline_only",
        int(contract["maximum_execution_count"]) == 1,
        contract["required_entrypoint"] == "scripts/demos/day57_execute_approved_day24_acceptance.py",
    )
    if not all(checks):
        raise ValueError("Day 56 approval does not release this Day 57 execution.")
    return path, approval


def extract_row(case_report):
    case = case_report["case"]
    frequencies = {float(row["frequency_cyc_per_mm"]): row for row in case_report["mtf_summary"]["frequencies"]}
    return {
        "case_id": case["case_id"],
        "offset_mm": float(case["offset_mm"]),
        "spot_mean_rms_um": float(case_report["spot_summary"]["equal_field_mean_rms_um"]),
        "spot_worst_rms_um": float(case_report["spot_summary"]["worst_field_rms_um"]),
        "mtf30_mean": float(frequencies[30.0]["overall_mean_mtf"]),
        "mtf30_minimum": float(frequencies[30.0]["minimum_mtf"]),
        "mtf50_mean": float(frequencies[50.0]["overall_mean_mtf"]),
        "mtf50_minimum": float(frequencies[50.0]["minimum_mtf"]),
    }


def validate_case_report(path, expected_hash, expected_id, expected_offset):
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise ValueError(f"Frozen case evidence changed: {expected_id}")
    report = json.loads(path.read_text(encoding="utf-8"))
    checks = (
        report.get("status") == "success",
        report.get("case", {}).get("case_id") == expected_id,
        math.isclose(float(report["case"]["offset_mm"]), float(expected_offset), abs_tol=1e-12),
        report.get("connection_closed") is True,
        report.get("input_model_unchanged") is True,
        report.get("working_copy_unchanged") is True,
        report.get("quick_focus_used") is False,
        report.get("optimization_used") is False,
        report.get("save_as_used") is False,
    )
    if not all(checks):
        raise ValueError(f"Frozen case evidence is unsafe: {expected_id}")
    return report


def assemble_rows(approval):
    ids = approval["approved_execution_contract"]["expected_case_ids"]
    offsets = [float(x) for x in approval["approved_execution_contract"]["expected_offsets_mm"]]
    day52_info = approval["source_day52_review"]
    day55_info = approval["source_day55_review"]
    day52 = load_json(Path(day52_info["path"]), day52_info["sha256"], "day52_cp09_slot2_baseline_review_generation")
    day55 = load_json(Path(day55_info["path"]), day55_info["sha256"], "day55_cp09_slot2_residual_batch_review_generation")
    audits = {row["case_id"]: row for row in day55["cp09_review"]["case_audits"]}
    baseline_path = Path(day52["source_day51_result"]["path"])
    reports = {}
    reports["defocus_004"] = validate_case_report(
        baseline_path, day52["source_day51_result"]["sha256"], "defocus_004", 0.0
    )
    for case_id, audit in audits.items():
        reports[case_id] = validate_case_report(
            Path(audit["case_report_path"]), audit["case_report_sha256"], case_id, audit["offset_mm"]
        )
    if set(reports) != set(ids):
        raise ValueError("Day 52/55 evidence does not assemble exactly seven cases.")
    rows = [extract_row(reports[case_id]) for case_id in ids]
    if [row["offset_mm"] for row in rows] != offsets:
        raise ValueError("Assembled offsets do not match the Day 56 contract.")
    return rows, day52_info, day55_info


def validate_historical(config):
    source = config["source"]
    path = (PROJECT_ROOT / source["historical_day24_report"]).resolve()
    return path, load_json(path, source["historical_day24_report_sha256"], source["expected_historical_task"])


def ensure_not_consumed(config):
    root = (PROJECT_ROOT / config["output"]["root"]).resolve()
    marker = root / f"{config['authorization']['marker_prefix']}.json"
    if marker.exists() or list(root.glob("execution_*/slot3_acceptance_result.json")):
        raise ValueError("The Day 56 one-time approval has already been consumed.")
    return root, marker


def prepare_plan(config):
    validate_switches(config)
    approval_path, approval = validate_approval(config)
    rows, day52_info, day55_info = assemble_rows(approval)
    historical_path, historical = validate_historical(config)
    root, marker = ensure_not_consumed(config)
    return {
        "approval_path": approval_path,
        "approval": approval,
        "approval_sha256": config["source"]["day56_approval_sha256"],
        "rows": rows,
        "day52_info": day52_info,
        "day55_info": day55_info,
        "historical_path": historical_path,
        "historical": historical,
        "output_root": root,
        "marker": marker,
    }


def print_introduction(config):
    intro = config["teaching_introduction"]
    print("========== TODAY'S INTRODUCTION ==========")
    print(f"Why today: {intro['why_today']}")
    print(f"Link to yesterday: {intro['relation_to_previous_day']}")
    print("Core concepts:")
    for concept in intro["concepts"]:
        print(f"  - {concept}")
    print(f"Completion standard: {intro['completion_standard']}")
    print()


def main():
    config = load_config("configs/day57_approved_day24_acceptance_execution.yaml")
    plan = prepare_plan(config)
    print_introduction(config)
    print("========== DAY 57 APPROVED DAY24 ACCEPTANCE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No authorization will be consumed and no acceptance output will be created.")
    print("Approved scope: Slot 3 / Day 24 / seven measured cases / one offline execution")
    for row in plan["rows"]:
        print(f"  {row['case_id']}: offset={row['offset_mm']:+.3f} mm, Spot={row['spot_mean_rms_um']:.3f} um, MTF30min={row['mtf30_minimum']:.4f}, MTF50min={row['mtf50_minimum']:.4f}")
    print(f"Authorization marker: {plan['marker']}")
    print(f"Isolated output root: {plan['output_root']}")
    print("Stop after execution: CP09_slot_gate")
    print()
    print("[PASS] Frozen Day56 one-time approval verified")
    print("[PASS] Day52 control and Day55 six-case evidence assembled into seven points")
    print("[PASS] Historical Day24 result and three teaching scenarios verified")
    print("[PASS] No prior marker or result has consumed this approval")
    print("[PASS] ZOS-API, new optical calculation, interpolation and Slot 4-6 remain locked")
    print("PLAN ONLY finished. No output, authorization consumption or calculation was created.")


if __name__ == "__main__":
    main()
