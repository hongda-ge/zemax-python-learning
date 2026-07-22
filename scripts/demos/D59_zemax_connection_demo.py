"""D59 real Standalone ZOS-API connection lifecycle demo."""

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.zemax.connection import (  # noqa: E402
    StandaloneZemaxConnection,
)


RESULT_FILE = PROJECT_ROOT / "outputs" / "D59_zosapi_connection_result.json"


def main() -> int:
    connection = None
    exit_code = 1
    result = {
        "test": "D59_zosapi_connection",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "backend": "zemax",
        "simulation_mode": False,
        "status": "failed",
        "connection_closed": False,
    }

    print("Project-X D59 real ZOS-API connection test")
    print("Python executable: {0}".format(sys.executable))
    print("This test will start and then close OpticStudio.")

    try:
        connection = StandaloneZemaxConnection()
        connection_info = connection.info()
        result.update(connection_info)
        result["status"] = "success"
        exit_code = 0

        print("CONNECTION_RESULT")
        print(json.dumps(connection_info, indent=2, ensure_ascii=False))
        print("ZOS-API connection test PASSED")

    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        print("ZOS-API connection test FAILED")
        print("Error type: {0}".format(type(exc).__name__))
        print("Error message: {0}".format(exc))
        traceback.print_exc()

    finally:
        if connection is not None:
            connection.close()
            result["connection_closed"] = connection.closed
            print("OpticStudio connection closed: {0}".format(connection.closed))

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("Result file: {0}".format(RESULT_FILE))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
