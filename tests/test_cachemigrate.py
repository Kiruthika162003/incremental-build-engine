from __future__ import annotations

import pytest

from forge.cachemigrate import CacheMigrator
from forge.errors import Invalid

OLD_SHELF = {
    "compile:a": {"digest": "aa", "ticks": 10},
    "compile:b": {"digest": "bb", "ticks": 20},
    "link:app": {"digest": "cc"},
}


def widen(entry: dict) -> dict | str:
    if "ticks" not in entry:
        return "the new format requires the cost field"
    return {
        "digest": entry["digest"] * 2,
        "cost": {"ticks": entry["ticks"]},
    }


class TestMigration:
    def test_upgradable_entries_keep_their_warmth(self):
        migrator = CacheMigrator(upgrade=widen)
        report = migrator.run(dict(OLD_SHELF))
        assert report.startswith("2 of 3 entrie(s) survive (67%)")
        assert migrator.migrated["compile:a"] == {
            "digest": "aaaa",
            "cost": {"ticks": 10},
        }

    def test_nothing_is_dropped_silently(self):
        migrator = CacheMigrator(upgrade=widen)
        report = migrator.run(dict(OLD_SHELF))
        assert (
            "dropped link:app: the new format requires the "
            "cost field"
        ) in report
        assert migrator.dropped == [
            "link:app: the new format requires the cost field"
        ]

    def test_an_empty_shelf_is_refused(self):
        with pytest.raises(Invalid):
            CacheMigrator(upgrade=widen).run({})


class TestTheDryRun:
    def test_the_dry_run_writes_nothing(self):
        migrator = CacheMigrator(upgrade=widen)
        report = migrator.run(dict(OLD_SHELF), dry_run=True)
        assert report.startswith("dry run: 2 of 3")
        assert migrator.migrated == {}
        assert migrator.dropped == []

    def test_heavy_loss_demands_a_translator(self):
        lossy = CacheMigrator(
            upgrade=lambda _entry: "cannot represent"
        )
        report = lossy.run(dict(OLD_SHELF), dry_run=True)
        assert "0 of 3 entrie(s) survive" in report
        assert "should pay for a translator" in report

    def test_a_healthy_dry_run_stays_calm(self):
        migrator = CacheMigrator(upgrade=widen)
        report = migrator.run(dict(OLD_SHELF), dry_run=True)
        assert "translator" not in report
