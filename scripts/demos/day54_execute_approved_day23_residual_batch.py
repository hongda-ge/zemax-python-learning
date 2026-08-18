"""Day 54 step 2: consume Day 53 approval and execute six residual cases."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_run_residual_defocus_batch import build_row  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day54_approved_day23_residual_batch_plan import collect_inputs, sha256_file  # noqa: E402


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def historical_map(report):
    return {row["case_id"]: row for row in report["rows"]}


def reproduction_difference(row, reference):
    spot_keys = ("spot_mean_rms_um", "spot_worst_rms_um")
    mtf_keys = ("mtf30_mean", "mtf30_minimum", "mtf50_mean", "mtf50_minimum")
    return {
        "maximum_spot_summary_difference_um": max(abs(float(row[key]) - float(reference[key])) for key in spot_keys),
        "maximum_mtf_summary_difference": max(abs(float(row[key]) - float(reference[key])) for key in mtf_keys),
    }


def consume_authorization(config, inputs, run_dir):
    marker = inputs["marker"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": "day54_authorization_consumption",
        "status": "consumed_before_zosapi_execution",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(inputs["approval_path"]),
        "approval_sha256": config["source"]["day53_approval_sha256"],
        "decision_id": inputs["approval"]["decision_id"],
        "run_directory": str(run_dir),
        "maximum_batch_execution_count": 1,
        "rerun_released": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return marker


def main():
    config = load_config("configs/day54_approved_day23_residual_batch.yaml")
    inputs = collect_inputs(config)
    baseline_config = load_config(inputs["day23"]["source"]["baseline_config"])
    frozen_paths = (inputs["approval_path"], inputs["baseline_path"], inputs["historical_path"], inputs["day23_path"], inputs["model_path"])
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    stamp = datetime.now().astimezone().strftime(config["output"]["execution_directory_prefix"] + "%Y%m%d_%H%M%S")
    run_dir = inputs["output_root"] / stamp
    marker = consume_authorization(config, inputs, run_dir)
    references = historical_map(inputs["historical"])
    results, rows, reproductions = [], [], []

    print("========== DAY 54 APPROVED DAY23 RESIDUAL BATCH ==========")
    print("Day53 one-time batch authorization has been consumed.")
    print(f"Batch directory: {run_dir}")
    print("Six nonzero cases run sequentially; each uses an independent connection and copy.")
    print("No zero-offset rerun, Quick Focus, optimization or SaveAs.")

    for case in inputs["cases"]:
        print(f"\nRunning {case['case_id']} at offset {float(case['offset_mm']):+.3f} mm...")
        result, result_path = execute_case(inputs["day23"], baseline_config, case, run_dir / case["case_id"], inputs["model_path"], task_name="day54_approved_day23_residual_case", report_name=config["output"]["case_result_name"])
        tolerance = float(config["guardrails"]["numeric_tolerance_mm"])
        if not math.isclose(float(result["surface6_after"]["radius"]), float(inputs["day23"]["reference_state"]["surface6_radius_mm"]), rel_tol=0.0, abs_tol=tolerance):
            raise ValueError(f"{case['case_id']} changed Surface 6 radius.")
        checks = (result.get("connection_closed") is True, result.get("input_model_unchanged") is True, result.get("working_copy_unchanged") is True, result.get("quick_focus_used") is False, result.get("optimization_used") is False, result.get("save_as_used") is False)
        if not all(checks):
            raise ValueError(f"{case['case_id']} failed the safety audit.")
        row = build_row(result, inputs["baseline"])
        diff = reproduction_difference(row, references[case["case_id"]])
        if diff["maximum_spot_summary_difference_um"] > float(config["guardrails"]["maximum_spot_summary_difference_um"]) or diff["maximum_mtf_summary_difference"] > float(config["guardrails"]["maximum_mtf_summary_difference"]):
            raise ValueError(f"{case['case_id']} did not reproduce the frozen Day 23 optical evidence.")
        result.update({"resource_slot": 2, "approval": {"path": str(inputs["approval_path"]), "sha256": config["source"]["day53_approval_sha256"], "decision_id": inputs["approval"]["decision_id"], "consumed_once": True}, "historical_reproduction": diff, "downstream_slots_released": False, "engineering_change_approved": False, "post_execution_gate": config["guardrails"]["post_execution_gate"]})
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(result)
        rows.append(row)
        reproductions.append({"case_id": case["case_id"], **diff})
        print(f"[PASS] Spot mean/worst: {row['spot_mean_rms_um']:.3f}/{row['spot_worst_rms_um']:.3f} um")
        print(f"[PASS] MTF30 mean/min: {row['mtf30_mean']:.4f}/{row['mtf30_minimum']:.4f}")
        print(f"[PASS] MTF50 mean/min: {row['mtf50_mean']:.4f}/{row['mtf50_minimum']:.4f}")
        print("[PASS] Historical reproduction, connection closure and hash audit")

    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / config["output"]["comparison_csv_name"]
    result_path = run_dir / config["output"]["batch_result_name"]
    write_csv(csv_path, rows)
    for path, digest in frozen_hashes.items():
        if sha256_file(path) != digest:
            raise ValueError(f"A frozen Day 54 input changed during execution: {path}")
    report = {
        "task": "day54_approved_day23_residual_batch_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "resource_slot": 2,
        "approval": {"path": str(inputs["approval_path"]), "sha256": config["source"]["day53_approval_sha256"], "decision_id": inputs["approval"]["decision_id"], "consumed_once": True, "consumption_marker": str(marker)},
        "source_model": str(inputs["model_path"]),
        "source_sha256": config["source"]["focused_model_sha256"],
        "source_baseline_result": str(inputs["baseline_path"]),
        "case_count": len(results),
        "case_ids": [result["case"]["case_id"] for result in results],
        "rows": rows,
        "historical_reproduction": reproductions,
        "case_reports": [str(run_dir / result["case"]["case_id"] / config["output"]["case_result_name"]) for result in results],
        "all_connections_closed": all(result["connection_closed"] for result in results),
        "all_input_models_unchanged": all(result["input_model_unchanged"] for result in results),
        "all_working_copies_unchanged": all(result["working_copy_unchanged"] for result in results),
        "all_frozen_inputs_unchanged": True,
        "baseline_rerun_performed": False,
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
        "post_execution_gate": config["guardrails"]["post_execution_gate"],
        "cp09_manual_review_required": True,
    }
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n========== DAY 54 RESIDUAL-BATCH SUMMARY ==========")
    for row in rows:
        print(f"{row['case_id']}: offset={row['offset_mm']:+.3f} mm, Spot mean={row['spot_mean_rms_um']:.3f} um, MTF30={row['mtf30_mean']:.4f}, MTF50={row['mtf50_mean']:.4f}")
    print("[PASS] Day53 approval consumed exactly once")
    print("[PASS] Six nonzero cases completed; zero-offset baseline was not rerun")
    print("[PASS] Historical optical evidence reproduced within frozen tolerances")
    print("[PASS] All connections closed; source and disk copies unchanged")
    print("[PASS] No Quick Focus, optimization, SaveAs or downstream release")
    print("[WAIT] CP09 manual review is required before Slot 3")
    print(f"[PASS] Comparison CSV: {csv_path}")
    print(f"[PASS] Slot 2 batch result: {result_path}")


if __name__ == "__main__":
    main()
