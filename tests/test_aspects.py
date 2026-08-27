from __future__ import annotations

import pytest

from forge.aspects import (
    Aspect,
    license_aspect,
    license_verdict,
    union_fold,
)
from forge.errors import Invalid
from forge.graph import Graph


def stack() -> Graph:
    graph = Graph()
    graph.declare("zlib")
    graph.declare("crypto")
    graph.declare("net", needs=("zlib", "crypto"))
    graph.declare("app", needs=("net",))
    return graph


LICENSES = {"zlib": "Zlib", "crypto": "Apache-2.0"}


class TestTheWalk:
    def test_answers_fold_up_the_graph(self):
        answers = license_aspect(LICENSES).walk(stack(), "app")
        assert answers["app"] == frozenset({"Zlib", "Apache-2.0"})

    def test_leaves_answer_for_themselves(self):
        answers = license_aspect(LICENSES).walk(stack(), "app")
        assert answers["zlib"] == frozenset({"Zlib"})

    def test_the_undeclared_contribute_nothing(self):
        answers = license_aspect(LICENSES).walk(stack(), "app")
        assert answers["net"] == frozenset({"Zlib", "Apache-2.0"})

    def test_a_sloppy_extractor_is_refused(self):
        aspect = Aspect(
            name="sloppy",
            extract=lambda target: {target},
            fold=union_fold,
        )
        with pytest.raises(Invalid, match="must return a frozenset"):
            aspect.walk(stack(), "app")

    def test_one_pass_answers_every_target(self):
        answers = license_aspect(LICENSES).walk(stack(), "app")
        assert set(answers) == {"zlib", "crypto", "net", "app"}


class TestTheLawyersQuestion:
    def test_a_shippable_mix_ships(self):
        answers = license_aspect(LICENSES).walk(stack(), "app")
        assert license_verdict(answers, "app") == (
            "app: ships ['Apache-2.0', 'Zlib']"
        )

    def test_the_forbidden_pair_is_refused_at_the_top(self):
        licenses = dict(
            LICENSES, zlib="GPL-3.0", crypto="proprietary"
        )
        answers = license_aspect(licenses).walk(stack(), "app")
        verdict = license_verdict(answers, "app")
        assert verdict.startswith("app: REFUSED")

    def test_a_bare_graph_declares_nothing(self):
        answers = license_aspect({}).walk(stack(), "app")
        assert license_verdict(answers, "app") == (
            "app: ships nothing declared"
        )
