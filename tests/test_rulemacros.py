from __future__ import annotations

import pytest

from forge.buildfile import Stanza
from forge.errors import Invalid
from forge.rulemacros import MacroRegistry, compile_test_report


def registry() -> MacroRegistry:
    reg = MacroRegistry()
    reg.define("ctr", compile_test_report)
    return reg


class TestExpansion:
    def test_one_call_becomes_three_stanzas(self):
        stanzas = registry().expand(
            "ctr", "auth", {"inputs": ("auth.c",)}
        )
        assert [stanza.name for stanza in stanzas] == [
            "auth.obj",
            "auth.test",
            "auth.report",
        ]

    def test_two_instances_cannot_collide_by_construction(self):
        reg = registry()
        first = reg.expand("ctr", "auth", {"inputs": ("auth.c",)})
        second = reg.expand("ctr", "billing", {"inputs": ("billing.c",)})
        names = {stanza.name for stanza in first} | {
            stanza.name for stanza in second
        }
        assert len(names) == 6

    def test_an_unknown_macro_lists_the_defined(self):
        with pytest.raises(Invalid, match="defined are"):
            registry().expand("ghost", "x", {})

    def test_double_definition_is_refused(self):
        reg = registry()
        with pytest.raises(Invalid):
            reg.define("ctr", compile_test_report)


class TestHygiene:
    def test_a_stanza_outside_the_prefix_is_refused(self):
        def rogue(instance: str, params: dict) -> list[Stanza]:
            del instance, params
            return [
                Stanza(
                    name="global-target",
                    command="cc",
                    writes=("x",),
                )
            ]

        reg = MacroRegistry()
        reg.define("rogue", rogue)
        with pytest.raises(Invalid, match="outside its prefix"):
            reg.expand("rogue", "auth", {})

    def test_reaching_for_a_strangers_target_is_refused(self):
        def grabby(instance: str, params: dict) -> list[Stanza]:
            del params
            return [
                Stanza(
                    name=f"{instance}.obj",
                    command="cc",
                    writes=(f"{instance}.obj",),
                    needs=("billing.obj",),
                )
            ]

        reg = MacroRegistry()
        reg.define("grabby", grabby)
        with pytest.raises(Invalid, match="neither internal nor"):
            reg.expand("grabby", "auth", {"inputs": ()})

    def test_declared_inputs_may_cross_the_prefix(self):
        stanzas = registry().expand(
            "ctr", "auth", {"inputs": ("auth.c",)}
        )
        assert stanzas[0].needs == ("auth.c",)

    def test_an_empty_expansion_is_a_confident_typo(self):
        def hollow(instance: str, params: dict) -> list[Stanza]:
            del instance, params
            return []

        reg = MacroRegistry()
        reg.define("hollow", hollow)
        with pytest.raises(Invalid, match="typo with confidence"):
            reg.expand("hollow", "x", {})
