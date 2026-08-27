from __future__ import annotations

import pytest

from forge.debounce import FORCE_CEILING, QUIET_WINDOW, Debouncer
from forge.errors import Invalid


class TestBursts:
    def test_the_burst_holds_while_events_arrive(self):
        bouncer = Debouncer()
        bouncer.event("main.c", now=0)
        bouncer.event("main.c", now=1)
        bouncer.event("main.c", now=2)
        assert bouncer.poll(now=3) is None

    def test_the_quiet_window_releases_one_batch(self):
        bouncer = Debouncer()
        bouncer.event("main.c", now=0)
        bouncer.event("lib.c", now=1)
        batch = bouncer.poll(now=1 + QUIET_WINDOW)
        assert batch == ["lib.c", "main.c"]
        assert bouncer.batches_out == 1

    def test_four_saves_in_a_burst_start_one_build(self):
        bouncer = Debouncer()
        for tick in range(4):
            bouncer.event("main.c", now=tick)
        batch = bouncer.poll(now=3 + QUIET_WINDOW)
        assert batch == ["main.c"]
        assert bouncer.salary() == (
            "4 events became 1 batches; 3 builds never started "
            "(0 force releases)"
        )

    def test_silence_polls_return_nothing(self):
        assert Debouncer().poll(now=100) is None


class TestTheCeiling:
    def test_the_chatty_tool_is_force_released(self):
        bouncer = Debouncer()
        for tick in range(FORCE_CEILING + 2):
            bouncer.event("build.log", now=tick)
        batch = bouncer.poll(now=FORCE_CEILING)
        assert batch == ["build.log"]
        assert bouncer.force_releases == 1

    def test_the_next_burst_starts_fresh_after_release(self):
        bouncer = Debouncer()
        bouncer.event("main.c", now=0)
        bouncer.poll(now=QUIET_WINDOW)
        bouncer.event("lib.c", now=20)
        assert bouncer.poll(now=21) is None
        assert bouncer.poll(now=20 + QUIET_WINDOW) == ["lib.c"]

    def test_an_unemployed_debouncer_has_no_salary(self):
        with pytest.raises(Invalid):
            Debouncer().salary()
