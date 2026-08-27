"""Precompiled header economics: the fastest include is also the widest bomb.

Precompiling a header saves its parse cost at every inclusion,
which is why teams precompile the biggest header they can find,
and why their incremental builds then crater: everything that
includes the PCH rebuilds when any header inside it moves, so the
same wideness that multiplies the saving multiplies the blast.
The planner prices both sides: daily parse savings from inclusion
count times parse cost, against expected invalidation cost from
the header's own churn rate times the cone it flattens. A header
earns precompilation only when the ledger is positive, and the
report shows the losing headers with both numbers, because the
argument "it is included 400 times" is only half an argument
until the churn column is on the table next to it.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Header:
    name: str
    parse_ticks: int
    inclusions: int
    edits_per_week: int
    rebuild_ticks_per_includer: int

    def __post_init__(self) -> None:
        if self.parse_ticks <= 0 or self.inclusions < 0:
            raise Invalid(
                f"{self.name} needs positive parse ticks and a "
                "nonnegative inclusion count"
            )


@dataclass(frozen=True)
class Verdict:
    header: str
    weekly_saving: int
    weekly_blast: int

    def worth_it(self) -> bool:
        return self.weekly_saving > self.weekly_blast

    def line(self) -> str:
        judgement = (
            "precompile" if self.worth_it() else "leave it plain"
        )
        return (
            f"{self.header}: saves {self.weekly_saving}/week, "
            f"blast {self.weekly_blast}/week, {judgement}"
        )


BUILDS_PER_WEEK = 50


def appraise(header: Header) -> Verdict:
    weekly_saving = (
        header.parse_ticks * header.inclusions * BUILDS_PER_WEEK
    )
    weekly_blast = (
        header.edits_per_week
        * header.inclusions
        * header.rebuild_ticks_per_includer
    )
    return Verdict(
        header=header.name,
        weekly_saving=weekly_saving,
        weekly_blast=weekly_blast,
    )


def plan(headers: list[Header]) -> str:
    if not headers:
        raise Invalid("no headers to appraise")
    verdicts = sorted(
        (appraise(header) for header in headers),
        key=lambda v: v.weekly_blast - v.weekly_saving,
    )
    chosen = [v for v in verdicts if v.worth_it()]
    lines = [
        f"{len(chosen)} of {len(headers)} header(s) earn "
        "precompilation"
    ]
    lines.extend(f"  {verdict.line()}" for verdict in verdicts)
    return "\n".join(lines)


def stability_price(header: Header) -> str:
    verdict = appraise(header)
    if verdict.worth_it():
        return (
            f"{header.name} already earns its keep at "
            f"{header.edits_per_week} edit(s) a week"
        )
    if header.inclusions == 0 or header.rebuild_ticks_per_includer == 0:
        raise Invalid(
            f"{header.name} has no blast to reduce; the ledger "
            "is not about stability"
        )
    breakeven = (
        header.parse_ticks * BUILDS_PER_WEEK
    ) // header.rebuild_ticks_per_includer
    return (
        f"{header.name} would earn precompilation at "
        f"{breakeven} edit(s) a week or fewer; it sees "
        f"{header.edits_per_week}, so the fix is stability, "
        "not tooling"
    )
