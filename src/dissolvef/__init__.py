"""
文件夹解散包
包含了解散嵌套文件夹、解散单媒体文件夹、直接解散文件夹等功能
支持相似度检测和撤销
"""
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .nested import flatten_single_subfolder
from .media import release_single_media_folder, VIDEO_FORMATS, ARCHIVE_FORMATS
from .direct import dissolve_folder, handle_name_conflict
from .archive import release_single_archive_folder, is_archive_file
from .path_filter import PathFilter, path_filter, filter_archive_paths, filter_direct_paths, is_path_safe
from .similarity import calculate_similarity, check_similarity
from .undo import UndoManager, undo_manager, UndoRecord, DissolveOperation

__all__ = [
    # 核心功能
    'flatten_single_subfolder',
    'release_single_media_folder', 
    'release_single_archive_folder',
    'dissolve_folder', 
    'handle_name_conflict',
    'is_archive_file',
    # 常量
    'VIDEO_FORMATS', 
    'ARCHIVE_FORMATS',
    # 相似度
    'calculate_similarity',
    'check_similarity',
    # 撤销
    'UndoManager',
    'undo_manager',
    'UndoRecord',
    'DissolveOperation',
    # 路径过滤
    'PathFilter',
    'path_filter',
    'filter_archive_paths',
    'filter_direct_paths',
    'is_path_safe',
]
