"""
文件时间戳恢复工具
从文件名中识别日期并恢复文件的时间戳
"""
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from loguru import logger

from restoret.core.extract_date import extract_date_from_filename
from restoret.core.restore_timestamp import restore_file_timestamp
from restoret.interactive import run_interactive

console = Console()
app = typer.Typer(help="文件时间戳恢复工具")

def get_paths_from_clipboard() -> List[Path]:
    """从剪贴板获取路径列表"""
    try:
        import pyperclip
        clipboard_content = pyperclip.paste()
        paths = []
        if clipboard_content:
            for line in clipboard_content.splitlines():
                if line := line.strip().strip('"').strip("'"):
                    path = Path(line)
                    if path.exists():
                        paths.append(path)
                    else:
                        console.print(f"[yellow]警告：路径不存在[/yellow] - {line}")
        return paths
    except ImportError:
        console.print("[yellow]警告：未安装pyperclip模块，无法从剪贴板读取[/yellow]")
        return []
    except Exception as e:
        console.print(f"[red]从剪贴板读取失败[/red]: {e}")
        return []

def collect_files(path: Path) -> List[Path]:
    """收集指定路径下的所有文件"""
    files = []
    if path.is_file():
        files.append(path)
    elif path.is_dir():
        for item in path.rglob('*'):
            if item.is_file():
                files.append(item)
    return files

@app.command()
def restore(
    paths: List[Path] = typer.Argument(None, help="要处理的文件或文件夹路径列表"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    preview: bool = typer.Option(False, "--preview", "-p", help="预览模式，只显示将要执行的操作"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启动交互式界面"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r", help="递归处理子文件夹"),
):
    """恢复文件时间戳"""
    
    # 如果指定了交互式模式，直接启动交互式界面
    if interactive:
        run_interactive()
        return
    
    # 获取要处理的路径
    path_list = []
    
    if clipboard:
        path_list.extend(get_paths_from_clipboard())
    
    if paths:
        path_list.extend(paths)
    
    if not path_list:
        console.print("请输入要处理的文件或文件夹路径，每行一个，输入空行结束:")
        while True:
            try:
                line = input().strip()
                if not line:
                    break
                
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    path_list.append(path)
                else:
                    console.print(f"[yellow]警告：路径不存在[/yellow] - {line}")
            except KeyboardInterrupt:
                console.print("\n操作已取消")
                return
    
    if not path_list:
        console.print("[red]错误: 未提供任何有效的路径[/red]")
        raise typer.Exit(code=1)
    
    # 收集所有文件
    all_files = []
    for path in path_list:
        files = collect_files(path)
        all_files.extend(files)
    
    if not all_files:
        console.print("[yellow]未找到任何文件[/yellow]")
        return
    
    console.print(f"[cyan]找到 {len(all_files)} 个文件[/cyan]")
    
    # 分析文件并提取日期
    processable_files = []
    skipped_files = []
    
    console.print("\n[bold]分析文件名中的日期...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("分析文件...", total=len(all_files))
        
        for file_path in all_files:
            progress.update(task, description=f"分析: {file_path.name}")
            
            extracted_date = extract_date_from_filename(file_path.name)
            if extracted_date:
                processable_files.append((file_path, extracted_date))
                logger.info(f"从 '{file_path.name}' 提取到日期: {extracted_date}")
            else:
                skipped_files.append(file_path)
                logger.debug(f"未能从 '{file_path.name}' 提取日期")
            
            progress.advance(task)
    
    # 显示统计信息
    console.print(f"\n[green]可处理文件: {len(processable_files)}[/green]")
    console.print(f"[yellow]跳过文件: {len(skipped_files)}[/yellow]")
    
    if not processable_files:
        console.print("[yellow]没有找到可处理的文件[/yellow]")
        return
    
    # 显示预览表格
    if preview or len(processable_files) <= 10:
        table = Table(show_header=True)
        table.add_column("文件名", style="cyan")
        table.add_column("识别日期", style="green")
        table.add_column("当前修改时间", style="yellow")
        
        show_count = min(10, len(processable_files))
        for file_path, extracted_date in processable_files[:show_count]:
            current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            table.add_row(
                file_path.name,
                extracted_date.strftime("%Y-%m-%d"),
                current_mtime.strftime("%Y-%m-%d %H:%M:%S")
            )
        
        if len(processable_files) > 10:
            table.add_row("...", "...", "...")
        
        console.print(table)
    
    if preview:
        console.print("\n[yellow]预览模式：以上操作将被执行（但实际未执行）[/yellow]")
        return
    
    # 确认执行
    if not typer.confirm("确认恢复这些文件的时间戳？"):
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 执行时间戳恢复
    console.print("\n[bold]恢复文件时间戳...[/bold]")
    
    success_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("恢复时间戳...", total=len(processable_files))
        
        for file_path, extracted_date in processable_files:
            progress.update(task, description=f"处理: {file_path.name}")
            
            try:
                restore_file_timestamp(file_path, extracted_date)
                success_count += 1
                logger.info(f"已恢复 {file_path} 的时间戳为 {extracted_date}")
            except Exception as e:
                error_count += 1
                logger.error(f"恢复 {file_path} 时间戳失败: {e}")
                console.print(f"[red]错误[/red]: {file_path.name} - {e}")
            
            progress.advance(task)
    
    # 显示结果
    console.print(Panel.fit(
        f"[green]成功处理: {success_count}[/green]\n"
        f"[red]处理失败: {error_count}[/red]\n"
        f"[yellow]跳过文件: {len(skipped_files)}[/yellow]",
        title="📊 处理结果",
        border_style="green"
    ))

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """文件时间戳恢复工具主入口"""
    if ctx.invoked_subcommand is None:
        # 如果没有指定子命令，启动交互式界面
        run_interactive()

if __name__ == "__main__":
    app()
