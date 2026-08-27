from __future__ import annotations

import pytest

from forge.cacheproof import CacheProver
from forge.errors import Invalid

TRUTH = {f"compile:unit{number}": f"digest{number}" for number in range(30)}


def honest_rebuilder(key: str) -> str:
    return TRUTH[key]


def prover(percent: int = 100, rebuild=honest_rebuilder) -> CacheProver:
    return CacheProver(sample_percent=percent, rebuild=rebuild)


class TestSampling:
    def test_full_sampling_audits_every_hit(self):
        chosen = prover(100)
        for key, digest in TRUTH.items():
            chosen.audit_hit(key, digest, rebuild_ticks=5)
        assert chosen.sampled == len(TRUTH)
        assert chosen.agreed == len(TRUTH)

    def test_partial_sampling_trusts_most_hits(self):
        chosen = prover(10)
        verdicts = [
            chosen.audit_hit(key, digest, rebuild_ticks=5)
            for key, digest in TRUTH.items()
        ]
        assert verdicts.count("trusted") > 20
        assert chosen.sampled == len(TRUTH) - verdicts.count(
            "trusted"
        )

    def test_the_sample_is_deterministic(self):
        first = prover(30)
        second = prover(30)
        for key, digest in TRUTH.items():
            assert first.audit_hit(
                key, digest, 1
            ) == second.audit_hit(key, digest, 1)

    def test_a_zero_rate_is_refused(self):
        with pytest.raises(Invalid):
            prover(0)


class TestTheKeybug:
    def test_disagreement_names_the_action_and_both_digests(self):
        chosen = prover(
            100, rebuild=lambda _key: "the-real-bytes"
        )
        verdict = chosen.audit_hit(
            "compile:unit3", "stale-bytes", rebuild_ticks=9
        )
        assert verdict.startswith("KEYBUG compile:unit3")
        assert "cache served stale-by" in verdict
        assert "some input escaped the key" in verdict
        assert chosen.findings

    def test_agreement_is_quiet(self):
        chosen = prover(100)
        assert chosen.audit_hit(
            "compile:unit1", "digest1", rebuild_ticks=5
        ) == "verified"


class TestTheLedger:
    def test_the_clean_ledger_admits_its_limits(self):
        chosen = prover(100)
        for key, digest in TRUTH.items():
            chosen.audit_hit(key, digest, rebuild_ticks=2)
        ledger = chosen.ledger()
        assert "30 hit(s) sampled at 100%" in ledger
        assert "60 tick(s) spent" in ledger
        assert "confidence, not proof" in ledger

    def test_an_unsampled_ledger_says_so(self):
        assert "exactly what it was this morning" in (
            prover(1).ledger()
        )
