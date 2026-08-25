"""Consume one migration approval and run one zero-offset Spot/MTF control."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_validate_baseline_control import execute_case  # noqa: E402
from scripts.demos.day25_validate_baseline_control import (  # noqa: E402
    compare_control,
    evaluate_balanced,
    observed_summary,
)
from scripts.validation.migration_zero_control_regression_plan import (  # noqa: E402
    CONFIG_PATH,
    sha256_file,
    validate_plan,
)


def maximum_differences(comparison):
    spot = max(abs(float(row["difference"])) for row in comparison if row["metric"].startswith("spot_"))
    mtf = max(abs(float(row["difference"])) for row in comparison if row["metric"].startswith("mtf"))
    return spot, mtf


def main():
    config, paths, expected_hashes, output_root, marker, historical, _ = validate_plan()
    stamp = datetime.now().astimezone().strftime("execution_%Y%m%d_%H%M%S")
    case_dir = output_root / stamp / config["approved_control"]["case_id"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    approval_record = {
        "task": "migration_zero_control_authorization_consumption",
        "status": "consumed_before_zosapi_connection",
        "time_local": datetime.now().astimezone().isoformat(),
        "decision_id": config["approval"]["decision_id"],
        "config_path": str(CONFIG_PATH),
        "config_sha256": sha256_file(CONFIG_PATH),
        "run_directory": str(case_dir.parent),
        "reusable": False,
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(approval_record, stream, ensure_ascii=False, indent=2)

    day25 = load_config(paths["day25"])
    baseline = load_config(PROJECT_ROOT / day25["source"]["baseline_config"])
    control = {
        "case_id": config["approved_control"]["case_id"],
        "offset_mm": 0.0,
        "target_image_distance_mm": config["approved_control"]["target_image_distance_mm"],
        "is_control": True,
        "is_migration_regression": True,
    }
    result, result_path = execute_case(
        day25,
        baseline,
        control,
        case_dir,
        paths["model"],
        task_name="migration_zero_control_regression_execution",
        report_name="migration_zero_control_result.json",
        model_source_kind="baseline",
    )
    observed = observed_summary(result)
    comparison = compare_control(day25, historical["summary_metrics"], observed)
    balanced = evaluate_balanced(day25, observed)
    maximum_spot, maximum_mtf = maximum_differences(comparison)
    acceptance = config["acceptance"]
    passed = all((
        maximum_spot <= float(acceptance["maximum_spot_summary_difference_um"]),
        maximum_mtf <= float(acceptance["maximum_mtf_summary_difference"]),
        all(balanced.values()),
        result.get("connection_closed") is True,
        result.get("input_model_unchanged") is True,
        result.get("working_copy_unchanged") is True,
        result.get("quick_focus_used") is False,
        result.get("optimization_used") is False,
        result.get("save_as_used") is False,
        all(sha256_file(paths[name]) == expected for name, expected in expected_hashes.items()),
    ))
    result.update({
        "migration_regression_status": "PASS" if passed else "REVIEW_REQUIRED",
        "authorization_marker": str(marker),
        "historical_zosapi_version": config["environment"]["historical_zosapi_version"],
        "current_expected_zosapi_version": config["environment"]["current_zosapi_version"],
        "summary_metrics": observed,
        "historical_reproduction": comparison,
        "maximum_historical_spot_difference_um": maximum_spot,
        "maximum_historical_mtf_difference": maximum_mtf,
        "balanced_acceptance_checks": balanced,
        "post_execution_gate": config["post_execution"]["gate"],
        "manual_review_required": True,
        "day75_released": False,
        "seven_point_batch_released": False,
    })
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("========== MIGRATION ZERO CONTROL RESULT ==========")
    print("Status: {0}".format(result["migration_regression_status"]))
    print("Spot max difference: {0:.9f} um".format(maximum_spot))
    print("MTF max difference: {0:.9f}".format(maximum_mtf))
    print("Connection closed: {0}".format(result.get("connection_closed")))
    print("Input model unchanged: {0}".format(result.get("input_model_unchanged")))
    print("Result: {0}".format(result_path))
    print("[WAIT] Manual migration review required; Day75 remains locked")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
