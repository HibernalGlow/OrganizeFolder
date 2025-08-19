#!/usr/bin/env python3
"""测试 migratef 模块的文件夹支持功能"""

import tempfile
import os
from pathlib import Path
import sys

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from migratef.__main__ import collect_files_from_paths

def test_collect_files_from_paths():
    """测试从路径列表中收集文件的功能"""
    # 创建临时测试目录结构
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建一些测试文件和文件夹
        test_file1 = temp_path / "file1.txt"
        test_file1.write_text("Test file 1")
        
        test_dir = temp_path / "subdir"
        test_dir.mkdir()
        
        test_file2 = test_dir / "file2.txt"
        test_file2.write_text("Test file 2")
        
        test_file3 = test_dir / "file3.txt"
        test_file3.write_text("Test file 3")
        
        nested_dir = test_dir / "nested"
        nested_dir.mkdir()
        
        test_file4 = nested_dir / "file4.txt"
        test_file4.write_text("Test file 4")
        
        # 测试收集文件
        source_paths = [str(test_file1), str(test_dir)]
        collected_files = collect_files_from_paths(source_paths)
        
        print(f"源路径: {source_paths}")
        print(f"收集到的文件: {collected_files}")
        
        # 验证结果
        expected_files = [
            str(test_file1),
            str(test_file2),
            str(test_file3),
            str(test_file4)
        ]
        
        # 转换为 Path 对象进行比较
        collected_paths = [Path(f) for f in collected_files]
        expected_paths = [Path(f) for f in expected_files]
        
        # 检查是否包含所有预期文件
        for expected in expected_paths:
            if expected not in collected_paths:
                print(f"❌ 缺失文件: {expected}")
                return False
        
        print("✅ 文件收集测试通过！")
        return True

if __name__ == "__main__":
    success = test_collect_files_from_paths()
    if success:
        print("\n🎉 所有测试通过！文件夹支持功能正常工作。")
    else:
        print("\n❌ 测试失败！")
        sys.exit(1)
