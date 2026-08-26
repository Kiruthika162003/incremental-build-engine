from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.lockfile import (
    Available,
    Registry,
    audit_lock,
    install,
    resolve,
)


def registry() -> Registry:
    reg = Registry()
    reg.publish(Available("json", (1, 0), "json one point oh"))
    reg.publish(Available("json", (1, 4), "json one point four"))
    reg.publish(Available("json", (2, 0), "json two"))
    reg.publish(Available("http", (3, 1), "http three one"))
    return reg


MANIFEST = {
    "json": ((1, 0), (2, 0)),
    "http": ((3, 0), (4, 0)),
}


class TestResolution:
    def test_the_newest_inside_the_range_wins(self):
        lock = resolve(MANIFEST, registry())
        assert lock["json"].version == (1, 4)
        assert lock["http"].version == (3, 1)

    def test_an_unsatisfiable_range_is_named(self):
        with pytest.raises(Missing, match="nothing satisfies"):
            resolve({"json": ((9, 0), (10, 0))}, registry())

    def test_republishing_a_version_is_refused(self):
        reg = registry()
        with pytest.raises(Invalid, match="immutable"):
            reg.publish(Available("json", (1, 4), "different bytes"))


class TestInstallation:
    def test_the_lock_installs_the_same_bytes_forever(self):
        lock = resolve(MANIFEST, registry())
        first = install(lock, registry())
        second = install(lock, registry())
        assert first == second
        assert first["json"] == "json one point four"

    def test_a_new_release_does_not_move_the_install(self):
        reg = registry()
        lock = resolve(MANIFEST, reg)
        reg.publish(Available("json", (1, 9), "json one point nine"))
        installed = install(lock, reg)
        assert installed["json"] == "json one point four"

    def test_tampered_bytes_stop_the_install(self):
        reg = registry()
        lock = resolve(MANIFEST, reg)
        reg.packages["json"] = [
            Available("json", (1, 4), "poisoned payload"),
            *[
                held
                for held in reg.packages["json"]
                if held.version != (1, 4)
            ],
        ]
        with pytest.raises(Invalid, match="either way a stop"):
            install(lock, reg)

    def test_a_vanished_version_is_named(self):
        reg = registry()
        lock = resolve(MANIFEST, reg)
        reg.packages["http"] = []
        with pytest.raises(Missing, match="vanished"):
            install(lock, reg)


class TestTheAudit:
    def test_a_clean_lock_has_no_complaints(self):
        lock = resolve(MANIFEST, registry())
        assert audit_lock(MANIFEST, lock) == []

    def test_the_three_betrayals_are_named(self):
        lock = resolve(MANIFEST, registry())
        grown = dict(MANIFEST)
        grown["yaml"] = ((1, 0), (2, 0))
        del grown["http"]
        complaints = audit_lock(grown, lock)
        assert "yaml: in the manifest, never resolved" in complaints
        assert "http: locked but no longer wanted" in complaints

    def test_a_narrowed_range_exposes_the_stale_pick(self):
        lock = resolve(MANIFEST, registry())
        narrowed = dict(MANIFEST)
        narrowed["json"] = ((1, 5), (2, 0))
        complaints = audit_lock(narrowed, lock)
        assert complaints == [
            "json: locked at (1, 4), outside [(1, 5), (2, 0))"
        ]
