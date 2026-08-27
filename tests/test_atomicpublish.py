from __future__ import annotations

import pytest

from forge.atomicpublish import (
    PublishSim,
    contract_verdict,
    torn_states,
)
from forge.errors import Invalid

OLD = "version=1;payload=aaaa"
NEW = "version=2;payload=bbbb"


class TestTheTear:
    def test_in_place_writes_expose_torn_states(self):
        sim = PublishSim(files={"out.cfg": OLD})
        states = sim.write_in_place("out.cfg", NEW)
        assert torn_states(OLD, states)

    def test_the_verdict_names_the_tear(self):
        sim = PublishSim(files={"out.cfg": OLD})
        states = sim.write_in_place("out.cfg", NEW)
        verdict = contract_verdict(OLD, NEW, states)
        assert verdict.startswith("TORN:")


class TestTheAtomicPath:
    def test_readers_see_only_old_until_the_rename(self):
        sim = PublishSim(files={"out.cfg": OLD})
        states = sim.publish_atomic("out.cfg", NEW)
        assert set(states) == {OLD}
        assert sim.files["out.cfg"] == NEW

    def test_the_contract_verdict_is_clean(self):
        sim = PublishSim(files={"out.cfg": OLD})
        states = sim.publish_atomic("out.cfg", NEW)
        verdict = contract_verdict(OLD, NEW, [*states, NEW])
        assert verdict.startswith("atomic:")
        assert "never the truth in transit" in verdict

    def test_a_first_publish_has_no_old_bytes_to_show(self):
        sim = PublishSim()
        states = sim.publish_atomic("fresh.cfg", NEW)
        assert all(state is None for state in states)
        assert sim.files["fresh.cfg"] == NEW


class TestCrashRecovery:
    def test_the_sweep_names_the_stale_temp(self):
        sim = PublishSim(files={"out.cfg": OLD})
        sim.crash_during_publish("out.cfg", NEW)
        report = sim.sweep_temps()
        assert len(report) == 1
        assert report[0].startswith("out.cfg.tmp: removed")
        assert sim.files == {"out.cfg": OLD}

    def test_a_clean_tree_sweeps_nothing(self):
        assert PublishSim(files={"a": "x"}).sweep_temps() == []

    def test_no_observations_cannot_be_judged(self):
        with pytest.raises(Invalid):
            contract_verdict(OLD, NEW, [])
