from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.strictdeps import StrictChecker


def world() -> StrictChecker:
    checker = StrictChecker()
    checker.provides("jsonlib", ("parse_json", "dump_json"))
    checker.provides("httplib", ("http_get", "http_post"))
    checker.provides("loglib", ("log_info",))
    return checker


class TestFreeloading:
    def test_declared_use_passes_clean(self):
        violations, hoarded = world().check(
            "app",
            declared_deps=("jsonlib",),
            consumed_symbols=("parse_json",),
        )
        assert violations == []
        assert hoarded == []

    def test_the_transitive_arrival_is_visible_but_unusable(self):
        violations, _ = world().check(
            "app",
            declared_deps=("jsonlib",),
            consumed_symbols=("parse_json", "http_get"),
        )
        assert violations == [
            "app uses http_get from httplib without declaring it; "
            "add: needs = httplib"
        ]

    def test_a_symbol_nobody_provides_is_refused(self):
        with pytest.raises(Invalid, match="nothing provides"):
            world().check(
                "app",
                declared_deps=(),
                consumed_symbols=("teleport",),
            )

    def test_a_dep_that_provides_nothing_is_refused(self):
        with pytest.raises(Invalid, match="provides nothing"):
            world().check(
                "app",
                declared_deps=("mystery",),
                consumed_symbols=(),
            )


class TestHoarding:
    def test_the_unused_declaration_is_named(self):
        _, hoarded = world().check(
            "app",
            declared_deps=("jsonlib", "loglib"),
            consumed_symbols=("parse_json",),
        )
        assert hoarded == [
            "app declares loglib but consumes nothing from it"
        ]

    def test_the_diet_reads_both_lists(self):
        page = world().diet(
            "app",
            declared_deps=("loglib",),
            consumed_symbols=("parse_json",),
        )
        assert "without declaring it" in page
        assert "consumes nothing from it" in page

    def test_a_matched_diet_says_so(self):
        assert world().diet(
            "app",
            declared_deps=("jsonlib",),
            consumed_symbols=("dump_json",),
        ) == "app: the declaration matches the diet"


class TestProviders:
    def test_one_name_one_home(self):
        checker = world()
        with pytest.raises(Invalid, match="one name, one home"):
            checker.provides("rival", ("parse_json",))

    def test_double_provision_is_refused(self):
        checker = world()
        with pytest.raises(Invalid):
            checker.provides("jsonlib", ("extra",))
