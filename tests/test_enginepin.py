from __future__ import annotations

import pytest

from forge.enginepin import FarmRollCall, grade, parse_version
from forge.errors import Invalid

PIN = (2, 3, 0)


class TestParsing:
    def test_a_dotted_triple_parses(self):
        assert parse_version("2.3.7") == (2, 3, 7)

    def test_junk_is_refused(self):
        for text in ("2.3", "v2.3.0", "2.3.x", ""):
            with pytest.raises(Invalid):
                parse_version(text)


class TestGrading:
    def test_the_same_version_is_compliant(self):
        assert grade(PIN, (2, 3, 0)) == "compliant"

    def test_a_newer_minor_is_compliant(self):
        assert grade(PIN, (2, 5, 1)) == "compliant"

    def test_an_older_minor_would_drop_fields(self):
        verdict = grade(PIN, (2, 1, 9))
        assert verdict.startswith("refused: minor 1")
        assert "silently drop fields" in verdict

    def test_a_different_major_is_a_stranger(self):
        assert "the protocols are strangers" in grade(PIN, (3, 0, 0))
        assert "strangers" in grade(PIN, (1, 9, 9))


class TestTheRollCall:
    def test_a_clean_farm_speaks_one_protocol(self):
        farm = FarmRollCall(pin=PIN)
        farm.check_in("w1", "2.3.0")
        farm.check_in("w2", "2.4.2")
        assert farm.roll_call() == (
            "2 worker(s) compliant with pin 2.3.0; the farm "
            "speaks one protocol"
        )

    def test_skewed_workers_are_named_with_verdicts(self):
        farm = FarmRollCall(pin=PIN)
        farm.check_in("w1", "2.3.0")
        farm.check_in("w-old", "2.1.0")
        report = farm.roll_call()
        assert "1 compliant, 1 skewed against pin 2.3.0" in report
        assert "w-old at 2.1.0: refused: minor 1" in report

    def test_the_all_skewed_farm_blames_the_pin(self):
        farm = FarmRollCall(pin=(9, 0, 0))
        farm.check_in("w1", "2.3.0")
        farm.check_in("w2", "2.3.0")
        assert (
            "the finger points at the pin nobody rolled forward"
        ) in farm.roll_call()

    def test_check_in_answers_each_worker_directly(self):
        farm = FarmRollCall(pin=PIN)
        assert farm.check_in("w1", "2.3.0") == "w1 joins the farm"
        assert "refused" in farm.check_in("w2", "1.0.0")

    def test_an_empty_farm_has_no_roll_call(self):
        with pytest.raises(Invalid):
            FarmRollCall(pin=PIN).roll_call()
