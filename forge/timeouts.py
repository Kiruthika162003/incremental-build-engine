"""Action deadlines: hung is a diagnosis, and slow is not a crime.

A wedged compiler holds its worker forever, and a fixed global
timeout kills the legitimate half-hour link at minute ten. The
deadline is personal: each action's allowance derives from its
own recorded p99 times a patience factor, so the chronically slow
rule earns a long leash and the normally-quick rule that suddenly
hangs is caught in minutes. A kill is a verdict with evidence,
the allowance, the history it came from, and the overrun, and
kills feed back into nothing, deliberately: a hung run must not
poison the duration history that sets future allowances, because
one wedge would otherwise teach the deadline to tolerate wedges.
The waiver list exists for the honest exceptions, actions whose
runtime is data-dependent and unbounded, each waiver carrying a
reason, and the report separates kills from waivers from clean
finishes so the fleet's patience is a number someone chose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PATIENCE_FACTOR = 3.0
MINIMUM_ALLOWANCE = 10


@dataclass
class DeadlineKeeper:
    p99_history: dict[str, int] = field(default_factory=dict)
    waivers: dict[str, str] = field(default_factory=dict)
    kills: list[str] = field(default_factory=list)
    clean_finishes: int = 0
    waived_runs: int = 0

    def learn_p99(self, action: str, p99: int) -> None:
        if p99 <= 0:
            raise Invalid("a p99 must be positive")
        self.p99_history[action] = p99

    def waive(self, action: str, reason: str) -> None:
        if not reason.strip():
            raise Invalid(
                f"{action}: a waiver without a reason is a timeout "
                f"nobody chose"
            )
        self.waivers[action] = reason

    def allowance(self, action: str) -> int | None:
        if action in self.waivers:
            return None
        p99 = self.p99_history.get(action)
        if p99 is None:
            return None
        return max(
            MINIMUM_ALLOWANCE, int(p99 * PATIENCE_FACTOR)
        )

    def observe_run(self, action: str, duration: int) -> str:
        held = self.allowance(action)
        if held is None:
            if action in self.waivers:
                self.waived_runs += 1
                return (
                    f"{action} ran {duration} under waiver "
                    f"({self.waivers[action]})"
                )
            self.clean_finishes += 1
            return f"{action} ran {duration}; no history yet, watched"
        if duration > held:
            p99 = self.p99_history[action]
            verdict = (
                f"KILLED {action} at {held}: p99 {p99} times "
                f"{PATIENCE_FACTOR} patience, overran by "
                f"{duration - held}"
            )
            self.kills.append(verdict)
            return verdict
        self.clean_finishes += 1
        return f"{action} finished at {duration} inside {held}"

    def patience_report(self) -> str:
        return (
            f"{self.clean_finishes} clean, {len(self.kills)} killed, "
            f"{self.waived_runs} waived across "
            f"{len(self.waivers)} standing waivers"
        )
