"""
cleaner 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import logging
import typer
from rich.console import Console

from .empty import remove_empty_folders
from .backup import remove_backup_and_temp

# 创建 Typer 应用
app = typer.Typer(help="文件清理工具 - 删除空文件夹和备份文件")

# 创建 Rich Console
console = Console()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("cleaner")

def get_paths_from_clipboard() -> List[Path]:
    """从剪贴板读取多行路径"""
    paths = []
    try:
        import pyperclip
        clipboard_content = pyperclip.paste()
        if clipboard_content:
            for line in clipboard_content.splitlines():
                if line := line.strip().strip('"').strip("'"):
                    path = Path(line)
                    if path.exists():
                        paths.append(path)
                    else:
                        logger.warning(f"警告：路径不存在 - {line}")
            
            logger.info(f"从剪贴板读取到 {len(paths)} 个有效路径")
    except ImportError:
        logger.warning("未安装pyperclip模块，无法从剪贴板读取。")
    except Exception as e:
        logger.warning(f"读取剪贴板失败: {e}")
    
    return paths

# Rich交互式界面 
def run_interactive() -> None:
    """运行交互式界面"""
    try:
        # 导入Rich库组件
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt, Confirm
        from rich.table import Table
        from rich.status import Status
        from rich.rule import Rule
        from rich import box
    except ImportError:
        logger.warning("未安装rich模块，无法使用交互式界面，将使用命令行模式")
        logger.info("提示: 可以通过 pip install rich 安装")
        return False
        
    # 创建控制台
    console = Console()
    
    # 自定义日志类，使用rich的格式
    class RichLogger:
        def info(self, message):
            console.print(message)
        def warning(self, message):
            console.print(f"[yellow]{message}[/yellow]")
        def error(self, message):
            console.print(f"[red]{message}[/red]")
    
    rich_logger = RichLogger()
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "# 文件清理工具\n\n一个用于清理文件夹的工具，提供空文件夹和备份文件清理功能",
        title="cleanf",
        border_style="blue"
    ))
    
    # 选择路径
    console.print("\n[bold blue]== 选择要处理的路径 ==[/bold blue]")
    paths = []
    
    console.print("请选择路径输入方式:")
    console.print("1. 从剪贴板读取路径")
    console.print("2. 手动输入路径")
    console.print("3. 浏览文件夹")
    
    choice = Prompt.ask("请选择", choices=["1", "2", "3"], default="1")
    
    # 从剪贴板读取
    if choice == "1":
        paths = get_paths_from_clipboard()
        
        if paths:
            table = Table(title="从剪贴板读取的路径")
            table.add_column("序号", style="cyan")
            table.add_column("路径", style="green")
            
            for i, path in enumerate(paths, 1):
                table.add_row(str(i), str(path))
                
            console.print(table)
        else:
            console.print("[yellow]未从剪贴板读取到任何有效路径[/yellow]")
            return False
    
    # 手动输入
    elif choice == "2":
        console.print("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            try:
                line = input().strip()
                if not line:
                    break
                
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    paths.append(path)
                else:
                    console.print(f"[yellow]警告：路径不存在 - {line}[/yellow]")
            except KeyboardInterrupt:
                console.print("\n[yellow]操作已取消[/yellow]")
                return False
    
    # 浏览文件夹（简化版）
    elif choice == "3":
        console.print("[yellow]暂不支持浏览文件夹，请使用其他方式输入路径[/yellow]")
        return False
    
    # 检查路径
    if not paths:
        console.print("[yellow]未选择任何路径，操作取消[/yellow]")
        return False
    
    # 选择要执行的操作
    console.print("\n[bold blue]== 选择要执行的操作 ==[/bold blue]")
    
    table = Table(title="可用操作")
    table.add_column("序号", style="cyan")
    table.add_column("操作", style="green")
    table.add_column("说明", style="magenta")
    
    table.add_row("1", "删除空文件夹", "递归删除所有空文件夹")
    table.add_row("2", "清理备份和临时文件", "删除备份文件(.bak)和临时文件夹")
    table.add_row("3", "全部执行", "执行以上所有操作")
    
    console.print(table)
    
    choice = Prompt.ask("请选择操作(多选请用逗号分隔，如1,2)", choices=["1", "2", "3"], default="3")
    
    operations = {
        "remove_empty": False,
        "clean_backup": False
    }
    
    # 设置操作标志
    choices = [c.strip() for c in choice.split(",")]
    if "1" in choices or "3" in choices:
        operations["remove_empty"] = True
    if "2" in choices or "3" in choices:
        operations["clean_backup"] = True
    
    # 选择排除关键词
    exclude_keywords = []
    if Confirm.ask("是否要排除某些文件夹/文件?", default=False):
        console.print("请输入排除关键词，多个关键词用逗号分隔:")
        keywords = input().strip()
        if keywords:
            exclude_keywords.extend([kw.strip() for kw in keywords.split(",")])
    
    # 处理每个路径
    total_empty_removed = 0
    total_backup_removed = 0
    
    for path in paths:
        console.print(Rule(f"处理目录: {path}"))
        
        if operations["remove_empty"]:
            console.print("\n[bold cyan]>>> 删除空文件夹...[/bold cyan]")
            removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, logger=rich_logger)
            total_empty_removed += removed
        
        if operations["clean_backup"]:
            console.print("\n[bold cyan]>>> 清理备份文件和临时文件夹...[/bold cyan]")
            removed, _ = remove_backup_and_temp(path, exclude_keywords=exclude_keywords, logger=rich_logger)
            total_backup_removed += removed
    
    # 输出总结信息
    console.print("\n[bold blue]清理总结:[/bold blue]")
    if operations["remove_empty"]:
        console.print(f"- 删除空文件夹: [green]{total_empty_removed}[/green] 个")
    if operations["clean_backup"]:
        console.print(f"- 删除备份和临时文件: [green]{total_backup_removed}[/green] 个")
    console.print(f"- 总计删除: [green]{total_empty_removed + total_backup_removed}[/green] 个项目")
    
    console.print("\n[bold green]操作已完成![/bold green]")
    console.print("按 [bold]Enter[/bold] 键退出...", end="")
    input()
    return True

@app.command()
def clean(
    paths: List[Path] = typer.Argument(None, help="要处理的路径列表", exists=True, dir_okay=True, file_okay=False),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启用交互式界面"),
    empty: bool = typer.Option(False, "--empty", "-e", help="删除空文件夹"),
    backup: bool = typer.Option(False, "--backup", "-b", help="删除备份文件和临时文件夹"),
    all: bool = typer.Option(False, "--all", "-a", help="执行所有清理操作"),
    exclude: Optional[str] = typer.Option(None, help="排除关键词列表，用逗号分隔多个关键词")
):
    """清理文件夹：删除空文件夹和备份文件"""
    # 如果使用交互式界面，或者不带任何参数
    if interactive or (len(sys.argv) == 1):
        if run_interactive():
            return
        # 如果交互式界面失败或返回False，继续使用命令行模式
    
    # 命令行模式
    # 处理清理模式参数
    remove_empty = empty or all
    clean_backup = backup or all
    
    if not (remove_empty or clean_backup):
        typer.echo("提示：未指定任何清理操作，默认执行所有清理操作")
        remove_empty = clean_backup = True
    
    # 获取要处理的路径
    path_list = []
    
    if clipboard:
        path_list.extend(get_paths_from_clipboard())
    
    if paths:
        path_list.extend(paths)
    
    if not path_list:
        typer.echo("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            try:
                line = input().strip()
                if not line:
                    break
                
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    path_list.append(path)
                else:
                    typer.echo(f"警告：路径不存在 - {line}", err=True)
            except KeyboardInterrupt:
                typer.echo("\n操作已取消")
                return
    
    if not path_list:
        typer.echo("未提供任何有效的路径", err=True)
        raise typer.Exit(code=1)
    
    # 处理排除关键词
    exclude_keywords = []
    if exclude:
        exclude_keywords.extend(exclude.split(','))
    
    # 处理每个路径
    total_empty_removed = 0
    total_backup_removed = 0
    
    for path in path_list:
        typer.echo(f"\n处理目录: {path}")
        
        if remove_empty:
            typer.echo("\n>>> 删除空文件夹...")
            removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, logger=logger)
            total_empty_removed += removed
        
        if clean_backup:
            typer.echo("\n>>> 清理备份文件和临时文件夹...")
            removed, _ = remove_backup_and_temp(path, exclude_keywords=exclude_keywords, logger=logger)
            total_backup_removed += removed
    
    typer.echo("\n清理总结:")
    if remove_empty:
        typer.echo(f"- 删除空文件夹: {total_empty_removed} 个")
    if clean_backup:
        typer.echo(f"- 删除备份和临时文件: {total_backup_removed} 个")
    typer.echo(f"- 总计删除: {total_empty_removed + total_backup_removed} 个项目")

def main():
    """主入口函数"""
    # 检查是否没有提供任何参数，直接启动交互式界面
    if len(sys.argv) == 1:
        if run_interactive():
            return
    
    # 使用 Typer 处理命令行
    app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        typer.echo("\n操作已取消")
    except Exception as e:
        typer.echo(f"发生错误: {e}", err=True)
        sys.exit(1)