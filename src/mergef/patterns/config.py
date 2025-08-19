"""
配置管理模块
支持保存和加载自定义模式配置
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from .patterns import PatternConfig, PatternMatcher, DEFAULT_PATTERNS, create_custom_pattern


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录，如果为None则使用默认目录
        """
        if config_dir is None:
            # 使用用户配置目录
            if os.name == 'nt':  # Windows
                config_dir = Path(os.environ.get('APPDATA', '')) / 'mergef'
            else:  # Unix-like
                config_dir = Path.home() / '.config' / 'mergef'
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / 'patterns.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_patterns(self, patterns: List[PatternConfig]) -> bool:
        """
        保存模式配置到文件
        
        Args:
            patterns: 模式配置列表
            
        Returns:
            是否保存成功
        """
        try:
            config_data = {
                'version': '1.0',
                'patterns': [
                    {
                        'name': p.name,
                        'pattern': p.pattern,
                        'description': p.description,
                        'target_pattern': p.target_pattern,
                        'example': p.example
                    }
                    for p in patterns
                ]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def load_patterns(self) -> List[PatternConfig]:
        """
        从文件加载模式配置
        
        Returns:
            模式配置列表
        """
        try:
            if not self.config_file.exists():
                return []
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            patterns = []
            for pattern_data in config_data.get('patterns', []):
                try:
                    pattern = PatternConfig(
                        name=pattern_data['name'],
                        pattern=pattern_data['pattern'],
                        description=pattern_data['description'],
                        target_pattern=pattern_data['target_pattern'],
                        example=pattern_data['example']
                    )
                    patterns.append(pattern)
                except KeyError:
                    continue  # 跳过格式不正确的配置
            
            return patterns
        except Exception:
            return []
    
    def save_custom_patterns_only(self, matcher: PatternMatcher) -> bool:
        """
        只保存自定义模式（不包括默认模式）
        
        Args:
            matcher: 模式匹配器
            
        Returns:
            是否保存成功
        """
        # 找出自定义模式（不在默认模式中的）
        default_names = {p.name for p in DEFAULT_PATTERNS}
        custom_patterns = [
            p for p in matcher.list_patterns()
            if p.name not in default_names
        ]
        
        return self.save_patterns(custom_patterns)
    
    def create_matcher_with_saved_patterns(self) -> PatternMatcher:
        """
        创建包含保存的自定义模式的匹配器
        
        Returns:
            模式匹配器
        """
        matcher = PatternMatcher()  # 使用默认模式
        
        # 加载并添加自定义模式
        custom_patterns = self.load_patterns()
        for pattern in custom_patterns:
            matcher.add_pattern(pattern)
        
        return matcher
    
    def add_custom_pattern(self, name: str, pattern: str, target_pattern: str,
                          description: str = "", example: str = "") -> bool:
        """
        添加并保存自定义模式
        
        Args:
            name: 模式名称
            pattern: 正则表达式模式
            target_pattern: 目标识别模式
            description: 描述
            example: 示例
            
        Returns:
            是否成功
        """
        try:
            # 验证正则表达式
            import re
            re.compile(pattern)
            re.compile(target_pattern)
            
            # 创建新模式
            new_pattern = create_custom_pattern(name, pattern, target_pattern, description, example)
            
            # 加载现有自定义模式
            existing_patterns = self.load_patterns()
            
            # 检查是否已存在同名模式
            existing_names = {p.name for p in existing_patterns}
            if name in existing_names:
                # 替换现有模式
                existing_patterns = [p for p in existing_patterns if p.name != name]
            
            existing_patterns.append(new_pattern)
            
            # 保存
            return self.save_patterns(existing_patterns)
            
        except Exception:
            return False
    
    def remove_custom_pattern(self, name: str) -> bool:
        """
        删除自定义模式
        
        Args:
            name: 模式名称
            
        Returns:
            是否成功
        """
        try:
            patterns = self.load_patterns()
            patterns = [p for p in patterns if p.name != name]
            return self.save_patterns(patterns)
        except Exception:
            return False
    
    def list_custom_patterns(self) -> List[PatternConfig]:
        """
        列出所有自定义模式
        
        Returns:
            自定义模式列表
        """
        return self.load_patterns()


# 创建全局配置管理器实例
config_manager = ConfigManager()


# 导出
__all__ = [
    'ConfigManager',
    'config_manager'
]
