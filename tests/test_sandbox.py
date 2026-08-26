from __future__ import annotations

import pytest

from forge.actions import Action
from forge.errors import Hermetic
from forge.sandbox import SandboxMeter, run_sandboxed
from forge.workspace import Workspace


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("secret.h", "#define KEY 42")
    return tree


def clean_action() -> Action:
    def rule(view) -> None:
        view.write_text("main.o", f"obj({view.read_text('main.c')})")

    return Action(
        name="compile",
        command="cc",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def sneaky_action() -> Action:
    def rule(view) -> None:
        view.read_text("secret.h")
        view.write_text("main.o", "obj")

    return Action(
        name="compile",
        command="cc",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def half_action() -> Action:
    def rule(view) -> None:
        view.write_text("main.o", f"obj({view.read_text('main.c')})")

    return Action(
        name="compile",
        command="cc",
        reads=("main.c",),
        writes=("main.o", "main.d"),
        rule=rule,
    )


class TestTheView:
    def test_a_clean_action_promotes_its_outputs(self):
        tree = world()
        result = run_sandboxed(clean_action(), tree)
        assert result.outcome == "promoted"
        assert tree.read_text("main.o") == "obj(int main;)"

    def test_the_undeclared_read_fails_at_the_crime(self):
        with pytest.raises(Hermetic, match="never declared"):
            run_sandboxed(sneaky_action(), world())

    def test_the_refusal_leaves_the_real_tree_untouched(self):
        tree = world()
        with pytest.raises(Hermetic):
            run_sandboxed(sneaky_action(), tree)
        assert not tree.exists("main.o")

    def test_intermediate_files_are_legal_inside_the_box(self):
        def rule(view) -> None:
            view.write_text("tmp.i", view.read_text("main.c"))
            view.write_text("main.o", f"obj({view.read_text('tmp.i')})")

        action = Action(
            name="compile",
            command="cc",
            reads=("main.c",),
            writes=("main.o",),
            rule=rule,
        )
        tree = world()
        run_sandboxed(action, tree)
        assert tree.exists("main.o")
        assert not tree.exists("tmp.i")


class TestBrokenPromises:
    def test_half_written_output_promotes_nothing(self):
        tree = world()
        with pytest.raises(Hermetic, match="never wrote"):
            run_sandboxed(half_action(), tree)
        assert not tree.exists("main.o")
        assert not tree.exists("main.d")


class TestTheMeter:
    def test_the_receipt_prices_the_copies(self):
        meter = SandboxMeter()
        meter.run(clean_action(), world())
        with pytest.raises(Hermetic):
            meter.run(sneaky_action(), world())
        assert meter.receipt() == (
            "2 sandboxed runs, 1 refused, 9 bytes copied in"
        )
