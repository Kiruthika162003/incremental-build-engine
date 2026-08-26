from __future__ import annotations

import pytest

from forge.actions import Action
from forge.engine import Engine
from forge.errors import Invalid, Missing
from forge.workspace import Workspace


def compiler(source: str, out: str, runs: list[str]) -> Action:
    def rule(tree) -> None:
        runs.append(out)
        tree.write_text(out, f"obj({tree.read_text(source)})")

    return Action(
        name=f"compile {source}",
        command="cc -O2",
        reads=(source,),
        writes=(out,),
        rule=rule,
    )


def linker(objects: tuple[str, ...], out: str, runs: list[str]) -> Action:
    def rule(tree) -> None:
        runs.append(out)
        parts = "+".join(tree.read_text(obj) for obj in objects)
        tree.write_text(out, f"bin[{parts}]")

    return Action(
        name=f"link {out}",
        command="ld",
        reads=objects,
        writes=(out,),
        rule=rule,
    )


def project() -> tuple[Engine, Workspace, list[str]]:
    runs: list[str] = []
    engine = Engine()
    engine.source("main.c")
    engine.source("lib.c")
    engine.rule(
        "main.o", compiler("main.c", "main.o", runs), needs=("main.c",)
    )
    engine.rule(
        "lib.o", compiler("lib.c", "lib.o", runs), needs=("lib.c",)
    )
    engine.rule(
        "app",
        linker(("main.o", "lib.o"), "app", runs),
        needs=("main.o", "lib.o"),
        cost=5,
    )
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("lib.c", "int lib;")
    return engine, tree, runs


class TestColdBuilds:
    def test_the_cold_build_runs_everything(self):
        engine, tree, _ = project()
        report = engine.build("app", tree)
        assert report.ran == ["lib.o", "main.o", "app"]
        assert tree.read_text("app") == "bin[obj(int main;)+obj(int lib;)]"

    def test_the_second_build_is_all_hits(self):
        engine, tree, runs = project()
        engine.build("app", tree)
        report = engine.build("app", tree)
        assert report.ran == []
        assert report.hits == ["lib.o", "main.o", "app"]
        assert runs == ["lib.o", "main.o", "app"]

    def test_missing_sources_are_named(self):
        engine, tree, _ = project()
        tree.delete("lib.c")
        with pytest.raises(Missing, match=r"lib\.c"):
            engine.build("app", tree)

    def test_double_rules_are_refused(self):
        engine, _, runs = project()
        with pytest.raises(Invalid):
            engine.rule(
                "app", compiler("x", "y", runs), needs=()
            )


class TestIncrementality:
    def test_an_edit_rebuilds_only_its_cone(self):
        engine, tree, _ = project()
        engine.build("app", tree)
        tree.write_text("lib.c", "int lib; // v2")
        report = engine.build("app", tree)
        assert report.ran == ["lib.o", "app"]
        assert report.hits == ["main.o"]

    def test_early_cutoff_stops_the_rebuild_at_identical_bytes(self):
        engine, tree, runs = project()
        first = engine.build("app", tree)
        tree.write_text("lib.c", "int lib; // comment only")

        def same_bytes_rule(inner) -> None:
            runs.append("lib.o")
            inner.read_text("lib.c")
            inner.write_text("lib.o", "obj(int lib;)")

        engine.actions["lib.o"] = Action(
            name="compile lib.c",
            command="cc -O2",
            reads=("lib.c",),
            writes=("lib.o",),
            rule=same_bytes_rule,
        )
        second = engine.build("app", tree)
        assert second.ran == ["lib.o"]
        assert "app" in second.hits
        assert engine.cutoff_count(first, second) >= 1

    def test_the_report_line_reads_the_build(self):
        engine, tree, _ = project()
        report = engine.build("app", tree)
        assert report.line() == "app: 5 visited, 3 ran, 0 from cache"
