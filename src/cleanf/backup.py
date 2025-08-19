"""
备份文件和临时文件清理模块
"""
import os
import shutil
import json
from pathlib import Path
import fnmatch
import threading
import concurrent.futures
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger
import re
from .config import DELETE_PATTERNS

# 默认删除规则配置（作为备用）
DEFAULT_DELETE_PATTERNS = [
    ('*.bak', 'file'),     # 仅匹配文件
    ('temp_*', 'dir'),     # 仅匹配文件夹
    ('*.trash', 'both'),   # 同时匹配文件和文件夹
    ('[#hb]*.txt', 'file') # 以[#hb]开头的txt文件
]

def load_delete_patterns_from_json(json_path: str = None) -> List[Tuple[str, str]]:
    """
    从JSON文件加载删除规则
    
    参数:
    json_path (str, 可选): JSON配置文件路径，默认为当前目录下的delete_patterns.json
    
    返回:
    List[Tuple[str, str]]: 删除规则列表
    """
    if json_path is None:
        # 使用当前脚本所在目录的delete_patterns.json
        json_path = Path(__file__).parent / "delete_patterns.json"
    
    try:
        json_path = Path(json_path)
        if not json_path.exists():
            logger.info(f"配置文件不存在: {json_path}，使用默认配置")
            return DEFAULT_DELETE_PATTERNS
            
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        patterns = []
        for item in config.get('delete_patterns', []):
            pattern = item.get('pattern', '')
            item_type = item.get('type', 'both')
            if pattern:
                patterns.append((pattern, item_type))
                
        return patterns if patterns else DEFAULT_DELETE_PATTERNS
        
    except Exception as e:
        logger.info(f"读取配置文件失败: {e}，使用默认配置")
        return DEFAULT_DELETE_PATTERNS


class BackupCleaner:
    """备份文件和临时文件清理类"""
    def __init__(self):
        """初始化清理器"""
        self.patterns = DELETE_PATTERNS

    def _wildcard_to_regex(self, pattern: str) -> str:
        """将shell通配符模式转换为正则表达式"""
        # 转义正则特殊字符
        pattern = re.escape(pattern)
        # 替换通配符
        pattern = pattern.replace(r'\*', '.*').replace(r'\?', '.')
        return f'^{pattern}$'

    def is_match(self, name: str, pattern: str) -> bool:
        """使用正则表达式匹配文件或文件夹名称，支持shell通配符自动转换"""
        regex = pattern
        # regex = self._wildcard_to_regex(pattern)
        result = re.fullmatch(regex, name, re.IGNORECASE) is not None
        return result

    def should_delete(self, path: Path, patterns) -> bool:
        """
        检查路径是否应该被删除
        
        参数:
        path (Path): 要检查的路径
        patterns (List[dict]): 匹配模式列表，每项为dict，含pattern和type
            type可以是: 'file'(文件), 'dir'(文件夹), 'both'(两者)
        
        返回:
        bool: 如果应该删除则为True
        """
        name = path.name
        is_dir = path.is_dir()
        
        for rule in patterns:
            pattern = rule["pattern"]
            item_type = rule["type"]
            if item_type == 'file' and not is_dir and self.is_match(name, pattern):
                return True
            elif item_type == 'dir' and is_dir and self.is_match(name, pattern):
                return True
            elif item_type == 'both' and self.is_match(name, pattern):
                return True
        return False
    
    def is_excluded(self, path: str, exclude_keywords: List[str]) -> bool:
        """检查路径是否应该被排除"""
        return any(keyword in path for keyword in exclude_keywords)
    
    def scan_items(self, dir_path: Path, patterns, 
                   exclude_keywords: List[str]) -> List[Path]:
        """
        扫描目录中要删除的项目，但不实际删除
        
        返回: 要删除的项目列表
        """
        items_to_delete = []
        
        try:
            # 获取所有项目
            items = list(dir_path.iterdir())
            
            # 先扫描文件
            for item in items:
                if item.is_file():
                    if not self.is_excluded(str(item), exclude_keywords) and self.should_delete(item, patterns):
                        items_to_delete.append(item)
            
            # 再扫描文件夹(由底向上)
            for item in items:
                if item.is_dir():
                    # 先递归扫描子文件夹
                    sub_items = self.scan_items(item, patterns, exclude_keywords)
                    items_to_delete.extend(sub_items)
                    
                    # 检查原始文件夹是否要删除
                    if not self.is_excluded(str(item), exclude_keywords) and self.should_delete(item, patterns):
                        items_to_delete.append(item)
                        
        except Exception as e:
            logger.info(f"扫描目录时出错 {dir_path}: {e}")
        
        return items_to_delete

    def process_item(self, item_path: Path, patterns, 
                     exclude_keywords: List[str]) -> Tuple[int, int]:
        """
        处理单个项目(文件或文件夹)
        
        返回: (删除数, 跳过数)
        """
        # 如果路径包含排除关键词，跳过
        if self.is_excluded(str(item_path), exclude_keywords):
            logger.info(f"跳过排除项: {item_path}")
            return 0, 1
            
        # 检查是否符合删除条件
        if self.should_delete(item_path, patterns):
            try:
                if item_path.is_dir():
                    shutil.rmtree(item_path)
                    logger.info(f"已删除文件夹: {item_path}")
                else:
                    item_path.unlink()
                    logger.info(f"已删除文件: {item_path}")
                return 1, 0
            except Exception as e:
                logger.info(f"删除失败 {item_path}: {e}")
                return 0, 1
        
        return 0, 0
    
    def process_directory(self, dir_path: Path, patterns, 
                         exclude_keywords: List[str]) -> Tuple[int, int]:
        """
        处理目录中的所有项目
        
        返回: (删除数, 跳过数)
        """
        removed = 0
        skipped = 0
        
        try:
            # 获取所有项目
            items = list(dir_path.iterdir())
            
            # 先处理文件
            for item in items:
                if item.is_file():
                    r, s = self.process_item(item, patterns, exclude_keywords)
                    removed += r
                    skipped += s
            
            # 再处理文件夹(由底向上)
            for item in items:
                if item.is_dir():
                    # 先递归处理子文件夹
                    r, s = self.process_directory(item, patterns, exclude_keywords)
                    removed += r
                    skipped += s
                      # 如果原始文件夹仍然存在，再尝试删除它
                    if item.exists():
                        r, s = self.process_item(item, patterns, exclude_keywords)
                        removed += r
                        skipped += s
                        
        except Exception as e:
            logger.info(f"处理目录时出错 {dir_path}: {e}")
        
        return removed, skipped
    
    def clean(self, path, patterns=None, exclude_keywords=None, 
              max_workers=None, preview_mode=False) -> Tuple[int, int]:
        """
        清理备份文件和临时文件
        
        参数:
        path (str/Path): 目标路径
        patterns (List[dict], 可选): 自定义匹配模式
        exclude_keywords (List[str], 可选): 排除关键词
        max_workers (int, 可选): 最大工作线程数
        preview_mode (bool, 可选): 是否为预览模式
        
        返回:
        tuple: (已删除数量, 已跳过数量) 或 预览模式下返回 (要删除的文件列表, 0)
        """
        path = Path(path) if isinstance(path, str) else path
        patterns = patterns or self.patterns
        exclude_keywords = exclude_keywords or []
        
        if preview_mode:
            logger.info(f"\n扫描要删除的备份文件和临时文件: {path}")
            items_to_delete = self.scan_items(path, patterns, exclude_keywords)
            return items_to_delete, 0
        
        logger.info(f"\n开始清理备份文件和临时文件: {path}")
        
        # 确保路径存在
        if not path.exists():
            logger.info(f"路径不存在: {path}")
            return 0, 0
            
        # 单线程清理
        return self.process_directory(path, patterns, exclude_keywords)


