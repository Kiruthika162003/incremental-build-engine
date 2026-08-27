from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.ownership import OwnerBook


def book() -> OwnerBook:
    built = OwnerBook()
    built.declare("auth", ("meera", "raj"))
    built.declare("auth/tokens", ("dana",))
    built.declare("billing", ("li",))
    return built


class TestRouting:
    def test_direct_ownership_wins(self):
        names, reason = book().route("auth/tokens")
        assert names == ("dana",)
        assert reason == "owned directly"

    def test_deep_paths_inherit_upward(self):
        names, reason = book().route("auth/tokens/rotation/keys")
        assert names == ("dana",)
        assert reason == "inherited from auth/tokens"

    def test_the_unowned_say_so_plainly(self):
        names, reason = book().route("search/index")
        assert names == ()
        assert reason == "no owner anywhere up the tree"

    def test_empty_owner_lists_are_refused(self):
        with pytest.raises(Invalid, match="orphan with"):
            OwnerBook().declare("x", ())


class TestTheAudit:
    def test_orphans_and_ghosts_are_separate_lists(self):
        orphans, ghosts = book().audit(
            ["auth", "billing", "search"],
            active_roster={"meera", "raj", "dana"},
        )
        assert orphans == ["search"]
        assert ghosts == ["billing"]

    def test_one_active_owner_is_enough(self):
        _, ghosts = book().audit(
            ["auth"], active_roster={"raj"}
        )
        assert ghosts == []


class TestTheLoad:
    def test_the_report_orders_by_weight(self):
        built = book()
        packages = ["auth", "auth/tokens", "billing"]
        report = built.load_report(packages)
        assert report.splitlines()[0] == "dana: 1 packages"

    def test_the_bus_factor_is_named_at_ten(self):
        built = OwnerBook()
        built.declare("mono", ("atlas",))
        packages = [f"mono/pkg{number}" for number in range(12)]
        report = built.load_report(packages)
        assert "atlas: 12 packages" in report
        assert "bus factor wearing a compliment" in report

    def test_an_empty_book_asks_for_a_volunteer(self):
        assert OwnerBook().load_report(["x"]) == (
            "nobody owns anything; start with a volunteer"
        )
