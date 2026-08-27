"""Matching actions to worker pools: no match must explain itself.

A remote farm is pools with properties, linux-x64 with 32 GB,
mac-arm with a code-signing identity, and every action demands
the properties it cannot run without. Matching is subset logic
and the happy path is boring; the product is the unhappy path,
because "no worker available" is the least actionable sentence in
CI. When nothing matches, the explainer scores every pool by how
close it came and names the missing properties of the nearest
one, turning a queue stuck at forty minutes into "the mac pool
lacks xcode=15; it has xcode=14". Demand keys that no pool
anywhere offers are called out separately as typos or fantasies,
since a demand nobody can meet is usually a demand nobody meant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass(frozen=True)
class Pool:
    name: str
    offers: tuple[tuple[str, str], ...]
    slots: int

    def offer_map(self) -> dict[str, str]:
        return dict(self.offers)


@dataclass
class Matcher:
    pools: list[Pool] = field(default_factory=list)

    def add_pool(self, pool: Pool) -> None:
        if pool.slots < 1:
            raise Invalid(
                f"pool {pool.name} has no slots and is a memorial, "
                "not a pool"
            )
        if any(held.name == pool.name for held in self.pools):
            raise Invalid(f"pool {pool.name} already registered")
        self.pools.append(pool)

    def match(self, demands: dict[str, str]) -> str:
        if not self.pools:
            raise Invalid("no pools registered")
        fitting = [
            pool
            for pool in self.pools
            if all(
                pool.offer_map().get(key) == value
                for key, value in demands.items()
            )
        ]
        if fitting:
            chosen = max(fitting, key=lambda pool: pool.slots)
            return f"{chosen.name} ({chosen.slots} slots)"
        raise Invalid(self._explain(demands))

    def _explain(self, demands: dict[str, str]) -> str:
        offered_keys = {
            key
            for pool in self.pools
            for key, _ in pool.offers
        }
        fantasies = sorted(
            key for key in demands if key not in offered_keys
        )
        lines = ["no pool matches; the near misses:"]
        scored = []
        for pool in self.pools:
            offer = pool.offer_map()
            missing = sorted(
                f"{key}={value} (pool has "
                f"{offer.get(key, 'nothing')})"
                for key, value in demands.items()
                if offer.get(key) != value
            )
            scored.append((len(missing), pool.name, missing))
        scored.sort()
        for _, name, missing in scored[:2]:
            lines.append(
                f"  {name} lacks {'; '.join(missing)}"
            )
        if fantasies:
            lines.append(
                f"  demanded keys no pool offers anywhere: "
                f"{', '.join(fantasies)}; a demand nobody can "
                "meet is usually a demand nobody meant"
            )
        return "\n".join(lines)
