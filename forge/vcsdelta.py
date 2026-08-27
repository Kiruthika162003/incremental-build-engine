"""From diff to targets: the commit's paths become the build's work.

CI receives a list of changed paths and must decide what to build,
and the mapping is less obvious than it looks. A source path maps
to the targets that read it. A BUILD file path maps to every
target its package declares, because a rule edit can change any of
them. A deleted path maps to its readers too, who are about to
fail loudly and should do so in this build rather than the next. A
path nothing owns maps to nothing, and the report says so per
path rather than silently, because the day someone renames a
directory, the silent no-op is how a week of commits builds
nothing and everyone finds out on Friday. The output is the seed
set for selection and the reason each seed is in it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class DeltaMapper:
    graph: Graph
    package_targets: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    readers: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def declare_package(
        self, build_file: str, targets: tuple[str, ...]
    ) -> None:
        if build_file in self.package_targets:
            raise Invalid(f"{build_file} is already declared")
        for target in targets:
            self.graph.get(target)
        self.package_targets[build_file] = targets

    def declare_readers(
        self, path: str, targets: tuple[str, ...]
    ) -> None:
        for target in targets:
            self.graph.get(target)
        self.readers[path] = targets

    def map_change(self, path: str, deleted: bool = False) -> tuple:
        """Returns (seeds, reason)."""
        if path in self.package_targets:
            return (
                self.package_targets[path],
                "a BUILD edit can change any rule in its package",
            )
        if path in self.readers:
            if deleted:
                return (
                    self.readers[path],
                    "deleted; its readers should fail in this build, "
                    "not the next",
                )
            return (self.readers[path], "source read by these targets")
        return ((), "nothing owns this path")

    def seeds_for(
        self, changes: list[tuple[str, bool]]
    ) -> tuple[list[str], list[str]]:
        seeds: set[str] = set()
        orphaned: list[str] = []
        for path, deleted in changes:
            found, _ = self.map_change(path, deleted)
            if not found:
                orphaned.append(path)
            seeds.update(found)
        return sorted(seeds), orphaned

    def report(self, changes: list[tuple[str, bool]]) -> str:
        lines = []
        for path, deleted in sorted(changes):
            seeds, reason = self.map_change(path, deleted)
            shown = ", ".join(seeds) if seeds else "NOTHING"
            lines.append(f"{path} -> {shown} ({reason})")
        seeds, orphaned = self.seeds_for(changes)
        lines.append(
            f"{len(seeds)} seed targets, {len(orphaned)} orphan paths"
        )
        if orphaned:
            lines.append(
                "orphans deserve a look before Friday: "
                + ", ".join(orphaned)
            )
        return "\n".join(lines)
