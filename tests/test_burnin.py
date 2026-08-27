from __future__ import annotations

import pytest

from forge.burnin import BurnInRig
from forge.errors import Invalid

KNOWN = {
    "compile:probe1": "digest-a",
    "compile:probe2": "digest-b",
    "link:probe3": "digest-c",
}


def honest_worker(_worker: str, probe: str) -> str:
    return KNOWN[probe]


def rig(run=honest_worker) -> BurnInRig:
    return BurnInRig(known_digests=dict(KNOWN), run_probe=run)


class TestAdmission:
    def test_the_honest_machine_is_admitted(self):
        verdict = rig().evaluate("worker-9")
        assert verdict == (
            "worker-9 admitted after 3 probe(s) reproduced cold"
        )

    def test_one_wrong_answer_rejects_with_the_probe_named(self):
        def skewed(_worker, probe):
            if probe == "compile:probe2":
                return "wrong-bytes"
            return KNOWN[probe]

        chosen = rig(run=skewed)
        verdict = chosen.evaluate("worker-x")
        assert verdict.startswith(
            "worker-x REJECTED on compile:probe2"
        )
        assert "unmeasurable rate" in verdict

    def test_a_probeless_rig_is_refused(self):
        with pytest.raises(Invalid):
            BurnInRig(known_digests={}, run_probe=honest_worker)


class TestFlakyProbes:
    def test_a_probe_that_disagrees_with_itself_is_retired(self):
        answers = iter(["flaky-1", "flaky-2"])

        def unstable(_worker, probe):
            if probe == "link:probe3":
                return next(answers)
            return KNOWN[probe]

        chosen = rig(run=unstable)
        verdict = chosen.evaluate("worker-y")
        assert "admitted after 2 probe(s)" in verdict
        assert chosen.retired_probes == ["link:probe3"]

    def test_the_report_explains_the_retirement(self):
        answers = iter(["x", "y"])

        def unstable(_worker, probe):
            if probe == "compile:probe1":
                return next(answers)
            return KNOWN[probe]

        chosen = rig(run=unstable)
        chosen.evaluate("worker-z")
        report = chosen.rig_report()
        assert "1 admitted, 0 rejected, 1 probe(s) retired" in (
            report
        )
        assert (
            "disqualifies the probe, not the machine" in report
        )

    def test_a_retired_probe_stays_retired_for_the_next_worker(self):
        answers = iter(["x", "y"])

        def unstable(_worker, probe):
            if probe == "compile:probe1":
                return next(answers)
            return KNOWN[probe]

        chosen = rig(run=unstable)
        chosen.evaluate("worker-a")
        assert "admitted after 2 probe(s)" in chosen.evaluate(
            "worker-b"
        )
