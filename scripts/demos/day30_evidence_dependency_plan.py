"""Day 30 step 1: validate the reviewed teaching and evidence dependency plan."""

import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def validate_execution_lock(config):
    """Keep the Day 30 planning step offline and non-mutating."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 30 execution switch must be Boolean.")
    forbidden = (
        "enabled",
        "allow_zosapi_connection",
        "allow_model_copy",
        "allow_new_optical_calculation",
        "allow_source_file_modification",
    )
    enabled = [key for key in forbidden if execution.get(key) is not False]
    if enabled:
        raise ValueError("Day 30 plan action enabled: " + ", ".join(enabled))
    if execution["allow_graph_generation"] is not True:
        raise ValueError("Reviewed Day 30 graph generation must be enabled.")


def newest_registry(config):
    """Load the newest completed Day 29 registry."""

    root = PROJECT_ROOT / config["source"]["day29_registry_root"]
    name = config["source"]["day29_registry_name"]
    candidates = list(root.glob(f"registry_*/{name}"))
    if not candidates:
        raise FileNotFoundError("No Day 29 experiment registry was found.")
    path = max(candidates, key=lambda item: item.stat().st_mtime)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] != "success":
        raise ValueError("The newest Day 29 registry is not successful.")
    if report["registered_day_count"] != config["source"]["expected_registered_day_count"]:
        raise ValueError("The Day 29 registered-day count is incorrect.")
    if report["documentation_gap_days"] != config["source"]["expected_documentation_gaps"]:
        raise ValueError("The Day 29 registry still contains documentation gaps.")
    return path, report


def build_edges(config):
    """Combine reviewed edges while preserving their declared type."""

    edges = []
    for edge in config["teaching_prerequisite_edges"]:
        edges.append(
            {
                "from": int(edge["from"]),
                "to": int(edge["to"]),
                "edge_type": "teaching_prerequisite",
                "description": edge["reason"],
            }
        )
    for edge in config["evidence_dependency_edges"]:
        edges.append(
            {
                "from": int(edge["from"]),
                "to": int(edge["to"]),
                "edge_type": "evidence_dependency",
                "description": edge["evidence"],
            }
        )
    return edges


def topological_order(nodes, edges):
    """Return a deterministic topological order or reject a cycle."""

    outgoing = defaultdict(list)
    indegree = {node: 0 for node in nodes}
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    queue = deque(sorted(node for node, count in indegree.items() if count == 0))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for target in sorted(outgoing[node]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(nodes):
        raise ValueError("The Day 30 dependency graph contains a cycle.")
    return order


def validate_graph(config, registry, edges):
    """Audit node coverage, edge direction and explicit config provenance."""

    scope = config["graph_scope"]
    nodes = list(range(int(scope["first_day"]), int(scope["last_day"]) + 1))
    if len(nodes) != int(scope["node_count"]):
        raise ValueError("Day 30 graph node count is inconsistent.")
    registry_nodes = sorted(int(entry["day"]) for entry in registry["entries"])
    if config["validation"]["require_every_node_in_registry"] and registry_nodes != nodes:
        raise ValueError("Day 30 nodes do not match the Day 29 registry.")

    pairs = [(edge["from"], edge["to"]) for edge in edges]
    if config["validation"]["require_unique_edges"] and len(pairs) != len(set(pairs)):
        raise ValueError("Day 30 contains a duplicate dependency edge.")
    for upstream, downstream in pairs:
        if upstream not in nodes or downstream not in nodes:
            raise ValueError(f"Out-of-scope edge: Day {upstream} -> Day {downstream}")
        if config["validation"]["require_forward_day_direction"] and upstream >= downstream:
            raise ValueError(f"Non-forward edge: Day {upstream} -> Day {downstream}")

    order = topological_order(nodes, edges)
    indegree = Counter(edge["to"] for edge in edges)
    roots = [node for node in nodes if indegree[node] == 0]
    if config["validation"]["require_all_nonroot_nodes_have_upstream"]:
        missing = [node for node in nodes if node not in roots and indegree[node] == 0]
        if missing:
            raise ValueError(f"Nonroot nodes without upstream evidence: {missing}")

    if config["validation"]["verify_evidence_day_token_in_downstream_config_from_day8"]:
        registry_by_day = {int(entry["day"]): entry for entry in registry["entries"]}
        for edge in edges:
            if edge["edge_type"] != "evidence_dependency" or edge["to"] < 8:
                continue
            config_path = PROJECT_ROOT / registry_by_day[edge["to"]]["primary_config"]
            config_text = config_path.read_text(encoding="utf-8").lower()
            token = f"day{edge['from']}"
            if token not in config_text:
                raise ValueError(
                    f"Day {edge['to']} config does not mention upstream {token}."
                )
    return nodes, roots, order


def validate_guardrails(config):
    """Keep graph interpretation explicit and non-scoring."""

    rules = config["validation"]
    if rules["forbid_filename_only_scientific_conclusions"] is not True:
        raise ValueError("Filename-only scientific inference must stay forbidden.")
    if rules["hidden_dependency_score_allowed"] is not False:
        raise ValueError("Hidden dependency scores are forbidden.")
    if config["graph_scope"]["include_day29_as_audit_tool"] is not False:
        raise ValueError("Day 29 is an audit tool, not a scientific evidence node.")


def main():
    config = load_config("configs/day30_evidence_dependency_graph.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    registry_path, registry = newest_registry(config)
    edges = build_edges(config)
    nodes, roots, order = validate_graph(config, registry, edges)

    teaching_count = sum(edge["edge_type"] == "teaching_prerequisite" for edge in edges)
    evidence_count = sum(edge["edge_type"] == "evidence_dependency" for edge in edges)
    incoming = Counter(edge["to"] for edge in edges)
    outgoing = Counter(edge["from"] for edge in edges)
    max_in = max(incoming.values())
    max_out = max(outgoing.values())
    fan_in = [day for day in nodes if incoming[day] == max_in]
    fan_out = [day for day in nodes if outgoing[day] == max_out]

    print("========== DAY 30 EVIDENCE-DEPENDENCY PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, model copy or optical calculation will occur.")
    print("No dependency output will be generated in this step.")
    print(f"Day 29 registry: {registry_path}")
    print(f"Graph scope: Day {nodes[0]}-Day {nodes[-1]} ({len(nodes)} nodes)")
    print()
    print("Edge classes:")
    print(f"  teaching_prerequisite: {teaching_count}")
    print(f"  evidence_dependency: {evidence_count}")
    print(f"  total: {len(edges)}")
    print()
    print(f"Root node(s): {roots}")
    print(f"Topological order: {order}")
    print(f"Largest evidence fan-in: {max_in} upstream days at {fan_in}")
    print(f"Largest fan-out: {max_out} downstream days at {fan_out}")
    print()
    print("[PASS] Day3-Day28 nodes match the complete Day 29 registry")
    print("[PASS] All dependency edges are unique and forward-directed")
    print("[PASS] Combined teaching/evidence graph is acyclic")
    print("[PASS] Every evidence edge is mentioned by the downstream Day8+ config")
    print("[PASS] Day29 remains an audit tool outside the scientific graph")
    print("[PASS] ZOS-API, source modification and hidden score forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
