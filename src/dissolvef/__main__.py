"""
dissolve 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Literal
import logging
import typer
from enum import Enum
from rich.console import Console

from dissolvef.nested import flatten_single_subfolder
from dissolvef.media import release_single_media_folder
from dissolvef.direct import dissolve_folder
from dissolvef.archive import release_single_archive_folder

# 创建 Typer 应用
app = typer.Typer(help="文件夹解散工具 - 解散嵌套文件夹和释放单媒体文件夹")

# 创建 Rich Console
console = Console()

# 配置日志
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,     )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="dissolvef", console_output=True)

# 定义冲突处理策略
class ConflictStrategy(str, Enum):
    AUTO = "auto"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"

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
        "# 文件夹解散工具\n\n一个用于解散和整理文件夹结构的工具",
        title="dissolvef",
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
    
    table.add_row("1", "解散单媒体文件夹", "解散只包含单个媒体文件的文件夹")
    table.add_row("2", "解散嵌套的单一文件夹", "解散只有一个子文件夹的嵌套文件夹")
    table.add_row("3", "直接解散指定文件夹", "将整个文件夹的内容移动到其父文件夹")
    table.add_row("4", "全部功能（除直接解散）", "执行选项1和2的操作")
    table.add_row("5", "解散单压缩包文件夹", "解散只包含单个压缩包的文件夹")
    
    console.print(table)
    
    choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "4", "5"], default="4")
    
    operations = {
        "media_mode": False,
        "nested_mode": False,
        "direct_mode": False,
        "archive_mode": False
    }
    
    # 设置操作标志
    if choice == "1" or choice == "4":
        operations["media_mode"] = True
    if choice == "2" or choice == "4":
        operations["nested_mode"] = True
    if choice == "3":
        operations["direct_mode"] = True
    if choice == "5":
        operations["archive_mode"] = True
    
    # 选择排除关键词
    exclude_keywords = []
    if (operations["media_mode"] or operations["nested_mode"]) and Confirm.ask("是否要排除某些文件夹/文件?", default=False):
        console.print("请输入排除关键词，多个关键词用逗号分隔:")
        keywords = input().strip()
        if keywords:
            exclude_keywords.extend([kw.strip() for kw in keywords.split(",")])
    
    # 如果选择直接解散，设置冲突处理方式
    file_conflict = dir_conflict = 'auto'
    if operations["direct_mode"]:
        console.print("\n[bold blue]== 冲突处理方式 ==[/bold blue]")
        console.print("当目标位置已存在同名文件或文件夹时的处理方式")
        
        file_conflict = Prompt.ask(
            "文件冲突处理方式", 
            choices=["auto", "skip", "overwrite", "rename"], 
            default="auto"
        )
        
        dir_conflict = Prompt.ask(
            "文件夹冲突处理方式", 
            choices=["auto", "skip", "overwrite", "rename"], 
            default="auto"
        )
        
        console.print(f"文件冲突处理: [green]{file_conflict}[/green] (auto代表跳过)")
        console.print(f"文件夹冲突处理: [green]{dir_conflict}[/green] (auto代表合并)")
    
    # 询问是否预览
    preview_mode = Confirm.ask("是否启用预览模式(不实际执行操作)?", default=False)
    
    # 处理每个路径
    total_dissolved_folders = 0
    total_dissolved_files = 0
    total_dissolved_dirs = 0
    total_flattened_nested = 0
    total_released_media = 0
    total_released_archive = 0
    
    if operations["direct_mode"]:
        # 直接解散模式
        console.print("\n[bold cyan]>>> 执行直接解散文件夹操作...[/bold cyan]")
        for path in paths:
            console.print(Rule(f"处理目录: {path}"))
            success, files_count, dirs_count = dissolve_folder(
                path, 
                file_conflict=file_conflict,
                dir_conflict=dir_conflict,
                preview=preview_mode,
                use_status=False
            )
            if success or preview_mode:
                total_dissolved_folders += 1
                total_dissolved_files += files_count
                total_dissolved_dirs += dirs_count
    else:
        # 其他解散模式
        for path in paths:
            console.print(Rule(f"处理目录: {path}"))
            if operations["media_mode"]:
                console.print("\n[bold cyan]>>> 解散单媒体文件夹...[/bold cyan]")
                count = release_single_media_folder(path, exclude_keywords, preview_mode)
                total_released_media += count
            if operations["nested_mode"]:
                console.print("\n[bold cyan]>>> 解散嵌套的单一文件夹...[/bold cyan]")
                result = flatten_single_subfolder(path, exclude_keywords)
                # 兼容新返回值 (count, skipped)
                count = result[0] if isinstance(result, tuple) else result
                total_flattened_nested += count
            if operations["archive_mode"]:
                console.print("\n[bold cyan]>>> 解散单压缩包文件夹...[/bold cyan]")
                result = release_single_archive_folder(path, exclude_keywords, preview_mode)
                # 兼容新返回值 (count, skipped)
                count = result[0] if isinstance(result, tuple) else result
                total_released_archive += count
    
    # 输出操作总结
    console.print("\n[bold blue]解散操作总结:[/bold blue]")
    mode_prefix = "将" if preview_mode else "已"
    
    if operations["direct_mode"]:
        console.print(f"- {mode_prefix}解散 [green]{total_dissolved_folders}[/green] 个文件夹")
        console.print(f"- {mode_prefix}移动 [green]{total_dissolved_files}[/green] 个文件")
        console.print(f"- {mode_prefix}移动 [green]{total_dissolved_dirs}[/green] 个文件夹")
    else:
        if operations["media_mode"]:
            console.print(f"- {mode_prefix}解散 [green]{total_released_media}[/green] 个单媒体文件夹")
        if operations["nested_mode"]:
            console.print(f"- {mode_prefix}解散 [green]{total_flattened_nested}[/green] 个嵌套文件夹")
        if operations["archive_mode"]:
            console.print(f"- {mode_prefix}解散 [green]{total_released_archive}[/green] 个单压缩包文件夹")
    
    if preview_mode:
        console.print("\n[yellow]注意：这是预览模式，实际操作未执行[/yellow]")
    
    console.print("\n[bold green]操作已完成![/bold green]")
    console.print("按 [bold]Enter[/bold] 键退出...", end="")
    input()
    return True

@app.command()
def dissolve(
    paths: List[Path] = typer.Argument(None, help="要处理的路径列表", exists=True, dir_okay=True, file_okay=False),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启用交互式界面"),
    direct: bool = typer.Option(False, "--direct", "-d", help="直接解散指定文件夹"),
    nested: bool = typer.Option(False, "--nested", "-n", help="解散嵌套的单一文件夹"),
    media: bool = typer.Option(False, "--media", "-m", help="解散单媒体文件夹"),
    all: bool = typer.Option(False, "--all", "-a", help="执行所有解散操作（不含直接解散）"),
    file_conflict: ConflictStrategy = typer.Option(
        ConflictStrategy.AUTO, help="文件冲突处理方式 (仅用于直接解散模式)"
    ),
    dir_conflict: ConflictStrategy = typer.Option(
        ConflictStrategy.AUTO, help="文件夹冲突处理方式 (仅用于直接解散模式)"
    ),
    exclude: Optional[str] = typer.Option(None, help="排除关键词列表，用逗号分隔多个关键词"),
    preview: bool = typer.Option(False, "--preview", "-p", help="预览模式，不实际执行操作"),
    archive: bool = typer.Option(False, "--archive", "-z", help="解散单压缩包文件夹")
):
    """解散文件夹：解散嵌套文件夹、单媒体文件夹或直接解散文件夹"""
    # 如果使用交互式界面，或者不带任何参数
    if interactive or (len(sys.argv) == 1):
        if run_interactive():
            return
        # 如果交互式界面失败或返回False，继续使用命令行模式
    
    # 处理解散模式参数
    nested_mode = nested or all
    media_mode = media or all
    archive_mode = archive or all
    # 至少选择一种模式
    if not (direct or nested_mode or media_mode or archive_mode):
        typer.echo("提示：未指定任何解散操作，默认执行单媒体文件夹解散")
        media_mode = True
    
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
        typer.echo("错误: 未提供任何有效的路径", err=True)
        raise typer.Exit(code=1)
    
    # 处理排除关键词
    exclude_keywords = []
    if exclude:
        exclude_keywords.extend(exclude.split(','))
    
    # 处理每个路径
    total_dissolved_folders = 0
    total_dissolved_files = 0
    total_dissolved_dirs = 0
    total_flattened_nested = 0
    total_released_media = 0
    total_released_archive = 0
    
    if direct:
        # 直接解散模式
        typer.echo("\n>>> 执行直接解散文件夹操作...")
        for path in path_list:
            typer.echo(f"\n处理目录: {path}")
            success, files_count, dirs_count = dissolve_folder(
                path, 
                file_conflict=str(file_conflict),
                dir_conflict=str(dir_conflict),
                preview=preview
            )
            if success or preview:
                total_dissolved_folders += 1
                total_dissolved_files += files_count
                total_dissolved_dirs += dirs_count
    else:
        # 其他解散模式
        for path in path_list:
            typer.echo(f"\n处理目录: {path}")
            if media_mode:
                typer.echo("\n>>> 解散单媒体文件夹...")
                count = release_single_media_folder(path, exclude_keywords, preview)
                total_released_media += count
            if nested_mode:
                typer.echo("\n>>> 解散嵌套的单一文件夹...")
                result = flatten_single_subfolder(path, exclude_keywords)
                count = result[0] if isinstance(result, tuple) else result
                total_flattened_nested += count
            if archive_mode:
                typer.echo("\n>>> 解散单压缩包文件夹...")
                result = release_single_archive_folder(path, exclude_keywords, preview)
                count = result[0] if isinstance(result, tuple) else result
                total_released_archive += count
    
    # 输出操作总结
    typer.echo("\n解散操作总结:")
    mode_prefix = "将" if preview else "已"
    
    if direct:
        typer.echo(f"- {mode_prefix}解散 {total_dissolved_folders} 个文件夹")
        typer.echo(f"- {mode_prefix}移动 {total_dissolved_files} 个文件")
        typer.echo(f"- {mode_prefix}移动 {total_dissolved_dirs} 个文件夹")
    else:
        if media_mode:
            typer.echo(f"- {mode_prefix}解散 {total_released_media} 个单媒体文件夹")
        if nested_mode:
            typer.echo(f"- {mode_prefix}解散 {total_flattened_nested} 个嵌套文件夹")
        if archive_mode:
            typer.echo(f"- {mode_prefix}解散 {total_released_archive} 个单压缩包文件夹")
    
    if preview:
        typer.echo("注意：这是预览模式，实际操作未执行")

if __name__ == "__main__":

    app()
