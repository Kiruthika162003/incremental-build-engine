"""Graph pictures: the dot export draws what the queries describe.

Sometimes the answer to "why does the app depend on the fixtures"
is best delivered as a picture in a design review, and hand-drawn
diagrams of build graphs are stale before the marker dries. The
dot exporter renders the graph, or any subgraph reachable from a
goal, in Graphviz syntax with deterministic ordering, and the
styling is semantic rather than decorative: sources are boxes,
built targets are ellipses, and an optional highlight set draws
the named path in bold so a somepath answer becomes a red line
through the picture. The exporter refuses goals the graph does
not hold rather than drawing an empty page, because an empty
diagram in a slide deck reads as "no dependencies" to everyone
who was not in the room.
"""

from __future__ import annotations

from forge.errors import Missing
from forge.graph import Graph


def to_dot(
    graph: Graph,
    goal: str | None = None,
    highlight: list[str] | None = None,
    actions: set[str] | None = None,
) -> str:
    if goal is not None and goal not in graph.targets:
        raise Missing(
            f"no target named {goal}; an empty diagram reads as no "
            f"dependencies to everyone who was not in the room"
        )
    names = (
        graph.build_order(goal)
        if goal is not None
        else sorted(graph.targets)
    )
    built = actions or set()
    bold = set(highlight or [])
    bold_edges = set()
    if highlight:
        for index in range(len(highlight) - 1):
            bold_edges.add((highlight[index], highlight[index + 1]))
    lines = ["digraph forge {", "  rankdir=LR;"]
    for name in names:
        shape = "ellipse" if name in built else "box"
        style = ", penwidth=3" if name in bold else ""
        lines.append(f'  "{name}" [shape={shape}{style}];')
    for name in names:
        for need in sorted(graph.get(name).needs):
            if need not in names:
                continue
            emphasis = (
                " [penwidth=3, color=red]"
                if (name, need) in bold_edges
                else ""
            )
            lines.append(f'  "{name}" -> "{need}"{emphasis};')
    lines.append("}")
    return "\n".join(lines)
