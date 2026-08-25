"""Consume Day78 approval and recalculate the +/-0.012 mm envelopes offline."""

import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / "configs" / "day79_approved_day27_offline_recalculation.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def failed_metrics(point, limits):
    failed = []
    if float(point["spot_mean_rms_um"]) > float(limits["spot_mean_rms_um_max"]):
        failed.append("spot_mean")
    if float(point["spot_worst_rms_um"]) > float(limits["spot_worst_rms_um_max"]):
        failed.append("spot_worst")
    if float(point["mtf30_minimum"]) < float(limits["mtf30_minimum_min"]):
        failed.append("mtf30_minimum")
    if float(point["mtf50_minimum"]) < float(limits["mtf50_minimum_min"]):
        failed.append("mtf50_minimum")
    return failed


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare_inputs():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key in ("approval", "day25_report", "day76_batch")}
    for key, path in paths.items():
        if not path.is_file() or sha256_file(path) != source[key + "_sha256"]:
            raise RuntimeError("Frozen Day79 source changed: " + key)
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    day25 = json.loads(paths["day25_report"].read_text(encoding="utf-8"))
    day76 = json.loads(paths["day76_batch"].read_text(encoding="utf-8"))
    marker = PROJECT_ROOT / config["output"]["root"] / config["output"]["authorization_marker"]
    checks = (
        approval.get("status") == "success",
        approval.get("decision_status") == "DAY27_OFFLINE_RECALCULATION_APPROVED_FOR_ONE_23_POINT_EVALUATION",
        approval.get("recalculation_executed_by_day78") is False,
        len(day25.get("combined_measured_points", [])) == 16,
        day76.get("all_cases_completed") is True and len(day76.get("rows", [])) == 7,
        not marker.exists(),
        config["execution"]["allow_zosapi_connection"] is False,
        config["execution"]["allow_slot6_release"] is False,
    )
    if not all(checks):
        raise RuntimeError("Day79 plan or authorization check failed.")
    return config, paths, approval, day25, day76, marker


