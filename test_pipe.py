"""
migrate 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.prompt import Prompt
from loguru import logger
from datetime import datetime

# 导入我们的模块
from .input import (
    get_stdin_files, 
    get_source_files_interactively, 
    get_target_dir_interactively,
    get_paths_from_clipboard
)
from .migrate import migrate_files_with_structure

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
    import os
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


logger, config_info = setup_logger(app_name="migratef", console_output=True)

# 创建 Typer 应用
app = typer.Typer(help="文件迁移工具 - 保持目录结构迁移文件")

# 初始化 Rich Console，用于用户交互
console = Console()


@app.command()
def migrate(
    files: List[Path] = typer.Argument(None, help="要迁移的文件列表"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取文件路径"),
    target: Optional[Path] = typer.Option(None, "--target", "-t", help="目标文件夹路径"),
    threads: Optional[int] = typer.Option(None, "--threads", help="使用的线程数量"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启用交互式界面"),
    copy: bool = typer.Option(False, "--copy", help="复制文件而不是移动"),
    move: bool = typer.Option(True, "--move", help="移动文件而不是复制"),
):
    """迁移文件，并保持目录结构"""
    
    # 获取管道输入
    stdin_files = get_stdin_files()
    
    # 如果有管道输入且指定了目标目录，直接处理
    if stdin_files and target:
        action_choice = "copy" if copy else "move"
        logger.info(f"从管道接收到 {len(stdin_files)} 个文件，目标目录: {target}")
        migrate_files_with_structure(stdin_files, str(target), max_workers=threads or 16, action=action_choice)
        return
    
    # 如果有管道输入且没有指定目标目录，进入交互模式
    if stdin_files and not target:
        logger.info(f"从管道接收到 {len(stdin_files)} 个文件，进入交互模式")
        target_dir = get_target_dir_interactively()
        # 询问操作类型
        action_choice = Prompt.ask(
            "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
            choices=["copy", "move"],
            default="move"
        ).lower()
        # 执行迁移
        migrate_files_with_structure(stdin_files, target_dir, max_workers=threads or 16, action=action_choice)
        return
    
    # 如果指定了交互式界面或没有任何参数且没有管道输入，启动交互式界面
    if interactive or (not files and not stdin_files and not clipboard):
        # 交互式获取源文件
        source_files = get_source_files_interactively()
        # 交互式获取目标目录
        if source_files:
            target_dir = get_target_dir_interactively()
            # 询问操作类型
            action_choice = Prompt.ask(
                "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
                choices=["copy", "move"],
                default="move"
            ).lower()
            # 执行迁移
            migrate_files_with_structure(source_files, target_dir, max_workers=threads or 16, action=action_choice)
        return    
    
    # 命令行模式
    source_files = []
    
    # 先添加管道输入的文件
    if stdin_files:
        source_files.extend(stdin_files)
    
    # 添加从剪贴板读取的文件
    if clipboard:
        clipboard_files = get_paths_from_clipboard()
        source_files.extend(clipboard_files)
    
    # 添加命令行参数指定的文件
    if files:
        for file_path in files:
            if file_path.exists() and file_path.is_file():
                source_files.append(str(file_path.resolve()))
            else:
                logger.warning(f"跳过无效文件: {file_path}")
    
    if not source_files:
        logger.error("没有提供有效的源文件")
        console.print("[red]错误: 没有提供有效的源文件[/red]")
        console.print("使用 --interactive 选项启动交互式界面，或使用 --clipboard 从剪贴板读取路径")
        raise typer.Exit(code=1)
    
    # 获取目标目录
    if target:
        target_dir = str(target.resolve())
    else:
        target_dir = get_target_dir_interactively()
    
    # 确定操作类型
    action_choice = "copy" if copy else "move"
    
    # 执行迁移
    migrate_files_with_structure(source_files, target_dir, max_workers=threads or 16, action=action_choice)


@app.command()
def quick(
    source: List[str] = typer.Argument(..., help="源文件路径列表"),
    target: str = typer.Argument(..., help="目标目录路径"),
    threads: Optional[int] = typer.Option(16, "--threads", help="使用的线程数量"),
    action: str = typer.Option("move", "--action", help="操作类型: copy 或 move"),
):
    """快速迁移模式 - 直接指定源文件和目标目录"""
    
    # 验证操作类型
    if action not in ["copy", "move"]:
        logger.error(f"无效的操作类型: {action}")
        console.print(f"[red]错误: 无效的操作类型 '{action}'，只支持 'copy' 或 'move'[/red]")
        raise typer.Exit(code=1)
    
    # 验证源文件
    valid_sources = []
    for src in source:
        src_path = Path(src)
        if src_path.exists() and src_path.is_file():
            valid_sources.append(src)
        else:
            logger.warning(f"跳过无效文件: {src}")
    
    if not valid_sources:
        logger.error("没有提供有效的源文件")
        console.print("[red]错误: 没有提供有效的源文件[/red]")
        raise typer.Exit(code=1)
    
    logger.info(f"快速迁移模式: {len(valid_sources)} 个文件 -> {target}")
    
    # 执行迁移
    migrate_files_with_structure(valid_sources, target, max_workers=threads, action=action)


def main():
    """主入口函数"""
    # 获取管道输入
    stdin_files = get_stdin_files()
    
    # 如果有管道输入且没有其他命令行参数，进入交互模式
    if stdin_files and len(sys.argv) == 1:
        logger.info(f"从管道接收到 {len(stdin_files)} 个文件，进入交互模式")
        target_dir = get_target_dir_interactively()
        # 询问操作类型
        action_choice = Prompt.ask(
            "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
            choices=["copy", "move"],
            default="move"
        ).lower()
        # 执行迁移
        migrate_files_with_structure(stdin_files, target_dir, max_workers=16, action=action_choice)
        return
    
    # 检查是否没有提供任何参数且没有管道输入，直接启动交互式界面
    if len(sys.argv) == 1 and not stdin_files:
        # 交互式获取源文件
        source_files = get_source_files_interactively()
        # 交互式获取目标目录
        if source_files:
            target_dir = get_target_dir_interactively()
            # 询问操作类型
            action_choice = Prompt.ask(
                "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
                choices=["copy", "move"],
                default="move"
            ).lower()
            # 执行迁移
            migrate_files_with_structure(source_files, target_dir, max_workers=16, action=action_choice)
        return
    
    # 使用 Typer 处理命令行
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.error("操作已中断")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        sys.exit(1)
