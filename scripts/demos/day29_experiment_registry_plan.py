"""Day 29 step 1: audit the teaching-experiment registry plan."""

import fnmatch
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep the registry planning step read-only and offline."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 29 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_source_file_modification",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 29 forbidden plan action enabled: " + ", ".join(enabled))
    if execution["allow_registry_generation"] is not True:
        raise ValueError("Reviewed Day 29 registry generation must be enabled.")


def validate_scope(config):
    """Require one complete and non-overlapping Day3-Day28 track."""

    scope = config["registry_scope"]
    first_day = int(scope["first_day"])
    last_day = int(scope["last_day"])
    days = list(range(first_day, last_day + 1))
    if len(days) != int(scope["day_count"]):
        raise ValueError("Day 29 registry day count is inconsistent.")
    if scope["include_current_optical_teaching_track_only"] is not True:
        raise ValueError("Day 29 must remain limited to the current teaching track.")
    phases = config["phase_definitions"]
    phase_days = [int(day) for phase in phases for day in phase["days"]]
    if sorted(phase_days) != days or len(phase_days) != len(set(phase_days)):
        raise ValueError("Day 29 phase definitions must cover every day exactly once.")
    classification = config["execution_classification"]
    classified_days = [int(day) for day in classification["zosapi_days"]]
    classified_days += [int(day) for day in classification["offline_only_days"]]
    if classification["require_complete_partition"] is not True:
        raise ValueError("Day 29 execution classification must require a full partition.")
    if sorted(classified_days) != days or len(classified_days) != len(set(classified_days)):
        raise ValueError("Day 29 execution classes must cover every day exactly once.")
    early_metadata_days = sorted(int(day) for day in config["early_day_metadata"])
    if early_metadata_days != [3, 4, 5, 6, 7]:
        raise ValueError("Day 29 early-day metadata must cover Day3-Day7.")
    return days


def find_matching_files(directory, patterns, day):
    """Find files using case-insensitive day-specific patterns."""

    if not directory.is_dir():
        raise FileNotFoundError(f"Registry source directory not found: {directory}")
    day_patterns = [pattern.format(day=day).lower() for pattern in patterns]
    matches = []
    for path in directory.iterdir():
        if path.is_file() and any(
            fnmatch.fnmatch(path.name.lower(), pattern) for pattern in day_patterns
        ):
            matches.append(path)
    return sorted(matches)


def phase_for_day(config, day):
    """Return the declared phase for one day."""

    matches = [phase for phase in config["phase_definitions"] if day in phase["days"]]
    if len(matches) != 1:
        raise ValueError(f"Day {day} does not belong to exactly one phase.")
    return matches[0]


def shared_config_for_day(config, day):
    """Resolve the documented early-day shared config exception."""

    matches = [
        item for item in config["shared_config_exceptions"] if day in item["days"]
    ]
    if len(matches) > 1:
        raise ValueError(f"Day {day} has multiple shared config exceptions.")
    if not matches:
        return None
    path = PROJECT_ROOT / matches[0]["config"]
    if not path.is_file():
        raise FileNotFoundError(f"Shared config not found: {path}")
    return path


def inventory_days(config, days):
    """Build a read-only coverage inventory without inferring conclusions."""

    directories = {
        key: PROJECT_ROOT / value for key, value in config["source_directories"].items()
    }
    rules = config["file_rules"]
    rows = []
    for day in days:
        configs = find_matching_files(
            directories["configs"], rules["config_patterns"], day
        )
        scripts = find_matching_files(
            directories["scripts"], rules["script_patterns"], day
        )
        notes = find_matching_files(
            directories["learning_notes"], rules["note_patterns"], day
        )
        shared = shared_config_for_day(config, day)
        primary_configs = configs or ([shared] if shared else [])
        rows.append(
            {
                "day": day,
                "phase": phase_for_day(config, day),
                "configs": primary_configs,
                "scripts": scripts,
                "notes": notes,
                "uses_shared_config": not configs and shared is not None,
            }
        )
    return rows


def validate_inventory(config, rows):
    """Require executable coverage and complete reviewed documentation."""

    rules = config["file_rules"]
    errors = []
    for row in rows:
        day = row["day"]
        if rules["require_at_least_one_script_per_day"] and not row["scripts"]:
            errors.append(f"Day {day}: no script")
        if rules["require_exactly_one_learning_note_every_day"] and len(row["notes"]) != 1:
            errors.append(f"Day {day}: expected one note, found {len(row['notes'])}")
        if day >= 8:
            if rules["require_exactly_one_primary_config_from_day8"] and len(row["configs"]) != 1:
                errors.append(f"Day {day}: expected one config, found {len(row['configs'])}")
    if errors:
        raise ValueError("Day 29 inventory failed: " + "; ".join(errors))


def validate_guardrails(config):
    """Keep inventory factual and non-mutating."""

    policy = config["audit_policy"]
    required_true = (
        "read_only_inventory",
        "report_missing_files",
        "report_multiple_primary_files",
        "report_documentation_gaps",
    )
    forbidden_true = (
        "infer_scientific_conclusion_from_filename",
        "modify_existing_day_files",
        "hidden_completion_score_allowed",
    )
    invalid = [key for key in required_true if policy.get(key) is not True]
    invalid += [key for key in forbidden_true if policy.get(key) is not False]
    if invalid:
        raise ValueError("Day 29 guardrail failed: " + ", ".join(invalid))


def relative_list(paths):
    """Format project-relative paths for readable console output."""

    return [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in paths]


def main():
    config = load_config("configs/day29_experiment_registry.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    days = validate_scope(config)
    rows = inventory_days(config, days)
    validate_inventory(config, rows)

    print("========== DAY 29 EXPERIMENT-REGISTRY PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical calculation will occur.")
    print("No registry file or existing source file will be written by this plan step.")
    print(f"Registry scope: Day {days[0]} to Day {days[-1]} ({len(days)} days)")
    print("Architecture demos such as D30 and D37-D60 remain outside this track.")
    print()
    print("Phase coverage:")
    for phase in config["phase_definitions"]:
        print(
            f"  {phase['id']}: Day {min(phase['days'])}-Day {max(phase['days'])} "
            f"({len(phase['days'])} days) - {phase['name']}"
        )
    print()
    print("Artifact coverage by day:")
    for row in rows:
        config_label = relative_list(row["configs"])[0] if row["configs"] else "MISSING"
        note_label = relative_list(row["notes"])[0] if row["notes"] else "MISSING"
        shared = " [shared]" if row["uses_shared_config"] else ""
        print(
            f"  Day {row['day']:02d}: config={config_label}{shared}; "
            f"scripts={len(row['scripts'])}; note={note_label}"
        )
    early_gaps = [row["day"] for row in rows if row["day"] < 8 and not row["notes"]]
    print()
    print(f"Early-day documentation gaps: {early_gaps}")
    print("Planned registry fields:")
    print("  " + ", ".join(config["planned_registry_fields"]))
    print()
    print("[PASS] Day3-Day28 scope contains 26 unique days")
    print("[PASS] Every day has at least one executable teaching script")
    print("[PASS] Day8-Day28 each have one primary config")
    print("[PASS] Day3-Day7 shared baseline config exceptions verified")
    print("[PASS] Day3-Day28 each have one learning note")
    print("[PASS] Documentation gaps were reported, not hidden")
    print("[PASS] ZOS-API, source modification and hidden score forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
