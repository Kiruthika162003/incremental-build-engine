"""Orphan files: in the tree, read by nothing, explained by nobody.

Repositories accumulate files the build stopped reading years
ago, and they cost more than disk: every new engineer reads
them, every refactor routes around them, and every grep
returns them as false leads. The census crosses the tree
against the union of every target's declared reads and the
build files themselves, and what remains is orphaned, reported
with its size and its last-known reader when the history
remembers one, because "delete util_old.c, unread since the
parser rewrite" is an actionable sentence while "cleanup" is
not. The exemption list is short and principled, documentation
and licenses serve humans rather than targets, and everything
else unread gets the same two-option verdict: wire it back in
deliberately, or delete it deliberately, since the third
option, keeping it ambient, is the one the census exists to
end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

HUMAN_SERVING = (".md", "LICENSE", "NOTICE")


@dataclass
class OrphanCensus:
    tree_files: dict[str, int]
    declared_reads: set[str]
    build_files: set[str]
    last_reader: dict[str, str] = field(default_factory=dict)

    def orphans(self) -> list[str]:
        if not self.tree_files:
            raise Invalid("an empty tree has no orphans")
        found = []
        for path in sorted(self.tree_files):
            if path in self.declared_reads:
                continue
            if path in self.build_files:
                continue
            if path.endswith(HUMAN_SERVING) or any(
                marker in path for marker in ("LICENSE", "NOTICE")
            ):
                continue
            found.append(path)
        return found

    def report(self) -> str:
        found = self.orphans()
        if not found:
            return (
                "every file is read by a target, a build file, "
                "or a human; the tree is spoken for"
            )
        total_bytes = sum(
            self.tree_files[path] for path in found
        )
        lines = [
            f"{len(found)} orphan(s) holding {total_bytes} "
            "byte(s) of ambiguity"
        ]
        for path in found:
            history = self.last_reader.get(path)
            story = (
                f"unread since {history}"
                if history
                else "no reader in living memory"
            )
            lines.append(
                f"  {path} ({self.tree_files[path]} bytes): "
                f"{story}; wire it back in deliberately or "
                "delete it deliberately"
            )
        lines.append(
            "the third option, keeping it ambient, is the one "
            "this census exists to end"
        )
        return "\n".join(lines)
