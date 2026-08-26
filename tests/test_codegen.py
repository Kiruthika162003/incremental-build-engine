from __future__ import annotations

import pytest

from forge.codegen import SchemaGenerator
from forge.errors import Invalid
from forge.workspace import Workspace

SCHEMA = """
type User
type Order
type Invoice
"""


def world(schema: str = SCHEMA) -> Workspace:
    tree = Workspace()
    tree.write_text("api.schema", schema)
    return tree


def generator() -> SchemaGenerator:
    return SchemaGenerator(schema_path="api.schema", out_dir="gen")


class TestTheFan:
    def test_the_fan_width_follows_the_schema(self):
        tree = world()
        receipt = generator().generate(tree)
        assert receipt.generated == [
            "gen/user.gen",
            "gen/order.gen",
            "gen/invoice.gen",
        ]
        assert tree.read_text("gen/user.gen").startswith("class User")

    def test_the_manifest_is_a_stable_output(self):
        tree = world()
        generator().generate(tree)
        assert generator().fan(tree) == [
            "gen/user.gen",
            "gen/order.gen",
            "gen/invoice.gen",
        ]

    def test_regeneration_is_all_unchanged(self):
        tree = world()
        generator().generate(tree)
        receipt = generator().generate(tree)
        assert receipt.generated == []
        assert len(receipt.unchanged) == 3
        assert receipt.line() == "0 generated, 3 unchanged, 0 swept"


class TestTheSweep:
    def test_a_deleted_type_takes_its_file_with_it(self):
        tree = world()
        generator().generate(tree)
        tree.write_text("api.schema", "type User\ntype Order\n")
        receipt = generator().generate(tree)
        assert receipt.swept == ["gen/invoice.gen"]
        assert not tree.exists("gen/invoice.gen")

    def test_the_manifest_forgets_the_swept(self):
        tree = world()
        generator().generate(tree)
        tree.write_text("api.schema", "type User\n")
        generator().generate(tree)
        assert generator().fan(tree) == ["gen/user.gen"]

    def test_a_renamed_type_is_a_sweep_plus_a_generate(self):
        tree = world(schema="type User\n")
        generator().generate(tree)
        tree.write_text("api.schema", "type Customer\n")
        receipt = generator().generate(tree)
        assert receipt.generated == ["gen/customer.gen"]
        assert receipt.swept == ["gen/user.gen"]


class TestRefusals:
    def test_an_empty_schema_is_a_mistake_upstream(self):
        tree = world(schema="just a comment\n")
        with pytest.raises(Invalid, match="mistake upstream"):
            generator().generate(tree)

    def test_a_doubled_type_is_refused(self):
        tree = world(schema="type User\ntype User\n")
        with pytest.raises(Invalid, match="declared twice"):
            generator().generate(tree)
