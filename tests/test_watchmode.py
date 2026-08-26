from __future__ import annotations

from forge.loader import load
from forge.watchmode import Watcher
from forge.workspace import Workspace

PROJECT = """
source = main.c
source = lib.c

rule = main.o
command = cc
reads = main.c
writes = main.o
needs = main.c

rule = lib.o
command = cc
reads = lib.c
writes = lib.o
needs = lib.c

rule = app
command = ld
reads = main.o, lib.o
writes = app
needs = main.o, lib.o
"""


def session() -> tuple[Watcher, Workspace]:
    engine = load(PROJECT)
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("lib.c", "int lib;")
    watcher = Watcher(engine=engine, goal="app")
    watcher.prime(tree)
    return watcher, tree


class TestPolling:
    def test_a_quiet_poll_visits_nothing(self):
        watcher, tree = session()
        poll = watcher.poll(tree)
        assert poll.line() == "quiet"
        assert watcher.quiet_polls == 1

    def test_an_edit_rebuilds_exactly_its_cone(self):
        watcher, tree = session()
        tree.write_text("lib.c", "int lib; // v2")
        poll = watcher.poll(tree)
        assert poll.changed == ["lib.c"]
        assert poll.cone == ["app", "lib.o"]
        assert poll.report.ran == ["lib.o", "app"]
        assert poll.line() == "lib.c moved; cone of 2, 2 rebuilt"

    def test_the_second_save_of_the_same_bytes_is_quiet(self):
        watcher, tree = session()
        tree.write_text("lib.c", "int lib;")
        poll = watcher.poll(tree)
        assert poll.line() == "quiet"

    def test_two_edits_merge_their_cones(self):
        watcher, tree = session()
        tree.write_text("main.c", "int main; // v2")
        tree.write_text("lib.c", "int lib; // v2")
        poll = watcher.poll(tree)
        assert poll.cone == ["app", "lib.o", "main.o"]
        assert poll.report.ran == ["lib.o", "main.o", "app"]


class TestBrokenWorlds:
    def test_a_deleted_source_is_a_broken_world_not_a_rebuild(self):
        watcher, tree = session()
        tree.delete("lib.c")
        poll = watcher.poll(tree)
        assert poll.broken == (
            "lib.c was deleted but rules still read it"
        )
        assert poll.report is None

    def test_the_session_ledger_prices_the_quiet_hours(self):
        watcher, tree = session()
        for _ in range(5):
            watcher.poll(tree)
        tree.write_text("main.c", "int main; // v2")
        watcher.poll(tree)
        assert watcher.session() == "6 polls, 5 quiet, 1 rebuilds"
