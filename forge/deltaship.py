"""Shipping deltas: the artifact moved three bytes, so send three bytes.

A nightly binary differs from yesterday's by a fraction of a
percent, and shipping the whole artifact to every machine every
night pays full freight for bytes the fleet already holds. The
delta shipper sends a patch against a base the receiver names,
and the economics are a simple inequality, patch size against
full size, with one structural risk that undoes teams: chains.
A receiver three patches behind must apply all three in order,
each against the exact intermediate digest, and one corrupted
link strands every machine behind it, so the shipper enforces a
chain budget: past the budget the receiver gets the full
artifact and a fresh base, because the freight saved by a long
chain is borrowed against the morning the chain breaks. Every
patch names its base and target digests and application refuses
a wrong base outright, since a patch applied to the wrong base
produces a plausible corrupt binary, which is worse than no
binary at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

CHAIN_BUDGET = 3


@dataclass(frozen=True)
class Patch:
    base_digest: str
    target_digest: str
    patch_bytes: int
    full_bytes: int

    def worth_it(self) -> bool:
        return self.patch_bytes < self.full_bytes


@dataclass
class DeltaShipper:
    latest_digest: str
    full_bytes: int
    history: list[Patch] = field(default_factory=list)
    freight_saved: int = 0
    full_ships: int = 0

    def publish(
        self, new_digest: str, patch_bytes: int
    ) -> None:
        if new_digest == self.latest_digest:
            raise Invalid("publishing the same digest ships nothing")
        self.history.append(
            Patch(
                base_digest=self.latest_digest,
                target_digest=new_digest,
                patch_bytes=patch_bytes,
                full_bytes=self.full_bytes,
            )
        )
        self.latest_digest = new_digest

    def plan_for(self, receiver_digest: str) -> str:
        if receiver_digest == self.latest_digest:
            return "up to date; ship nothing"
        chain: list[Patch] = []
        cursor = receiver_digest
        for patch in self.history:
            if patch.base_digest == cursor:
                chain.append(patch)
                cursor = patch.target_digest
        if cursor != self.latest_digest or not chain:
            self.full_ships += 1
            return (
                f"full artifact ({self.full_bytes} bytes): the "
                "receiver's base is unknown to the chain"
            )
        if len(chain) > CHAIN_BUDGET:
            self.full_ships += 1
            return (
                f"full artifact ({self.full_bytes} bytes): "
                f"{len(chain)} patches exceed the chain budget "
                f"of {CHAIN_BUDGET}; long chains borrow freight "
                "against the morning they break"
            )
        patch_total = sum(patch.patch_bytes for patch in chain)
        if patch_total >= self.full_bytes:
            self.full_ships += 1
            return (
                f"full artifact ({self.full_bytes} bytes): the "
                f"chain weighs {patch_total} and saves nothing"
            )
        self.freight_saved += self.full_bytes - patch_total
        steps = " -> ".join(
            patch.target_digest[:6] for patch in chain
        )
        return (
            f"{len(chain)} patch(es), {patch_total} bytes "
            f"({steps}); each applies against its exact base"
        )

    def apply(
        self, receiver_digest: str, patch: Patch
    ) -> str:
        if patch.base_digest != receiver_digest:
            raise Invalid(
                f"patch expects base {patch.base_digest[:6]}, "
                f"receiver holds {receiver_digest[:6]}; a patch "
                "on the wrong base makes a plausible corrupt "
                "binary, worse than none"
            )
        return patch.target_digest

    def ledger(self) -> str:
        return (
            f"{self.freight_saved} byte(s) of freight saved, "
            f"{self.full_ships} full ship(s)"
        )
