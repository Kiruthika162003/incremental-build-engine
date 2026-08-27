from __future__ import annotations

import pytest

from forge.digestmail import WeeklyDigest
from forge.errors import Invalid


def week() -> WeeklyDigest:
    digest = WeeklyDigest()
    digest.add_section(
        "info",
        "tickbill",
        "compile ticks up 8 percent",
        "volume, not unit cost; the graph grew",
    )
    digest.add_section(
        "incident",
        "cacheproof",
        "one KEYBUG caught",
        "compile:app served stale bytes; entry invalidated",
    )
    digest.add_section("warning", "waterline", "disk ETA", "")
    return digest


class TestTheDigest:
    def test_severity_orders_and_sources_are_named(self):
        page = week().render()
        lines = page.splitlines()
        assert lines[0] == (
            "[incident] one KEYBUG caught (per cacheproof)"
        )
        assert "(per tickbill)" in page

    def test_empty_bodies_are_omitted_and_counted(self):
        page = week().render()
        assert "waterline" not in page
        assert "1 quiet section(s) omitted" in page
        assert "make the loud ones legible" in page

    def test_the_all_quiet_week_is_one_line(self):
        digest = WeeklyDigest()
        digest.add_section("info", "tickbill", "x", "")
        digest.add_section("info", "waterline", "y", " ")
        page = digest.render()
        assert page.startswith("all quiet (2 organ(s)")
        assert "respects the reader" in page

    def test_sourceless_lines_are_rumors(self):
        with pytest.raises(Invalid) as caught:
            WeeklyDigest().add_section("info", " ", "t", "b")
        assert "a rumor with formatting" in str(caught.value)

    def test_wild_severities_are_refused(self):
        with pytest.raises(Invalid):
            WeeklyDigest().add_section("loud", "organ", "t", "b")
