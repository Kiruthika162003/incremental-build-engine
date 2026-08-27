"""Dual reads: the new store earns trust one compared answer at a time.

Migrating the artifact store is not done when the data is
copied; it is done when the new store has answered like the
old one for long enough to be believed. The dual-read era
serves every request from the old store, asks the new store
the same question in the shadow, and compares: agreements
accumulate toward the cutover quorum, and every disagreement
is logged with the key and both answers while the user is
served the old truth unharmed, which is the era's whole
appeal, verification at zero user risk. The cutover gate is
quantitative and slightly paranoid: enough comparisons, a
clean recent streak, and zero unexplained disagreements,
because a disagreement explained by replication lag is
scheduling and a disagreement explained by nothing is the
exact bug the era exists to catch before it answers alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

CUTOVER_COMPARISONS = 100
CLEAN_STREAK = 25


@dataclass
class DualReader:
    old_store: dict[str, str]
    new_store: dict[str, str]
    comparisons: int = 0
    streak: int = 0
    unexplained: list[str] = field(default_factory=list)
    explained: list[str] = field(default_factory=list)

    def read(
        self, key: str, lag_excused: bool = False
    ) -> str:
        truth = self.old_store.get(key)
        if truth is None:
            raise Invalid(f"{key} is not in the old store")
        shadow = self.new_store.get(key)
        self.comparisons += 1
        if shadow == truth:
            self.streak += 1
        elif lag_excused:
            self.explained.append(
                f"{key}: lag-excused, scheduling not a bug"
            )
            self.streak = 0
        else:
            self.unexplained.append(
                f"{key}: old {truth!r}, new {shadow!r}"
            )
            self.streak = 0
        return truth

    def cutover_gate(self) -> str:
        if self.unexplained:
            return (
                f"HOLD: {len(self.unexplained)} unexplained "
                "disagreement(s); a disagreement explained by "
                "nothing is the exact bug this era exists to "
                "catch before it answers alone"
            )
        if self.comparisons < CUTOVER_COMPARISONS:
            return (
                f"HOLD: {self.comparisons} of "
                f"{CUTOVER_COMPARISONS} comparisons banked"
            )
        if self.streak < CLEAN_STREAK:
            return (
                f"HOLD: the clean streak is {self.streak} of "
                f"{CLEAN_STREAK}; lag excuses pause the clock "
                "without stopping the era"
            )
        return (
            f"CUT OVER: {self.comparisons} comparisons, "
            f"streak {self.streak}, "
            f"{len(self.explained)} lag excuse(s) on record, "
            "zero unexplained"
        )
