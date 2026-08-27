"""Spawn strategy: observe, sandbox, or batch, chosen by evidence.

The engine has three ways to run an action and each buys a
different thing: observation is cheapest and catches leaks after
the fact, the sandbox prevents leaks by construction but pays a
copy-in, and batching amortises spawn floors for tiny same-tool
fleets. The chooser is a decision table, not a vibe: a rule with
a clean track record runs observed, a rule that has ever leaked
runs sandboxed until it earns parole with consecutive clean runs,
and cheap rules with same-tool siblings in the same wave batch.
Every choice is recorded with its reason, and the strategy mix
report shows the fleet drifting toward observation as the
codebase's hygiene improves, which is the intended equilibrium:
the sandbox is a hospital, not a home.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PAROLE_AFTER = 3
BATCH_COST_CEILING = 2


@dataclass
class RuleRecord:
    leaks: int = 0
    clean_streak: int = 0


@dataclass
class StrategyChooser:
    records: dict[str, RuleRecord] = field(default_factory=dict)
    choices: list[tuple[str, str, str]] = field(default_factory=list)

    def _record(self, rule: str) -> RuleRecord:
        return self.records.setdefault(rule, RuleRecord())

    def observed_leak(self, rule: str) -> None:
        record = self._record(rule)
        record.leaks += 1
        record.clean_streak = 0

    def observed_clean(self, rule: str) -> None:
        self._record(rule).clean_streak += 1

    def choose(
        self,
        rule: str,
        cost: int,
        same_tool_siblings: int,
    ) -> str:
        if cost < 0:
            raise Invalid("cost cannot be negative")
        record = self._record(rule)
        if record.leaks > 0 and record.clean_streak < PAROLE_AFTER:
            choice, reason = "sandbox", (
                f"leaked {record.leaks} time(s); "
                f"{PAROLE_AFTER - record.clean_streak} clean runs "
                f"from parole"
            )
        elif (
            cost <= BATCH_COST_CEILING and same_tool_siblings >= 2
        ):
            choice, reason = "batch", (
                f"cheap ({cost}) with {same_tool_siblings} same-tool "
                f"siblings"
            )
        else:
            choice, reason = "observe", "clean record; cheapest wins"
        self.choices.append((rule, choice, reason))
        return choice

    def mix_report(self) -> str:
        if not self.choices:
            raise Invalid("nothing chosen yet")
        counts: dict[str, int] = {}
        for _, choice, _ in self.choices:
            counts[choice] = counts.get(choice, 0) + 1
        total = len(self.choices)
        parts = ", ".join(
            f"{choice} {counts.get(choice, 0) / total:.0%}"
            for choice in ("observe", "sandbox", "batch")
        )
        hospitalised = counts.get("sandbox", 0)
        tail = (
            "; the sandbox is a hospital, not a home"
            if hospitalised
            else "; the ward is empty"
        )
        return parts + tail

    def explain(self, rule: str) -> str:
        for name, choice, reason in reversed(self.choices):
            if name == rule:
                return f"{rule}: {choice} ({reason})"
        raise Invalid(f"{rule} has never been chosen for")
