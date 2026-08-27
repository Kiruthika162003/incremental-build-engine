from __future__ import annotations

import pytest

from forge.errors import Missing
from forge.symbolselect import (
    InterfaceSelector,
    SourceUnit,
    Symbol,
)

PARSE = Symbol(name="parse", signature="(text: str) -> Tree", public=True)
HELPER = Symbol(name="_scan", signature="(text: str) -> list", public=False)


def core(body: str, symbols=(PARSE, HELPER)) -> SourceUnit:
    return SourceUnit(
        path="core.py", body=body, symbols=tuple(symbols)
    )


def selector() -> InterfaceSelector:
    built = InterfaceSelector()
    built.admit(core("v1"), dependents=("app.py", "tool.py"))
    return built


class TestDigests:
    def test_private_symbols_do_not_touch_the_interface(self):
        with_helper = core("v1")
        without = core("v1", symbols=(PARSE,))
        assert (
            with_helper.interface_digest()
            == without.interface_digest()
        )

    def test_a_signature_change_moves_the_interface(self):
        widened = Symbol(
            name="parse",
            signature="(text: str, strict: bool) -> Tree",
            public=True,
        )
        assert (
            core("v1").interface_digest()
            != core("v1", symbols=(widened,)).interface_digest()
        )

    def test_a_unit_with_no_public_face_still_digests(self):
        assert core(
            "v1", symbols=(HELPER,)
        ).interface_digest()


class TestTheThreeOutcomes:
    def test_byte_identical_is_a_file_cutoff(self):
        chosen = selector()
        verdict = chosen.edit(core("v1"))
        assert "(file cutoff)" in verdict
        assert chosen.file_saves == 3

    def test_a_body_edit_recompiles_alone(self):
        chosen = selector()
        verdict = chosen.edit(core("v2"))
        assert "recompiles alone" in verdict
        assert "2 dependent(s) keep their objects" in verdict
        assert chosen.interface_saves == 2

    def test_a_public_change_names_who_pays(self):
        chosen = selector()
        widened = Symbol(
            name="parse",
            signature="(text: str, strict: bool) -> Tree",
            public=True,
        )
        verdict = chosen.edit(core("v2", symbols=(widened,)))
        assert "changed its public face" in verdict
        assert "app.py, tool.py" in verdict
        assert chosen.ripples == 1

    def test_a_stranger_edit_is_refused(self):
        with pytest.raises(Missing):
            selector().edit(
                SourceUnit(path="ghost.py", body="x", symbols=())
            )


class TestTheLedger:
    def test_the_ledger_splits_the_two_kinds_of_saving(self):
        chosen = selector()
        chosen.edit(core("v2"))
        chosen.edit(core("v3"))
        chosen.edit(core("v3"))
        assert chosen.ledger() == (
            "3 compiles saved by file cutoff, "
            "4 by interface cutoff, "
            "0 interface ripple(s) paid in full"
        )

    def test_a_new_private_helper_is_an_interface_save(self):
        chosen = selector()
        grown = core("v2", symbols=(PARSE, HELPER, Symbol(
            name="_cache", signature="() -> dict", public=False
        )))
        assert "(interface cutoff)" in chosen.edit(grown)
