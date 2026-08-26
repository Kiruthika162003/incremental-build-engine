"""The query language: one line of text, one graph question, one answer.

Tools and people both ask the graph questions, and a Python API
serves only one of them. The language is five verbs with a strict
shape: deps(target), rdeps(target), somepath(a, b), allpaths(a, b),
and count(expression) wrapping any of the others. Parsing is
deliberately humourless: unknown verbs list the knowns, arity
mismatches say what was expected, and an unknown target is the
graph's own Missing error passed through untouched, because the
query layer inventing its own not-found dialect would give the
same mistake two names. Output is text with one item per line
since the consumers are shells and diffs, and a count() answer is
just the number, which makes the language composable with every
tool that ever read a stream.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph
from forge.query import Query

VERBS = ("deps", "rdeps", "somepath", "allpaths", "count")


@dataclass
class QueryRunner:
    graph: Graph

    def _parse(self, text: str) -> tuple[str, list[str]]:
        text = text.strip()
        if "(" not in text or not text.endswith(")"):
            raise Invalid(
                f"a query looks like verb(args); got {text!r}"
            )
        verb, _, rest = text.partition("(")
        verb = verb.strip()
        if verb not in VERBS:
            raise Invalid(
                f"unknown verb {verb!r}; the language has {VERBS}"
            )
        inner = rest[:-1].strip()
        arguments = [
            part.strip() for part in inner.split(",") if part.strip()
        ]
        return verb, arguments

    def _need_arity(
        self, verb: str, arguments: list[str], wanted: int
    ) -> None:
        if len(arguments) != wanted:
            raise Invalid(
                f"{verb} takes {wanted} argument"
                f"{'s' if wanted != 1 else ''}; got {len(arguments)}"
            )

    def run(self, text: str) -> str:
        verb, arguments = self._parse(text)
        query = Query(graph=self.graph)
        if verb == "count":
            self._need_arity(verb, [text], 1)
            inner = text.strip()[len("count(") : -1]
            answer = self.run(inner)
            if not answer:
                return "0"
            return str(len(answer.splitlines()))
        if verb == "deps":
            self._need_arity(verb, arguments, 1)
            return "\n".join(query.deps(arguments[0]))
        if verb == "rdeps":
            self._need_arity(verb, arguments, 1)
            return "\n".join(query.rdeps(arguments[0]))
        if verb == "somepath":
            self._need_arity(verb, arguments, 2)
            path = query.somepath(arguments[0], arguments[1])
            return "\n".join(path) if path else ""
        self._need_arity(verb, arguments, 2)
        return str(query.allpaths(arguments[0], arguments[1]))
