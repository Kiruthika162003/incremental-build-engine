from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.fetchplan import FetchPlan, Pin

ZLIB = Pin(name="zlib", version="1.3", digest="aabbccdd0011")
CURL = Pin(name="curl", version="8.5", digest="deadbeef4455")


def plan() -> FetchPlan:
    built = FetchPlan()
    built.add(ZLIB)
    built.add(CURL)
    return built


def full_mirror() -> dict[str, str]:
    return {
        ZLIB.mirror_path(): ZLIB.digest,
        CURL.mirror_path(): CURL.digest,
    }


class TestThePlan:
    def test_mirror_paths_carry_the_digest_prefix(self):
        assert ZLIB.mirror_path() == (
            "mirror/zlib/aabbccdd/zlib-1.3.tar"
        )

    def test_the_manifest_is_sorted_and_digested(self):
        lines = plan().manifest()
        assert lines[0].startswith("mirror/curl/deadbeef/")
        assert lines[0].endswith("sha256:deadbeef4455")
        assert lines[1].startswith("mirror/zlib/")

    def test_a_short_digest_is_not_worth_trusting(self):
        with pytest.raises(Invalid):
            Pin(name="x", version="1", digest="ab")

    def test_conflicting_pins_accuse_the_lockfile(self):
        built = plan()
        with pytest.raises(Invalid):
            built.add(
                Pin(name="zlib", version="1.4", digest="ffffffff")
            )

    def test_repinning_the_same_digest_is_idempotent(self):
        built = plan()
        built.add(ZLIB)
        assert len(built.pins) == 2


class TestVerification:
    def test_a_complete_mirror_is_ready(self):
        assert plan().verdict(full_mirror()) == (
            "the mirror is ready: 2 components verified"
        )

    def test_the_three_failure_lists_are_kept_apart(self):
        mirror = full_mirror()
        del mirror[ZLIB.mirror_path()]
        mirror[CURL.mirror_path()] = "0000000099"
        mirror["mirror/old/junk.tar"] = "1234"
        missing, corrupt, stray = plan().verify(mirror)
        assert missing == [ZLIB.mirror_path()]
        assert corrupt == [
            "mirror/curl/deadbeef/curl-8.5.tar "
            "expected deadbeef found 00000000"
        ]
        assert stray == ["mirror/old/junk.tar"]

    def test_strays_are_reported_but_do_not_block(self):
        mirror = full_mirror()
        mirror["mirror/old/junk.tar"] = "1234"
        verdict = plan().verdict(mirror)
        assert verdict.startswith("the mirror is ready")
        assert "1 stray file(s) rotting harmlessly" in verdict

    def test_missing_and_corrupt_stop_the_truck(self):
        mirror = full_mirror()
        del mirror[CURL.mirror_path()]
        verdict = plan().verdict(mirror)
        assert verdict.startswith("the truck cannot leave:")
        assert "missing: mirror/curl" in verdict
