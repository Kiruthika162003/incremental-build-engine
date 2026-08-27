"""Profile-guided optimization: the profile is a perishable ingredient.

A fresh profile buys real speed, but the profile describes the
program that was, not the program that is, and every commit
widens that gap. The keeper tracks how many of the profiled
functions still exist under their recorded interface; coverage
decays as code moves, and the speedup model is blunt about the
cliff: gains scale with coverage down to a floor, and below the
floor the stale profile starts training the optimizer on lies,
hot paths that no longer exist and branches that now go the
other way, where the honest answer is to build without it. The
gate therefore has three verdicts, use, refresh, and refuse,
and the refuse case is the one teams skip: they treat the
profile as a cache when it is an opinion, and old opinions about
hot code are how binaries get slower with optimization on.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

REFRESH_FLOOR = 0.8
REFUSE_FLOOR = 0.5
FULL_SPEEDUP_PERCENT = 12


@dataclass(frozen=True)
class Profile:
    build_id: str
    functions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.functions:
            raise Invalid(
                "an empty profile optimizes nothing and proves "
                "the collector is broken"
            )


def coverage(profile: Profile, live_functions: set[str]) -> float:
    still_there = sum(
        1
        for function in profile.functions
        if function in live_functions
    )
    return still_there / len(profile.functions)


def expected_speedup(cover: float) -> int:
    if cover < REFUSE_FLOOR:
        return 0
    return round(FULL_SPEEDUP_PERCENT * cover)


def verdict(profile: Profile, live_functions: set[str]) -> str:
    cover = coverage(profile, live_functions)
    percent = f"{cover:.0%}"
    if cover >= REFRESH_FLOOR:
        return (
            f"use it: {percent} of profiled functions survive, "
            f"expect about {expected_speedup(cover)}% "
            f"(profile {profile.build_id})"
        )
    if cover >= REFUSE_FLOOR:
        return (
            f"refresh soon: coverage fell to {percent}, the "
            f"speedup is down to {expected_speedup(cover)}% and "
            "falling with every merge"
        )
    dead = sorted(
        function
        for function in profile.functions
        if function not in live_functions
    )
    return (
        f"refuse it: {percent} coverage means the profile is an "
        f"old opinion, not a cache; {len(dead)} profiled "
        f"function(s) no longer exist, build plain and recollect "
        f"(first missing: {dead[0]})"
    )


def refresh_ledger(
    coverages: list[float], refresh_cost_percent: int
) -> str:
    if not coverages:
        raise Invalid("no history to price")
    if any(not 0 <= cover <= 1 for cover in coverages):
        raise Invalid("coverage is a fraction between 0 and 1")
    banked = sum(
        expected_speedup(cover) for cover in coverages
    )
    always_fresh = FULL_SPEEDUP_PERCENT * len(coverages)
    lost = always_fresh - banked
    action = (
        "the refresh pays for itself"
        if lost > refresh_cost_percent
        else "riding the decay is still cheaper"
    )
    return (
        f"{len(coverages)} release(s): banked {banked}% where "
        f"always-fresh banks {always_fresh}%, {lost}% lost to "
        f"decay against a refresh cost of "
        f"{refresh_cost_percent}%: {action}"
    )
