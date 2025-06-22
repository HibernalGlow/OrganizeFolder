"""
文件迁移模块 - 核心迁移逻辑
"""
import shutil
import concurrent.futures
from pathlib import Path
from typing import List, Literal
from threading import Lock
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TransferSpeedColumn, FileSizeColumn
from loguru import logger

# 线程锁，用于保护进度条更新
progress_lock = Lock()

def migrate_files_with_structure(
    source_file_paths: List[str], 
    target_root_dir: str, 
    max_workers: int = None, 
    action: Literal['copy', 'move'] = 'move'
) -> None:
    """
    迁移文件并保持目录结构
    
    Args:
        source_file_paths: 源文件路径列表
        target_root_dir: 目标根目录
        max_workers: 最大工作线程数
        action: 操作类型，'copy'（复制）或'move'（移动）
    """
    if not source_file_paths:
        logger.warning("没有提供源文件路径")
        return
    
    target_root = Path(target_root_dir)
    
    # 确保目标根目录存在
    target_root.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"目标根目录: {target_root}")
    logger.info(f"使用线程数: {max_workers}")
    
    # 统计信息
    success_count = 0
    error_count = 0
    errors = []
    
    # 创建进度条
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        "•",
        TextColumn("[progress.completed]{task.completed}/{task.total}"),
        "•",
        TimeElapsedColumn(),
        TextColumn(""),
        console=None,
        transient=False
    ) as progress:
        
        task = progress.add_task(
            f"正在{'复制' if action == 'copy' else '移动'}文件...",
            total=len(source_file_paths)
        )
        
        def migrate_single_file(source_path_str: str) -> tuple[bool, str, str]:
            """迁移单个文件"""
            try:
                source_path = Path(source_path_str)
                
                if not source_path.exists():
                    return False, f"源文件不存在: {source_path}", ""
                
                if not source_path.is_file():
                    return False, f"源路径不是文件: {source_path}", ""
                  # 构建目标路径，保持目录结构
                # 获取源文件的绝对路径
                source_abs = source_path.resolve()
                
                # 简化路径处理：使用文件名和其父目录的最后几级
                # 这样可以保持一定的目录结构但不会重建完整的绝对路径
                parts = source_abs.parts
                if len(parts) >= 2:
                    # 取最后2级目录 + 文件名，这样可以保持一些目录结构
                    relative_parts = parts[-2:]
                    target_path = target_root / Path(*relative_parts)
                else:
                    # 如果路径太短，直接使用文件名
                    target_path = target_root / source_abs.name
                
                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 如果目标文件已存在，生成新名称
                if target_path.exists():
                    base_name = target_path.stem
                    suffix = target_path.suffix
                    counter = 1
                    while target_path.exists():
                        target_path = target_path.parent / f"{base_name}_{counter}{suffix}"
                        counter += 1
                
                # 执行复制或移动操作
                if action == 'copy':
                    shutil.copy2(source_path, target_path)
                else:  # move
                    shutil.move(str(source_path), str(target_path))
                
                # 更新进度条
                with progress_lock:
                    progress.update(task, advance=1, description=f"{'复制' if action == 'copy' else '移动'}: {source_path.name}")
                
                return True, "", str(target_path)
                
            except Exception as e:
                error_msg = f"{'复制' if action == 'copy' else '移动'}文件失败 {source_path_str}: {str(e)}"
                logger.error(error_msg)
                with progress_lock:
                    progress.update(task, advance=1)
                return False, error_msg, ""
        
        # 使用线程池处理文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_path = {
                executor.submit(migrate_single_file, path): path 
                for path in source_file_paths
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_path):
                success, error_msg, target_path = future.result()
                if success:
                    success_count += 1
                    logger.debug(f"成功{'复制' if action == 'copy' else '移动'}: {future_to_path[future]} -> {target_path}")
                else:
                    error_count += 1
                    errors.append(error_msg)
    
    # 显示统计信息
    action_name = "复制" if action == "copy" else "移动"
    logger.info(f"迁移总结 ({action_name}):")
    logger.info(f"  成功{action_name}: {success_count} 个文件")
    if error_count > 0:
        logger.warning(f"  失败{action_name}: {error_count} 个文件")
        for error in errors[:10]:  # 只显示前10个错误
            logger.error(f"    {error}")
        if len(errors) > 10:
            logger.error(f"    ... 还有 {len(errors) - 10} 个错误")
    else:
        logger.info(f"  遇到错误: {error_count} 个文件")
    
    if success_count > 0:
        logger.success(f"迁移完成！成功{action_name} {success_count} 个文件到 {target_root}")
    else:
        logger.error("迁移失败！没有文件被成功处理")
