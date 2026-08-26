from __future__ import annotations

import pytest

from forge.buildhealth import HealthPage
from forge.errors import Invalid


def healthy_page() -> HealthPage:
    page = HealthPage()
    page.take("cache_hit_rate", 0.85)
    page.take("hermetic_leaks", 0)
    page.take("flaky_rules", 0)
    page.take("log_deterministic", True)
    page.take("path_growth_pct", 3)
    return page


class TestGrading:
    def test_a_healthy_build_reads_healthy(self):
        assert healthy_page().verdict() == "healthy on all five axes"

    def test_the_verdict_is_the_minimum_never_the_average(self):
        page = healthy_page()
        page.take("hermetic_leaks", 1)
        verdict = page.verdict()
        assert verdict.startswith("UNHEALTHY: 1 axis(es) failing")
        assert "start at hermetic_leaks" in verdict
        assert "owner forge.hermetic" in verdict

    def test_each_line_carries_number_threshold_and_owner(self):
        page = healthy_page()
        assert (
            "cache_hit_rate: 0.85 (above 0.5) [ok, owner forge.cache]"
            in page.page()
        )

    def test_a_failing_line_says_failing(self):
        page = healthy_page()
        page.take("flaky_rules", 2)
        assert (
            "flaky_rules: 2 (at_most 0) [FAILING, owner forge.flaky]"
            in page.page()
        )


class TestContracts:
    def test_unknown_axes_are_refused_with_the_roster(self):
        with pytest.raises(Invalid, match="the page tracks"):
            HealthPage().take("vibes", 10)

    def test_an_incomplete_page_refuses_to_judge(self):
        page = HealthPage()
        page.take("cache_hit_rate", 0.9)
        with pytest.raises(Invalid, match="incomplete"):
            page.verdict()

    def test_nondeterministic_logs_fail_the_axis(self):
        page = healthy_page()
        page.take("log_deterministic", False)
        assert "UNHEALTHY" in page.verdict()
