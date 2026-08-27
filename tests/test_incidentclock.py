from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.incidentclock import Incident, fleet_report

SLOW_FIND = Incident(
    name="INC-441",
    began=0,
    detected=180,
    mitigated=195,
    repaired=206,
)
QUICK = Incident(
    name="INC-442",
    began=300,
    detected=305,
    mitigated=330,
    repaired=340,
)


class TestOneIncident:
    def test_the_story_splits_the_three_clocks(self):
        story = SLOW_FIND.story()
        assert (
            "206 tick(s) total; detection 180, mitigation 15, "
            "repair 11"
        ) in story
        assert "detection dominated" in story

    def test_disordered_clocks_are_refused(self):
        with pytest.raises(Invalid):
            Incident(
                name="x",
                began=10,
                detected=5,
                mitigated=20,
                repaired=30,
            )


class TestTheFleet:
    def test_the_dominant_phase_gets_the_prescription(self):
        report = fleet_report([SLOW_FIND, QUICK])
        assert report.startswith("2 incident(s), 246 tick(s)")
        assert "detection: 185 (75%)" in report
        assert "the investment belongs in monitoring" in report
        assert "the wrong sport" in report

    def test_a_balanced_fleet_gets_no_sermon(self):
        balanced = Incident(
            name="even",
            began=0,
            detected=10,
            mitigated=20,
            repaired=30,
        )
        report = fleet_report([balanced])
        assert "wrong sport" not in report

    def test_no_incidents_is_refused_with_a_smile(self):
        with pytest.raises(Invalid) as caught:
            fleet_report([])
        assert "enjoy it while it lasts" in str(caught.value)
