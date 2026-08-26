from __future__ import annotations

import pytest

from forge.buildfile import parse, render
from forge.errors import Invalid

GOOD = """
source = main.c
source = lib.c

rule = main.o
command = cc -O2
reads = main.c
writes = main.o
needs = main.c

rule = app          # the final link
command = ld
reads = main.o
writes = app
needs = main.o
cost = 5
"""


class TestParsing:
    def test_a_good_file_round_trips_its_meaning(self):
        parsed = parse(GOOD)
        assert parsed.sources == ["main.c", "lib.c"]
        assert parsed.stanzas["app"].cost == 5
        assert parsed.stanzas["app"].needs == ("main.o",)

    def test_comments_and_blanks_are_invisible(self):
        parsed = parse(GOOD)
        assert parsed.stanzas["app"].command == "ld"

    def test_order_lists_sources_then_rules(self):
        assert parse(GOOD).order() == ["main.c", "lib.c", "main.o", "app"]

    def test_render_reparses_to_the_same_meaning(self):
        parsed = parse(GOOD)
        again = parse(render(parsed))
        assert again.sources == parsed.sources
        assert set(again.stanzas) == set(parsed.stanzas)
        assert again.stanzas["app"].cost == 5


class TestRefusals:
    def test_unknown_fields_are_named_with_the_knowns(self):
        with pytest.raises(Invalid, match="unknown field 'wrties'"):
            parse("rule = a\nwrties = x\ncommand = c\nwrites = y")

    def test_the_line_number_travels_with_the_error(self):
        with pytest.raises(Invalid, match="line 3"):
            parse("rule = a\ncommand = c\nbogus = 1\nwrites = x")

    def test_duplicate_rules_are_refused(self):
        with pytest.raises(Invalid, match="declared twice"):
            parse(
                "rule = a\ncommand = c\nwrites = x\n"
                "rule = a\ncommand = c\nwrites = y"
            )

    def test_fields_before_any_rule_are_refused(self):
        with pytest.raises(Invalid, match="before any rule"):
            parse("command = cc")

    def test_a_need_nothing_declares_fails_at_load(self):
        with pytest.raises(Invalid, match="which nothing declares"):
            parse(
                "rule = app\ncommand = ld\nwrites = app\nneeds = ghost.o"
            )

    def test_a_rule_without_outputs_fails_at_load(self):
        with pytest.raises(Invalid, match="writes nothing"):
            parse("rule = a\ncommand = c")

    def test_a_rule_without_a_command_fails_at_load(self):
        with pytest.raises(Invalid, match="has no command"):
            parse("rule = a\nwrites = x")

    def test_sources_after_rules_are_refused(self):
        with pytest.raises(Invalid, match="belong before rules"):
            parse(
                "rule = a\ncommand = c\nwrites = x\nsource = late.c"
            )

    def test_costs_must_be_whole_numbers(self):
        with pytest.raises(Invalid, match="whole number"):
            parse(
                "rule = a\ncommand = c\nwrites = x\ncost = 2.5"
            )
