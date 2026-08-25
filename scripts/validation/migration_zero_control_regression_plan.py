"""Plan-only validation for the one-shot migration zero-control regression."""

import hashlib
import json
import platform
import sys
from importlib import metadata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / "configs" / "migration_zero_control_regression_retry_request.yaml"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def collect_inputs(config):
    source = config["source"]
    paths = {
        "model": PROJECT_ROOT / source["focused_model"],
        "day25": PROJECT_ROOT / source["day25_config"],
        "historical": PROJECT_ROOT / source["historical_day73_result"],
        "spot": PROJECT_ROOT / source["historical_spot"],
        "mtf": PROJECT_ROOT / source["historical_mtf"],
    }
    expected_hashes = {
        "model": source["focused_model_sha256"],
        "historical": source["historical_day73_result_sha256"],
        "spot": source["historical_spot_sha256"],
        "mtf": source["historical_mtf_sha256"],
    }
    output_root = PROJECT_ROOT / config["output"]["root"]
    marker = output_root / config["output"]["authorization_marker"]
    historical = json.loads(paths["historical"].read_text(encoding="utf-8"))
    return paths, expected_hashes, output_root, marker, historical


def validate_plan():
    config = load_config(CONFIG_PATH)
    paths, expected_hashes, output_root, marker, historical = collect_inputs(config)
    checks = {
        "execution_enabled": config["execution"]["enabled"] is True,
        "approved_once": config["case"]["status"] == "approved_for_one_migration_regression",
        "python_version": platform.python_version() == config["environment"]["expected_python"],
        "pythonnet_version": metadata.version("pythonnet") == config["environment"]["expected_pythonnet"],
        "authorization_unconsumed": not marker.exists(),
        "historical_success": historical.get("status") == "success",
        "historical_connection_closed": historical.get("connection_closed") is True,
    }
    for name, path in paths.items():
        checks[name + "_exists"] = path.is_file()
    for name, expected in expected_hashes.items():
        checks[name + "_sha256"] = paths[name].is_file() and sha256_file(paths[name]) == expected
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError("Migration regression plan failed: " + ", ".join(failed))
    return config, paths, expected_hashes, output_root, marker, historical, checks


def main():
    config, paths, _, output_root, marker, _, checks = validate_plan()
    print("========== MIGRATION ZERO CONTROL: PLAN ONLY ==========")
    for name, passed in checks.items():
        print("[PASS] {0}: {1}".format(name, passed))
    print("[PASS] Model: {0}".format(paths["model"]))
    print("[PASS] Output root: {0}".format(output_root))
    print("[PASS] One-time marker absent: {0}".format(marker))
    print("[LOCK] No Quick Focus, optimization, SaveAs, Day73 rerun or seven-point batch")
    print("[WAIT] Approved execution may now consume the authorization once")


if __name__ == "__main__":
    main()
