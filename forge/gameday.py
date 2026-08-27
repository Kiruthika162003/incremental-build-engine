"""Game day: break it on purpose, on a Tuesday, with a scorecard.

Every resilience mechanism in the platform is a claim, and the
game day is the audit of claims: kill a worker and the retry
should absorb it, poison a cache entry and the prover should
catch it, flood the queue and the breaker should trip. The
exercise declares its expectations before the first fault is
injected, because expectations written afterward are called
observations, and the scorecard grades each injected fault
against the mechanism that claimed to handle it: held, failed,
or the third and most instructive outcome, handled by the
wrong mechanism, the retry absorbing what the breaker should
have refused, which passes a naive drill while hiding a
misconfiguration. The closing rule is cultural and enforced:
a game day with a perfect score and no findings is rerun
harder, since the exercise exists to find the soft spot, and
finding nothing means the drill was soft, not the platform
hard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class GameDay:
    expectations: dict[str, str] = field(default_factory=dict)
    results: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )
    started: bool = False

    def expect(self, fault: str, mechanism: str) -> None:
        if self.started:
            raise Invalid(
                "expectations written after the first fault "
                "are called observations"
            )
        self.expectations[fault] = mechanism

    def inject(
        self, fault: str, handled_by: str | None
    ) -> str:
        if fault not in self.expectations:
            raise Invalid(
                f"{fault} was not declared; surprise faults "
                "belong in incidents, not exercises"
            )
        self.started = True
        expected = self.expectations[fault]
        if handled_by is None:
            self.results[fault] = ("failed", "nothing caught it")
            return f"{fault}: FAILED, nothing caught it"
        if handled_by == expected:
            self.results[fault] = ("held", expected)
            return f"{fault}: held by {expected} as claimed"
        self.results[fault] = (
            "wrong-mechanism",
            handled_by,
        )
        return (
            f"{fault}: absorbed by {handled_by} where "
            f"{expected} claimed it; passes a naive drill "
            "while hiding a misconfiguration"
        )

    def scorecard(self) -> str:
        if not self.results:
            raise Invalid("no faults injected; run the day")
        held = sum(
            1
            for outcome, _ in self.results.values()
            if outcome == "held"
        )
        failed = [
            fault
            for fault, (outcome, _) in self.results.items()
            if outcome == "failed"
        ]
        misrouted = [
            f"{fault} (by {who}, not "
            f"{self.expectations[fault]})"
            for fault, (outcome, who) in self.results.items()
            if outcome == "wrong-mechanism"
        ]
        lines = [
            f"{held} held, {len(failed)} failed, "
            f"{len(misrouted)} handled by the wrong mechanism"
        ]
        lines.extend(f"  failed: {fault}" for fault in failed)
        lines.extend(
            f"  misrouted: {entry}" for entry in misrouted
        )
        if held == len(self.results):
            lines.append(
                "perfect score: rerun harder, because finding "
                "nothing means the drill was soft, not the "
                "platform hard"
            )
        return "\n".join(lines)
