"""Day 39 step 1: validate and preview the formal Day 22 impact scope."""

import hashlib
import json
import sys
from collections import defaultdict, deque
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
    """Allow offline scope calculation/reporting while locking every execution action."""

    execution = config["execution"]
    if not execution or any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 39 execution switch must be Boolean.")
    allowed_true = {
        "allow_formal_impact_scope_calculation",
        "allow_impact_report_generation",
    }
    if any(execution.get(key) is not True for key in allowed_true):
        raise ValueError("Day 39 offline scope calculation and reporting must be allowed.")
    prohibited = [key for key, value in execution.items() if key not in allowed_true and value is not False]
    if prohibited:
        raise ValueError("Day 39 prohibited action enabled: " + ", ".join(prohibited))


def load_approval(config):
    """Verify the exact Day 38 record and its narrow permission boundary."""

    source = config["source"]
    approval_path = PROJECT_ROOT / source["day38_approval_report"]
    if not approval_path.is_file() or sha256_file(approval_path) != source["day38_approval_sha256"]:
        raise ValueError("The frozen Day 38 approval record changed.")
    report = json.loads(approval_path.read_text(encoding="utf-8"))
    required = (
        report.get("task") == source["expected_day38_task"],
        report.get("status") == "success",
        report.get("decision_status") == source["expected_decision_status"],
        report["source_change_request"].get("request_id") == source["expected_request_id"],
        report["permissions"].get("impact_analysis_released") is True,
        report["permissions"].get("source_modification_released") is False,
        report["permissions"].get("zosapi_execution_released") is False,
        report["permissions"].get("historical_task_execution_released") is False,
        report.get("impact_analysis_performed") is False,
        report.get("existing_source_modified") is False,
    )
    if not all(required):
        raise ValueError("The Day 38 approval does not permit this analysis safely.")
    return approval_path, report


def load_graph_and_registry(config):
    """Verify the Day 30 DAG and its embedded Day 29 registry."""

    source = config["source"]
    graph_path = PROJECT_ROOT / source["day30_graph_report"]
    if not graph_path.is_file() or sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The frozen Day 30 dependency graph changed.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if (
        graph.get("task") != source["expected_graph_task"]
        or graph.get("status") != "success"
        or int(graph.get("node_count", -1)) != int(source["expected_node_count"])
        or int(graph.get("edge_count", -1)) != int(source["expected_edge_count"])
    ):
        raise ValueError("The Day 30 dependency graph metadata is incorrect.")
    registry_path = Path(graph["source_registry"])
    if not registry_path.is_file() or sha256_file(registry_path) != graph["source_registry_sha256"]:
        raise ValueError("The Day 29 registry embedded in Day 30 changed.")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("status") != "success" or int(registry.get("registered_day_count", -1)) != 26:
        raise ValueError("The Day 29 registry metadata is incorrect.")
    return graph_path, graph, registry_path, registry


def validate_target_unchanged(config, approval):
    """Confirm that the proposed Day 22 target is still untouched."""

    source = config["source"]
    target_path = PROJECT_ROOT / source["target_config"]
    if not target_path.is_file() or sha256_file(target_path) != source["target_config_sha256"]:
        raise ValueError("The Day 22 target config changed before impact analysis.")
    target = approval["target_under_review"]
    if Path(target["path"]).resolve() != target_path.resolve():
        raise ValueError("The approved target path does not match Day 39.")
    if target["sha256"] != source["target_config_sha256"] or target.get("target_modified") is not False:
        raise ValueError("The approved Day 22 target version is inconsistent.")
    return target_path


def transitive_descendants(changed_day, graph):
    """Traverse all outgoing dependency paths from one changed day."""

    adjacency = defaultdict(list)
    for edge in graph["edges"]:
        adjacency[int(edge["from"])].append(int(edge["to"]))
    visited = set()
    queue = deque(adjacency[changed_day])
    while queue:
        day = queue.popleft()
        if day in visited:
            continue
        visited.add(day)
        queue.extend(adjacency[day])
    return visited


