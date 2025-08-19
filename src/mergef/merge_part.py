"""
合并同名的part文件夹核心功能模块 - 安全版本
"""
import os
import re
import shutil
from pathlib import Path
import argparse
from collections import defaultdict
import subprocess
import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich import print
from typing import List, Optional, Dict, Any
import tempfile
import time
from datetime import datetime

# 创建 Rich Console
console = Console()

def create_backup_folder(base_path):
    """创建备份文件夹"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = base_path / f"mergef_backup_{timestamp}"
    backup_folder.mkdir(exist_ok=True)
    return backup_folder

def safe_copy_folder(src, dst):
    """安全地复制文件夹"""
    try:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return True
    except Exception as e:
        print(f"[red]复制文件夹失败: {e}[/]")
        return False

def safe_move_file(src, dst):
    """安全地移动文件，先复制再删除原文件"""
    try:
        # 确保目标目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 先复制文件
        shutil.copy2(src, dst)

        # 验证复制是否成功
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            # 复制成功，删除原文件
            src.unlink()
            return True
        else:
            # 复制失败，删除目标文件（如果存在）
            if dst.exists():
                dst.unlink()
            return False
    except Exception as e:
        print(f"[red]移动文件失败: {src} -> {dst}, 错误: {e}[/]")
        return False

def get_base_name(folder_name):
    """获取文件夹的基本名称（去掉part部分）"""
    # 修改后的正则表达式，支持 part/p 两种前缀格式
    pattern = r'^(.+?)(?:[-_ ]*(?:part|p)[-_ ]*\d+)$'
    match = re.match(pattern, folder_name, re.IGNORECASE)
    return match.group(1).strip() if match else None

def merge_part_folders(base_path, preview_mode=False):
    """
    安全地合并同名的part文件夹

    参数:
        base_path: 要处理的基础路径
        preview_mode: 是否为预览模式，如果为True则只显示将要执行的操作而不实际执行
    """
    base_path = Path(base_path)
    folder_groups = defaultdict(list)

    # 如果是预览模式，显示预览标识
    if preview_mode:
        print(Panel.fit(
            "[bold yellow]预览模式已启用[/]\n"
            "以下是将要执行的操作，但实际不会修改任何文件",
            title="📋 预览模式", border_style="yellow"
        ))
    else:
        print(Panel.fit(
            "[bold green]安全合并模式[/]\n"
            "将创建备份并使用安全的文件操作方式",
            title="🛡️ 安全模式", border_style="green"
        ))

    # 收集所有一级文件夹并按基本名称分组
    for item in base_path.iterdir():
        if not item.is_dir():
            continue

        base_name = get_base_name(item.name)
        if base_name:
            folder_groups[base_name].append(item)

    # 如果没有找到part文件夹
    if not folder_groups:
        print("[yellow]⚠️ 警告: 未找到任何符合part命名格式的文件夹[/]")
        return

    # 创建备份文件夹（仅在非预览模式下）
    backup_folder = None
    if not preview_mode:
        backup_folder = create_backup_folder(base_path)
        print(f"[green]✓ 已创建备份文件夹: {backup_folder}[/]")
    
    # 处理每组文件夹
    for base_name, folders in folder_groups.items():
        if len(folders) <= 1:
            continue

        # 找到part/p 1文件夹作为目标文件夹
        target_folder = None
        other_folders = []

        for folder in folders:
            if re.search(r'(?:part|p)[-_ ]*1$', folder.name, re.IGNORECASE):
                target_folder = folder
            else:
                other_folders.append(folder)

        if not target_folder:
            print(f"[yellow]⚠️ 警告：{base_name} 组中没有找到 part 1 文件夹，跳过处理[/]")
            continue

        # 使用Panel显示处理信息，让界面更美观
        print(Panel.fit(
            f"[bold cyan]处理 {base_name} 组[/]\n\n"
            f"[green]目标文件夹:[/] {target_folder}\n"
            f"[green]要合并的文件夹:[/] {[f.name for f in other_folders]}",
            title="📁 文件夹合并任务",
            border_style="cyan"
        ))

        if preview_mode:
            print("[yellow]预览模式: 以下操作将被执行（但实际未执行）[/]")

        # 在非预览模式下，先备份所有相关文件夹
        if not preview_mode and backup_folder:
            print(f"[cyan]正在备份相关文件夹...[/]")
            for folder in [target_folder] + other_folders:
                backup_path = backup_folder / folder.name
                if safe_copy_folder(folder, backup_path):
                    print(f"[green]✓ 已备份: {folder.name}[/]")
                else:
                    print(f"[red]✗ 备份失败: {folder.name}，停止处理此组[/]")
                    continue
        
        # 安全地移动其他part文件夹中的内容到part 1
        for folder in other_folders:
            try:
                print(f"\n[cyan]合并 {folder.name} 到 {target_folder.name}[/]")

                if preview_mode:
                    # 预览模式：只显示将要执行的操作
                    for item in folder.iterdir():
                        print(f"[yellow]预览: 移动: {item.name} -> {target_folder.name}/[/]")
                    print(f"[yellow]预览: 删除空文件夹: {folder}[/]")
                    continue

                # 实际执行模式：安全地移动文件
                all_files_moved = True
                moved_files = []

                # 先尝试移动所有文件
                for item in folder.iterdir():
                    dest_path = target_folder / item.name

                    # 处理重名文件
                    if dest_path.exists():
                        print(f"[yellow]目标路径已存在，重命名: {item.name}[/]")
                        base, ext = os.path.splitext(item.name)
                        counter = 1
                        while dest_path.exists():
                            new_name = f"{base}_{counter}{ext}"
                            dest_path = target_folder / new_name
                            counter += 1

                    # 使用安全移动函数
                    if safe_move_file(item, dest_path):
                        print(f"[green]✓ 移动成功: {item.name} -> {dest_path.name}[/]")
                        moved_files.append((item, dest_path))
                    else:
                        print(f"[red]✗ 移动失败: {item.name}[/]")
                        all_files_moved = False
                        break

                # 只有在所有文件都成功移动后才删除原文件夹
                if all_files_moved:
                    try:
                        # 确认文件夹为空
                        if not any(folder.iterdir()):
                            folder.rmdir()
                            print(f"[green]✓ 删除空文件夹: {folder}[/]")
                        else:
                            print(f"[yellow]⚠️ 文件夹不为空，未删除: {folder}[/]")
                    except Exception as e:
                        print(f"[yellow]⚠️ 删除文件夹失败: {folder}, 错误: {e}[/]")
                else:
                    print(f"[red]✗ 由于文件移动失败，保留原文件夹: {folder}[/]")

            except Exception as e:
                print(f"[bold red]处理文件夹 {folder} 时出错: {e}[/]")
                print(f"[yellow]建议检查备份文件夹: {backup_folder}[/]")

        # 安全地重命名文件夹（去掉part 1）
        try:
            new_name = base_name
            new_path = target_folder.parent / new_name

            if preview_mode:
                if new_path.exists():
                    print(f"[yellow]预览: 目标路径已存在，将添加数字后缀: {new_name}[/]")
                print(f"[yellow]预览: 重命名文件夹: {target_folder.name} -> {new_name}[/]")
            else:
                # 处理重名情况
                if new_path.exists():
                    print(f"[yellow]目标路径已存在，添加数字后缀: {new_name}[/]")
                    counter = 1
                    while new_path.exists():
                        new_path = target_folder.parent / f"{new_name}_{counter}"
                        counter += 1

                # 安全重命名：先创建临时名称，再重命名到最终名称
                temp_name = f"{target_folder.name}_temp_{int(time.time())}"
                temp_path = target_folder.parent / temp_name

                try:
                    # 先重命名到临时名称
                    target_folder.rename(temp_path)
                    # 再重命名到最终名称
                    temp_path.rename(new_path)
                    print(f"[green]✓ 重命名文件夹: {target_folder.name} -> {new_path.name}[/]")
                    target_folder = new_path  # 更新target_folder为新的路径
                except Exception as rename_error:
                    # 如果重命名失败，尝试恢复原名称
                    if temp_path.exists():
                        try:
                            temp_path.rename(target_folder)
                        except:
                            pass
                    raise rename_error

        except Exception as e:
            print(f"[bold red]重命名文件夹失败: {e}[/]")
            print(f"[yellow]建议检查备份文件夹: {backup_folder}[/]")

    # 显示完成信息
    if not preview_mode and backup_folder:
        print(f"\n[bold green]✓ 合并操作完成！[/]")
        print(f"[cyan]备份文件夹位置: {backup_folder}[/]")
        print(f"[yellow]如果发现问题，可以从备份文件夹恢复数据[/]")

def get_multiple_paths(use_clipboard=False):
    """获取多个路径输入，支持剪贴板和手动输入"""
    paths = []
    
    # 从剪贴板读取路径
    if use_clipboard:
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                clipboard_paths = [p.strip().strip('"') for p in clipboard_content.splitlines() if p.strip()]
                for path in clipboard_paths:
                    try:
                        normalized_path = os.path.normpath(path)
                        if os.path.exists(normalized_path):
                            paths.append(normalized_path)
                            print(f"[green]📎 从剪贴板读取路径: {normalized_path}[/]")
                        else:
                            print(f"[yellow]⚠️ 警告: 路径不存在 - {path}[/]")
                    except Exception as e:
                        print(f"[yellow]⚠️ 警告: 路径处理失败 - {path}[/]")
                        print(f"[red]❌ 错误信息: {str(e)}[/]")
            else:
                print("[yellow]⚠️ 剪贴板为空[/]")
        except Exception as e:
            print(f"[yellow]⚠️ 警告: 剪贴板读取失败: {str(e)}[/]")
    
    # 如果没有使用剪贴板或剪贴板为空，使用手动输入
    if not paths:
        print("[cyan]请输入目录路径（每行一个，输入空行结束）:[/]")
        while True:
            path = console.input().strip()
            if not path:
                break
            
            try:
                path = path.strip().strip('"')
                normalized_path = os.path.normpath(path)
                
                if os.path.exists(normalized_path):
                    paths.append(normalized_path)
                    print(f"[green]已添加路径: {normalized_path}[/]")
                else:
                    print(f"[yellow]⚠️ 警告: 路径不存在 - {path}[/]")
            except Exception as e:
                print(f"[yellow]⚠️ 警告: 路径处理失败 - {path}[/]")
                print(f"[red]❌ 错误信息: {str(e)}[/]")
    
    if not paths:
        raise ValueError("[red]❌ 未输入有效路径[/]")
    return paths
