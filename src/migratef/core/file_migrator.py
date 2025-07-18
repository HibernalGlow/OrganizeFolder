"""
文件迁移核心模块 - 负责实际的文件迁移操作
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict
import concurrent.futures
from threading import Lock
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from loguru import logger


class FileMigrator:
    """文件迁移器类"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def migrate_files_with_structure(
        self, 
        source_file_paths: List[str], 
        target_root_dir: str, 
        max_workers: int = None, 
        action: str = 'copy', 
        preserve_structure: bool = True
    ) -> Dict[str, int]:
        """
        将指定的文件列表迁移（复制或移动）到目标根目录，并可选择保留其原始的目录结构。

        Args:
            source_file_paths: 需要迁移的文件路径列表
            target_root_dir: 文件将被迁移到的目标根目录路径
            max_workers: 使用的最大线程数，默认为 None (os.cpu_count())
            action: 操作类型，'copy' 或 'move'，默认为 'copy'
            preserve_structure: 是否保持目录结构，True为保持，False为扁平迁移
            
        Returns:
            Dict[str, int]: 包含迁移统计的字典
        """
        if not source_file_paths:
            logger.warning("没有需要迁移的文件")
            return {'migrated': 0, 'error': 0, 'skipped': 0}

        try:
            target_root = Path(target_root_dir).resolve()
            target_root.mkdir(parents=True, exist_ok=True)
            structure_mode = "保持目录结构" if preserve_structure else "扁平迁移"
            logger.info(f"目标根目录: {target_root}")
            logger.info(f"迁移模式: {structure_mode}")
            logger.info(f"使用线程数: {max_workers or os.cpu_count()}")
        except Exception as e:
            logger.error(f"错误：无法创建或访问目标目录 '{target_root_dir}': {e}")
            return {'migrated': 0, 'error': 1, 'skipped': 0}

        # 使用线程安全的计数器和锁
        counters = {'migrated': 0, 'error': 0, 'skipped': 0}
        lock = Lock()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[{task.completed}/{task.total}]"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False
        ) as progress:

            task_id = progress.add_task("[cyan]正在迁移文件...", total=len(source_file_paths))

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self._process_single_file, 
                        file_path, target_root, progress, task_id, lock, counters, action, preserve_structure
                    )
                    for file_path in source_file_paths
                ]

        # 完成后更新进度条描述
        progress.stop_task(task_id)
        progress.update(task_id, description="[bold green]迁移完成[/bold green]")
        progress.refresh()

        action_verb_past = "移动" if action == 'move' else "复制"
        logger.info(f"迁移总结 ({action_verb_past}):")
        logger.info(f"  成功{action_verb_past}: {counters['migrated']} 个文件")
        if counters['skipped'] > 0:
            logger.warning(f"  跳过文件: {counters['skipped']} 个")
        if counters['error'] > 0:
            logger.error(f"  遇到错误: {counters['error']} 个文件")
        else:
            logger.info(f"  遇到错误: 0 个文件")
        
        return counters
    
    def migrate_paths_directly(
        self, 
        source_paths: List[str], 
        target_root_dir: str, 
        action: str = 'copy'
    ) -> Dict[str, int]:
        """
        直接迁移文件和文件夹到目标目录（类似 mv 命令）
        
        Args:
            source_paths: 源文件和文件夹路径列表
            target_root_dir: 目标根目录
            action: 操作类型，'copy' 或 'move'
            
        Returns:
            Dict[str, int]: 包含迁移统计的字典
        """
        if not source_paths:
            logger.warning("没有需要迁移的文件或文件夹")
            return {'migrated': 0, 'error': 0, 'skipped': 0}

        try:
            target_root = Path(target_root_dir).resolve()
            target_root.mkdir(parents=True, exist_ok=True)
            logger.info(f"目标根目录: {target_root}")
            logger.info(f"迁移模式: 直接迁移")
        except Exception as e:
            logger.error(f"错误：无法创建或访问目标目录 '{target_root_dir}': {e}")
            return {'migrated': 0, 'error': 1, 'skipped': 0}

        counters = {'migrated': 0, 'error': 0, 'skipped': 0}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[{task.completed}/{task.total}]"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False
        ) as progress:
            
            task_id = progress.add_task("[cyan]正在迁移文件和文件夹...", total=len(source_paths))
            
            for source_path_str in source_paths:
                source_path = Path(source_path_str).resolve()
                item_name = source_path.name
                
                try:
                    if not source_path.exists():
                        logger.warning(f"跳过: 源 '{item_name}' 不存在")
                        counters['skipped'] += 1
                        progress.update(task_id, advance=1, description=f"[yellow]跳过:[/yellow] [dim]{item_name}[/dim]")
                        continue
                    
                    target_path = target_root / item_name
                    
                    # 检查目标是否已存在
                    if target_path.exists():
                        logger.warning(f"跳过: 目标 '{target_path}' 已存在")
                        counters['skipped'] += 1
                        progress.update(task_id, advance=1, description=f"[yellow]跳过(已存在):[/yellow] [dim]{item_name}[/dim]")
                        continue
                    
                    if action == 'move':
                        shutil.move(str(source_path), str(target_path))
                        counters['migrated'] += 1
                        progress.update(task_id, advance=1, description=f"[blue]移动:[/blue] [dim]{item_name}[/dim]")
                    else:  # copy
                        if source_path.is_file():
                            shutil.copy2(source_path, target_path)
                        else:  # directory
                            shutil.copytree(source_path, target_path)
                        counters['migrated'] += 1
                        progress.update(task_id, advance=1, description=f"[green]复制:[/green] [dim]{item_name}[/dim]")
                        
                except Exception as e:
                    action_verb = "移动" if action == 'move' else "复制"
                    logger.error(f"错误: {action_verb} '{item_name}' 到 '{target_root}' 时出错: {e}")
                    counters['error'] += 1
                    progress.update(task_id, advance=1, description=f"[red]错误({action}):[/red] [dim]{item_name}[/dim]")
        
        # 输出总结
        action_verb_past = "移动" if action == 'move' else "复制"
        logger.info(f"迁移总结 ({action_verb_past}):")
        logger.info(f"  成功{action_verb_past}: {counters['migrated']} 个项目")
        if counters['skipped'] > 0:
            logger.warning(f"  跳过项目: {counters['skipped']} 个")
        if counters['error'] > 0:
            logger.error(f"  遇到错误: {counters['error']} 个项目")
        else:
            logger.info(f"  遇到错误: 0 个项目")
        
        return counters
    
    def _process_single_file(
        self, 
        source_file_str: str, 
        target_root: Path, 
        progress: Progress, 
        task_id, 
        lock: Lock, 
        counters: Dict[str, int], 
        action: str = 'copy', 
        preserve_structure: bool = True
    ) -> str:
        """处理单个文件的迁移逻辑（私有方法）"""
        source_file = Path(source_file_str).resolve()
        file_name = source_file.name

        try:
            # 再次检查文件是否存在且是文件
            if not source_file.is_file():
                with lock:
                    logger.warning(f"跳过: 源 '{file_name}' 在处理时不是文件或已消失")
                    counters['skipped'] += 1
                progress.update(task_id, advance=1, description=f"[yellow]跳过:[/yellow] [dim]{file_name}[/dim]")
                return "skipped"

            # 确定目标路径
            if preserve_structure:
                # 保持目录结构模式
                try:
                    drive, path_without_drive = os.path.splitdrive(source_file)
                    relative_parts = path_without_drive.strip(os.sep).split(os.sep)
                    relative_path = Path(*relative_parts)
                    target_file_path = target_root / relative_path
                except Exception as e:
                    with lock:
                        logger.error(f"错误: 无法确定文件 '{file_name}' 的相对路径: {e}")
                        counters['error'] += 1
                    progress.update(task_id, advance=1, description=f"[red]错误(路径):[/red] [dim]{file_name}[/dim]")
                    return "error"
            else:
                # 扁平迁移模式 - 直接放到目标目录
                target_file_path = target_root / file_name

            # 创建目标目录
            try:
                with lock:
                    target_file_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                with lock:
                    logger.error(f"错误: 无法创建目标目录 '{target_file_path.parent}': {e}。跳过文件 '{file_name}'")
                    counters['error'] += 1
                progress.update(task_id, advance=1, description=f"[red]错误(目录):[/red] [dim]{file_name}[/dim]")
                return "error"

            # 复制或移动文件
            try:
                if action == 'move':
                    shutil.move(str(source_file), target_file_path)
                    with lock:
                        counters['migrated'] += 1
                    progress.update(task_id, advance=1, description=f"[blue]移动:[/blue] [dim]{file_name}[/dim]")
                else:  # copy
                    shutil.copy2(source_file, target_file_path)
                    with lock:
                        counters['migrated'] += 1
                    progress.update(task_id, advance=1, description=f"[green]复制:[/green] [dim]{file_name}[/dim]")
                return "success"
            except Exception as e:
                with lock:
                    action_verb = "移动" if action == 'move' else "复制"
                    logger.error(f"错误: {action_verb}文件 '{file_name}' 到 '{target_file_path}' 时出错: {e}")
                    counters['error'] += 1
                progress.update(task_id, advance=1, description=f"[red]错误({action}):[/red] [dim]{file_name}[/dim]")
                return "error"

        except Exception as e:
            # 捕获处理单个文件的其他意外错误
            with lock:
                logger.error(f"处理文件 '{source_file_str}' 时发生意外错误: {e}")
                counters['error'] += 1
            progress.update(task_id, advance=1, description=f"[red]错误(未知):[/red] [dim]{file_name}[/dim]")
            return "error"
