from __future__ import annotations

from examples import (
    coldci,
    editsession,
    farmday,
    firstproject,
    graphhealth,
    migrationday,
    monorepoday,
    perfweek,
    refactorweek,
    releasepipeline,
    supplychain,
    vendorweek,
)


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


class TestColdCi:
    def test_the_morning_reads_in_three_lines(self, capsys):
        assert coldci.main() == 0
        out = capsys.readouterr().out
        assert "lints:   3 spawns for 9 actions; 18 floor ticks avoided" in out
        assert "probe:   stamper: FLAKY, outputs differ at ['stamp.out']" in out
        assert "98% of the build stayed in the sky" in out


class TestRefactorWeek:
    def test_the_week_reads_end_to_end(self, capsys):
        assert refactorweek.main() == 0
        out = capsys.readouterr().out
        assert (
            "netlib -> network_lib [90 ticks left]: billing (2x), "
            "search (1x)"
        ) in out
        assert "cache impact: 1 existing targets will miss (app)" in out
        assert "declare auth/internal restricted to ['billing']" in out
        assert "orphans: ['search'], ghost-owned: []" in out


class TestEditSession:
    def test_the_session_reads_end_to_end(self, capsys):
        assert editsession.main() == 0
        out = capsys.readouterr().out
        assert "save:   main.c moved; cone of 2, 2 rebuilt" in out
        assert "4 polls, 3 quiet, 1 rebuilds" in out
        assert "buffer: keys diverge" in out
        assert "compdb: fresh" in out


class TestSupplyChain:
    def test_the_day_holds_at_every_gate(self, capsys):
        assert supplychain.main() == 0
        out = capsys.readouterr().out
        assert "the midnight 1.9 release changed nothing" in out
        assert (
            "quarantine served None, corroboration served 'digest-1'"
        ) in out
        assert "licenses: MIT: 1, Zlib: 1, proprietary: 1" in out
        assert "externals: json, zlib" in out


class TestPerfWeek:
    def test_the_week_reads_end_to_end(self, capsys):
        assert perfweek.main() == 0
        out = capsys.readouterr().out
        assert (
            "1 benchmark(s) armed, 1 declined for noise, "
            "1 regression(s)"
        ) in out
        assert "REGRESSION parse: 8.0%" in out
        assert "refresh soon: coverage fell to 60%" in out
        assert "OVERDRAFT 50ms" in out
        assert "60 tick(s) returned to the developer" in out


class TestMigrationDay:
    def test_the_day_reads_end_to_end(self, capsys):
        assert migrationday.main() == 0
        out = capsys.readouterr().out
        assert (
            "3/4 rules translated clean (75%); 1 need a human, "
            "1 phony targets dropped"
        ) in out
        assert "agreement 67% (2 of 3 outputs)" in out
        assert "the shadow is the system; cut over" in out
        assert "3 held total" in out
        assert "2 compliant, 1 skewed against pin 2.3.0" in out
        assert "app-9.0 promoted staging -> canary" in out


class TestFarmDay:
    def test_the_day_reads_end_to_end(self, capsys):
        assert farmday.main() == 0
        out = capsys.readouterr().out
        assert (
            "2 scale-up(s), 1 scale-down(s), 16 idle worker "
            "tick(s), 44 queued build tick(s)"
        ) in out
        assert "done at tick 70" in out
        assert "memory-bound (16 memory waits vs 0 worker waits)" in out
        assert "1 batch jobs promoted by patience" in out
        assert "mac-arm lacks xcode=15 (pool has 14)" in out


class TestVendorWeek:
    def test_the_week_reads_end_to_end(self, capsys):
        assert vendorweek.main() == 0
        out = capsys.readouterr().out
        assert (
            "corrupt: mirror/curl/deadbeef/curl-8.5.tar "
            "expected deadbeef found 00000000"
        ) in out
        assert "1 stray file(s) rotting harmlessly" in out
        assert "stale = ['win32-workaround']" in out
        assert "app ships clean: 3 components" in out
        assert "NOTICE: Compression by the zlib authors." in out
        assert "which vendor produced" in out
        assert "root causes: ['zlib.tar']" in out


class TestGraphHealth:
    def test_the_rounds_read_end_to_end(self, capsys):
        assert graphhealth.main() == 0
        out = capsys.readouterr().out
        assert "declare auth/internal restricted to ['billing']" in out
        assert "app declares httplib but consumes nothing from it" in out
        assert "loop: auth, billing" in out
        assert "add needs = crypto (observed at run time)" in out
