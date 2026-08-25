"""Consume the Day75 approval and execute seven recovery cases sequentially."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_validate_baseline_control import evaluate_balanced_checks, observed_summary  # noqa: E402
from scripts.validation.day76_approved_seven_point_recovery_batch_plan import (  # noqa: E402
    CONFIG_PATH,
    sha256_file,
    validate_plan,
)


def main():
    config, paths, approval, cases, marker, _ = validate_plan()
    output_root = PROJECT_ROOT / config["output"]["root"]
    stamp = datetime.now().astimezone().strftime("execution_%Y%m%d_%H%M%S")
    run_dir = output_root / stamp
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker_record = {
        "task": "day76_seven_point_batch_authorization_consumption",
        "status": "consumed_before_first_zosapi_connection",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval_path": str(paths["approval"]),
        "approval_sha256": config["source"]["approval_sha256"],
        "decision_id": approval["decision_id"],
        "run_directory": str(run_dir),
        "reusable": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(marker_record, stream, ensure_ascii=False, indent=2)

    day25 = load_config(paths["day25_config"])
    baseline = load_config(PROJECT_ROOT / day25["source"]["baseline_config"])
    rows = []
    batch_status = "success"
    failure = None
    for index, approved_case in enumerate(cases, start=1):
        case = dict(approved_case)
        case["is_control"] = False
        case["batch_index"] = index
        try:
            result, result_path = execute_case(
                day25,
                baseline,
                case,
                run_dir / case["case_id"],
                paths["focused_model"],
                task_name="day76_approved_seven_point_recovery_case",
                report_name="recovery_case_result.json",
                model_source_kind="baseline",
            )
            summary = observed_summary(result)
            acceptance = evaluate_balanced_checks(day25, summary)
            safety_pass = all((
                result.get("connection_closed") is True,
                result.get("input_model_unchanged") is True,
                result.get("working_copy_unchanged") is True,
                result.get("quick_focus_used") is False,
                result.get("optimization_used") is False,
                result.get("save_as_used") is False,
                sha256_file(paths["focused_model"]) == config["source"]["focused_model_sha256"],
            ))
            if not safety_pass:
                raise RuntimeError("Case safety audit failed: {0}".format(case["case_id"]))
            result.update({
                "authorization_marker": str(marker),
                "summary_metrics": summary,
                "balanced_acceptance_checks": acceptance,
                "balanced_acceptance_pass": all(acceptance.values()),
                "post_execution_gate": config["guardrails"]["post_execution_gate"],
                "day27_recalculation_released": False,
                "slot6_released": False,
            })
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append({
                "case_id": case["case_id"],
                "offset_mm": case["offset_mm"],
                "target_image_distance_mm": case["target_image_distance_mm"],
                "result_path": str(result_path),
                "summary_metrics": summary,
                "balanced_acceptance_checks": acceptance,
                "balanced_acceptance_pass": all(acceptance.values()),
                "connection_closed": True,
                "model_safety_pass": True,
            })
            print("[PASS] {0} {1:+.3f} mm; acceptance={2}".format(case["case_id"], float(case["offset_mm"]), all(acceptance.values())))
        except Exception as exc:
            batch_status = "failed_stopped_on_unexpected_execution_error"
            failure = {"case_id": case["case_id"], "type": type(exc).__name__, "message": str(exc)}
            print("[STOP] {0}: {1}: {2}".format(case["case_id"], type(exc).__name__, exc))
            break

    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / config["output"]["batch_report"]
    report = {
        "task": "day76_approved_seven_point_recovery_batch_execution",
        "status": batch_status,
        "time_local": datetime.now().astimezone().isoformat(),
        "approval": {"path": str(paths["approval"]), "sha256": config["source"]["approval_sha256"], "consumed_once": True, "reusable": False},
        "planned_case_count": 7,
        "completed_case_count": len(rows),
        "rows": rows,
        "failure": failure,
        "all_cases_completed": len(rows) == 7 and failure is None,
        "all_connections_closed": all(row["connection_closed"] for row in rows),
        "all_model_safety_checks_passed": all(row["model_safety_pass"] for row in rows),
        "quick_focus_used": False,
        "optimization_used": False,
        "save_as_used": False,
        "post_execution_gate": config["guardrails"]["post_execution_gate"],
        "cp09_manual_review_required": True,
        "day27_recalculation_released": False,
        "slot6_released": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Batch status: {0}".format(batch_status))
    print("Completed: {0}/7".format(len(rows)))
    print("Result: {0}".format(report_path))
    print("[WAIT] CP09 manual review required; Day27 and Slot6 remain locked")
    if batch_status != "success" or len(rows) != 7:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
