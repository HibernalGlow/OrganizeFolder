"""Tests for synct file mode functionality"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from synct.core.extract_timestamp import extract_timestamp_from_name
from synct.core.file_mode import (
    archive_file,
    categorize_files,
    scan_files_for_timestamp,
)


class TestExtractTimestamp:
    """测试从文件名提取时间戳"""

    def test_yyyy_mm_dd_format(self):
        """测试 yyyy-mm-dd 格式"""
        result = extract_timestamp_from_name("2024-05-15_photo")
        assert result is not None
        assert result.year == 2024
        assert result.month == 5
        assert result.day == 15

    def test_yyyymmdd_format(self):
        """测试 yyyymmdd 格式"""
        result = extract_timestamp_from_name("20240315_document")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 15

    def test_yyyy_mm_format(self):
        """测试 yyyy-mm 格式"""
        result = extract_timestamp_from_name("2024-05_monthly_report")
        assert result is not None
        assert result.year == 2024
        assert result.month == 5

    def test_no_timestamp(self):
        """测试无时间戳的文件名"""
        result = extract_timestamp_from_name("random_filename")
        assert result is None

    def test_chinese_filename_with_date(self):
        """测试包含中文的文件名"""
        result = extract_timestamp_from_name("2024-01-01_新年照片")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1


class TestScanFilesForTimestamp:
    """测试文件扫描功能"""

    def test_scan_non_recursive(self, tmp_path):
        """测试非递归扫描"""
        # 创建测试文件
        (tmp_path / "2024-05-15_photo.jpg").touch()
        (tmp_path / "2024-06-20_doc.pdf").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "2024-07-01_nested.txt").touch()

        files = scan_files_for_timestamp(str(tmp_path), recursive=False)

        assert len(files) == 2
        filenames = [f[2] for f in files]
        assert "2024-05-15_photo.jpg" in filenames
        assert "2024-06-20_doc.pdf" in filenames
        assert "2024-07-01_nested.txt" not in filenames

    def test_scan_recursive(self, tmp_path):
        """测试递归扫描"""
        # 创建测试文件
        (tmp_path / "2024-05-15_photo.jpg").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "2024-07-01_nested.txt").touch()
        (tmp_path / "subdir" / "deep").mkdir()
        (tmp_path / "subdir" / "deep" / "2024-08-01_deep.txt").touch()

        files = scan_files_for_timestamp(str(tmp_path), recursive=True)

        assert len(files) == 3
        filenames = [f[2] for f in files]
        assert "2024-05-15_photo.jpg" in filenames
        assert "2024-07-01_nested.txt" in filenames
        assert "2024-08-01_deep.txt" in filenames

    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        files = scan_files_for_timestamp(str(tmp_path), recursive=False)
        assert len(files) == 0


class TestCategorizeFiles:
    """测试文件分类功能"""

    def test_categorize_single_layer(self, tmp_path):
        """测试单层格式分类"""
        files = [
            (str(tmp_path / "2024-05-15_photo.jpg"), datetime(2024, 5, 15), "2024-05-15_photo.jpg"),
            (str(tmp_path / "2024-06-20_doc.pdf"), datetime(2024, 6, 20), "2024-06-20_doc.pdf"),
        ]
        base_dst = str(tmp_path / "archive")

        operations = categorize_files(files, base_dst, "year_month")

        assert len(operations) == 2
        assert "2024-05" in operations[0]["destination"]
        assert "2024-06" in operations[1]["destination"]

    def test_categorize_multi_layer(self, tmp_path):
        """测试多层格式分类"""
        files = [
            (str(tmp_path / "2024-05-15_photo.jpg"), datetime(2024, 5, 15), "2024-05-15_photo.jpg"),
        ]
        base_dst = str(tmp_path / "archive")

        operations = categorize_files(files, base_dst, "nested_y_m")

        assert len(operations) == 1
        # 检查路径包含年和月的目录层级
        dst = operations[0]["destination"]
        assert "2024" in dst
        assert "05" in dst


class TestArchiveFile:
    """测试文件归档功能"""

    def test_archive_file_basic(self, tmp_path):
        """测试基本归档功能"""
        # 创建源文件
        src_file = tmp_path / "2024-05-15_photo.jpg"
        src_file.write_text("test content")
        base_dst = str(tmp_path / "archive")

        result = archive_file(
            str(src_file),
            datetime(2024, 5, 15),
            base_dst,
            "year_month"
        )

        assert os.path.exists(result)
        assert "2024-05" in result
        assert not os.path.exists(str(src_file))

    def test_archive_file_dry_run(self, tmp_path):
        """测试预览模式"""
        src_file = tmp_path / "test.jpg"
        src_file.write_text("test")
        base_dst = str(tmp_path / "archive")

        result = archive_file(
            str(src_file),
            datetime(2024, 5, 15),
            base_dst,
            "year_month",
            dry_run=True
        )

        # 源文件仍然存在
        assert os.path.exists(str(src_file))
        # 目标路径返回但不创建
        assert "2024-05" in result

    def test_archive_file_conflict_resolution(self, tmp_path):
        """测试同名文件冲突处理"""
        # 创建两个同名源文件
        src_file1 = tmp_path / "source1" / "test.jpg"
        src_file2 = tmp_path / "source2" / "test.jpg"
        src_file1.parent.mkdir(parents=True)
        src_file2.parent.mkdir(parents=True)
        src_file1.write_text("content1")
        src_file2.write_text("content2")

        base_dst = str(tmp_path / "archive")
        dt = datetime(2024, 5, 15)

        # 归档第一个文件
        result1 = archive_file(str(src_file1), dt, base_dst, "year_month")
        # 归档第二个同名文件
        result2 = archive_file(str(src_file2), dt, base_dst, "year_month")

        assert os.path.exists(result1)
        assert os.path.exists(result2)
        assert result1 != result2
        assert "_1" in os.path.basename(result2)


class TestIntegration:
    """端到端集成测试"""

    def test_full_workflow(self, tmp_path):
        """测试完整工作流程"""
        # 设置测试目录
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # 创建带时间戳的测试文件
        (source_dir / "2024-01-15_january.txt").write_text("january")
        (source_dir / "2024-02-20_february.txt").write_text("february")
        (source_dir / "2024-01-25_also_january.txt").write_text("also january")
        (source_dir / "no_date_file.txt").write_text("no date")

        # 扫描文件
        files = scan_files_for_timestamp(str(source_dir), recursive=False)
        assert len(files) == 4  # 包括无日期文件（使用创建时间）

        # 分类
        base_dst = str(tmp_path / "archive")
        operations = categorize_files(files, base_dst, "year_month")
        assert len(operations) == 4

        # 归档（只归档有明确日期的）
        for op in operations:
            if "2024-01" in op["rel_destination"] or "2024-02" in op["rel_destination"]:
                archive_file(op["source"], op["timestamp"], base_dst, "year_month")

        # 验证归档目录结构
        jan_dir = tmp_path / "archive" / "2024-01"
        feb_dir = tmp_path / "archive" / "2024-02"

        assert jan_dir.exists()
        assert feb_dir.exists()
        assert len(list(jan_dir.iterdir())) == 2  # 两个一月的文件
        assert len(list(feb_dir.iterdir())) == 1  # 一个二月的文件
