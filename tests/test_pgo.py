from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.pgo import (
    Profile,
    coverage,
    expected_speedup,
    refresh_ledger,
    verdict,
)

PROFILE = Profile(
    build_id="rel-142",
    functions=("parse", "render", "walk", "hash_page", "encode"),
)


class TestCoverage:
    def test_full_survival_is_full_coverage(self):
        live = set(PROFILE.functions)
        assert coverage(PROFILE, live) == 1.0

    def test_renamed_functions_decay_the_profile(self):
        live = {"parse", "render", "walk", "hash_page_v2", "encode2"}
        assert coverage(PROFILE, live) == 0.6

    def test_an_empty_profile_is_refused(self):
        with pytest.raises(Invalid):
            Profile(build_id="x", functions=())


class TestTheThreeVerdicts:
    def test_a_fresh_profile_is_used_with_its_number(self):
        live = set(PROFILE.functions)
        line = verdict(PROFILE, live)
        assert line.startswith("use it: 100%")
        assert "expect about 12%" in line

    def test_the_middle_band_says_refresh_soon(self):
        live = {"parse", "render", "walk", "x", "y"}
        line = verdict(PROFILE, live)
        assert line.startswith("refresh soon: coverage fell to 60%")
        assert "down to 7%" in line

    def test_below_the_floor_the_profile_is_refused(self):
        live = {"parse", "brand_new", "other"}
        line = verdict(PROFILE, live)
        assert line.startswith("refuse it: 20% coverage")
        assert "old opinion, not a cache" in line
        assert "4 profiled function(s) no longer exist" in line
        assert "first missing: encode" in line

    def test_the_speedup_cliff_is_zero_below_the_floor(self):
        assert expected_speedup(0.49) == 0
        assert expected_speedup(0.5) == 6


class TestTheRefreshLedger:
    def test_decay_that_outruns_the_cost_buys_a_refresh(self):
        report = refresh_ledger(
            [1.0, 0.9, 0.7, 0.55], refresh_cost_percent=8
        )
        assert "banked 38% where always-fresh banks 48%" in report
        assert "10% lost to decay" in report
        assert "the refresh pays for itself" in report

    def test_mild_decay_rides(self):
        report = refresh_ledger(
            [1.0, 0.95], refresh_cost_percent=8
        )
        assert "riding the decay is still cheaper" in report

    def test_bad_fractions_are_refused(self):
        with pytest.raises(Invalid):
            refresh_ledger([1.2], refresh_cost_percent=1)

    def test_an_empty_history_is_refused(self):
        with pytest.raises(Invalid):
            refresh_ledger([], refresh_cost_percent=1)
