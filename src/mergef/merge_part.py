"""
合并同名的part文件夹核心功能模块
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

# 创建 Rich Console
console = Console()

def get_base_name(folder_name):
    """获取文件夹的基本名称（去掉part部分）"""
    # 修改后的正则表达式，支持 part/p 两种前缀格式
    pattern = r'^(.+?)(?:[-_ ]*(?:part|p)[-_ ]*\d+)$'
    match = re.match(pattern, folder_name, re.IGNORECASE)
    return match.group(1).strip() if match else None

def merge_part_folders(base_path, preview_mode=False):
    """
    合并同名的part文件夹
    
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
        
        # 移动其他part文件夹中的内容到part 1
        for folder in other_folders:
            try:
                print(f"\n[cyan]合并 {folder.name} 到 {target_folder.name}[/]")
                # 创建临时文件夹用于解散操作
                temp_folder = target_folder / f"temp_{folder.name}"
                
                if not preview_mode:
                    temp_folder.mkdir(exist_ok=True)
                else:
                    print(f"[yellow]预览: 创建临时文件夹 {temp_folder}[/]")
                
                # 先将文件移动到临时文件夹
                file_count = 0
                for item in folder.iterdir():
                    dest_path = temp_folder / item.name
                    if not preview_mode and dest_path.exists():
                        print(f"[yellow]目标路径已存在，重命名: {item.name}[/]")
                        base, ext = os.path.splitext(item.name)
                        counter = 1
                        while dest_path.exists():
                            new_name = f"{base}_{counter}{ext}"
                            dest_path = temp_folder / new_name
                            counter += 1
                    
                    if preview_mode:
                        print(f"[yellow]预览: 移动: {item.name} -> {dest_path}[/]")
                    else:
                        print(f"[green]移动: {item.name} -> {dest_path}[/]")
                        shutil.move(str(item), str(dest_path))
                    file_count += 1
                
                # 删除空文件夹
                if preview_mode:
                    print(f"[yellow]预览: 删除空文件夹: {folder}[/]")
                else:
                    folder.rmdir()
                    print(f"[green]删除空文件夹: {folder}[/]")
                
                # 对临时文件夹进行解散操作
                # script_path = Path(__file__).parent.parent / 'dissolvef' / 'direct.py'
                # if script_path.exists():
                print(f"\n[cyan]解散文件夹内容: {temp_folder}[/]")
                if preview_mode:
                    print(f"[yellow]预览: 调用解散文件夹脚本处理 {temp_folder}[/]")
                else:
                    try:
                        # 导入并直接调用模块函数而不是使用subprocess
                        from dissolvef import dissolve_folder
                        dissolve_folder(temp_folder)
                    except ImportError:
                        print("[yellow]无法导入解散文件夹模块，尝试使用子进程调用[/]")
                        # try:
                        #     subprocess.run(['python', str(script_path), str(temp_folder)], check=True)
                        # except subprocess.CalledProcessError as e:
                        #     print(f"[red]调用解散文件夹脚本失败: {e}[/]")
                
                # 将解散后的文件移动到目标文件夹
                if not preview_mode:
                    for item in temp_folder.iterdir():
                        final_dest = target_folder / item.name
                        if final_dest.exists():
                            base, ext = os.path.splitext(item.name)
                            counter = 1
                            while final_dest.exists():
                                new_name = f"{base}_{counter}{ext}"
                                final_dest = target_folder / new_name
                                counter += 1
                        shutil.move(str(item), str(final_dest))
                    
                    # 删除临时文件夹
                    temp_folder.rmdir()
                else:
                    print(f"[yellow]预览: 将临时文件夹内容移动到目标文件夹 {target_folder}[/]")
                    print(f"[yellow]预览: 删除临时文件夹 {temp_folder}[/]")
                
            except Exception as e:
                print(f"[bold red]处理文件夹 {folder} 时出错: {e}[/]")
                if not preview_mode and temp_folder.exists():
                    shutil.rmtree(str(temp_folder))
        
        # 重命名文件夹（去掉part 1）
        try:
            new_name = base_name
            new_path = target_folder.parent / new_name
            
            if preview_mode:
                if new_path.exists():
                    print(f"[yellow]预览: 目标路径已存在，将添加数字后缀: {new_name}[/]")
                print(f"[yellow]预览: 重命名文件夹: {target_folder.name} -> {new_name}[/]")
            else:
                if new_path.exists():
                    print(f"[yellow]目标路径已存在，添加数字后缀: {new_name}[/]")
                    counter = 1
                    while new_path.exists():
                        new_path = target_folder.parent / f"{new_name}_{counter}"
                        counter += 1
                
                target_folder.rename(new_path)
                print(f"[green]重命名文件夹: {target_folder.name} -> {new_path.name}[/]")
                target_folder = new_path  # 更新target_folder为新的路径
        except Exception as e:
            print(f"[bold red]重命名文件夹失败: {e}[/]")

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
