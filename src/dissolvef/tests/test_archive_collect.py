import tempfile
from pathlib import Path

from dissolvef.archive import collect_single_archive_paths


def test_collect_single_archive_paths_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 符合条件：仅一个压缩包
        folder_ok = root / "series_a"
        folder_ok.mkdir()
        archive_ok = folder_ok / "series_a.zip"
        archive_ok.write_text("zip")

        # 不符合条件：包含额外文件
        folder_extra = root / "series_b"
        folder_extra.mkdir()
        (folder_extra / "series_b.zip").write_text("zip")
        (folder_extra / "readme.txt").write_text("extra")

        paths, skipped, sim_skipped = collect_single_archive_paths(
            root,
            protect_first_level=False,
        )

        assert skipped >= 0
        assert sim_skipped == 0
        assert [str(p) for p in paths] == [str(archive_ok.resolve())]


def test_collect_single_archive_paths_with_similarity_filter():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        folder = root / "alpha"
        folder.mkdir()
        archive = folder / "beta.zip"
        archive.write_text("zip")

        paths, _, sim_skipped = collect_single_archive_paths(
            root,
            similarity_threshold=0.9,
            protect_first_level=False,
        )

        assert paths == []
        assert sim_skipped == 1


def test_collect_single_archive_paths_skip_blacklist():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 命中默认黑名单关键词“画集”
        folder = root / "画集_sample"
        folder.mkdir()
        archive = folder / "画集_sample.zip"
        archive.write_text("zip")

        paths_without_skip, skipped_without_skip, _ = collect_single_archive_paths(
            root,
            protect_first_level=False,
            skip_blacklist=False,
        )
        assert paths_without_skip == []
        assert skipped_without_skip >= 1

        paths_with_skip, skipped_with_skip, _ = collect_single_archive_paths(
            root,
            protect_first_level=False,
            skip_blacklist=True,
        )
        assert [str(p) for p in paths_with_skip] == [str(archive.resolve())]
        assert skipped_with_skip == 0
