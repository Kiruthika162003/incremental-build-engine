"""The build seal: one fingerprint for sources, tools, and graph together.

"Same build" is a three-part question wearing one word: same
source tree, same toolchain, same graph shape. The seal digests
each part separately and folds the three into one fingerprint,
so two machines can compare a single string, and when the
strings differ the diff names the part instead of shrugging,
because "the builds differ" starts an afternoon of archaeology
while "same sources, same graph, toolchain differs: gcc-13.1
against gcc-13.2" starts a one-line fix. The component digests
travel with the seal for exactly that purpose; a fingerprint
that cannot explain its own mismatches is a checksum, not a
seal.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.content import digest_pairs, digest_text
from forge.errors import Invalid


@dataclass(frozen=True)
class BuildSeal:
    tree_digest: str
    tool_digest: str
    graph_digest: str

    def fingerprint(self) -> str:
        return digest_pairs(
            [
                ("graph", self.graph_digest),
                ("tools", self.tool_digest),
                ("tree", self.tree_digest),
            ]
        )


def seal_build(
    tree_digest: str,
    toolchain: dict[str, str],
    target_shapes: dict[str, tuple[str, ...]],
) -> BuildSeal:
    if not toolchain:
        raise Invalid("a build with no tools built nothing")
    tool_digest = digest_pairs(sorted(toolchain.items()))
    graph_digest = digest_pairs(
        sorted(
            (name, digest_text("|".join(needs)))
            for name, needs in target_shapes.items()
        )
    )
    return BuildSeal(
        tree_digest=tree_digest,
        tool_digest=tool_digest,
        graph_digest=graph_digest,
    )


def compare(
    ours: BuildSeal,
    theirs: BuildSeal,
    our_tools: dict[str, str] | None = None,
    their_tools: dict[str, str] | None = None,
) -> str:
    if ours.fingerprint() == theirs.fingerprint():
        return (
            f"same build: {ours.fingerprint()[:12]} on both "
            "machines"
        )
    parts = []
    if ours.tree_digest != theirs.tree_digest:
        parts.append("sources differ")
    if ours.graph_digest != theirs.graph_digest:
        parts.append("graph shape differs")
    if ours.tool_digest != theirs.tool_digest:
        detail = "toolchain differs"
        if our_tools is not None and their_tools is not None:
            moved = sorted(
                f"{tool}: {our_tools[tool]} against "
                f"{their_tools.get(tool, 'absent')}"
                for tool in our_tools
                if our_tools[tool] != their_tools.get(tool)
            )
            extra = sorted(
                f"{tool}: absent against {their_tools[tool]}"
                for tool in their_tools
                if tool not in our_tools
            )
            named = "; ".join(moved + extra)
            detail = f"toolchain differs ({named})"
        parts.append(detail)
    same = [
        label
        for label, mine, yours in (
            ("sources", ours.tree_digest, theirs.tree_digest),
            ("graph", ours.graph_digest, theirs.graph_digest),
            ("toolchain", ours.tool_digest, theirs.tool_digest),
        )
        if mine == yours
    ]
    prefix = (
        f"same {' and '.join(same)}, " if same else ""
    )
    return prefix + "; ".join(parts)
