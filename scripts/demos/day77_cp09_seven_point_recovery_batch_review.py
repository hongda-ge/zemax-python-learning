"""Generate the offline Day 77 CP09 review for the seven-point batch."""

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


CONFIG_PATH = PROJECT_ROOT / "configs" / "day77_cp09_seven_point_recovery_batch_review.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def prepare_review():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    keys = ("batch_result", "authorization_marker", "retry_approval", "day25_config", "focused_model")
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key in keys}
    checks = {}
    for key, path in paths.items():
        checks[key + "_exists"] = path.is_file()
        checks[key + "_sha256"] = path.is_file() and sha256_file(path) == source[key + "_sha256"]
    batch = json.loads(paths["batch_result"].read_text(encoding="utf-8"))
    marker = json.loads(paths["authorization_marker"].read_text(encoding="utf-8"))
    approval = json.loads(paths["retry_approval"].read_text(encoding="utf-8"))
    criteria = config["review_criteria"]
    rows = batch.get("rows", [])
    checks.update({
        "batch_success": batch.get("status") == "success",
        "all_cases_completed": batch.get("all_cases_completed") is True,
        "case_count": len(rows) == int(criteria["expected_case_count"]),
        "case_ids": [row["case_id"] for row in rows] == criteria["expected_case_ids"],
        "offsets": all(math.isclose(float(row["offset_mm"]), float(expected), abs_tol=1e-12) for row, expected in zip(rows, criteria["expected_offsets_mm"])),
        "acceptance_pattern": [row["balanced_acceptance_pass"] for row in rows] == criteria["expected_acceptance"],
        "connections_closed": batch.get("all_connections_closed") is True and all(row.get("connection_closed") is True for row in rows),
        "model_safety": batch.get("all_model_safety_checks_passed") is True and all(row.get("model_safety_pass") is True for row in rows),
        "forbidden_actions_unused": batch.get("quick_focus_used") is False and batch.get("optimization_used") is False and batch.get("save_as_used") is False,
        "approval_consumed_once": marker.get("status") == "consumed_before_first_zosapi_connection" and marker.get("reusable") is False,
        "approval_scope": approval.get("status") == "success" and int(approval.get("maximum_case_execution_count", 0)) == 7,
        "cp09_pending": batch.get("post_execution_gate") == "CP09_recovery_batch_gate" and batch.get("cp09_manual_review_required") is True,
        "downstream_locked": batch.get("day27_recalculation_released") is False and batch.get("slot6_released") is False,
    })
    raw_evidence = []
    for row in rows:
        result_path = Path(row["result_path"])
        result = json.loads(result_path.read_text(encoding="utf-8"))
        spot = Path(result["spot_text"])
        mtf = Path(result["mtf_text"])
        raw_evidence.append({
            "case_id": row["case_id"],
            "result_path": str(result_path),
            "result_sha256": sha256_file(result_path),
            "spot_path": str(spot),
            "spot_sha256": sha256_file(spot),
            "mtf_path": str(mtf),
            "mtf_sha256": sha256_file(mtf),
        })
    checks["raw_evidence_count"] = len(raw_evidence) == 7
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Day77 CP09 review failed: " + ", ".join(failed))
    return config, paths, batch, checks, raw_evidence


def build_markdown(record):
    rows = "\n".join(
        "- `{0}` `{1:+.3f} mm`: acceptance `{2}`".format(row["case_id"], float(row["offset_mm"]), row["balanced_acceptance_pass"])
        for row in record["cp09_review"]["rows"]
    )
    return """# Day 77 CP09 七点恢复批次复核

## 结论

- 决策：`{decision}`
- 状态：`{status}`
- 程序执行：7/7 成功
- 教学验收：5 PASS / 2 FAIL
- ZOS-API 连接：全部关闭
- 模型安全：全部通过

## 七点结果

{rows}

## 学习重点

程序执行成功表示 API、文件、连接与模型保护链完整；教学验收 FAIL 表示该测量点未同时满足四个冻结阈值。两者不能混为一谈。

本审核只确认 Day 27 离线重算申请资格，不自动重算，也不释放 Slot 6。
""".format(decision=record["decision_id"], status=record["decision_status"], rows=rows)


def main():
    config, paths, batch, checks, raw = prepare_review()
    record = {
        "task": "day77_cp09_seven_point_recovery_batch_review_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["pass_status"],
        "source_batch": {"path": str(paths["batch_result"]), "sha256": config["source"]["batch_result_sha256"], "verified": True},
        "cp09_review": {
            "task_review_status": "PASS",
            "completed_case_count": 7,
            "acceptance_pass_count": sum(1 for row in batch["rows"] if row["balanced_acceptance_pass"]),
            "acceptance_fail_count": sum(1 for row in batch["rows"] if not row["balanced_acceptance_pass"]),
            "rows": batch["rows"],
            "all_connections_closed": True,
            "all_model_safety_checks_passed": True,
            "raw_evidence": raw,
        },
        "checks": checks,
        "permissions": {
            "day76_batch_review_completed": True,
            "day27_recalculation_request_eligible": True,
            "day27_recalculation_released": False,
            "slot6_released": False,
            "additional_zosapi_execution_released": False,
        },
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "day27_recalculated": False,
    }
    names = config["output"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("review_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    markdown_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown(record), encoding="utf-8")
    print("========== DAY 77 CP09 OFFLINE REVIEW ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    print("Decision: {0}".format(record["decision_status"]))
    print("Execution: 7/7; acceptance: 5 PASS / 2 FAIL")
    print("JSON: {0}".format(json_path))
    print("Markdown: {0}".format(markdown_path))
    print("[LOCK] Day27 recalculation and Slot6 remain unreleased")


if __name__ == "__main__":
    main()
