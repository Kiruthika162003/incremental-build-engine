from __future__ import annotations

import pytest

from forge.actions import Action
from forge.errors import Invalid
from forge.variants import Variant, VariantBuilder
from forge.workspace import Workspace

DEBUG = Variant(name="debug", flags="-g")
RELEASE = Variant(name="release", flags="-O2")


def compile_action(runs: list[int]) -> Action:
    def rule(tree) -> None:
        runs[0] += 1
        tree.write_text("main.o", f"obj({tree.read_text('main.c')})")

    return Action(
        name="compile",
        command="cc",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def asset_action(runs: list[int]) -> Action:
    def rule(tree) -> None:
        runs[0] += 1
        tree.write_text("logo.out", tree.read_text("logo.svg"))

    return Action(
        name="copy asset",
        command="cp",
        reads=("logo.svg",),
        writes=("logo.out",),
        rule=rule,
    )


def project(runs: list[int]) -> VariantBuilder:
    builder = VariantBuilder()
    builder.declare("main.o", compile_action(runs), varies=True)
    builder.declare("logo.out", asset_action(runs), varies=False)
    return builder


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("logo.svg", "<svg/>")
    return tree


class TestVarying:
    def test_each_variant_compiles_its_own_object(self):
        runs = [0]
        builder = project(runs)
        tree = world()
        assert builder.build(DEBUG, tree) == ["main.o", "logo.out"]
        assert builder.build(RELEASE, tree) == ["main.o"]
        assert runs == [3]

    def test_the_asset_is_shared_across_variants(self):
        runs = [0]
        builder = project(runs)
        tree = world()
        builder.build(DEBUG, tree)
        builder.build(RELEASE, tree)
        assert builder.runs_by_variant == {"debug": 2, "release": 1}

    def test_rebuilding_a_variant_is_all_hits(self):
        runs = [0]
        builder = project(runs)
        tree = world()
        builder.build(DEBUG, tree)
        builder.build(RELEASE, tree)
        assert builder.build(DEBUG, tree) == []
        assert runs == [3]

    def test_double_declaration_is_refused(self):
        runs = [0]
        builder = project(runs)
        with pytest.raises(Invalid):
            builder.declare("main.o", compile_action(runs), varies=True)


class TestTheReport:
    def test_the_split_is_measured_against_the_clone_world(self):
        runs = [0]
        builder = project(runs)
        tree = world()
        builder.build(DEBUG, tree)
        builder.build(RELEASE, tree)
        assert builder.sharing_report([DEBUG, RELEASE]) == (
            "3 entries held for 2 variants; 1 rules shared, 1 varied; "
            "clone-everything would hold 4"
        )
