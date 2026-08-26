"""Eviction regret, measured: LRU and cost-aware lose different bets.

One access trace, two policies, and the only score that matters.
The trace holds a big cheap asset, a small dear compilation, and a
stream of medium entries that overflows a 200-byte cache; the day
ends with a lookup of everything once more. LRU evicts by
coldness and pays 2 regret misses on the day; cost-aware protects
the dear entry, sacrifices the cheap fat early, and pays 2 as
well, but they are different misses: LRU regrets the dear
compilation it let go, at 50 rebuild ticks, while cost-aware
regrets the cheap fat at 2. The tick bill is the audit's point:
equal miss counts, a twenty-five-fold difference in repayment,
and any dashboard that counts misses without pricing them would
call these two policies tied.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.gcpolicy import EvictingCache


def _day(policy: str) -> tuple[int, int]:
    cache = EvictingCache(capacity_bytes=200, policy=policy)
    cache.admit("cheap-fat", size=120, cost=2, now=0)
    cache.admit("dear-lean", size=30, cost=50, now=1)
    for number in range(3):
        cache.admit(f"medium{number}", size=60, cost=10, now=2 + number)
    regret_ticks = 0
    for key, cost in (
        ("cheap-fat", 2),
        ("dear-lean", 50),
        ("medium0", 10),
        ("medium1", 10),
        ("medium2", 10),
    ):
        if not cache.lookup(key, now=10) and key in cache.forgotten:
            regret_ticks += cost
    return cache.regret_misses, regret_ticks


def run() -> Finding:
    lru_misses, lru_ticks = _day("lru")
    aware_misses, aware_ticks = _day("cost-aware")
    numbers = {
        "lru_regret_misses": lru_misses,
        "lru_regret_ticks": lru_ticks,
        "aware_regret_misses": aware_misses,
        "aware_regret_ticks": aware_ticks,
    }
    holds = (
        lru_misses == aware_misses == 2
        and lru_ticks == 52
        and aware_ticks == 12
    )
    return Finding(
        audit="regretledger",
        claim=(
            "equal regret misses, unequal bills: LRU repays 52 ticks "
            "where cost-aware repays 12, and counting misses without "
            "pricing them calls that a tie"
        ),
        numbers=numbers,
        holds=holds,
    )
