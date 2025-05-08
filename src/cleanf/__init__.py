"""
文件清理包
包含了删除空文件夹和清理备份/临时文件的功能
"""
from pathlib import Path
from typing import List, Optional, Tuple

from .empty import remove_empty_folders
from .backup import remove_backup_and_temp, BackupCleaner

__all__ = ['remove_empty_folders', 'remove_backup_and_temp', 'BackupCleaner', 'clean_directories']


def clean_directories(paths, remove_empty=True, clean_backup=True, exclude_keywords=None, logger=None):
    """
    清理目录，包括删除空文件夹和清理备份/临时文件
    
    参数:
    paths (list): 要处理的路径列表
    remove_empty (bool): 是否删除空文件夹
    clean_backup (bool): 是否清理备份和临时文件
    exclude_keywords (list): 排除关键词列表
    logger: 日志记录器
    
    返回:
    tuple: (清理操作数, 空文件夹删除数, 备份文件删除数)
    """
    exclude_keywords = exclude_keywords or []
    total_empty_removed = 0
    total_backup_removed = 0
    operation_count = 0
    
    for path in paths:
        if logger:
            logger.info(f"\n处理目录: {path}")
        else:
            print(f"\n处理目录: {path}")
            
        # 删除空文件夹
        if remove_empty:
            operation_count += 1
            removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, logger=logger)
            total_empty_removed += removed
            
        # 清理备份文件和临时文件夹
        if clean_backup:
            operation_count += 1
            removed, _ = remove_backup_and_temp(path, exclude_keywords=exclude_keywords, logger=logger)
            total_backup_removed += removed
            
    return operation_count, total_empty_removed, total_backup_removed