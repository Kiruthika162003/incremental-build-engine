from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.perfgate import Bench, armed, fleet_report, verdict

STEADY_OLD = Bench(name="parse", samples=(100, 101, 99, 100))
STEADY_BAD = Bench(name="parse", samples=(108, 109, 107, 108))
NOISY_OLD = Bench(name="render", samples=(100, 92, 108))
NOISY_NEW = Bench(name="render", samples=(104, 96, 112))


class TestArming:
    def test_a_steady_bench_earns_its_gate(self):
        assert armed(STEADY_OLD, threshold_percent=5)

    def test_a_noisy_bench_does_not(self):
        assert not armed(NOISY_OLD, threshold_percent=5)

    def test_two_samples_cannot_show_a_spread(self):
        with pytest.raises(Invalid):
            Bench(name="x", samples=(1, 2))


class TestVerdicts:
    def test_a_real_regression_is_named_in_percentages(self):
        line = verdict(STEADY_OLD, STEADY_BAD, threshold_percent=5)
        assert line.startswith("REGRESSION parse: 8.0%")
        assert "this is signal" in line

    def test_a_small_drift_is_inside_the_threshold(self):
        drift = Bench(name="parse", samples=(102, 103, 101, 102))
        line = verdict(STEADY_OLD, drift, threshold_percent=5)
        assert "inside the threshold, not actionable" in line

    def test_an_improvement_reads_as_no_regression(self):
        faster = Bench(name="parse", samples=(95, 96, 94, 95))
        assert "no regression" in verdict(
            STEADY_OLD, faster, threshold_percent=5
        )

    def test_the_noisy_bench_declines_with_its_repairs(self):
        line = verdict(NOISY_OLD, NOISY_NEW, threshold_percent=5)
        assert "declines to gate: spread 16.0%" in line
        assert "more iterations or a quieter machine" in line

    def test_mismatched_benchmarks_are_refused(self):
        with pytest.raises(Invalid):
            verdict(STEADY_OLD, NOISY_NEW, threshold_percent=5)


class TestTheFleet:
    def test_the_fleet_report_counts_all_three_columns(self):
        report = fleet_report(
            [
                (STEADY_OLD, STEADY_BAD),
                (NOISY_OLD, NOISY_NEW),
            ],
            threshold_percent=5,
        )
        assert report.startswith(
            "1 benchmark(s) armed, 1 declined for noise, "
            "1 regression(s)"
        )

    def test_an_empty_fleet_is_refused(self):
        with pytest.raises(Invalid):
            fleet_report([], threshold_percent=5)
