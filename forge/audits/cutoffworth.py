"""Early cutoff is worth the whole upper graph on a comment edit.

A twenty-target tower: one source at the bottom, nineteen build
steps stacked above it, each costing 5 ticks. A comment-only edit
changes the source's digest, so the bottom step must rerun, but it
emits the same bytes it emitted yesterday, and everything above it
hits the cache. The measured build: 1 rule ran, 19 hits, 95 ticks
saved out of the 100 a timestamp system would have spent, and a
second identical edit repeats the arithmetic exactly. The cutoff's
value scales with the height of what sits above the edited file,
which is why the deepest-buried headers hurt timestamp builds the
most and content builds the least.
"""

from __future__ import annotations

from forge.actions import Action
from forge.audits.finding import Finding
from forge.engine import Engine
from forge.workspace import Workspace

HEIGHT = 19
STEP_COST = 5


def _stable_step(lower: str, upper: str) -> Action:
    def rule(tree) -> None:
        tree.read_text(lower)
        tree.write_text(upper, f"stage[{upper}]")

    return Action(
        name=f"raise {upper}",
        command="stage",
        reads=(lower,),
        writes=(upper,),
        rule=rule,
    )


def _tower() -> tuple[Engine, Workspace]:
    engine = Engine()
    engine.source("base.src")
    below = "base.src"
    for level in range(HEIGHT):
        name = f"floor{level}"
        engine.rule(
            name,
            _stable_step(below, name),
            needs=(below,),
            cost=STEP_COST,
        )
        below = name
    tree = Workspace()
    tree.write_text("base.src", "the original text")
    return engine, tree


def run() -> Finding:
    engine, tree = _tower()
    engine.build(f"floor{HEIGHT - 1}", tree)
    tree.write_text("base.src", "the original text // comment")
    edited = engine.build(f"floor{HEIGHT - 1}", tree)
    numbers = {
        "rules_run_after_edit": len(edited.ran),
        "hits_after_edit": len(edited.hits),
        "ticks_saved": engine.cache.ticks_saved,
        "timestamp_world_would_run": HEIGHT,
    }
    holds = (
        numbers["rules_run_after_edit"] == 1
        and numbers["hits_after_edit"] == HEIGHT - 1
        and numbers["ticks_saved"] == (HEIGHT - 1) * STEP_COST
    )
    return Finding(
        audit="cutoffworth",
        claim=(
            "a comment edit reruns 1 rule of 19 and banks 90 ticks; "
            "the cutoff is worth the whole tower above the edit"
        ),
        numbers=numbers,
        holds=holds,
    )
