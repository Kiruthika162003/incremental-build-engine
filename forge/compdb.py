"""The compilation database: the IDE deserves the build's own truth.

Language servers reconstruct compile commands by guessing, and
their guesses drift from the build's reality one flag at a time
until go-to-definition lands in the wrong header. The database
export walks the graph and emits, for every compile-shaped rule,
the exact command, the source file, and the working directory the
build would use, in a stable order so the generated file diffs
only when the build changes. The staleness stamp is the honest
part: the database embeds the graph digest it was generated from,
the checker compares it against the live graph, and an IDE reading
a stale database gets told by tooling rather than by a subtly
wrong jump, because the failure mode of a stale database is not an
error message, it is a developer slowly losing trust in their
editor.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.actions import Action
from forge.content import digest_text
from forge.errors import Stale
from forge.graph import Graph


@dataclass(frozen=True)
class CompileEntry:
    file: str
    command: str
    directory: str

    def render(self) -> str:
        return (
            f'{{"file": "{self.file}", "command": "{self.command}", '
            f'"directory": "{self.directory}"}}'
        )


def graph_digest(graph: Graph, actions: dict[str, Action]) -> str:
    rows = "|".join(
        f"{name}:{actions[name].command}:{','.join(actions[name].reads)}"
        for name in sorted(actions)
        if name in graph.targets
    )
    return digest_text(rows)


def export(
    graph: Graph,
    actions: dict[str, Action],
    directory: str = "/workspace",
) -> str:
    entries = []
    for name in sorted(actions):
        action = actions[name]
        if not action.command.startswith("cc"):
            continue
        for source in action.reads:
            if source.endswith(".c"):
                entries.append(
                    CompileEntry(
                        file=source,
                        command=f"{action.command} {source}",
                        directory=directory,
                    )
                )
    body = ",\n  ".join(entry.render() for entry in entries)
    stamp = graph_digest(graph, actions)
    return (
        f'{{"graph_digest": "{stamp}",\n "entries": [\n  {body}\n ]}}'
    )


def check_freshness(
    database: str, graph: Graph, actions: dict[str, Action]
) -> None:
    live = graph_digest(graph, actions)
    if f'"graph_digest": "{live}"' not in database:
        raise Stale(
            "the compilation database was generated from an older "
            "graph; regenerate it before trusting a single jump"
        )
