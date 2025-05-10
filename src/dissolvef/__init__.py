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
]

