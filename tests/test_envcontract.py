from __future__ import annotations

import pytest

from forge.envcontract import (
    ContractedEnv,
    EnvContract,
    influence_scan,
    migration_advice,
    run_contracted,
)
from forge.errors import Hermetic, Invalid

CONTRACT = EnvContract(
    declared=(("CC", "gcc-12"), ("LANG", "C.UTF-8"))
)


class TestTheContract:
    def test_declared_variables_are_served(self):
        env = ContractedEnv(CONTRACT)
        assert env.get("CC") == "gcc-12"

    def test_the_undeclared_read_fails_at_the_crime(self):
        env = ContractedEnv(CONTRACT)
        with pytest.raises(Hermetic, match="never declared"):
            env.get("HOME")

    def test_the_key_moves_with_the_values(self):
        changed = EnvContract(
            declared=(("CC", "gcc-13"), ("LANG", "C.UTF-8"))
        )
        assert CONTRACT.key_fold() != changed.key_fold()

    def test_declaration_order_does_not_move_the_key(self):
        reordered = EnvContract(
            declared=(("LANG", "C.UTF-8"), ("CC", "gcc-12"))
        )
        assert CONTRACT.key_fold() == reordered.key_fold()

    def test_unread_declarations_are_reported(self):
        def rule(env: ContractedEnv) -> str:
            return f"compiled with {env.get('CC')}"

        output, unread = run_contracted(rule, CONTRACT)
        assert output == "compiled with gcc-12"
        assert unread == ["LANG"]


class TestTheScan:
    def ambient_rule(self, env: dict) -> str:
        return f"built by {env['CC']} on {env.get('HOSTNAME', 'any')}"

    def test_influential_variables_are_found(self):
        ambient = {
            "CC": "gcc-12",
            "HOSTNAME": "ci-3",
            "UNUSED_TOKEN": "abc",
        }
        assert influence_scan(self.ambient_rule, ambient) == [
            "CC",
            "HOSTNAME",
        ]

    def test_the_advice_splits_declare_from_ignore(self):
        ambient = {
            "CC": "gcc-12",
            "HOSTNAME": "ci-3",
            "UNUSED_TOKEN": "abc",
        }
        advice = migration_advice(self.ambient_rule, ambient)
        assert advice == (
            "declare ['CC', 'HOSTNAME']; leave ['UNUSED_TOKEN'] out "
            "of the key, they never influenced the output"
        )

    def test_an_empty_environment_is_refused(self):
        with pytest.raises(Invalid):
            influence_scan(self.ambient_rule, {})
