"""Day 19 step 1: audit and print the FFT MTF compensation plan."""

import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.model_ops import sha256_file  # noqa: E402


def validate_execution_lock(config):
    """Guarantee that the planning step cannot authorize any execution."""

    execution = config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 19 execution must remain disabled.")
    reviewed_flags = (
        "allow_zosapi_connection",
        "allow_surface2_in_memory_write",
        "allow_surface6_make_solve_fixed",
        "allow_uncompensated_fft_mtf",
        "allow_quick_focus",
        "allow_compensated_fft_mtf",
        "allow_endpoint_001_execution",
        "allow_endpoint_002_execution",
        "allow_offline_analysis",
        "allow_optimization",
        "allow_save_as",
    )
    invalid = [
        key for key in reviewed_flags if not isinstance(execution[key], bool)
    ]
    if invalid:
        raise ValueError("Day 19 execution flag is not Boolean: " + ", ".join(invalid))
    if execution["allow_optimization"] is not False:
        raise ValueError("Day 19 optimization must remain forbidden.")
    if execution["allow_save_as"] is not False:
        raise ValueError("Day 19 SaveAs must remain forbidden.")


def validate_source(config):
    """Load the baseline and verify the frozen source model fingerprint."""

    baseline = load_config(config["source"]["baseline_config"])
    source_file = PROJECT_ROOT / baseline["model"]["source_file"]
    if not source_file.is_file():
        raise FileNotFoundError(f"Source model not found: {source_file}")
    source_hash = sha256_file(source_file).upper()
    expected_hash = config["source"]["expected_source_sha256"].upper()
    if source_hash != expected_hash:
        raise ValueError("The frozen Day 19 source model changed.")
    return baseline, source_file, source_hash


def validate_mtf_recipe(config, baseline):
    """Require the reviewed Day 9/baseline FFT MTF definition."""

    planned = config["analysis"]
    frozen = baseline["analysis"]["fft_mtf"]
    keys = (
        "type",
        "sampling",
        "maximum_frequency_cyc_per_mm",
        "evaluation_frequencies_cyc_per_mm",
        "components",
        "fields",
        "wavelengths",
        "surface",
        "polarization",
    )
    mismatches = [key for key in keys if planned[key] != frozen[key]]
    if mismatches:
        raise ValueError("Day 19 FFT MTF recipe mismatch: " + ", ".join(mismatches))


