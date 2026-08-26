from __future__ import annotations

import pytest

from forge.actions import Action
from forge.errors import Missing
from forge.overlay import Overlay
from forge.workspace import Workspace


def disk() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    return tree


def compile_action() -> Action:
    def rule(view) -> None:
        view.write_text("main.o", f"obj({view.read_text('main.c')})")

    return Action(
        name="compile",
        command="cc",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


class TestShadowing:
    def test_the_buffer_shadows_the_disk(self):
        overlay = Overlay(base=disk())
        overlay.open_buffer("main.c", "int main; // typing")
        assert overlay.read_text("main.c") == "int main; // typing"
        assert overlay.reads_from_buffer == 1

    def test_unshadowed_files_come_from_disk(self):
        overlay = Overlay(base=disk())
        assert overlay.read_text("main.c") == "int main;"
        assert overlay.reads_from_disk == 1

    def test_the_digest_moves_with_the_typing(self):
        overlay = Overlay(base=disk())
        before = overlay.digest_of("main.c")
        overlay.open_buffer("main.c", "int main; // typing")
        assert overlay.digest_of("main.c") != before

    def test_dropping_the_buffer_returns_to_disk(self):
        overlay = Overlay(base=disk())
        overlay.open_buffer("main.c", "int main; // typing")
        overlay.drop_buffer("main.c")
        assert overlay.read_text("main.c") == "int main;"

    def test_dropping_a_closed_buffer_is_refused(self):
        with pytest.raises(Missing):
            Overlay(base=disk()).drop_buffer("main.c")


class TestImaginaryOutputs:
    def test_builds_land_in_the_overlay_never_the_disk(self):
        base = disk()
        overlay = Overlay(base=base)
        overlay.open_buffer("main.c", "int main; // typing")
        compile_action().rule(overlay)
        assert overlay.read_text("main.o") == "obj(int main; // typing)"
        assert not base.exists("main.o")

    def test_the_action_key_moves_with_the_buffer(self):
        overlay = Overlay(base=disk())
        action = compile_action()
        saved_key = action.key(overlay)
        overlay.open_buffer("main.c", "int main; // typing")
        assert action.key(overlay) != saved_key

    def test_the_report_reads_the_shadow_world(self):
        overlay = Overlay(base=disk())
        overlay.open_buffer("main.c", "int main; // typing")
        compile_action().rule(overlay)
        assert overlay.shadow_report() == (
            "1 buffers shadowing, 1 imaginary outputs, "
            "1 buffer reads, 0 disk reads"
        )
