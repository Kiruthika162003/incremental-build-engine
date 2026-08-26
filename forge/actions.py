"""Actions: a rule is a pure function from declared inputs to outputs.

An action declares the files it reads, the files it writes, and a
command identity that stands in for the tool and its flags. The
action key folds all three with the content digests of the declared
inputs, which is the single most important equation in the system:
same inputs, same command, same key, and a cache that stores
results by key never re-runs work the world has already paid for.
The key deliberately includes the command identity because the same
sources through a different compiler are a different build, and
deliberately excludes timestamps, hostnames, and order of
declaration, because none of those change the bytes that come out.
Execution runs the rule against the workspace and records what was
actually touched, so the hermeticity gap, declared minus observed,
is measured on every run rather than trusted.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.content import digest_pairs, digest_text
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass(frozen=True)
class Action:
    name: str
    command: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    rule: Callable[[Workspace], None]

    def __post_init__(self) -> None:
        if not self.writes:
            raise Invalid(
                f"{self.name} writes nothing; a build step with no "
                f"outputs is a side effect wearing a costume"
            )
        overlap = set(self.reads) & set(self.writes)
        if overlap:
            raise Invalid(
                f"{self.name} both reads and writes "
                f"{sorted(overlap)}; in-place mutation breaks caching"
            )

    def key(self, tree: Workspace) -> str:
        input_rows = [
            (path, tree.digest_of(path)) for path in self.reads
        ]
        fold = digest_pairs(input_rows)
        return digest_text(
            f"{self.command}|{fold}|{','.join(sorted(self.writes))}"
        )


@dataclass
class Observation:
    action: str
    read: set[str] = field(default_factory=set)
    wrote: set[str] = field(default_factory=set)

    def undeclared_reads(self, action: Action) -> list[str]:
        return sorted(self.read - set(action.reads))

    def undeclared_writes(self, action: Action) -> list[str]:
        return sorted(self.wrote - set(action.writes))

    def promised_but_silent(self, action: Action) -> list[str]:
        return sorted(set(action.writes) - self.wrote)


class ObservedWorkspace:
    """A watching wrapper: same tree, every touch recorded."""

    def __init__(self, tree: Workspace, observation: Observation):
        self._tree = tree
        self._seen = observation

    def read(self, path: str) -> bytes:
        self._seen.read.add(path)
        return self._tree.read(path)

    def read_text(self, path: str) -> str:
        self._seen.read.add(path)
        return self._tree.read_text(path)

    def write(self, path: str, payload: bytes) -> str:
        self._seen.wrote.add(path)
        return self._tree.write(path, payload)

    def write_text(self, path: str, text: str) -> str:
        self._seen.wrote.add(path)
        return self._tree.write_text(path, text)

    def exists(self, path: str) -> bool:
        return self._tree.exists(path)


def execute(action: Action, tree: Workspace) -> Observation:
    observation = Observation(action=action.name)
    action.rule(ObservedWorkspace(tree, observation))
    return observation
