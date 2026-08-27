"""The canary dial is not the delivery, and small fleets prove it.

The slice is a hash bucket, so the percentage on the dial is a
probability, not a promise. On a 40-target fleet the drill asks
for 20 percent and receives 10: four targets, half the dial,
pure bucket luck, and a team reading "20 percent canaried" off
the dial would be reporting double their actual coverage. The
same dial on a 1000-target fleet delivers 19.2 percent, which is
the law of large numbers showing up for work. Both numbers stay
recorded because the lesson is operational: canary coverage must
be reported from the built count, never from the dial, and small
fleets should widen the dial until the built count, not the
setting, reaches the coverage the promotion gate demands.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.toolcanary import CanaryRun, in_slice

SMALL_FLEET = tuple(f"pkg{number}/lib" for number in range(40))
BIG_FLEET = tuple(
    f"srv{number}/module" for number in range(1000)
)


def run() -> Finding:
    small_hit = sum(
        1 for target in SMALL_FLEET if in_slice(target, 20)
    )
    big_hit = sum(
        1 for target in BIG_FLEET if in_slice(target, 20)
    )
    canary = CanaryRun(percent=20)
    for target in SMALL_FLEET:
        canary.observe(target, "old", "old")
    numbers = {
        "dial_percent": 20,
        "small_fleet_delivered": small_hit,
        "small_fleet_percent": 100 * small_hit / len(SMALL_FLEET),
        "big_fleet_delivered": big_hit,
        "big_fleet_percent": 100 * big_hit / len(BIG_FLEET),
        "tiny_slice_verdict_holds": (
            "certifies nothing" in canary.promotion_verdict()
        ),
    }
    holds = (
        numbers["small_fleet_delivered"] == 4
        and numbers["small_fleet_percent"] == 10.0
        and numbers["big_fleet_delivered"] == 192
        and numbers["big_fleet_percent"] == 19.2
        and numbers["tiny_slice_verdict_holds"]
    )
    return Finding(
        audit="sliceluck",
        claim=(
            "the 20 percent dial delivers 10 percent on 40 "
            "targets and 19.2 on a thousand: coverage must be "
            "reported from the built count, never from the dial"
        ),
        numbers=numbers,
        holds=holds,
    )
