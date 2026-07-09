from pathlib import Path
import yaml


def load_yaml(path: Path) -> dict:
    """Safely load a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML file is empty: {path}")

    if not isinstance(data, dict):
        raise TypeError("YAML top level must be a dictionary/object.")

    return data


def estimate_sweep_values(start: float, end: float, step: float) -> list:
    """Generate sweep values and avoid floating point display noise."""
    if step <= 0:
        raise ValueError("Step must be greater than 0.")

    if end < start:
        raise ValueError("End value must be greater than or equal to start value.")

    values = []
    current = start
    eps = abs(step) * 1e-9

    while current <= end + eps:
        values.append(round(current, 10))
        current += step

    return values


def is_subpath(child: Path, parent: Path) -> bool:
    """
    Check whether child path is inside parent path.

    This prevents paths like:
    results/../../Desktop
    """
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def check_model_file(task: dict, policy: dict) -> list:
    """Check model file extension and unsafe path usage."""
    errors = []

    model_file = task.get("model_file", "")
    model_path = Path(model_file)

    allowed_extensions = policy["project"]["allowed_model_extensions"]

    if model_path.suffix.lower() not in allowed_extensions:
        errors.append(
            f"Model file extension must be one of {allowed_extensions}, "
            f"but got: {model_path.suffix}"
        )

    if policy["path_rules"]["forbid_absolute_paths"] and model_path.is_absolute():
        errors.append("model_file must not be an absolute path.")

    if policy["path_rules"]["forbid_parent_directory"] and ".." in model_path.parts:
        errors.append("model_file must not contain parent directory '..'.")

    return errors


def check_output_dir(task: dict, policy: dict, project_root: Path) -> list:
    """Check output directory safety."""
    errors = []

    safety = task.get("safety", {})
    output_dir = safety.get("output_dir", "")

    if not output_dir:
        errors.append("safety.output_dir is missing.")
        return errors

    output_path = Path(output_dir)

    if policy["path_rules"]["forbid_absolute_paths"] and output_path.is_absolute():
        errors.append("output_dir must not be an absolute path.")

    if policy["path_rules"]["forbid_parent_directory"] and ".." in output_path.parts:
        errors.append("output_dir must not contain parent directory '..'.")

    allowed_root_name = policy["project"]["allowed_output_root"]
    allowed_root = project_root / allowed_root_name
    full_output_path = project_root / output_path

    if not is_subpath(full_output_path, allowed_root):
        errors.append(
            f"output_dir must be inside '{allowed_root_name}/'. "
            f"Current output_dir: {output_dir}"
        )

    return errors


def check_target_range(task: dict, policy: dict) -> list:
    """Check surface number, parameter type, unit and sweep range."""
    errors = []

    target = task.get("target", {})

    surface = target.get("surface")
    parameter = target.get("parameter")
    unit = target.get("unit")
    start = target.get("start")
    end = target.get("end")
    step = target.get("step")

    min_surface = policy["target"]["min_surface"]
    max_surface = policy["target"]["max_surface"]

    if surface is None:
        errors.append("target.surface is missing.")
    elif not (min_surface <= surface <= max_surface):
        errors.append(
            f"target.surface must be between {min_surface} and {max_surface}, "
            f"but got {surface}."
        )

    allowed_parameters = policy["allowed_parameters"]

    if parameter not in allowed_parameters:
        errors.append(
            f"Parameter '{parameter}' is not allowed. "
            f"Allowed parameters: {list(allowed_parameters.keys())}"
        )
        return errors

    parameter_policy = allowed_parameters[parameter]

    expected_unit = parameter_policy["unit"]
    if unit != expected_unit:
        errors.append(
            f"Parameter '{parameter}' must use unit '{expected_unit}', "
            f"but got '{unit}'."
        )

    min_value = parameter_policy["min_value"]
    max_value = parameter_policy["max_value"]
    min_step = parameter_policy["min_step"]

    if start is None or end is None or step is None:
        errors.append("target.start, target.end and target.step must all exist.")
        return errors

    if start < min_value:
        errors.append(
            f"target.start is too small for {parameter}. "
            f"Minimum allowed value: {min_value}, got {start}."
        )

    if end > max_value:
        errors.append(
            f"target.end is too large for {parameter}. "
            f"Maximum allowed value: {max_value}, got {end}."
        )

    if step < min_step:
        errors.append(
            f"target.step is too small for {parameter}. "
            f"Minimum allowed step: {min_step}, got {step}."
        )

    if end < start:
        errors.append("target.end must be greater than or equal to target.start.")

    return errors


def check_run_count(task: dict, policy: dict) -> list:
    """Check estimated run count."""
    errors = []

    target = task.get("target", {})
    safety = task.get("safety", {})

    start = target.get("start")
    end = target.get("end")
    step = target.get("step")

    if start is None or end is None or step is None:
        errors.append("Cannot estimate run count because start/end/step is missing.")
        return errors

    values = estimate_sweep_values(start, end, step)
    run_count = len(values)

    task_max_runs = safety.get("max_runs")
    hard_limit = policy["execution"]["max_runs_hard_limit"]

    if task_max_runs is None:
        errors.append("safety.max_runs is missing.")
        return errors

    if run_count > task_max_runs:
        errors.append(
            f"Estimated runs {run_count} exceed task max_runs {task_max_runs}."
        )

    if run_count > hard_limit:
        errors.append(
            f"Estimated runs {run_count} exceed hard limit {hard_limit}."
        )

    return errors


def check_execution_flags(task: dict, policy: dict) -> list:
    """Check read-only and dry-run flags."""
    errors = []

    safety = task.get("safety", {})

    if policy["execution"]["require_dry_run_first"]:
        if safety.get("dry_run_first") is not True:
            errors.append("safety.dry_run_first must be true.")

    if policy["execution"]["require_read_only_original_model"]:
        if safety.get("read_only_original_model") is not True:
            errors.append("safety.read_only_original_model must be true.")

    return errors


def run_all_safety_checks(task: dict, policy: dict, project_root: Path) -> list:
    """Run all D33 safety checks and return error messages."""
    errors = []

    errors.extend(check_model_file(task, policy))
    errors.extend(check_output_dir(task, policy, project_root))
    errors.extend(check_target_range(task, policy))
    errors.extend(check_run_count(task, policy))
    errors.extend(check_execution_flags(task, policy))

    return errors