from __future__ import annotations

import pytest

from forge.aliases import AliasBook
from forge.errors import Invalid, Missing, Stale
from forge.graph import Graph


def book() -> AliasBook:
    graph = Graph()
    graph.declare("network_lib")
    built = AliasBook(graph=graph)
    built.declare("netlib", "network_lib", expires=100)
    return built


class TestResolution:
    def test_the_old_name_forwards_before_the_deadline(self):
        assert book().resolve("netlib", "billing", now=50) == (
            "network_lib"
        )

    def test_real_names_pass_through_untouched(self):
        assert book().resolve("network_lib", "billing", now=50) == (
            "network_lib"
        )

    def test_after_the_deadline_the_failure_carries_the_new_name(self):
        with pytest.raises(Stale, match="called network_lib now"):
            book().resolve("netlib", "billing", now=100)

    def test_every_resolution_is_counted_per_caller(self):
        built = book()
        built.resolve("netlib", "billing", now=1)
        built.resolve("netlib", "billing", now=2)
        built.resolve("netlib", "search", now=3)
        assert built.aliases["netlib"].callers == {
            "billing": 2,
            "search": 1,
        }


class TestDeclaration:
    def test_chains_are_refused_as_archaeology(self):
        built = book()
        built.graph.declare("other")
        with pytest.raises(Invalid, match="archaeology"):
            built.declare("ancient", "netlib", expires=200)

    def test_a_broken_signpost_is_refused(self):
        built = book()
        with pytest.raises(Missing, match="worse than none"):
            built.declare("dangling", "ghost_target", expires=200)

    def test_double_aliasing_is_refused(self):
        built = book()
        with pytest.raises(Invalid):
            built.declare("netlib", "network_lib", expires=300)


class TestTheWorklist:
    def test_the_nag_lists_callers_with_counts(self):
        built = book()
        built.resolve("netlib", "billing", now=1)
        page = built.worklist(now=50)
        assert page == (
            "netlib -> network_lib [50 ticks left]: billing (1x)"
        )

    def test_untouched_aliases_say_nobody_yet(self):
        assert "nobody yet" in book().worklist(now=50)

    def test_the_quiet_expired_are_safe_to_delete(self):
        built = book()
        assert built.safe_to_delete(now=150) == ["netlib"]
        built.resolve("netlib", "late_team", now=50)
        assert built.safe_to_delete(now=150) == []
