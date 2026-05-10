"""Tests for classf pipeline."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


class TestInferCommonParent:
    def test_single_path(self):
        from classf.__main__ import _infer_common_parent

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.touch()
            result = _infer_common_parent([str(test_file)])
            assert result == Path(tmpdir)

    def test_multiple_paths_same_parent(self):
        from classf.__main__ import _infer_common_parent

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            file1.touch()
            file2.touch()
            result = _infer_common_parent([str(file1), str(file2)])
            assert result == Path(tmpdir)

    def test_multiple_paths_different_parents(self):
        from classf.__main__ import _infer_common_parent

        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "dir1"
            dir2 = Path(tmpdir) / "dir2"
            dir1.mkdir()
            dir2.mkdir()
            file1 = dir1 / "file1.txt"
            file2 = dir2 / "file2.txt"
            file1.touch()
            file2.touch()
            result = _infer_common_parent([str(file1), str(file2)])
            assert result is None

    def test_empty_paths(self):
        from classf.__main__ import _infer_common_parent

        result = _infer_common_parent([])
        assert result is None


class TestMigrateDirectClassify:
    def test_classify_only_creates_already_dir(self):
        from classf.__main__ import _migrate_direct

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            source_dir = base / "source"
            source_dir.mkdir()
            test_file = source_dir / "test.txt"
            test_file.write_text("test content")

            _migrate_direct(
                [str(test_file)],
                target_dir=None,
                action="move",
                existing_dir="merge",
                classify="only",
            )

            already_dir = source_dir / "already"
            assert already_dir.exists()
            assert (already_dir / "test.txt").exists()
            assert not test_file.exists()

    def test_classify_auto_creates_already_and_wait(self):
        from classf.__main__ import _migrate_direct

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            source_dir = base / "source"
            source_dir.mkdir()

            file_to_move = source_dir / "move_me.txt"
            file_to_move.write_text("content")
            other_file = source_dir / "other.txt"
            other_file.write_text("other content")

            _migrate_direct(
                [str(file_to_move)],
                target_dir=None,
                action="move",
                existing_dir="merge",
                classify="auto",
            )

            already_dir = source_dir / "already"
            wait_dir = source_dir / "wait"

            assert already_dir.exists()
            assert (already_dir / "move_me.txt").exists()
            assert not file_to_move.exists()

            assert wait_dir.exists()
            assert (wait_dir / "other.txt").exists()
            assert not other_file.exists()

    def test_classify_only_with_explicit_target(self):
        from classf.__main__ import _migrate_direct

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            source_dir = base / "source"
            source_dir.mkdir()
            target_dir = base / "target"
            target_dir.mkdir()

            test_file = source_dir / "test.txt"
            test_file.write_text("test content")

            _migrate_direct(
                [str(test_file)],
                target_dir=str(target_dir),
                action="move",
                existing_dir="merge",
                classify="only",
            )

            assert (target_dir / "test.txt").exists()
            assert not test_file.exists()

    def test_classify_off_requires_target(self):
        from classf.__main__ import _migrate_direct
        import typer

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "test.txt"
            test_file.write_text("content")

            with pytest.raises(typer.Exit):
                _migrate_direct(
                    [str(test_file)],
                    target_dir=None,
                    action="move",
                    existing_dir="merge",
                    classify="off",
                )


class TestMigratefCollectWaitCandidates:
    def test_collect_wait_candidates(self):
        from migratef.__main__ import _collect_wait_candidates

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            already_dir = base / "already"
            wait_dir = base / "wait"

            file1 = base / "file1.txt"
            file2 = base / "file2.txt"
            file1.write_text("1")
            file2.write_text("2")

            source_paths = [str(file1)]
            candidates = _collect_wait_candidates(base, source_paths, already_dir, wait_dir)

            assert str(file2) in candidates
            assert str(file1) not in candidates
