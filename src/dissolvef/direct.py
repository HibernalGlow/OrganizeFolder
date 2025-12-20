"""
文件夹直接解散模块

将指定文件夹的内容移动到其父文件夹，然后删除该文件夹
"""

import os
import shutil
from pathlib import Path
from typing import Tuple
from rich.console import Console
import rich.status
from loguru import logger

console = Console()

def handle_name_conflict(target_path, is_dir=False, mode='auto'):
    """
    处理文件名冲突
    
    参数:
    target_path (Path): 目标路径
    is_dir (bool): 是否是文件夹
    mode (str): 处理模式
        - 'auto': 文件跳过，文件夹合并
        - 'skip': 跳过
        - 'overwrite': 覆盖（文件夹会合并内容）
        - 'rename': 重命名
    
    返回:
    tuple: (Path, bool) - (最终路径, 是否继续处理)
    """
    # 如果目标不存在，直接返回
    if not target_path.exists():
        return target_path, True
        
    # 处理自动模式
    if mode == 'auto':
        mode = 'overwrite' if is_dir else 'skip'
    
    # 输出日志
    item_type = "文件夹" if is_dir else "文件"
      # 根据不同模式处理冲突
    if mode == 'skip':
        message = f"跳过已存在的{item_type}: {target_path}"
        logger.info(message)
        console.print(message)
        return target_path, False
        
    elif mode == 'overwrite':
        if is_dir:
            message = f"将合并到已存在的文件夹: {target_path}"
            logger.info(message)
            console.print(message)
            return target_path, True
        else:
            message = f"将覆盖已存在的文件: {target_path}"
            logger.info(message)
            console.print(message)
            target_path.unlink()
            return target_path, True
            
    else:  # rename
        counter = 1
        while True:
            new_name = f"{target_path.stem}_{counter}{target_path.suffix}"
            new_path = target_path.parent / new_name
            if not new_path.exists():
                message = f"重命名为: {new_path}"
                logger.info(message)
                console.print(message)
                return new_path, True
            counter += 1

