from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.releasetrain import CherryPick, ReleaseTrain


def train() -> ReleaseTrain:
    return ReleaseTrain(version="24.3", cut_commit="c4412")


class TestPhases:
    def test_the_train_advances_through_its_phases(self):
        rolling = train()
        assert rolling.advance() == "24.3 enters stabilizing"
        assert rolling.advance() == "24.3 enters frozen"

    def test_frozen_is_the_last_phase(self):
        rolling = train()
        rolling.advance()
        rolling.advance()
        with pytest.raises(Invalid):
            rolling.advance()


class TestTheGate:
    def test_the_open_train_boards_with_one_approval(self):
        rolling = train()
        verdict = rolling.request(
            CherryPick(fix="fix-tls", approvals=1)
        )
        assert verdict == "fix-tls boards the 24.3 train"

    def test_stabilizing_demands_two_and_a_written_risk(self):
        rolling = train()
        rolling.advance()
        assert "wants two approvals, got 1" in rolling.request(
            CherryPick(fix="fix-a", approvals=1)
        )
        assert "written down, not remembered" in rolling.request(
            CherryPick(fix="fix-b", approvals=2)
        )
        assert "boards" in rolling.request(
            CherryPick(
                fix="fix-c",
                approvals=2,
                risk_note="touches the parser cache",
            )
        )

    def test_frozen_admits_only_the_showstopper(self):
        rolling = train()
        rolling.advance()
        rolling.advance()
        assert "takes the next train" in rolling.request(
            CherryPick(
                fix="nice-to-have",
                approvals=2,
                risk_note="small",
            )
        )
        assert "boards" in rolling.request(
            CherryPick(
                fix="data-loss-fix",
                approvals=2,
                showstopper=True,
            )
        )

    def test_zero_approvals_never_board_anywhere(self):
        assert "one approval" in train().request(
            CherryPick(fix="drive-by", approvals=0)
        )


class TestTheManifest:
    def test_the_manifest_is_the_release_note(self):
        rolling = train()
        rolling.request(CherryPick(fix="fix-tls", approvals=1))
        rolling.advance()
        rolling.request(
            CherryPick(
                fix="fix-parser",
                approvals=2,
                risk_note="cache shape",
            )
        )
        rolling.request(CherryPick(fix="rushed", approvals=1))
        manifest = rolling.manifest()
        assert "24.3 cut at c4412 (phase: stabilizing)" in manifest
        assert "boarded: 2" in manifest
        assert (
            "fix-parser boarded during stabilizing "
            "(risk: cache shape)"
        ) in manifest
        assert "turned away: 1" in manifest
        assert "rushed refused during stabilizing" in manifest
