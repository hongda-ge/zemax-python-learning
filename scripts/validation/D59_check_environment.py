"""D59 Project-X environment preflight check.

This script checks the Python environment and local ZOS-API files only.
It does not launch OpticStudio or consume a Zemax license.
"""

import importlib
import platform
import sys
from importlib import metadata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ZEMAX_INSTALL_DIR = Path(r"L:\Program Files\Zemax2024 R1.03")

EXPECTED_PYTHON = (3, 8)
REQUIRED_IMPORTS = {
    "clr": "pythonnet",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "pandas": "pandas",
    "yaml": "PyYAML",
    "jsonschema": "jsonschema",
    "pycparser": "pycparser",
}
REQUIRED_ZEMAX_DLLS = (
    "ZOSAPI_NetHelper.dll",
    "ZOSAPI.dll",
    "ZOSAPI_Interfaces.dll",
)


def print_check(label, passed, detail):
    """Print one readable PASS/FAIL line and return its status."""
    status = "PASS" if passed else "FAIL"
    print("[{0}] {1}: {2}".format(status, label, detail))
    return passed


def package_version(distribution_name):
    """Return an installed distribution version or a clear fallback."""
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return "not installed"


def main():
    checks = []

    print("Project-X D59 environment preflight")
    print("Project root: {0}".format(PROJECT_ROOT))
    print("Python executable: {0}".format(sys.executable))
    print()

    python_ok = sys.version_info[:2] == EXPECTED_PYTHON
    checks.append(
        print_check(
            "Python version",
            python_ok,
            platform.python_version(),
        )
    )

    architecture = platform.architecture()[0]
    checks.append(
        print_check(
            "Python architecture",
            architecture == "64bit",
            architecture,
        )
    )

    for import_name, distribution_name in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(import_name)
            version = package_version(distribution_name)
            checks.append(
                print_check(import_name, True, "version {0}".format(version))
            )
        except Exception as exc:
            checks.append(
                print_check(import_name, False, "{0}: {1}".format(type(exc).__name__, exc))
            )

    checks.append(
        print_check(
            "Zemax install directory",
            ZEMAX_INSTALL_DIR.is_dir(),
            str(ZEMAX_INSTALL_DIR),
        )
    )

    for dll_name in REQUIRED_ZEMAX_DLLS:
        dll_path = ZEMAX_INSTALL_DIR / dll_name
        checks.append(print_check(dll_name, dll_path.is_file(), str(dll_path)))

    print()
    if all(checks):
        print("Environment preflight PASSED.")
        return 0

    failed_count = len([result for result in checks if not result])
    print("Environment preflight FAILED: {0} check(s) failed.".format(failed_count))
    return 1


if __name__ == "__main__":
    sys.exit(main())
