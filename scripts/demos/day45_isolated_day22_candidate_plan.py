"""Day 45 step 1: preview one isolated Day 22 candidate entirely in memory."""

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_boundaries(config):
    """Permit candidate artifacts but keep scientific execution locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 45 execution switch must be Boolean.")
    allowed_true = {
        "allow_candidate_preview",
        "allow_candidate_file_generation",
        "allow_candidate_fingerprint_generation",
        "allow_manifest_generation",
    }
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 45 candidate preparation permissions are incomplete.")
    prohibited = [
        key for key, value in execution.items()
        if key not in allowed_true and value is not False
    ]
    if prohibited:
        raise ValueError("Day 45 prohibited action enabled: " + ", ".join(prohibited))
    validation = config["validation"]
    forbidden = (
        "source_modification_allowed",
        "slot1_execution_allowed",
        "zosapi_connection_allowed",
        "downstream_release_allowed",
        "engineering_change_claim_allowed",
    )
    if any(validation.get(key) is not False for key in forbidden):
        raise ValueError("A forbidden Day 45 action or claim was enabled.")


def validate_candidate_policy(config):
    """Require text preservation, semantic comparison and a future approval gate."""

    policy = config["candidate_policy"]
    required = (
        "copy_source_text_before_edit",
        "preserve_comments_and_layout",
        "replace_exactly_one_scalar_line",
        "parse_source_and_candidate_yaml",
        "require_one_semantic_difference",
        "candidate_is_not_official_baseline",
        "future_execution_requires_separate_approval",
    )
    if any(policy.get(key) is not True for key in required):
        raise ValueError("The Day 45 candidate policy is incomplete.")


def load_approval(config):
    """Load the exact Day 44 approval and verify candidate-only permissions."""

    source = config["source"]
    path = PROJECT_ROOT / source["day44_approval_record"]
    if not path.is_file() or sha256_file(path) != source["day44_approval_sha256"]:
        raise ValueError("The frozen Day 44 approval changed.")
    approval = json.loads(path.read_text(encoding="utf-8"))
    permissions = approval["permissions"]
    checks = (
        approval.get("task") == source["expected_day44_task"],
        approval.get("status") == "success",
        approval.get("decision_status") == source["expected_decision_status"],
        approval.get("approval_record_generated") is True,
        permissions.get("candidate_preparation_released") is True,
        permissions.get("candidate_fingerprint_generation_released") is True,
        permissions.get("pre_execution_manifest_generation_released") is True,
        permissions.get("source_modification_released") is False,
        permissions.get("slot_01_execution_released") is False,
        permissions.get("zosapi_execution_released") is False,
        permissions.get("downstream_slots_released") is False,
        approval.get("candidate_prepared") is False,
        approval.get("review_task_executed") is False,
    )
    if not all(checks):
        raise ValueError("Day 44 does not safely authorize Day 45 candidate preparation.")
    return path, approval


def validate_official_source(config, approval):
    """Bind candidate preparation to the unchanged official Day 22 config."""

    source = config["source"]
    path = PROJECT_ROOT / source["official_day22_config"]
    if not path.is_file() or sha256_file(path) != source["official_day22_sha256"]:
        raise ValueError("The official Day 22 config changed before candidate preparation.")
    approved_target = approval["target_under_review"]
    if Path(approved_target["path"]).resolve() != path.resolve():
        raise ValueError("The Day 44 target path does not match Day 45.")
    if approved_target["sha256"] != source["official_day22_sha256"] or approved_target["modified"] is not False:
        raise ValueError("The Day 44 official-target state is inconsistent.")
    return path


def validate_change_boundary(config, approval):
    """Require exact agreement between Day 44 and Day 45 change declarations."""

    change = config["change"]
    approved = approval["change_under_preparation"]
    checks = (
        change["canonical_field"] == approved["field"],
        float(change["current_value"]) == float(approved["current_value"]),
        float(change["proposed_value"]) == float(approved["proposed_value"]),
        change["unit"] == approved["unit"],
        config["outputs"]["root_from_approval"] == approval["candidate_boundary"]["root"],
    )
    if not all(checks):
        raise ValueError("The Day 45 change boundary differs from Day 44 approval.")


def find_change_item(document, config):
    """Find the approved list item in parsed YAML and verify its current value."""

    change = config["change"]
    items = document.get(change["list_key"])
    if not isinstance(items, list):
        raise ValueError("The Day 22 teaching_error_sources list is missing.")
    matches = [item for item in items if item.get("id") == change["item_id"]]
    if len(matches) != 1:
        raise ValueError("The positioning_accuracy item is missing or duplicated.")
    item = matches[0]
    if float(item[change["value_key"]]) != float(change["current_value"]):
        raise ValueError("The official positioning_accuracy value changed.")
    return item


def build_candidate_text(source_text, config):
    """Replace exactly one scalar line inside the approved YAML list item."""

    change = config["change"]
    lines = source_text.splitlines(keepends=True)
    item_pattern = re.compile(r"^(?P<indent>\s*)-\s+id:\s*[\"']?" + re.escape(change["item_id"]) + r"[\"']?\s*$")
    value_pattern = re.compile(
        r"^(?P<prefix>\s*" + re.escape(change["value_key"]) + r"\s*:\s*)(?P<value>[^\s#]+)(?P<suffix>\s*(?:#.*)?)(?P<newline>\r?\n?)$"
    )
    item_start = None
    item_indent = None
    for index, line in enumerate(lines):
        match = item_pattern.match(line.rstrip("\r\n"))
        if match:
            if item_start is not None:
                raise ValueError("The positioning_accuracy YAML item is duplicated.")
            item_start = index
            item_indent = len(match.group("indent"))
    if item_start is None:
        raise ValueError("The positioning_accuracy YAML item was not found in text.")
    replacements = []
    for index in range(item_start + 1, len(lines)):
        stripped = lines[index].lstrip()
        current_indent = len(lines[index]) - len(stripped)
        if stripped.startswith("- id:") and current_indent == item_indent:
            break
        match = value_pattern.match(lines[index])
        if not match:
            continue
        if float(match.group("value")) != float(change["current_value"]):
            raise ValueError("The scalar text does not contain the approved current value.")
        lines[index] = (
            match.group("prefix")
            + change["output_literal"]
            + match.group("suffix")
            + match.group("newline")
        )
        replacements.append(index + 1)
    if len(replacements) != 1:
        raise ValueError("Day 45 must replace exactly one scalar line.")
    return "".join(lines), replacements[0]


def semantic_differences(source, candidate, path=""):
    """Return leaf-level semantic differences between two parsed documents."""

    differences = []
    if isinstance(source, dict) and isinstance(candidate, dict):
        for key in sorted(set(source) | set(candidate)):
            child = f"{path}.{key}" if path else str(key)
            if key not in source or key not in candidate:
                differences.append({"path": child, "source": source.get(key), "candidate": candidate.get(key)})
            else:
                differences.extend(semantic_differences(source[key], candidate[key], child))
    elif isinstance(source, list) and isinstance(candidate, list):
        if len(source) != len(candidate):
            differences.append({"path": path + ".length", "source": len(source), "candidate": len(candidate)})
        else:
            for index, (left, right) in enumerate(zip(source, candidate)):
                label = left.get("id") if isinstance(left, dict) and "id" in left else str(index)
                differences.extend(semantic_differences(left, right, f"{path}.{label}"))
    elif source != candidate:
        differences.append({"path": path, "source": source, "candidate": candidate})
    return differences


def build_preview(config, approval_path, official_path):
    """Construct and audit the candidate in memory without writing it."""

    source_text = official_path.read_text(encoding="utf-8")
    source_document = yaml.safe_load(source_text)
    find_change_item(source_document, config)
    candidate_text, changed_line = build_candidate_text(source_text, config)
    candidate_document = yaml.safe_load(candidate_text)
    differences = semantic_differences(source_document, candidate_document)
    expected_path = config["change"]["canonical_field"]
    if len(differences) != 1 or differences[0]["path"] != expected_path:
        raise ValueError("The in-memory candidate contains an undeclared semantic difference.")
    difference = differences[0]
    if float(difference["source"]) != float(config["change"]["current_value"]):
        raise ValueError("The semantic source value is incorrect.")
    if float(difference["candidate"]) != float(config["change"]["proposed_value"]):
        raise ValueError("The semantic candidate value is incorrect.")
    return {
        "approval_path": str(approval_path),
        "official_path": str(official_path),
        "official_sha256": sha256_file(official_path),
        "candidate_text": candidate_text,
        "changed_line": changed_line,
        "semantic_differences": differences,
        "candidate_prepared_in_memory": True,
        "candidate_file_written": False,
        "review_task_executed": False,
    }


def print_introduction(config):
    """Print today's four-part teaching introduction."""

    intro = config["teaching_introduction"]
    print("========== TODAY'S INTRODUCTION ==========")
    print(f"Why today: {intro['why_today']}")
    print(f"Link to yesterday: {intro['relation_to_previous_day']}")
    print("Core concepts:")
    for concept in intro["concepts"]:
        print(f"  - {concept}")
    print(f"Completion standard: {intro['completion_standard']}")
    print()


