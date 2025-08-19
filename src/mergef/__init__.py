"""
mergef 包 - 用于合并同名的part文件夹

主要功能:
- 合并同名的part文件夹 (如 movie part1, movie part2, movie part3 等)
- 支持多种part命名格式，如 part1, p1 等
"""

from .merge_part import merge_part_folders, get_base_name

__all__ = ['merge_part_folders', 'get_base_name']
