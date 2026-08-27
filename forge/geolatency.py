"""Office latency: the Sydney developer pays a tax the dashboard averages away.

The farm lives in one region and the developers do not, and
every cache miss costs a round trip whose price depends
entirely on where the developer sits: two milliseconds from
the office upstairs, three hundred from across the ocean. The
tax report multiplies each office's round-trip time by its
daily misses, which converts a networking fact into a
personnel fact, hours of humans waiting, ranked by office,
and the prescription threshold is explicit: an office whose
daily tax crosses the line earns an edge cache, priced
against the tax it retires, and the payback period prints in
days because that is the unit approvals think in. The
refusal to average is the module's spine: a fleet-wide mean
latency erases exactly the person the report exists to
defend.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

EDGE_CACHE_COST_MS_EQUIVALENT = 50_000_000
TAX_THRESHOLD_MS_PER_DAY = 1_000_000


@dataclass(frozen=True)
class Office:
    name: str
    round_trip_ms: int
    daily_misses: int

    def __post_init__(self) -> None:
        if self.round_trip_ms <= 0:
            raise Invalid(
                f"{self.name}: a nonpositive round trip means "
                "the office is inside the farm"
            )

    def daily_tax_ms(self) -> int:
        return self.round_trip_ms * self.daily_misses


def tax_report(offices: list[Office]) -> str:
    if not offices:
        raise Invalid("no offices, no tax")
    ranked = sorted(
        offices,
        key=lambda office: -office.daily_tax_ms(),
    )
    lines = ["the miss tax by office, never averaged:"]
    for office in ranked:
        tax = office.daily_tax_ms()
        lines.append(
            f"  {office.name}: {office.round_trip_ms}ms x "
            f"{office.daily_misses} miss(es) = {tax}ms/day"
        )
        if tax >= TAX_THRESHOLD_MS_PER_DAY:
            payback = EDGE_CACHE_COST_MS_EQUIVALENT // tax
            lines.append(
                f"    earns an edge cache: payback in "
                f"{payback} day(s), the unit approvals think in"
            )
    lines.append(
        "a fleet-wide mean erases exactly the person this "
        "report exists to defend"
    )
    return "\n".join(lines)
