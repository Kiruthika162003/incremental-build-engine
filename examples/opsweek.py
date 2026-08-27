"""An operations week: burn-in, preflight, control groups, and the ocean.

Run with: python -m examples.opsweek
"""

from __future__ import annotations

from forge.burnin import BurnInRig
from forge.controlgroup import ControlGroup
from forge.deltaship import DeltaShipper
from forge.georeplica import GeoCache
from forge.preflight import Preflight

KNOWN = {"compile:probe1": "digest-a", "link:probe2": "digest-b"}


def monday_the_new_machines():
    def fleet(worker, probe):
        if worker == "rack9-new" and probe == "link:probe2":
            return "wrong-bytes"
        return KNOWN[probe]

    rig = BurnInRig(known_digests=dict(KNOWN), run_probe=fleet)
    print(f"monday:   {rig.evaluate('rack7-new')}")
    print(f"          {rig.evaluate('rack9-new').split(':')[0]}"
          f": one wrong known answer, machine refused")


def tuesday_the_desk():
    flight = Preflight()
    flight.add_check("parse", 2, lambda: "unexpected token in BUILD")
    flight.add_check("graph", 5, lambda: None)
    print(f"tuesday:  {flight.run().splitlines()[0]}")
    print(f"          {flight.ledger()}")


def wednesday_the_control():
    group = ControlGroup(control_percent=10)
    group.record_build("build-0", 90, "truth", "compile:app")
    group.record_build("build-3", 110, "truth", "compile:app")
    group.record_build("build-1", 8, "truth", "compile:app")
    group.record_build("build-2", 12, "truth", "compile:app")
    print(f"wednesday: {group.speedup_report()}")


def thursday_the_ocean():
    cache = GeoCache(replication_lag=30)
    cache.upload("release:app", region="eu", now=100)
    verdict = cache.lookup(
        "release:app", "us", now=110, caller="release"
    )
    print(f"thursday: {verdict}")


def friday_the_freight():
    shipper = DeltaShipper(latest_digest="night0", full_bytes=10000)
    for night in range(1, 4):
        shipper.publish(f"night{night}", patch_bytes=120)
    print(f"friday:   {shipper.plan_for('night1')}")
    print(f"          {shipper.ledger()}")


def main() -> int:
    monday_the_new_machines()
    tuesday_the_desk()
    wednesday_the_control()
    thursday_the_ocean()
    friday_the_freight()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
