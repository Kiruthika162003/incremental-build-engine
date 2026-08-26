"""BUILD files: the graph as text, refused loudly when it lies.

A build description is a list of rule stanzas: a name, a command,
what it reads, what it writes, what it needs, and a cost. The
parser is strict where tools are usually forgiving, because every
silently tolerated typo becomes an afternoon of debugging someone
else's afternoon: unknown fields are errors, duplicate names are
errors, a rule that needs a target no stanza declares is an error
at load time rather than a surprise at build time, and every error
carries the line number it came from. The format is deliberately
line-based and boring, name = value with one rule per block,
since a build file is read a thousand times more often than it is
written and clever syntax bills the reader every time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

KNOWN_FIELDS = {"rule", "command", "reads", "writes", "needs", "cost"}


@dataclass
class Stanza:
    name: str
    command: str = ""
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    cost: int = 1
    line: int = 0


@dataclass
class BuildFile:
    stanzas: dict[str, Stanza] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def order(self) -> list[str]:
        return [*self.sources, *self.stanzas]


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(
        part.strip() for part in value.split(",") if part.strip()
    )


def parse(text: str) -> BuildFile:
    parsed = BuildFile()
    current: Stanza | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise Invalid(f"line {number}: expected field = value")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "source":
            if current is not None:
                raise Invalid(
                    f"line {number}: source lines belong before rules"
                )
            if value in parsed.sources:
                raise Invalid(f"line {number}: source {value} repeats")
            parsed.sources.append(value)
            continue
        if key not in KNOWN_FIELDS:
            raise Invalid(
                f"line {number}: unknown field {key!r}; "
                f"knowns are {sorted(KNOWN_FIELDS | {'source'})}"
            )
        if key == "rule":
            if not value:
                raise Invalid(f"line {number}: a rule needs a name")
            if value in parsed.stanzas or value in parsed.sources:
                raise Invalid(f"line {number}: {value} declared twice")
            current = Stanza(name=value, line=number)
            parsed.stanzas[value] = current
            continue
        if current is None:
            raise Invalid(
                f"line {number}: {key} appears before any rule"
            )
        if key == "command":
            current.command = value
        elif key == "reads":
            current.reads = _split_list(value)
        elif key == "writes":
            current.writes = _split_list(value)
        elif key == "needs":
            current.needs = _split_list(value)
        elif key == "cost":
            if not value.isdigit():
                raise Invalid(
                    f"line {number}: cost must be a whole number"
                )
            current.cost = int(value)
    _check(parsed)
    return parsed


def _check(parsed: BuildFile) -> None:
    known = set(parsed.sources) | set(parsed.stanzas)
    for stanza in parsed.stanzas.values():
        if not stanza.writes:
            raise Invalid(
                f"line {stanza.line}: rule {stanza.name} writes nothing"
            )
        if not stanza.command:
            raise Invalid(
                f"line {stanza.line}: rule {stanza.name} has no command"
            )
        for need in stanza.needs:
            if need not in known:
                raise Invalid(
                    f"line {stanza.line}: {stanza.name} needs "
                    f"{need}, which nothing declares"
                )


def render(parsed: BuildFile) -> str:
    lines = [f"source = {source}" for source in parsed.sources]
    for stanza in parsed.stanzas.values():
        lines.append("")
        lines.append(f"rule = {stanza.name}")
        lines.append(f"command = {stanza.command}")
        if stanza.reads:
            lines.append(f"reads = {', '.join(stanza.reads)}")
        lines.append(f"writes = {', '.join(stanza.writes)}")
        if stanza.needs:
            lines.append(f"needs = {', '.join(stanza.needs)}")
        if stanza.cost != 1:
            lines.append(f"cost = {stanza.cost}")
    return "\n".join(lines)
