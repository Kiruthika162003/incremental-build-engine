from __future__ import annotations

from examples import firstproject


class TestFirstProject:
    def test_the_three_builds_tell_the_story(self, capsys):
        assert firstproject.main() == 0
        out = capsys.readouterr().out
        assert "cold:  app: 8 visited, 5 ran, 0 from cache" in out
        assert "warm:  app: 8 visited, 0 ran, 5 from cache" in out
        assert "edit:  app: 8 visited, 3 ran, 2 from cache" in out
        assert "main.o untouched" in out
        assert "7 hits, 8 misses (47%)" in out
