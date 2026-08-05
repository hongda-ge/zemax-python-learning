"""Day 10 step 2: load and calculate the frozen MFE for fine_005 only."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.merit_ops import (  # noqa: E402
    calculate_existing_merit_function,
    load_merit_recipe,
)
from modules.zemax.model_ops import (  # noqa: E402
    copy_output_model,
    open_working_model,
    read_surface,
    sha256_file,
)
from scripts.demos.day10_merit_function_plan import (  # noqa: E402
    build_merit_candidate_plan,
    find_latest_day9_tradeoff_report,
    validate_execution_lock,
    validate_merit_definition,
)


def validate_single_authorization(day10_config):
    """Authorize exactly one baseline Merit Function calculation."""

    execution = day10_config["execution"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 10 execution must remain disabled.")
    if execution["allow_single_baseline_validation"] is not True:
        raise ValueError("Single Day 10 baseline validation is not approved.")


def select_baseline_candidate(candidates):
    """Select exactly fine_005, the Day 8 baseline and Spot winner."""

    matches = [
        candidate
        for candidate in candidates
        if candidate["case_id"] == "fine_005"
    ]
    if len(matches) != 1 or matches[0]["is_baseline"] is not True:
        raise ValueError("Unable to identify the fine_005 baseline candidate.")
    return matches[0]


def execute_baseline_merit(
    day10_config,
    candidate,
    case_dir,
    task_name="day10_baseline_merit_validation",
):
    """Calculate one copied model in memory and leave a complete audit report."""

    case_dir.mkdir(parents=True, exist_ok=True)
    result_file = case_dir / candidate["merit_result_name"]
    definition_file = case_dir / "merit_operand_definition.json"
    source = day10_config["source"]
    recipe_file = (PROJECT_ROOT / source["merit_recipe_file"]).resolve()
    recipe_hash = sha256_file(recipe_file).upper()
    if recipe_hash != source["merit_recipe_sha256"].upper():
        raise ValueError("The frozen Merit Function recipe changed.")
    input_hash_before = sha256_file(candidate["focused_model"])
    result = {
        "task": task_name,
        "status": "failed",
        "time_local": datetime.now().astimezone().isoformat(),
        "candidate": candidate,
        "input_model_sha256_before": input_hash_before,
        "connection_closed": False,
        "optimization_run": False,
        "recipe_file": str(recipe_file),
        "recipe_sha256": recipe_hash,
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
        if not math.isclose(
            surface_2["thickness"],
            candidate["value_mm"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("The Merit Function input thickness is incorrect.")

        recipe_load = load_merit_recipe(
            connection.system,
            connection.ZOSAPI,
            recipe_file,
            source["merit_recipe_operand_count"],
            source["merit_recipe_loaded_definition_sha256"],
            strict_definition=True,
        )
        merit = calculate_existing_merit_function(
            connection.system,
            connection.ZOSAPI,
        )
        definition_file.write_text(
            json.dumps(
                {
                    "operand_count": merit["operand_count"],
                    "definition_sha256": merit["definition_sha256"],
                    "operands": merit["operands"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result.update(
            {
                "status": "success",
                "surface_2": surface_2,
                "recipe_load": recipe_load,
                "merit_value": merit["merit_value"],
                "operand_count": merit["operand_count"],
                "merit_definition_sha256": merit["definition_sha256"],
                "merit_definition_unchanged": merit[
                    "definition_unchanged"
                ],
                "operand_definition_file": str(definition_file),
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

        checks = {
            "input model changed": result["input_model_unchanged"] is True,
            "working copy changed on disk": result.get(
                "working_copy_unchanged"
            )
            is True,
            "connection did not close": result["connection_closed"] is True,
            "optimization was run": result["optimization_run"] is False,
        }
        if caught_error is None:
            for message, passed in checks.items():
                if not passed:
                    caught_error = RuntimeError(message)
                    break
        if caught_error is not None:
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }

        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if caught_error is not None:
        raise caught_error
    return result, result_file


def main():
    day10_config = load_config("configs/day10_merit_function_validation.yaml")
    baseline_config = load_config(day10_config["source"]["baseline_config"])
    validate_execution_lock(day10_config)
    validate_single_authorization(day10_config)
    validate_merit_definition(day10_config, baseline_config)

    report_file = find_latest_day9_tradeoff_report(day10_config)
    _, _, candidates = build_merit_candidate_plan(day10_config, report_file)
    candidate = select_baseline_candidate(candidates)
    run_id = datetime.now().strftime("baseline_check_%Y%m%d_%H%M%S")
    case_dir = (
        PROJECT_ROOT
        / day10_config["output"]["root"]
        / run_id
        / candidate["case_id"]
    )

    print("========== DAY 10 BASELINE MERIT VALIDATION ==========")
    print("Only fine_005 will run; fine_003 and fine_004 stay locked.")
    print("The frozen Merit Function recipe will be loaded and calculated once.")
    print("No optimization, refocus, model write or SaveAs will be used.")
    print(f"Input focused model: {candidate['focused_model']}")
    print(f"Output directory: {case_dir.parent}")

    result, result_file = execute_baseline_merit(
        day10_config,
        candidate,
        case_dir,
    )

    print("[PASS] ZOS-API connection and focused working copy")
    print(f"[PASS] Surface 2 thickness: {result['surface_2']['thickness']:.7f} mm")
    print(
        "Merit operands: "
        f"{result['recipe_load']['original_operand_count']} -> "
        f"{result['recipe_load']['loaded_operand_count']}"
    )
    print(f"[PASS] Frozen recipe SHA256: {result['recipe_sha256']}")
    print("[PASS] Merit Function recipe loaded in memory")
    print(
        "Expected loaded definition SHA256: "
        f"{result['recipe_load']['expected_definition_sha256']}"
    )
    print(
        "Loaded definition SHA256: "
        f"{result['recipe_load']['loaded_definition_sha256']}"
    )
    print("[PASS] Loaded Merit Function definition matches the frozen fingerprint")
    print(f"Merit Function value: {result['merit_value']:.12g}")
    print(f"Operand count: {result['operand_count']}")
    print(f"Definition SHA256: {result['merit_definition_sha256']}")
    print("[PASS] Merit Function definition unchanged during calculation")
    print("[PASS] No optimization was run")
    print("[PASS] Day 8 focused input model unchanged")
    print("[PASS] Day 10 working copy unchanged on disk")
    print("[PASS] ZOS-API connection closed")
    print(f"[PASS] Operand definition: {result['operand_definition_file']}")
    print(f"[PASS] Result report: {result_file}")
    print("Day 10 baseline Merit Function validation completed.")


if __name__ == "__main__":
    main()
