"""
从文件名中提取日期的核心模块
"""
import re
from datetime import datetime
from dateutil import parser
from loguru import logger

def extract_date_from_filename(filename: str) -> datetime:
    """
    从文件名中提取日期
    
    参数:
        filename: 文件名
        
    返回:
        datetime对象，如果未找到则返回None
    """
    logger.debug(f"开始从文件名提取日期: {filename}")
    
    # 常见日期格式的正则表达式
    patterns = [
        # YYYY-MM-DD 格式 (如: 2019-07-21)
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])",
        # YYYY.MM.DD 格式
        r"(20\d{2}|19\d{2})\.(0[1-9]|1[0-2])\.(0[1-9]|[12][0-9]|3[01])",
        # YYYY_MM_DD 格式
        r"(20\d{2}|19\d{2})_(0[1-9]|1[0-2])_(0[1-9]|[12][0-9]|3[01])",
        # YYYYMMDD 格式 (如: 20190721)
        r"(20\d{2}|19\d{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])",
        # YYYY-MM 格式 (如: 2019-07)
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])",
        # YYYY.MM 格式
        r"(20\d{2}|19\d{2})\.(0[1-9]|1[0-2])",
        # YYYY_MM 格式
        r"(20\d{2}|19\d{2})_(0[1-9]|1[0-2])",
        # YYYYMM 格式 (如: 201907)
        r"(20\d{2}|19\d{2})(0[1-9]|1[0-2])",
        # DD-MM-YYYY 格式 (如: 21-07-2019)
        r"(0[1-9]|[12][0-9]|3[01])[-_.]?(0[1-9]|1[0-2])[-_.]?(20\d{2}|19\d{2})",
        # MM-DD-YYYY 格式 (如: 07-21-2019)
        r"(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])[-_.]?(20\d{2}|19\d{2})",
        # YY-MM-DD 格式 (如: 19-07-21)
        r"(\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])",
        # YY.MM.DD 格式
        r"(\d{2})\.(0[1-9]|1[0-2])\.(0[1-9]|[12][0-9]|3[01])",
        # YYMMDD 格式 (如: 190721)
        r"(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])",
    ]
    
    for pattern_index, pattern in enumerate(patterns):
        matches = re.finditer(pattern, filename)
        for match in matches:
            matched_text = match.group()
            logger.debug(f"匹配到模式 {pattern_index+1}: {matched_text}")
            
            try:
                # 尝试解析日期
                dt = None
                
                # 对于不同的模式，使用不同的解析策略
                if pattern_index <= 7:  # YYYY开头的格式
                    dt = parser.parse(matched_text)
                elif pattern_index in [8, 9]:  # DD-MM-YYYY 或 MM-DD-YYYY
                    # 需要特殊处理，因为dateutil可能会混淆
                    parts = re.split(r'[-_.]', matched_text)
                    if len(parts) == 3:
                        if pattern_index == 8:  # DD-MM-YYYY
                            dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        else:  # MM-DD-YYYY
                            dt = datetime(int(parts[2]), int(parts[0]), int(parts[1]))
                else:  # YY开头的格式
                    dt = parser.parse(matched_text)
                    # 如果年份是两位数，需要调整到合理范围
                    if dt.year < 50:
                        dt = dt.replace(year=dt.year + 2000)
                    elif dt.year < 100:
                        dt = dt.replace(year=dt.year + 1900)
                
                # 合理性校验
                if dt and _is_valid_date(dt):
                    logger.info(f"从 '{filename}' 成功提取日期: {dt}")
                    return dt
                else:
                    logger.debug(f"日期不在合理范围内: {dt}")
                    
            except Exception as e:
                logger.debug(f"解析日期失败: {matched_text}, 错误: {e}")
                continue
    
    logger.debug(f"未能从 '{filename}' 提取有效日期")
    return None

def _is_valid_date(dt: datetime) -> bool:
    """
    检查日期是否在合理范围内
    
    参数:
        dt: datetime对象
        
    返回:
        bool: 是否有效
    """
    current_year = datetime.now().year
    
    # 年份范围检查 (1990-当前年份+1)
    if not (1990 <= dt.year <= current_year + 1):
        return False
    
    # 月份范围检查
    if not (1 <= dt.month <= 12):
        return False
    
    # 日期范围检查
    if not (1 <= dt.day <= 31):
        return False
    
    # 检查日期是否真实存在（如2月30日不存在）
    try:
        datetime(dt.year, dt.month, dt.day)
        return True
    except ValueError:
        return False