def dissolve_folder(path, file_conflict='auto', dir_conflict='auto', preview=False, use_status=True):
    """
    将指定文件夹中的所有内容移动到其父文件夹中，然后删除该文件夹
    
    参数:
    path (Path/str): 要解散的文件夹路径
    file_conflict (str): 文件冲突处理方式 ('auto'/'skip'/'overwrite'/'rename')
    dir_conflict (str): 文件夹冲突处理方式 ('auto'/'skip'/'overwrite'/'rename')
    preview (bool): 如果为True，只预览操作不实际执行
    use_status (bool): 是否使用状态指示器
    
    返回:
    tuple: (bool, int, int) - (是否成功, 移动的文件数量, 移动的文件夹数量)
    """
    # 初始化计数器
    moved_files = 0
    moved_dirs = 0
    
    try:
        # 转换路径为绝对路径
        path = Path(path).resolve()
        
        # 检查路径有效性
        if not path.exists() or not path.is_dir():
            message = f"错误：{path} 不是一个有效的文件夹"
            logger.error(message)
            console.print(f"[red]{message}[/red]")
            return False, 0, 0
            
        # 获取父目录
        parent_dir = path.parent
        message = f"\n{'预览' if preview else '开始'}解散文件夹: {path}"
        logger.info(message)        
        console.print(message)
        if preview:
            console.print(f"[bold cyan]预览模式:[/bold cyan] 不会实际移动文件")
        
        # 创建一个Rich状态指示器
        status = None
        if use_status and not preview:
            status = rich.status.Status("正在扫描文件夹内容...", spinner="dots")
            status.start()
        
        # 获取所有项目并排序（文件优先）
        items = list(path.iterdir())
        items.sort(key=lambda x: (x.is_dir(), x.name))  # 文件在前，文件夹在后
        
        logger.info(f"找到 {len([i for i in items if i.is_file()])} 个文件和 {len([i for i in items if i.is_dir()])} 个文件夹")
        
        for item in items:
            target_path = parent_dir / item.name
            is_dir = item.is_dir()
              # 更新状态
            if status and not preview:
                status.update(f"处理: {item.name}")
            
            # 处理名称冲突
            conflict_mode = dir_conflict if is_dir else file_conflict            
            target_path, should_proceed = handle_name_conflict(
                target_path, 
                is_dir=is_dir,
                mode=conflict_mode
            )
            
            if not should_proceed:
                continue
            
            # 记录操作    
            message = f"{'将' if preview else ''}移动: {item.name} -> {target_path}"
            logger.info(message)
            console.print(message)
            
            # 如果不是预览模式，实际执行移动
            if not preview:
                try:
                    if is_dir and target_path.exists():
                        # 如果是文件夹且目标存在，则移动内容而不是整个文件夹
                        for sub_item in item.iterdir():
                            sub_target = target_path / sub_item.name
                            if sub_target.exists():
                                # 对子项目递归应用相同的冲突处理策略
                                sub_is_dir = sub_item.is_dir()
                                sub_conflict_mode = dir_conflict if sub_is_dir else file_conflict
                                sub_target, sub_should_proceed = handle_name_conflict(
                                    sub_target,
                                    is_dir=sub_is_dir,
                                    mode=sub_conflict_mode,
                                    logger=logger
                                )
                                if not sub_should_proceed:
                                    continue
                                    
                            # 执行移动
                            shutil.move(str(sub_item), str(sub_target))
                            
                            if sub_is_dir:
                                moved_dirs += 1
                            else:
                                moved_files += 1
                    else:
                        # 如果是文件或目标文件夹不存在，直接移动
                        shutil.move(str(item), str(target_path))
                        
                        if is_dir:
                            moved_dirs += 1
                        else:
                            moved_files += 1
                            
                except Exception as e:
                    message = f"移动 {item.name} 失败: {e}"
                    if logger:
                        logger.error(message)
                    else:
                        console.print(f"[red]{message}[/red]")
                    continue
            else:
                # 预览模式下只计数
                if is_dir:
                    moved_dirs += 1
                else:
                    moved_files += 1
        
        # 如果不是预览模式，尝试删除原文件夹
        if not preview:
            try:
                # 检查文件夹是否为空
                remaining_items = list(path.iterdir())
                if remaining_items:
                    message = f"警告：文件夹 {path} 仍包含 {len(remaining_items)} 个项目，无法删除"
                    if logger:
                        logger.warning(message)
                        for item in remaining_items:
                            logger.warning(f"  - {item.name}")
                    else:
                        console.print(f"[yellow]{message}[/yellow]")
                        for item in remaining_items:
                            console.print(f"  - {item.name}")
                    return False, moved_files, moved_dirs
                else:
                    path.rmdir()
                    message = f"已成功解散并删除文件夹: {path}"
                    if logger:
                        logger.info(message)
                    else:
                        console.print(f"[green]{message}[/green]")
            except Exception as e:
                message = f"删除文件夹失败: {e}"
                if logger:
                    logger.error(message)
                else:
                    console.print(f"[red]{message}[/red]")
                return False, moved_files, moved_dirs
        
        # 输出处理结果
        message = f"文件夹{'解散预览' if preview else '解散'}完成，{'将' if preview else ''}移动 {moved_files} 个文件和 {moved_dirs} 个文件夹"
        if logger:
            logger.info(message)
        else:
            if status.started:
                status.stop()
            console.print(f"\n{message}")
        
        return True, moved_files, moved_dirs
            
    except Exception as e:
        message = f"解散文件夹时出错: {e}"
        if logger:
            logger.error(message)
        else:
            if 'status' in locals() and status.started:
                status.stop()
            console.print(f"[red]{message}[/red]")
        return False, moved_files, moved_dirs
    finally:
        # 确保状态指示器被停止
        if status and not preview and status.started:
            status.stop()

# 直接运行此文件时的入口点
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='直接解散文件夹')
    parser.add_argument('path', type=str, help='要解散的文件夹路径')
    parser.add_argument('--file-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                      default='auto', help='文件冲突处理方式 (默认: auto)')
    parser.add_argument('--dir-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                      default='auto', help='文件夹冲突处理方式 (默认: auto)')
    parser.add_argument('--preview', '-p', action='store_true', help='预览模式，不实际执行操作')
    
    args = parser.parse_args()
    
    # 转换路径
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]错误：路径不存在[/red] - {path}")
        exit(1)
    
    console.print(f"开始处理路径: [cyan]{path}[/cyan]")
    success, files_count, dirs_count = dissolve_folder(
        path, 
        file_conflict=args.file_conflict,
        dir_conflict=args.dir_conflict,
        preview=args.preview
    )
    
    mode_text = "预览" if args.preview else "执行"
    if success or args.preview:

        console.print(f"解散操作{mode_text}完成，{'将' if args.preview else '已'}移动 [green]{files_count}[/green] 个文件和 [green]{dirs_count}[/green] 个文件夹")
    else:
        console.print(f"[yellow]警告：解散操作未完全成功，已移动 {files_count} 个文件和 {dirs_count} 个文件夹，但原文件夹未删除[/yellow]")
