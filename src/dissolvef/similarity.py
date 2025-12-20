"""
相似度计算模块

提供字符串相似度计算功能，用于判断父文件夹与子项名称的相似程度
"""

from difflib import SequenceMatcher
from pathlib import Path


def calculate_similarity(str1: str, str2: str) -> float:
    """
    计算两个字符串的相似度
    
    参数:
        str1: 第一个字符串
        str2: 第二个字符串
        
    返回:
        float: 相似度值 (0.0 - 1.0)
    """
    if not str1 or not str2:
        return 0.0
    # 移除扩展名进行比较
    name1 = Path(str1).stem if '.' in str1 else str1
    name2 = Path(str2).stem if '.' in str2 else str2
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def check_similarity(parent_name: str, child_name: str, threshold: float = 0.6) -> tuple[bool, float]:
    """
    检查父文件夹与子项名称的相似度是否超过阈值
    
    参数:
        parent_name: 父文件夹名称
        child_name: 子项名称（文件夹或文件）
        threshold: 相似度阈值 (0.0 - 1.0)，默认 0.6
        
    返回:
        tuple[bool, float]: (是否通过检查, 实际相似度)
    """
    similarity = calculate_similarity(parent_name, child_name)
    return similarity >= threshold, similarity
