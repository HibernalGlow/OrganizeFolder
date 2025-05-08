"""
备份文件和临时文件清理模块
"""
import os
import shutil
from pathlib import Path
import fnmatch
import threading
import concurrent.futures
from typing import List, Tuple, Dict, Any, Optional

# 在文件顶部添加删除规则配置
DEFAULT_DELETE_PATTERNS = [
    ('*.bak', 'file'),     # 仅匹配文件
    ('temp_*', 'dir'),     # 仅匹配文件夹
    ('*.trash', 'both')    # 同时匹配文件和文件夹
]


class BackupCleaner:
    """备份文件和临时文件清理类"""
    
    def __init__(self, logger=None):
        """初始化清理器"""
        self.logger = logger
        
    def log(self, message):
        """输出日志"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def is_match(self, name: str, pattern: str) -> bool:
        """检查文件或文件夹名称是否匹配模式"""
        return fnmatch.fnmatch(name.lower(), pattern.lower())
    
    def should_delete(self, path: Path, patterns: List[Tuple[str, str]]) -> bool:
        """
        检查路径是否应该被删除
        
        参数:
        path (Path): 要检查的路径
        patterns (List[Tuple[str, str]]): 匹配模式列表，每项为(模式, 类型)
            类型可以是: 'file'(文件), 'dir'(文件夹), 'both'(两者)
            
        返回:
        bool: 如果应该删除则为True
        """
        name = path.name
        is_dir = path.is_dir()
        
        for pattern, item_type in patterns:
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
    
    def process_item(self, item_path: Path, patterns: List[Tuple[str, str]], 
                     exclude_keywords: List[str]) -> Tuple[int, int]:
        """
        处理单个项目(文件或文件夹)
        
        返回: (删除数, 跳过数)
        """
        # 如果路径包含排除关键词，跳过
        if self.is_excluded(str(item_path), exclude_keywords):
            self.log(f"跳过排除项: {item_path}")
            return 0, 1
            
        # 检查是否符合删除条件
        if self.should_delete(item_path, patterns):
            try:
                if item_path.is_dir():
                    shutil.rmtree(item_path)
                    self.log(f"已删除文件夹: {item_path}")
                else:
                    item_path.unlink()
                    self.log(f"已删除文件: {item_path}")
                return 1, 0
            except Exception as e:
                self.log(f"删除失败 {item_path}: {e}")
                return 0, 1
        
        return 0, 0
    
    def process_directory(self, dir_path: Path, patterns: List[Tuple[str, str]], 
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
            self.log(f"处理目录时出错 {dir_path}: {e}")
        
        return removed, skipped
    
    def clean(self, path, patterns=None, exclude_keywords=None, 
              max_workers=None) -> Tuple[int, int]:
        """
        清理备份文件和临时文件
        
        参数:
        path (str/Path): 目标路径
        patterns (List[Tuple[str, str]], 可选): 自定义匹配模式
        exclude_keywords (List[str], 可选): 排除关键词
        max_workers (int, 可选): 最大工作线程数
        
        返回:
        tuple: (已删除数量, 已跳过数量)
        """
        path = Path(path) if isinstance(path, str) else path
        patterns = patterns or DEFAULT_DELETE_PATTERNS
        exclude_keywords = exclude_keywords or []
        
        self.log(f"\n开始清理备份文件和临时文件: {path}")
        
        # 确保路径存在
        if not path.exists():
            self.log(f"路径不存在: {path}")
            return 0, 0
            
        # 单线程清理
        return self.process_directory(path, patterns, exclude_keywords)


def remove_backup_and_temp(path, exclude_keywords=None, logger=None):
    """
    删除指定路径下的备份文件和临时文件夹
    
    参数:
    path (str/Path): 目标路径
    exclude_keywords (list, 可选): 排除关键词列表
    logger: 日志记录器
    
    返回:
    tuple: (已删除数量, 已跳过数量)
    """
    path = Path(path) if isinstance(path, str) else path
    if logger:
        logger.info(f"\n开始清理备份文件和临时文件夹: {path}")
    
    try:
        # 创建清理器实例
        cleaner = BackupCleaner(logger=logger)
        
        # 执行清理
        removed_count, skipped_count = cleaner.clean(
            path=path,
            patterns=DEFAULT_DELETE_PATTERNS,
            exclude_keywords=exclude_keywords or []
        )
        
        if logger:
            logger.info(f"清理完成，共删除 {removed_count} 个项目，跳过 {skipped_count} 个项目")
        
        return removed_count, skipped_count
        
    except Exception as e:
        if logger:
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
                            print(f"警告：路径不存在 - {line}")
                
                print(f"从剪贴板读取到 {len(paths)} 个有效路径")
        except ImportError:
            print("警告：未安装pyperclip模块，无法从剪贴板读取。")
        except Exception as e:
            print(f"从剪贴板读取失败: {e}")
    
    if args.paths:
        for path_str in args.paths:
            path = Path(path_str.strip('"').strip("'"))
            if path.exists():
                paths.append(path)
            else:
                print(f"警告：路径不存在 - {path_str}")
    
    if not paths:
        print("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            if line := input().strip():
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    paths.append(path)
                else:
                    print(f"警告：路径不存在 - {line}")
            else:
                break
    
    if not paths:
        print("未提供任何有效的路径")
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
        print(f"\n处理路径: {path}")
        removed, skipped = cleaner.clean(path, exclude_keywords=exclude_keywords)
        total_removed += removed
        total_skipped += skipped
    
    print(f"\n清理完成，共删除 {total_removed} 个项目，跳过 {total_skipped} 个项目")