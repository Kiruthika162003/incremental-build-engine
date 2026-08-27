"""Two days of equal demand price the shape of arrival.

A calm day asks for 12 builds every tick; a flapping day asks for
24 and then nothing, alternating, and both days total 120 builds.
The guess was that flapping would also hurt the queue; the
measurement says otherwise, and the audit keeps the sharper
truth: both days pay exactly 80 queued ticks, because the burst
queues what the lull then drains, and the flap's entire surcharge
lands in the other currency, 40 idle worker ticks against zero,
plus a fleet held at 8 where the calm day holds 4. The cool-down
does its job in the background: the one-tick lulls never fill the
three-tick cool period, so the fleet never thrashes down and back
up, which is the asymmetry working as designed and the reason
the surcharge is idleness rather than boot storms.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.autoscale import AutoScaler


def _farm() -> AutoScaler:
    return AutoScaler(
        min_workers=2,
        max_workers=10,
        depth_per_worker=3,
        cool_ticks=3,
    )


def run() -> Finding:
    calm = _farm()
    for _ in range(10):
        calm.tick(queue_depth=12)
    flap = _farm()
    for _ in range(5):
        flap.tick(queue_depth=24)
        flap.tick(queue_depth=0)
    numbers = {
        "calm_queued": calm.queued_ticks,
        "flap_queued": flap.queued_ticks,
        "calm_idle": calm.idle_ticks,
        "flap_idle": flap.idle_ticks,
        "calm_fleet": calm.workers,
        "flap_fleet": flap.workers,
        "flap_scale_downs": flap.scale_downs,
        "demand_each": 120,
    }
    holds = (
        numbers["calm_queued"] == 80
        and numbers["flap_queued"] == 80
        and numbers["calm_idle"] == 0
        and numbers["flap_idle"] == 40
        and numbers["calm_fleet"] == 4
        and numbers["flap_fleet"] == 8
        and numbers["flap_scale_downs"] == 0
    )
    return Finding(
        audit="flapbill",
        claim=(
            "equal demand, equal wait: both days queue 80 ticks, "
            "and the flap's whole surcharge is 40 idle ticks and "
            "a doubled fleet that never cools down"
        ),
        numbers=numbers,
        holds=holds,
    )
