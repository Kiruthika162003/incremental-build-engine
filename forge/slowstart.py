"""Slow start: the returning worker earns its load doubling by doubling.

A machine fresh from maintenance looks healthy to every probe
and still fails in the one way probes miss, under production
load, so handing it a full slate on its first tick bets forty
builds on an assumption. The ramp borrows TCP's oldest idea:
start with one action, double the allowance after every clean
round, and on the first failure halve the allowance and hold
it there for a penalty round, so a genuinely sick machine
converges to a trickle that hurts nobody while a healthy one
reaches full load in a handful of doublings. The ledger
records the ramp's shape, rounds to full load and failures
absorbed at reduced blast radius, because the alternative
worth comparing is always the same one: the machine that got
everything at once and took forty builds down with its first
bad fan bearing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class SlowStart:
    full_load: int
    allowance: int = 1
    penalty_rounds_left: int = 0
    rounds: int = 0
    failures_absorbed: int = 0
    history: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.full_load < 1:
            raise Invalid("full load must be at least one action")

    def round_result(self, clean: bool) -> str:
        self.rounds += 1
        self.history.append(self.allowance)
        if not clean:
            self.failures_absorbed += 1
            blast = self.allowance
            self.allowance = max(1, self.allowance // 2)
            self.penalty_rounds_left = 1
            return (
                f"round {self.rounds}: failure at allowance "
                f"{blast}; halved to {self.allowance} and held "
                "for a penalty round"
            )
        if self.penalty_rounds_left > 0:
            self.penalty_rounds_left -= 1
            return (
                f"round {self.rounds}: clean, allowance held "
                f"at {self.allowance} (penalty round)"
            )
        if self.allowance >= self.full_load:
            return (
                f"round {self.rounds}: at full load "
                f"({self.full_load})"
            )
        self.allowance = min(
            self.full_load, self.allowance * 2
        )
        return (
            f"round {self.rounds}: clean, allowance doubles "
            f"to {self.allowance}"
        )

    def ramp_report(self) -> str:
        if not self.history:
            raise Invalid("no rounds run")
        shape = " -> ".join(
            str(value) for value in self.history
        )
        at_full = self.allowance >= self.full_load
        line = (
            f"ramp {shape}; {self.failures_absorbed} "
            f"failure(s) absorbed at reduced blast radius"
        )
        if at_full:
            line += f"; full load in {self.rounds} round(s)"
        else:
            line += (
                f"; still at {self.allowance} of "
                f"{self.full_load}, which is the ramp doing "
                "its job on a machine not yet believed"
            )
        return line
