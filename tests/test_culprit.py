from __future__ import annotations

import pytest

from forge.culprit import Hunt, breakage_after
from forge.errors import Invalid

WINDOW = [f"c{number:03d}" for number in range(128)]


class TestBisection:
    def test_the_culprit_falls_out_by_arithmetic(self):
        hunt = Hunt(
            commits=list(WINDOW),
            is_broken_at=breakage_after("c077", WINDOW),
        )
        assert hunt.run() == "c077"

    def test_the_bill_is_logarithmic(self):
        hunt = Hunt(
            commits=list(WINDOW),
            is_broken_at=breakage_after("c077", WINDOW),
        )
        culprit = hunt.run()
        assert hunt.builds_spent <= 9
        assert hunt.receipt(culprit) == (
            "culprit: c077, found in 9 builds over a window of 128"
        )

    def test_the_first_commit_can_be_guilty(self):
        window = WINDOW[:8]
        hunt = Hunt(
            commits=list(window),
            is_broken_at=breakage_after("c001", window),
        )
        assert hunt.run() == "c001"

    def test_the_last_commit_can_be_guilty(self):
        window = WINDOW[:8]
        hunt = Hunt(
            commits=list(window),
            is_broken_at=breakage_after("c007", window),
        )
        assert hunt.run() == "c007"


class TestAssumptions:
    def test_a_green_end_means_nothing_to_hunt(self):
        hunt = Hunt(
            commits=WINDOW[:8],
            is_broken_at=lambda _commit: False,
        )
        with pytest.raises(Invalid, match="nothing to hunt"):
            hunt.run()

    def test_a_red_start_means_widen_the_window(self):
        hunt = Hunt(
            commits=WINDOW[:8],
            is_broken_at=lambda _commit: True,
        )
        with pytest.raises(Invalid, match="widen the window"):
            hunt.run()

    def test_a_tiny_window_is_refused(self):
        with pytest.raises(Invalid):
            Hunt(commits=["only"], is_broken_at=lambda _commit: True)


class TestFlakiness:
    def test_a_flaky_predicate_aborts_instead_of_convicting(self):
        answers = iter([True, False])

        def coin_flip(_commit: str) -> bool:
            return next(answers)

        hunt = Hunt(
            commits=WINDOW[:8],
            is_broken_at=coin_flip,
            double_check=True,
        )
        with pytest.raises(Invalid, match="no conviction"):
            hunt.run()

    def test_double_checking_doubles_the_bill(self):
        hunt = Hunt(
            commits=WINDOW[:16],
            is_broken_at=breakage_after("c009", WINDOW[:16]),
            double_check=True,
        )
        hunt.run()
        single = Hunt(
            commits=WINDOW[:16],
            is_broken_at=breakage_after("c009", WINDOW[:16]),
        )
        single.run()
        assert hunt.builds_spent == 2 * single.builds_spent