def remove_backup_and_temp(path, exclude_keywords=None, custom_patterns=None, preview_mode=False):
    """
    删除指定路径下的备份文件和临时文件夹
    
    参数:
    path (str/Path): 目标路径
    exclude_keywords (list, 可选): 排除关键词列表
    custom_patterns (list, 可选): 自定义清理模式列表，如果不提供则使用默认模式
    preview_mode (bool, 可选): 是否为预览模式，如果是则返回要删除的文件列表
    
    返回:
    tuple: (已删除数量, 已跳过数量) 或 预览模式下返回 (要删除的文件列表, 0)
    """
    path = Path(path) if isinstance(path, str) else path
    
    try:
        # 创建清理器实例
        cleaner = BackupCleaner()
        
        # 使用自定义模式或默认模式
        patterns = custom_patterns if custom_patterns is not None else DELETE_PATTERNS
        
        # 执行清理或预览
        removed_count, skipped_count = cleaner.clean(
            path=path,
            patterns=patterns,
            exclude_keywords=exclude_keywords or [],
            preview_mode=preview_mode
        )
        
        if not preview_mode:
            logger.info(f"清理完成，共删除 {removed_count} 个项目，跳过 {skipped_count} 个项目")
        
        return removed_count, skipped_count
        
    except Exception as e:
        logger.info(f"清理过程出错: {e}")
        return 0, 0


if __name__ == "__main__":
    import argparse
    import sys
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='删除备份文件和临时文件夹')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('--exclude', help='排除关键词列表，用逗号分隔多个关键词')
    args = parser.parse_args()
    
    # 获取要处理的路径
    paths = []
    
    if args.clipboard:
        try:
            import pyperclip
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                for line in clipboard_content.splitlines():
                    if line := line.strip().strip('"').strip("'"):
                        path = Path(line)
                        if path.exists():
                            paths.append(path)
                        else:
                            logger.warning(f"警告：路径不存在 - {line}")
                
                logger.info(f"从剪贴板读取到 {len(paths)} 个有效路径")
        except ImportError:
            logger.warning("警告：未安装pyperclip模块，无法从剪贴板读取。")
        except Exception as e:
            logger.error(f"从剪贴板读取失败: {e}")
    
    if args.paths:
        for path_str in args.paths:
            path = Path(path_str.strip('"').strip("'"))
            if path.exists():
                paths.append(path)
            else:
                logger.warning(f"警告：路径不存在 - {path_str}")
    
    if not paths:
        logger.info("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            if line := input().strip():
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    paths.append(path)
                else:
                    logger.warning(f"警告：路径不存在 - {line}")
            else:
                break
    
    if not paths:
        logger.info("未提供任何有效的路径")
        sys.exit(1)
    
    # 处理排除关键词
    exclude_keywords = []
    if args.exclude:
        exclude_keywords.extend(args.exclude.split(','))
    
    # 处理每个路径
    total_removed = 0
    total_skipped = 0
    
    cleaner = BackupCleaner()
    for path in paths:
        logger.info(f"\n处理路径: {path}")
        removed, skipped = cleaner.clean(path, exclude_keywords=exclude_keywords)
        total_removed += removed
        total_skipped += skipped
    
    logger.info(f"\n清理完成，共删除 {total_removed} 个项目，跳过 {total_skipped} 个项目")