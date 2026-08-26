from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.installtree import (
    InstallLayout,
    assemble,
    drift,
    layout_digest,
)
from forge.workspace import Workspace


def built_world() -> Workspace:
    tree = Workspace()
    tree.write_text("out/app", "bin[app]")
    tree.write_text("out/helper", "bin[helper]")
    tree.write_text("out/debug.log", "noise")
    return tree


def layout() -> InstallLayout:
    plan = InstallLayout()
    plan.place("out/app", "bin/app")
    plan.place("out/helper", "libexec/helper")
    return plan


class TestAssembly:
    def test_artifacts_land_at_their_destinations(self):
        tree = built_world()
        receipt = assemble(layout(), tree)
        assert tree.read_text("dist/bin/app") == "bin[app]"
        assert receipt.placed == ["dist/bin/app", "dist/libexec/helper"]

    def test_a_hole_refuses_the_whole_install(self):
        plan = layout()
        plan.place("out/ghost", "bin/ghost")
        with pytest.raises(Missing, match="refuses to ship a hole"):
            assemble(plan, built_world())

    def test_strays_in_the_install_root_are_swept(self):
        tree = built_world()
        tree.write_text("dist/leftover.so", "old bits")
        receipt = assemble(layout(), tree)
        assert receipt.swept == ["dist/leftover.so"]
        assert not tree.exists("dist/leftover.so")
        assert receipt.line() == "2 placed, 1 strays swept"

    def test_two_claims_on_one_destination_are_refused(self):
        plan = layout()
        with pytest.raises(Invalid, match="cannot hold both"):
            plan.place("out/debug.log", "bin/app")


class TestDrift:
    def test_identical_installs_share_a_digest(self):
        first = built_world()
        assemble(layout(), first)
        second = built_world()
        assemble(layout(), second)
        assert layout_digest(layout(), first) == layout_digest(
            layout(), second
        )

    def test_moved_content_is_named_by_destination(self):
        tree = built_world()
        assemble(layout(), tree)
        previous = {
            "bin/app": tree.digest_of("dist/bin/app"),
            "libexec/helper": "0" * 32,
            "man/old.1": "1" * 32,
        }
        report = drift(previous, layout(), tree)
        assert report == [
            "libexec/helper: content moved",
            "man/old.1: dropped from the package",
        ]

    def test_a_new_destination_reads_as_new(self):
        tree = built_world()
        assemble(layout(), tree)
        report = drift({}, layout(), tree)
        assert "bin/app: new in this release" in report
