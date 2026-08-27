"""Co-failure history: the tests that break with this file, per the record.

Graph-based test selection knows what depends on what; history
knows what actually breaks together, and the two disagree in
both directions. The ledger records, for every failing run,
which files were edited and which tests went red, and builds
the conditional record: for a given file, the tests that have
failed in its company and how often. Selection by history then
picks the tests whose co-failure count clears a floor, and the
honest column is recall measured against the record itself:
when this file was edited and something failed, how often would
the history-selected set have caught it. History is not causality
and says so, a test that fails with every edit is a flake, not
an oracle, and the report flags tests whose co-failure spreads
evenly across every file as suspects for the flake bench rather
than evidence of coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

FLOOR = 2
FLAKE_SPREAD = 3


@dataclass
class CoFailLedger:
    runs: list[tuple[frozenset[str], frozenset[str]]] = field(
        default_factory=list
    )

    def record_run(
        self,
        edited: tuple[str, ...],
        failed_tests: tuple[str, ...],
    ) -> None:
        if not edited:
            raise Invalid(
                "a run with no edits cannot teach co-failure"
            )
        self.runs.append(
            (frozenset(edited), frozenset(failed_tests))
        )

    def cofailures(self, path: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for edited, failed in self.runs:
            if path not in edited:
                continue
            for test in failed:
                counts[test] = counts.get(test, 0) + 1
        return counts

    def select(self, path: str) -> list[str]:
        return sorted(
            test
            for test, count in self.cofailures(path).items()
            if count >= FLOOR
        )

    def recall(self, path: str) -> str:
        chosen = set(self.select(path))
        relevant = 0
        caught = 0
        for edited, failed in self.runs:
            if path not in edited or not failed:
                continue
            relevant += 1
            if failed & chosen:
                caught += 1
        if relevant == 0:
            raise Invalid(
                f"{path} has no failing history to score against"
            )
        return (
            f"{path}: history selects {len(chosen)} test(s), "
            f"catching {caught} of {relevant} failing run(s) "
            f"({100 * caught // relevant}% recall on the record)"
        )

    def flake_suspects(self) -> list[str]:
        spread: dict[str, set[str]] = {}
        for edited, failed in self.runs:
            for test in failed:
                spread.setdefault(test, set()).update(edited)
        return sorted(
            f"{test}: fails alongside {len(files)} different "
            "file(s); that is a flake profile, not coupling"
            for test, files in spread.items()
            if len(files) >= FLAKE_SPREAD
        )
