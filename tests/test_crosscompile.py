from __future__ import annotations

import pytest

from forge.crosscompile import CrossGraph, PlatformRule
from forge.errors import Invalid


def wired() -> CrossGraph:
    graph = CrossGraph()
    graph.declare(PlatformRule(name="host:protoc", platform="host"))
    graph.declare(
        PlatformRule(
            name="target:messages.o",
            platform="target",
            runs_tool="host:protoc",
        )
    )
    graph.declare(
        PlatformRule(
            name="target:app",
            platform="target",
            consumes=("target:messages.o",),
        )
    )
    return graph


class TestTheLine:
    def test_a_legal_cross_build_checks_clean(self):
        assert wired().check() == []

    def test_an_artifact_crossing_the_line_is_named(self):
        graph = wired()
        graph.declare(
            PlatformRule(
                name="host:debugger",
                platform="host",
                consumes=("target:messages.o",),
            )
        )
        complaints = graph.check()
        assert complaints == [
            "host:debugger (host) consumes target:messages.o "
            "(target): an artifact crossed the line"
        ]

    def test_only_host_tools_execute(self):
        graph = wired()
        graph.declare(
            PlatformRule(
                name="target:codegen",
                platform="target",
                runs_tool="target:app",
            )
        )
        complaints = graph.check()
        assert any(
            "only host tools execute" in line for line in complaints
        )

    def test_dangling_references_are_named(self):
        graph = CrossGraph()
        graph.declare(
            PlatformRule(
                name="target:app",
                platform="target",
                consumes=("target:ghost.o",),
            )
        )
        assert "nothing declares" in graph.check()[0]

    def test_unknown_platforms_are_refused_at_the_door(self):
        with pytest.raises(Invalid, match="unknown platform"):
            PlatformRule(name="x", platform="wasm")


class TestTheEconomy:
    def test_shared_stems_are_counted_once(self):
        graph = wired()
        graph.declare(
            PlatformRule(name="host:compiler", platform="host")
        )
        graph.declare(
            PlatformRule(name="target:compiler", platform="target")
        )
        shared, split = graph.shared_and_split()
        assert split == ["compiler"]
        assert "protoc" in shared
        assert graph.economy() == (
            "1 stems doubled across platforms, 3 built once"
        )
