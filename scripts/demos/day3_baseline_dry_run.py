"""Day 3: read the baseline YAML and print a dry-run scan plan."""

import hashlib

from modules.config_loader import get_project_root, load_config


def validate_scan_values(parameter):
    """Reject scan values that violate the YAML safety limits."""

    baseline = parameter["baseline_value"]
    values = parameter["exploration"]["values"]
    minimum = parameter["safety"]["hard_minimum"]
    maximum = parameter["safety"]["hard_maximum"]

    if baseline not in values:
        raise ValueError("The baseline value is missing from the scan values.")

    for value in values:
        if value < minimum or value > maximum:
            raise ValueError(
                f"Unsafe scan value {value}: "
                f"allowed range is [{minimum}, {maximum}]."
            )


def calculate_sha256(file_path):
    """Calculate a file fingerprint without modifying the file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(block)

    return sha256.hexdigest().upper()


def validate_source_model(model):
    """Confirm that the source model exists and matches the recorded hash."""

    source_path = get_project_root() / model["source_file"]

    if not source_path.is_file():
        raise FileNotFoundError(f"Source model not found: {source_path}")

    expected_hash = model["source_sha256"].upper()
    actual_hash = calculate_sha256(source_path)

    if actual_hash != expected_hash:
        raise ValueError(
            "Source model SHA256 does not match the YAML configuration.\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}"
        )

    return source_path, actual_hash


def validate_dry_run_mode(config):
    """Require the safe execution state and real-Zemax provenance labels."""

    if config["execution"]["enabled"] is not False:
        raise ValueError(
            "Dry run refused: execution.enabled must remain false."
        )

    backend = config["backend"]

    if backend["name"] != "zemax":
        raise ValueError(
            f"Unexpected backend: {backend['name']!r}; expected 'zemax'."
        )

    if backend["data_source"] != "real_zemax":
        raise ValueError(
            "Mock or unknown data source rejected: "
            f"{backend['data_source']!r}."
        )


def validate_model_path_protection(model):
    """Keep the original model separate from the writable working copy."""

    project_root = get_project_root()
    source_path = (project_root / model["source_file"]).resolve()
    working_path = (project_root / model["working_copy"]).resolve()

    if source_path == working_path:
        raise ValueError(
            "Source model and working copy must use different paths."
        )

    if model["read_only_original"] is not True:
        raise ValueError("read_only_original must be true.")

    if model["forbid_overwrite_original"] is not True:
        raise ValueError("forbid_overwrite_original must be true.")

    return working_path


def main():
    config = load_config("configs/baseline_case.yaml")

    validate_dry_run_mode(config)

    parameter = config["outer_parameter"]
    validate_scan_values(parameter)
    source_path, source_hash = validate_source_model(config["model"])
    working_path = validate_model_path_protection(config["model"])

    surface = parameter["surface"]
    property_name = parameter["property"]
    unit = parameter["unit"]
    baseline = parameter["baseline_value"]
    values = parameter["exploration"]["values"]

    print("========== DAY 3 DRY RUN ==========")
    print("No Zemax connection will be created.")
    print(f"Execution enabled: {config['execution']['enabled']}")
    print(f"Source model: {source_path}")
    print(f"Working copy: {working_path}")
    print(f"Source SHA256: {source_hash}")
    print()
    print("[PASS] Dry-run mode and data provenance")
    print("[PASS] Scan values and safety limits")
    print("[PASS] Source model identity")
    print("[PASS] Original-model path protection")
    print()

    for case_number, value in enumerate(values, start=1):
        baseline_mark = " <- baseline" if value == baseline else ""
        print(
            f"Case {case_number:03d}: "
            f"Surface {surface} {property_name} = {value:.3f} {unit}"
            f"{baseline_mark}"
        )

    print()
    print(f"Total cases: {len(values)}")
    print("DRY RUN finished. No model was modified.")


if __name__ == "__main__":
    main()
