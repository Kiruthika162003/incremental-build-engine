"""A performance week: gates that know their noise, budgets with owners.

Run with: python -m examples.perfweek
"""

from __future__ import annotations

from forge.failfirst import FailFirstScheduler, FailureHistory
from forge.perfgate import Bench, fleet_report
from forge.pgo import Profile
from forge.pgo import verdict as pgo_verdict
from forge.suitebudget import DirectoryBudget, suite_report


def monday_the_gates():
    pairs = [
        (
            Bench(name="parse", samples=(100, 101, 99, 100)),
            Bench(name="parse", samples=(108, 109, 107, 108)),
        ),
        (
            Bench(name="render", samples=(100, 92, 108)),
            Bench(name="render", samples=(104, 96, 112)),
        ),
    ]
    report = fleet_report(pairs, threshold_percent=5)
    print(f"monday:  {report.splitlines()[0]}")
    print(f"         {report.splitlines()[1].strip()}")


def tuesday_the_profile():
    profile = Profile(
        build_id="rel-142",
        functions=("parse", "render", "walk", "hash_page", "encode"),
    )
    live = {"parse", "render", "walk", "hash_page_v2", "encode2"}
    print(f"tuesday: {pgo_verdict(profile, live)}")


def wednesday_the_budgets():
    parser_dir = DirectoryBudget(
        directory="tests/parser",
        allowance_ms=500,
        per_test_norm_ms=100,
    )
    parser_dir.admit("test_tokens", 40)
    parser_dir.admit("test_tree", 60)
    integration = DirectoryBudget(
        directory="tests/integration",
        allowance_ms=100,
        per_test_norm_ms=100,
    )
    integration.admit("test_end_to_end", 90)
    integration.admit("test_smoke", 60)
    report = suite_report([parser_dir, integration])
    print(f"wednesday: {report.splitlines()[0]}")
    print(f"           {report.splitlines()[1]}")


def thursday_the_ordering():
    history = FailureHistory()
    for _ in range(5):
        history.record("test_api", True)
        history.record("test_zpipeline", False)
    scheduler = FailFirstScheduler(
        history=history,
        costs={"test_api": 60, "test_zpipeline": 30},
    )
    print(
        "thursday: "
        + scheduler.savings_report(failing={"test_zpipeline"})
    )


def main() -> int:
    monday_the_gates()
    tuesday_the_profile()
    wednesday_the_budgets()
    thursday_the_ordering()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
