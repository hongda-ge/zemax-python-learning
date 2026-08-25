"""Generate the offline Day 80 CP09 review of the Day 79 recalculation."""

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


CONFIG_PATH = PROJECT_ROOT / "configs" / "day80_cp09_day27_recalculation_review.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def prepare_review():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    keys = ("day79_result", "detail_csv", "summary_csv", "authorization_marker", "day78_approval")
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key in keys}
    checks = {}
    for key, path in paths.items():
        checks[key + "_exists"] = path.is_file()
        checks[key + "_sha256"] = path.is_file() and sha256_file(path) == source[key + "_sha256"]
    result = json.loads(paths["day79_result"].read_text(encoding="utf-8"))
    marker = json.loads(paths["authorization_marker"].read_text(encoding="utf-8"))
    approval = json.loads(paths["day78_approval"].read_text(encoding="utf-8"))
    with paths["detail_csv"].open("r", encoding="utf-8-sig", newline="") as stream:
        detail_rows = list(csv.DictReader(stream))
    with paths["summary_csv"].open("r", encoding="utf-8-sig", newline="") as stream:
        summary_rows = list(csv.DictReader(stream))
    criteria = config["review_criteria"]
    failed_details = [row for row in result["details"] if not row["sampled_state_pass"]]
    observed_failed = {row["candidate_id"]: row for row in failed_details}
    expected_failed = criteria["expected_failed_states"]
    failed_state_checks = []
    for candidate_id, expected in expected_failed.items():
        row = observed_failed.get(candidate_id, {})
        failed_state_checks.append(all((
            row.get("state_id") == expected["state_id"],
            math.isclose(float(row.get("measured_offset_mm", 999)), float(expected["measured_offset_mm"]), abs_tol=1e-12),
            row.get("failed_metrics", "").split(";") == expected["failed_metrics"],
        )))
    checks.update({
        "result_success": result.get("status") == "success",
        "approval_consumed_once": marker.get("status") == "consumed_before_offline_recalculation" and marker.get("reusable") is False,
        "approval_valid": approval.get("status") == "success" and approval.get("reusable") is False,
        "combined_count": int(result.get("combined_measured_point_count", 0)) == int(criteria["expected_combined_point_count"]),
        "detail_count_json": len(result.get("details", [])) == int(criteria["expected_detail_state_count"]),
        "detail_count_csv": len(detail_rows) == int(criteria["expected_detail_state_count"]),
        "summary_count_json": len(result.get("summaries", [])) == int(criteria["expected_candidate_count"]),
        "summary_count_csv": len(summary_rows) == int(criteria["expected_candidate_count"]),
        "pass_candidates": result.get("sampled_envelope_pass_candidates") == criteria["expected_pass_candidates"],
        "fail_candidates": result.get("sampled_envelope_fail_candidates") == criteria["expected_fail_candidates"],
        "failed_states_and_metrics": all(failed_state_checks) and len(failed_details) == 2,
        "measured_only": result.get("measured_points_only") is True,
        "no_new_optics": result.get("new_zosapi_connection_created") is False and result.get("new_optical_metric_calculated") is False,
        "no_inference": result.get("interpolation_used") is False and result.get("extrapolation_used") is False and result.get("curve_fit_used") is False,
        "no_continuous_claim": result.get("continuous_acceptance_interval_claimed") is False,
        "no_unique_winner": result.get("unique_engineering_winner") is None,
        "cp09_pending": result.get("post_execution_gate") == "CP09_day27_recalculation_gate" and result.get("cp09_manual_review_required") is True,
        "slot6_locked": result.get("slot6_released") is False,
    })
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Day80 CP09 review failed: " + ", ".join(failed))
    return config, paths, result, checks


def main():
    config, paths, result, checks = prepare_review()
    record = {
        "task": "day80_cp09_day27_recalculation_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["pass_status"],
        "source_day79_result": {"path": str(paths["day79_result"]), "sha256": config["source"]["day79_result_sha256"], "verified": True},
        "cp09_review": {
            "task_review_status": "PASS",
            "combined_measured_point_count": 23,
            "exact_sample_state_count": 12,
            "candidate_count": 4,
            "pass_candidates": result["sampled_envelope_pass_candidates"],
            "fail_candidates": result["sampled_envelope_fail_candidates"],
            "scientific_boundary_preserved": True,
        },
        "checks": checks,
        "permissions": {
            "day79_recalculation_review_completed": True,
            "slot6_release_request_eligible": True,
            "slot6_released": False,
            "new_zosapi_execution_released": False,
            "engineering_change_released": False,
            "continuous_tolerance_claim_released": False,
        },
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "slot6_release_performed": False,
    }
    names = config["output"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    md_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("""# Day 80 CP09 Day 27 重算复核\n\n- 决策：`{0}`\n- 状态：`{1}`\n- 23 个精确实测点、12 个包络状态、4 个命令候选均已复核\n- PASS：`command_002`、`command_003`\n- FAIL：`command_001`、`command_004`\n- 未连接 ZOS-API，未插值、外推或拟合\n- 未声明连续通过区间或唯一工程赢家\n- 只获得 Slot 6 释放申请资格；Slot 6 尚未释放\n""".format(record["decision_id"], record["decision_status"]), encoding="utf-8")
    print("========== DAY 80 CP09 OFFLINE REVIEW ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    print("Decision: {0}".format(record["decision_status"]))
    print("JSON: {0}".format(json_path))
    print("Markdown: {0}".format(md_path))
    print("[LOCK] Slot6 is request-eligible but not released")


if __name__ == "__main__":
    main()
