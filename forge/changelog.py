"""The generated changelog: what shipped is computed, not remembered.

Release notes written from memory list what the author remembers
shipping, which is a subset with a bias. The generator computes
instead: the tree diff between two releases yields what moved,
arrived, and left the package; the provenance manifests yield
which sources changed underneath each moved artifact; and the
changelog is the join, each shipped change traced to the source
edits that caused it. The untraceable line is kept, not hidden:
an artifact that changed with no source edit under it means the
toolchain or an undeclared input moved, and that sentence belongs
in release notes more than any feature does. The tone is
inventory, not marketing, because the changelog's reader is
usually someone deciding whether to upgrade during an incident.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.treediff import diff_trees


@dataclass(frozen=True)
class ReleaseSnapshot:
    version: str
    tree: dict[str, bytes]
    source_digests: dict[str, str]


def _source_changes(
    before: ReleaseSnapshot, after: ReleaseSnapshot
) -> list[str]:
    return sorted(
        path
        for path in set(before.source_digests)
        | set(after.source_digests)
        if before.source_digests.get(path)
        != after.source_digests.get(path)
    )


def generate(
    before: ReleaseSnapshot, after: ReleaseSnapshot
) -> str:
    if before.version == after.version:
        raise Invalid(
            "two snapshots of one version have no changelog between "
            "them"
        )
    delta = diff_trees(before.tree, after.tree)
    sources = _source_changes(before, after)
    lines = [f"changes from {before.version} to {after.version}"]
    if delta.quiet():
        lines.append(
            "  no shipped artifact changed; this is a re-tag"
        )
        return "\n".join(lines)
    for path in delta.modified:
        lines.append(f"  changed: {path}")
    for old, new in delta.moved:
        lines.append(f"  moved: {old} -> {new}")
    for path in delta.added:
        lines.append(f"  new: {path}")
    for path in delta.removed:
        lines.append(f"  gone: {path}")
    if sources:
        lines.append(
            f"  driven by {len(sources)} source edits: "
            f"{', '.join(sources)}"
        )
    elif delta.modified:
        lines.append(
            "  WARNING: artifacts changed with no source edit "
            "underneath; the toolchain or an undeclared input "
            "moved, and that sentence belongs here more than any "
            "feature does"
        )
    return "\n".join(lines)
