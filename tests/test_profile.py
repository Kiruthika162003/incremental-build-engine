from __future__ import annotations

from forge.graph import Graph
from forge.profile import Profile


def lopsided() -> Profile:
    """The fat rule sits off the path; the path is a chain of thin ones."""
    graph = Graph()
    graph.declare("gen")
    graph.declare("thin1", needs=("gen",))
    graph.declare("thin2", needs=("thin1",))
    graph.declare("fat", needs=("gen",))
    graph.declare("app", needs=("thin2", "fat"))
    return Profile(
        graph=graph,
        costs={"gen": 1, "thin1": 6, "thin2": 6, "fat": 9, "app": 1},
    )


class TestHotspots:
    def test_the_fattest_rule_leads_the_table(self):
        rows = lopsided().hotspots("app")
        assert rows[0] == ("fat", 9)

    def test_top_limits_the_table(self):
        assert len(lopsided().hotspots("app", top=2)) == 2


class TestSlack:
    def test_the_path_rules_have_zero_slack(self):
        rows = lopsided().slack_table("app")
        on_path = {row.target for row in rows if row.slack == 0}
        assert on_path == {"gen", "thin1", "thin2", "app"}

    def test_the_fat_off_path_rule_has_the_slack(self):
        rows = lopsided().slack_table("app")
        fat = next(row for row in rows if row.target == "fat")
        assert fat.slack == 3

    def test_the_row_marks_the_path(self):
        rows = lopsided().slack_table("app")
        assert rows[0].line().endswith("<- the path")


class TestAdvice:
    def test_the_fat_off_path_rule_is_named_a_waste(self):
        advice = lopsided().advice("app")
        assert advice.startswith(
            "the fattest rule (fat, 9 ticks) is OFF the path"
        )
        assert "gen, thin1, thin2, app" in advice

    def test_a_fat_rule_on_the_path_is_the_real_target(self):
        graph = Graph()
        graph.declare("gen")
        graph.declare("heavy", needs=("gen",))
        graph.declare("app", needs=("heavy",))
        profile = Profile(
            graph=graph, costs={"gen": 1, "heavy": 20, "app": 1}
        )
        assert profile.advice("app") == (
            "optimise heavy: it is both the fattest rule and on the path"
        )

    def test_the_page_carries_both_tables_and_the_advice(self):
        page = lopsided().page("app")
        assert "hotspots:" in page
        assert "slack:" in page
        assert page.splitlines()[-1].startswith("the fattest rule")
