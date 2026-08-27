from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.policystack import PolicyStack, Rule


def sediment() -> PolicyStack:
    return PolicyStack(
        rules=[
            Rule(1, "allow", "public/*"),
            Rule(3, "allow", "secrets/build-keys"),
            Rule(9, "deny", "secrets/*"),
            Rule(12, "deny", "secrets/build-keys"),
        ]
    )


class TestEvaluation:
    def test_the_deciding_rule_is_named(self):
        assert sediment().evaluate("public/readme") == (
            "allow by rule 1 (public/*)"
        )
        assert sediment().evaluate("secrets/prod-cert") == (
            "deny by rule 9 (secrets/*)"
        )

    def test_the_earlier_allow_beats_the_later_deny(self):
        assert sediment().evaluate("secrets/build-keys") == (
            "allow by rule 3 (secrets/build-keys)"
        )

    def test_the_default_is_deny_with_a_shrug(self):
        assert "the stack ran out of opinions" in (
            sediment().evaluate("attic/junk")
        )

    def test_a_wild_effect_is_refused(self):
        with pytest.raises(Invalid):
            Rule(1, "maybe", "x")


class TestShadows:
    def test_the_shadowed_deny_is_named_with_its_shadower(self):
        found = sediment().shadows()
        assert len(found) == 1
        assert found[0] == (
            "rule 12 (deny secrets/build-keys) can never "
            "fire: rule 3 (allow secrets/build-keys) swallows it"
        )

    def test_a_wildcard_swallows_its_own_subpaths(self):
        stack = PolicyStack(
            rules=[
                Rule(1, "allow", "src/*"),
                Rule(2, "deny", "src/generated/*"),
            ]
        )
        assert len(stack.shadows()) == 1

    def test_the_lint_calls_shadows_false_protection(self):
        report = sediment().lint()
        assert report.startswith("1 shadowed rule(s)")
        assert "look like protection" in report

    def test_a_clean_stack_is_fully_reachable(self):
        stack = PolicyStack(
            rules=[
                Rule(1, "deny", "secrets/*"),
                Rule(2, "allow", "public/*"),
            ]
        )
        assert stack.lint() == "2 rule(s), every one reachable"
