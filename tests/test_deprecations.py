from __future__ import annotations

import pytest

from forge.deprecations import DeprecationRegistry
from forge.errors import Invalid


def registry() -> DeprecationRegistry:
    built = DeprecationRegistry()
    built.deprecate("srcs_glob", "explicit_srcs", grace_uses=3)
    built.deprecate("copy_outputs", "install_to", grace_uses=5)
    return built


class TestLifecycle:
    def test_a_current_attribute_passes_quietly(self):
        assert registry().observe("name", "lib") == (
            "name: current, carry on"
        )

    def test_the_warning_names_the_replacement_and_budget(self):
        assert registry().observe("srcs_glob", "corelib") == (
            "corelib: srcs_glob is deprecated, use "
            "explicit_srcs (2 grace use(s) left)"
        )

    def test_the_spent_budget_escalates_to_refusal(self):
        reg = registry()
        for number in range(3):
            reg.observe("srcs_glob", f"lib{number}")
        with pytest.raises(Invalid) as caught:
            reg.observe("srcs_glob", "late-lib")
        assert "grace budget of 3 is spent" in str(caught.value)
        assert "migrate to explicit_srcs" in str(caught.value)

    def test_zero_grace_is_just_a_removal(self):
        with pytest.raises(Invalid):
            DeprecationRegistry().deprecate("a", "b", grace_uses=0)

    def test_self_replacement_is_refused(self):
        with pytest.raises(Invalid):
            DeprecationRegistry().deprecate("a", "a", grace_uses=1)

    def test_double_deprecation_is_refused(self):
        reg = registry()
        with pytest.raises(Invalid):
            reg.deprecate("srcs_glob", "other", grace_uses=1)


class TestTheCensus:
    def test_the_closest_hammer_sorts_first(self):
        reg = registry()
        reg.observe("srcs_glob", "a")
        reg.observe("srcs_glob", "b")
        reg.observe("copy_outputs", "c")
        census = reg.census().splitlines()
        assert census[0] == "2 deprecation(s) in flight"
        assert census[1] == (
            "  srcs_glob -> explicit_srcs: 2 use(s), 1 grace left"
        )

    def test_the_unused_deprecation_is_declared_finished(self):
        census = registry().census()
        assert (
            "srcs_glob: never used in the window; delete the "
            "attribute outright"
        ) in census

    def test_an_empty_registry_is_at_peace(self):
        assert DeprecationRegistry().census() == (
            "no deprecations; the schema is at peace"
        )
