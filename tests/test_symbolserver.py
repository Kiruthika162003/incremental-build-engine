from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.symbolserver import SymbolServer

TABLE = {
    0x1000: "main (app.c:12)",
    0x1040: "parse (parser.c:88)",
    0x2000: "render (render.c:5)",
}


def server() -> SymbolServer:
    built = SymbolServer()
    built.ingest("build-aabbcc", dict(TABLE))
    return built


class TestIngestion:
    def test_ingestion_frees_the_binary_to_be_stripped(self):
        verdict = server().ingest("build-ddeeff", {0x1: "f"})
        assert "the binary may now be stripped" in verdict

    def test_an_unkeyed_blob_is_refused_at_the_door(self):
        with pytest.raises(Invalid) as caught:
            SymbolServer().ingest("  ", {0x1: "f"})
        assert "write-only storage" in str(caught.value)

    def test_build_ids_do_not_get_second_opinions(self):
        with pytest.raises(Invalid):
            server().ingest("build-aabbcc", {0x1: "g"})

    def test_an_empty_table_is_refused(self):
        with pytest.raises(Invalid):
            SymbolServer().ingest("build-x", {})


class TestResolution:
    def test_a_full_crash_resolves_with_names_and_lines(self):
        report = server().resolve_crash(
            "build-aabbcc", [0x1000, 0x1040]
        )
        assert report.startswith("2 of 2 frame(s) resolved")
        assert "0x1000 -> main (app.c:12)" in report

    def test_the_stranger_binary_is_diagnosed_not_shrugged(self):
        line = server().resolve_frame("build-local", 0x1000)
        assert "the whole binary is a stranger" in line
        assert "never went through the farm" in line

    def test_the_unknown_address_names_its_search(self):
        line = server().resolve_frame("build-aabbcc", 0x9999)
        assert "known binary, unknown address among 3" in line
        assert "corruption or inlining" in line

    def test_a_frameless_crash_is_a_rumor(self):
        with pytest.raises(Invalid):
            server().resolve_crash("build-aabbcc", [])


class TestRetention:
    def test_symbols_outlive_their_binaries_on_purpose(self):
        note = server().retention_note(binaries_alive=set())
        assert note.startswith(
            "1 symbol table(s) outlive their binaries"
        )
        assert "month eleven" in note
