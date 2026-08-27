"""An edit week grades the two cutoffs against each other.

Ten edits to a core unit watched by four dependents: two saves
that changed nothing, five body rewrites, three signature
changes. File cutoff catches the empty saves and banks 10
compiles; the interface digest catches the body rewrites and
banks 20, twice as much, which is the audit's point: the cutoff
teams forget to build is the one that pays double. The three
signature changes ripple to all four watchers each, and the
drill checks they are paid in full, because a cutoff that also
swallowed real interface changes would not be an optimization
but a correctness bug with good press.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.symbolselect import (
    InterfaceSelector,
    SourceUnit,
    Symbol,
)

WATCHERS = ("app.py", "tool.py", "bench.py", "docs.py")


def _unit(body: str, signature: str) -> SourceUnit:
    return SourceUnit(
        path="core.py",
        body=body,
        symbols=(
            Symbol(
                name="parse", signature=signature, public=True
            ),
        ),
    )


def run() -> Finding:
    selector = InterfaceSelector()
    selector.admit(
        _unit("v0", "(text) -> Tree"), dependents=WATCHERS
    )
    week = [
        ("v0", "(text) -> Tree"),
        ("v1", "(text) -> Tree"),
        ("v2", "(text) -> Tree"),
        ("v2", "(text) -> Tree"),
        ("v3", "(text) -> Tree"),
        ("v4", "(text) -> Tree"),
        ("v4b", "(text, strict) -> Tree"),
        ("v5", "(text, strict) -> Tree"),
        ("v5b", "(text, strict, depth) -> Tree"),
        ("v6", "(text, strict, depth, log) -> Tree"),
    ]
    for body, signature in week:
        selector.edit(_unit(body, signature))
    numbers = {
        "file_saves": selector.file_saves,
        "interface_saves": selector.interface_saves,
        "ripples": selector.ripples,
        "ripple_compiles_paid": selector.ripples * len(WATCHERS),
        "interface_over_file": (
            selector.interface_saves / selector.file_saves
        ),
    }
    holds = (
        numbers["file_saves"] == 10
        and numbers["interface_saves"] == 20
        and numbers["ripples"] == 3
        and numbers["ripple_compiles_paid"] == 12
        and numbers["interface_over_file"] == 2.0
    )
    return Finding(
        audit="facedrill",
        claim=(
            "the forgotten cutoff pays double: 20 compiles saved "
            "by the interface digest against 10 by file identity, "
            "while all 12 ripple compiles are paid in full"
        ),
        numbers=numbers,
        holds=holds,
    )
