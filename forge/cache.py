"""The action cache: work the world already paid for is never repurchased.

A cache entry maps an action key to the digests of the outputs that
key produced, with the bytes themselves living in the CAS. On a hit
the outputs are materialised into the workspace from the store, no
rule runs, and the ledger records the time not spent, because a
cache that cannot say what it saved cannot defend its own existence
at the next infrastructure review. Entries are only written after a
run whose observation was clean: caching the output of an action
that read undeclared files would serve tomorrow's build yesterday's
accident, so the dirty run executes but its result is deliberately
not remembered, and the refusal is counted where the review can see
it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, Observation, execute
from forge.content import ContentStore
from forge.workspace import Workspace


@dataclass
class CacheEntry:
    outputs: dict[str, str]
    cost: int


@dataclass
class ActionCache:
    store: ContentStore = field(default_factory=ContentStore)
    entries: dict[str, CacheEntry] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0
    ticks_saved: int = 0
    dirty_refusals: int = 0

    def run(
        self, action: Action, tree: Workspace, cost: int = 1
    ) -> tuple[str, Observation | None]:
        """Returns ('hit'|'miss'|'miss-dirty', observation or None)."""
        key = action.key(tree)
        held = self.entries.get(key)
        if held is not None:
            for path, output_digest in held.outputs.items():
                tree.write(path, self.store.get(output_digest))
            self.hits += 1
            self.ticks_saved += held.cost
            return "hit", None
        observation = execute(action, tree)
        self.misses += 1
        dirty = (
            observation.undeclared_reads(action)
            or observation.undeclared_writes(action)
            or observation.promised_but_silent(action)
        )
        if dirty:
            self.dirty_refusals += 1
            return "miss-dirty", observation
        outputs = {}
        for path in action.writes:
            payload = tree.read(path)
            outputs[path] = self.store.put(payload)
        self.entries[key] = CacheEntry(outputs=outputs, cost=cost)
        return "miss", observation

    def ledger(self) -> str:
        total = self.hits + self.misses
        rate = self.hits / total if total else 0.0
        return (
            f"{self.hits} hits, {self.misses} misses ({rate:.0%}), "
            f"{self.ticks_saved} ticks saved, "
            f"{self.dirty_refusals} dirty results refused"
        )
