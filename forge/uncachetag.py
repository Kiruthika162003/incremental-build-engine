"""Uncacheable by declaration: some rules must run, and must say so.

A rule that fetches the current exchange rates or talks to a
license server is not deterministic and never will be, and the
honest move is declaring it rather than letting the flakiness
detector convict it later. A no-cache tag exempts the rule from
caching entirely: it runs every build, its outputs still flow
downstream by content, and the taint stops exactly there, because
a downstream rule that sees identical bytes from an uncacheable
parent still deserves its hit. The budget is the governance half:
uncacheable ticks per build are capped, every tagged rule must
carry a reason string a human wrote, and the report lists them
with their costs, since an exemption list nobody reviews grows
until the cache is a decoration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.cache import ActionCache
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass(frozen=True)
class NoCacheTag:
    rule: str
    reason: str
    cost: int

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise Invalid(
                f"{self.rule}: an exemption without a reason is a "
                f"cache leak with paperwork"
            )


@dataclass
class ExemptionLedger:
    budget_ticks: int
    tags: dict[str, NoCacheTag] = field(default_factory=dict)
    forced_runs: int = 0

    def declare(self, tag: NoCacheTag) -> None:
        if tag.rule in self.tags:
            raise Invalid(f"{tag.rule} is already exempt")
        spent = self.spent_ticks() + tag.cost
        if spent > self.budget_ticks:
            raise Invalid(
                f"exempting {tag.rule} needs {spent} ticks against a "
                f"budget of {self.budget_ticks}; the cache is becoming "
                f"a decoration"
            )
        self.tags[tag.rule] = tag

    def spent_ticks(self) -> int:
        return sum(tag.cost for tag in self.tags.values())

    def is_exempt(self, rule: str) -> bool:
        return rule in self.tags

    def run(
        self,
        action: Action,
        cache: ActionCache,
        tree: Workspace,
    ) -> str:
        if not self.is_exempt(action.name):
            outcome, _ = cache.run(action, tree)
            return outcome
        execute(action, tree)
        self.forced_runs += 1
        return "forced"

    def review_page(self) -> str:
        if not self.tags:
            return "no exemptions; every rule answers to the cache"
        lines = [
            f"{tag.rule}: {tag.cost} ticks every build ({tag.reason})"
            for tag in sorted(
                self.tags.values(), key=lambda tag: -tag.cost
            )
        ]
        lines.append(
            f"{self.spent_ticks()} of {self.budget_ticks} exemption "
            f"ticks spent, {self.forced_runs} forced runs so far"
        )
        return "\n".join(lines)
