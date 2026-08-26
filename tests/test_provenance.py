from __future__ import annotations

import pytest

from forge.errors import Missing
from forge.loader import load
from forge.provenance import record, reproduce
from forge.workspace import Workspace

PROJECT = """
source = main.c
source = lib.c

rule = main.o
command = cc -O2
reads = main.c
writes = main.o
needs = main.c

rule = lib.o
command = cc -O2
reads = lib.c
writes = lib.o
needs = lib.c

rule = app
command = ld
reads = main.o, lib.o
writes = app
needs = main.o, lib.o
"""

SOURCES = {"main.c": "int main;", "lib.c": "int lib;"}


def built() -> tuple:
    engine = load(PROJECT)
    tree = Workspace()
    for path, text in SOURCES.items():
        tree.write_text(path, text)
    manifest = record(engine, "app", tree)
    return engine, manifest


class TestTheManifest:
    def test_the_story_names_every_participant(self):
        _, manifest = built()
        assert set(manifest.source_digests) == {"main.c", "lib.c"}
        assert set(manifest.entries) == {"main.o", "lib.o", "app"}

    def test_the_attestation_is_stable(self):
        _, first = built()
        _, second = built()
        assert first.attestation() == second.attestation()

    def test_a_changed_source_changes_the_attestation(self):
        _, manifest = built()
        tree = Workspace()
        tree.write_text("main.c", "int main; // v2")
        tree.write_text("lib.c", "int lib;")
        other = record(load(PROJECT), "app", tree)
        assert other.attestation() != manifest.attestation()


class TestPoison:
    def test_the_poisoned_source_names_its_reach(self):
        _, manifest = built()
        assert manifest.reached_by("lib.c") == ["app", "lib.o"]

    def test_the_untouched_side_is_not_dragged_in(self):
        _, manifest = built()
        assert "main.o" not in manifest.reached_by("lib.c")

    def test_a_stranger_is_refused(self):
        _, manifest = built()
        with pytest.raises(Missing, match="not in this build's story"):
            manifest.reached_by("ghost.c")


class TestReproduction:
    def test_the_same_sources_reproduce_byte_for_byte(self):
        _, manifest = built()
        ok, verdict = reproduce(load(PROJECT), manifest, SOURCES)
        assert ok
        assert "byte for byte" in verdict

    def test_a_drifted_source_fails_with_the_differing_names(self):
        _, manifest = built()
        drifted = dict(SOURCES, **{"lib.c": "int lib; // drifted"})
        ok, verdict = reproduce(load(PROJECT), manifest, drifted)
        assert not ok
        assert "lib.o" in verdict
        assert "app" in verdict
