"""Discovered dependencies: the compiler knows what it read; believe it late.

Header dependencies cannot be declared up front without lying in
one direction or the other: declare too few and the cache serves
stale objects, declare the union of everything and every header
edit rebuilds the world. The depfile protocol splits the timeline:
the first build runs with the declared inputs and records what the
rule actually read, the discovery is saved beside the cache entry,
and every later build checks the discovered set's digests before
trusting a hit. This is sound because the first run's key was
honest for the first run, and the discovered set only ever grows
the check, never shrinks it; the day the rule reads a new file, the
observed set changes, the old discovery misses, and the rebuild
re-discovers. Believing the compiler early is a guess; believing
it after it has run is bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.content import ContentStore
from forge.workspace import Workspace


@dataclass
class Discovery:
    outputs: dict[str, str]
    read_digests: dict[str, str]
    cost: int


@dataclass
class DiscoveringCache:
    store: ContentStore = field(default_factory=ContentStore)
    discoveries: dict[str, Discovery] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0
    stale_discoveries: int = 0

    def _discovery_key(self, action: Action) -> str:
        return f"{action.name}|{action.command}"

    def run(self, action: Action, tree: Workspace, cost: int = 1) -> str:
        key = self._discovery_key(action)
        held = self.discoveries.get(key)
        if held is not None:
            current = {
                path: tree.digest_of(path)
                for path in held.read_digests
                if tree.exists(path)
            }
            if current == held.read_digests:
                for path, digest in held.outputs.items():
                    tree.write(path, self.store.get(digest))
                self.hits += 1
                return "hit"
            self.stale_discoveries += 1
        observation = execute(action, tree)
        self.misses += 1
        self.discoveries[key] = Discovery(
            outputs={
                path: self.store.put(tree.read(path))
                for path in observation.wrote
            },
            read_digests={
                path: tree.digest_of(path) for path in observation.read
            },
            cost=cost,
        )
        return "miss"

    def discovered_reads(self, action: Action) -> list[str]:
        held = self.discoveries.get(self._discovery_key(action))
        if held is None:
            return []
        return sorted(held.read_digests)

    def ledger(self) -> str:
        return (
            f"{self.hits} hits, {self.misses} misses, "
            f"{self.stale_discoveries} discoveries went stale"
        )