def build_scope(config, approval, graph, registry):
    """Build the independently calculated review set and compare estimates."""

    policy = config["impact_scope"]
    changed_day = int(policy["changed_day"])
    graph_days = {int(node["day"]) for node in graph["nodes"]}
    if changed_day not in graph_days:
        raise ValueError("The changed Day is absent from the Day 30 graph.")
    descendants = transitive_descendants(changed_day, graph)
    if changed_day in descendants:
        raise ValueError("The Day 30 graph contains a cycle back to the changed Day.")
    formal_set = descendants | {changed_day}
    topology = [int(day) for day in graph["topological_order"]]
    review_order = [day for day in topology if day in formal_set]
    if set(review_order) != formal_set or len(review_order) != len(formal_set):
        raise ValueError("The formal review set is not represented exactly once in topology.")

    metadata = {int(entry["day"]): entry for entry in registry["entries"]}
    if any(day not in metadata for day in review_order):
        raise ValueError("A formal review Day is missing from the Day 29 registry.")
    uses_zosapi = [day for day in review_order if metadata[day]["execution_class"] == "uses_zosapi"]
    offline_only = [day for day in review_order if metadata[day]["execution_class"] == "offline_only"]
    if len(uses_zosapi) + len(offline_only) != len(review_order):
        raise ValueError("An unsupported execution class was found.")

    estimate = [int(day) for day in approval["requester_estimate"]["review_days"]]
    if estimate != [int(day) for day in policy["expected_requester_estimate"]]:
        raise ValueError("The requester estimate no longer matches the frozen plan.")
    if approval["requester_estimate"].get("scope_is_unverified") is not True:
        raise ValueError("The requester estimate was prematurely marked verified.")
    estimated_set = set(estimate)
    omitted = [day for day in review_order if day not in estimated_set]
    overreported = [day for day in estimate if day not in formal_set]
    return {
        "changed_day": changed_day,
        "direct_downstream": next(
            list(node["direct_downstream"]) for node in graph["nodes"] if int(node["day"]) == changed_day
        ),
        "descendants": [day for day in topology if day in descendants],
        "review_order": review_order,
        "uses_zosapi_days": uses_zosapi,
        "offline_only_days": offline_only,
        "requester_estimate": estimate,
        "omitted_by_requester": omitted,
        "overreported_by_requester": overreported,
        "estimate_exact_match": not omitted and not overreported,
    }


def validate_claim_boundaries(config):
    """Prevent scope calculation from becoming modification or execution approval."""

    validation = config["validation"]
    false_flags = (
        "requester_estimate_may_replace_calculation",
        "impact_scope_may_imply_source_change",
        "automatic_execution_allowed",
        "engineering_rerun_claim_allowed",
        "hidden_impact_score_allowed",
    )
    if any(validation.get(key) is not False for key in false_flags):
        raise ValueError("A forbidden Day 39 implication or claim was enabled.")


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
    config = load_config("configs/day39_formal_impact_scope.yaml")
    validate_execution_lock(config)
    approval_path, approval = load_approval(config)
    graph_path, graph, registry_path, registry = load_graph_and_registry(config)
    target_path = validate_target_unchanged(config, approval)
    scope = build_scope(config, approval, graph, registry)
    validate_claim_boundaries(config)

    print_introduction(config)
    print("========== DAY 39 FORMAL IMPACT-SCOPE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No impact report, source change, ZOS-API connection or review task execution will occur.")
    print(f"Day 38 approval: {approval_path}")
    print(f"Day 30 graph: {graph_path}")
    print(f"Day 29 registry: {registry_path}")
    print(f"Unchanged target: {target_path}")
    print()
    print(f"Changed source: Day {scope['changed_day']}")
    print(f"Direct downstream: {scope['direct_downstream']}")
    print(f"All transitive descendants: {scope['descendants']}")
    print(f"Formal review order: {scope['review_order']}")
    print(f"ZOS-API review class: {scope['uses_zosapi_days']}")
    print(f"Offline review class: {scope['offline_only_days']}")
    print()
    print(f"Requester estimate: {scope['requester_estimate']}")
    print(f"Omitted by requester: {scope['omitted_by_requester']}")
    print(f"Overreported by requester: {scope['overreported_by_requester']}")
    print(f"Exact set match: {scope['estimate_exact_match']}")
    print()
    print("[PASS] Frozen Day 38 approval and Day 30 graph verified")
    print("[PASS] Day 22 target remained unchanged")
    print("[PASS] Day 22 and all transitive descendants included exactly once")
    print("[PASS] Formal review set follows Day 30 topological order")
    print("[PASS] Requester estimate compared by omissions and overreporting")
    print("[PASS] Review classes identified without executing any task")
    print("PLAN ONLY finished. No output or source modification was created.")


if __name__ == "__main__":
    main()
