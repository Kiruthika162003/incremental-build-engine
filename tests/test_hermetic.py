from __future__ import annotations

from forge.actions import Action
from forge.engine import Engine
from forge.hermetic import audit_build
from forge.workspace import Workspace


def clean_compile(source: str, out: str) -> Action:
    def rule(tree) -> None:
        tree.write_text(out, f"obj({tree.read_text(source)})")

    return Action(
        name=f"compile {source}",
        command="cc",
        reads=(source,),
        writes=(out,),
        rule=rule,
    )


def leaky_compile(source: str, sneak: str, out: str) -> Action:
    def rule(tree) -> None:
        tree.read_text(sneak)
        tree.write_text(out, f"obj({tree.read_text(source)})")

    return Action(
        name=f"compile {source}",
        command="cc",
        reads=(source,),
        writes=(out,),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("util.c", "int util;")
    tree.write_text("secret.h", "#define KEY 42")
    return tree


class TestBlessing:
    def test_a_clean_build_is_blessed(self):
        engine = Engine()
        engine.source("main.c")
        engine.rule(
            "main.o", clean_compile("main.c", "main.o"), needs=("main.c",)
        )
        report = audit_build(engine, "main.o", world())
        assert report.blessed()
        assert report.page() == "blessed: all 1 actions hermetic"

    def test_one_leak_refuses_the_whole_blessing(self):
        engine = Engine()
        engine.source("main.c")
        engine.source("util.c")
        engine.rule(
            "main.o",
            leaky_compile("main.c", "secret.h", "main.o"),
            needs=("main.c",),
        )
        engine.rule(
            "util.o", clean_compile("util.c", "util.o"), needs=("util.c",)
        )
        engine.rule(
            "app",
            clean_compile("main.o", "app"),
            needs=("main.o", "util.o"),
        )
        report = audit_build(engine, "app", world())
        assert not report.blessed()
        assert report.clean == 2

    def test_an_empty_audit_is_not_a_blessing(self):
        engine = Engine()
        engine.source("main.c")
        report = audit_build(engine, "main.c", world())
        assert not report.blessed()


class TestTheGapReport:
    def wired(self) -> Engine:
        engine = Engine()
        engine.source("main.c")
        engine.source("util.c")
        engine.rule(
            "main.o",
            leaky_compile("main.c", "secret.h", "main.o"),
            needs=("main.c",),
        )
        engine.rule(
            "util.o",
            leaky_compile("util.c", "secret.h", "util.o"),
            needs=("util.c",),
        )
        engine.rule(
            "app",
            clean_compile("main.o", "app"),
            needs=("main.o", "util.o"),
        )
        engine.rule(
            "installer", clean_compile("app", "installer"), needs=("app",)
        )
        return engine

    def test_leaks_sort_by_poison_spread(self):
        report = audit_build(self.wired(), "installer", world())
        assert [leak.action for leak in report.leaks] == [
            "main.o",
            "util.o",
        ]
        assert report.leaks[0].poisoned_downstream == 2

    def test_the_leak_line_names_the_paths(self):
        report = audit_build(self.wired(), "installer", world())
        assert report.leaks[0].line() == (
            "main.o: reads ['secret.h'] (poisons 2 downstream)"
        )

    def test_the_page_reads_not_blessed_first(self):
        page = audit_build(self.wired(), "installer", world()).page()
        assert page.startswith("NOT blessed: 2 of 4 actions leak")
