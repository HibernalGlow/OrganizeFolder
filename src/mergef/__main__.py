"""
mergef 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
import os
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

from .merge_part import merge_part_folders, get_multiple_paths

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
    合并同名的part文件夹
    
    此命令会查找并合并类似 'movie part1'、'movie part2' 这样的分段文件夹
    """
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
