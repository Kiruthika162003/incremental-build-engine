"""A day in the cache's life: tiers, storms, proofs, and honest failures.

Run with: python -m examples.cacheday
"""

from __future__ import annotations

from forge.branchcache import BranchCache
from forge.cacheproof import CacheProver
from forge.failcache import FailureCache
from forge.singleflight import SingleFlight
from forge.tieredcache import TieredCache


def dawn_the_tiers():
    cache = TieredCache(local_capacity=2)
    cache.remote.update({"k1": "d1", "k2": "d2"})
    cache.lookup("k1")
    cache.lookup("k1")
    cache.lookup("k2")
    cache.lookup("k2")
    print(f"dawn:    {cache.ledger()}")


def morning_the_storm():
    flight = SingleFlight()
    for number in range(200):
        flight.request(
            "compile:core-cone", f"shard-{number}", run_ticks=90
        )
    flight.complete("compile:core-cone", "digest-77")
    print(f"morning: {flight.receipt()}")


def noon_the_branch():
    cache = BranchCache(
        branch="feature-x",
        main_entries={"compile:core": "d1", "link:app": "d2"},
    )
    cache.lookup("compile:core")
    cache.lookup("link:app")
    cache.store("compile:core", "branch-d1")
    cache.lookup("compile:core")
    print(f"noon:    {cache.ledger()}")


def afternoon_the_proof():
    prover = CacheProver(
        sample_percent=100,
        rebuild=lambda _key: "honest-bytes",
    )
    prover.audit_hit("compile:a", "honest-bytes", rebuild_ticks=4)
    verdict = prover.audit_hit(
        "compile:b", "stale-bytes", rebuild_ticks=4
    )
    print(f"afternoon: {verdict.splitlines()[0]}")
    print(f"           {prover.ledger()}")


def dusk_the_red_build():
    failures = FailureCache()
    failures.report_failure(
        "compile:parser|abc", "unknown type tokn_t", 90
    )
    failures.report_failure(
        "compile:parser|abc", "unknown type tokn_t", 90
    )
    for _ in range(6):
        failures.lookup("compile:parser|abc", run_ticks=90)
    print(f"dusk:    {failures.ledger()}")


def main() -> int:
    dawn_the_tiers()
    morning_the_storm()
    noon_the_branch()
    afternoon_the_proof()
    dusk_the_red_build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
