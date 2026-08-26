"""Cross compilation: two platforms in one graph, and never confused.

A cross build runs tools on the host to make artifacts for the
target, and the classic disaster is an artifact crossing the line:
a target-arch object linked into a host tool, discovered at run
time on the wrong machine. Here every rule and artifact carries a
platform, host tools consume and produce host artifacts, target
rules consume target artifacts but may run host tools, and the
checker walks the graph refusing any edge that mixes platforms
outside the one legal shape: a generator rule whose executable is
host and whose output is target. The two-platform build doubles
exactly the rules that differ by platform and shares the rest,
and the platform report counts both, since the whole economy of
cross building is that the generator built once serves every
target architecture in the fleet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PLATFORMS = ("host", "target")


@dataclass(frozen=True)
class PlatformRule:
    name: str
    platform: str
    consumes: tuple[str, ...] = ()
    runs_tool: str | None = None

    def __post_init__(self) -> None:
        if self.platform not in PLATFORMS:
            raise Invalid(
                f"{self.name}: unknown platform {self.platform!r}"
            )


@dataclass
class CrossGraph:
    rules: dict[str, PlatformRule] = field(default_factory=dict)

    def declare(self, rule: PlatformRule) -> None:
        if rule.name in self.rules:
            raise Invalid(f"{rule.name} is already declared")
        self.rules[rule.name] = rule

    def platform_of(self, name: str) -> str:
        if name not in self.rules:
            raise Invalid(f"no rule named {name}")
        return self.rules[name].platform

    def check(self) -> list[str]:
        complaints = []
        for rule in self.rules.values():
            for consumed in rule.consumes:
                if consumed not in self.rules:
                    complaints.append(
                        f"{rule.name} consumes {consumed}, which "
                        f"nothing declares"
                    )
                    continue
                producer = self.rules[consumed]
                if producer.platform != rule.platform:
                    complaints.append(
                        f"{rule.name} ({rule.platform}) consumes "
                        f"{consumed} ({producer.platform}): an "
                        f"artifact crossed the line"
                    )
            if rule.runs_tool is not None:
                tool = self.rules.get(rule.runs_tool)
                if tool is None:
                    complaints.append(
                        f"{rule.name} runs {rule.runs_tool}, which "
                        f"nothing declares"
                    )
                elif tool.platform != "host":
                    complaints.append(
                        f"{rule.name} runs {rule.runs_tool} "
                        f"({tool.platform}): only host tools execute "
                        f"during a build"
                    )
        return complaints

    def shared_and_split(self) -> tuple[list[str], list[str]]:
        by_stem: dict[str, set[str]] = {}
        for rule in self.rules.values():
            stem = rule.name.removeprefix("host:").removeprefix(
                "target:"
            )
            by_stem.setdefault(stem, set()).add(rule.platform)
        split = sorted(
            stem
            for stem, platforms in by_stem.items()
            if len(platforms) == 2
        )
        shared = sorted(
            stem
            for stem, platforms in by_stem.items()
            if len(platforms) == 1
        )
        return shared, split

    def economy(self) -> str:
        shared, split = self.shared_and_split()
        return (
            f"{len(split)} stems doubled across platforms, "
            f"{len(shared)} built once"
        )
