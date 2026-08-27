"""The platform manager's quarter: budgets, fault lines, and the cut.

Run with: python -m examples.platformquarter
"""

from __future__ import annotations

from forge.austerity import Program, austerity_plan
from forge.errorbudget import ErrorBudget
from forge.faultline import FaultLineReport
from forge.pagebudget import PageBudget
from forge.tickbill import ClassBill, compare_months
from forge.workermatch import Pool


def week_one_the_error_budget():
    budget = ErrorBudget(window_builds=10000, promise_percent=99.0)
    budget.burn("worker-death", 60)
    budget.burn("cache-corruption", 20)
    print(f"week 1:  {budget.window_report().splitlines()[0]}")
    print(f"         {budget.window_report().splitlines()[-1].strip()}")


def week_three_the_pages():
    pages = PageBudget(weekly_cap=6)
    for number in range(8):
        pages.raise_alert(
            "flaky-disk-monitor", "warning", f"blip {number}"
        )
    pages.raise_alert("cache-corruption", "critical", "mismatch")
    pages.flush_week()
    print(f"week 3:  {pages.spend_ledger().splitlines()[-1].strip()}")


def week_six_the_fault_line():
    report = FaultLineReport(
        pools=[
            Pool(name="linux-a", offers=(("os", "linux"),), slots=20),
            Pool(name="linux-b", offers=(("os", "linux"),), slots=20),
            Pool(
                name="mac-sign",
                offers=(("os", "mac"), ("signing", "yes")),
                slots=2,
            ),
        ],
        demand_classes={
            "compile": {"os": "linux"},
            "release-sign": {"os": "mac", "signing": "yes"},
        },
    )
    print(f"week 6:  {report.report().splitlines()[0]}")


def week_nine_the_tick_bill():
    may = {
        "compile": ClassBill("compile", 200, 2000),
        "test": ClassBill("test", 100, 1000),
    }
    june = {
        "compile": ClassBill("compile", 220, 2860),
        "test": ClassBill("test", 90, 900),
    }
    print(f"week 9:  {compare_months(may, june).splitlines()[-1]}")


def week_twelve_the_cut():
    plan = austerity_plan(
        [
            Program("prewarming", 100, 700),
            Program("hedging", 200, 600),
            Program(
                "nightly-cleanroom", 80, 0, insurance=True
            ),
        ],
        budget_per_week=200,
    )
    print(f"week 12: {plan.splitlines()[0]}")
    print(f"         {plan.splitlines()[-1].strip()}")


def main() -> int:
    week_one_the_error_budget()
    week_three_the_pages()
    week_six_the_fault_line()
    week_nine_the_tick_bill()
    week_twelve_the_cut()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
