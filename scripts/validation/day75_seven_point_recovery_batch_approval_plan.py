"""Plan-only validation for the Day 75 seven-point batch approval."""

import csv
import hashlib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / "configs" / "day75_seven_point_recovery_batch_approval.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_plan():
    config = load_config(CONFIG_PATH)
    source = config["source"]
    pairs = (
        ("day74_review", "day74_review_sha256"),
        ("migration_review", "migration_review_sha256"),
        ("migration_result", "migration_result_sha256"),
        ("day68_plan", "day68_plan_sha256"),
        ("recovery_case_csv", "recovery_case_csv_sha256"),
        ("day25_config", "day25_config_sha256"),
        ("focused_model", "focused_model_sha256"),
    )
    paths = {key: (PROJECT_ROOT / source[key]).resolve() for key, _ in pairs}
    checks = {}
    for key, hash_key in pairs:
        checks[key + "_exists"] = paths[key].is_file()
        checks[key + "_sha256"] = checks[key + "_exists"] and sha256_file(paths[key]) == source[hash_key]

    day74 = load_json(paths["day74_review"])
    migration_review = load_json(paths["migration_review"])
    migration_result = load_json(paths["migration_result"])
    day68 = load_json(paths["day68_plan"])
    checks.update({
        "day74_pass": day74.get("cp09_review", {}).get("task_review_status") == "PASS",
        "day74_batch_request_eligible": day74.get("permissions", {}).get("seven_point_batch_approval_request_eligible") is True,
        "day74_batch_not_released": day74.get("permissions", {}).get("seven_point_batch_execution_released") is False,
        "migration_pass": migration_review.get("status") == "PASS" and migration_result.get("migration_regression_status") == "PASS",
        "migration_connection_closed": migration_result.get("connection_closed") is True,
        "migration_models_unchanged": migration_result.get("input_model_unchanged") is True and migration_result.get("working_copy_unchanged") is True,
        "day68_seven_cases": int(day68.get("recovery_case_count", 0)) == 7,
        "approval_only": config["execution"]["enabled"] is False and config["execution"]["allow_zosapi_connection"] is False,
    })

    with paths["recovery_case_csv"].open("r", encoding="utf-8-sig", newline="") as stream:
        csv_cases = list(csv.DictReader(stream))
    cases = config["approved_cases"]
    checks["case_count"] = len(cases) == len(csv_cases) == 7
    checks["case_ids"] = [row["case_id"] for row in cases] == [row["case_id"] for row in csv_cases]
    checks["offsets"] = all(math.isclose(float(a["offset_mm"]), float(b["offset_mm"]), abs_tol=1e-12) for a, b in zip(cases, csv_cases))
    checks["targets"] = all(math.isclose(float(a["target_image_distance_mm"]), float(b["target_image_distance_mm"]), abs_tol=1e-12) for a, b in zip(cases, csv_cases))

    contract = config["proposed_execution_contract"]
    checks.update({
        "one_batch": int(contract["maximum_batch_execution_count"]) == 1,
        "seven_case_limit": int(contract["maximum_case_execution_count"]) == 7,
        "single_active_connection": int(contract["maximum_active_zosapi_connections"]) == 1,
        "sequential": contract["run_sequentially"] is True,
        "forbidden_optics": contract["allow_quick_focus"] is False and contract["allow_optimization"] is False and contract["allow_save_as"] is False,
        "zero_control_locked": contract["allow_zero_control_rerun"] is False,
        "cp09_stop": contract["post_execution_gate"] == "CP09_recovery_batch_gate",
        "downstream_locked": config["decision"]["day27_recalculation_released"] is False and config["decision"]["slot6_released"] is False,
    })
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Day75 approval plan failed: " + ", ".join(failed))
    return config, paths, checks


def main():
    config, paths, checks = validate_plan()
    print("========== DAY 75 SEVEN-POINT APPROVAL: PLAN ONLY ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    print("Cases:")
    for case in config["approved_cases"]:
        print("  {0}: {1:+.3f} mm -> {2:.15f} mm".format(case["case_id"], float(case["offset_mm"]), float(case["target_image_distance_mm"])))
    print("Focused model: {0}".format(paths["focused_model"]))
    print("Required future entrypoint: {0}".format(config["proposed_execution_contract"]["required_entrypoint"]))
    print("[LOCK] This plan creates no approval record and no ZOS-API connection")
    print("[LOCK] Day27 recalculation, Slot6, Quick Focus, optimization and SaveAs remain forbidden")
    print("[WAIT] Manual review is required before generating the one-shot approval record")


if __name__ == "__main__":
    main()
