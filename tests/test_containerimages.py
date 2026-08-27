from __future__ import annotations

import pytest

from forge.containerimages import (
    ImageBuilder,
    Layer,
    advise,
    change_bill,
    expected_bill,
)
from forge.errors import Invalid

BASE = Layer(name="base", content="debian:12", build_cost=30)
DEPS = Layer(name="deps", content="apt install gcc", build_cost=60)
SRC = Layer(name="src", content="COPY . /app rev1", build_cost=10)

FREQUENCY = {"base": 1, "deps": 4, "src": 30}


class TestLayerCache:
    def test_the_first_build_builds_everything(self):
        builder = ImageBuilder()
        builder.build([BASE, DEPS, SRC])
        assert builder.rebuilds == 3

    def test_the_unchanged_stack_is_all_hits(self):
        builder = ImageBuilder()
        builder.build([BASE, DEPS, SRC])
        builder.build([BASE, DEPS, SRC])
        assert builder.layer_hits == 3

    def test_a_changed_layer_invalidates_everything_above(self):
        builder = ImageBuilder()
        builder.build([BASE, DEPS, SRC])
        newdeps = Layer(
            name="deps", content="apt install gcc g++", build_cost=60
        )
        builder.build([BASE, newdeps, SRC])
        assert builder.rebuilds == 5
        assert builder.layer_hits == 1

    def test_an_empty_stack_is_refused(self):
        with pytest.raises(Invalid):
            ImageBuilder().build([])


class TestTheBill:
    def test_a_change_pays_for_itself_and_everything_above(self):
        stack = [BASE, DEPS, SRC]
        assert change_bill(stack, 0) == 100
        assert change_bill(stack, 2) == 10

    def test_the_classic_mistake_priced(self):
        good = [BASE, DEPS, SRC]
        bad = [BASE, SRC, DEPS]
        assert expected_bill(good, FREQUENCY) == 680
        assert expected_bill(bad, FREQUENCY) == 2440

    def test_out_of_range_layers_are_refused(self):
        with pytest.raises(Invalid):
            change_bill([BASE], 5)


class TestTheAdvisor:
    def test_the_optimal_stack_is_left_alone(self):
        verdict = advise([BASE, DEPS, SRC], FREQUENCY)
        assert verdict.startswith("the stack is optimal at 680")

    def test_the_reorder_comes_with_both_bills(self):
        verdict = advise([BASE, SRC, DEPS], FREQUENCY)
        assert "2440 ticks per period becomes 680" in verdict
        assert "a saving of 1760" in verdict
        assert "base -> deps -> src" in verdict
