from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.inputnorm import (
    canonical_text,
    normalized_digest,
    platform_agreement,
    raw_split_cost,
)

LINUX = b"int main() {\n  return 0;\n}\n"
WINDOWS = b"int main() {\r\n  return 0;\r\n}\r\n"
OLD_MAC = b"int main() {\r  return 0;\r}\r"
WITH_BOM = b"\xef\xbb\xbf" + LINUX


class TestCanonicalForm:
    def test_all_three_line_ending_families_converge(self):
        assert canonical_text(WINDOWS) == LINUX
        assert canonical_text(OLD_MAC) == LINUX

    def test_the_bom_is_stripped(self):
        assert canonical_text(WITH_BOM) == LINUX

    def test_a_missing_final_newline_is_added(self):
        assert canonical_text(b"x").endswith(b"\n")

    def test_empty_stays_empty(self):
        assert canonical_text(b"") == b""


class TestDigesting:
    def test_windows_and_linux_checkouts_share_a_digest(self):
        assert normalized_digest(
            "main.c", WINDOWS
        ) == normalized_digest("main.c", LINUX)

    def test_binaries_digest_raw(self):
        png = b"\x89PNG\x00\r\n\x1a"
        assert normalized_digest("logo.png", png) != (
            normalized_digest(
                "logo.png", png.replace(b"\r\n", b"\n")
            )
        )

    def test_a_text_file_with_nul_bytes_is_named_a_lie(self):
        with pytest.raises(Invalid) as caught:
            normalized_digest("data.txt", b"abc\x00def")
        assert "poisons the cache quietly" in str(caught.value)


class TestAgreement:
    def test_the_fleet_agrees_after_normalization(self):
        verdict = platform_agreement(
            "main.c",
            {"linux-ci": LINUX, "win-dev": WINDOWS, "mac-old": OLD_MAC},
        )
        assert "3 checkout(s) agree" in verdict

    def test_real_drift_is_not_blamed_on_line_endings(self):
        verdict = platform_agreement(
            "main.c",
            {"linux-ci": LINUX, "win-dev": b"int main() { return 9; }\r\n"},
        )
        assert "content drift, not line endings" in verdict
        assert "linux-ci:" in verdict

    def test_one_checkout_cannot_agree_with_itself(self):
        with pytest.raises(Invalid):
            platform_agreement("main.c", {"solo": LINUX})


class TestTheSplitCost:
    def test_normalization_heals_the_three_way_split(self):
        report = raw_split_cost(
            "main.c",
            {"a": LINUX, "b": WINDOWS, "c": OLD_MAC},
        )
        assert "split the cache 3 way(s)" in report
        assert "heals 2 split(s)" in report
