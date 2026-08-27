from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.waterline import Waterline


def steady_riser() -> Waterline:
    line = Waterline(capacity=1000)
    for used in (600, 700, 800, 900):
        line.observe(used)
    return line


class TestTheForecast:
    def test_the_steady_rate_names_the_day_unrounded(self):
        forecast = steady_riser().forecast()
        assert forecast.startswith(
            "fills in 1.0 day(s) at 100/day"
        )
        assert "who needed the one" in forecast

    def test_the_erratic_rate_declines_with_the_variance(self):
        line = Waterline(capacity=1000)
        for used in (100, 110, 400, 420):
            line.observe(used)
        forecast = line.forecast()
        assert forecast.startswith("no forecast: the rate swings")
        assert "a horoscope with units" in forecast

    def test_the_falling_waterline_says_so(self):
        line = Waterline(capacity=1000)
        for used in (900, 800, 700):
            line.observe(used)
        assert "falling or flat" in line.forecast()

    def test_two_points_are_not_a_rate(self):
        line = Waterline(capacity=100)
        line.observe(10)
        line.observe(20)
        with pytest.raises(Invalid):
            line.forecast()

    def test_usage_beyond_capacity_is_refused(self):
        with pytest.raises(Invalid):
            Waterline(capacity=100).observe(150)
