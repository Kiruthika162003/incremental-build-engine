from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.visibility import (
    PUBLIC,
    Visibility,
    VisibilityWall,
    package_of,
)


def monorepo() -> VisibilityWall:
    graph = Graph()
    graph.declare("auth/session")
    graph.declare("auth/internal")
    graph.declare("billing/charge", needs=("auth/session",))
    graph.declare("auth/api", needs=("auth/internal",))
    wall = VisibilityWall(graph=graph)
    wall.declare("auth/session", PUBLIC)
    return wall


class TestPackages:
    def test_the_package_is_the_directory(self):
        assert package_of("auth/session") == "auth"
        assert package_of("rootfile") == ""

    def test_bad_visibility_kinds_are_refused(self):
        with pytest.raises(Invalid):
            Visibility(kind="secret")
        with pytest.raises(Invalid, match="at least one"):
            Visibility(kind="restricted")


class TestTheWall:
    def test_public_targets_cross_packages_freely(self):
        assert monorepo().violations() == []

    def test_private_is_the_default_and_walls_hold(self):
        wall = monorepo()
        wall.graph.declare(
            "billing/report", needs=("auth/internal",)
        )
        violations = wall.violations()
        assert len(violations) == 1
        assert "billing/report may not see auth/internal" in violations[0]

    def test_same_package_sees_its_own_privates(self):
        wall = monorepo()
        assert wall.may_depend("auth/api", "auth/internal")

    def test_restricted_admits_the_named_and_nobody_else(self):
        wall = monorepo()
        wall.graph.declare("search/index", needs=())
        wall.declare(
            "auth/internal",
            Visibility(kind="restricted", allowed=("billing",)),
        )
        assert wall.may_depend("billing/charge", "auth/internal")
        assert not wall.may_depend("search/index", "auth/internal")

    def test_assert_walled_raises_with_every_breach(self):
        wall = monorepo()
        wall.graph.declare(
            "billing/report", needs=("auth/internal",)
        )
        with pytest.raises(Invalid, match="may not see"):
            wall.assert_walled()


class TestTheAdvice:
    def test_the_grant_is_a_diff_not_a_debate(self):
        wall = monorepo()
        advice = wall.widen_advice("billing/report", "auth/internal")
        assert advice == (
            "declare auth/internal restricted to ['billing']"
        )

    def test_widening_a_restriction_keeps_the_existing_grants(self):
        wall = monorepo()
        wall.declare(
            "auth/internal",
            Visibility(kind="restricted", allowed=("billing",)),
        )
        advice = wall.widen_advice("search/index", "auth/internal")
        assert advice == (
            "declare auth/internal restricted to ['billing', 'search']"
        )
