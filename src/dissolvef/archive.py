"""
单压缩包文件夹解散模块

提供释放单个压缩包文件夹的功能，将文件夹中唯一的压缩包文件移动到上级目录
支持相似度检测和撤销
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
import rich.status
from loguru import logger

from .path_filter import filter_archive_paths
from .similarity import check_similarity
from .undo import undo_manager

console = Console()

# 支持的压缩包格式
ARCHIVE_FORMATS = {'.zip', '.rar', '.7z', '.cbz', '.cbr'}


def is_archive_file(filename) -> bool:
    """判断文件是否为压缩包文件"""
    return any(str(filename).lower().endswith(ext) for ext in ARCHIVE_FORMATS)


def release_single_archive_folder(
    path,
    exclude_keywords: Optional[List[str]] = None,
    preview: bool = False,
    similarity_threshold: float = 0.0,
    protect_first_level: bool = True,
    enable_undo: bool = True,
    skip_blacklist: bool = False,
) -> Tuple[int, int]:
    """
    如果文件夹中只有一个压缩包文件，将其释放到上层目录

    参数:
        path (str/Path): 目标路径
        exclude_keywords (list): 排除关键词列表
        preview (bool): 如果为 True，只预览操作不实际执行
        similarity_threshold (float): 相似度阈值 (0.0-1.0)，0 表示不检测
        protect_first_level (bool): 是否保护输入路径下一级文件夹
        enable_undo (bool): 是否启用撤销记录
        skip_blacklist (bool): 是否临时跳过黑名单过滤
    
    返回:
        Tuple[int, int]: (处理的文件夹数量, 因相似度不足跳过的数量)
    """
    if isinstance(path, str):
        path = Path(path)
    
    if not path.exists():
        logger.error(f"路径不存在: {path}")
        console.print(f"[red]错误:[/red] 路径不存在 - {path}")
        return 0, 0
    
    processed_count = 0
    skipped_count = 0
    similarity_skipped = 0
    
    status = rich.status.Status("正在扫描压缩包文件夹...", spinner="dots")
    status_started = False
    
    if not preview:
        status.start()
        status_started = True
        # 开始撤销批次
        if enable_undo:
            undo_manager.start_batch('archive', str(path))
    
    if preview:
        console.print(f"[bold cyan]预览模式:[/bold cyan] 不会实际移动文件")
    
    message = f"{'预览' if preview else '开始处理'}单压缩包文件夹: {path}"
    console.print(message)
    
    try:
        # 收集所有需要检查的文件夹路径
        all_folders = []
        for root, dirs, files in os.walk(path, topdown=False):
            all_folders.append(Path(root))
        
        # 使用路径过滤器过滤黑名单路径
        if skip_blacklist:
            valid_folders = all_folders
            skipped_folders = []
            skipped_count = 0
        else:
            valid_folders, skipped_folders = filter_archive_paths(all_folders, log_skipped=True)
            skipped_count = len(skipped_folders)
        
        # 兼容旧的 exclude_keywords 参数
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
            if protect_first_level and root_path != path and root_path.parent == path:
                continue

            if status_started:
                status.update(f"检查文件夹: {root_path.name}")
            
            try:
                items = list(root_path.iterdir())
                files = [item for item in items if item.is_file()]
                dirs = [item for item in items if item.is_dir()]
                
                archive_files = [f for f in files if is_archive_file(f.name)]
                
                if len(archive_files) == 1 and len(files) == 1 and len(dirs) == 0:
                    archive_file = archive_files[0]
                    folder_name = root_path.name
                    archive_name = archive_file.stem
                    
                    # 相似度检测
                    if similarity_threshold > 0:
                        passed, similarity = check_similarity(folder_name, archive_name, similarity_threshold)
                        if not passed:
                            similarity_skipped += 1
                            console.print(f"  ⏭️ 跳过: [cyan]{folder_name}[/cyan]/[yellow]{archive_file.name}[/yellow] (相似度 {similarity:.0%} < {similarity_threshold:.0%})")
                            continue
                        else:
                            console.print(f"  ✓ 匹配: [cyan]{folder_name}[/cyan]/[green]{archive_file.name}[/green] (相似度 {similarity:.0%})")
                    
                    console.print(f"\n找到符合条件的文件夹: [cyan]{root_path}[/cyan]")
                    console.print(f"- 单个压缩包文件: [green]{archive_file.name}[/green]")
                    
                    parent_dir = root_path.parent
                    target_path = parent_dir / archive_file.name
                    
                    # 处理名称冲突
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
                            # 记录撤销操作
                            if enable_undo:
                                undo_manager.record_move(archive_file, target_path)
                            
                            os.rmdir(str(root_path))
                            # 记录删除目录操作
                            if enable_undo:
                                undo_manager.record_delete_dir(root_path)
                            
                            processed_count += 1
                            logger.info("- 文件移动成功")
                            logger.info("- 文件夹删除成功")
                            console.print("- [green]文件移动成功[/green]")
                            console.print("- [green]文件夹删除成功[/green]")
                        except Exception as e:
                            logger.error(f"处理文件夹时出错 {root_path}: {str(e)}")
                            console.print(f"[red]处理文件夹时出错[/red] {root_path}: {str(e)}")
                    else:
                        processed_count += 1
                        
            except Exception as e:
                logger.error(f"处理文件夹时出错 {root_path}: {str(e)}")
                console.print(f"[red]处理文件夹时出错[/red] {root_path}: {str(e)}")
        
        # 完成撤销批次
        if not preview and enable_undo:
            operation_id = undo_manager.finish_batch()
            if operation_id:
                console.print(f"🔄 撤销 ID: [green]{operation_id}[/green]")
        
        result_message = f"单压缩包文件夹{'预览' if preview else '处理'}完成，共{'发现' if preview else '处理了'} {processed_count} 个文件夹"
        if skipped_count > 0:
            result_message += f"，跳过 {skipped_count} 个黑名单路径"
        if similarity_skipped > 0:
            result_message += f"，跳过 {similarity_skipped} 个（相似度不足）"
        if processed_count == 0:
            result_message += " (没有找到符合条件的文件夹)"
        
        logger.info(result_message)
        if status_started:
            status.stop()
        console.print(f"\n{result_message}")
        
        return processed_count, similarity_skipped
        
    except Exception as e:
        logger.error(f"解散单压缩包文件夹出错: {e}")
        if status_started:
            status.stop()
        console.print(f"[red]解散单压缩包文件夹出错[/red]: {e}")
        return processed_count, similarity_skipped
    finally:
        if not preview and status_started:
            try:
                status.stop()
            except:
                pass


def collect_single_archive_paths(
    path,
    exclude_keywords: Optional[List[str]] = None,
    similarity_threshold: float = 0.0,
    protect_first_level: bool = True,
    skip_blacklist: bool = False,
) -> Tuple[List[Path], int, int]:
    """
    收集“单压缩包文件夹”中的压缩包路径，不执行移动。

    参数:
        path (str/Path): 目标路径
        exclude_keywords (list): 排除关键词列表
        similarity_threshold (float): 相似度阈值 (0.0-1.0)，0 表示不检测
        protect_first_level (bool): 是否保护输入路径下一级文件夹
        skip_blacklist (bool): 是否临时跳过黑名单过滤

    返回:
        Tuple[List[Path], int, int]: (压缩包路径列表, 因黑名单/排除跳过数量, 因相似度不足跳过数量)
    """
    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        logger.error(f"路径不存在: {path}")
        console.print(f"[red]错误:[/red] 路径不存在 - {path}")
        return [], 0, 0

    if exclude_keywords is None:
        exclude_keywords = []

    archive_paths: List[Path] = []
    skipped_count = 0
    similarity_skipped = 0

    status = rich.status.Status("正在收集单压缩包路径...", spinner="dots")
    status.start()

    try:
        all_folders = []
        for root, dirs, files in os.walk(path, topdown=False):
            all_folders.append(Path(root))

        if skip_blacklist:
            valid_folders = all_folders
            skipped_folders = []
            skipped_count = 0
        else:
            valid_folders, skipped_folders = filter_archive_paths(all_folders, log_skipped=True)
            skipped_count = len(skipped_folders)

        if exclude_keywords:
            filtered_folders = []
            for folder in valid_folders:
                if not any(keyword in str(folder) for keyword in exclude_keywords):
                    filtered_folders.append(folder)
                else:
                    skipped_count += 1
                    logger.info(f"跳过含有排除关键词的文件夹: {folder}")
            valid_folders = filtered_folders

        for root_path in valid_folders:
            if protect_first_level and root_path != path and root_path.parent == path:
                continue

            status.update(f"检查文件夹: {root_path.name}")

            try:
                items = list(root_path.iterdir())
                files = [item for item in items if item.is_file()]
                dirs = [item for item in items if item.is_dir()]

                archive_files = [f for f in files if is_archive_file(f.name)]
                if len(archive_files) != 1 or len(files) != 1 or len(dirs) != 0:
                    continue

                archive_file = archive_files[0]
                if similarity_threshold > 0:
                    passed, similarity = check_similarity(root_path.name, archive_file.stem, similarity_threshold)
                    if not passed:
                        similarity_skipped += 1
                        continue

                archive_paths.append(archive_file.resolve())
            except Exception as e:
                logger.error(f"收集路径时出错 {root_path}: {str(e)}")

        # 去重并排序，保证输出稳定
        archive_paths = sorted(set(archive_paths), key=lambda p: str(p).lower())

        console.print(f"\n收集完成，匹配到 [green]{len(archive_paths)}[/green] 个压缩包路径")
        if skipped_count > 0:
            console.print(f"- 跳过黑名单/排除关键词路径: [yellow]{skipped_count}[/yellow]")
        if similarity_skipped > 0:
            console.print(f"- 跳过相似度不足: [yellow]{similarity_skipped}[/yellow]")

        return archive_paths, skipped_count, similarity_skipped
    except Exception as e:
        logger.error(f"收集单压缩包路径出错: {e}")
        console.print(f"[red]收集单压缩包路径出错[/red]: {e}")
        return archive_paths, skipped_count, similarity_skipped
    finally:
        try:
            status.stop()
        except Exception:
            pass


# 直接运行此文件时的入口点
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='解散单压缩包文件夹')
    parser.add_argument('path', type=str, help='要处理的路径')
    parser.add_argument('--exclude', type=str, help='排除关键词，用逗号分隔')
    parser.add_argument('--preview', '-p', action='store_true', help='预览模式')
    parser.add_argument('--similarity', '-s', type=float, default=0.0, help='相似度阈值 (0.0-1.0)')
    
    args = parser.parse_args()
    
    exclude_keywords = []
    if args.exclude:
        exclude_keywords = [keyword.strip() for keyword in args.exclude.split(',')]
    
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]错误：路径不存在[/red] - {path}")
        exit(1)
    
    console.print(f"开始处理路径: [cyan]{path}[/cyan]")
    count, skipped = release_single_archive_folder(
        path, exclude_keywords,
        preview=args.preview,
        similarity_threshold=args.similarity
    )
    console.print(f"处理完成，共处理 [green]{count}[/green] 个单压缩包文件夹，跳过 [yellow]{skipped}[/yellow] 个")
