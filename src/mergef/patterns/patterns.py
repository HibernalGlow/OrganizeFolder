"""
分段文件夹命名模式配置模块
支持自定义正则表达式模式，增强系统的扩展性
"""
import re
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass


class PatternConfig(NamedTuple):
    """模式配置"""
    name: str
    pattern: str
    description: str
    target_pattern: str  # 用于识别目标文件夹（通常是part 1）的模式
    example: str


# 预定义的命名模式
DEFAULT_PATTERNS = [
    PatternConfig(
        name="classic_part",
        pattern=r'^(.+?)[-_ ]*(?:part|p)[-_ ]*(\d+)$',
        description="经典part格式：name part1, name part2",
        target_pattern=r'[-_ ]*(?:part|p)[-_ ]*1$',
        example="Movie part1, Movie part2"
    ),    PatternConfig(
        name="complex_japanese_part",
        pattern=r'^(.+?)[-_ ]*part(\d+)[-_](\d+)$',
        description="复杂日文part格式：name part1-1, name part1-2",
        target_pattern=r'[-_ ]*part1[-_]1$',
        example="6994-[作者名] part1-1, 6994-[作者名] part1-2"
    ),
    PatternConfig(
        name="complex_japanese_simple",
        pattern=r'^(.+?)[-_ ]*part(\d+)$',
        description="复杂日文简单part格式：name part1, name part2",
        target_pattern=r'[-_ ]*part1$',
        example="6994-[作者名] part1, 6994-[作者名] part2"
    ),
    PatternConfig(
        name="dash_numeric",
        pattern=r'^(.+?)[-_](\d+)[-_](\d+)$',
        description="横线数字格式：name-1-1, name-1-2",
        target_pattern=r'[-_]1[-_]1$',
        example="Movie-1-1, Movie-1-2"
    ),
    PatternConfig(
        name="simple_numeric",
        pattern=r'^(.+?)[-_ ]*(\d+)$',
        description="简单数字格式：name1, name2",
        target_pattern=r'[-_ ]*1$',
        example="Movie1, Movie2"
    ),
    # PatternConfig(
    #     name="bracketed_part",
    #     pattern=r'^(.+?)\[(?:part|p)[-_ ]*(\d+)\]$',
    #     description="方括号格式：name[part1], name[part2]",
    #     target_pattern=r'\[(?:part|p)[-_ ]*1\]$',
    #     example="Movie[part1], Movie[part2]"
    # ),
    # PatternConfig(
    #     name="parentheses_part",
    #     pattern=r'^(.+?)\((?:part|p)[-_ ]*(\d+)\)$',
    #     description="圆括号格式：name(part1), name(part2)",
    #     target_pattern=r'\((?:part|p)[-_ ]*1\)$',
    #     example="Movie(part1), Movie(part2)"
    # ),
    # PatternConfig(
    #     name="dot_part",
    #     pattern=r'^(.+?)\.(?:part|p)[-_ ]*(\d+)$',
    #     description="点分隔格式：name.part1, name.part2",
    #     target_pattern=r'\.(?:part|p)[-_ ]*1$',
    #     example="Movie.part1, Movie.part2"
    # ),
    # PatternConfig(
    #     name="cd_format",
    #     pattern=r'^(.+?)[-_ ]*(?:cd|disc)[-_ ]*(\d+)$',
    #     description="CD/光盘格式：name cd1, name cd2",
    #     target_pattern=r'[-_ ]*(?:cd|disc)[-_ ]*1$',
    #     example="Movie cd1, Movie cd2"
    # ),
    # PatternConfig(
    #     name="volume_format",
    #     pattern=r'^(.+?)[-_ ]*(?:vol|volume)[-_ ]*(\d+)$',
    #     description="卷格式：name vol1, name vol2",
    #     target_pattern=r'[-_ ]*(?:vol|volume)[-_ ]*1$',
    #     example="Movie vol1, Movie vol2"
    # ),
]


class PatternMatcher:
    """模式匹配器"""
    
    def __init__(self, patterns: List[PatternConfig] = None):
        """
        初始化模式匹配器
        
        Args:
            patterns: 自定义模式列表，如果为None则使用默认模式
        """
        self.patterns = patterns or DEFAULT_PATTERNS.copy()
    
    def add_pattern(self, pattern_config: PatternConfig) -> None:
        """添加新的模式配置"""
        self.patterns.append(pattern_config)
    
    def get_base_name_and_pattern(self, folder_name: str) -> Optional[Tuple[str, PatternConfig]]:
        """
        获取文件夹的基本名称和匹配的模式
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            (基本名称, 匹配的模式配置) 或 None
        """
        for pattern_config in self.patterns:
            match = re.match(pattern_config.pattern, folder_name, re.IGNORECASE)
            if match:
                base_name = match.group(1).strip()
                return base_name, pattern_config
        return None
    
    def is_target_folder(self, folder_name: str, pattern_config: PatternConfig) -> bool:
        """
        判断是否为目标文件夹（通常是第一个分段）
        
        Args:
            folder_name: 文件夹名称
            pattern_config: 模式配置
            
        Returns:
            是否为目标文件夹
        """
        return bool(re.search(pattern_config.target_pattern, folder_name, re.IGNORECASE))
    
    def get_sort_key(self, folder_name: str, pattern_config: PatternConfig) -> Tuple[int, ...]:
        """
        获取文件夹的排序键，用于确定合并顺序
        
        Args:
            folder_name: 文件夹名称
            pattern_config: 模式配置
            
        Returns:
            排序键元组
        """
        match = re.match(pattern_config.pattern, folder_name, re.IGNORECASE)
        if match:
            # 提取所有数字部分作为排序键
            numbers = []
            for group in match.groups()[1:]:  # 跳过基本名称组
                try:
                    numbers.append(int(group))
                except (ValueError, TypeError):
                    numbers.append(0)
            return tuple(numbers) if numbers else (0,)
        return (float('inf'),)  # 无法匹配的放在最后
    
    def list_patterns(self) -> List[PatternConfig]:
        """获取所有可用的模式"""
        return self.patterns.copy()
    
    def get_pattern_by_name(self, name: str) -> Optional[PatternConfig]:
        """根据名称获取模式配置"""
        for pattern in self.patterns:
            if pattern.name == name:
                return pattern
        return None


# 创建默认的模式匹配器实例
default_matcher = PatternMatcher()


def get_base_name(folder_name: str) -> Optional[str]:
    """
    向后兼容的函数，获取文件夹的基本名称
    
    Args:
        folder_name: 文件夹名称
        
    Returns:
        基本名称或None
    """
    result = default_matcher.get_base_name_and_pattern(folder_name)
    return result[0] if result else None


def create_custom_pattern(name: str, pattern: str, target_pattern: str, 
                         description: str = "", example: str = "") -> PatternConfig:
    """
    创建自定义模式配置
    
    Args:
        name: 模式名称
        pattern: 正则表达式模式
        target_pattern: 目标文件夹识别模式
        description: 模式描述
        example: 示例
        
    Returns:
        模式配置对象
    """
    return PatternConfig(
        name=name,
        pattern=pattern,
        description=description,
        target_pattern=target_pattern,
        example=example
    )


# 导出常用函数和类
__all__ = [
    'PatternConfig',
    'PatternMatcher',
    'DEFAULT_PATTERNS',
    'default_matcher',
    'get_base_name',
    'create_custom_pattern'
]
