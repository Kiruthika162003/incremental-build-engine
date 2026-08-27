"""The waterline: the disk fills Thursday, says the rate, if the rate holds.

Disk alerts fire at thresholds, which means they fire when
the time to act is already spent; the waterline watches the
rate of rise instead and answers the operational question,
when does this disk fill at the current rate, in days,
because Thursday is actionable and 87 percent is trivia. The
forecast carries its own honesty clause: the ETA is published
only when the recent rate is steady, and an erratic rate gets
"no forecast" with the variance named, since a confident
Thursday computed from a rate that doubled twice this week is
not a forecast, it is a horoscope with units. A falling
waterline is reported as such, and the report resists the
final temptation: it never rounds an ETA of 1.4 days up to
"about two", because the operator who trusts the two is the
one who needed the one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

STEADY_SPREAD = 0.5


@dataclass
class Waterline:
    capacity: int
    samples: list[int] = field(default_factory=list)

    def observe(self, used: int) -> None:
        if not 0 <= used <= self.capacity:
            raise Invalid(
                "usage must sit between zero and capacity"
            )
        self.samples.append(used)

    def _rates(self) -> list[int]:
        return [
            after - before
            for before, after in zip(
                self.samples, self.samples[1:], strict=False
            )
        ]

    def forecast(self) -> str:
        if len(self.samples) < 3:
            raise Invalid(
                "a rate needs at least three observations"
            )
        rates = self._rates()[-4:]
        mean = sum(rates) / len(rates)
        if mean <= 0:
            return (
                "the waterline is falling or flat; no fill "
                "date exists at the current rate"
            )
        spread = max(rates) - min(rates)
        if spread > abs(mean) * (1 + STEADY_SPREAD):
            return (
                f"no forecast: the rate swings by {spread} "
                f"around a mean of {mean:.0f}, and a confident "
                "Thursday from a rate that doubled twice this "
                "week is a horoscope with units"
            )
        remaining = self.capacity - self.samples[-1]
        days = remaining / mean
        return (
            f"fills in {days:.1f} day(s) at "
            f"{mean:.0f}/day; unrounded, because the operator "
            "who trusts the two is the one who needed the one"
        )
