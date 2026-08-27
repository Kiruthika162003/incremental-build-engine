from __future__ import annotations

import pytest

from forge.docdrill import drill, extract, report
from forge.errors import Invalid

GOOD_DOC = """Intro prose.

```
target app needs corelib
```

More prose.

``` no-check
pseudo-code here
```
"""

ROTTED_DOC = """Guide.

```
target app needs ghostlib
```
"""


def checker(body: str) -> str | None:
    if "ghostlib" in body:
        return "ghostlib is not a target anyone declares"
    return None


class TestExtraction:
    def test_samples_carry_their_doc_and_line(self):
        samples = extract("guide.md", GOOD_DOC)
        assert len(samples) == 2
        assert samples[0].line == 3
        assert samples[0].body == "target app needs corelib"

    def test_the_skip_tag_marks_the_sample_unchecked(self):
        samples = extract("guide.md", GOOD_DOC)
        assert samples[0].checked
        assert not samples[1].checked

    def test_an_unclosed_fence_is_refused(self):
        with pytest.raises(Invalid) as caught:
            extract("bad.md", "```\ndangling")
        assert "opened at line 1 and never closed" in str(
            caught.value
        )


class TestTheDrill:
    def test_rot_is_reported_by_file_and_line(self):
        rotted, checked, dodged = drill(
            {"guide.md": ROTTED_DOC}, checker
        )
        assert rotted == [
            "guide.md:3: ghostlib is not a target anyone declares"
        ]
        assert checked == 1
        assert dodged == 0

    def test_optouts_are_counted_not_hidden(self):
        _, checked, dodged = drill({"g.md": GOOD_DOC}, checker)
        assert (checked, dodged) == (1, 1)


class TestTheReport:
    def test_a_healthy_doc_reads_clean(self):
        page = report({"g.md": GOOD_DOC}, checker)
        assert page.startswith(
            "1 sample(s) checked, 0 rotted, 1 opted out"
        )

    def test_a_dodging_doc_is_called_out(self):
        dodgy = "```no-check\na\n```\n\n``` no-check\nb\n```\n"
        page = report({"d.md": dodgy}, checker)
        assert "they dodged it" in page

    def test_promising_nothing_is_its_own_verdict(self):
        assert report({"empty.md": "prose only"}, checker) == (
            "no samples found; the docs promise nothing"
        )

    def test_no_documents_is_refused(self):
        with pytest.raises(Invalid):
            report({}, checker)
