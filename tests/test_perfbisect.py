from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.perfbisect import NoisyBisect

COMMITS = [f"c{number}" for number in range(16)]
CULPRIT_AT = 11
NOISE_PATTERN = (0, 7, -4)


def noisy_sampler(commit: str, run_index: int) -> int:
    base = 100
    if int(commit[1:]) >= CULPRIT_AT:
        base = 112
    return base + NOISE_PATTERN[run_index % len(NOISE_PATTERN)]


def bisect(**overrides) -> NoisyBisect:
    settings = {
        "commits": list(COMMITS),
        "sample": noisy_sampler,
        "baseline_ticks": 100,
        "threshold_percent": 10,
        "noise_percent": 8,
        "samples_per_step": 3,
    }
    settings.update(overrides)
    return NoisyBisect(**settings)


class TestTheMajority:
    def test_the_culprit_is_found_through_the_noise(self):
        chosen = bisect()
        assert chosen.find_culprit() == "c11"

    def test_the_votes_show_their_arithmetic(self):
        chosen = bisect()
        chosen.find_culprit()
        assert any(
            vote.endswith("2/3 slow -> slow")
            for vote in chosen.votes
        )

    def test_the_ledger_prices_the_certainty(self):
        chosen = bisect()
        chosen.find_culprit()
        assert chosen.runs_spent == 3 * len(chosen.votes)
        assert "certainty is what the extra runs bought" in (
            chosen.ledger()
        )


class TestRefusals:
    def test_signal_under_noise_declines_to_start(self):
        with pytest.raises(Invalid) as caught:
            bisect(threshold_percent=5)
        assert "it would elect one" in str(caught.value)

    def test_even_samples_invite_ties(self):
        with pytest.raises(Invalid):
            bisect(samples_per_step=4)

    def test_a_fast_tip_means_nothing_to_bisect(self):
        def calm(_commit, run_index):
            return 100 + NOISE_PATTERN[run_index % 3]

        with pytest.raises(Invalid) as caught:
            bisect(sample=calm).find_culprit()
        assert "no regression to bisect" in str(caught.value)

    def test_a_single_commit_is_not_a_range(self):
        with pytest.raises(Invalid):
            bisect(commits=["only"])
