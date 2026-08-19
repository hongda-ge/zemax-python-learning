"""Day 63 step 2: consume Day 62 approval and execute nine boundary cases."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_run_boundary_scan import (  # noqa: E402
    evaluate_balanced,
    flatten_result,
)
from scripts.demos.day25_validate_baseline_control import observed_summary  # noqa: E402
from scripts.demos.day63_approved_day25_boundary_batch_plan import (  # noqa: E402
    collect_inputs,
    sha256_file,
)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def consume_authorization(config, inputs, run_dir):
    marker = inputs["marker"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": "day63_authorization_consumption",
        "status": "consumed_before_zosapi_execution",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(inputs["approval_path"]),
        "approval_sha256": config["source"]["day62_approval_sha256"],
        "decision_id": inputs["approval"]["decision_id"],
        "run_directory": str(run_dir),
        "maximum_batch_execution_count": 1,
        "maximum_case_execution_count": 9,
        "rerun_released": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return marker


def historical_map(report):
    return {row["case_id"]: row for row in report["rows"]}


def reproduction_difference(row, reference):
    spot_keys = ("spot_mean_rms_um", "spot_worst_rms_um")
    mtf_keys = ("mtf30_mean", "mtf30_minimum", "mtf50_mean", "mtf50_minimum")
    return {
        "maximum_spot_summary_difference_um": max(
            abs(float(row[key]) - float(reference[key])) for key in spot_keys
        ),
        "maximum_mtf_summary_difference": max(
            abs(float(row[key]) - float(reference[key])) for key in mtf_keys
        ),
        "acceptance_pass_matches": bool(row["balanced_acceptance_pass"])
        is bool(reference["balanced_acceptance_pass"]),
        "failed_metrics_match": str(row["failed_metrics"]) == str(reference["failed_metrics"]),
    }


def main():
    config = load_config("configs/day63_approved_day25_boundary_batch.yaml")
    inputs = collect_inputs(config)
    baseline = load_config(inputs["day25"]["source"]["baseline_config"])
    frozen_paths = (
        inputs["approval_path"],
        inputs["control_path"],
        inputs["historical_path"],
        inputs["day25_path"],
        inputs["model_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    stamp = datetime.now().astimezone().strftime(
        config["output"]["execution_directory_prefix"] + "%Y%m%d_%H%M%S"
    )
    run_dir = inputs["output_root"] / stamp
    marker = consume_authorization(config, inputs, run_dir)
    references = historical_map(inputs["historical"])
    results, rows, reproductions = [], [], []

    print("========== DAY 63 APPROVED DAY25 BOUNDARY BATCH ==========")
    print("Day62 one-time batch authorization has been consumed.")
    print(f"Batch directory: {run_dir}")
    print("Nine nonzero cases run sequentially; each uses an independent connection and copy.")
    print("No zero-offset rerun, Quick Focus, optimization or SaveAs.")
    print("Acceptance FAIL is recorded and does not stop the batch.")

    for case in inputs["cases"]:
        print(f"\nRunning {case['case_id']} at offset {float(case['offset_mm']):+.3f} mm...")
        result, result_path = execute_case(
            inputs["day25"],
            baseline,
            case,
            run_dir / case["case_id"],
            inputs["model_path"],
            task_name="day63_approved_day25_boundary_case",
            report_name=config["output"]["case_result_name"],
        )
        safety = (
            result.get("connection_closed") is True,
            result.get("input_model_unchanged") is True,
            result.get("working_copy_unchanged") is True,
            result.get("quick_focus_used") is False,
            result.get("optimization_used") is False,
            result.get("save_as_used") is False,
        )
        if not all(safety):
            raise ValueError(f"{case['case_id']} failed the safety audit.")
        metrics = observed_summary(result)
        checks, passed, failed = evaluate_balanced(inputs["day25"], metrics)
        row = flatten_result(case, metrics, checks, passed, failed, result_path)
        diff = reproduction_difference(row, references[case["case_id"]])
        if diff["maximum_spot_summary_difference_um"] > float(config["guardrails"]["maximum_spot_summary_difference_um"]):
            raise ValueError(f"{case['case_id']} did not reproduce historical Spot evidence.")
        if diff["maximum_mtf_summary_difference"] > float(config["guardrails"]["maximum_mtf_summary_difference"]):
            raise ValueError(f"{case['case_id']} did not reproduce historical MTF evidence.")
        if not diff["acceptance_pass_matches"] or not diff["failed_metrics_match"]:
            raise ValueError(f"{case['case_id']} did not reproduce the historical acceptance signature.")
        result.update(
            {
                "resource_slot": 4,
                "approval": {
                    "path": str(inputs["approval_path"]),
                    "sha256": config["source"]["day62_approval_sha256"],
                    "decision_id": inputs["approval"]["decision_id"],
                    "consumed_once": True,
                },
                "summary_metrics": metrics,
                "balanced_acceptance_checks": checks,
                "balanced_acceptance_pass": passed,
                "failed_metrics": failed,
                "historical_reproduction": diff,
                "downstream_slots_released": False,
                "continuous_tolerance_claimed": False,
                "engineering_change_approved": False,
                "post_execution_gate": config["guardrails"]["post_execution_gate"],
            }
        )
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(result)
        rows.append(row)
        reproductions.append({"case_id": case["case_id"], **diff})
        print(f"[PASS] Optical analysis; acceptance={'PASS' if passed else 'FAIL'}" + (f" ({', '.join(failed)})" if failed else ""))
        print(f"  Spot mean/worst={metrics['spot_mean_rms_um']:.6f}/{metrics['spot_worst_rms_um']:.6f} um")
        print(f"  MTF30 mean/min={metrics['mtf30_mean']:.6f}/{metrics['mtf30_minimum']:.6f}")
        print(f"  MTF50 mean/min={metrics['mtf50_mean']:.6f}/{metrics['mtf50_minimum']:.6f}")
        print("  [PASS] Historical reproduction, connection closure and hash audit")

    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / config["output"]["comparison_csv_name"]
    result_path = run_dir / config["output"]["batch_result_name"]
    write_csv(csv_path, rows)
    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 63 input changed during execution: {path}")
    report = {
        "task": "day63_approved_day25_boundary_batch_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "resource_slot": 4,
        "approval": {
            "path": str(inputs["approval_path"]),
            "sha256": config["source"]["day62_approval_sha256"],
            "decision_id": inputs["approval"]["decision_id"],
            "consumed_once": True,
            "consumption_marker": str(marker),
        },
        "source_model": str(inputs["model_path"]),
        "source_sha256": config["source"]["focused_model_sha256"],
        "source_control_result": str(inputs["control_path"]),
        "historical_boundary_batch": str(inputs["historical_path"]),
        "case_count": len(results),
        "case_ids": [result["case"]["case_id"] for result in results],
        "rows": rows,
        "historical_reproduction": reproductions,
        "case_reports": [str(run_dir / result["case"]["case_id"] / config["output"]["case_result_name"]) for result in results],
        "acceptance_pass_count": sum(row["balanced_acceptance_pass"] for row in rows),
        "all_connections_closed": all(result["connection_closed"] for result in results),
        "all_input_models_unchanged": all(result["input_model_unchanged"] for result in results),
        "all_working_copies_unchanged": all(result["working_copy_unchanged"] for result in results),
        "all_frozen_inputs_unchanged": True,
        "baseline_rerun_performed": False,
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "interpolation_used": False,
        "continuous_tolerance_claimed": False,
        "downstream_slots_released": False,
        "engineering_change_approved": False,
        "post_execution_gate": config["guardrails"]["post_execution_gate"],
        "cp09_manual_review_required": True,
    }
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n========== DAY 63 BOUNDARY-BATCH SUMMARY ==========")
    for row in rows:
        print(f"{row['case_id']}: offset={row['offset_mm']:+.3f} mm -> " + ("PASS" if row["balanced_acceptance_pass"] else f"FAIL ({row['failed_metrics']})"))
    print(f"[PASS] Successful optical cases: {len(rows)}")
    print(f"[RESULT] Balanced acceptance passes: {sum(row['balanced_acceptance_pass'] for row in rows)}/{len(rows)}")
    print("[PASS] Day62 approval consumed exactly once")
    print("[PASS] Historical optical and acceptance evidence reproduced")
    print("[PASS] All connections closed; source and disk copies unchanged")
    print("[PASS] No zero-offset rerun, Quick Focus, optimization or SaveAs")
    print("[PASS] Slot 5-6 remain locked; continuous tolerance is NOT claimed")
    print("[WAIT] CP09 manual review is required before Slot 5")
    print(f"[PASS] Comparison CSV: {csv_path}")
    print(f"[PASS] Slot 4 batch result: {result_path}")


if __name__ == "__main__":
    main()
