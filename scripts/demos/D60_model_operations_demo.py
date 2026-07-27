"""D60 real model-copy, LDE-read, thickness-change, and save-as demo."""

import argparse
import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.zemax.connection import StandaloneZemaxConnection  # noqa: E402
from modules.zemax.model_ops import (  # noqa: E402
    copy_baseline_model,
    open_working_model,
    read_surface,
    save_model_as,
    set_surface_thickness,
    sha256_file,
)


DEFAULT_MODEL = PROJECT_ROOT / "models" / "Cooke 40 degree field.zmx"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="D60 safe real-Zemax model operation demo"
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help="Baseline model under the project models directory.",
    )
    parser.add_argument(
        "--surface",
        type=int,
        default=3,
        help="Sequential LDE surface number to inspect and modify.",
    )
    parser.add_argument(
        "--delta-mm",
        type=float,
        default=0.1,
        help="Small thickness delta applied only to the working copy.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_id = datetime.now().strftime("D60_%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "outputs" / "D60_model_operations" / run_id
    result_file = run_dir / "result.json"
    run_dir.mkdir(parents=True, exist_ok=False)

    baseline_file = Path(args.model).expanduser().resolve()
    result = {
        "test": "D60_model_operations",
        "run_id": run_id,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "backend": "zemax",
        "simulation_mode": False,
        "status": "failed",
        "connection_closed": False,
        "surface_id": args.surface,
        "delta_mm": args.delta_mm,
    }
    connection = None
    exit_code = 1

    print("Project-X D60 real model operation demo")
    print("Baseline model: {0}".format(baseline_file))
    print("Run directory: {0}".format(run_dir))

    try:
        baseline_hash_before = sha256_file(baseline_file)
        copy_info = copy_baseline_model(
            baseline_file,
            run_dir,
            working_name="working_model.zmx",
        )
        result.update(copy_info)
        result["baseline_sha256_before"] = baseline_hash_before

        connection = StandaloneZemaxConnection()
        result["connection"] = connection.info()

        working_file = Path(copy_info["working_file"])
        open_working_model(connection.system, working_file)

        surface_before = read_surface(connection.system, args.surface)
        requested_thickness = surface_before["thickness"] + args.delta_mm
        thickness_change = set_surface_thickness(
            connection.system,
            args.surface,
            requested_thickness,
        )
        surface_after = read_surface(connection.system, args.surface)

        modified_file = save_model_as(
            connection.system,
            run_dir / "modified_model.zmx",
            run_dir,
        )

        result["surface_before"] = surface_before
        result["thickness_change"] = thickness_change
        result["surface_after"] = surface_after
        result["modified_model"] = str(modified_file)
        result["modified_model_sha256"] = sha256_file(modified_file)
        result["working_model_sha256_after_run"] = sha256_file(working_file)

        # Reload the saved file from disk. This distinguishes an in-memory
        # editor change from a value that was actually persisted by SaveAs.
        open_working_model(connection.system, modified_file)
        surface_reloaded = read_surface(connection.system, args.surface)
        result["surface_reloaded_from_saved_model"] = surface_reloaded
        result["saved_thickness_verified"] = math.isclose(
            surface_reloaded["thickness"],
            thickness_change["actual_thickness"],
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        if not result["saved_thickness_verified"]:
            raise RuntimeError(
                "Reloaded model thickness does not match the saved value."
            )

        baseline_hash_after = sha256_file(baseline_file)
        result["baseline_sha256_after"] = baseline_hash_after
        result["baseline_unchanged"] = (
            baseline_hash_before == baseline_hash_after
        )

        if not result["baseline_unchanged"]:
            raise RuntimeError("Baseline model hash changed during D60 test.")

        result["status"] = "success"
        exit_code = 0
        print("D60 model operation test PASSED")

    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        print("D60 model operation test FAILED")
        print("Error type: {0}".format(type(exc).__name__))
        print("Error message: {0}".format(exc))
        traceback.print_exc()

    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed

        if baseline_file.is_file():
            final_hash = sha256_file(baseline_file)
            result["baseline_sha256_finally"] = final_hash
            before_hash = result.get("baseline_sha256_before")
            if before_hash is not None:
                result["baseline_unchanged"] = before_hash == final_hash

        result_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("Connection closed: {0}".format(result["connection_closed"]))
        print("Baseline unchanged: {0}".format(result.get("baseline_unchanged")))
        print("Result file: {0}".format(result_file))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
