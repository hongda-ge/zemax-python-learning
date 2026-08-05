"""Day 9 step 2: validate FFT MTF on the Day 8 baseline candidate."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.analysis_ops import (  # noqa: E402
    export_fft_mtf_text,
    parse_fft_mtf_text,
)
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.model_ops import (  # noqa: E402
    copy_output_model,
    open_working_model,
    read_surface,
    sha256_file,
)
from scripts.demos.day9_fft_mtf_plan import (  # noqa: E402
    build_candidate_plan,
    find_latest_day8_report,
    validate_analysis_settings,
    validate_execution_lock,
)


def validate_single_authorization(day9_config):
    """Authorize only the best/baseline candidate."""

    execution = day9_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 9 execution must remain disabled.")
    if execution["allow_single_baseline_validation"] is not True:
        raise ValueError("Single Day 9 baseline validation is not approved.")


def select_baseline_candidate(report, candidates):
    """Select exactly the Day 8 best sampled candidate."""

    matches = [
        candidate
        for candidate in candidates
        if candidate["case_id"] == report["best_sampled_case"]
    ]
    if len(matches) != 1 or matches[0]["is_baseline"] is not True:
        raise ValueError("Unable to identify one Day 8 baseline candidate.")
    return matches[0]


def execute_fft_mtf_candidate(
    day9_config,
    baseline_config,
    candidate,
    case_dir,
    task_name,
):
    """Run one isolated FFT MTF case and always leave an audit report."""

    result_file = case_dir / candidate["mtf_result_name"]
    input_hash_before = sha256_file(candidate["focused_model"])
    result = {
        "task": task_name,
        "status": "failed",
        "time_local": datetime.now().astimezone().isoformat(),
        "candidate": candidate,
        "input_model_sha256_before": input_hash_before,
        "connection_closed": False,
    }
    connection = None
    copy_info = None
    working_hash_before = None
    caught_error = None

    try:
        copy_info = copy_output_model(
            candidate["focused_model"],
            case_dir,
            working_name="working_focused_model.zmx",
        )
        working_hash_before = sha256_file(copy_info["working_file"])
        result["working_copy"] = copy_info["working_file"]
        result["working_sha256_before"] = working_hash_before

        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        open_working_model(connection.system, copy_info["working_file"])
        surface_2 = read_surface(connection.system, 2)
        surface_6 = read_surface(connection.system, 6)
        if not math.isclose(
            surface_2["thickness"],
            candidate["value_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("The FFT MTF input thickness is incorrect.")

        mtf_text = export_fft_mtf_text(
            connection.system,
            connection.ZOSAPI,
            case_dir / candidate["mtf_text_name"],
            maximum_frequency=baseline_config["analysis"]["fft_mtf"][
                "maximum_frequency_cyc_per_mm"
            ],
        )
        mtf_metrics = parse_fft_mtf_text(
            mtf_text,
            day9_config["analysis"][
                "evaluation_frequencies_cyc_per_mm"
            ],
        )
        if mtf_metrics["field_count"] != 3:
            raise ValueError("FFT MTF did not return all three fields.")

        result.update(
            {
                "status": "success",
                "surface_2": surface_2,
                "surface_6": surface_6,
                "mtf_text": str(mtf_text),
                "mtf_metrics": mtf_metrics,
            }
        )
    except Exception as exc:
        caught_error = exc
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed

        input_hash_after = sha256_file(candidate["focused_model"])
        result["input_model_sha256_after"] = input_hash_after
        result["input_model_unchanged"] = input_hash_after == input_hash_before

        if copy_info is not None and working_hash_before is not None:
            working_hash_after = sha256_file(copy_info["working_file"])
            result["working_sha256_after"] = working_hash_after
            result["working_copy_unchanged"] = (
                working_hash_after == working_hash_before
            )

        if result["input_model_unchanged"] is not True and caught_error is None:
            caught_error = RuntimeError("Day 8 focused input model changed.")
        if (
            result.get("working_copy_unchanged") is not True
            and caught_error is None
        ):
            caught_error = RuntimeError("Day 9 disk working copy changed.")
        if result["connection_closed"] is not True and caught_error is None:
            caught_error = RuntimeError("ZOS-API connection did not close.")
        if caught_error is not None:
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }

        case_dir.mkdir(parents=True, exist_ok=True)
        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if caught_error is not None:
        raise caught_error
    return result, result_file


def print_candidate_metrics(result):
    """Print the six target-frequency field pairs for one result."""

    for field in result["mtf_metrics"]["fields"]:
        print(f"Field {field['field_y_degree']:.1f} deg:")
        for evaluation in field["evaluations"]:
            print(
                f"  {evaluation['sample_frequency_cyc_per_mm']:.1f} "
                f"cyc/mm: T={evaluation['tangential_mtf']:.4f}, "
                f"S={evaluation['sagittal_mtf']:.4f}, "
                f"mean={evaluation['mean_mtf']:.4f}"
            )


def main():
    day9_config = load_config("configs/day9_fft_mtf_validation.yaml")
    baseline_config = load_config(day9_config["source"]["baseline_config"])
    validate_execution_lock(day9_config)
    validate_single_authorization(day9_config)
    validate_analysis_settings(day9_config, baseline_config)

    day8_report_file = find_latest_day8_report(day9_config)
    day8_report, candidates = build_candidate_plan(
        day9_config,
        day8_report_file,
    )
    candidate = select_baseline_candidate(day8_report, candidates)
    run_id = datetime.now().strftime("baseline_check_%Y%m%d_%H%M%S")
    case_dir = (
        PROJECT_ROOT
        / day9_config["output"]["root"]
        / run_id
        / candidate["case_id"]
    )

    print("========== DAY 9 BASELINE FFT MTF VALIDATION ==========")
    print("Only fine_005 will run; fine_003, fine_004 and fine_006 stay locked.")
    print(f"Input focused model: {candidate['focused_model']}")
    print(f"Output directory: {case_dir.parent}")

    result, result_file = execute_fft_mtf_candidate(
        day9_config,
        baseline_config,
        candidate,
        case_dir,
        task_name="day9_baseline_fft_mtf_validation",
    )

    print("[PASS] ZOS-API connection and focused working copy")
    print(
        f"[PASS] Surface 2 thickness: "
        f"{result['surface_2']['thickness']:.7f} mm"
    )
    print_candidate_metrics(result)
    print("[PASS] Three fields and two target frequencies parsed")
    print("[PASS] Day 8 focused input model unchanged")
    print("[PASS] Day 9 working copy unchanged on disk")
    print("[PASS] ZOS-API connection closed")
    print(f"[PASS] Raw FFT MTF text: {result['mtf_text']}")
    print(f"[PASS] Result report: {result_file}")
    print("Day 9 baseline FFT MTF validation completed.")


if __name__ == "__main__":
    main()
