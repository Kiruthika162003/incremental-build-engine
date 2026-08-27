from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.publishgate import PublishGate

FACE_V1 = {"parse": "(text) -> Tree"}
FACE_V2 = {"parse": "(text) -> Tree", "walk": "(tree) -> Iter"}

CLEAN = {
    "proposed_bump": "minor",
    "before_face": FACE_V1,
    "after_face": FACE_V2,
    "changelog_versions": ("3.1.0", "3.0.0"),
    "notice_current": True,
    "stale_patches": (),
    "rotted_samples": 0,
}


def gate() -> PublishGate:
    return PublishGate()


class TestTheClerks:
    def test_five_signatures_publish_the_version(self):
        verdict = gate().publish("3.1.0", **CLEAN)
        assert verdict == (
            "3.1.0 published with 5 signature(s) on record"
        )

    def test_all_refusals_arrive_at_once(self):
        facts = dict(
            CLEAN,
            proposed_bump="patch",
            changelog_versions=("3.0.0",),
            rotted_samples=2,
        )
        with pytest.raises(Invalid) as caught:
            gate().publish("3.1.0", **facts)
        message = str(caught.value)
        assert "refused by 3 clerk(s), all reported at once" in (
            message
        )
        assert "the diff demands minor" in message
        assert "no entry for 3.1.0" in message
        assert "2 sample(s) no longer compile" in message

    def test_stale_patches_block_the_vendor_clerk(self):
        facts = dict(CLEAN, stale_patches=("win32-workaround",))
        with pytest.raises(Invalid) as caught:
            gate().publish("3.1.0", **facts)
        assert "win32-workaround still ride the old base" in (
            str(caught.value)
        )

    def test_republishing_is_refused(self):
        chosen = gate()
        chosen.publish("3.1.0", **CLEAN)
        with pytest.raises(Invalid):
            chosen.publish("3.1.0", **CLEAN)


class TestTheTrail:
    def test_the_trail_answers_was_it_checked(self):
        chosen = gate()
        chosen.publish("3.1.0", **CLEAN)
        assert chosen.audit_trail("3.1.0") == (
            "3.1.0: signed by version, changelog, attribution, "
            "vendor, docs"
        )

    def test_the_bypass_is_recorded_not_hidden(self):
        chosen = gate()
        chosen.bypass("3.1.1", reason="prod down, CVE fix")
        assert chosen.audit_trail("3.1.1") == (
            "3.1.1: BYPASSED (prod down, CVE fix)"
        )

    def test_a_reasonless_bypass_is_a_habit_starting(self):
        with pytest.raises(Invalid):
            gate().bypass("3.1.1", reason=" ")

    def test_an_unpublished_version_has_no_trail(self):
        with pytest.raises(Invalid):
            gate().audit_trail("9.9.9")
