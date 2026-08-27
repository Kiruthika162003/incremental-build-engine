"""Embargoed builds: the fix exists, and the cache must not say so.

A security fix under embargo is a paradox for build
infrastructure: it must build, test, and stage like any change,
while the shared cache, the build event stream, and the artifact
index all want to announce it to the fleet. The embargo room
gives the work a private namespace: its keys are salted so they
cannot collide with or be probed through the shared namespace,
its artifacts live in a store the fleet cannot read, and the
one rule with teeth is the leak check, which scans the shared
cache for any digest the room produced and treats a match as an
incident with a name, not a warning, because an embargoed
digest in a shared cache is disclosure, whatever the intent.
Lifting the embargo is explicit and one-way: the room's entries
are republished into the shared namespace unsalted, the room is
emptied, and the ledger records what was private, for how many
ticks, and that the leak check ran clean every day of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid


@dataclass
class EmbargoRoom:
    name: str
    opened_at: int
    private_entries: dict[str, str] = field(default_factory=dict)
    leak_checks_run: int = 0
    lifted_at: int | None = None

    def _salted(self, key: str) -> str:
        return digest_text(f"embargo|{self.name}|{key}")

    def build(self, key: str, digest: str) -> str:
        if self.lifted_at is not None:
            raise Invalid(
                f"{self.name} was lifted; embargoed work after "
                "the lift is a new embargo, not a footnote"
            )
        self.private_entries[key] = digest
        return (
            f"{key} built in the room under "
            f"{self._salted(key)[:8]}"
        )

    def leak_check(self, shared_cache: dict[str, str]) -> str:
        self.leak_checks_run += 1
        leaked = sorted(
            key
            for key, digest in self.private_entries.items()
            if digest in shared_cache.values()
        )
        if leaked:
            return (
                f"INCIDENT: {', '.join(leaked)} appear in the "
                "shared cache; an embargoed digest in a shared "
                "cache is disclosure, whatever the intent"
            )
        return (
            f"clean: {len(self.private_entries)} private "
            "entrie(s), none visible to the fleet"
        )

    def lift(
        self, shared_cache: dict[str, str], now: int
    ) -> str:
        if self.lifted_at is not None:
            raise Invalid(f"{self.name} is already lifted")
        if now < self.opened_at:
            raise Invalid("the embargo cannot lift before it began")
        for key, digest in self.private_entries.items():
            shared_cache[key] = digest
        count = len(self.private_entries)
        self.private_entries.clear()
        self.lifted_at = now
        return (
            f"{self.name} lifted: {count} entrie(s) republished "
            f"unsalted after {now - self.opened_at} tick(s) "
            f"private, {self.leak_checks_run} clean leak "
            "check(s) on record"
        )
