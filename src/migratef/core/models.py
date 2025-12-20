"""migratef 数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class MigrateOperation:
    """单个迁移操作记录"""
    source_path: Path  # 原始路径
    target_path: Path  # 目标路径
    action: str = "move"  # move 或 copy


@dataclass
class UndoRecord:
    """撤销记录"""
    id: str
    timestamp: datetime
    operations: List[MigrateOperation]
    description: str = ""
    action: str = "move"  # 原始操作类型


@dataclass
class UndoResult:
    """撤销结果"""
    success_count: int = 0
    failed_count: int = 0
    failed_items: List[tuple] = field(default_factory=list)  # (source, target, error)


@dataclass
class MigrateResult:
    """迁移结果"""
    migrated: int = 0
    skipped: int = 0
    error: int = 0
    operation_id: str = ""  # 用于撤销
