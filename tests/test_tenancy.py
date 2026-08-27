from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.tenancy import (
    Workload,
    price_private,
    price_salted,
    price_shared,
    signature_page,
)

LOAD = Workload(
    common_public_units=50,
    common_private_units=10,
    unique_units_per_tenant=20,
    ticks_per_unit=10,
)


class TestTheThreePolicies:
    def test_shared_builds_everything_once(self):
        ticks, note = price_shared(LOAD)
        assert ticks == 1000
        assert "existence leak accepted in writing" in note

    def test_private_builds_the_commons_per_tenant(self):
        ticks, note = price_private(LOAD)
        assert ticks == 1600
        assert "once per tenant" in note

    def test_salted_rejoins_only_the_public_commons(self):
        ticks, note = price_salted(LOAD)
        assert ticks == 1100
        assert "bytes both already agree are public" in note

    def test_one_tenant_is_not_tenancy(self):
        with pytest.raises(Invalid):
            Workload(
                common_public_units=1,
                common_private_units=1,
                unique_units_per_tenant=1,
                ticks_per_unit=1,
                tenants=1,
            )


class TestTheSignaturePage:
    def test_the_page_prices_all_three_with_the_premium(self):
        page = signature_page(LOAD)
        assert page.startswith(
            "a decision for a signature, not a default:"
        )
        assert "shared: 1000 tick(s)" in page
        assert "salted: 1100 tick(s)" in page
        assert "private: 1600 tick(s)" in page
        assert "isolation premium: 600 tick(s)" in page
        assert "the salted compromise recovers 500 of it" in page
