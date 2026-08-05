"""Day 10 repair step: export the reviewed Day 2 MFE as one .MF recipe."""

import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402
from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.merit_ops import read_merit_definition  # noqa: E402
from modules.zemax.model_ops import (  # noqa: E402
    copy_output_model,
    open_working_model,
    sha256_file,
)


def validate_export_authorization(config):
    """Allow recipe export without authorizing optimization or model writes."""

    execution = config["execution"]
    guardrails = config["guardrails"]
    if execution["enabled"] is not False:
        raise ValueError("Generic Day 10 execution must remain disabled.")
    if execution["allow_merit_recipe_export"] is not True:
        raise ValueError("Merit Function recipe export is not approved.")
    if guardrails["do_not_run_optimization"] is not True:
        raise ValueError("The optimization guardrail is not active.")
    if guardrails["do_not_modify_merit_function"] is not True:
        raise ValueError("The Merit Function guardrail is not active.")


def main():
    config = load_config("configs/day10_merit_function_validation.yaml")
    validate_export_authorization(config)
    source = config["source"]
    source_model = (PROJECT_ROOT / source["merit_recipe_source_model"]).resolve()
    recipe_file = (PROJECT_ROOT / source["merit_recipe_file"]).resolve()
    expected_source_hash = source["merit_recipe_source_sha256"].upper()

    if not source_model.is_file():
        raise FileNotFoundError(f"Day 2 Merit Function model not found: {source_model}")
    source_hash_before = sha256_file(source_model).upper()
    if source_hash_before != expected_source_hash:
        raise ValueError("The reviewed Day 2 Merit Function model changed.")
    if recipe_file.exists():
        raise FileExistsError(
            f"Merit Function recipe already exists; refusing overwrite: {recipe_file}"
        )

    run_id = datetime.now().strftime("recipe_export_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / config["output"]["root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_file = run_dir / "recipe_export_result.json"
    copy_info = copy_output_model(
        source_model,
        run_dir,
        working_name="day2_merit_source_working.zmx",
    )
    working_hash_before = sha256_file(copy_info["working_file"])
    result = {
        "task": "day10_export_merit_recipe",
        "status": "failed",
        "time_local": datetime.now().astimezone().isoformat(),
        "source_model": str(source_model),
        "source_sha256_before": source_hash_before,
        "working_copy": copy_info["working_file"],
        "working_sha256_before": working_hash_before,
        "recipe_file": str(recipe_file),
        "connection_closed": False,
        "optimization_run": False,
        "model_saved": False,
    }
    connection = None
    caught_error = None

    print("========== DAY 10 MERIT RECIPE EXPORT ==========")
    print("The Day 2 working model will be read from a copied file.")
    print("Only the Merit Function definition will be exported.")
    print("No optimization, model write or SaveAs will be used.")
    print(f"Source model: {source_model}")
    print(f"Recipe target: {recipe_file}")

    try:
        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()
        open_working_model(connection.system, copy_info["working_file"])
        definition = read_merit_definition(
            connection.system,
            connection.ZOSAPI,
        )
        if definition["operand_count"] <= 1:
            raise ValueError("The Day 2 model has no usable Merit Function.")

        recipe_file.parent.mkdir(parents=True, exist_ok=True)
        connection.system.MFE.SaveMeritFunction(str(recipe_file))
        if not recipe_file.is_file() or recipe_file.stat().st_size <= 0:
            raise RuntimeError("Zemax did not create the Merit Function recipe.")

        result.update(
            {
                "status": "success",
                "operand_count": definition["operand_count"],
                "definition_sha256": definition["definition_sha256"],
                "recipe_sha256": sha256_file(recipe_file),
                "recipe_size_bytes": recipe_file.stat().st_size,
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

        source_hash_after = sha256_file(source_model).upper()
        working_hash_after = sha256_file(copy_info["working_file"])
        result["source_sha256_after"] = source_hash_after
        result["source_unchanged"] = source_hash_after == source_hash_before
        result["working_sha256_after"] = working_hash_after
        result["working_copy_unchanged"] = (
            working_hash_after == working_hash_before
        )

        if caught_error is None:
            safety_checks = {
                "source model changed": result["source_unchanged"] is True,
                "working copy changed": result["working_copy_unchanged"] is True,
                "connection did not close": result["connection_closed"] is True,
                "optimization was run": result["optimization_run"] is False,
                "model was saved": result["model_saved"] is False,
            }
            for message, passed in safety_checks.items():
                if not passed:
                    caught_error = RuntimeError(message)
                    break
        if caught_error is not None:
            result["status"] = "failed"
            result["error"] = {
                "type": type(caught_error).__name__,
                "message": str(caught_error),
            }

        report_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if caught_error is not None:
        raise caught_error

    print("[PASS] ZOS-API connection and copied Day 2 model")
    print(f"Operand count: {result['operand_count']}")
    print(f"Definition SHA256: {result['definition_sha256']}")
    print(f"Recipe SHA256: {result['recipe_sha256']}")
    print(f"Recipe size: {result['recipe_size_bytes']} bytes")
    print("[PASS] Merit Function recipe exported")
    print("[PASS] No optimization or model save was used")
    print("[PASS] Source and working-copy models unchanged")
    print("[PASS] ZOS-API connection closed")
    print(f"[PASS] Result report: {report_file}")


if __name__ == "__main__":
    main()
