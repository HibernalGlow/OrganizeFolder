"""
文件迁移包
包含了保留目录结构的文件迁移功能
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
import shutil
import os

from .migrate import migrate_files_with_structure, get_source_files_interactively, get_target_dir_interactively

__all__ = [
    'migrate_files_with_structure',
    'get_source_files_interactively',
    'get_target_dir_interactively',
    'migrate_operations'
]

def migrate_operations(source_files: List[str], target_dir: str, action='copy', max_workers=None, logger=None):
    """
    执行文件迁移操作
    
    参数:
    source_files (List[str]): 要迁移的文件路径列表
    target_dir (str): 目标目录路径
    action (str): 'copy' 或 'move'，默认为 'copy'
    max_workers (int, optional): 最大工作线程数
    logger: 可选的日志记录器
    
    返回:
    Dict: 包含迁移操作的统计信息
    """
    # 保留目录结构的迁移
    migrate_files_with_structure(
        source_file_paths=source_files,
        target_root_dir=target_dir,
        max_workers=max_workers,
        action=action
    )
    
    return {
        "action": action,
        "source_files_count": len(source_files),
        "target_dir": target_dir
    }