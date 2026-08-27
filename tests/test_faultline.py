from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.faultline import FaultLineReport
from forge.workermatch import Pool

LINUX_A = Pool(
    name="linux-a", offers=(("os", "linux"),), slots=20
)
LINUX_B = Pool(
    name="linux-b", offers=(("os", "linux"),), slots=20
)
MAC_SIGN = Pool(
    name="mac-sign",
    offers=(("os", "mac"), ("signing", "yes")),
    slots=2,
)

DEMAND = {
    "compile": {"os": "linux"},
    "release-sign": {"os": "mac", "signing": "yes"},
}


def farm() -> FaultLineReport:
    return FaultLineReport(
        pools=[LINUX_A, LINUX_B, MAC_SIGN],
        demand_classes=dict(DEMAND),
    )


class TestSubtraction:
    def test_a_twinned_pool_is_capacity(self):
        assert farm().stranded_by("linux-a") == []

    def test_the_singleton_pool_is_a_fault_line(self):
        assert farm().stranded_by("mac-sign") == ["release-sign"]

    def test_a_stranger_pool_is_refused(self):
        with pytest.raises(Invalid):
            farm().stranded_by("ghost")


class TestTheReport:
    def test_the_fault_line_is_ranked_first_with_its_fix(self):
        report = farm().report()
        assert report.startswith(
            "the fault line is mac-sign: losing it strands "
            "release-sign"
        )
        assert (
            "a second pool with mac-sign's properties" in report
        )
        assert "  linux-a: capacity" in report
        assert "most necessary pool, not as its average one" in (
            report
        )

    def test_a_fully_twinned_farm_earns_the_verdict(self):
        report = FaultLineReport(
            pools=[LINUX_A, LINUX_B],
            demand_classes={"compile": {"os": "linux"}},
        ).report()
        assert report.startswith(
            "no single pool loss strands anything"
        )

    def test_no_demand_is_refused(self):
        with pytest.raises(Invalid):
            FaultLineReport(
                pools=[LINUX_A], demand_classes={}
            ).report()
