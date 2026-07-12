# scripts/demos/D58_backend_demo.py

from pathlib import Path
import sys
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.backends.mock_backend import MockBackend
from modules.backends.zemax_backend import ZemaxBackend


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    print("=" * 70)
    print("D58 Backend Demo")
    print("=" * 70)

    run_item = {
        "index": 1,
        "surface": 3,
        "parameter": "thickness",
        "value": 0.2,
        "unit": "mm",
    }

    print("\nStep 1: Run MockBackend")
    mock_backend = MockBackend()
    mock_result = mock_backend.execute_run(run_item)
    print_json(mock_result)

    print("\nStep 2: Run ZemaxBackend placeholder")
    zemax_backend = ZemaxBackend()
    zemax_result = zemax_backend.execute_run(run_item)
    print_json(zemax_result)

    print("\nD58 Backend Demo finished.")


if __name__ == "__main__":
    main()