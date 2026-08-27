from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.hotswap import HotSession
from forge.symbolselect import SourceUnit, Symbol

VIEW = Symbol(name="view", signature="(req) -> Response", public=True)


def unit(path, body, symbols=(VIEW,)):
    return SourceUnit(
        path=path, body=body, symbols=tuple(symbols)
    )


def session() -> HotSession:
    built = HotSession()
    built.admit(unit("views.py", "v1"))
    built.admit(unit("state.py", "s1"), holds_state=True)
    return built


class TestTheGate:
    def test_a_body_edit_swaps_in_place(self):
        live = session()
        assert live.save(unit("views.py", "v2")) == (
            "views.py: hot swap, body only"
        )
        assert live.swaps == 1

    def test_an_interface_change_restarts(self):
        live = session()
        wider = Symbol(
            name="view",
            signature="(req, ctx) -> Response",
            public=True,
        )
        verdict = live.save(
            unit("views.py", "v2", symbols=(wider,))
        )
        assert "the public face moved" in verdict
        assert live.restarts == 1

    def test_stateful_modules_always_restart(self):
        live = session()
        verdict = live.save(unit("state.py", "s2"))
        assert "classic unreproducible bug" in verdict
        assert live.restarts == 1

    def test_an_empty_save_does_nothing(self):
        live = session()
        assert "nothing moved" in live.save(unit("views.py", "v1"))
        assert live.quiet_saves == 1
        assert live.ticks_paid == 0

    def test_a_stranger_module_is_refused(self):
        with pytest.raises(Invalid):
            session().save(unit("ghost.py", "x"))


class TestTheRhythm:
    def test_the_bill_prices_the_gate_against_the_baseline(self):
        live = session()
        for round_number in range(2, 6):
            live.save(unit("views.py", f"v{round_number}"))
        live.save(unit("state.py", "s2"))
        assert live.rhythm_bill() == (
            "4 swap(s), 1 restart(s), 0 quiet save(s): paid "
            "16 ticks where restart-everything pays 60, saving 44"
        )
