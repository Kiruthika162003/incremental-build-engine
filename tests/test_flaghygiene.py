from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.flaghygiene import (
    audit,
    equivalent,
    hygiene_report,
    normalize,
)


class TestNormalization:
    def test_shuffled_defines_collide_into_one_key(self):
        assert equivalent(
            "cc -DFOO -DBAR -Iinc main.c",
            "cc -DBAR -Iinc -DFOO main.c",
        )

    def test_positional_arguments_keep_their_order(self):
        assert normalize("cc a.c b.c").endswith("a.c b.c")
        assert not equivalent("cc a.c b.c", "cc b.c a.c")

    def test_the_compiler_name_stays_first(self):
        assert normalize("cc -DZ -DA main.c").startswith("cc -DA -DZ")

    def test_an_empty_command_is_refused(self):
        with pytest.raises(Invalid):
            normalize("   ")


class TestThePoisonHunt:
    def test_the_timestamp_macro_is_named_with_its_repair(self):
        complaints = audit("cc -DBUILD_TIME=now main.c")
        assert len(complaints) == 1
        assert "bakes the clock or the host" in complaints[0].reason
        assert "stamp late" in complaints[0].repair

    def test_the_absolute_include_names_the_machine(self):
        complaints = audit("cc -I/home/dev9/proj/inc main.c")
        assert "differs per machine" in complaints[0].reason

    def test_a_per_run_seed_is_caught(self):
        complaints = audit("fuzz --seed=8271 corpus")
        assert "every key unique" in complaints[0].reason

    def test_a_fixed_seed_is_hygiene(self):
        assert audit("fuzz --seed=0 corpus") == []

    def test_a_clean_command_has_no_complaints(self):
        assert audit("cc -DNDEBUG -Iinc main.c") == []


class TestTheReport:
    def test_the_report_counts_recovered_and_poisoned(self):
        report = hygiene_report(
            [
                "cc -DFOO -DBAR main.c",
                "cc -DBAR -DFOO main.c",
                "cc -DBUILD_TIME=now main.c",
            ]
        )
        assert report.startswith(
            "3 command(s), 2 canonical key(s), "
            "1 recovered by normalization, 1 still poisoned"
        )
        assert "stamp late" in report

    def test_an_empty_fleet_is_refused(self):
        with pytest.raises(Invalid):
            hygiene_report([])
