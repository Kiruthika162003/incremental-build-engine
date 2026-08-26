"""Version stamping: the one file that must change without changing anything.

Every release wants the commit hash and version baked into a file,
and doing it naively re-links the world on every commit because the
stamp file's digest moves even when nothing real did. The split is
the standard trick done honestly: the volatile stamp is quarantined
into its own tiny leaf, everything that does not embed it depends
only on stable inputs, and the final assembly that does embed it is
deliberately the cheapest rule in the graph. The measured claim is
the module's whole point: after a stamp-only change, the rebuild is
exactly the assembly rule, and the cutoff arithmetic proves the
quarantine held. A stamp that leaks into a compile step is caught
by the same arithmetic, because the rebuild count stops being one,
and that regression is precisely what the audit pins.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.actions import Action
from forge.engine import BuildReport, Engine
from forge.workspace import Workspace

STAMP_PATH = "version.stamp"


def stamp_action(out: str, embeds: tuple[str, ...]) -> Action:
    """The final assembly: everything stable plus the volatile stamp."""
    reads = (*embeds, STAMP_PATH)

    def rule(tree) -> None:
        parts = "+".join(tree.read_text(path) for path in embeds)
        stamp = tree.read_text(STAMP_PATH)
        tree.write_text(out, f"release[{parts}@{stamp}]")

    return Action(
        name=f"assemble {out}",
        command="assemble",
        reads=reads,
        writes=(out,),
        rule=rule,
    )


@dataclass
class StampedProject:
    engine: Engine
    goal: str

    def set_stamp(self, tree: Workspace, version: str) -> None:
        tree.write_text(STAMP_PATH, version)

    def restamp_and_build(
        self, tree: Workspace, version: str
    ) -> BuildReport:
        self.set_stamp(tree, version)
        return self.engine.build(self.goal, tree)

    def quarantine_holds(self, report: BuildReport) -> bool:
        """A stamp-only change may rebuild exactly the assembly."""
        return len(report.ran) == 1 and report.ran[0] == self.goal


def stamped_tower(units: int) -> tuple[StampedProject, Workspace]:
    engine = Engine()
    tree = Workspace()
    embeds = []
    for index in range(units):
        source = f"unit{index}.c"
        out = f"unit{index}.o"
        engine.source(source)
        tree.write_text(source, f"int unit{index};")

        def compile_rule(view, source=source, out=out) -> None:
            view.write_text(out, f"obj({view.read_text(source)})")

        engine.rule(
            out,
            Action(
                name=f"compile {source}",
                command="cc",
                reads=(source,),
                writes=(out,),
                rule=compile_rule,
            ),
            needs=(source,),
            cost=8,
        )
        embeds.append(out)
    engine.source(STAMP_PATH)
    engine.rule(
        "release",
        stamp_action("release", tuple(embeds)),
        needs=(*embeds, STAMP_PATH),
        cost=1,
    )
    project = StampedProject(engine=engine, goal="release")
    project.set_stamp(tree, "v0.0.0")
    return project, tree
