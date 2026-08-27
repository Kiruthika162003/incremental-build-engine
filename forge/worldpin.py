"""World pinning: the build sees one revision, however long it runs.

A forty-minute build that reads files as they are races every
commit that lands during those forty minutes, and loses by
producing an artifact from a world that never existed: half of
revision 100, half of 103. The pin fixes the world at build
start: every read is answered as of the pinned revision, and
arrivals during the build land in the repository without
leaking into the running build's view. The violation detector
is the part teams skip and regret: it compares each content
the build actually consumed against the pinned world, and a
mismatch names the file and both revisions, because a torn
world is not a theoretical hazard, it is a Tuesday artifact
that no revision can reproduce, which is the worst provenance
a binary can have. Ending a build reports what arrived while
it ran, so the next build knows it starts from a moved world.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Stale


@dataclass
class PinnedWorld:
    revision: int
    files: dict[str, str]
    arrivals: list[tuple[int, str, str]] = field(
        default_factory=list
    )
    reads_served: int = 0

    def read(self, path: str) -> str:
        content = self.files.get(path)
        if content is None:
            raise Invalid(
                f"{path} does not exist at revision "
                f"{self.revision}"
            )
        self.reads_served += 1
        return content

    def commit_arrives(
        self, revision: int, path: str, content: str
    ) -> str:
        if revision <= self.revision:
            raise Invalid(
                f"revision {revision} is not after the pin at "
                f"{self.revision}"
            )
        self.arrivals.append((revision, path, content))
        return (
            f"r{revision} touching {path} lands in the repo, "
            "not in the running build's view"
        )

    def audit_consumed(
        self, consumed: dict[str, str]
    ) -> str:
        torn = []
        for path, content in sorted(consumed.items()):
            pinned = self.files.get(path)
            if pinned is None or content == pinned:
                continue
            culprit = next(
                (
                    revision
                    for revision, arrived_path, arrived in self.arrivals
                    if arrived_path == path
                    and arrived == content
                ),
                None,
            )
            source = (
                f"r{culprit}" if culprit else "no known revision"
            )
            torn.append(f"{path}: pinned r{self.revision}, consumed {source}")
        if torn:
            raise Stale(
                "TORN WORLD: "
                + "; ".join(torn)
                + "; the artifact mixes revisions and no "
                "revision can reproduce it, the worst "
                "provenance a binary can have"
            )
        return (
            f"every consumed byte matches revision "
            f"{self.revision}; the world held"
        )

    def finish(self) -> str:
        if not self.arrivals:
            return (
                f"built at r{self.revision}; nothing moved "
                "underneath"
            )
        latest = max(revision for revision, _, _ in self.arrivals)
        return (
            f"built at r{self.revision} while "
            f"{len(self.arrivals)} commit(s) landed, repo now "
            f"at r{latest}; the next build starts from a moved "
            "world"
        )
