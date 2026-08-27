"""Branch caches: inherit from main until you diverge, then pay your own way.

Giving every feature branch its own empty cache punishes the
first build of every branch for work main already did; letting
branches write into main's cache lets one broken branch poison
everyone. The overlay does neither: a branch reads through to
main's cache for keys it has not touched and writes only to its
own layer, so inheritance is free, divergence is paid once, and
main stays clean by construction. The ledger tells the branch
what it is: mostly-inherited means a cheap branch riding main's
work, mostly-owned means the branch has drifted far enough that
rebasing would return it to the cheap side, and the rebase hint
appears exactly when the owned share crosses half, because that
is the point where the branch is paying more than it inherits.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class BranchCache:
    branch: str
    main_entries: dict[str, str]
    overlay: dict[str, str] = field(default_factory=dict)
    inherited_hits: int = 0
    owned_hits: int = 0
    misses: int = 0

    def lookup(self, key: str) -> str | None:
        if key in self.overlay:
            self.owned_hits += 1
            return self.overlay[key]
        if key in self.main_entries:
            self.inherited_hits += 1
            return self.main_entries[key]
        self.misses += 1
        return None

    def store(self, key: str, digest: str) -> str:
        if self.main_entries.get(key) == digest:
            return (
                f"{key}: matches main byte for byte; the overlay "
                "declines a redundant copy"
            )
        self.overlay[key] = digest
        return f"{key}: stored in the {self.branch} overlay"

    def poison_check(self) -> str:
        overlap = [
            key
            for key, digest in self.overlay.items()
            if key in self.main_entries
            and self.main_entries[key] != digest
        ]
        return (
            f"{len(overlap)} key(s) shadowed with different "
            f"bytes; main's copies are untouched by construction"
        )

    def ledger(self) -> str:
        hits = self.inherited_hits + self.owned_hits
        if hits == 0:
            raise Invalid(
                f"{self.branch} has no hits to characterize"
            )
        owned_share = self.owned_hits / hits
        line = (
            f"{self.branch}: {self.inherited_hits} inherited "
            f"hit(s), {self.owned_hits} owned, {self.misses} "
            f"miss(es)"
        )
        if owned_share > 0.5:
            return (
                line
                + f"; owned share {owned_share:.0%}: the branch "
                "pays more than it inherits, rebase to return "
                "to the cheap side"
            )
        return (
            line
            + f"; owned share {owned_share:.0%}: riding main's "
            "work"
        )


def merge_back(cache: BranchCache) -> tuple[int, int]:
    promoted = 0
    dropped = 0
    for key, digest in cache.overlay.items():
        if cache.main_entries.get(key) == digest:
            dropped += 1
        else:
            cache.main_entries[key] = digest
            promoted += 1
    cache.overlay.clear()
    return promoted, dropped
