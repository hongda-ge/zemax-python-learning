"""Plan-only validation for the approved Day 76 recovery batch."""

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / "configs" / "day76_approved_seven_point_recovery_batch_retry_02.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_plan():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key in ("approval", "day25_config", "focused_model")}
    checks = {}
    for key, path in paths.items():
        checks[key + "_exists"] = path.is_file()
        checks[key + "_sha256"] = path.is_file() and sha256_file(path) == source[key + "_sha256"]
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    cases = approval.get("approved_cases", [])
    marker = PROJECT_ROOT / config["output"]["root"] / config["output"]["authorization_marker"]
    execution = config["execution"]
    checks.update({
        "approval_success": approval.get("status") == "success",
        "approval_decision": approval.get("decision_status") == "SEVEN_POINT_BATCH_APPROVED_FOR_ONE_RETRY_AFTER_PRE_CONNECTION_POLICY_FIX",
        "approval_not_executed": approval.get("reusable") is False,
        "seven_cases": len(cases) == 7,
        "nonzero_cases": all(float(case["offset_mm"]) != 0.0 for case in cases),
        "ascending_cases": [float(case["offset_mm"]) for case in cases] == sorted(float(case["offset_mm"]) for case in cases),
        "execution_enabled": execution["enabled"] is True,
        "one_batch": int(execution["maximum_batch_execution_count"]) == 1,
        "seven_case_limit": int(execution["maximum_case_execution_count"]) == 7,
        "single_connection": int(execution["maximum_active_zosapi_connections"]) == 1,
        "sequential": execution["run_sequentially"] is True,
        "forbidden_actions_locked": execution["allow_quick_focus"] is False and execution["allow_optimization"] is False and execution["allow_save_as"] is False,
        "downstream_locked": execution["allow_day27_recalculation"] is False and execution["allow_slot6_release"] is False,
        "authorization_unconsumed": not marker.exists(),
    })
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Day76 plan failed: " + ", ".join(failed))
    return config, paths, approval, cases, marker, checks


def main():
    config, paths, _, cases, marker, checks = validate_plan()
    print("========== DAY 76 SEVEN-POINT BATCH: PLAN ONLY ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    for case in cases:
        print("  {0}: {1:+.3f} mm".format(case["case_id"], float(case["offset_mm"])))
    print("Model: {0}".format(paths["focused_model"]))
    print("One-time marker: {0}".format(marker))
    print("[LOCK] No zero control, Quick Focus, optimization, SaveAs or downstream release")
    print("[WAIT] Approved batch may now consume authorization once")


if __name__ == "__main__":
    main()
