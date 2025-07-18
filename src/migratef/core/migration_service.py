"""
迁移服务模块 - 整合所有组件的高级服务接口
"""
from typing import List, Dict, Optional
from rich.console import Console
from loguru import logger

from ..core.path_collector import PathCollector, collect_files_from_paths
from ..core.file_migrator import FileMigrator
from ..ui.interactive import InteractiveUI


class MigrationService:
    """迁移服务类 - 提供高级的迁移功能接口"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.path_collector = PathCollector()
        self.file_migrator = FileMigrator(self.console)
        self.ui = InteractiveUI(self.console)
    
    def execute_migration(
        self,
        source_paths: List[str],
        target_dir: str,
        migration_mode: str,
        action_type: str,
        max_workers: Optional[int] = 16
    ) -> Dict[str, int]:
        """执行迁移操作
        
        Args:
            source_paths: 源路径列表
            target_dir: 目标目录
            migration_mode: 迁移模式 ('preserve', 'flat', 'direct')
            action_type: 操作类型 ('copy', 'move')
            max_workers: 最大工作线程数
            
        Returns:
            Dict[str, int]: 迁移统计结果
        """
        if not source_paths:
            logger.warning("没有提供源路径")
            return {'migrated': 0, 'error': 0, 'skipped': 0}
        
        if migration_mode == "direct":
            # 直接迁移模式
            return self.file_migrator.migrate_paths_directly(
                source_paths, target_dir, action=action_type
            )
        else:
            # 文件级迁移模式
            preserve_structure = (migration_mode == "preserve")
            source_files = collect_files_from_paths(source_paths, preserve_structure=preserve_structure)
            
            if not source_files:
                logger.error("没有找到可迁移的文件")
                return {'migrated': 0, 'error': 1, 'skipped': 0}
            
            return self.file_migrator.migrate_files_with_structure(
                source_files, 
                target_dir, 
                max_workers=max_workers, 
                action=action_type, 
                preserve_structure=preserve_structure
            )
    
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
