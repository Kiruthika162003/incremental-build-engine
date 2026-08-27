from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.licensecheck import (
    COPYLEFT,
    NOTICE,
    PERMISSIVE,
    License,
    LicenseGraph,
)

MIT = License(name="MIT", kind=PERMISSIVE)
APACHE = License(
    name="Apache-2.0",
    kind=NOTICE,
    attribution="This product includes software from the ASF.",
)
GPL = License(name="GPL-3.0", kind=COPYLEFT)


def shipping_app() -> LicenseGraph:
    graph = LicenseGraph()
    graph.declare("tlswrap", GPL)
    graph.declare("network", MIT, needs=("tlswrap",))
    graph.declare("json", APACHE)
    graph.declare("app", MIT, needs=("network", "json"))
    return graph


class TestDeclarations:
    def test_a_notice_license_must_carry_its_text(self):
        with pytest.raises(Invalid):
            License(name="BSD-attr", kind=NOTICE)

    def test_an_unknown_kind_is_refused(self):
        with pytest.raises(Invalid):
            License(name="odd", kind="handshake")

    def test_double_declaration_is_refused(self):
        graph = LicenseGraph()
        graph.declare("a", MIT)
        with pytest.raises(Invalid):
            graph.declare("a", MIT)

    def test_an_unlicensed_dependency_cannot_ship(self):
        graph = LicenseGraph()
        graph.declare("app", MIT, needs=("mystery",))
        with pytest.raises(Missing):
            graph.closure("app")


class TestTheCheck:
    def test_the_violation_is_a_path_not_a_verdict(self):
        graph = shipping_app()
        violations = graph.check("app", (PERMISSIVE, NOTICE))
        assert violations == [
            "app -> network -> tlswrap (GPL-3.0, copyleft)"
        ]

    def test_a_policy_that_allows_copyleft_passes(self):
        graph = shipping_app()
        assert graph.check(
            "app", (PERMISSIVE, NOTICE, COPYLEFT)
        ) == []

    def test_the_verdict_counts_the_closure_when_clean(self):
        graph = shipping_app()
        verdict = graph.verdict(
            "json", (PERMISSIVE, NOTICE)
        )
        assert verdict == (
            "json ships clean: 1 components, policy permissive/notice"
        )

    def test_the_failing_verdict_lists_every_path(self):
        graph = shipping_app()
        verdict = graph.verdict("app", (PERMISSIVE,))
        assert "2 violation(s)" in verdict
        assert "app -> json (Apache-2.0, notice)" in verdict
        assert "tlswrap (GPL-3.0, copyleft)" in verdict

    def test_an_unknown_policy_kind_is_refused(self):
        with pytest.raises(Invalid):
            shipping_app().check("app", ("vibes",))


class TestTheNoticeFile:
    def test_obligations_are_collected_once_and_sorted(self):
        graph = LicenseGraph()
        graph.declare("json", APACHE)
        graph.declare("yaml", APACHE)
        graph.declare(
            "zlib",
            License(
                name="Zlib-ack",
                kind=NOTICE,
                attribution="Compression by the zlib authors.",
            ),
        )
        graph.declare("app", MIT, needs=("json", "yaml", "zlib"))
        assert graph.notice_file("app") == (
            "Compression by the zlib authors.\n"
            "This product includes software from the ASF."
        )

    def test_a_permissive_closure_owes_nothing(self):
        graph = LicenseGraph()
        graph.declare("app", MIT)
        assert graph.notice_file("app") == (
            "no attribution obligations in the closure"
        )
