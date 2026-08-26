from __future__ import annotations

import pytest

from forge.buildevents import EventStream
from forge.errors import Invalid, Stale


def healthy_stream() -> EventStream:
    stream = EventStream()
    stream.emit("started")
    stream.emit("action-queued", "main.o")
    stream.emit("action-running", "main.o")
    stream.emit("action-done", "main.o", "2 ticks")
    stream.emit("action-cached", "lib.o")
    stream.emit("finished", detail="1 ran, 1 cached")
    return stream


class TestEmission:
    def test_sequences_are_dense_from_one(self):
        stream = healthy_stream()
        assert [event.sequence for event in stream.events] == [
            1, 2, 3, 4, 5, 6,
        ]

    def test_unknown_kinds_are_refused_with_the_grammar(self):
        with pytest.raises(Invalid, match="the grammar has"):
            EventStream().emit("action-exploded")

    def test_the_line_reads_in_order(self):
        stream = healthy_stream()
        assert stream.events[3].line() == "[4] action-done main.o (2 ticks)"


class TestReplay:
    def test_a_late_subscriber_replays_from_anywhere(self):
        stream = healthy_stream()
        tail = stream.replay_from(5)
        assert [event.kind for event in tail] == [
            "action-cached",
            "finished",
        ]

    def test_replaying_the_future_is_stale(self):
        with pytest.raises(Stale, match="beyond the stream"):
            healthy_stream().replay_from(99)

    def test_subscription_by_kind_filters(self):
        stream = healthy_stream()
        assert len(stream.of_kind("action-done")) == 1


class TestGrammar:
    def test_a_healthy_stream_passes_clean(self):
        assert healthy_stream().check_grammar() == []

    def test_a_missing_finish_is_named(self):
        stream = EventStream()
        stream.emit("started")
        stream.emit("action-running", "main.o")
        complaints = stream.check_grammar()
        assert "0 finished events; wanted 1" in complaints
        assert "main.o started but never ended" in complaints

    def test_events_outside_the_bracket_are_named(self):
        stream = EventStream()
        stream.emit("action-running", "early.o")
        stream.emit("started")
        stream.emit("action-done", "early.o")
        stream.emit("finished")
        complaints = stream.check_grammar()
        assert any("outside the bracket" in line for line in complaints)

    def test_double_starts_are_named(self):
        stream = EventStream()
        stream.emit("started")
        stream.emit("started")
        stream.emit("finished")
        assert "2 started events; wanted 1" in stream.check_grammar()
