from __future__ import annotations

import pytest

from forge.actions import Action
from forge.errors import Invalid
from forge.remotecache import RemoteBuilder, RemoteStore
from forge.workspace import Workspace


def compiler(runs: list[int]) -> Action:
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


def formatter(runs: list[int]) -> Action:
    def rule(tree) -> None:
        runs[0] += 1
        tree.write_text("fmt.txt", tree.read_text("main.c").strip())

    return Action(
        name="format",
        command="fmt",
        reads=("main.c",),
        writes=("fmt.txt",),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    return tree


class TestSharing:
    def test_the_second_machine_hits_what_the_first_built(self):
        runs = [0]
        remote = RemoteStore()
        first = RemoteBuilder(remote=remote)
        second = RemoteBuilder(remote=remote)
        assert first.run(compiler(runs), world(), cost=10) == "built"
        outcome = second.run(compiler(runs), world(), cost=10)
        assert outcome == "remote-hit"
        assert runs == [1]
        assert second.ticks_saved == 10

    def test_the_remote_hit_lands_the_bytes(self):
        runs = [0]
        remote = RemoteStore()
        RemoteBuilder(remote=remote).run(compiler(runs), world(), cost=10)
        tree = world()
        RemoteBuilder(remote=remote).run(compiler(runs), tree, cost=10)
        assert tree.read_text("main.o") == "obj(int main;)"

    def test_a_downloaded_result_becomes_a_local_hit_next_time(self):
        runs = [0]
        remote = RemoteStore()
        RemoteBuilder(remote=remote).run(compiler(runs), world(), cost=10)
        second = RemoteBuilder(remote=remote)
        second.run(compiler(runs), world(), cost=10)
        outcome = second.run(compiler(runs), world(), cost=10)
        assert outcome == "local-hit"
        assert remote.round_trips == 2

    def test_negative_costs_are_refused(self):
        with pytest.raises(Invalid):
            RemoteBuilder(remote=RemoteStore()).run(
                compiler([0]), world(), cost=-1
            )


class TestTheThreshold:
    def test_cheap_actions_never_touch_the_network(self):
        runs = [0]
        remote = RemoteStore()
        builder = RemoteBuilder(remote=remote, upload_threshold=3)
        assert builder.run(formatter(runs), world(), cost=1) == "built"
        assert remote.round_trips == 0
        assert remote.bytes_uploaded == 0
        assert builder.kept_local == 1

    def test_cheap_work_is_rebuilt_locally_on_every_machine(self):
        runs = [0]
        remote = RemoteStore()
        RemoteBuilder(remote=remote).run(formatter(runs), world(), cost=1)
        RemoteBuilder(remote=remote).run(formatter(runs), world(), cost=1)
        assert runs == [2]

    def test_the_threshold_is_the_dial(self):
        runs = [0]
        remote = RemoteStore()
        eager = RemoteBuilder(remote=remote, upload_threshold=1)
        eager.run(formatter(runs), world(), cost=1)
        assert remote.bytes_uploaded > 0


class TestTheReceipts:
    def test_both_sides_price_the_trade(self):
        runs = [0]
        remote = RemoteStore()
        first = RemoteBuilder(remote=remote)
        first.run(compiler(runs), world(), cost=10)
        second = RemoteBuilder(remote=remote)
        second.run(compiler(runs), world(), cost=10)
        assert first.receipt() == (
            "0 local hits, 0 remote hits, 1 built (0 kept local), "
            "0 ticks saved"
        )
        assert second.receipt() == (
            "0 local hits, 1 remote hits, 0 built (0 kept local), "
            "10 ticks saved"
        )
        assert remote.traffic() == "2 round trips, 14 down, 14 up"
