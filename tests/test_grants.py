from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.grants import GrantLedger


def ledger() -> GrantLedger:
    built = GrantLedger()
    built.grant("fetch", ("network", "clock"))
    built.grant("compile", ("env",))
    return built


class TestGranting:
    def test_unknown_capabilities_are_refused(self):
        with pytest.raises(Invalid):
            GrantLedger().grant("odd", ("sunlight",))

    def test_regranting_is_a_review_not_a_regrant(self):
        chosen = ledger()
        with pytest.raises(Invalid):
            chosen.grant("fetch", ("network",))


class TestUse:
    def test_a_held_grant_is_exercised_quietly(self):
        chosen = ledger()
        assert chosen.use("fetch", "network") == (
            "fetch used network"
        )

    def test_escalation_is_refused_at_the_moment_of_use(self):
        chosen = ledger()
        with pytest.raises(Invalid) as caught:
            chosen.use("compile", "network")
        assert "refused at the moment of use" in str(caught.value)
        assert "a diary" in str(caught.value)
        assert chosen.refusals

    def test_an_ungranted_class_cannot_use_anything(self):
        with pytest.raises(Invalid):
            ledger().use("ghost", "clock")


class TestTheAudit:
    def test_unused_grants_are_named_for_revocation(self):
        chosen = ledger()
        chosen.use("fetch", "network")
        chosen.use("compile", "env")
        audit = chosen.revocation_audit()
        assert audit.startswith("1 class(es) hold unused grants")
        assert "  fetch: revoke clock" in audit

    def test_a_tight_ledger_matches_keys_to_locks(self):
        chosen = ledger()
        chosen.use("fetch", "network")
        chosen.use("fetch", "clock")
        chosen.use("compile", "env")
        assert chosen.revocation_audit() == (
            "every grant was exercised; the keys match the locks"
        )

    def test_the_copied_template_is_hypothesized(self):
        chosen = GrantLedger()
        for name in ("codegen", "docs", "protogen"):
            chosen.grant(name, ("network", "env"))
            chosen.use(name, "env")
        audit = chosen.revocation_audit()
        assert (
            "network is unused across 3 class(es): the "
            "copied-template hypothesis"
        ) in audit
