from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.semver import advise, next_version, release_note

V1 = {"parse": "(text) -> Tree", "render": "(tree) -> str"}


class TestAdvice:
    def test_a_removal_is_major_and_named(self):
        advice = advise(V1, {"render": "(tree) -> str"})
        assert advice.bump == "major"
        assert advice.line() == "major, due to remove(parse)"

    def test_a_signature_change_is_major(self):
        after = dict(V1, parse="(text, strict) -> Tree")
        assert advise(V1, after).bump == "major"
        assert "change(parse)" in advise(V1, after).reasons

    def test_an_addition_is_minor(self):
        after = dict(V1, walk="(tree) -> Iterator")
        advice = advise(V1, after)
        assert advice.bump == "minor"
        assert advice.reasons == ("add(walk)",)

    def test_a_violent_internal_release_is_a_patch(self):
        advice = advise(V1, dict(V1))
        assert advice.bump == "patch"
        assert "internals do not version" in advice.line()

    def test_a_removal_outranks_an_addition(self):
        after = {"render": "(tree) -> str", "walk": "() -> None"}
        advice = advise(V1, after)
        assert advice.bump == "major"
        assert "remove(parse)" in advice.reasons
        assert "add(walk)" in advice.reasons


class TestNextVersion:
    def test_major_resets_the_lower_digits(self):
        assert next_version(
            (2, 4, 7), V1, {"render": "(tree) -> str"}
        ) == (3, 0, 0)

    def test_minor_resets_only_the_patch(self):
        after = dict(V1, walk="() -> None")
        assert next_version((2, 4, 7), V1, after) == (2, 5, 0)

    def test_a_patch_increments_in_place(self):
        assert next_version((2, 4, 7), V1, dict(V1)) == (2, 4, 8)

    def test_overshooting_the_required_bump_is_allowed(self):
        assert next_version(
            (2, 4, 7), V1, dict(V1), proposed_bump="major"
        ) == (3, 0, 0)

    def test_downgrading_the_required_bump_is_refused(self):
        with pytest.raises(Invalid) as caught:
            next_version(
                (2, 4, 7),
                V1,
                {"render": "(tree) -> str"},
                proposed_bump="minor",
            )
        assert "broken promise with a changelog" in str(caught.value)

    def test_an_unknown_bump_kind_is_refused(self):
        with pytest.raises(Invalid):
            next_version(
                (1, 0, 0), V1, dict(V1), proposed_bump="cosmic"
            )


class TestTheNote:
    def test_the_note_carries_version_and_reasons(self):
        note = release_note(
            (2, 4, 7), V1, {"render": "(tree) -> str"}
        )
        assert note == "3.0.0 (major, due to remove(parse))"
