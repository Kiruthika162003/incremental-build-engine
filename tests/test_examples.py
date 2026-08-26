from __future__ import annotations

from examples import firstproject, monorepoday, releasepipeline


class TestFirstProject:
    def test_the_three_builds_tell_the_story(self, capsys):
        assert firstproject.main() == 0
        out = capsys.readouterr().out
        assert "cold:  app: 8 visited, 5 ran, 0 from cache" in out
        assert "warm:  app: 8 visited, 0 ran, 5 from cache" in out
        assert "edit:  app: 8 visited, 3 ran, 2 from cache" in out
        assert "main.o untouched" in out
        assert "7 hits, 8 misses (47%)" in out


class TestMonorepoDay:
    def test_the_day_reads_in_numbers(self, capsys):
        assert monorepoday.main() == 0
        out = capsys.readouterr().out
        assert "morning edit: 1 changed: run 1, skip 3 (75% refund)" in out
        assert "core edit:    1 changed: run 4, skip 0 (0% refund)" in out
        assert "7 builds for 5 merges (1.4 builds per change), 1 exiled" in out
        assert "culprit: c19, found in 7 builds over a window of 32" in out


class TestReleasePipeline:
    def test_the_pipeline_ships_knowingly(self, capsys):
        assert releasepipeline.main() == 0
        out = capsys.readouterr().out
        assert "restamp:      ran ['release'], quarantine holds" in out
        assert "install:      2 placed, 0 strays swept" in out
        assert "package id:   " in out
        assert "drift:        bin/release: content moved" in out
