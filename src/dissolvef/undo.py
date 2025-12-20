"""
撤销管理模块

提供解散操作的撤销功能，记录操作历史并支持回滚
"""

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger


@dataclass
class DissolveOperation:
    """单个解散操作记录"""
    type: str  # 'move' | 'delete_dir'
    src: str
    dst: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UndoRecord:
    """撤销记录"""
    id: str
    timestamp: str
    mode: str  # 'nested' | 'archive' | 'media' | 'direct'
    path: str
    operations: List[DissolveOperation]
    count: int = 0
    
    def __post_init__(self):
        if self.count == 0:
            self.count = len(self.operations)


class UndoManager:
    """撤销管理器"""
    
    def __init__(self, undo_dir: Optional[Path] = None):
        """
        初始化撤销管理器
        
        参数:
            undo_dir: 撤销记录存储目录，默认为 ~/.dissolvef/undo
        """
        self.undo_dir = undo_dir or Path.home() / ".dissolvef" / "undo"
        self.undo_dir.mkdir(parents=True, exist_ok=True)
        self._current_operations: List[DissolveOperation] = []
        self._current_mode: str = ""
        self._current_path: str = ""
    
    def start_batch(self, mode: str, path: str):
        """
        开始一个批次操作
        
        参数:
            mode: 操作模式 ('nested' | 'archive' | 'media' | 'direct')
            path: 操作路径
        """
        self._current_operations = []
        self._current_mode = mode
        self._current_path = str(path)
    
    def record_move(self, src: Path, dst: Path):
        """
        记录移动操作
        
        参数:
            src: 源路径
            dst: 目标路径
        """
        self._current_operations.append(DissolveOperation(
            type='move',
            src=str(src),
            dst=str(dst)
        ))
    
    def record_delete_dir(self, path: Path):
        """
        记录删除目录操作
        
        参数:
            path: 被删除的目录路径
        """
        self._current_operations.append(DissolveOperation(
            type='delete_dir',
            src=str(path)
        ))
    
    def finish_batch(self) -> Optional[str]:
        """
        完成批次操作并保存记录
        
        返回:
            str: 操作 ID，如果没有操作则返回 None
        """
        if not self._current_operations:
            return None
        
        # 使用时间戳 + UUID 确保 ID 唯一性
        operation_id = f"dissolve-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        record = UndoRecord(
            id=operation_id,
            timestamp=datetime.now().isoformat(),
            mode=self._current_mode,
            path=self._current_path,
            operations=self._current_operations
        )
        
        self._save_record(record)
        self._current_operations = []
        
        return operation_id
    
    def _save_record(self, record: UndoRecord):
        """保存撤销记录"""
        file_path = self.undo_dir / f"{record.id}.json"
        data = {
            'id': record.id,
            'timestamp': record.timestamp,
            'mode': record.mode,
            'path': record.path,
            'count': record.count,
            'operations': [asdict(op) for op in record.operations]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_record(self, undo_id: str) -> Optional[UndoRecord]:
        """加载撤销记录"""
        file_path = self.undo_dir / f"{undo_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            operations = [DissolveOperation(**op) for op in data['operations']]
            return UndoRecord(
                id=data['id'],
                timestamp=data['timestamp'],
                mode=data['mode'],
                path=data['path'],
                operations=operations,
                count=data.get('count', len(operations))
            )
        except Exception as e:
            logger.error(f"加载撤销记录失败: {e}")
            return None
    
    def list_records(self, limit: int = 20) -> List[UndoRecord]:
        """
        列出撤销记录
        
        参数:
            limit: 最大返回数量
            
        返回:
            List[UndoRecord]: 撤销记录列表（按时间倒序）
        """
        records = []
        for file_path in self.undo_dir.glob("*.json"):
            record = self._load_record(file_path.stem)
            if record:
                records.append(record)
        
        # 按时间倒序排列
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
    
    def undo(self, undo_id: Optional[str] = None) -> tuple[int, int]:
        """
        执行撤销操作
        
        参数:
            undo_id: 要撤销的操作 ID，如果为 None 则撤销最新的操作
            
        返回:
            tuple[int, int]: (成功数量, 失败数量)
        """
        if undo_id is None:
            records = self.list_records(limit=1)
            if not records:
                logger.warning("没有可撤销的操作")
                return 0, 0
            undo_id = records[0].id
        
        record = self._load_record(undo_id)
        if not record:
            logger.error(f"撤销记录不存在: {undo_id}")
            return 0, 0
        
        success_count = 0
        failed_count = 0
        
        # 逆序执行撤销操作
        for op in reversed(record.operations):
            try:
                if op.type == 'move' and op.dst:
                    # 移动回原位置
                    dst_path = Path(op.dst)
                    src_path = Path(op.src)
                    if dst_path.exists():
                        # 确保源目录存在
                        src_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst_path), str(src_path))
                        success_count += 1
                        logger.info(f"撤销移动: {dst_path} -> {src_path}")
                    else:
                        failed_count += 1
                        logger.warning(f"文件不存在，无法撤销: {dst_path}")
                elif op.type == 'delete_dir':
                    # 重新创建目录
                    dir_path = Path(op.src)
                    dir_path.mkdir(parents=True, exist_ok=True)
                    success_count += 1
                    logger.info(f"重建目录: {dir_path}")
            except Exception as e:
                failed_count += 1
                logger.error(f"撤销操作失败: {e}")
        
        # 删除撤销记录
        self._delete_record(undo_id)
        
        return success_count, failed_count
    
    def _delete_record(self, undo_id: str):
        """删除撤销记录"""
        file_path = self.undo_dir / f"{undo_id}.json"
        if file_path.exists():
            file_path.unlink()


# 全局撤销管理器实例
undo_manager = UndoManager()
