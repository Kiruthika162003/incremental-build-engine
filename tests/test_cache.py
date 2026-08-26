from __future__ import annotations

from forge.actions import Action
from forge.cache import ActionCache
from forge.workspace import Workspace


def compile_action(counter: list[int]) -> Action:
    def rule(tree) -> None:
        counter[0] += 1
        source = tree.read_text("main.c")
        tree.write_text("main.o", f"obj({source})")

    return Action(
        name="compile",
        command="cc -O2",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("extra.h", "#define X 1")
    return tree


class TestHitsAndMisses:
    def test_the_first_run_misses_and_executes(self):
        runs = [0]
        cache = ActionCache()
        outcome, seen = cache.run(compile_action(runs), world(), cost=7)
        assert outcome == "miss"
        assert runs == [1]
        assert seen is not None

    def test_the_second_run_hits_and_does_not_execute(self):
        runs = [0]
        cache = ActionCache()
        tree = world()
        cache.run(compile_action(runs), tree, cost=7)
        tree.delete("main.o")
        outcome, seen = cache.run(compile_action(runs), tree, cost=7)
        assert outcome == "hit"
        assert runs == [1]
        assert seen is None
        assert tree.read_text("main.o") == "obj(int main;)"

    def test_a_changed_input_misses_again(self):
        runs = [0]
        cache = ActionCache()
        tree = world()
        cache.run(compile_action(runs), tree)
        tree.write_text("main.c", "int main; // v2")
        outcome, _ = cache.run(compile_action(runs), tree)
        assert outcome == "miss"
        assert runs == [2]

    def test_two_worlds_with_the_same_bytes_share_one_entry(self):
        runs = [0]
        cache = ActionCache()
        cache.run(compile_action(runs), world(), cost=7)
        outcome, _ = cache.run(compile_action(runs), world(), cost=7)
        assert outcome == "hit"
        assert runs == [1]

    def test_the_ledger_defends_the_cache(self):
        runs = [0]
        cache = ActionCache()
        tree = world()
        cache.run(compile_action(runs), tree, cost=7)
        cache.run(compile_action(runs), world(), cost=7)
        assert cache.ledger() == (
            "1 hits, 1 misses (50%), 7 ticks saved, "
            "0 dirty results refused"
        )


class TestDirtyRuns:
    def sneaky_action(self, runs: list[int]) -> Action:
        def rule(tree) -> None:
            runs[0] += 1
            tree.read_text("extra.h")
            source = tree.read_text("main.c")
            tree.write_text("main.o", f"obj({source})")

        return Action(
            name="compile",
            command="cc -O2",
            reads=("main.c",),
            writes=("main.o",),
            rule=rule,
        )

    def test_a_dirty_run_executes_but_is_not_remembered(self):
        runs = [0]
        cache = ActionCache()
        tree = world()
        outcome, seen = cache.run(self.sneaky_action(runs), tree)
        assert outcome == "miss-dirty"
        assert seen.undeclared_reads(self.sneaky_action(runs))
        assert cache.entries == {}
        assert cache.dirty_refusals == 1

    def test_the_dirty_action_never_earns_a_hit(self):
        runs = [0]
        cache = ActionCache()
        tree = world()
        cache.run(self.sneaky_action(runs), tree)
        cache.run(self.sneaky_action(runs), tree)
        assert runs == [2]
        assert cache.hits == 0