def main():
    config = load_config("configs/day45_isolated_day22_candidate.yaml")
    validate_execution_boundaries(config)
    validate_candidate_policy(config)
    approval_path, approval = load_approval(config)
    official_path = validate_official_source(config, approval)
    validate_change_boundary(config, approval)
    preview = build_preview(config, approval_path, official_path)

    print_introduction(config)
    print("========== DAY 45 ISOLATED DAY22 CANDIDATE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No candidate file, manifest, source change or review task execution will occur.")
    print(f"Day 44 approval: {approval_path}")
    print(f"Official source: {official_path}")
    print(f"Official SHA256: {preview['official_sha256']}")
    print(f"Approved candidate root: {PROJECT_ROOT / config['outputs']['root_from_approval']}")
    print()
    difference = preview["semantic_differences"][0]
    print(f"Planned line replacement: line {preview['changed_line']}")
    print(f"Semantic field: {difference['path']}")
    print(f"Value: {difference['source']:.3f} -> {difference['candidate']:.3f} mm")
    print()
    print("[PASS] Frozen Day 44 approval and official Day 22 fingerprint verified")
    print("[PASS] Candidate root matches the approved outputs boundary")
    print("[PASS] Exactly one scalar line would be replaced")
    print("[PASS] Exactly one semantic field would change")
    print("[PASS] Official config, Slot 1 execution and downstream slots remain locked")
    print("PLAN ONLY finished. No output, candidate or source modification was created.")


if __name__ == "__main__":
    main()
