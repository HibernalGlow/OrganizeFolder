"""
文件夹解散包
包含了解散嵌套文件夹、解散单媒体文件夹、直接解散文件夹等功能
"""
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .nested import flatten_single_subfolder
from .media import release_single_media_folder, VIDEO_FORMATS, ARCHIVE_FORMATS
from .direct import dissolve_folder, handle_name_conflict

__all__ = [
    'flatten_single_subfolder',
    'release_single_media_folder', 
    'dissolve_folder', 
    'handle_name_conflict',
    'VIDEO_FORMATS', 
    'ARCHIVE_FORMATS',
    'dissolve_operations'
]

def dissolve_operations(paths, dissolve_direct=False, flatten_nested=False, release_media=False, 
                       file_conflict='auto', dir_conflict='auto', exclude_keywords=None, logger=None, preview=False):
    """
    执行解散操作，包括直接解散、解散嵌套和解散单媒体文件夹等功能
    
    参数:
    paths (List[str/Path]): 要处理的路径列表
    dissolve_direct (bool): 是否直接解散指定文件夹
    flatten_nested (bool): 是否解散嵌套的单一文件夹
    release_media (bool): 是否解散单媒体文件夹
    file_conflict (str): 文件冲突处理方式 ('auto'/'skip'/'overwrite'/'rename')
    dir_conflict (str): 文件夹冲突处理方式 ('auto'/'skip'/'overwrite'/'rename')
    exclude_keywords (List[str]): 排除关键词列表
    logger: 日志记录器
    preview (bool): 预览模式，不实际执行操作
    
    返回:
    Dict: 包含各种操作的统计信息
    """
    if exclude_keywords is None:
        exclude_keywords = []
    
    stats = {
        "operation_count": 0,         # 执行的操作数
        "dissolved_folders": 0,        # 直接解散的文件夹数
        "dissolved_files": 0,         # 直接解散中移动的文件数
        "dissolved_dirs": 0,          # 直接解散中移动的文件夹数
        "flattened_nested": 0,        # 解散的嵌套文件夹数
        "released_media": 0,          # 解散的单媒体文件夹数
    }
    
    for path in paths:
        if not isinstance(path, Path):
            path = Path(path)
        
        message = f"\n处理目录: {path}"
        if logger:
            logger.info(message)
        elif not preview:
            print(message)
            
        # 如果指定了dissolve_direct模式，直接解散文件夹
        if dissolve_direct:
            stats["operation_count"] += 1
            success, files_count, dirs_count = dissolve_folder(
                path, 
                file_conflict=file_conflict,
                dir_conflict=dir_conflict,
                logger=logger,
                preview=preview
            )
            if success or preview:
                stats["dissolved_folders"] += 1
                stats["dissolved_files"] += files_count
                stats["dissolved_dirs"] += dirs_count
                
        else:
            # 1. 释放单独媒体文件夹
            if release_media:
                stats["operation_count"] += 1
                if logger:
                    logger.info("\n>>> 释放单独媒体文件夹...")
                count = release_single_media_folder(path, exclude_keywords, logger, preview)
                stats["released_media"] += count
            
            # 2. 解散嵌套的单独文件夹
            if flatten_nested:
                stats["operation_count"] += 1
                if logger:
                    logger.info("\n>>> 解散嵌套的单独文件夹...")
                count = flatten_single_subfolder(path, exclude_keywords, logger)
                stats["flattened_nested"] += count
    
    return stats