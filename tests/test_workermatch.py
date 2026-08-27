from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.workermatch import Matcher, Pool

LINUX = Pool(
    name="linux-x64",
    offers=(("os", "linux"), ("arch", "x64"), ("ram", "32g")),
    slots=40,
)
MAC = Pool(
    name="mac-arm",
    offers=(("os", "mac"), ("arch", "arm"), ("xcode", "14")),
    slots=6,
)


def farm() -> Matcher:
    matcher = Matcher()
    matcher.add_pool(LINUX)
    matcher.add_pool(MAC)
    return matcher


class TestMatching:
    def test_the_fitting_pool_with_the_most_slots_wins(self):
        assert farm().match({"os": "linux"}) == (
            "linux-x64 (40 slots)"
        )

    def test_full_demands_still_land(self):
        assert farm().match(
            {"os": "mac", "arch": "arm", "xcode": "14"}
        ) == "mac-arm (6 slots)"

    def test_an_empty_demand_takes_the_biggest_pool(self):
        assert farm().match({}) == "linux-x64 (40 slots)"


class TestTheExplainer:
    def test_the_near_miss_names_what_the_pool_lacks(self):
        with pytest.raises(Invalid) as caught:
            farm().match({"os": "mac", "xcode": "15"})
        message = str(caught.value)
        assert message.startswith("no pool matches")
        assert "mac-arm lacks xcode=15 (pool has 14)" in message

    def test_fantasy_keys_are_called_out_separately(self):
        with pytest.raises(Invalid) as caught:
            farm().match({"os": "linux", "gpu": "a100"})
        message = str(caught.value)
        assert "demanded keys no pool offers anywhere: gpu" in message
        assert "a demand nobody meant" in message

    def test_the_nearest_pool_is_listed_first(self):
        with pytest.raises(Invalid) as caught:
            farm().match({"os": "mac", "arch": "arm", "xcode": "15"})
        lines = str(caught.value).splitlines()
        assert lines[1].strip().startswith("mac-arm lacks")


class TestRegistration:
    def test_a_slotless_pool_is_a_memorial(self):
        with pytest.raises(Invalid):
            Matcher().add_pool(
                Pool(name="ghost", offers=(), slots=0)
            )

    def test_duplicate_pools_are_refused(self):
        matcher = farm()
        with pytest.raises(Invalid):
            matcher.add_pool(LINUX)

    def test_an_empty_farm_cannot_match(self):
        with pytest.raises(Invalid):
            Matcher().match({"os": "linux"})
