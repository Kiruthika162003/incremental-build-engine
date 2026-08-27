from __future__ import annotations

import pytest

from forge.cli import main


class TestCli:
    def test_audits_prints_the_page(self, capsys):
        assert main(["audits"]) == 0
        out = capsys.readouterr().out
        assert "cutoffworth:" in out
        assert "0 broken" in out

    def test_check_passes_while_everything_holds(self, capsys):
        assert main(["check"]) == 0
        assert "all audits hold" in capsys.readouterr().out

    def test_a_command_is_required(self):
        with pytest.raises(SystemExit):
            main([])

    def test_summary_is_one_honest_line(self, capsys):
        assert main(["summary"]) == 0
        assert "audits (0 broken)" in capsys.readouterr().out
