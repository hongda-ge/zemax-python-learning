"""Day 51 step 2: consume the approved one-time Day 23 baseline control."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day23_residual_defocus_optical_impact_plan import (  # noqa: E402
    validate_day8_evidence,
)
from scripts.demos.day23_validate_baseline_control import (  # noqa: E402
    compare_mtf,
    compare_spot,
    execute_case,
    validate_day9_baseline,
)
from scripts.demos.day51_approved_day23_baseline_control_plan import (  # noqa: E402
    collect_inputs,
    sha256_file,
    validate_execution_contract,
)


def require_reproduction(config, name, difference, limit):
    """Reject a baseline that differs from frozen evidence beyond its limit."""

    if float(difference) > float(limit):
        raise ValueError(
            f"Day 51 {name} reproduction failed: {difference} > {limit}."
        )


def main():
    config = load_config("configs/day51_approved_day23_baseline_control.yaml")
    validate_execution_contract(config)
    inputs = collect_inputs(config)
    day23_config = inputs["day23_config"]
    model_path = inputs["model_path"]
    model_hash = config["source"]["focused_model_sha256"]

    _, day8_case_path = validate_day8_evidence(day23_config, model_path, model_hash)
    day8_case = json.loads(day8_case_path.read_text(encoding="utf-8"))
    day9_path, day9 = validate_day9_baseline(day23_config, model_path, model_hash)
    previous = inputs["previous_control"]
    baseline_config = load_config(day23_config["source"]["baseline_config"])

    frozen_paths = (
        inputs["approval_path"],
        inputs["evidence_path"],
        inputs["day23_config_path"],
        inputs["day8_batch_path"],
        inputs["day8_case_path"],
        inputs["model_path"],
        inputs["day9_path"],
        inputs["previous_path"],
    )
    frozen_hashes = {path: sha256_file(path) for path in frozen_paths}
    stamp = datetime.now().astimezone().strftime(
        config["output"]["execution_directory_prefix"] + "%Y%m%d_%H%M%S"
    )
    run_dir = inputs["output_root"] / stamp
    case_dir = run_dir / config["output"]["case_directory"]

    print("========== DAY 51 APPROVED DAY23 BASELINE CONTROL ==========")
    print("Day50 one-time authorization will be consumed by this execution.")
    print("Only defocus_004 (0.000 mm) will run; six residual cases remain locked.")
    print(f"Focused input model: {model_path}")
    print(f"Output directory: {run_dir}")
    print("One Standalone connection; no Quick Focus, optimization or SaveAs.")

    result, result_path = execute_case(
        day23_config,
        baseline_config,
        inputs["control"],
        case_dir,
        model_path,
        task_name="day51_approved_day23_baseline_control_execution",
        report_name=config["output"]["result_name"],
    )

    spot_day8 = compare_spot(day8_case["spot_metrics"], result["spot_metrics"])
    mtf_day9 = compare_mtf(day9["mtf_metrics"], result["mtf_metrics"])
    spot_previous = compare_spot(previous["spot_metrics"], result["spot_metrics"])
    mtf_previous = compare_mtf(previous["mtf_metrics"], result["mtf_metrics"])
    spot_limit = float(config["guardrails"]["maximum_spot_difference_um"])
    mtf_limit = float(config["guardrails"]["maximum_mtf_difference"])
    require_reproduction(
        config,
        "Day8 Spot",
        spot_day8["maximum_absolute_difference_um"],
        spot_limit,
    )
    require_reproduction(
        config,
        "Day9 MTF",
        mtf_day9["maximum_absolute_difference"],
        mtf_limit,
    )
    require_reproduction(
        config,
        "previous Day23 Spot",
        spot_previous["maximum_absolute_difference_um"],
        spot_limit,
    )
    require_reproduction(
        config,
        "previous Day23 MTF",
        mtf_previous["maximum_absolute_difference"],
        mtf_limit,
    )

    result.update(
        {
            "resource_slot": 2,
            "approval": {
                "path": str(inputs["approval_path"]),
                "sha256": config["source"]["day50_approval_sha256"],
                "decision_id": inputs["approval"]["decision_id"],
                "consumed_once": True,
            },
            "change_specific_evidence": {
                "path": str(inputs["evidence_path"]),
                "sha256": config["source"]["day48_change_evidence_sha256"],
                "positioning_accuracy_mm": config["change_specific_evidence"][
                    "positioning_accuracy_mm"
                ],
                "changed_optical_input": False,
            },
            "source_day8_case_report": str(day8_case_path),
            "source_day9_mtf_report": str(day9_path),
            "source_previous_day23_control": str(inputs["previous_path"]),
            "spot_reproduction_vs_day8": spot_day8,
            "mtf_reproduction_vs_day9": mtf_day9,
            "spot_reproduction_vs_previous_day23": spot_previous,
            "mtf_reproduction_vs_previous_day23": mtf_previous,
            "slot2_baseline_control_completed": True,
            "residual_cases_executed": False,
            "downstream_slots_released": False,
            "engineering_change_approved": False,
            "post_execution_gate": config["guardrails"]["post_execution_gate"],
            "cp09_manual_review_required": True,
        }
    )

    for path, expected_hash in frozen_hashes.items():
        if sha256_file(path) != expected_hash:
            raise ValueError(f"A frozen Day 51 input changed during execution: {path}")
    result["all_frozen_inputs_unchanged"] = True
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[PASS] Day50 approval consumed exactly once")
    print("[PASS] ZOS-API connection and isolated working copy")
    print(f"[PASS] Image distance: {result['surface6_after']['thickness']:.10f} mm")
    for row in result["spot_metrics"]["fields"]:
        print(
            f"[PASS] Field {float(row['field_y_degree']):.1f} deg Spot RMS: "
            f"{float(row['rms_radius_um']):.6f} um"
        )
    for row in result["mtf_summary"]["frequencies"]:
        print(
            f"[PASS] MTF {row['frequency_cyc_per_mm']:.0f} mean/min: "
            f"{row['overall_mean_mtf']:.6f}/{row['minimum_mtf']:.6f}"
        )
    print(
        "[PASS] Maximum previous Spot reproduction difference: "
        f"{spot_previous['maximum_absolute_difference_um']:.9f} um"
    )
    print(
        "[PASS] Maximum previous MTF reproduction difference: "
        f"{mtf_previous['maximum_absolute_difference']:.9f}"
    )
    print("[PASS] Input and disk working-copy hashes unchanged")
    print("[PASS] ZOS-API connection closed")
    print("[PASS] Six residual cases and Slot 3-6 remain locked")
    print("[WAIT] CP09 manual review is required before any residual-case release")
    print(f"[PASS] Slot 2 baseline result: {result_path}")


if __name__ == "__main__":
    main()
