from __future__ import annotations

from forge.actions import Action
from forge.depfiles import DiscoveringCache
from forge.workspace import Workspace


def including_compiler(runs: list[int]) -> Action:
    """Reads main.c, follows its one include line, emits main.o."""

    def rule(tree) -> None:
        runs[0] += 1
        source = tree.read_text("main.c")
        include = source.split('"')[1] if '"' in source else None
        body = tree.read_text(include) if include else ""
        tree.write_text("main.o", f"obj({source}|{body})")

    return Action(
        name="compile main.c",
        command="cc -MD",
        reads=("main.c",),
        writes=("main.o",),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", 'include "util.h"; int main;')
    tree.write_text("util.h", "#define U 1")
    tree.write_text("other.h", "#define O 2")
    return tree


class TestDiscovery:
    def test_the_first_run_discovers_the_real_reads(self):
        runs = [0]
        cache = DiscoveringCache()
        action = including_compiler(runs)
        assert cache.run(action, world()) == "miss"
        assert cache.discovered_reads(action) == ["main.c", "util.h"]

    def test_the_second_run_hits_on_the_discovered_set(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        cache.run(including_compiler(runs), tree)
        assert cache.run(including_compiler(runs), tree) == "hit"
        assert runs == [1]

    def test_an_edited_header_misses_despite_being_undeclared(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        cache.run(including_compiler(runs), tree)
        tree.write_text("util.h", "#define U 99")
        assert cache.run(including_compiler(runs), tree) == "miss"
        assert runs == [2]
        assert cache.stale_discoveries == 1

    def test_unread_headers_still_do_not_matter(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        cache.run(including_compiler(runs), tree)
        tree.write_text("other.h", "#define O 99")
        assert cache.run(including_compiler(runs), tree) == "hit"
        assert runs == [1]

    def test_a_new_include_rediscovers_the_set(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        action = including_compiler(runs)
        cache.run(action, tree)
        tree.write_text("main.c", 'include "other.h"; int main;')
        assert cache.run(action, tree) == "miss"
        assert cache.discovered_reads(action) == ["main.c", "other.h"]

    def test_a_deleted_discovered_file_misses(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        cache.run(including_compiler(runs), tree)
        tree.delete("util.h")
        tree.write_text("main.c", "int main;")
        assert cache.run(including_compiler(runs), tree) == "miss"

    def test_the_ledger_counts_the_stale(self):
        runs = [0]
        cache = DiscoveringCache()
        tree = world()
        cache.run(including_compiler(runs), tree)
        tree.write_text("util.h", "#define U 2")
        cache.run(including_compiler(runs), tree)
        cache.run(including_compiler(runs), tree)
        assert cache.ledger() == (
            "1 hits, 2 misses, 1 discoveries went stale"
        )
