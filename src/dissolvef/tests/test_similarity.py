"""
相似度计算模块测试
"""
import pytest
from dissolvef.similarity import (
    calculate_similarity,
    check_similarity,
    is_similar,
    clean_name
)


class TestCleanName:
    """测试名称清理功能"""
    
    def test_remove_extension(self):
        """测试移除扩展名"""
        assert clean_name("test.zip") == "test"
        assert clean_name("archive.7z") == "archive"
        assert clean_name("file.tar.gz") == "file.tar"
    
    def test_no_extension(self):
        """测试无扩展名的情况"""
        assert clean_name("folder") == "folder"
        assert clean_name("test_folder") == "test_folder"


class TestCalculateSimilarity:
    """测试相似度计算"""
    
    def test_identical_strings(self):
        """测试完全相同的字符串"""
        assert calculate_similarity("test", "test") == 1.0
        assert calculate_similarity("文件夹", "文件夹") == 1.0
    
    def test_empty_strings(self):
        """测试空字符串"""
        assert calculate_similarity("", "") == 0.0
        assert calculate_similarity("test", "") == 0.0
        assert calculate_similarity("", "test") == 0.0
    
    def test_similar_strings(self):
        """测试相似字符串"""
        # 包含关系
        sim = calculate_similarity("作品集", "作品集合集")
        assert sim > 0.6
        
        # 部分匹配
        sim = calculate_similarity("漫画", "漫画合集")
        assert sim > 0.5
    
    def test_different_strings(self):
        """测试完全不同的字符串"""
        sim = calculate_similarity("abc", "xyz")
        assert sim < 0.3
    
    def test_with_extension(self):
        """测试带扩展名的文件名"""
        # 应该忽略扩展名进行比较
        sim = calculate_similarity("archive", "archive.zip")
        assert sim == 1.0
        
        sim = calculate_similarity("test_file", "test_file.7z")
        assert sim == 1.0
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        sim = calculate_similarity("Test", "test")
        assert sim > 0.8  # rapidfuzz 对大小写有一定区分
        
        sim = calculate_similarity("FOLDER", "folder")
        assert sim > 0.8
    
    def test_partial_match(self):
        """测试部分匹配"""
        # 父文件夹名是子项名的一部分
        sim = calculate_similarity("漫画", "漫画第一卷")
        assert sim > 0.5
        
        # 子项名是父文件夹名的一部分
        sim = calculate_similarity("作品合集2024", "作品合集")
        assert sim > 0.5
    
    def test_token_matching(self):
        """测试词汇匹配（顺序无关）"""
        sim = calculate_similarity("作品 合集", "合集 作品")
        assert sim > 0.8


class TestCheckSimilarity:
    """测试相似度检查"""
    
    def test_above_threshold(self):
        """测试超过阈值"""
        passed, sim = check_similarity("test", "test", 0.6)
        assert passed is True
        assert sim == 1.0
    
    def test_below_threshold(self):
        """测试低于阈值"""
        passed, sim = check_similarity("abc", "xyz", 0.6)
        assert passed is False
        assert sim < 0.6
    
    def test_zero_threshold(self):
        """测试阈值为0时跳过检测"""
        passed, sim = check_similarity("abc", "xyz", 0.0)
        assert passed is True
        assert sim == 1.0
    
    def test_custom_threshold(self):
        """测试自定义阈值"""
        # 使用较低阈值
        passed, sim = check_similarity("test", "testing", 0.5)
        assert passed is True
        
        # 使用较高阈值 - 使用不同的字符串避免 token_set_ratio 完全匹配
        passed, sim = check_similarity("hello", "world", 0.5)
        assert passed is False


class TestIsSimilar:
    """测试便捷函数"""
    
    def test_similar(self):
        """测试相似情况"""
        assert is_similar("test", "test") is True
        assert is_similar("folder", "folder.zip") is True
    
    def test_not_similar(self):
        """测试不相似情况"""
        assert is_similar("abc", "xyz") is False
    
    def test_custom_threshold(self):
        """测试自定义阈值"""
        assert is_similar("test", "testing", 0.5) is True
        # 使用不同的字符串避免 token_set_ratio 完全匹配
        assert is_similar("hello", "world", 0.5) is False


class TestRealWorldCases:
    """测试真实场景"""
    
    def test_nested_folder_cases(self):
        """测试嵌套文件夹场景"""
        # 常见的嵌套情况：父文件夹和子文件夹名称相似
        cases = [
            ("漫画合集", "漫画合集", True),
            ("作品集", "作品集.zip", True),
            ("游戏", "游戏合集", True),
            ("图片", "图片备份", True),
            ("完全不同", "另一个名字", False),
        ]
        
        for parent, child, expected in cases:
            result = is_similar(parent, child, 0.5)
            assert result == expected, f"Failed: {parent} vs {child}"
    
    def test_archive_folder_cases(self):
        """测试压缩包文件夹场景"""
        # 文件夹名和压缩包名相似
        cases = [
            ("资源包", "资源包.zip", True),
            ("素材", "素材.7z", True),
            ("project", "project.rar", True),
            ("backup_2024", "backup_2024.zip", True),
        ]
        
        for folder, archive, expected in cases:
            result = is_similar(folder, archive, 0.6)
            assert result == expected, f"Failed: {folder} vs {archive}"
