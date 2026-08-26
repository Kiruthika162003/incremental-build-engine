"""Configuration variants: debug and release share a graph, not a cache key.

The same sources build under many flag sets, and two mistakes
bracket the design space: keying the cache without the config
serves debug objects to release links, and cloning the whole graph
per config forgets that some rules do not care. The variant layer
threads the config into the command identity of exactly the rules
whose factories declare they vary, so a compile keyed with -g and
-O2 stores two entries while a config-blind asset copy stores one
shared entry both variants hit. The sharing report measures the
split: how many entries the cache holds per config, how many are
shared across all of them, and what the clone-everything design
would have stored instead, which is the number that justifies the
declaration burden on rule authors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.cache import ActionCache
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass(frozen=True)
class Variant:
    name: str
    flags: str


@dataclass
class VariantRule:
    base: Action
    varies: bool

    def for_variant(self, variant: Variant) -> Action:
        if not self.varies:
            return self.base
        return Action(
            name=self.base.name,
            command=f"{self.base.command} {variant.flags}",
            reads=self.base.reads,
            writes=self.base.writes,
            rule=self.base.rule,
        )


@dataclass
class VariantBuilder:
    cache: ActionCache = field(default_factory=ActionCache)
    rules: dict[str, VariantRule] = field(default_factory=dict)
    runs_by_variant: dict[str, int] = field(default_factory=dict)

    def declare(self, name: str, action: Action, varies: bool) -> None:
        if name in self.rules:
            raise Invalid(f"{name} is already declared")
        self.rules[name] = VariantRule(base=action, varies=varies)

    def build(self, variant: Variant, tree: Workspace) -> list[str]:
        ran = []
        for name, rule in self.rules.items():
            action = rule.for_variant(variant)
            outcome, _ = self.cache.run(action, tree)
            if outcome == "miss":
                ran.append(name)
                self.runs_by_variant[variant.name] = (
                    self.runs_by_variant.get(variant.name, 0) + 1
                )
        return ran

    def sharing_report(self, variants: list[Variant]) -> str:
        varying = sum(1 for rule in self.rules.values() if rule.varies)
        shared = len(self.rules) - varying
        held = len(self.cache.entries)
        cloned_world = len(self.rules) * len(variants)
        return (
            f"{held} entries held for {len(variants)} variants; "
            f"{shared} rules shared, {varying} varied; "
            f"clone-everything would hold {cloned_world}"
        )
