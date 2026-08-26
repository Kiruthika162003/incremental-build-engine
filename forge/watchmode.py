"""Watch mode: the build that reacts owes its speed to knowing what moved.

An editor saves a file; the watcher's job is to rebuild the least
that makes the world consistent again, and to know that number
before running anything. The watcher keeps the digest of every
source it has seen, diffs the tree against that memory on each
poll, and maps changed sources to their downstream cone through the
graph; everything outside the cone is provably untouchable and is
not even visited. Deletes are changes too, and a delete whose file
some rule still reads is surfaced as a broken world rather than a
rebuild, because rebuilding into a hole produces an error message
about the hole's neighbour. The session ledger tracks polls that
found nothing, since a watcher's common case is silence and its
cost in the quiet hours is the number that decides whether it may
run on laptops.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.engine import BuildReport, Engine
from forge.errors import Missing
from forge.workspace import Workspace


@dataclass
class Poll:
    changed: list[str]
    deleted: list[str]
    cone: list[str]
    report: BuildReport | None
    broken: str | None = None

    def line(self) -> str:
        if self.broken:
            return f"broken world: {self.broken}"
        if not self.changed and not self.deleted:
            return "quiet"
        moved = ", ".join(self.changed + self.deleted)
        rebuilt = len(self.report.ran) if self.report else 0
        return (
            f"{moved} moved; cone of {len(self.cone)}, "
            f"{rebuilt} rebuilt"
        )


@dataclass
class Watcher:
    engine: Engine
    goal: str
    remembered: dict[str, str] = field(default_factory=dict)
    polls: int = 0
    quiet_polls: int = 0
    rebuilds: int = 0

    def _sources(self) -> list[str]:
        return [
            name
            for name in self.engine.graph.build_order(self.goal)
            if name not in self.engine.actions
        ]

    def prime(self, tree: Workspace) -> BuildReport:
        """The first build: remember every source, build everything."""
        for source in self._sources():
            self.remembered[source] = tree.digest_of(source)
        return self.engine.build(self.goal, tree)

    def poll(self, tree: Workspace) -> Poll:
        self.polls += 1
        changed = []
        deleted = []
        for source in self._sources():
            if not tree.exists(source):
                deleted.append(source)
                continue
            digest = tree.digest_of(source)
            if self.remembered.get(source) != digest:
                changed.append(source)
                self.remembered[source] = digest
        if deleted:
            return Poll(
                changed=changed,
                deleted=deleted,
                cone=[],
                report=None,
                broken=f"{deleted[0]} was deleted but rules still read it",
            )
        if not changed:
            self.quiet_polls += 1
            return Poll(changed=[], deleted=[], cone=[], report=None)
        cone: set[str] = set()
        for source in changed:
            cone.update(self.engine.graph.downstream_of(source))
        report = self.engine.build(self.goal, tree)
        self.rebuilds += 1
        touched = set(report.ran)
        if not touched.issubset(cone):
            raise Missing(
                f"rebuilt outside the cone: {sorted(touched - cone)}"
            )
        return Poll(
            changed=changed,
            deleted=[],
            cone=sorted(cone),
            report=report,
        )

    def session(self) -> str:
        return (
            f"{self.polls} polls, {self.quiet_polls} quiet, "
            f"{self.rebuilds} rebuilds"
        )
