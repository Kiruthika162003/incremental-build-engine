"""A month of slowdown gets an address, and the address is over 100 percent.

May bills 3400 ticks and June bills 4160, a 22 percent
slowdown, and the naive expectation is that the guilty class
carries some fraction of that growth. The measured table says
compile carries 113 percent of it, which reads like an error
and is the audit's finding: shares of growth exceed 100 when
another class shrinks, here the test class paying back 100
ticks, and a report that clipped shares at 100 would hide the
credit and misprice the debit. The split inside the compile
debit is the second finding worth keeping: 200 of the 860 is
volume, more actions at May's unit price, and 660 is unit
cost, the same actions individually slower, so the defendant
is the toolchain or the inputs, not the team that grew the
graph.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.tickbill import ClassBill, compare_months

MAY = {
    "compile": ClassBill("compile", actions=200, total_ticks=2000),
    "link": ClassBill("link", actions=10, total_ticks=400),
    "test": ClassBill("test", actions=100, total_ticks=1000),
}
JUNE = {
    "compile": ClassBill("compile", actions=220, total_ticks=2860),
    "link": ClassBill("link", actions=10, total_ticks=400),
    "test": ClassBill("test", actions=90, total_ticks=900),
}


def run() -> Finding:
    report = compare_months(MAY, JUNE)
    numbers = {
        "may_total": 3400,
        "june_total": 4160,
        "growth": 760,
        "compile_debit": 860,
        "test_credit": -100,
        "compile_share_percent": 113,
        "volume_part": 200,
        "unit_cost_part": 660,
        "share_exceeds_hundred": "carries 113%" in report,
        "credit_printed": "credit test: -100" in report,
    }
    holds = (
        numbers["share_exceeds_hundred"]
        and numbers["credit_printed"]
        and "+22%" in report
        and "volume +200, unit cost +660" in report
    )
    return Finding(
        audit="growthaddress",
        claim=(
            "the guilty class carries 113 percent of the "
            "growth because the test class shrank; clipping "
            "shares at 100 would hide the credit and misprice "
            "the debit, and the 860 splits 200 volume against "
            "660 unit cost, indicting the toolchain, not the "
            "graph"
        ),
        numbers=numbers,
        holds=holds,
    )
