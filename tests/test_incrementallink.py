from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.incrementallink import IncrementalLinker, ObjectState

MAIN = ObjectState(symbols=("main",), size=100)
UTIL = ObjectState(symbols=("util_a", "util_b"), size=80)


def linked() -> IncrementalLinker:
    linker = IncrementalLinker(reserved_padding=20)
    linker.link({"main.o": MAIN, "util.o": UTIL}, binary_digest=None)
    return linker


class TestTheEnvelope:
    def test_the_first_build_is_a_full_link(self):
        linker = IncrementalLinker(reserved_padding=20)
        outcome = linker.link({"main.o": MAIN}, binary_digest=None)
        assert outcome == "full link (first build)"

    def test_a_body_edit_inside_padding_patches(self):
        linker = linked()
        grown = ObjectState(symbols=("main",), size=110)
        outcome = linker.link(
            {"main.o": grown, "util.o": UTIL},
            binary_digest=linker.last_binary_digest,
        )
        assert outcome == "patched main.o in place"
        assert linker.patches == 1

    def test_a_symbol_change_falls_back_with_the_reason(self):
        linker = linked()
        resymboled = ObjectState(symbols=("main", "extra"), size=100)
        outcome = linker.link(
            {"main.o": resymboled, "util.o": UTIL},
            binary_digest=linker.last_binary_digest,
        )
        assert outcome == "full link (main.o's symbol set moved)"

    def test_outgrowing_the_padding_falls_back(self):
        linker = linked()
        fat = ObjectState(symbols=("main",), size=130)
        outcome = linker.link(
            {"main.o": fat, "util.o": UTIL},
            binary_digest=linker.last_binary_digest,
        )
        assert "outgrew its reserved padding" in outcome

    def test_two_changed_objects_are_not_a_surgery(self):
        linker = linked()
        outcome = linker.link(
            {
                "main.o": ObjectState(symbols=("main",), size=101),
                "util.o": ObjectState(
                    symbols=("util_a", "util_b"), size=81
                ),
            },
            binary_digest=linker.last_binary_digest,
        )
        assert "2 objects changed" in outcome

    def test_a_strangers_binary_is_never_patched(self):
        linker = linked()
        outcome = linker.link(
            {"main.o": MAIN, "util.o": UTIL},
            binary_digest="someone-elses-digest",
        )
        assert "not this linker's own child" in outcome

    def test_a_new_object_forces_the_full_link(self):
        linker = linked()
        outcome = linker.link(
            {
                "main.o": MAIN,
                "util.o": UTIL,
                "new.o": ObjectState(symbols=("newfn",), size=10),
            },
            binary_digest=linker.last_binary_digest,
        )
        assert "the object set changed" in outcome

    def test_an_empty_link_is_refused(self):
        with pytest.raises(Invalid):
            linked().link({}, binary_digest=None)


class TestTheSeason:
    def test_the_ledger_prices_against_always_full(self):
        linker = linked()
        for size in (101, 102, 103):
            linker.link(
                {
                    "main.o": ObjectState(symbols=("main",), size=size),
                    "util.o": UTIL,
                },
                binary_digest=linker.last_binary_digest,
            )
        assert linker.season_ledger() == (
            "3 patches, 1 full links; 108 ticks saved against "
            "always-full"
        )
