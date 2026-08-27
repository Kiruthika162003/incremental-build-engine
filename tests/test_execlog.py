from __future__ import annotations

import pytest

from forge.actions import Action, execute
from forge.errors import Invalid
from forge.execlog import ExecutionLog, first_divergence, replay
from forge.workspace import Workspace


def compiler(flags: str = "-O2") -> Action:
    def rule(view) -> None:
        view.write_text("main.o", f"obj({view.read_text('main.c')})")

    return Action(
        name="compile",
        command=f"cc {flags}",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def logged_build(source: str, flags: str = "-O2") -> ExecutionLog:
    tree = Workspace()
    tree.write_text("main.c", source)
    action = compiler(flags)
    execute(action, tree)
    log = ExecutionLog()
    log.record(action, tree, duration=4)
    return log


class TestComparison:
    def test_identical_builds_have_no_divergence(self):
        ours = logged_build("int main;")
        theirs = logged_build("int main;")
        assert first_divergence(ours, theirs) is None

    def test_differing_inputs_are_named_by_path(self):
        ours = logged_build("int main;")
        theirs = logged_build("int main; // their edit")
        verdict = first_divergence(ours, theirs)
        assert verdict == "compile: inputs differ at ['main.c']"

    def test_a_drifted_command_is_separated_from_inputs(self):
        ours = logged_build("int main;")
        theirs = logged_build("int main;", flags="-O3")
        verdict = first_divergence(ours, theirs)
        assert verdict == (
            "compile: same inputs, different key; a command drifted"
        )

    def test_the_never_ran_is_weather_after_this(self):
        ours = logged_build("int main;")
        verdict = first_divergence(ours, ExecutionLog())
        assert "they never did" in verdict


class TestReplay:
    def test_a_faithful_replay_lands_byte_for_byte(self):
        log = logged_build("int main;")
        tree = Workspace()
        tree.write_text("main.c", "int main;")
        outcome = replay(log, {"compile": compiler()}, tree)
        assert outcome == "replayed 1 lines byte for byte"

    def test_the_mismatch_carries_the_log_coordinate(self):
        log = logged_build("int main;")
        tree = Workspace()
        tree.write_text("main.c", "int main; // drifted checkout")
        outcome = replay(log, {"compile": compiler()}, tree)
        assert outcome.startswith("MISMATCH at log line 1: compile")

    def test_an_unknown_action_is_refused_with_its_line(self):
        log = logged_build("int main;")
        with pytest.raises(Invalid, match="log line 1"):
            replay(log, {}, Workspace())
