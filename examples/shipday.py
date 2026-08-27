"""Ship day: the train, the ladder, the gate, and the boring go.

Run with: python -m examples.shipday
"""

from __future__ import annotations

from forge.handover import Handover
from forge.promotion import Ladder
from forge.receipt import BuildFacts, receipt
from forge.releasetrain import CherryPick, ReleaseTrain
from forge.shipgate import ShipGate

DIGEST = "feedface0011"


def morning_the_train():
    train = ReleaseTrain(version="24.4", cut_commit="c5120")
    train.advance()
    train.request(
        CherryPick(
            fix="tls-fix",
            approvals=2,
            risk_note="touches the handshake cache",
        )
    )
    train.request(CherryPick(fix="drive-by", approvals=1))
    print(f"morning: {train.manifest().splitlines()[0]}")
    print("         boarded 1, turned away 1")


def midday_the_ladder():
    ladder = Ladder()
    ladder.enter("app-24.4", DIGEST)
    for _ in range(3):
        ladder.promote("app-24.4", DIGEST)
    print(f"midday:  {ladder.story('app-24.4').splitlines()[-1]}")


def afternoon_the_gate():
    gate = ShipGate()
    gate.report("audits", True, "20 audits, 0 broken")
    gate.report("errorbudget", True, "70 of 100 spent")
    gate.report("cleanroom", True, "trust renewed")
    print(f"gate:    {gate.decide().splitlines()[0]}")


def evening_the_receipt_and_the_handover():
    facts = BuildFacts(
        targets_ran=2,
        cache_hits=40,
        cutoff_skips=6,
        interface_skips=9,
        farm_ticks=200,
        developer_wait_ticks=12,
    )
    print(f"evening: {receipt(facts).splitlines()[0]}")
    shift = Handover(outgoing="kiruthika")
    print(f"night:   {shift.note()}")


def main() -> int:
    morning_the_train()
    midday_the_ladder()
    afternoon_the_gate()
    evening_the_receipt_and_the_handover()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
