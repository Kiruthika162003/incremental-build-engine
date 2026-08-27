"""One day on the build farm: bursts, walls, patience, and near misses.

Run with: python -m examples.farmday
"""

from __future__ import annotations

from forge.autoscale import AutoScaler
from forge.buildqueue import FarmQueue, QueuedBuild
from forge.errors import Invalid
from forge.ramscheduler import MemoryAction, RamScheduler
from forge.workermatch import Matcher, Pool


def the_morning_burst():
    fleet = AutoScaler(
        min_workers=2,
        max_workers=12,
        depth_per_worker=3,
        cool_ticks=3,
    )
    morning = [0, 0, 24, 30, 18, 6, 0, 0, 0, 0]
    for depth in morning:
        fleet.tick(queue_depth=depth)
    print(f"morning: {fleet.bill()}")


def the_noon_wall():
    machine = RamScheduler(workers=8, ram_ceiling=64)
    noon = [
        MemoryAction(name="link-app", ticks=40, peak_ram=48),
        MemoryAction(name="link-tests", ticks=30, peak_ram=40),
        *[
            MemoryAction(
                name=f"compile-{number}", ticks=10, peak_ram=4
            )
            for number in range(6)
        ],
    ]
    finish = machine.simulate(noon)
    print(f"noon:    done at tick {finish}; {machine.diagnosis()}")


def the_evening_patience():
    farm = FarmQueue(slots=1)
    farm.submit(QueuedBuild(name="nightly", kind="batch", arrived=0))
    for round_number in range(3):
        first = QueuedBuild(
            name=f"dev-a{round_number}",
            kind="interactive",
            arrived=10 + 2 * round_number,
        )
        second = QueuedBuild(
            name=f"dev-b{round_number}",
            kind="interactive",
            arrived=11 + 2 * round_number,
        )
        farm.submit(first)
        farm.submit(second)
        farm.finish(second.name if second.name in farm.running else first.name)
        for name in list(farm.running):
            farm.finish(name)
    print(f"evening: {farm.bill()}")


def the_stuck_queue():
    matcher = Matcher()
    matcher.add_pool(
        Pool(
            name="linux-x64",
            offers=(("os", "linux"), ("arch", "x64")),
            slots=40,
        )
    )
    matcher.add_pool(
        Pool(
            name="mac-arm",
            offers=(("os", "mac"), ("xcode", "14")),
            slots=6,
        )
    )
    try:
        matcher.match({"os": "mac", "xcode": "15"})
    except Invalid as refusal:
        first_miss = str(refusal).splitlines()[1].strip()
        print(f"stuck:   {first_miss}")


def main() -> int:
    the_morning_burst()
    the_noon_wall()
    the_evening_patience()
    the_stuck_queue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
