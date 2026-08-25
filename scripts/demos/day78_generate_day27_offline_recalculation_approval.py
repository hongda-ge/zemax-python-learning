"""Validate and generate the offline-only Day 78 recalculation approval."""

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


CONFIG_PATH = PROJECT_ROOT / "configs" / "day78_day27_offline_recalculation_approval.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def prepare_plan():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    keys = ("day77_review", "day76_batch", "day68_plan", "recovery_case_csv", "day25_report")
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key in keys}
    checks = {}
    for key, path in paths.items():
        checks[key + "_exists"] = path.is_file()
        checks[key + "_sha256"] = path.is_file() and sha256_file(path) == source[key + "_sha256"]
    day77 = json.loads(paths["day77_review"].read_text(encoding="utf-8"))
    day76 = json.loads(paths["day76_batch"].read_text(encoding="utf-8"))
    day68 = json.loads(paths["day68_plan"].read_text(encoding="utf-8"))
    day25 = json.loads(paths["day25_report"].read_text(encoding="utf-8"))
    contract = config["approved_recalculation_contract"]
    checks.update({
        "day77_pass": day77.get("cp09_review", {}).get("task_review_status") == "PASS",
        "recalculation_request_eligible": day77.get("permissions", {}).get("day27_recalculation_request_eligible") is True,
        "day76_seven_complete": day76.get("all_cases_completed") is True and len(day76.get("rows", [])) == 7,
        "day68_uncertainty": math.isclose(float(day68["positioning_uncertainty_mm"]), 0.012, abs_tol=1e-12),
        "day68_recovery_count": int(day68["recovery_case_count"]) == 7,
        "day25_original_count": int(day25["measured_point_count"]) == 16,
        "combined_count": int(contract["combined_measured_point_count"]) == 23,
        "offline_only": contract["execution_class"] == "offline_only" and contract["allow_zosapi_connection"] is False,
        "exact_samples": contract["require_exact_measured_states"] is True,
        "no_inference": contract["interpolation_allowed"] is False and contract["extrapolation_allowed"] is False and contract["curve_fit_allowed"] is False,
        "no_continuous_claim": contract["continuous_interval_claim_allowed"] is False,
        "slot6_locked": config["decision"]["slot6_released"] is False,
        "day78_does_not_recalculate": config["execution"]["allow_day27_recalculation_by_day78"] is False,
    })
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Day78 approval plan failed: " + ", ".join(failed))
    return config, paths, checks


def main():
    config, paths, checks = prepare_plan()
    print("========== DAY 78 DAY27 RECALCULATION APPROVAL: PLAN ONLY ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    contract = config["approved_recalculation_contract"]
    record = {
        "task": "day78_day27_offline_recalculation_approval_generation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["decision"]["decision_id"],
        "decision_status": config["decision"]["decision_status"],
        "approved_by": config["decision"]["approved_by"],
        "frozen_sources": {key: {"path": str(path), "sha256": config["source"][key + "_sha256"], "verified": True} for key, path in paths.items()},
        "approved_recalculation_contract": contract,
        "permissions": {
            "one_day27_offline_recalculation_released": True,
            "zosapi_execution_released": False,
            "new_optical_calculation_released": False,
            "interpolation_released": False,
            "continuous_tolerance_claim_released": False,
            "slot6_released": False,
        },
        "recalculation_executed_by_day78": False,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "reusable": False,
    }
    names = config["output"]
    output_dir = PROJECT_ROOT / names["root"] / datetime.now().astimezone().strftime("approval_%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / names["json"]
    md_path = output_dir / names["markdown"]
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("""# Day 78 Day 27 离线重算审批\n\n- 决策：`{0}`\n- 状态：`{1}`\n- 范围：原 16 点 + 新 7 点 = 23 个精确实测点\n- 教学定位误差：`±0.012 mm`\n- 四个命令中心：`0.000 / 0.010 / 0.020 / 0.030 mm`\n- 仅允许一次离线重算，不连接 ZOS-API\n- 禁止插值、外推、拟合、连续公差与唯一工程赢家声明\n- Slot 6 仍锁定\n""".format(record["decision_id"], record["decision_status"]), encoding="utf-8")
    print("Decision: {0}".format(record["decision_status"]))
    print("Approved: one offline 23-point recalculation; ZOS-API=False")
    print("JSON: {0}".format(json_path))
    print("Markdown: {0}".format(md_path))
    print("[LOCK] Recalculation not executed by Day78; Slot6 remains locked")


if __name__ == "__main__":
    main()
