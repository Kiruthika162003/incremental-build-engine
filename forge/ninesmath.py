"""Nines arithmetic: availability promises compose down, never up.

A 99.9 percent service is allowed about 526 minutes of down
time a year, and the number surprises every meeting it visits,
which is reason enough to compute it instead of gesturing.
The composition rule is the one that bites: two 99.9 services
in series multiply to 99.8, so a build that needs the
coordinator and the cache and the store inherits the product
of their promises, not the minimum, and a platform quoting
its best component's nines is quoting a component, not a
platform. Redundancy runs the other way, two independent
99 percent replicas in parallel fail together 0.01 percent of
the time, and the honesty clause rides along: that arithmetic
assumes independence, and replicas sharing a power feed
share a fate, whatever the multiplication says.
"""

from __future__ import annotations

import math

from forge.errors import Invalid

MINUTES_PER_YEAR = 525_960


def _check(percent: float) -> None:
    if not 0 < percent < 100:
        raise Invalid(
            "availability is strictly between 0 and 100"
        )


def downtime_minutes_per_year(percent: float) -> float:
    _check(percent)
    return MINUTES_PER_YEAR * (100 - percent) / 100


def series(percents: list[float]) -> float:
    if len(percents) < 2:
        raise Invalid("series composition needs two services")
    product = 1.0
    for percent in percents:
        _check(percent)
        product *= percent / 100
    return 100 * product


def parallel(percents: list[float]) -> str:
    if len(percents) < 2:
        raise Invalid("redundancy needs a second replica")
    failure = 1.0
    for percent in percents:
        _check(percent)
        failure *= (100 - percent) / 100
    combined = 100 * (1 - failure)
    return (
        f"{combined:.4f}% assuming independence; replicas "
        "sharing a power feed share a fate, whatever the "
        "multiplication says"
    )


def nines_label(percent: float) -> str:
    _check(percent)
    label = math.floor(
        round(-math.log10(1 - percent / 100), 9)
    )
    if label < 1:
        return f"{percent}% has no nines to brag about"
    return (
        f"{percent}% is {label} nine(s), "
        f"{downtime_minutes_per_year(percent):.0f} minute(s) "
        "a year"
    )


def platform_promise(components: list[float]) -> str:
    combined = series(components)
    minutes = downtime_minutes_per_year(combined)
    best = max(components)
    return (
        f"the platform is {combined:.2f}%, "
        f"{minutes:.0f} minute(s) a year, and quoting the "
        f"best component's {best}% is quoting a component, "
        "not a platform"
    )
