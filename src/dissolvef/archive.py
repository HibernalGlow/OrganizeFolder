"""
单压缩包文件夹解散模块

提供释放单个压缩包文件夹的功能，将文件夹中唯一的压缩包文件移动到上级目录
"""

import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.status import Status
from loguru import logger
from .path_filter import path_filter, filter_archive_paths

console = Console()

# 支持的压缩包格式
ARCHIVE_FORMATS = {'.zip', '.rar', '.7z', '.cbz', '.cbr'}

def is_archive_file(filename):
    """判断文件是否为压缩包文件"""
    return any(str(filename).lower().endswith(ext) for ext in ARCHIVE_FORMATS)

def release_single_archive_folder(path, exclude_keywords=None, preview=False):
    """
    如果文件夹中只有一个压缩包文件，将其释放到上层目录

    参数:
    path (str/Path): 目标路径
    exclude_keywords (list): 排除关键词列表（已弃用，使用黑名单配置替代）
    preview (bool): 如果为True，只预览操作不实际执行
    
    返回:
    int: 处理的文件夹数量
    """
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        logger.error(f"路径不存在: {path}")
        console.print(f"[red]错误:[/red] 路径不存在 - {path}")
        return 0
    
    processed_count = 0
    skipped_count = 0
    status = Status("正在扫描压缩包文件夹...", spinner="dots")
    status_started = False
    
    if not preview:
        status.start()
        status_started = True
    
    if preview:
        console.print(f"[bold cyan]预览模式:[/bold cyan] 不会实际移动文件")
    
    message = f"{'预览' if preview else '开始处理'}单压缩包文件夹: {path}"
    console.print(message)
    try:
        # 首先收集所有需要检查的文件夹路径
        all_folders = []
        for root, dirs, files in os.walk(path, topdown=False):
            all_folders.append(Path(root))
        
        # 使用路径过滤器过滤黑名单路径
        valid_folders, skipped_folders = filter_archive_paths(all_folders, log_skipped=True)
        skipped_count = len(skipped_folders)
        
        # 兼容旧的exclude_keywords参数
        if exclude_keywords:
            filtered_folders = []
            for folder in valid_folders:
                if not any(keyword in str(folder) for keyword in exclude_keywords):
                    filtered_folders.append(folder)
                else:
                    skipped_count += 1
                    logger.info(f"跳过含有排除关键词的文件夹: {folder}")
            valid_folders = filtered_folders
        
        # 处理有效的文件夹
        for root_path in valid_folders:
            if not preview:
                status.update(f"检查文件夹: {root_path.name}")
            
            # logger.info(f"检查文件夹: {root_path}")
            try:
                items = list(root_path.iterdir())
                files = [item for item in items if item.is_file()]
                dirs = [item for item in items if item.is_dir()]
                logger.info(f"- 包含 {len(dirs)} 个子文件夹")
                logger.info(f"- 包含 {len(files)} 个文件")
                archive_files = [f for f in files if is_archive_file(f.name)]
                if len(archive_files) == 1 and len(files) == 1 and len(dirs) == 0:
                    archive_file = archive_files[0]
                    console.print(f"\n找到符合条件的文件夹: [cyan]{root_path}[/cyan]")
                    console.print(f"- 单个压缩包文件: [green]{archive_file.name}[/green]")
                    parent_dir = root_path.parent
                    target_path = parent_dir / archive_file.name
                    if target_path.exists():
                        counter = 1
                        while target_path.exists():
                            new_name = f"{archive_file.stem}_{counter}{archive_file.suffix}"
                            target_path = parent_dir / new_name
                            counter += 1
                            logger.info(f"- 目标文件已存在，尝试新名称: {new_name}")
                    logger.info(f"- {'将' if preview else ''}移动文件: {archive_file} -> {target_path}")
                    console.print(f"- {'将' if preview else ''}移动文件: [blue]{archive_file.name}[/blue] -> [green]{target_path}[/green]")
                    if not preview:
                        try:
                            shutil.move(str(archive_file), str(target_path))
                            os.rmdir(str(root_path))
                            processed_count += 1
                            logger.info("- 文件移动成功")
                            logger.info("- 文件夹删除成功")
                            console.print("- [green]文件移动成功[/green]")
                            console.print("- [green]文件夹删除成功[/green]")
                        except Exception as e:
                            logger.error(f"处理文件夹时出错 {root}:")
                            logger.error(f"错误信息: {str(e)}")
                            console.print(f"[red]处理文件夹时出错[/red] {root}:")
                            console.print(f"错误信息: {str(e)}")
                    else:
                        processed_count += 1
                elif preview and len(archive_files) > 0:
                    logger.info(f"不符合处理条件: {root}")
                    logger.info(f"- 压缩包文件数: {len(archive_files)} (需要为1)")
                    logger.info(f"- 总文件数: {len(files)} (需要为1)")
                    logger.info(f"- 子文件夹数: {len(dirs)} (需要为0)")
                    console.print(f"[yellow]不符合处理条件[/yellow]: {root}")
                    console.print(f"- 压缩包文件数: {len(archive_files)} (需要为1)")
                    console.print(f"- 总文件数: {len(files)} (需要为1)")
                    console.print(f"- 子文件夹数: {len(dirs)} (需要为0)")
            except Exception as e:
                logger.error(f"处理文件夹时出错 {root}:")
                logger.error(f"错误信息: {str(e)}")
                console.print(f"[red]处理文件夹时出错[/red] {root}:")
                console.print(f"错误信息: {str(e)}")
        result_message = f"单压缩包文件夹{'预览' if preview else '处理'}完成，共{'发现' if preview else '处理了'} {processed_count} 个文件夹"
        if skipped_count > 0:
            result_message += f"，跳过 {skipped_count} 个黑名单路径"
        if processed_count == 0:
            result_message += " (没有找到符合条件的文件夹)"
        logger.info(result_message)
        if status_started:
            status.stop()
        console.print(f"\n{result_message}")
        return processed_count
    except Exception as e:
        logger.error(f"解散单压缩包文件夹出错: {e}")
        if status_started:
            status.stop()
        console.print(f"[red]解散单压缩包文件夹出错[/red]: {e}")
        return processed_count
    finally:
        if not preview and status_started:
            try:
                status.stop()
            except:
                pass 