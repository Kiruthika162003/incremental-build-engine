"""The I/O census: the hottest file and the hungriest action, by count.

The workspace already meters every read and write; the census
turns those counters into the two names worth knowing. The
hottest file is the one read by the most distinct actions, and it
is the build's true center of gravity: a header everyone parses,
a config everyone loads, and any edit to it moves the whole
graph, which makes it the first candidate for splitting or
precompiling. The hungriest action is the one reading the most
distinct files, usually a link or an archive step, and it bounds
how well the build can ever be distributed, because an action
that touches nine hundred files ships nine hundred files to any
remote worker that runs it. The census also flags write
collisions as a courtesy, files written by more than one action,
since the conflict detector owns that verdict but the census
sees it first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class IoCensus:
    reads_by_action: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    writes_by_action: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )

    def observe(
        self,
        action: str,
        reads: tuple[str, ...],
        writes: tuple[str, ...],
    ) -> None:
        if action in self.reads_by_action:
            raise Invalid(f"{action} was already observed")
        self.reads_by_action[action] = tuple(sorted(set(reads)))
        self.writes_by_action[action] = tuple(sorted(set(writes)))

    def _readers(self) -> dict[str, list[str]]:
        readers: dict[str, list[str]] = {}
        for action, reads in self.reads_by_action.items():
            for path in reads:
                readers.setdefault(path, []).append(action)
        return readers

    def hottest_file(self) -> str:
        readers = self._readers()
        if not readers:
            raise Invalid("nothing was read; there is no census")
        path, actions = max(
            readers.items(),
            key=lambda row: (len(row[1]), row[0]),
        )
        return (
            f"{path} is read by {len(actions)} action(s); every "
            "edit to it moves that many rebuilds: split it or "
            "precompile it"
        )

    def hungriest_action(self) -> str:
        if not self.reads_by_action:
            raise Invalid("no actions observed")
        action, reads = max(
            self.reads_by_action.items(),
            key=lambda row: (len(row[1]), row[0]),
        )
        return (
            f"{action} reads {len(reads)} file(s); that is the "
            "freight bill any remote worker pays to run it"
        )

    def write_collisions(self) -> list[str]:
        writers: dict[str, list[str]] = {}
        for action, writes in self.writes_by_action.items():
            for path in writes:
                writers.setdefault(path, []).append(action)
        return sorted(
            f"{path} written by {', '.join(sorted(actions))}"
            for path, actions in writers.items()
            if len(actions) > 1
        )

    def report(self) -> str:
        lines = [self.hottest_file(), self.hungriest_action()]
        collisions = self.write_collisions()
        if collisions:
            lines.append(
                f"{len(collisions)} write collision(s) for the "
                "conflict detector:"
            )
            lines.extend(f"  {entry}" for entry in collisions)
        return "\n".join(lines)
