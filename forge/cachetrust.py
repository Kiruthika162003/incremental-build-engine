"""Cache trust: an entry is believed because of who wrote it, then verified.

A shared cache serving many machines is a supply chain: a
compromised laptop uploading one poisoned object serves it to
every colleague by tomorrow. Trust is tiered by writer: entries
from the hermetic CI fleet are believed outright, entries from
developer machines land in quarantine, visible but not served,
until a second, independent writer produces the same digest for
the same key, at which point the corroborated entry is promoted,
since two unrelated machines computing identical bytes is the
cheapest integrity proof there is. A mismatch between writers is
the alarm, not a coin flip: both entries are frozen, the key is
flagged for investigation with both writers named, and the ledger
counts promotions, quarantine serves refused, and collisions,
because a trust scheme that cannot show its refusals is a trust
scheme nobody should trust.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class TrustedEntry:
    key: str
    digest: str
    writer: str
    tier: str
    state: str


@dataclass
class TrustCache:
    trusted_writers: set[str] = field(default_factory=set)
    entries: dict[str, TrustedEntry] = field(default_factory=dict)
    frozen: dict[str, tuple[str, str]] = field(default_factory=dict)
    promotions: int = 0
    quarantine_refusals: int = 0
    collisions: list[str] = field(default_factory=list)

    def upload(self, key: str, digest: str, writer: str) -> str:
        if key in self.frozen:
            return f"{key} is frozen pending investigation"
        tier = (
            "trusted" if writer in self.trusted_writers else "developer"
        )
        held = self.entries.get(key)
        if held is None:
            state = "served" if tier == "trusted" else "quarantined"
            self.entries[key] = TrustedEntry(
                key=key,
                digest=digest,
                writer=writer,
                tier=tier,
                state=state,
            )
            return state
        if held.digest == digest:
            if held.state == "quarantined" and writer != held.writer:
                held.state = "served"
                self.promotions += 1
                return "corroborated and promoted"
            return "already known"
        self.frozen[key] = (held.writer, writer)
        del self.entries[key]
        self.collisions.append(
            f"{key}: {held.writer} and {writer} disagree; both frozen"
        )
        return "COLLISION: both entries frozen, investigate"

    def lookup(self, key: str) -> str | None:
        held = self.entries.get(key)
        if held is None:
            return None
        if held.state == "quarantined":
            self.quarantine_refusals += 1
            return None
        return held.digest

    def ledger(self) -> str:
        served = sum(
            1
            for entry in self.entries.values()
            if entry.state == "served"
        )
        quarantined = sum(
            1
            for entry in self.entries.values()
            if entry.state == "quarantined"
        )
        return (
            f"{served} served, {quarantined} in quarantine, "
            f"{self.promotions} promoted by corroboration, "
            f"{self.quarantine_refusals} quarantine serves refused, "
            f"{len(self.collisions)} collisions frozen"
        )


def register_trusted(cache: TrustCache, writer: str) -> None:
    if writer in cache.trusted_writers:
        raise Invalid(f"{writer} is already trusted")
    cache.trusted_writers.add(writer)
