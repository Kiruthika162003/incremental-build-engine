"""Bisecting a slowdown: the noisy oracle answers by majority, not by once.

Bisecting a hard failure is easy because the oracle is binary;
bisecting a 10 percent slowdown through 8 percent noise is
where bisects go to lie, because a single timing run at each
step answers with the noise as often as with the truth. The
noisy bisect samples each candidate commit several times and
votes: a commit is called slow only when the majority of its
samples cross the threshold, which trades runs for
correctness at a rate the ledger prints, since every extra
sample per step multiplies the whole bisect's cost and the
budget deserves to know what certainty costs. The refusal is
the module's spine: when the regression is smaller than the
noise band, the bisect declines to start, naming both numbers,
because a bisect that cannot distinguish its signal from its
noise does not find the culprit, it elects one.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

Sampler = Callable[[str, int], int]


@dataclass
class NoisyBisect:
    commits: list[str]
    sample: Sampler
    baseline_ticks: int
    threshold_percent: int
    noise_percent: int
    samples_per_step: int = 3
    runs_spent: int = 0
    votes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.commits) < 2:
            raise Invalid("a bisect needs a range")
        if self.samples_per_step % 2 == 0:
            raise Invalid(
                "an even sample count invites ties; use odd"
            )
        if self.threshold_percent <= self.noise_percent:
            raise Invalid(
                f"a {self.threshold_percent}% regression "
                f"cannot be bisected through "
                f"{self.noise_percent}% noise; the bisect "
                "would not find the culprit, it would elect one"
            )

    def _is_slow(self, commit: str) -> bool:
        cutoff = self.baseline_ticks * (
            100 + self.threshold_percent
        ) // 100
        slow_votes = 0
        for run_index in range(self.samples_per_step):
            self.runs_spent += 1
            if self.sample(commit, run_index) >= cutoff:
                slow_votes += 1
        verdict = slow_votes * 2 > self.samples_per_step
        self.votes.append(
            f"{commit}: {slow_votes}/{self.samples_per_step} "
            f"slow -> {'slow' if verdict else 'fast'}"
        )
        return verdict

    def find_culprit(self) -> str:
        low, high = 0, len(self.commits) - 1
        if not self._is_slow(self.commits[high]):
            raise Invalid(
                "the newest commit votes fast; there is no "
                "regression to bisect"
            )
        while high - low > 1:
            middle = (low + high) // 2
            if self._is_slow(self.commits[middle]):
                high = middle
            else:
                low = middle
        return self.commits[high]

    def ledger(self) -> str:
        return (
            f"{self.runs_spent} timing run(s) spent at "
            f"{self.samples_per_step} sample(s) per step; "
            "certainty is what the extra runs bought"
        )
