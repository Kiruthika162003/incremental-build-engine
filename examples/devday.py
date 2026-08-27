"""A developer's day: the desk, the loop, the swap, the receipt.

Run with: python -m examples.devday
"""

from __future__ import annotations

from forge.hotswap import HotSession
from forge.innerloop import InnerLoop
from forge.preflight import Preflight
from forge.receipt import BuildFacts, receipt
from forge.symbolselect import SourceUnit, Symbol

VIEW = Symbol(name="view", signature="(req) -> Response", public=True)


def nine_am_the_preflight():
    flight = Preflight()
    flight.add_check("parse", 2, lambda: None)
    flight.add_check("graph", 5, lambda: None)
    print(f"09:00  {flight.run()}")


def all_morning_the_loop():
    loop = InnerLoop()
    for _ in range(15):
        loop.record(2)
    for _ in range(5):
        loop.record(90)
    print(f"11:30  {loop.summary()}")
    print(f"       {loop.flow_verdict().split(': ')[-1]}")


def two_pm_the_swaps():
    live = HotSession()
    live.admit(
        SourceUnit(path="views.py", body="v1", symbols=(VIEW,))
    )
    for round_number in range(2, 6):
        live.save(
            SourceUnit(
                path="views.py",
                body=f"v{round_number}",
                symbols=(VIEW,),
            )
        )
    print(f"14:00  {live.rhythm_bill()}")


def six_pm_the_receipt():
    facts = BuildFacts(
        targets_ran=4,
        cache_hits=12,
        cutoff_skips=3,
        interface_skips=5,
        farm_ticks=120,
        developer_wait_ticks=8,
    )
    page = receipt(facts)
    for line in page.splitlines():
        print(f"18:00  {line}" if line.startswith("ran") else f"       {line.strip()}")


def main() -> int:
    nine_am_the_preflight()
    all_morning_the_loop()
    two_pm_the_swaps()
    six_pm_the_receipt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
