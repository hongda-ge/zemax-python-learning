"""Day 41 step 1: plan dependency-safe waves for the approved Day 22 change scope."""

import hashlib
import json
import sys
from pathlib import Path


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


def validate_execution_lock(config):
    """Allow offline wave calculation/reporting while keeping execution locked."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 41 execution switch must be Boolean.")
    allowed_true = {"allow_wave_calculation", "allow_wave_report_generation"}
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 41 wave calculation and reporting must be explicitly allowed.")
    prohibited = [key for key, value in execution.items() if key not in allowed_true and value is not False]
    if prohibited:
        raise ValueError("Day 41 prohibited action enabled: " + ", ".join(prohibited))


def load_scope_approval(config):
    """Verify the exact Day 40 planning-only scope approval."""

    source = config["source"]
    approval_path = PROJECT_ROOT / source["day40_scope_approval"]
    if not approval_path.is_file() or sha256_file(approval_path) != source["day40_scope_approval_sha256"]:
        raise ValueError("The frozen Day 40 scope approval changed.")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    expected_scope = [int(day) for day in config["expected_result"]["review_scope"]]
    checks = (
        approval.get("task") == source["expected_day40_task"],
        approval.get("status") == "success",
        approval.get("decision_status") == source["expected_decision_status"],
        approval.get("approved_review_scope") == expected_scope,
        approval["permissions"].get("review_plan_generation_released") is True,
        approval["permissions"].get("source_modification_released") is False,
        approval["permissions"].get("zosapi_execution_released") is False,
        approval["permissions"].get("review_task_execution_released") is False,
        approval.get("review_plan_generated") is False,
        approval.get("review_tasks_executed") is False,
        approval.get("existing_source_modified") is False,
    )
    if not all(checks):
        raise ValueError("The Day 40 approval does not safely permit Day 41 planning.")
    approved_capabilities = set(approval["decision"]["approved_capabilities"])
    if "plan_dependency_review_waves" not in approved_capabilities:
        raise ValueError("Day 40 did not release dependency-wave planning.")
    return approval_path, approval


def load_graph(config):
    """Verify the frozen Day 30 dependency graph."""

    source = config["source"]
    graph_path = PROJECT_ROOT / source["day30_graph_report"]
    if not graph_path.is_file() or sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The frozen Day 30 dependency graph changed.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if graph.get("task") != source["expected_graph_task"] or graph.get("status") != "success":
        raise ValueError("The Day 30 graph metadata is incorrect.")
    return graph_path, graph


def validate_target_unchanged(config, approval):
    """Confirm that planning still targets the untouched Day 22 config."""

    source = config["source"]
    target_path = PROJECT_ROOT / source["target_config"]
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target changed before wave planning.")
    target = approval["target_under_review"]
    if Path(target["path"]).resolve() != target_path.resolve():
        raise ValueError("The Day 40 target path does not match Day 41.")
    if target["sha256"] != source["target_config_sha256"] or target.get("modified") is not False:
        raise ValueError("The Day 40 target version is inconsistent.")
    return target_path


def induced_edges(review_nodes, graph):
    """Return dependency edges whose endpoints are both in the approved scope."""

    review_set = set(review_nodes)
    return [
        (int(edge["from"]), int(edge["to"]))
        for edge in graph["edges"]
        if int(edge["from"]) in review_set and int(edge["to"]) in review_set
    ]


def build_waves(review_nodes, graph):
    """Use deterministic Kahn-style releases to construct dependency waves."""

    edges = induced_edges(review_nodes, graph)
    remaining = set(review_nodes)
    waves = []
    while remaining:
        ready = sorted(
            node
            for node in remaining
            if not any(source in remaining and target == node for source, target in edges)
        )
        if not ready:
            raise ValueError("The approved Day 41 review subgraph contains a cycle.")
        waves.append(ready)
        remaining -= set(ready)
    return waves, edges


def build_result(config, approval, graph):
    """Build and validate one change-specific wave result."""

    expected = config["expected_result"]
    review_nodes = [int(day) for day in approval["approved_review_scope"]]
    waves, edges = build_waves(review_nodes, graph)
    flattened = [day for wave in waves for day in wave]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(review_nodes):
        raise ValueError("A Day 41 review node was lost or duplicated.")
    wave_index = {
        node: number
        for number, wave in enumerate(waves, start=1)
        for node in wave
    }
    for source, target in edges:
        if wave_index[source] >= wave_index[target]:
            raise ValueError(f"Affected edge Day{source}->Day{target} does not move forward.")
    changed_day = int(expected["changed_day"])
    if waves[0] != [changed_day]:
        raise ValueError("The first Day 41 wave must contain only the changed source.")
    expected_waves = [[int(day) for day in wave] for wave in expected["waves"]]
    checks = (
        review_nodes == [int(day) for day in expected["review_scope"]],
        len(review_nodes) == int(expected["review_node_count"]),
        len(edges) == int(expected["affected_edge_count"]),
        len(waves) == int(expected["wave_count"]),
        max(len(wave) for wave in waves) == int(expected["maximum_wave_width"]),
        waves == expected_waves,
    )
    if not all(checks):
        raise ValueError("The calculated Day 41 wave structure changed.")
    execution_class = {
        int(day): "uses_zosapi"
        for day in approval["uses_zosapi_review_days"]
    }
    execution_class.update({
        int(day): "offline_only"
        for day in approval["offline_only_review_days"]
    })
    if set(execution_class) != set(review_nodes):
        raise ValueError("The Day 40 execution-class mapping is incomplete.")
    details = []
    for number, wave in enumerate(waves, start=1):
        details.append(
            {
                "wave": number,
                "days": wave,
                "uses_zosapi_days": [day for day in wave if execution_class[day] == "uses_zosapi"],
                "offline_only_days": [day for day in wave if execution_class[day] == "offline_only"],
                "execution_released": False,
            }
        )
    return {
        "changed_day": changed_day,
        "review_node_count": len(review_nodes),
        "affected_edges": edges,
        "affected_edge_count": len(edges),
        "wave_count": len(waves),
        "maximum_wave_width": max(len(wave) for wave in waves),
        "waves": details,
    }


def validate_policies(config):
    """Keep dependency readiness separate from real resource concurrency."""

    policy = config["wave_policy"]
    required_true = (
        "use_approved_scope_only",
        "use_induced_review_subgraph",
        "treat_unaffected_upstream_as_already_available",
        "start_with_changed_source",
        "release_node_only_after_all_affected_upstream_complete",
        "allow_same_wave_only_without_affected_dependency",
        "preserve_execution_class_labels",
        "theoretical_parallelism_only",
    )
    invalid = [key for key in required_true if policy.get(key) is not True]
    validation = config["validation"]
    invalid += [
        key
        for key in (
            "resource_parallelism_claim_allowed",
            "automatic_execution_allowed",
            "source_modification_allowed",
            "engineering_rerun_claim_allowed",
            "hidden_priority_score_allowed",
        )
        if validation.get(key) is not False
    ]
    if invalid:
        raise ValueError("Day 41 policy validation failed: " + ", ".join(invalid))


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
    config = load_config("configs/day41_change_specific_review_waves.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    approval_path, approval = load_scope_approval(config)
    graph_path, graph = load_graph(config)
    target_path = validate_target_unchanged(config, approval)
    result = build_result(config, approval, graph)

    print_introduction(config)
    print("========== DAY 41 CHANGE-SPECIFIC REVIEW-WAVE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No wave report, source change, ZOS-API connection or review task execution will occur.")
    print("Waves describe dependency readiness, not actual resource concurrency.")
    print(f"Day 40 scope approval: {approval_path}")
    print(f"Day 30 dependency graph: {graph_path}")
    print(f"Unchanged target: {target_path}")
    print()
    print(
        f"Changed Day {result['changed_day']}: nodes={result['review_node_count']}, "
        f"affected edges={result['affected_edge_count']}, waves={result['wave_count']}, "
        f"max width={result['maximum_wave_width']}"
    )
    for wave in result["waves"]:
        print(
            f"  Wave {wave['wave']:02d}: days={wave['days']}; "
            f"ZOS-API={wave['uses_zosapi_days']}; offline={wave['offline_only_days']}; "
            f"execution released={wave['execution_released']}"
        )
    print()
    print("[PASS] Frozen Day 40 scope approval and Day 30 graph verified")
    print("[PASS] Every approved review node appears in exactly one wave")
    print("[PASS] Every affected dependency points from an earlier to a later wave")
    print("[PASS] The first wave contains only changed Day 22")
    print("[PASS] Execution classes retained without releasing any task")
    print("[PASS] Resource concurrency and hidden priority claims remain forbidden")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