def find_latest_report(root, prefix, filename):
    """Find one latest Day 18 report by stable directory prefix."""

    matches = list(root.glob(f"{prefix}_*/{filename}"))
    if not matches:
        raise FileNotFoundError(f"No Day 18 report found: {filename}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def find_day18_reports(config):
    """Locate the latest negative, positive and offline analysis evidence."""

    source = config["source"]
    root = PROJECT_ROOT / source["day18_output_root"]
    return (
        find_latest_report(root, "negative_endpoint", source["negative_report_name"]),
        find_latest_report(root, "positive_endpoint", source["positive_report_name"]),
        find_latest_report(root, "offline_analysis", source["analysis_report_name"]),
    )


def validate_endpoint_report(config, report, expected_task, expected_delta):
    """Audit one successful and immutable Day 18 endpoint experiment."""

    checks = {
        "task": report.get("task") == expected_task,
        "status": report.get("status") == "success",
        "delta": math.isclose(
            float(report.get("endpoint", {}).get("delta_mm", 99.0)),
            expected_delta,
            abs_tol=1e-12,
        ),
        "source hash": report.get("source_sha256", "").upper()
        == config["source"]["expected_source_sha256"].upper(),
        "no optimization": report.get("optimization_used") is False,
        "no SaveAs": report.get("save_as_used") is False,
        "no winner": report.get("unique_engineering_winner") is None,
    }
    for branch_name in ("preserve_solve", "freeze_radius"):
        branch = report.get(branch_name, {})
        checks[f"{branch_name} success"] = branch.get("status") == "success"
        checks[f"{branch_name} connection"] = branch.get("connection_closed") is True
        checks[f"{branch_name} source"] = branch.get("source_unchanged") is True
        checks[f"{branch_name} copy"] = branch.get("working_copy_unchanged") is True
        checks[f"{branch_name} no optimization"] = branch.get("optimization_used") is False
        checks[f"{branch_name} no SaveAs"] = branch.get("save_as_used") is False
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 18 endpoint evidence failed: " + ", ".join(failed))


def validate_analysis_report(config, report, negative_file, positive_file):
    """Require the completed two-endpoint Day 18 conclusion and provenance."""

    checks = {
        "task": report.get("task") == config["source"]["expected_analysis_task"],
        "status": report.get("status") == "success",
        "negative source": Path(report.get("source_negative_report", "")).resolve()
        == negative_file.resolve(),
        "positive source": Path(report.get("source_positive_report", "")).resolve()
        == positive_file.resolve(),
        "two rows": len(report.get("rows", [])) == 2,
        "no ZOS-API": report.get("new_zosapi_connection_created") is False,
        "no optical calculation": report.get("new_optical_metric_calculated") is False,
        "no winner": report.get("unique_engineering_winner") is None,
        "strong attenuation": float(
            report.get("minimum_branch_difference_attenuation_percent", -1.0)
        )
        >= 98.0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 18 analysis evidence failed: " + ", ".join(failed))


def build_experiment_plan(config):
    """Expand two endpoints into four paired branch tasks."""

    experiments = []
    deltas = config["parameter"]["endpoint_deltas_mm"]
    values = config["parameter"]["endpoint_values_mm"]
    for index, (delta, value) in enumerate(zip(deltas, values), start=1):
        endpoint_id = f"endpoint_{index:03d}"
        experiments.append(
            {
                "endpoint_id": endpoint_id,
                "value_mm": float(value),
                "delta_mm": float(delta),
                "directory_name": endpoint_id + "_" + f"{value:.3f}".replace(".", "p"),
                "branches": ["preserve_solve", "freeze_radius"],
            }
        )
    if len(experiments) != int(config["comparison"]["endpoint_count"]):
        raise ValueError("Day 19 endpoint count is incorrect.")
    return experiments


def main():
    config = load_config("configs/day19_focus_compensation_mtf.yaml")
    validate_execution_lock(config)
    baseline, source_file, source_hash = validate_source(config)
    validate_mtf_recipe(config, baseline)
    negative_file, positive_file, analysis_file = find_day18_reports(config)
    negative = json.loads(negative_file.read_text(encoding="utf-8"))
    positive = json.loads(positive_file.read_text(encoding="utf-8"))
    analysis_report = json.loads(analysis_file.read_text(encoding="utf-8"))
    validate_endpoint_report(
        config,
        negative,
        config["source"]["expected_negative_task"],
        -0.4,
    )
    validate_endpoint_report(
        config,
        positive,
        config["source"]["expected_positive_task"],
        0.4,
    )
    validate_analysis_report(
        config,
        analysis_report,
        negative_file,
        positive_file,
    )
    experiments = build_experiment_plan(config)
    mtf = config["analysis"]

    print("========== DAY 19 FOCUS-COMPENSATION FFT MTF PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical analysis will be created.")
    print(f"Source model: {source_file}")
    print(f"Source SHA256: {source_hash}")
    print(f"Day 18 negative evidence: {negative_file}")
    print(f"Day 18 positive evidence: {positive_file}")
    print(f"Day 18 analysis evidence: {analysis_file}")
    print(
        "FFT MTF frequencies: "
        + ", ".join(
            f"{frequency:.0f} cycles/mm"
            for frequency in mtf["evaluation_frequencies_cyc_per_mm"]
        )
    )
    print("Components: tangential and sagittal; fields/wavelengths: all")
    print()

    for experiment in experiments:
        print(
            f"{experiment['endpoint_id']}: {experiment['value_mm']:.7f} mm, "
            f"delta {experiment['delta_mm']:+.1f} mm"
        )
        for branch_name in experiment["branches"]:
            print(
                f"  {branch_name}: fixed-image FFT MTF -> "
                "Quick Focus -> focused FFT MTF"
            )

    print()
    print("Planned workload after approval:")
    print(f"  independent branch models: {config['comparison']['branch_model_count']}")
    print(f"  FFT MTF exports: {config['comparison']['fft_mtf_export_count']}")
    print(f"  Quick Focus runs: {config['comparison']['quick_focus_run_count']}")
    print()
    print("[PASS] Frozen source model verified")
    print("[PASS] Both Day 18 endpoint experiments and safety audits verified")
    print("[PASS] Day 18 offline conclusion and provenance verified")
    print("[PASS] FFT MTF recipe matches the frozen baseline settings")
    print("[PASS] Fixed-image and focused states declared for both branches")
    print("[PASS] Optimization, SaveAs, hidden score and winner forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
