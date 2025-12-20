"""
相似度计算模块

使用 rapidfuzz 库进行高性能字符串相似度计算
"""

from pathlib import Path
from typing import Tuple

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein


def clean_name(name: str) -> str:
    """
    清理名称，移除扩展名
    
    参数:
        name: 原始名称
        
    返回:
        str: 清理后的名称
    """
    return Path(name).stem if '.' in name else name


def calculate_similarity(str1: str, str2: str) -> float:
    """
    计算两个字符串的相似度
    
    使用 rapidfuzz 的多种算法取最高值：
    - ratio: 简单比率
    - partial_ratio: 部分匹配（处理包含关系）
    - token_sort_ratio: 词序无关匹配
    
    参数:
        str1: 第一个字符串
        str2: 第二个字符串
        
    返回:
        float: 相似度值 (0.0 - 1.0)
    """
    if not str1 or not str2:
        return 0.0
    
    # 清理名称
    n1 = clean_name(str1)
    n2 = clean_name(str2)
    
    if not n1 or not n2:
        return 0.0
    
    # 使用多种算法计算相似度，取最高值
    scores = [
        fuzz.ratio(n1, n2),
        fuzz.partial_ratio(n1, n2),
        fuzz.token_sort_ratio(n1, n2),
        fuzz.token_set_ratio(n1, n2),
    ]
    
    # rapidfuzz 返回 0-100，转换为 0-1
    return max(scores) / 100.0


def check_similarity(parent_name: str, child_name: str, threshold: float = 0.6) -> Tuple[bool, float]:
    """
    检查父文件夹与子项名称的相似度是否超过阈值
    
    参数:
        parent_name: 父文件夹名称
        child_name: 子项名称（文件夹或文件）
        threshold: 相似度阈值 (0.0 - 1.0)，默认 0.6
        
    返回:
        Tuple[bool, float]: (是否通过检查, 实际相似度)
    """
    if threshold <= 0:
        return True, 1.0
    
    similarity = calculate_similarity(parent_name, child_name)
    return similarity >= threshold, similarity


def is_similar(str1: str, str2: str, threshold: float = 0.6) -> bool:
    """
    判断两个字符串是否相似
    
    参数:
        str1: 第一个字符串
        str2: 第二个字符串
        threshold: 相似度阈值
        
    返回:
        bool: 是否相似
    """
    return calculate_similarity(str1, str2) >= threshold
