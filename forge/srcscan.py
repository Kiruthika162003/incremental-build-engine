"""The include scanner: a fast guess, graded against the truth.

Depfiles are exact but arrive after the first build; a scanner
reads the source text up front and guesses the includes, which
lets the graph warn about missing headers before anything runs.
The catch is that scanning is an approximation of the language:
it sees the include the preprocessor would have skipped inside a
disabled branch, and it cannot see the include a macro assembles
from pieces. Both failure modes are real, so the scanner is never
the authority; it is the early warning, and the grader compares
its guess against the observed truth from an actual run, reporting
overapproximations that cause needless rebuilds and
underapproximations that would cause stale ones. The grade is the
policy input: a codebase whose scanner underapproximates has
macro-assembled includes, and no cache should trust a scan there.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Missing
from forge.workspace import Workspace


def scan_includes(tree: Workspace, path: str) -> list[str]:
    if not tree.exists(path):
        raise Missing(f"cannot scan {path}; it does not exist")
    found = []
    for raw in tree.read_text(path).splitlines():
        line = raw.strip()
        if line.startswith('include "') and line.endswith('"'):
            name = line[len('include "') : -1]
            if name not in found:
                found.append(name)
    return found


def transitive_scan(tree: Workspace, path: str) -> list[str]:
    seen: list[str] = []
    frontier = [path]
    while frontier:
        current = frontier.pop(0)
        for include in scan_includes(tree, current):
            if include not in seen and tree.exists(include):
                seen.append(include)
                frontier.append(include)
    return sorted(seen)


@dataclass(frozen=True)
class ScanGrade:
    scanned: tuple[str, ...]
    observed: tuple[str, ...]

    def overapproximated(self) -> list[str]:
        """Scanned but never read: needless rebuild triggers."""
        return sorted(set(self.scanned) - set(self.observed))

    def underapproximated(self) -> list[str]:
        """Read but never scanned: stale-build risks."""
        return sorted(set(self.observed) - set(self.scanned))

    def verdict(self) -> str:
        over = self.overapproximated()
        under = self.underapproximated()
        if not over and not under:
            return "exact: the scan may seed the graph"
        if under:
            return (
                f"UNSAFE: the scan missed {under}; a cache trusting "
                f"it would serve stale objects"
            )
        return (
            f"safe but wasteful: {over} would trigger needless "
            f"rebuilds"
        )


def grade(
    tree: Workspace, source: str, observed_reads: list[str]
) -> ScanGrade:
    scanned = transitive_scan(tree, source)
    observed = sorted(
        path for path in observed_reads if path != source
    )
    return ScanGrade(
        scanned=tuple(scanned), observed=tuple(observed)
    )
