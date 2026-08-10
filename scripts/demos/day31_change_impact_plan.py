"""Day 31 step 1: plan transitive review sets from the frozen Day 30 DAG."""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def sha256_file(path):
    """Calculate an uppercase file fingerprint without modifying the file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Keep the Day 31 planning step offline and non-mutating."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 31 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_source_file_modification",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 31 plan action enabled: " + ", ".join(enabled))
    if execution["allow_impact_report_generation"] is not True:
        raise ValueError("Reviewed Day 31 impact generation must be enabled.")


def load_day30_graph(config):
    """Load and verify the frozen Day 30 dependency report and Day 29 registry."""

    source = config["source"]
    graph_path = PROJECT_ROOT / source["day30_graph_report"]
    if not graph_path.is_file():
        raise FileNotFoundError(f"Day 30 graph report not found: {graph_path}")
    if sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The frozen Day 30 graph SHA256 is incorrect.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    checks = (
        graph["task"] == source["expected_task"],
        graph["status"] == source["expected_status"],
        graph["node_count"] == source["expected_node_count"],
        graph["edge_count"] == source["expected_edge_count"],
    )
    if not all(checks):
        raise ValueError("The frozen Day 30 graph metadata is incorrect.")

    registry_path = Path(graph["source_registry"])
    if not registry_path.is_file():
        raise FileNotFoundError(f"Day 29 source registry not found: {registry_path}")
    if sha256_file(registry_path) != graph["source_registry_sha256"]:
        raise ValueError("The Day 29 registry no longer matches Day 30 provenance.")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    return graph_path, graph, registry_path, registry


def build_indexes(graph):
    """Build forward and reverse adjacency from reviewed Day 30 edges."""

    nodes = [int(node["day"]) for node in graph["nodes"]]
    downstream = {node: [] for node in nodes}
    upstream = {node: [] for node in nodes}
    for edge in graph["edges"]:
        source = int(edge["from"])
        target = int(edge["to"])
        downstream[source].append(target)
        upstream[target].append(source)
    return nodes, downstream, upstream


def transitive_reachable(start, adjacency):
    """Return every node reachable from start, excluding start itself."""

    reached = set()
    stack = list(adjacency[start])
    while stack:
        node = stack.pop()
        if node in reached:
            continue
        reached.add(node)
        stack.extend(adjacency[node])
    return reached


def build_scenario_results(config, graph, registry):
    """Calculate conservative review sets without executing any experiment."""

    nodes, downstream, upstream = build_indexes(graph)
    order = [int(day) for day in graph["topological_order"]]
    order_index = {day: index for index, day in enumerate(order)}
    execution_class = {
        int(entry["day"]): entry["execution_class"] for entry in registry["entries"]
    }
    results = []
    for scenario in config["teaching_change_scenarios"]:
        changed = int(scenario["changed_day"])
        if changed not in nodes:
            raise ValueError(f"Changed Day {changed} is not in the Day 30 graph.")
        descendants = transitive_reachable(changed, downstream)
        ancestors = transitive_reachable(changed, upstream)
        review_set = set(descendants)
        if config["impact_policy"]["include_changed_node"]:
            review_set.add(changed)
        if review_set & ancestors:
            raise ValueError(f"Scenario {scenario['id']} incorrectly includes ancestors.")
        review_order = [day for day in order if day in review_set]
        if review_order != sorted(review_order, key=order_index.get):
            raise ValueError(f"Scenario {scenario['id']} is not topologically ordered.")
        if len(descendants) != int(scenario["expected_descendant_count"]):
            raise ValueError(f"Scenario {scenario['id']} descendant count changed.")
        if len(review_set) != int(scenario["expected_review_set_count"]):
            raise ValueError(f"Scenario {scenario['id']} review-set count changed.")
        results.append(
            {
                "scenario_id": scenario["id"],
                "changed_day": changed,
                "changed_artifact": scenario["changed_artifact"],
                "descendants": [day for day in order if day in descendants],
                "review_order": review_order,
                "uses_zosapi_days": [
                    day for day in review_order if execution_class[day] == "uses_zosapi"
                ],
                "offline_only_days": [
                    day for day in review_order if execution_class[day] == "offline_only"
                ],
            }
        )
    return results


def validate_policies(config):
    """Prevent impact analysis from becoming an automatic rerun claim."""

    policy = config["impact_policy"]
    required_true = (
        "include_changed_node",
        "include_all_transitive_descendants",
        "order_by_day30_topology",
        "exclude_unrelated_branches",
        "classify_by_execution_class",
        "affected_does_not_mean_automatic_zosapi_rerun",
    )
    invalid = [key for key in required_true if policy.get(key) is not True]
    validation = config["validation"]
    invalid += [
        key
        for key in (
            "hidden_impact_score_allowed",
            "automatic_execution_allowed",
            "engineering_rerun_claim_allowed",
        )
        if validation.get(key) is not False
    ]
    scenario_ids = [item["id"] for item in config["teaching_change_scenarios"]]
    if validation["require_unique_scenario_ids"] and len(scenario_ids) != len(set(scenario_ids)):
        invalid.append("duplicate_scenario_ids")
    if invalid:
        raise ValueError("Day 31 policy validation failed: " + ", ".join(invalid))


def main():
    config = load_config("configs/day31_change_impact_analysis.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    graph_path, graph, registry_path, registry = load_day30_graph(config)
    results = build_scenario_results(config, graph, registry)

    print("========== DAY 31 CHANGE-IMPACT PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical calculation will occur.")
    print("No impact report or automatic rerun will be created in this step.")
    print(f"Day 30 graph: {graph_path}")
    print(f"Day 29 registry: {registry_path}")
    print()
    for result in results:
        print(f"{result['scenario_id']}: changed Day {result['changed_day']}")
        print(f"  artifact: {result['changed_artifact']}")
        print(
            f"  descendants={len(result['descendants'])}; "
            f"review set={len(result['review_order'])}"
        )
        print(f"  review order: {result['review_order']}")
        print(
            f"  uses_zosapi={len(result['uses_zosapi_days'])}; "
            f"offline_only={len(result['offline_only_days'])}"
        )
    print()
    print("[PASS] Frozen Day 30 graph and Day 29 registry fingerprints verified")
    print("[PASS] Three changed nodes and all transitive descendants verified")
    print("[PASS] Ancestors and unrelated branches excluded from each review set")
    print("[PASS] Review sets follow the Day 30 topological order")
    print("[PASS] Affected nodes are classified, not automatically executed")
    print("[PASS] ZOS-API, hidden score and engineering rerun claim forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
