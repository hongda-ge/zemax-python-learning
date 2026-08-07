"""Day 18 step 3: validate paired Spot states at the positive endpoint."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day18_focus_compensation_plan import (  # noqa: E402
    build_endpoint_plan,
    find_latest_day17_reports,
    validate_common_recipe,
    validate_day17_evidence,
    validate_plan_lock,
    validate_source,
)
from scripts.demos.day18_validate_negative_endpoint import (  # noqa: E402
    compare_spot,
    execute_paired_branch,
    print_paired_branch,
    validate_day17_reproduction,
)


def require_positive_endpoint_approval(config):
    """Allow endpoint 002 while endpoint 001 remains locked."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 write": execution["allow_surface2_in_memory_write"],
        "MakeSolveFixed": execution["allow_surface6_make_solve_fixed"],
        "uncompensated Spot": execution[
            "allow_uncompensated_standard_spot"
        ],
        "Quick Focus": execution["allow_quick_focus"],
        "compensated Spot": execution[
            "allow_compensated_standard_spot"
        ],
        "endpoint 002": execution["allow_endpoint_002_execution"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 18 validation not approved: " + ", ".join(missing))
    forbidden = {
        "endpoint 001": execution["allow_endpoint_001_execution"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 18 validation action: " + ", ".join(enabled))


def main():
    config = load_config("configs/day18_focus_compensation_effect.yaml")
    validate_plan_lock(config)
    require_positive_endpoint_approval(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_common_recipe(config, baseline)
    batch_file, analysis_file = find_latest_day17_reports(config)
    validate_day17_evidence(config, batch_file, analysis_file)

    endpoints = build_endpoint_plan(config)
    endpoint = endpoints[1]
    if not math.isclose(endpoint["delta_mm"], 0.4, abs_tol=1e-12):
        raise ValueError("The Day 18 validation endpoint is not +0.4 mm.")

    day17_batch = json.loads(batch_file.read_text(encoding="utf-8"))
    endpoint_evidence = next(
        result
        for result in day17_batch["new_results"]
        if math.isclose(
            float(result["case"]["delta_mm"]),
            endpoint["delta_mm"],
            abs_tol=1e-12,
        )
    )

    run_id = datetime.now().strftime("positive_endpoint_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    endpoint_dir = run_dir / endpoint["directory_name"]
    results = {}

    print("========== DAY 18 POSITIVE-ENDPOINT VALIDATION ==========")
    print("Only endpoint_002 will run; endpoint_001 is locked.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(
        f"Endpoint: {endpoint['value_mm']:.7f} mm "
        f"(delta {endpoint['delta_mm']:+.1f} mm)"
    )
    print("Each branch exports fixed-image Spot, then Quick Focus and focused Spot.")
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        print(f"\nRunning {branch_name}...")
        results[branch_name] = execute_paired_branch(
            config,
            endpoint,
            branch_name,
            endpoint_dir / branch_name,
            source_file,
        )
        print("[PASS] Paired branch completed; connection closed and hashes unchanged")

    reproduction = validate_day17_reproduction(
        config,
        endpoint_evidence,
        results,
    )
    uncompensated_branch_difference = compare_spot(
        results["preserve_solve"]["uncompensated_spot_summary"],
        results["freeze_radius"]["uncompensated_spot_summary"],
    )
    compensated_branch_difference = compare_spot(
        results["preserve_solve"]["compensated_spot_summary"],
        results["freeze_radius"]["compensated_spot_summary"],
    )
    report = {
        "task": "day18_positive_endpoint_validation",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day17_batch_report": str(batch_file),
        "source_day17_analysis_report": str(analysis_file),
        "endpoint": endpoint,
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "day17_reproduction": reproduction,
        "uncompensated_branch_difference": uncompensated_branch_difference,
        "compensated_branch_difference": compensated_branch_difference,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file = run_dir / "positive_endpoint_validation_report.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 18 PAIRED RESULT ==========")
    print_paired_branch(results["preserve_solve"])
    print_paired_branch(results["freeze_radius"])
    print("\nFrozen minus preserve mean RMS difference:")
    print(
        "  Fixed image: "
        f"{uncompensated_branch_difference['mean_difference_um']:+.3f} um"
    )
    print(
        "  After Quick Focus: "
        f"{compensated_branch_difference['mean_difference_um']:+.3f} um"
    )
    print("[PASS] Both focused results reproduced Day 17")
    print("[PASS] Negative endpoint was not re-executed")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
