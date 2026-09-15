"""Construct and render the four tool-specific RQ1 causal graphs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import networkx as nx


CAUSAL_NODES = (
    "app_popularity_encoded",
    "apk_size_scaled",
    "reporting_policy",
    "reported_alert_is_third_party",
    "verdict",
)

CAUSAL_EDGES = (
    ("app_popularity_encoded", "apk_size_scaled"),
    ("app_popularity_encoded", "reported_alert_is_third_party"),
    ("app_popularity_encoded", "verdict"),
    ("apk_size_scaled", "reported_alert_is_third_party"),
    ("apk_size_scaled", "verdict"),
    ("reporting_policy", "reported_alert_is_third_party"),
    ("reporting_policy", "verdict"),
    ("reported_alert_is_third_party", "verdict"),
)

NODE_LABELS = {
    "app_popularity_encoded": "App popularity\n(confounder)",
    "apk_size_scaled": "APK size\n(confounder)",
    "reporting_policy": "Reporting policy\n(dev-only vs dev + third-party)",
    "reported_alert_is_third_party": "Reported alert provenance\n(dev vs third-party)",
    "verdict": "Alert verdict\n(outcome; mean = precision)",
}

NODE_COLORS = {
    "app_popularity_encoded": "#dbeafe",
    "apk_size_scaled": "#dbeafe",
    "reporting_policy": "#fde68a",
    "reported_alert_is_third_party": "#ede9fe",
    "verdict": "#dcfce7",
}


def build_causal_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(CAUSAL_NODES)
    graph.add_edges_from(CAUSAL_EDGES)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("The RQ1 graph specification must be acyclic")
    return graph


def graph_source(tool_name: str):
    graph = build_causal_graph()
    lines = [
        "digraph {",
        f'  label="{tool_name} reporting-policy causal graph\\nDirections come from SLR and general domain knowledge";',
        "  labelloc=t;",
        "  rankdir=LR;",
        "  graph [pad=0.25, nodesep=0.45, ranksep=1.15];",
        '  node [shape=box, style="rounded,filled", color="#315a7d", fontname="Helvetica"];',
        '  edge [color="#334155", fontname="Helvetica", fontsize=9];',
    ]
    for node in graph.nodes:
        label = NODE_LABELS[node].replace("\n", "\\n")
        lines.append(
            f'  "{node}" [label="{label}", fillcolor="{NODE_COLORS[node]}"];'
        )
    for source, target in graph.edges:
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_causal_graph(
    tool_name: str,
    output_path: Path,
):
    """Render one SVG directly from memory without creating an intermediate DOT file."""

    dot_binary = shutil.which("dot")
    if dot_binary is None:
        raise RuntimeError("Graphviz 'dot' executable is required to render graph images")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [dot_binary, "-Tsvg", "-o", str(output_path)],
        input=graph_source(tool_name),
        text=True,
        check=True,
    )
