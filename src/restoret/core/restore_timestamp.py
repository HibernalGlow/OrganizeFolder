"""
恢复文件时间戳的核心模块
"""
import os
import time
from pathlib import Path
from datetime import datetime
from loguru import logger

def restore_file_timestamp(file_path: Path, target_date: datetime):
    """
    恢复文件的时间戳到指定日期
    
    参数:
        file_path: 文件路径
        target_date: 目标日期
    """
    try:
        # 将datetime转换为时间戳
        timestamp = time.mktime(target_date.timetuple())
        
        # 设置文件的访问时间和修改时间
        os.utime(file_path, (timestamp, timestamp))
        
        logger.info(f"已恢复 {file_path} 的时间戳为 {target_date}")
        
    except Exception as e:
        logger.error(f"恢复 {file_path} 时间戳失败: {e}")
        raise