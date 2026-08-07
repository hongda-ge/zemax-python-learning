"""Day 19 step 3: compare FFT MTF before/after focus at +0.4 mm."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day19_focus_compensation_mtf_plan import (  # noqa: E402
    build_experiment_plan,
    find_day18_reports,
    validate_analysis_report,
    validate_endpoint_report,
    validate_execution_lock,
    validate_mtf_recipe,
    validate_source,
)
from scripts.demos.day19_validate_negative_endpoint_mtf import (  # noqa: E402
    compare_mtf,
    execute_paired_branch,
    print_branch,
    validate_day18_reproduction,
)


def require_positive_authorization(config):
    """Authorize all paired actions for endpoint 002 only."""

    execution = config["execution"]
    required = {
        "ZOS-API connection": execution["allow_zosapi_connection"],
        "Surface 2 write": execution["allow_surface2_in_memory_write"],
        "MakeSolveFixed": execution["allow_surface6_make_solve_fixed"],
        "fixed-image FFT MTF": execution["allow_uncompensated_fft_mtf"],
        "Quick Focus": execution["allow_quick_focus"],
        "focused FFT MTF": execution["allow_compensated_fft_mtf"],
        "endpoint 002": execution["allow_endpoint_002_execution"],
    }
    missing = [name for name, value in required.items() if value is not True]
    if missing:
        raise ValueError("Day 19 positive endpoint not approved: " + ", ".join(missing))
    forbidden = {
        "endpoint 001": execution["allow_endpoint_001_execution"],
        "offline analysis": execution["allow_offline_analysis"],
        "optimization": execution["allow_optimization"],
        "SaveAs": execution["allow_save_as"],
    }
    enabled = [name for name, value in forbidden.items() if value is not False]
    if enabled:
        raise ValueError("Forbidden Day 19 action: " + ", ".join(enabled))


def main():
    config = load_config("configs/day19_focus_compensation_mtf.yaml")
    validate_execution_lock(config)
    require_positive_authorization(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_mtf_recipe(config, baseline)
    negative_file, positive_file, analysis_file = find_day18_reports(config)
    negative_report = json.loads(negative_file.read_text(encoding="utf-8"))
    positive_report = json.loads(positive_file.read_text(encoding="utf-8"))
    day18_analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    validate_endpoint_report(
        config,
        negative_report,
        config["source"]["expected_negative_task"],
        -0.4,
    )
    validate_endpoint_report(
        config,
        positive_report,
        config["source"]["expected_positive_task"],
        0.4,
    )
    validate_analysis_report(
        config,
        day18_analysis,
        negative_file,
        positive_file,
    )
    endpoint = build_experiment_plan(config)[1]
    if not math.isclose(endpoint["delta_mm"], 0.4, abs_tol=1e-12):
        raise ValueError("The Day 19 positive endpoint is incorrect.")
    run_dir = (
        PROJECT_ROOT
        / config["output"]["root"]
        / datetime.now().strftime("positive_endpoint_%Y%m%d_%H%M%S")
    )
    endpoint_dir = run_dir / endpoint["directory_name"]
    results = {}

    print("========== DAY 19 POSITIVE-ENDPOINT FFT MTF ==========")
    print("Only endpoint_002 will run; endpoint_001 is locked.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(
        f"Endpoint: {endpoint['value_mm']:.7f} mm "
        f"(delta {endpoint['delta_mm']:+.1f} mm)"
    )
    print("Each branch exports fixed-image MTF, then Quick Focus and focused MTF.")
    print("No optimization or SaveAs will be used.")

    for branch_name in ("preserve_solve", "freeze_radius"):
        print(f"\nRunning {branch_name}...")
        results[branch_name] = execute_paired_branch(
            config,
            baseline,
            endpoint,
            branch_name,
            endpoint_dir / branch_name,
            source_file,
        )
        print("[PASS] Paired branch completed; connection closed and hashes unchanged")

    reproduction = validate_day18_reproduction(config, positive_report, results)
    fixed_branch_difference = compare_mtf(
        results["preserve_solve"]["fixed_image_mtf_summary"],
        results["freeze_radius"]["fixed_image_mtf_summary"],
    )
    focused_branch_difference = compare_mtf(
        results["preserve_solve"]["focused_mtf_summary"],
        results["freeze_radius"]["focused_mtf_summary"],
    )
    report = {
        "task": "day19_positive_endpoint_mtf",
        "status": "success",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_file),
        "source_sha256": source_hash,
        "source_day18_report": str(positive_file),
        "endpoint": endpoint,
        "preserve_solve": results["preserve_solve"],
        "freeze_radius": results["freeze_radius"],
        "day18_reproduction": reproduction,
        "fixed_image_branch_difference": fixed_branch_difference,
        "focused_branch_difference": focused_branch_difference,
        "optimization_used": False,
        "save_as_used": False,
        "unique_engineering_winner": None,
    }
    report_file = run_dir / "positive_endpoint_mtf_report.json"
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== DAY 19 POSITIVE-ENDPOINT RESULT ==========")
    print_branch(results["preserve_solve"])
    print_branch(results["freeze_radius"])
    print("[PASS] Structural and focus states reproduced Day 18")
    print("[PASS] Negative endpoint was not re-executed")
    print("[PASS] No optimization or model save was used")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
