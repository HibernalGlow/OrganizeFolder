"""
迁移服务模块 - 整合所有组件的高级服务接口
"""
from typing import List, Dict, Optional
from pathlib import Path
from rich.console import Console
from loguru import logger

from ..core.path_collector import PathCollector, collect_files_from_paths
from ..core.file_migrator import FileMigrator
from ..core.undo import UndoManager
from ..core.models import MigrateOperation, UndoResult
from ..ui.interactive import InteractiveUI


class MigrationService:
    """迁移服务类 - 提供高级的迁移功能接口"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.path_collector = PathCollector()
        self.file_migrator = FileMigrator(self.console)
        self.ui = InteractiveUI(self.console)
        self.undo_manager = UndoManager()
        self._last_operation_id = ""
    
    def execute_migration(
        self,
        source_paths: List[str],
        target_dir: str,
        migration_mode: str,
        action_type: str,
        max_workers: Optional[int] = 16,
        record_undo: bool = True
    ) -> Dict[str, any]:
        """执行迁移操作
        
        Args:
            source_paths: 源路径列表
            target_dir: 目标目录
            migration_mode: 迁移模式 ('preserve', 'flat', 'direct')
            action_type: 操作类型 ('copy', 'move')
            max_workers: 最大工作线程数
            record_undo: 是否记录撤销信息
            
        Returns:
            Dict: 迁移统计结果，包含 operation_id 用于撤销
        """
        if not source_paths:
            logger.warning("没有提供源路径")
            return {'migrated': 0, 'error': 0, 'skipped': 0, 'operation_id': ''}
        
        # 收集迁移操作用于撤销记录
        operations: List[MigrateOperation] = []
        
        if migration_mode == "direct":
            # 直接迁移模式 - 记录文件夹级别的操作
            target_path = Path(target_dir).resolve()
            for src in source_paths:
                src_path = Path(src).resolve()
                if src_path.exists():
                    tgt_path = target_path / src_path.name
                    operations.append(MigrateOperation(
                        source_path=src_path,
                        target_path=tgt_path,
                        action=action_type
                    ))
            
            result = self.file_migrator.migrate_paths_directly(
                source_paths, target_dir, action=action_type
            )
        else:
            # 文件级迁移模式
            preserve_structure = (migration_mode == "preserve")
            source_files = collect_files_from_paths(source_paths, preserve_structure=preserve_structure)
            
            if not source_files:
                logger.error("没有找到可迁移的文件")
                return {'migrated': 0, 'error': 1, 'skipped': 0, 'operation_id': ''}
            
            # 记录文件级别的操作 - 使用与 file_migrator 一致的路径计算方式
            target_path = Path(target_dir).resolve()
            for file_path in source_files:
                src_path = Path(file_path).resolve()
                if preserve_structure:
                    # 保持结构：使用与 file_migrator 一致的方式计算相对路径
                    import os
                    drive, path_without_drive = os.path.splitdrive(src_path)
                    relative_parts = path_without_drive.strip(os.sep).split(os.sep)
                    relative_path = Path(*relative_parts)
                    tgt_path = target_path / relative_path
                else:
                    tgt_path = target_path / src_path.name
                
                operations.append(MigrateOperation(
                    source_path=src_path,
                    target_path=tgt_path,
                    action=action_type
                ))
            
            result = self.file_migrator.migrate_files_with_structure(
                source_files, 
                target_dir, 
                max_workers=max_workers, 
                action=action_type, 
                preserve_structure=preserve_structure
            )
        
        # 记录撤销信息
        operation_id = ""
        if record_undo and result.get('migrated', 0) > 0:
            # 只记录成功的操作数量对应的操作
            successful_ops = operations[:result.get('migrated', 0)]
            if successful_ops:
                operation_id = self.undo_manager.record(
                    successful_ops,
                    action=action_type,
                    description=f"{migration_mode} 迁移到 {target_dir}"
                )
                self._last_operation_id = operation_id
                logger.info(f"记录撤销批次: {operation_id}")
        
        result['operation_id'] = operation_id
        return result
    
    def undo(self, batch_id: str = "") -> Dict[str, any]:
        """撤销迁移操作
        
        Args:
            batch_id: 批次 ID，为空则撤销最近一次操作
            
        Returns:
            Dict: 撤销结果
        """
        if batch_id:
            result = self.undo_manager.undo(batch_id)
        else:
            result = self.undo_manager.undo_latest()
        
        return {
            'success_count': result.success_count,
            'failed_count': result.failed_count,
            'failed_items': [(str(s), str(t), e) for s, t, e in result.failed_items]
        }
    
    def get_undo_history(self, limit: int = 10) -> List[Dict]:
        """获取撤销历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 历史记录列表
        """
        records = self.undo_manager.get_history(limit)
        return [
            {
                'id': r.id,
                'timestamp': r.timestamp.isoformat(),
                'description': r.description,
                'action': r.action,
                'count': len(r.operations)
            }
            for r in records
        ]
    
    def get_last_operation_id(self) -> str:
        """获取最近一次操作的 ID"""
        return self._last_operation_id
    
    def interactive_migration(self) -> Dict[str, int]:
        """交互式迁移流程"""
        source_paths, target_dir, migration_mode, action_type = self.ui.get_complete_migration_config()
        
        if not source_paths:
            logger.info("用户取消了操作或未提供源路径")
            return {'migrated': 0, 'error': 0, 'skipped': 0}
        
        return self.execute_migration(
            source_paths=source_paths,
            target_dir=target_dir,
            migration_mode=migration_mode,
            action_type=action_type
        )
    
    def add_paths_from_clipboard(self) -> Dict[str, int]:
        """从剪贴板添加路径"""
        return self.path_collector.add_paths_from_clipboard()
    
    def add_paths_from_list(self, paths: List[str]) -> Dict[str, int]:
        """从路径列表添加路径"""
        return self.path_collector.add_paths_from_list(paths)
    
    def get_collected_paths(self) -> List[str]:
        """获取已收集的路径"""
        return self.path_collector.get_paths()
    
    def clear_collected_paths(self):
        """清空已收集的路径"""
        self.path_collector.clear()
