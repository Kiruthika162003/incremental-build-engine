from __future__ import annotations

from forge.actions import Action
from forge.stamps import STAMP_PATH, stamped_tower


class TestQuarantine:
    def test_the_cold_build_runs_everything(self):
        project, tree = stamped_tower(units=4)
        report = project.engine.build("release", tree)
        assert len(report.ran) == 5
        assert "v0.0.0" in tree.read_text("release")

    def test_a_restamp_rebuilds_exactly_the_assembly(self):
        project, tree = stamped_tower(units=4)
        project.engine.build("release", tree)
        report = project.restamp_and_build(tree, "v1.2.3")
        assert project.quarantine_holds(report)
        assert report.ran == ["release"]
        assert len(report.hits) == 4
        assert "v1.2.3" in tree.read_text("release")

    def test_restamping_the_same_version_rebuilds_nothing(self):
        project, tree = stamped_tower(units=4)
        project.engine.build("release", tree)
        report = project.restamp_and_build(tree, "v0.0.0")
        assert report.ran == []

    def test_a_real_edit_still_rebuilds_its_cone(self):
        project, tree = stamped_tower(units=4)
        project.engine.build("release", tree)
        tree.write_text("unit2.c", "int unit2; // v2")
        report = project.engine.build("release", tree)
        assert report.ran == ["unit2.o", "release"]
        assert not project.quarantine_holds(report)

    def test_a_leaked_stamp_is_caught_by_the_arithmetic(self):
        project, tree = stamped_tower(units=2)

        def leaky_rule(view) -> None:
            stamp = view.read_text(STAMP_PATH)
            view.write_text(
                "unit0.o", f"obj({view.read_text('unit0.c')}@{stamp})"
            )

        project.engine.actions["unit0.o"] = Action(
            name="compile unit0.c",
            command="cc",
            reads=("unit0.c", STAMP_PATH),
            writes=("unit0.o",),
            rule=leaky_rule,
        )
        project.engine.build("release", tree)
        report = project.restamp_and_build(tree, "v9.9.9")
        assert not project.quarantine_holds(report)
        assert report.ran == ["unit0.o", "release"]
