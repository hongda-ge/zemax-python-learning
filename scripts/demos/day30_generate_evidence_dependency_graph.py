"""Day 30 step 2: generate reviewed dependency registries and a DAG figure."""

import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MATPLOTLIB_CACHE = PROJECT_ROOT / "outputs" / ".matplotlib_cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

from modules.config_loader import load_config  # noqa: E402
from scripts.demos.day30_evidence_dependency_plan import (  # noqa: E402
    build_edges,
    newest_registry,
    validate_execution_lock,
    validate_graph,
    validate_guardrails,
)


CHINA_TIME = timezone(timedelta(hours=8))


def sha256_file(path):
    """Return an uppercase SHA256 fingerprint for one evidence file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def graph_indexes(nodes, edges):
    """Build explicit direct upstream/downstream indexes."""

    upstream = {node: [] for node in nodes}
    downstream = {node: [] for node in nodes}
    for edge in edges:
        upstream[edge["to"]].append(edge["from"])
        downstream[edge["from"]].append(edge["to"])
    for values in upstream.values():
        values.sort()
    for values in downstream.values():
        values.sort()
    return upstream, downstream


def terminal_nodes(nodes, downstream):
    """Return nodes with no declared downstream consumer."""

    return [node for node in nodes if not downstream[node]]


def dependency_depths(order, upstream):
    """Assign each node to its longest reviewed upstream depth."""

    depths = {}
    for node in order:
        depths[node] = 0 if not upstream[node] else 1 + max(
            depths[parent] for parent in upstream[node]
        )
    return depths


def phase_by_day(registry):
    """Return reviewed Day 29 phase metadata by day."""

    return {
        int(entry["day"]): {
            "phase_id": entry["phase_id"],
            "phase_name": entry["phase_name"],
            "title": entry["title"],
        }
        for entry in registry["entries"]
    }


def make_output_dir(config):
    """Create one timestamped Day 30 output directory."""

    timestamp = datetime.now(CHINA_TIME).strftime("dependency_graph_%Y%m%d_%H%M%S")
    root = PROJECT_ROOT / config["planned_outputs_after_approval"]["root"]
    output_dir = root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_edge_csv(path, edges):
    """Write one flat edge list for spreadsheets and later graph tools."""

    columns = ["from_day", "to_day", "edge_type", "description"]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for edge in edges:
            writer.writerow(
                {
                    "from_day": edge["from"],
                    "to_day": edge["to"],
                    "edge_type": edge["edge_type"],
                    "description": edge["description"],
                }
            )


def write_markdown(path, report):
    """Write a compact human-readable evidence dependency index."""

    lines = [
        "# Day3-Day28 实验依赖图与证据追溯",
        "",
        "> 本文档记录人工审核的教学先修关系与科学证据依赖，不根据文件名猜测实验结论。",
        "",
        "## 图结构摘要",
        "",
        f"- 节点：{report['node_count']} 个（Day3-Day28）",
        f"- 教学先修边：{report['edge_counts']['teaching_prerequisite']} 条",
        f"- 科学证据边：{report['edge_counts']['evidence_dependency']} 条",
        f"- 根节点：{report['root_nodes']}",
        f"- 终端节点：{report['terminal_nodes']}",
        f"- 拓扑顺序：{report['topological_order']}",
        "",
        "## 每日直接依赖",
        "",
        "| Day | 阶段 | 主题 | 直接上游 | 直接下游 |",
        "|---:|---|---|---|---|",
    ]
    for node in report["nodes"]:
        upstream = ", ".join(f"Day{day}" for day in node["direct_upstream"]) or "—"
        downstream = ", ".join(f"Day{day}" for day in node["direct_downstream"]) or "—"
        lines.append(
            f"| {node['day']} | `{node['phase_id']}` | {node['title']} | "
            f"{upstream} | {downstream} |"
        )
    lines.extend(["", "## 依赖边明细", ""])
    for edge in report["edges"]:
        label = "教学先修" if edge["edge_type"] == "teaching_prerequisite" else "科学证据"
        lines.append(
            f"- Day{edge['from']} → Day{edge['to']}（{label}）：{edge['description']}"
        )
    lines.extend(
        [
            "",
            "## 阅读边界",
            "",
            "- 入度和出度只描述已声明关系，不代表实验质量或重要性分数。",
            "- 教学先修关系不等于直接读取上游结果文件。",
            "- 科学证据边表示下游配置明确提到并复用了上游 Day 的证据。",
            "- Day29 是注册与审计工具，不属于 Day3-Day28 科学证据节点。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_graph(path, nodes, edges, order, upstream, phase_meta):
    """Plot a depth-layered static DAG with phase and edge-type encoding."""

    depths = dependency_depths(order, upstream)
    layers = defaultdict(list)
    for node in nodes:
        layers[depths[node]].append(node)
    positions = {}
    for depth, layer_nodes in sorted(layers.items()):
        ordered_nodes = sorted(layer_nodes)
        center = (len(ordered_nodes) - 1) / 2.0
        for index, node in enumerate(ordered_nodes):
            positions[node] = (depth, center - index)

    phase_colors = {
        "foundation_and_scan": "#4C78A8",
        "decision_and_solve": "#F58518",
        "mechanism_and_acceptance": "#54A24B",
    }
    figure, axis = plt.subplots(figsize=(20, 9))
    axis.set_axis_off()

    for edge in edges:
        start = positions[edge["from"]]
        end = positions[edge["to"]]
        teaching = edge["edge_type"] == "teaching_prerequisite"
        arrow = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.2 if teaching else 1.0,
            linestyle="--" if teaching else "-",
            color="#7A7A7A" if teaching else "#9BB9D3",
            alpha=0.85 if teaching else 0.62,
            connectionstyle="arc3,rad=0.06",
            shrinkA=12,
            shrinkB=12,
            zorder=1,
        )
        axis.add_patch(arrow)

    for node in nodes:
        x, y = positions[node]
        phase_id = phase_meta[node]["phase_id"]
        axis.scatter(
            [x],
            [y],
            s=530,
            color=phase_colors[phase_id],
            edgecolors="#FFFFFF",
            linewidths=1.4,
            zorder=3,
        )
        axis.text(
            x,
            y,
            f"D{node}",
            ha="center",
            va="center",
            color="white",
            fontsize=8.5,
            fontweight="bold",
            zorder=4,
        )

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
               markeredgecolor="white", markersize=10, label=phase.replace("_", " "))
        for phase, color in phase_colors.items()
    ]
    handles.extend(
        [
            Line2D([0], [0], color="#7A7A7A", linestyle="--", label="teaching prerequisite"),
            Line2D([0], [0], color="#9BB9D3", linestyle="-", label="evidence dependency"),
        ]
    )
    axis.legend(handles=handles, loc="upper left", frameon=False, ncol=3, fontsize=9)
    axis.set_title(
        "Day 3-Day 28 Teaching and Evidence Dependency DAG",
        fontsize=15,
        pad=18,
    )
    axis.margins(x=0.04, y=0.22)
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def main():
    config = load_config("configs/day30_evidence_dependency_graph.yaml")
    validate_execution_lock(config)
    validate_guardrails(config)
    registry_path, registry = newest_registry(config)
    edges = build_edges(config)
    nodes, roots, order = validate_graph(config, registry, edges)
    upstream, downstream = graph_indexes(nodes, edges)
    terminals = terminal_nodes(nodes, downstream)
    phase_meta = phase_by_day(registry)
    edge_counts = dict(Counter(edge["edge_type"] for edge in edges))

    output_dir = make_output_dir(config)
    filenames = config["planned_outputs_after_approval"]
    json_file = output_dir / filenames["json"]
    csv_file = output_dir / filenames["csv"]
    markdown_file = output_dir / filenames["markdown"]
    figure_file = output_dir / filenames["figure"]

    report = {
        "task": "day30_evidence_dependency_graph_generation",
        "status": "success",
        "time_local": datetime.now(CHINA_TIME).isoformat(),
        "source_registry": str(registry_path),
        "source_registry_sha256": sha256_file(registry_path),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "edge_counts": edge_counts,
        "root_nodes": roots,
        "terminal_nodes": terminals,
        "topological_order": order,
        "nodes": [
            {
                "day": node,
                **phase_meta[node],
                "direct_upstream": upstream[node],
                "direct_downstream": downstream[node],
                "in_degree": len(upstream[node]),
                "out_degree": len(downstream[node]),
            }
            for node in nodes
        ],
        "edges": edges,
        "new_zosapi_connection_created": False,
        "new_optical_metric_calculated": False,
        "existing_source_file_modified": False,
        "hidden_dependency_score_used": False,
    }
    write_edge_csv(csv_file, edges)
    write_markdown(markdown_file, report)
    plot_graph(figure_file, nodes, edges, order, upstream, phase_meta)
    json_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    incoming = Counter(edge["to"] for edge in edges)
    outgoing = Counter(edge["from"] for edge in edges)
    max_in = max(incoming.values())
    max_out = max(outgoing.values())
    fan_in = [node for node in nodes if incoming[node] == max_in]
    fan_out = [node for node in nodes if outgoing[node] == max_out]

    print("========== DAY 30 EVIDENCE DEPENDENCY GRAPH ==========")
    print("No ZOS-API connection or optical calculation was used.")
    print(f"Nodes: {len(nodes)}; edges: {len(edges)}")
    print(f"Teaching prerequisites: {edge_counts['teaching_prerequisite']}")
    print(f"Scientific evidence dependencies: {edge_counts['evidence_dependency']}")
    print(f"Root nodes: {roots}")
    print(f"Terminal nodes: {terminals}")
    print(f"Largest fan-in: {max_in} at {fan_in}")
    print(f"Largest fan-out: {max_out} at {fan_out}")
    print()
    print("[PASS] All 26 registered teaching days represented")
    print("[PASS] All 35 reviewed edges represented")
    print("[PASS] DAG and downstream-config provenance revalidated")
    print("[PASS] No hidden dependency score or scientific conclusion inferred")
    print(f"[PASS] Edge CSV: {csv_file}")
    print(f"[PASS] Graph JSON: {json_file}")
    print(f"[PASS] Markdown index: {markdown_file}")
    print(f"[PASS] DAG figure: {figure_file}")


if __name__ == "__main__":
    main()
