from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.loader import load, standard_toolbox
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
cost = 5
"""


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("lib.c", "int lib;")
    return tree


class TestLoading:
    def test_the_file_becomes_a_working_engine(self):
        engine = load(PROJECT)
        tree = world()
        report = engine.build("app", tree)
        assert report.ran == ["lib.o", "main.o", "app"]
        assert tree.read_text("app") == "bin[obj(int main;)+obj(int lib;)]"

    def test_the_loaded_engine_is_incremental(self):
        engine = load(PROJECT)
        tree = world()
        engine.build("app", tree)
        tree.write_text("lib.c", "int lib; // v2")
        report = engine.build("app", tree)
        assert report.ran == ["lib.o", "app"]
        assert report.hits == ["main.o"]

    def test_costs_travel_from_text_to_engine(self):
        assert load(PROJECT).costs["app"] == 5


class TestRefusals:
    def test_an_unregistered_tool_lists_the_toolbox(self):
        text = "source = x\nrule = a\ncommand = javac\nreads = x\nwrites = y\nneeds = x"
        with pytest.raises(Invalid, match="the toolbox holds"):
            load(text)

    def test_a_read_nothing_provides_is_a_lie_about_the_world(self):
        text = (
            "source = main.c\n"
            "rule = main.o\ncommand = cc\nreads = ghost.h\n"
            "writes = main.o\nneeds = main.c"
        )
        with pytest.raises(Invalid, match="no source or rule provides"):
            load(text)

    def test_reading_another_rules_output_is_provided(self):
        text = (
            "source = main.c\n"
            "rule = main.o\ncommand = cc\nreads = main.c\n"
            "writes = main.o\nneeds = main.c\n"
            "rule = app\ncommand = ld\nreads = main.o\n"
            "writes = app\nneeds = main.o"
        )
        engine = load(text)
        tree = Workspace()
        tree.write_text("main.c", "int main;")
        assert engine.build("app", tree).ran == ["main.o", "app"]

    def test_double_registration_is_refused(self):
        box = standard_toolbox()
        with pytest.raises(Invalid, match="already registered"):
            box.register("cc", lambda _stanza: None)
