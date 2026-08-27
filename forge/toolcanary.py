"""Canarying a new toolchain on a slice before betting the fleet on it.

Adopting a compiler fleet-wide on the vendor's word is how a
Tuesday becomes a war room; the canary buys the same upgrade with
a slice instead: a deterministic five percent of targets build
with the new tool alongside the old one, and the comparison sorts
every canaried target into agree, differ, or fail. The slice is
chosen by name hash, not by hand, because hand-picked targets are
always the easy ones and a canary of easy targets certifies
nothing. Promotion has numeric teeth: no failures, agreement at
or above the bar, and a minimum slice actually built, so "the
canary looked fine" is replaced by three numbers, and widening
the slice is the only path from five percent to the fleet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

AGREEMENT_BAR = 0.95
MINIMUM_SLICE = 5


def in_slice(target: str, percent: int) -> bool:
    if not 0 < percent <= 100:
        raise Invalid("the slice must be between 1 and 100 percent")
    bucket = int(digest_text(target)[:8], 16) % 100
    return bucket < percent


@dataclass
class CanaryRun:
    percent: int
    agree: list[str] = field(default_factory=list)
    differ: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: int = 0

    def observe(
        self,
        target: str,
        old_digest: str,
        new_digest: str | None,
    ) -> None:
        if not in_slice(target, self.percent):
            self.skipped += 1
            return
        if new_digest is None:
            self.failed.append(target)
        elif new_digest == old_digest:
            self.agree.append(target)
        else:
            self.differ.append(target)

    def built(self) -> int:
        return (
            len(self.agree) + len(self.differ) + len(self.failed)
        )

    def agreement(self) -> float:
        if self.built() == 0:
            raise Invalid(
                "the canary built nothing; widen the slice or "
                "check the hash"
            )
        return len(self.agree) / self.built()

    def promotion_verdict(self) -> str:
        built = self.built()
        if built < MINIMUM_SLICE:
            return (
                f"HOLD: only {built} target(s) canaried against "
                f"a minimum of {MINIMUM_SLICE}; a tiny slice "
                "certifies nothing"
            )
        if self.failed:
            return (
                f"HOLD: {len(self.failed)} failure(s) "
                f"({', '.join(sorted(self.failed))}); failures "
                "are not a percentage question"
            )
        share = self.agreement()
        if share < AGREEMENT_BAR:
            return (
                f"HOLD: agreement {share:.0%} under the "
                f"{AGREEMENT_BAR:.0%} bar; the differ list is "
                f"the work ({', '.join(sorted(self.differ))})"
            )
        return (
            f"PROMOTE: {built} built, agreement {share:.0%}, "
            f"0 failures; widen the slice"
        )
