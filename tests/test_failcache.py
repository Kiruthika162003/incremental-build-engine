from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.failcache import FailureCache

KEY = "compile:parser|inputs=abc123"
ERROR = "parser.c:88: unknown type name 'tokn_t'"


def certified_cache() -> FailureCache:
    cache = FailureCache()
    cache.report_failure(KEY, ERROR, run_ticks=90)
    cache.report_failure(KEY, ERROR, run_ticks=90)
    return cache


class TestCertification:
    def test_one_sighting_is_not_enough(self):
        cache = FailureCache()
        verdict = cache.report_failure(KEY, ERROR, run_ticks=90)
        assert "one reproduction away" in verdict
        assert cache.lookup(KEY, run_ticks=90) is None

    def test_two_matching_sightings_certify(self):
        cache = certified_cache()
        assert KEY in cache.certified
        served = cache.lookup(KEY, run_ticks=90)
        assert served is not None
        assert "bust this entry" in served

    def test_two_different_errors_refuse_loudly(self):
        cache = FailureCache()
        cache.report_failure(KEY, ERROR, run_ticks=90)
        verdict = cache.report_failure(
            KEY, "linker timeout", run_ticks=90
        )
        assert verdict.startswith("REFUSED")
        assert "permanent lie" in verdict
        assert cache.lookup(KEY, run_ticks=90) is None

    def test_an_empty_error_is_refused(self):
        with pytest.raises(Invalid):
            FailureCache().report_failure(KEY, " ", run_ticks=1)


class TestTheEconomics:
    def test_served_failures_bank_their_run_cost(self):
        cache = certified_cache()
        for _ in range(12):
            cache.lookup(KEY, run_ticks=90)
        ledger = cache.ledger()
        assert "12 failure(s) served" in ledger
        assert "1080 tick(s) saved" in ledger
        assert "90 spent certifying" in ledger

    def test_the_fix_busts_the_entry_by_construction(self):
        cache = certified_cache()
        fixed_key = "compile:parser|inputs=def456"
        assert cache.lookup(fixed_key, run_ticks=90) is None
