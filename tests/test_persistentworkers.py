from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.persistentworkers import (
    REQUESTS_BEFORE_RETIREMENT,
    WorkerPool,
)

BOOTS = {"javac": 50, "protoc": 20}


class TestLeasing:
    def test_the_first_request_pays_the_toll(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        outcome, cost = pool.request("javac")
        assert outcome == "booted"
        assert cost == 51

    def test_the_second_request_rides_warm(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        pool.request("javac")
        outcome, cost = pool.request("javac")
        assert outcome == "warm"
        assert cost == 1

    def test_tools_do_not_share_workers(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        pool.request("javac")
        outcome, _ = pool.request("protoc")
        assert outcome == "booted"

    def test_an_unknown_tool_is_refused(self):
        with pytest.raises(Invalid, match="no boot cost"):
            WorkerPool(boot_costs=dict(BOOTS)).request("rustc")


class TestTheBudget:
    def test_overflow_retires_the_idlest(self):
        pool = WorkerPool(boot_costs=dict(BOOTS), budget=1)
        pool.request("javac")
        outcome, _ = pool.request("protoc")
        assert outcome == "booted"
        assert pool.retirements == 1
        assert [worker.tool for worker in pool.workers] == ["protoc"]

    def test_a_zero_budget_is_refused(self):
        with pytest.raises(Invalid):
            WorkerPool(boot_costs=dict(BOOTS), budget=0)


class TestDriftControl:
    def test_a_long_lived_worker_is_retired_on_schedule(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        pool.request("javac")
        for _ in range(REQUESTS_BEFORE_RETIREMENT - 2):
            outcome, _ = pool.request("javac")
            assert outcome == "warm"
        outcome, _ = pool.request("javac")
        assert outcome == "warm"
        assert pool.workers == []
        assert pool.retirements == 1

    def test_the_next_request_after_retirement_boots_fresh(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        for _ in range(REQUESTS_BEFORE_RETIREMENT):
            pool.request("javac")
        outcome, _ = pool.request("javac")
        assert outcome == "booted"


class TestAmortisation:
    def test_one_boot_spreads_over_a_hundred_requests(self):
        pool = WorkerPool(boot_costs=dict(BOOTS))
        for _ in range(100):
            pool.request("javac")
        assert pool.amortisation() == (
            "50 ticks of boot toll over 100 requests "
            "(0.5 per request), 1 retirements"
        )

    def test_an_idle_pool_refuses_the_question(self):
        with pytest.raises(Invalid):
            WorkerPool(boot_costs=dict(BOOTS)).amortisation()
