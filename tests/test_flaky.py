from __future__ import annotations

import pytest

from forge.actions import Action
from forge.errors import Invalid
from forge.flaky import Certifier, probe
from forge.workspace import Workspace


def steady_action() -> Action:
    def rule(tree) -> None:
        tree.write_text("out.o", f"obj({tree.read_text('in.c')})")

    return Action(
        name="steady",
        command="cc",
        reads=("in.c",),
        writes=("out.o",),
        rule=rule,
    )


def stamping_action() -> Action:
    ticks = [0]

    def rule(tree) -> None:
        ticks[0] += 1
        tree.write_text(
            "out.o", f"obj({tree.read_text('in.c')})@{ticks[0]}"
        )

    return Action(
        name="stamper",
        command="cc -DSTAMP",
        reads=("in.c",),
        writes=("out.o",),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("in.c", "int x;")
    return tree


class TestProbing:
    def test_identical_bytes_twice_earn_the_certificate(self):
        verdict = probe(steady_action(), world())
        assert verdict.deterministic
        assert verdict.line() == "steady: certified deterministic"

    def test_a_timestamp_is_caught_by_the_second_run(self):
        verdict = probe(stamping_action(), world())
        assert not verdict.deterministic
        assert verdict.differing == ("out.o",)
        assert "FLAKY" in verdict.line()

    def test_the_probe_does_not_touch_the_real_tree(self):
        tree = world()
        probe(steady_action(), tree)
        assert not tree.exists("out.o")
        assert tree.touch_counts("in.c") == (0, 1)


class TestTheCertifier:
    def test_certificates_are_cached_per_command(self):
        certifier = Certifier()
        certifier.certify(steady_action(), world())
        certifier.certify(steady_action(), world())
        assert certifier.probes_run == 1

    def test_the_cache_may_believe_only_the_certified(self):
        certifier = Certifier()
        assert not certifier.believable(steady_action())
        certifier.certify(steady_action(), world())
        assert certifier.believable(steady_action())
        certifier.certify(stamping_action(), world())
        assert not certifier.believable(stamping_action())

    def test_flaky_rules_are_listed_by_name(self):
        certifier = Certifier()
        certifier.certify(steady_action(), world())
        certifier.certify(stamping_action(), world())
        assert certifier.flaky_rules() == ["stamper"]

    def test_a_changed_command_revokes_the_old_certificate(self):
        certifier = Certifier()
        certifier.certify(steady_action(), world())
        upgraded = Action(
            name="steady",
            command="cc -O3",
            reads=("in.c",),
            writes=("out.o",),
            rule=steady_action().rule,
        )
        certifier.revoke_on_command_change(upgraded)
        assert not certifier.believable(steady_action())

    def test_the_page_counts_the_flaky(self):
        certifier = Certifier()
        certifier.certify(steady_action(), world())
        certifier.certify(stamping_action(), world())
        page = certifier.registry_page()
        assert page.endswith("2 rules probed, 1 flaky")

    def test_an_empty_registry_refuses_to_report(self):
        with pytest.raises(Invalid):
            Certifier().registry_page()
