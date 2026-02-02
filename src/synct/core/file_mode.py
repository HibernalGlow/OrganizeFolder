"""文件模式：根据文件名中的时间戳对文件进行分类归档"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.console import Console

from .archive_folders import FORMATS
from .extract_timestamp import extract_timestamp_from_name

console = Console()


def scan_files_for_timestamp(
    directory: str, recursive: bool = False
) -> list[tuple[str, datetime, str]]:
    """扫描目录中的文件，从文件名提取时间戳
    
    Args:
        directory: 要扫描的目录路径
        recursive: 是否递归扫描子目录，默认 False
        
    Returns:
        list of (文件完整路径, 时间戳, 文件名)
    """
    files_with_timestamp = []
    
    if recursive:
        # 递归扫描
        for root, _, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                result = _extract_file_timestamp(file_path, filename)
                if result:
                    files_with_timestamp.append(result)
    else:
        # 仅扫描顶层
        try:
            for name in os.listdir(directory):
                file_path = os.path.join(directory, name)
                if os.path.isfile(file_path):
                    result = _extract_file_timestamp(file_path, name)
                    if result:
                        files_with_timestamp.append(result)
        except PermissionError as e:
            logger.warning(f"无法访问目录 {directory}: {e}")
    
    logger.info(f"扫描完成，找到 {len(files_with_timestamp)} 个文件")
    return files_with_timestamp


def _extract_file_timestamp(
    file_path: str, filename: str
) -> Optional[tuple[str, datetime, str]]:
    """从文件名提取时间戳，失败时使用文件创建时间
    
    Args:
        file_path: 文件完整路径
        filename: 文件名
        
    Returns:
        (文件路径, 时间戳, 文件名) 或 None
    """
    # 去掉扩展名后尝试提取
    name_without_ext = Path(filename).stem
    dt = extract_timestamp_from_name(name_without_ext)
    
    if dt:
        logger.debug(f"从文件名 '{filename}' 提取到时间戳: {dt}")
    else:
        # 使用文件创建时间作为后备
        try:
            ctime = os.stat(file_path).st_ctime
            dt = datetime.fromtimestamp(ctime)
            logger.debug(f"文件 '{filename}' 未识别到时间戳，使用创建时间: {dt}")
        except OSError as e:
            logger.warning(f"无法获取文件 '{filename}' 的创建时间: {e}")
            return None
    
    return (file_path, dt, filename)


def categorize_files(
    files_with_timestamp: list[tuple[str, datetime, str]],
    base_dst: str,
    format_key: str = "year_month",
) -> list[dict]:
    """为文件生成分类移动操作预览
    
    Args:
        files_with_timestamp: (文件路径, 时间戳, 文件名) 列表
        base_dst: 归档目标基础目录
        format_key: 日期格式键名
        
    Returns:
        操作列表，每项包含 source, destination, timestamp, filename
    """
    if format_key not in FORMATS:
        raise ValueError(f"不支持的格式: {format_key}")
    
    operations = []
    format_spec = FORMATS[format_key]
    
    for file_path, dt, filename in files_with_timestamp:
        # 生成目标路径
        if isinstance(format_spec, list):
            # 多层格式
            dst = base_dst
            for fmt in format_spec:
                dst = os.path.join(dst, dt.strftime(fmt))
        else:
            # 单层格式
            dst = os.path.join(base_dst, dt.strftime(format_spec))
        
        dst_file = os.path.join(dst, filename)
        rel_dst = os.path.relpath(dst_file, base_dst)
        
        operations.append({
            "source": file_path,
            "destination": dst_file,
            "rel_destination": rel_dst,
            "timestamp": dt,
            "filename": filename,
        })
    
    return operations


def archive_file(
    src_file: str, dt: datetime, base_dst: str, format_key: str = "year_month", dry_run: bool = False
) -> str:
    """归档单个文件到基于时间戳的目录结构
    
    Args:
        src_file: 源文件路径
        dt: 时间戳
        base_dst: 归档目标基础目录
        format_key: 日期格式键名
        dry_run: 预览模式，不实际移动文件
        
    Returns:
        目标文件路径
    """
    if format_key not in FORMATS:
        raise ValueError(f"不支持的格式: {format_key}")
    
    format_spec = FORMATS[format_key]
    filename = os.path.basename(src_file)
    
    # 构建目标目录
    if isinstance(format_spec, list):
        dst_dir = base_dst
        for fmt in format_spec:
            dst_dir = os.path.join(dst_dir, dt.strftime(fmt))
    else:
        dst_dir = os.path.join(base_dst, dt.strftime(format_spec))
    
    dst_file = os.path.join(dst_dir, filename)
    
    if dry_run:
        logger.debug(f"预览: 将 {src_file} 移动到 {dst_file}")
        return dst_file
    
    # 检查源文件是否存在
    if not os.path.exists(src_file):
        raise FileNotFoundError(f"源文件不存在: {src_file}")
    
    # 创建目标目录
    os.makedirs(dst_dir, exist_ok=True)
    
    # 处理同名文件冲突
    if os.path.exists(dst_file):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dst_file):
            new_name = f"{base}_{counter}{ext}"
            dst_file = os.path.join(dst_dir, new_name)
            counter += 1
        logger.warning(f"目标文件已存在，重命名为: {os.path.basename(dst_file)}")
    
    logger.info(f"移动文件: {src_file} -> {dst_file}")
    shutil.move(src_file, dst_file)
    return dst_file
