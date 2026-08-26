from __future__ import annotations

import pytest

from forge.actions import Action, execute
from forge.errors import Invalid
from forge.workspace import Workspace


def compile_rule(tree) -> None:
    source = tree.read_text("main.c")
    tree.write_text("main.o", f"obj({source})")


def compile_action() -> Action:
    return Action(
        name="compile",
        command="cc -O2",
        reads=("main.c",),
        writes=("main.o",),
        rule=compile_rule,
    )


def seeded() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("extra.h", "#define X 1")
    return tree


class TestContracts:
    def test_outputless_actions_are_refused(self):
        with pytest.raises(Invalid, match="costume"):
            Action(
                name="noop",
                command="true",
                reads=(),
                writes=(),
                rule=lambda _tree: None,
            )

    def test_in_place_mutation_is_refused(self):
        with pytest.raises(Invalid, match="in-place"):
            Action(
                name="patch",
                command="sed -i",
                reads=("f.txt",),
                writes=("f.txt",),
                rule=lambda _tree: None,
            )


class TestKeys:
    def test_same_world_same_key(self):
        tree = seeded()
        assert compile_action().key(tree) == compile_action().key(tree)

    def test_changed_input_changes_the_key(self):
        tree = seeded()
        before = compile_action().key(tree)
        tree.write_text("main.c", "int main; // v2")
        assert compile_action().key(tree) != before

    def test_a_different_compiler_is_a_different_build(self):
        tree = seeded()
        gcc = compile_action()
        clang = Action(
            name="compile",
            command="clang -O2",
            reads=("main.c",),
            writes=("main.o",),
            rule=compile_rule,
        )
        assert gcc.key(tree) != clang.key(tree)

    def test_undeclared_files_do_not_move_the_key(self):
        tree = seeded()
        before = compile_action().key(tree)
        tree.write_text("extra.h", "#define X 2")
        assert compile_action().key(tree) == before


class TestExecution:
    def test_the_rule_runs_and_the_output_lands(self):
        tree = seeded()
        execute(compile_action(), tree)
        assert tree.read_text("main.o") == "obj(int main;)"

    def test_every_touch_is_observed(self):
        tree = seeded()
        seen = execute(compile_action(), tree)
        assert seen.read == {"main.c"}
        assert seen.wrote == {"main.o"}

    def test_a_sneaky_read_is_measured_not_trusted(self):
        def sneaky(tree) -> None:
            tree.read_text("extra.h")
            compile_rule(tree)

        action = Action(
            name="compile",
            command="cc -O2",
            reads=("main.c",),
            writes=("main.o",),
            rule=sneaky,
        )
        tree = seeded()
        seen = execute(action, tree)
        assert seen.undeclared_reads(action) == ["extra.h"]

    def test_a_sneaky_write_is_measured_too(self):
        def messy(tree) -> None:
            compile_rule(tree)
            tree.write_text("stray.tmp", "oops")

        action = Action(
            name="compile",
            command="cc -O2",
            reads=("main.c",),
            writes=("main.o",),
            rule=messy,
        )
        seen = execute(action, seeded())
        assert seen.undeclared_writes(action) == ["stray.tmp"]

    def test_a_broken_promise_is_named(self):
        def lazy(tree) -> None:
            tree.read_text("main.c")
            tree.write_text("main.o", "obj")

        action = Action(
            name="compile",
            command="cc -O2",
            reads=("main.c",),
            writes=("main.o", "main.d"),
            rule=lazy,
        )
        seen = execute(action, seeded())
        assert seen.promised_but_silent(action) == ["main.d"]
