"""The environment contract: variables are inputs, or they are lies.

An action that reads PATH, HOME, or LANG without declaring them is
hermetic in the filesystem and leaky in the environment, and the
leak has the same shape as an undeclared file: the cache serves
yesterday's output the day the variable changes. The contract
makes environment explicit: an action declares the variables it
may see with pinned values, execution happens against exactly that
dictionary and nothing more, and the declared pairs fold into the
action key so a changed value is a changed key. The scrubber is
the migration tool: given the ambient environment a legacy action
ran under, it reports which variables actually influenced the
output by rerunning with each one dropped, because the alternative
migration strategy, declaring everything, pins the whole machine
into the key and the cache never hits again.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from forge.content import digest_text
from forge.errors import Hermetic, Invalid


@dataclass(frozen=True)
class EnvContract:
    declared: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, str]:
        return dict(self.declared)

    def key_fold(self) -> str:
        rows = "|".join(
            f"{name}={value}" for name, value in sorted(self.declared)
        )
        return digest_text(rows)


class ContractedEnv:
    """The only environment the rule may see."""

    def __init__(self, contract: EnvContract):
        self._values = contract.as_dict()
        self.reads: set[str] = set()

    def get(self, name: str) -> str:
        if name not in self._values:
            raise Hermetic(
                f"the rule read {name}, which its contract never "
                f"declared; declared are {sorted(self._values)}"
            )
        self.reads.add(name)
        return self._values[name]


def run_contracted(
    rule: Callable[[ContractedEnv], str],
    contract: EnvContract,
) -> tuple[str, list[str]]:
    """Returns (output, declared-but-unread variables)."""
    env = ContractedEnv(contract)
    output = rule(env)
    unread = sorted(set(contract.as_dict()) - env.reads)
    return output, unread


def influence_scan(
    rule: Callable[[dict], str],
    ambient: dict[str, str],
) -> list[str]:
    """Which ambient variables actually change the output."""
    if not ambient:
        raise Invalid("an empty environment influences nothing")
    baseline = rule(dict(ambient))
    influential = []
    for name in sorted(ambient):
        reduced = {
            key: value
            for key, value in ambient.items()
            if key != name
        }
        try:
            without = rule(reduced)
        except KeyError:
            influential.append(name)
            continue
        if without != baseline:
            influential.append(name)
    return influential


def migration_advice(
    rule: Callable[[dict], str],
    ambient: dict[str, str],
) -> str:
    influential = influence_scan(rule, ambient)
    ignored = sorted(set(ambient) - set(influential))
    return (
        f"declare {influential}; leave {ignored} out of the key, "
        f"they never influenced the output"
    )
