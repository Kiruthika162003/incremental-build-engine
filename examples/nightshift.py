"""The night shift: pinned worlds, patient janitors, and the clean room.

Run with: python -m examples.nightshift
"""

from __future__ import annotations

from forge.cleanroom import CleanRoom
from forge.errors import Stale
from forge.idlejanitor import IdleJanitor
from forge.prescale import Prescaler
from forge.wal import Journal
from forge.worldpin import PinnedWorld


def ten_pm_the_pin():
    world = PinnedWorld(
        revision=4400, files={"core.c": "int core;"}
    )
    world.commit_arrives(4401, "core.c", "int core_v2;")
    try:
        world.audit_consumed({"core.c": "int core_v2;"})
    except Stale as torn:
        print(f"22:00  {str(torn).split(';')[0]}")
    print(f"       {world.finish()}")


def midnight_the_cleanroom():
    room = CleanRoom()
    incremental = {"parser.o": "STALE", "app": "c3"}
    clean = {"parser.o": "c1", "app": "c3"}
    print(f"00:00  {room.compare(incremental, clean).splitlines()[0]}")
    print(f"       {room.trust_verdict()}")


def two_am_the_janitor():
    janitor = IdleJanitor()
    janitor.add_chore("warm-core-cone", 30)
    janitor.add_chore("cleanroom-slice", 20, insurance=True)
    janitor.idle_gap(25)
    print(f"02:00  {janitor.real_work_arrives()}")
    print(f"       {janitor.week_ledger().split('; real')[0]}")


def four_am_the_journal():
    journal = Journal()
    journal.append("parser.o", "digest-1")
    journal.append("app", "digest-2")
    journal.simulate_torn_tail()
    _, verdict = journal.recover()
    print(f"04:00  {verdict.split(';')[0]}")


def six_am_the_calendar():
    scaler = Prescaler(depth_per_worker=3)
    for week in range(4):
        scaler.observe_week({10: 24 + 3 * week})
    print(f"06:00  {scaler.serve_slot(10, actual_depth=40)}")


def main() -> int:
    ten_pm_the_pin()
    midnight_the_cleanroom()
    two_am_the_janitor()
    four_am_the_journal()
    six_am_the_calendar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
