from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.retries import (
    Attempt,
    RetryLedger,
    classify,
    flaky_infrastructure,
    run_with_retries,
)


def flaky_then_ok(failures: int):
    remaining = [failures]

    def attempt() -> Attempt:
        if remaining[0] > 0:
            remaining[0] -= 1
            return Attempt(outcome="fail", message="Connection reset by peer")
        return Attempt(outcome="ok")

    return attempt


class TestClassification:
    def test_the_weather_is_recognised(self):
        assert classify("Connection reset by peer") == "connection reset"
        assert classify("read TIMEOUT after 30s") == "timeout"

    def test_everything_else_is_permanent(self):
        assert classify("syntax error on line 4") == "permanent"


class TestRetrying:
    def test_one_hiccup_is_absorbed(self):
        ledger = RetryLedger()
        line = run_with_retries("fetch", flaky_then_ok(1), ledger)
        assert line == "fetch: ok after 1 retries"
        assert ledger.retries_spent == 1

    def test_a_permanent_failure_never_retries(self):
        ledger = RetryLedger()

        def attempt() -> Attempt:
            return Attempt(outcome="fail", message="syntax error")

        line = run_with_retries("compile", attempt, ledger)
        assert line == "compile: failed permanently (syntax error)"
        assert ledger.retries_spent == 0
        assert ledger.permanent_failures == ["compile"]

    def test_exhausted_retries_reclassify_the_action(self):
        ledger = RetryLedger()
        line = run_with_retries("fetch", flaky_then_ok(9), ledger)
        assert line == (
            "fetch: reclassified as broken after 3 transient "
            "failures in a row"
        )
        assert ledger.reclassified == ["fetch"]

    def test_negative_retries_are_refused(self):
        with pytest.raises(Invalid):
            run_with_retries(
                "x", flaky_then_ok(0), RetryLedger(), max_retries=-1
            )


class TestTheWeather:
    def test_the_flap_is_a_sentence_not_forty_red_builds(self):
        ledger = RetryLedger()
        for name in ("a", "b", "c"):
            run_with_retries(name, flaky_then_ok(1), ledger)
        warning = flaky_infrastructure(ledger, threshold=3)
        assert warning == (
            "the infrastructure is flapping: connection reset hit "
            "3 times across the build"
        )

    def test_scattered_hiccups_stay_quiet(self):
        ledger = RetryLedger()
        run_with_retries("a", flaky_then_ok(1), ledger)
        assert flaky_infrastructure(ledger, threshold=3) is None

    def test_the_report_reads_by_frequency(self):
        ledger = RetryLedger()
        run_with_retries("a", flaky_then_ok(2), ledger)
        assert ledger.weather_report() == (
            "transient weather: connection reset: 2"
        )
        assert RetryLedger().weather_report() == (
            "no transient failures; the weather was clear"
        )
