"""Transient failures: retry the weather, never the bug.

A build step fails for two unlike reasons wearing one exit code:
the network hiccuped, or the code is wrong. Retrying the first is
hygiene; retrying the second is burning compute to delay the
truth, so the policy splits on evidence. A failure whose message
matches the transient patterns earns a bounded number of retries;
anything else fails immediately and permanently, and a rule that
exhausts its retries is reclassified on the spot, because three
network hiccups in a row on one action is a fact about the action.
The infra ledger aggregates transient hits by pattern across the
whole build, which is how "the proxy is flapping" gets noticed as
a sentence instead of as forty unrelated red builds.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

TRANSIENT_PATTERNS = (
    "connection reset",
    "timeout",
    "temporarily unavailable",
)
MAX_RETRIES = 2


@dataclass
class Attempt:
    outcome: str
    message: str = ""


@dataclass
class RetryLedger:
    by_pattern: dict[str, int] = field(default_factory=dict)
    reclassified: list[str] = field(default_factory=list)
    permanent_failures: list[str] = field(default_factory=list)
    retries_spent: int = 0

    def weather_report(self) -> str:
        if not self.by_pattern:
            return "no transient failures; the weather was clear"
        rows = ", ".join(
            f"{pattern}: {count}"
            for pattern, count in sorted(
                self.by_pattern.items(), key=lambda row: -row[1]
            )
        )
        return f"transient weather: {rows}"


def classify(message: str) -> str:
    lowered = message.lower()
    for pattern in TRANSIENT_PATTERNS:
        if pattern in lowered:
            return pattern
    return "permanent"


def run_with_retries(
    name: str,
    attempt: Callable[[], Attempt],
    ledger: RetryLedger,
    max_retries: int = MAX_RETRIES,
) -> str:
    if max_retries < 0:
        raise Invalid("retries cannot be negative")
    tries = 0
    while True:
        result = attempt()
        if result.outcome == "ok":
            return f"{name}: ok after {tries} retries"
        kind = classify(result.message)
        if kind == "permanent":
            ledger.permanent_failures.append(name)
            return f"{name}: failed permanently ({result.message})"
        ledger.by_pattern[kind] = ledger.by_pattern.get(kind, 0) + 1
        if tries >= max_retries:
            ledger.reclassified.append(name)
            return (
                f"{name}: reclassified as broken after "
                f"{tries + 1} transient failures in a row"
            )
        tries += 1
        ledger.retries_spent += 1


def flaky_infrastructure(ledger: RetryLedger, threshold: int = 3) -> str | None:
    for pattern, count in sorted(ledger.by_pattern.items()):
        if count >= threshold:
            return (
                f"the infrastructure is flapping: {pattern} hit "
                f"{count} times across the build"
            )
    return None
