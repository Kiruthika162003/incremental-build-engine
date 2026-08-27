"""One month of container builds, and the ratio that hides in counts.

Thirty days: sources change daily, dependencies four times, the
base never after day one. The model prices the stacks at 680
against 2440 ticks per period, a 3.6x bill for putting sources
under dependencies. The simulated month then exposed the guess
hiding in the claim: the layer meter reads 35 rebuilds against
61, only 1.7x, and both numbers are correct, because the meter
counts layers while the cascade drags specifically the expensive
one. A dashboard that counts layer rebuilds would report the
backwards stack as twice as bad; the tick bill says three and a
half times, and the difference is the 60-tick dependency layer
riding along on every daily source change.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.containerimages import ImageBuilder, Layer, expected_bill

FREQUENCY = {"base": 1, "deps": 4, "src": 30}


def _layers(source_rev: int, deps_rev: int, base_rev: int) -> dict:
    return {
        "base": Layer(
            name="base", content=f"debian:{base_rev}", build_cost=30
        ),
        "deps": Layer(
            name="deps",
            content=f"apt install gcc r{deps_rev}",
            build_cost=60,
        ),
        "src": Layer(
            name="src", content=f"COPY . /app rev{source_rev}", build_cost=10
        ),
    }


def _month(order: tuple[str, str, str]) -> int:
    builder = ImageBuilder()
    for day in range(1, 31):
        deps_rev = (day - 1) // 8
        parts = _layers(source_rev=day, deps_rev=deps_rev, base_rev=12)
        builder.build([parts[name] for name in order])
    return builder.rebuilds


def run() -> Finding:
    good_stack = [
        Layer(name="base", content="debian:12", build_cost=30),
        Layer(name="deps", content="apt install gcc", build_cost=60),
        Layer(name="src", content="COPY . /app", build_cost=10),
    ]
    bad_stack = [good_stack[0], good_stack[2], good_stack[1]]
    numbers = {
        "good_ticks_per_period": expected_bill(good_stack, FREQUENCY),
        "bad_ticks_per_period": expected_bill(bad_stack, FREQUENCY),
        "good_month_layer_rebuilds": _month(("base", "deps", "src")),
        "bad_month_layer_rebuilds": _month(("base", "src", "deps")),
    }
    ratio_model = (
        numbers["bad_ticks_per_period"]
        / numbers["good_ticks_per_period"]
    )
    holds = (
        numbers["good_ticks_per_period"] == 680
        and numbers["bad_ticks_per_period"] == 2440
        and round(ratio_model, 1) == 3.6
        and numbers["good_month_layer_rebuilds"] == 35
        and numbers["bad_month_layer_rebuilds"] == 61
    )
    return Finding(
        audit="layerbill",
        claim=(
            "layer counts read 1.7x while the tick bill reads 3.6x: "
            "counting rebuilds understates the damage because the "
            "cascade drags the expensive layer"
        ),
        numbers=numbers,
        holds=holds,
    )
