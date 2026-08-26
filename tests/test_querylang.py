from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.graph import Graph
from forge.querylang import QueryRunner


def runner() -> QueryRunner:
    graph = Graph()
    graph.declare("base")
    graph.declare("util", needs=("base",))
    graph.declare("app", needs=("util", "base"))
    return QueryRunner(graph=graph)


class TestTheVerbs:
    def test_deps_answers_one_per_line(self):
        assert runner().run("deps(app)") == "base\nutil"

    def test_rdeps_answers_the_blast(self):
        assert runner().run("rdeps(base)") == "app\nutil"

    def test_somepath_prints_the_chain(self):
        assert runner().run("somepath(app, base)") == "app\nbase"

    def test_allpaths_is_just_the_number(self):
        assert runner().run("allpaths(app, base)") == "2"

    def test_count_wraps_any_other_query(self):
        assert runner().run("count(deps(app))") == "2"
        assert runner().run("count(rdeps(app))") == "0"

    def test_whitespace_is_forgiven(self):
        assert runner().run("  deps( app )  ") == "base\nutil"


class TestRefusals:
    def test_unknown_verbs_list_the_language(self):
        with pytest.raises(Invalid, match="the language has"):
            runner().run("friends(app)")

    def test_shapeless_text_is_named(self):
        with pytest.raises(Invalid, match="verb\\(args\\)"):
            runner().run("deps app")

    def test_arity_mismatches_say_what_was_wanted(self):
        with pytest.raises(Invalid, match="takes 2 arguments; got 1"):
            runner().run("somepath(app)")

    def test_unknown_targets_keep_the_graphs_own_error(self):
        with pytest.raises(Missing):
            runner().run("deps(ghost)")
