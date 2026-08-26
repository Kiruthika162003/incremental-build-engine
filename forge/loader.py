"""The loader: a BUILD file becomes a wired engine, commands become rules.

The parser knows the text and the engine knows the graph; the
loader is the treaty between them. Each stanza's command string is
resolved against a toolbox of command factories, so "cc" in a file
becomes the same rule object everywhere it appears and a command
nobody registered fails at load time with the toolbox's contents in
the message. Costs and needs travel from stanza to engine
unchanged, and sources become graph leaves the workspace must
provide. The loader is also where the file's honesty is enforced
one level deeper than parsing can see: a stanza whose reads name a
target that is neither a source nor another stanza's output is a
lie about the world, and it is refused with the stanza's line
number, because the error a person can act on is the one that
points at the text they wrote.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.actions import Action
from forge.buildfile import BuildFile, Stanza, parse
from forge.engine import Engine
from forge.errors import Invalid

CommandFactory = Callable[[Stanza], Action]


@dataclass
class Toolbox:
    factories: dict[str, CommandFactory] = field(default_factory=dict)

    def register(self, command: str, factory: CommandFactory) -> None:
        if command in self.factories:
            raise Invalid(f"command {command} is already registered")
        self.factories[command] = factory

    def resolve(self, stanza: Stanza) -> Action:
        head = stanza.command.split()[0]
        factory = self.factories.get(head)
        if factory is None:
            raise Invalid(
                f"line {stanza.line}: no tool named {head!r}; "
                f"the toolbox holds {sorted(self.factories)}"
            )
        return factory(stanza)


def standard_toolbox() -> Toolbox:
    """The demonstration tools: enough to build the examples."""
    box = Toolbox()

    def compile_factory(stanza: Stanza) -> Action:
        def rule(tree) -> None:
            parts = [tree.read_text(path) for path in stanza.reads]
            tree.write_text(
                stanza.writes[0], f"obj({'+'.join(parts)})"
            )

        return Action(
            name=stanza.name,
            command=stanza.command,
            reads=stanza.reads,
            writes=stanza.writes,
            rule=rule,
        )

    def link_factory(stanza: Stanza) -> Action:
        def rule(tree) -> None:
            parts = [tree.read_text(path) for path in stanza.reads]
            tree.write_text(
                stanza.writes[0], f"bin[{'+'.join(parts)}]"
            )

        return Action(
            name=stanza.name,
            command=stanza.command,
            reads=stanza.reads,
            writes=stanza.writes,
            rule=rule,
        )

    def archive_factory(stanza: Stanza) -> Action:
        def rule(tree) -> None:
            parts = [tree.read_text(path) for path in stanza.reads]
            tree.write_text(
                stanza.writes[0], f"ar({'|'.join(parts)})"
            )

        return Action(
            name=stanza.name,
            command=stanza.command,
            reads=stanza.reads,
            writes=stanza.writes,
            rule=rule,
        )

    box.register("cc", compile_factory)
    box.register("ld", link_factory)
    box.register("ar", archive_factory)
    return box


def load(text: str, toolbox: Toolbox | None = None) -> Engine:
    parsed: BuildFile = parse(text)
    box = toolbox or standard_toolbox()
    engine = Engine()
    produced: set[str] = set(parsed.sources)
    for stanza in parsed.stanzas.values():
        produced.update(stanza.writes)
    for stanza in parsed.stanzas.values():
        for path in stanza.reads:
            if path not in produced:
                raise Invalid(
                    f"line {stanza.line}: {stanza.name} reads "
                    f"{path}, which no source or rule provides"
                )
    for source in parsed.sources:
        engine.source(source)
    for stanza in parsed.stanzas.values():
        engine.rule(
            stanza.name,
            box.resolve(stanza),
            needs=stanza.needs,
            cost=stanza.cost,
        )
    return engine
