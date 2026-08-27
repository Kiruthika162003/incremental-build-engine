from __future__ import annotations

import pytest

from forge.deltaship import DeltaShipper, Patch
from forge.errors import Invalid


def shipper() -> DeltaShipper:
    built = DeltaShipper(
        latest_digest="night0", full_bytes=10000
    )
    for night in range(1, 5):
        built.publish(f"night{night}", patch_bytes=120)
    return built


class TestPlanning:
    def test_a_current_receiver_ships_nothing(self):
        assert shipper().plan_for("night4") == (
            "up to date; ship nothing"
        )

    def test_a_short_chain_ships_patches_with_the_route(self):
        plan = shipper().plan_for("night2")
        assert plan.startswith("2 patch(es), 240 bytes")
        assert "night3 -> night4"[:6] in plan

    def test_past_the_budget_the_full_artifact_ships(self):
        plan = shipper().plan_for("night0")
        assert plan.startswith("full artifact (10000 bytes)")
        assert "4 patches exceed the chain budget of 3" in plan

    def test_an_unknown_base_gets_the_full_artifact(self):
        plan = shipper().plan_for("handmade-digest")
        assert "the receiver's base is unknown" in plan

    def test_a_heavy_chain_saves_nothing_and_says_so(self):
        heavy = DeltaShipper(
            latest_digest="v0", full_bytes=100
        )
        heavy.publish("v1", patch_bytes=90)
        heavy.publish("v2", patch_bytes=90)
        assert "saves nothing" in heavy.plan_for("v0")


class TestApplication:
    def test_the_wrong_base_is_refused_with_the_reason(self):
        patch = Patch(
            base_digest="night3",
            target_digest="night4",
            patch_bytes=120,
            full_bytes=10000,
        )
        with pytest.raises(Invalid) as caught:
            shipper().apply("night1", patch)
        assert "plausible corrupt binary" in str(caught.value)

    def test_the_right_base_advances_the_receiver(self):
        patch = Patch(
            base_digest="night3",
            target_digest="night4",
            patch_bytes=120,
            full_bytes=10000,
        )
        assert shipper().apply("night3", patch) == "night4"

    def test_republishing_the_same_digest_is_refused(self):
        with pytest.raises(Invalid):
            shipper().publish("night4", patch_bytes=1)


class TestTheLedger:
    def test_freight_saved_and_full_ships_are_both_counted(self):
        built = shipper()
        built.plan_for("night2")
        built.plan_for("night0")
        assert built.ledger() == (
            "9760 byte(s) of freight saved, 1 full ship(s)"
        )
