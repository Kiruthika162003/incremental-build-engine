"""Migration day: import the Makefile, shadow the old world, promote the new.

Run with: python -m examples.migrationday
"""

from __future__ import annotations

from forge.enginepin import FarmRollCall
from forge.makeimport import import_makefile
from forge.promotion import Ladder
from forge.shadowbuild import MigrationRatchet, ShadowRun

MAKEFILE = """\
.PHONY: all
all: app

app: main.o util.o
\tld main.o util.o

main.o: main.c
\tcc main.c

util.o: util.c
\tcc util.c

%.gen: %.tmpl
\tgenerate $<
"""


def import_the_makefile():
    parsed, report = import_makefile(MAKEFILE)
    print(f"import:  {report.grade()}")
    print(
        f"         targets: {', '.join(sorted(parsed.stanzas))}"
    )


def shadow_the_old_world() -> MigrationRatchet:
    ratchet = MigrationRatchet()
    monday = ShadowRun(
        old_outputs={"app": "d1", "main.o": "d2", "util.o": "d3"},
        new_outputs={"app": "DIFF", "main.o": "d2", "util.o": "d3"},
    )
    print(f"monday:  {monday.triage().splitlines()[0]}")
    print(f"         {ratchet.advance(monday)}")
    friday = ShadowRun(
        old_outputs={"app": "d1", "main.o": "d2", "util.o": "d3"},
        new_outputs={"app": "d1", "main.o": "d2", "util.o": "d3"},
    )
    print(f"friday:  {friday.triage().splitlines()[-1].strip()}")
    print(f"         {ratchet.advance(friday)}")
    return ratchet


def check_the_farm():
    farm = FarmRollCall(pin=(2, 3, 0))
    farm.check_in("w1", "2.3.0")
    farm.check_in("w2", "2.4.1")
    farm.check_in("w-old", "2.1.7")
    print(f"farm:    {farm.roll_call().splitlines()[0]}")


def promote_the_first_build():
    ladder = Ladder()
    ladder.enter("app-9.0", "feedface0011")
    ladder.promote("app-9.0", "feedface0011")
    ladder.promote("app-9.0", "feedface0011")
    print(f"ladder:  {ladder.story('app-9.0').splitlines()[-1]}")


def main() -> int:
    import_the_makefile()
    shadow_the_old_world()
    check_the_farm()
    promote_the_first_build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
