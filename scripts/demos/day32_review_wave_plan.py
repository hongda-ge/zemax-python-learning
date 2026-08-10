"""Day 32 step 1: plan dependency-safe review waves without execution."""

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
    """Calculate an uppercase SHA256 fingerprint."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_execution_lock(config):
    """Allow reports while keeping Day 32 offline and non-executing."""

    execution = config["execution"]
    if any(not isinstance(value, bool) for value in execution.values()):
        raise ValueError("Every Day 32 execution switch must be Boolean.")
    if execution.get("allow_wave_report_generation") is not True:
        raise ValueError("Day 32 wave report generation must be explicitly approved.")
    prohibited = [
        key
        for key, value in execution.items()
        if key != "allow_wave_report_generation" and value is not False
    ]
    if prohibited:
        raise ValueError("Day 32 prohibited action enabled: " + ", ".join(prohibited))


def load_sources(config):
    """Load and verify the frozen Day 31 impact report and Day 30 DAG."""

    source = config["source"]
    impact_path = PROJECT_ROOT / source["day31_impact_report"]
    if not impact_path.is_file():
        raise FileNotFoundError(f"Day 31 impact report not found: {impact_path}")
    if sha256_file(impact_path) != source["day31_impact_sha256"]:
        raise ValueError("The frozen Day 31 impact SHA256 is incorrect.")
    impact = json.loads(impact_path.read_text(encoding="utf-8"))
    checks = (
        impact["task"] == source["day31_expected_task"],
        impact["status"] == source["day31_expected_status"],
        impact["scenario_count"] == source["day31_expected_scenario_count"],
        len(impact["review_rows"]) == source["day31_expected_review_row_count"],
        impact["automatic_execution_performed"] is False,
    )
    if not all(checks):
        raise ValueError("The frozen Day 31 impact metadata is incorrect.")

    graph_path = Path(impact["source_day30_graph"])
    if not graph_path.is_file():
        raise FileNotFoundError(f"Day 30 graph not found: {graph_path}")
    if sha256_file(graph_path) != source["day30_graph_sha256"]:
        raise ValueError("The Day 30 graph no longer matches Day 32 provenance.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    return impact_path, impact, graph_path, graph


def induced_edges(review_nodes, graph):
    """Return only dependency edges whose endpoints are both under review."""

    review_set = set(review_nodes)
    return [
        (int(edge["from"]), int(edge["to"]))
        for edge in graph["edges"]
        if int(edge["from"]) in review_set and int(edge["to"]) in review_set
    ]


def build_waves(review_nodes, graph):
    """Use Kahn-style releases to build deterministic dependency waves."""

    review_set = set(review_nodes)
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
            raise ValueError("The induced Day 32 review graph contains a cycle.")
        waves.append(ready)
        remaining -= set(ready)
    if set(node for wave in waves for node in wave) != review_set:
        raise ValueError("Day 32 wave construction lost a review node.")
    return waves, edges


def build_wave_results(config, impact, graph):
    """Build and audit waves for all reviewed Day 31 scenarios."""

    execution_class = {
        int(row["day"]): row["execution_class"] for row in impact["review_rows"]
    }
    expected = config["expected_scenarios"]
    results = []
    for scenario in impact["scenarios"]:
        scenario_id = scenario["scenario_id"]
        if scenario_id not in expected:
            raise ValueError(f"Unexpected Day 31 scenario: {scenario_id}")
        review_nodes = [int(day) for day in scenario["review_order"]]
        waves, edges = build_waves(review_nodes, graph)
        wave_index = {
            node: wave_number
            for wave_number, wave in enumerate(waves, start=1)
            for node in wave
        }
        for source, target in edges:
            if wave_index[source] >= wave_index[target]:
                raise ValueError(
                    f"Affected edge Day{source}->Day{target} does not move forward."
                )
        if waves[0] != [int(scenario["changed_day"])]:
            raise ValueError(f"Scenario {scenario_id} must start from its changed source.")
        rule = expected[scenario_id]
        checks = (
            len(review_nodes) == int(rule["review_node_count"]),
            len(waves) == int(rule["wave_count"]),
            max(len(wave) for wave in waves) == int(rule["maximum_wave_width"]),
        )
        if not all(checks):
            raise ValueError(f"Scenario {scenario_id} wave expectations changed.")
        wave_details = []
        for number, wave in enumerate(waves, start=1):
            wave_details.append(
                {
                    "wave": number,
                    "days": wave,
                    "uses_zosapi_days": [
                        day for day in wave if execution_class[day] == "uses_zosapi"
                    ],
                    "offline_only_days": [
                        day for day in wave if execution_class[day] == "offline_only"
                    ],
                }
            )
        results.append(
            {
                "scenario_id": scenario_id,
                "changed_day": int(scenario["changed_day"]),
                "review_node_count": len(review_nodes),
                "affected_edge_count": len(edges),
                "wave_count": len(waves),
                "maximum_wave_width": max(len(wave) for wave in waves),
                "waves": wave_details,
            }
        )
    return results


def validate_policies(config):
    """Separate dependency parallelism from actual resource concurrency."""

    policy = config["wave_policy"]
    required_true = (
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
            "hidden_priority_score_allowed",
            "resource_parallelism_claim_allowed",
            "automatic_execution_allowed",
        )
        if validation.get(key) is not False
    ]
    if invalid:
        raise ValueError("Day 32 policy validation failed: " + ", ".join(invalid))


def print_introduction(config):
    """Print the fixed teaching introduction requested for Day32+."""

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
    config = load_config("configs/day32_review_wave_planning.yaml")
    validate_execution_lock(config)
    validate_policies(config)
    impact_path, impact, graph_path, graph = load_sources(config)
    results = build_wave_results(config, impact, graph)

    print_introduction(config)
    print("========== DAY 32 REVIEW-WAVE PLAN ==========")
    print("Mode: PLAN ONLY")
    print("No ZOS-API connection, optical calculation or task execution will occur.")
    print("Waves describe dependency readiness, not actual resource concurrency.")
    print(f"Day 31 impact report: {impact_path}")
    print(f"Day 30 dependency graph: {graph_path}")
    print()
    for result in results:
        print(
            f"{result['scenario_id']}: nodes={result['review_node_count']}, "
            f"waves={result['wave_count']}, max width={result['maximum_wave_width']}"
        )
        for wave in result["waves"]:
            print(
                f"  Wave {wave['wave']:02d}: days={wave['days']}; "
                f"ZOS-API={wave['uses_zosapi_days']}; offline={wave['offline_only_days']}"
            )
    print()
    print("[PASS] Frozen Day 31 and Day 30 fingerprints verified")
    print("[PASS] Every review node appears in exactly one wave")
    print("[PASS] Every affected dependency points from an earlier to a later wave")
    print("[PASS] Each first wave contains only the changed source")
    print("[PASS] Execution classes retained without automatic execution")
    print("[PASS] Resource concurrency and hidden priority claims forbidden")
    print("PLAN ONLY finished. No output was created.")


if __name__ == "__main__":
    main()
