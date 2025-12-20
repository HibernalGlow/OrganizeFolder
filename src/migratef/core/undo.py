"""撤销管理器

使用 SQLite 持久化存储撤销历史，支持迁移操作的撤销。
"""

import logging
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import MigrateOperation, UndoRecord, UndoResult

logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = Path.home() / ".migratef" / "undo.db"


class UndoManager:
    """撤销管理器 - 使用 SQLite 存储撤销记录"""

    def __init__(self, db_path: Optional[Path] = None):
        """初始化撤销管理器

        Args:
            db_path: 数据库文件路径，默认为 ~/.migratef/undo.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """创建数据库表"""
        cursor = self.conn.cursor()

        # 批次表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_batches (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                description TEXT,
                action TEXT DEFAULT 'move',
                undone INTEGER DEFAULT 0
            )
        """)

        # 操作表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                target_path TEXT NOT NULL,
                seq_order INTEGER NOT NULL,
                FOREIGN KEY (batch_id) REFERENCES undo_batches(id)
            )
        """)

        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_operations_batch 
            ON undo_operations(batch_id)
        """)

        self.conn.commit()

    def record(
        self, 
        operations: List[MigrateOperation], 
        action: str = "move",
        description: str = ""
    ) -> str:
        """记录一批迁移操作

        Args:
            operations: 迁移操作列表
            action: 操作类型 (move/copy)
            description: 操作描述

        Returns:
            批次 ID
        """
        if not operations:
            return ""

        batch_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        cursor = self.conn.cursor()

        # 插入批次记录
        cursor.execute(
            "INSERT INTO undo_batches (id, timestamp, description, action) VALUES (?, ?, ?, ?)",
            (batch_id, timestamp, description, action),
        )

        # 插入操作记录（按顺序）
        for seq, op in enumerate(operations):
            cursor.execute(
                """INSERT INTO undo_operations 
                   (batch_id, source_path, target_path, seq_order) 
                   VALUES (?, ?, ?, ?)""",
                (batch_id, str(op.source_path), str(op.target_path), seq),
            )

        self.conn.commit()
        logger.info(f"记录撤销批次 {batch_id}: {len(operations)} 个操作")
        return batch_id

    def undo(self, batch_id: str) -> UndoResult:
        """撤销指定批次的操作

        对于 move 操作：将文件从目标路径移回源路径
        对于 copy 操作：删除目标路径的文件

        Args:
            batch_id: 批次 ID

        Returns:
            撤销结果
        """
        cursor = self.conn.cursor()

        # 检查批次是否存在且未撤销
        cursor.execute(
            "SELECT undone, action FROM undo_batches WHERE id = ?", (batch_id,)
        )
        row = cursor.fetchone()

        if not row:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), Path(), f"批次不存在: {batch_id}")],
            )

        if row[0]:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), Path(), f"批次已撤销: {batch_id}")],
            )

        action = row[1] or "move"

        # 获取操作记录（逆序）
        cursor.execute(
            """SELECT source_path, target_path FROM undo_operations 
               WHERE batch_id = ? ORDER BY seq_order DESC""",
            (batch_id,),
        )
        operations = cursor.fetchall()

        success_count = 0
        failed_count = 0
        failed_items: List[tuple] = []

        # 执行撤销
        for source_path_str, target_path_str in operations:
            source_path = Path(source_path_str)
            target_path = Path(target_path_str)

            try:
                if action == "move":
                    # 移动操作：将文件从目标移回源
                    if target_path.exists():
                        # 确保源目录存在
                        source_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(target_path), str(source_path))
                        success_count += 1
                        logger.info(f"撤销移动: {target_path.name} -> {source_path}")
                    else:
                        failed_count += 1
                        failed_items.append(
                            (source_path, target_path, f"目标文件不存在: {target_path}")
                        )
                else:
                    # 复制操作：删除目标文件
                    if target_path.exists():
                        if target_path.is_dir():
                            shutil.rmtree(target_path)
                        else:
                            target_path.unlink()
                        success_count += 1
                        logger.info(f"撤销复制(删除): {target_path}")
                    else:
                        # 文件已不存在，视为成功
                        success_count += 1
                        
            except Exception as e:
                failed_count += 1
                failed_items.append((source_path, target_path, str(e)))
                logger.error(f"撤销失败 {target_path} -> {source_path}: {e}")

        # 标记批次为已撤销
        cursor.execute(
            "UPDATE undo_batches SET undone = 1 WHERE id = ?", (batch_id,)
        )
        self.conn.commit()

        return UndoResult(
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items,
        )

    def undo_latest(self) -> UndoResult:
        """撤销最近一次操作

        Returns:
            撤销结果
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id FROM undo_batches 
               WHERE undone = 0 
               ORDER BY timestamp DESC LIMIT 1"""
        )
        row = cursor.fetchone()

        if not row:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), Path(), "没有可撤销的操作")],
            )

        return self.undo(row[0])

    def get_history(self, limit: int = 10) -> List[UndoRecord]:
        """获取最近的操作历史

        Args:
            limit: 返回记录数量限制

        Returns:
            撤销记录列表
        """
        cursor = self.conn.cursor()

        # 获取批次
        cursor.execute(
            """SELECT id, timestamp, description, action, undone FROM undo_batches 
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        batches = cursor.fetchall()

        records: List[UndoRecord] = []

        for batch_id, timestamp_str, description, action, undone in batches:
            # 获取该批次的操作
            cursor.execute(
                """SELECT source_path, target_path FROM undo_operations 
                   WHERE batch_id = ? ORDER BY seq_order""",
                (batch_id,),
            )
            ops = [
                MigrateOperation(source_path=Path(src), target_path=Path(tgt))
                for src, tgt in cursor.fetchall()
            ]

            records.append(
                UndoRecord(
                    id=batch_id,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    operations=ops,
                    description=description or "",
                    action=action or "move",
                )
            )

        return records

    def clear_history(self, keep_recent: int = 0) -> int:
        """清理历史记录

        Args:
            keep_recent: 保留最近的记录数量

        Returns:
            删除的记录数量
        """
        cursor = self.conn.cursor()

        if keep_recent > 0:
            cursor.execute(
                """SELECT id FROM undo_batches 
                   ORDER BY timestamp DESC LIMIT ?""",
                (keep_recent,),
            )
            keep_ids = [row[0] for row in cursor.fetchall()]

            if keep_ids:
                placeholders = ",".join("?" * len(keep_ids))
                cursor.execute(
                    f"DELETE FROM undo_operations WHERE batch_id NOT IN ({placeholders})",
                    keep_ids,
                )
                cursor.execute(
                    f"DELETE FROM undo_batches WHERE id NOT IN ({placeholders})",
                    keep_ids,
                )
        else:
            cursor.execute("DELETE FROM undo_operations")
            cursor.execute("DELETE FROM undo_batches")

        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    def close(self) -> None:
        """关闭数据库连接"""
        self.conn.close()

    def __enter__(self) -> "UndoManager":
        return self

    def __exit__(self, *args) -> None:
        self.close()
