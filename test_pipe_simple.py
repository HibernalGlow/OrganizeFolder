#!/usr/bin/env python3
"""
测试管道功能的简单脚本
"""
import tempfile
import os
from pathlib import Path

# 创建几个测试文件
test_dir = Path(tempfile.mkdtemp())
test_files = []

for i in range(3):
    test_file = test_dir / f"test_file_{i}.txt"
    test_file.write_text(f"这是测试文件 {i}")
    test_files.append(str(test_file))
    print(str(test_file))

# 只输出文件路径，不输出提示信息到stdout
# print(f"\n创建了 {len(test_files)} 个测试文件在: {test_dir}")
# print("可以使用以下命令测试管道功能:")
# print(f"python test_pipe.py | python -m src.migratef --target {test_dir}/migrated")
