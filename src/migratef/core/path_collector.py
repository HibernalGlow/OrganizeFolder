"""
路径收集模块 - 负责从各种来源收集和验证文件路径
"""
from pathlib import Path
from typing import List
import pyperclip
from loguru import logger


class PathCollector:
    """路径收集器类"""
    
    def __init__(self):
        self.collected_paths = []
    
    def add_path(self, path_str: str) -> bool:
        """添加单个路径
        
        Args:
            path_str: 路径字符串
            
        Returns:
            bool: 是否成功添加
        """
        # 移除首尾可能存在的双引号或单引号
        cleaned_path = path_str.strip('\"\'')
        path = Path(cleaned_path)
        
        if path.exists() and (path.is_file() or path.is_dir()):
            if cleaned_path not in self.collected_paths:
                self.collected_paths.append(cleaned_path)
                logger.info(f"已添加: {cleaned_path}")
                return True
            else:
                logger.debug(f"已存在: {cleaned_path}")
                return False
        elif path.exists() and not (path.is_file() or path.is_dir()):
            logger.warning(f"警告: '{path.name}' 不是文件或文件夹，已跳过")
            return False
        else:
            logger.error(f"错误: 路径 '{path_str}' (或处理后的 '{cleaned_path}') 不存在或路径无效，已跳过")
            return False
    
    def add_paths_from_list(self, paths: List[str]) -> dict:
        """从路径列表添加多个路径
        
        Args:
            paths: 路径字符串列表
            
        Returns:
            dict: 包含添加统计的字典
        """
        stats = {'added': 0, 'skipped': 0, 'error': 0}
        
        for path_str in paths:
            if self.add_path(path_str):
                stats['added'] += 1
            else:
                # 根据具体错误类型进行分类
                cleaned_path = path_str.strip('\"\'')
                path = Path(cleaned_path)
                if path.exists():
                    stats['skipped'] += 1
                else:
                    stats['error'] += 1
        
        return stats
    
    def add_paths_from_clipboard(self) -> dict:
        """从剪贴板添加路径
        
        Returns:
            dict: 包含处理统计的字典
        """
        try:
            clipboard_content = pyperclip.paste()
            if not clipboard_content:
                logger.warning("剪贴板为空")
                return {'added': 0, 'skipped': 0, 'error': 0}
            
            paths_from_clipboard = [p.strip() for p in clipboard_content.splitlines() if p.strip()]
            if not paths_from_clipboard:
                logger.warning("剪贴板内容解析后没有有效的路径")
                return {'added': 0, 'skipped': 0, 'error': 0}
            
            logger.info(f"正在处理剪贴板中的 {len(paths_from_clipboard)} 个路径...")
            stats = self.add_paths_from_list(paths_from_clipboard)
            logger.info(f"剪贴板处理完成：添加 {stats['added']}, 跳过 {stats['skipped']}, 错误 {stats['error']}")
            return stats
            
        except Exception as e:
            logger.error(f"从剪贴板读取或处理时发生错误: {e}")
            return {'added': 0, 'skipped': 0, 'error': 1}
    
    def get_paths(self) -> List[str]:
        """获取收集到的所有路径"""
        return self.collected_paths.copy()
    
    def clear(self):
        """清空收集到的路径"""
        self.collected_paths.clear()
    
    def count(self) -> int:
        """获取收集到的路径数量"""
        return len(self.collected_paths)


def collect_files_from_paths(source_paths: List[str], preserve_structure: bool = True) -> List[str]:
    """从路径列表（文件和文件夹）中收集所有文件。
    
    Args:
        source_paths: 包含文件和文件夹路径的列表
        preserve_structure: 是否保持目录结构，如果为False则只处理直接输入的文件
        
    Returns:
        所有文件路径的列表
    """
    all_files = []
    
    for path_str in source_paths:
        path = Path(path_str)
        
        if path.is_file():
            # 如果是文件，直接添加
            all_files.append(str(path))
        elif path.is_dir():
            if preserve_structure:
                # 保持目录结构模式：递归收集所有文件
                try:
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            all_files.append(str(file_path))
                    logger.info(f"从文件夹 '{path}' 收集了 {len([f for f in path.rglob('*') if Path(f).is_file()])} 个文件")
                except Exception as e:
                    logger.error(f"扫描文件夹 '{path}' 时出错: {e}")
            else:
                # 扁平迁移模式：只收集第一层的文件
                try:
                    files_count = 0
                    for item in path.iterdir():
                        if item.is_file():
                            all_files.append(str(item))
                            files_count += 1
                    logger.info(f"从文件夹 '{path}' 的第一层收集了 {files_count} 个文件")
                except Exception as e:
                    logger.error(f"扫描文件夹 '{path}' 时出错: {e}")
        else:
            logger.warning(f"跳过无效路径: {path}")
    
    logger.info(f"总共收集了 {len(all_files)} 个文件")
    return all_files
