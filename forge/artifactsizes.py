"""Size budgets: the binary grows one reasonable commit at a time.

Nobody ships a bloated binary on purpose; they ship four hundred
commits that each added a little. The size ledger records every
artifact's bytes per build, budgets are declared per artifact
with a hard ceiling and a soft slope, and the two catch different
sins: the ceiling refuses the build that crosses it outright,
while the slope watches the trend, flagging an artifact that grew
more than its allowance over the trailing window even though
every individual commit looked innocent. The attribution line is
what makes the flag actionable: the growth is split across the
builds in the window by their measured deltas, so the report says
which build brought the bytes, and four hundred reasonable
commits stop being a defence the day the ledger can name the six
that mattered.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

WINDOW = 5


@dataclass
class SizeBudget:
    ceiling: int
    slope_per_window: int


@dataclass
class SizeLedger:
    budgets: dict[str, SizeBudget] = field(default_factory=dict)
    history: dict[str, list[tuple[str, int]]] = field(
        default_factory=dict
    )

    def budget(
        self, artifact: str, ceiling: int, slope_per_window: int
    ) -> None:
        if ceiling <= 0 or slope_per_window < 0:
            raise Invalid("a budget needs a positive ceiling")
        self.budgets[artifact] = SizeBudget(
            ceiling=ceiling, slope_per_window=slope_per_window
        )

    def record(self, artifact: str, build: str, size: int) -> str:
        held = self.budgets.get(artifact)
        if held is None:
            raise Invalid(
                f"{artifact} has no budget; unmeasured growth is "
                f"how binaries bloat"
            )
        if size > held.ceiling:
            return (
                f"REFUSED: {artifact} at {size} crosses its ceiling "
                f"of {held.ceiling}"
            )
        rows = self.history.setdefault(artifact, [])
        rows.append((build, size))
        del rows[: -WINDOW - 1]
        if len(rows) >= 2:
            growth = rows[-1][1] - rows[0][1]
            if growth > held.slope_per_window:
                return (
                    f"SLOPE: {artifact} grew {growth} over the "
                    f"window against an allowance of "
                    f"{held.slope_per_window}"
                )
        return "within budget"

    def attribution(self, artifact: str) -> list[str]:
        rows = self.history.get(artifact, [])
        if len(rows) < 2:
            raise Invalid(
                f"{artifact} has too little history to attribute"
            )
        deltas = []
        for (_, before), (build, after) in zip(
            rows, rows[1:], strict=False
        ):
            delta = after - before
            if delta > 0:
                deltas.append((delta, build))
        deltas.sort(reverse=True)
        return [
            f"{build} brought {delta} bytes"
            for delta, build in deltas
        ]