def main():
    config, paths, approval, day25, day76, marker = prepare_inputs()
    output_root = PROJECT_ROOT / config["output"]["root"]
    run_dir = output_root / datetime.now().astimezone().strftime("recalculation_%Y%m%d_%H%M%S")
    marker.parent.mkdir(parents=True, exist_ok=True)
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({
            "task": "day79_offline_recalculation_authorization_consumption",
            "status": "consumed_before_offline_recalculation",
            "time_local": datetime.now().astimezone().isoformat(),
            "approval_path": str(paths["approval"]),
            "approval_sha256": config["source"]["approval_sha256"],
            "decision_id": approval["decision_id"],
            "run_directory": str(run_dir),
            "reusable": False,
        }, stream, ensure_ascii=False, indent=2)

    points = {}
    for item in day25["combined_measured_points"]:
        point = dict(item)
        point["evidence_source"] = "day25_original"
        points[round(float(point["offset_mm"]), 9)] = point
    for row in day76["rows"]:
        summary = row["summary_metrics"]
        point = {
            "source_day": 76,
            "case_id": row["case_id"],
            "offset_mm": float(row["offset_mm"]),
            **summary,
            "balanced_acceptance_pass": row["balanced_acceptance_pass"],
            "failed_metrics": ";".join(name for name, passed in row["balanced_acceptance_checks"].items() if not passed),
            "evidence_source": "day76_recovery",
        }
        key = round(point["offset_mm"], 9)
        if key in points:
            raise RuntimeError("Recovered point duplicates original evidence: {0}".format(key))
        points[key] = point
    if len(points) != 23:
        raise RuntimeError("Combined evidence pool is not exactly 23 unique points.")

    recalc = config["recalculation"]
    limits = recalc["balanced_limits"]
    details = []
    summaries = []
    for index, center in enumerate(recalc["candidate_command_offsets_mm"], start=1):
        candidate_id = "command_{0:03d}".format(index)
        candidate_rows = []
        for state in recalc["relative_positions"]:
            measured = round(float(center) + float(state["relative_offset_mm"]), 9)
            if measured not in points:
                raise RuntimeError("Missing exact measured state: {0:+.3f}".format(measured))
            point = points[measured]
            failed = failed_metrics(point, limits)
            row = {
                "candidate_id": candidate_id,
                "command_offset_mm": float(center),
                "state_id": state["state_id"],
                "relative_offset_mm": float(state["relative_offset_mm"]),
                "measured_offset_mm": measured,
                "source_day": point["source_day"],
                "source_case_id": point["case_id"],
                "evidence_source": point["evidence_source"],
                "spot_mean_rms_um": point["spot_mean_rms_um"],
                "spot_worst_rms_um": point["spot_worst_rms_um"],
                "mtf30_minimum": point["mtf30_minimum"],
                "mtf50_minimum": point["mtf50_minimum"],
                "sampled_state_pass": not failed,
                "failed_metrics": ";".join(failed),
            }
            details.append(row)
            candidate_rows.append(row)
        failed_rows = [row for row in candidate_rows if not row["sampled_state_pass"]]
        summaries.append({
            "candidate_id": candidate_id,
            "command_offset_mm": float(center),
            "teaching_positioning_uncertainty_mm": 0.012,
            "sampled_state_count": 3,
            "passed_sampled_state_count": 3 - len(failed_rows),
            "failed_sampled_state_count": len(failed_rows),
            "sampled_envelope_pass": not failed_rows,
            "failed_state_ids": ";".join(row["state_id"] for row in failed_rows),
            "failed_measured_offsets_mm": ";".join("{0:+.3f}".format(row["measured_offset_mm"]) for row in failed_rows),
            "continuous_interval_pass_claimed": False,
        })

    run_dir.mkdir(parents=True, exist_ok=False)
    detail_path = run_dir / config["output"]["detail_csv"]
    summary_path = run_dir / config["output"]["summary_csv"]
    report_path = run_dir / config["output"]["report"]
    write_csv(detail_path, details)
    write_csv(summary_path, summaries)
    passing = [row["candidate_id"] for row in summaries if row["sampled_envelope_pass"]]
    failing = [row["candidate_id"] for row in summaries if not row["sampled_envelope_pass"]]
    report = {
        "task": "day79_approved_day27_offline_recalculation_execution",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "approval": {"path": str(paths["approval"]), "sha256": config["source"]["approval_sha256"], "consumed_once": True, "reusable": False},
        "original_measured_point_count": 16,
        "recovered_measured_point_count": 7,
        "combined_measured_point_count": 23,
        "teaching_positioning_uncertainty_mm": 0.012,
        "details": details,
        "summaries": summaries,
        "sampled_envelope_pass_candidates": passing,
        "sampled_envelope_fail_candidates": failing,
        "measured_points_only": True,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "interpolation_used": False,
        "extrapolation_used": False,
        "curve_fit_used": False,
        "continuous_acceptance_interval_claimed": False,
        "unique_engineering_winner": None,
        "slot6_released": False,
        "post_execution_gate": config["guardrails"]["post_execution_gate"],
        "cp09_manual_review_required": True,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("========== DAY 79 OFFLINE RECALCULATION ==========")
    for summary in summaries:
        print("{0} {1:+.3f} mm: {2} ({3}/3 states)".format(summary["candidate_id"], summary["command_offset_mm"], "PASS" if summary["sampled_envelope_pass"] else "FAIL", summary["passed_sampled_state_count"]))
    print("PASS candidates: {0}".format(passing))
    print("FAIL candidates: {0}".format(failing))
    print("Report: {0}".format(report_path))
    print("[LOCK] No ZOS-API; CP09 review required; Slot6 remains locked")


if __name__ == "__main__":
    main()
