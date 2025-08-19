"""
mergef 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
import os
import shutil
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print
import pyperclip
import logging
from loguru import logger

from mergef.merge_part import merge_part_folders, get_multiple_paths

# 创建 Typer 应用
app = typer.Typer(help="文件夹合并工具 - 合并同名的part文件夹")

# 创建 Rich Console
console = Console()

@app.command()
def merge(
    paths: List[str] = typer.Argument(None, help="要处理的路径，可以指定多个"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    preview: bool = typer.Option(False, "--preview", "-p", help="预览模式，不实际执行操作")
):
    """
    安全合并同名的part文件夹（推荐使用）

    此命令会自动创建备份，使用安全的文件操作方式
    """
    _execute_merge(paths, clipboard, preview)

@app.command()
def merge_unsafe(
    paths: List[str] = typer.Argument(None, help="要处理的路径，可以指定多个"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    preview: bool = typer.Option(False, "--preview", "-p", help="预览模式，不实际执行操作")
):
    """
    不安全的合并模式（不推荐，仅用于兼容性）

    ⚠️ 警告：此模式可能导致数据丢失，建议使用 merge 命令
    """
    console.print("[bold red]⚠️ 警告：您正在使用不安全的合并模式！[/]")
    console.print("[yellow]建议使用 'mergef merge' 命令进行安全合并[/]")

    if not preview:
        confirm = typer.confirm("确定要继续使用不安全模式吗？")
        if not confirm:
            console.print("[green]已取消操作，建议使用安全模式[/]")
            return

    # 这里可以调用原来的不安全逻辑（如果需要保留的话）
    _execute_merge(paths, clipboard, preview)

def _execute_merge(paths, clipboard, preview):
    try:
        # 设置预览模式
        if preview:
            console.print("[bold yellow]预览模式已启用，将只显示将要执行的操作，不会实际修改文件[/]")

        # 获取路径
        target_paths = []

        if paths:
            target_paths = [os.path.normpath(p) for p in paths if os.path.exists(p)]

        if not target_paths:
            target_paths = get_multiple_paths(clipboard)
              # 处理每个路径
        with Progress() as progress:
            task = progress.add_task("[cyan]处理路径...", total=len(target_paths))

            for path in target_paths:
                console.print(f"\n[bold blue]开始处理路径:[/] {path}")
                try:
                    merge_part_folders(path, preview_mode=preview)
                except Exception as e:
                    console.print(f"[bold red]处理路径 {path} 时出错: {e}[/]")
                    logger.exception(f"处理路径 {path} 时出错")
                finally:
                    progress.update(task, advance=1)

        if not preview:
            console.print("\n[bold green]✓ 合并操作已完成[/]")
        else:
            console.print("\n[bold yellow]✓ 预览完成，未执行实际操作[/]")

    except ValueError as e:
        console.print(f"[bold red]{str(e)}[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]发生错误: {str(e)}[/]")
        logger.exception("执行过程中发生错误")
        sys.exit(1)

@app.command()
def restore(
    backup_path: str = typer.Argument(help="备份文件夹路径"),
    target_path: str = typer.Argument(help="恢复到的目标路径")
):
    """
    从备份文件夹恢复数据

    用于在合并操作出现问题时恢复原始数据
    """
    try:
        backup_folder = Path(backup_path)
        target_folder = Path(target_path)

        if not backup_folder.exists():
            console.print(f"[bold red]备份文件夹不存在: {backup_path}[/]")
            return

        if not backup_folder.is_dir():
            console.print(f"[bold red]指定的路径不是文件夹: {backup_path}[/]")
            return

        console.print(f"[cyan]准备从备份恢复数据...[/]")
        console.print(f"[yellow]备份源: {backup_folder}[/]")
        console.print(f"[yellow]恢复到: {target_folder}[/]")

        confirm = typer.confirm("确定要执行恢复操作吗？这将覆盖目标位置的现有文件")
        if not confirm:
            console.print("[yellow]恢复操作已取消[/]")
            return

        # 确保目标目录存在
        target_folder.mkdir(parents=True, exist_ok=True)

        # 恢复每个备份的文件夹
        restored_count = 0
        for backup_item in backup_folder.iterdir():
            if backup_item.is_dir():
                restore_target = target_folder / backup_item.name

                # 如果目标已存在，先删除
                if restore_target.exists():
                    shutil.rmtree(restore_target)

                # 复制备份文件夹到目标位置
                shutil.copytree(backup_item, restore_target)
                console.print(f"[green]✓ 已恢复: {backup_item.name}[/]")
                restored_count += 1

        console.print(f"\n[bold green]✓ 恢复完成！共恢复 {restored_count} 个文件夹[/]")

    except Exception as e:
        console.print(f"[bold red]恢复过程中发生错误: {str(e)}[/]")
        logger.exception("恢复过程中发生错误")

@app.command()
def list_backups(
    path: str = typer.Argument(".", help="要搜索备份的路径，默认为当前目录")
):
    """
    列出指定路径下的所有备份文件夹
    """
    try:
        search_path = Path(path)
        if not search_path.exists():
            console.print(f"[bold red]路径不存在: {path}[/]")
            return

        backup_folders = []
        for item in search_path.iterdir():
            if item.is_dir() and item.name.startswith("mergef_backup_"):
                backup_folders.append(item)

        if not backup_folders:
            console.print(f"[yellow]在 {path} 中未找到任何备份文件夹[/]")
            return

        console.print(f"[cyan]在 {path} 中找到以下备份文件夹:[/]")
        for backup in sorted(backup_folders, key=lambda x: x.name):
            # 提取时间戳
            timestamp_part = backup.name.replace("mergef_backup_", "")
            try:
                # 尝试解析时间戳
                from datetime import datetime
                dt = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = timestamp_part

            console.print(f"  [green]{backup.name}[/] (创建时间: {time_str})")

        console.print(f"\n[yellow]使用 'mergef restore <备份路径> <目标路径>' 来恢复数据[/]")

    except Exception as e:
        console.print(f"[bold red]列出备份时发生错误: {str(e)}[/]")

def run_interactive() -> None:
    """提供Rich交互式界面"""
    console.print(Panel.fit(
        "[bold green]Part文件夹合并工具[/]\n"
        "此工具用于合并同名的part文件夹（如 movie part1, movie part2 等）",
        title="mergef"
    ))
    
    # 询问用户是否使用剪贴板
    use_clipboard = Confirm.ask("是否从剪贴板读取路径？", default=True)
    preview_mode = Confirm.ask("是否启用预览模式（不实际执行操作）？", default=False)
    
    try:
        paths = get_multiple_paths(use_clipboard)
          # 处理每个路径
        with Progress() as progress:
            task = progress.add_task("[cyan]处理路径...", total=len(paths))
            
            for path in paths:
                console.print(f"\n[bold blue]开始处理路径:[/] {path}")
                try:
                    merge_part_folders(path, preview_mode=preview_mode)
                except Exception as e:
                    console.print(f"[bold red]处理路径 {path} 时出错: {e}[/]")
                    logger.exception(f"处理路径 {path} 时出错")
                finally:
                    progress.update(task, advance=1)
        
        if not preview_mode:
            console.print("\n[bold green]✓ 合并操作已完成[/]")
        else:
            console.print("\n[bold yellow]✓ 预览完成，未执行实际操作[/]")
            
    except ValueError as e:
        console.print(f"[bold red]{str(e)}[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]发生错误: {str(e)}[/]")
        logger.exception("执行过程中发生错误")
        sys.exit(1)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """mergef 包的主入口点"""
    if ctx.invoked_subcommand is None:
        run_interactive()

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]发生错误: {str(e)}[/]")
        sys.exit(1)
