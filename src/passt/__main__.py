#!/usr/bin/env python3
"""
压缩包批量解压工具 with 密码尝试和文件重命名

使用rich交互式输入，支持7z解压和文件重命名
"""

import os
import sys
import json
import subprocess
import shutil
import time
import psutil
import signal
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 导入命令行参数库
import typer

# 导入Rich库
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from passt.core.extract import ArchiveExtractor

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

logger, config_info = setup_logger(app_name="passt", console_output=True)

# 创建 Typer 应用
app = typer.Typer(help="压缩包批量解压工具 - 支持密码尝试和文件重命名")

console = Console()

# 支持的压缩包格式
ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', 
    '.xz', '.tar.gz', '.tar.bz2', '.tar.xz',
    '.cbz', '.cbr'
}


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
                        console.print(f"[yellow]警告：路径不存在 - {line}[/yellow]")
            console.print(f"[green]从剪贴板读取到 {len(paths)} 个有效路径[/green]")
    except ImportError:
        console.print("[red]警告：未安装pyperclip模块，无法从剪贴板读取[/red]")
    except Exception as e:
        console.print(f"[red]从剪贴板读取失败: {e}[/red]")
    return paths



def get_user_options() -> Tuple[bool, bool]:
    """获取用户的解压选项
    
    Returns:
        Tuple[bool, bool]: (use_sdel, dissolve_folder)
    """
    console.print("\n[cyan]解压选项配置:[/cyan]")
    
    # 询问是否使用sdel（删除原压缩包）
    use_sdel = Confirm.ask(
        "是否在解压成功后删除原压缩包 (sdel)?",
        default=True
    )
    
    # 询问是否解散文件夹
    dissolve_folder = Confirm.ask(
        "是否在重命名后解散压缩包文件夹（将内容移到父目录）?",
        default=True
    )
    
    return use_sdel, dissolve_folder


def run_interactive() -> None:
    """运行交互式界面"""
    console.print(Panel.fit(
        "[bold blue]压缩包批量解压工具[/bold blue]\n"
        "支持密码尝试和文件重命名功能\n"
        "支持格式: ZIP, RAR, 7Z, TAR, CBZ, CBR 等",
        title="🗜️ 压缩包解压器"
    ))
    
    # 获取用户输入
    target_path = get_user_input()
    if target_path is None:
        console.print("[yellow]用户取消操作[/yellow]")
        return
    
    # 初始化解压器
    extractor = ArchiveExtractor()
    
    # 查找压缩包
    console.print(f"\n[cyan]正在扫描路径: {target_path}[/cyan]")
    archives = extractor.find_archives(target_path)
    
    # 处理压缩包
    extractor.process_archives(archives)


def get_user_input() -> Optional[Path]:
    """获取用户输入的路径
    
    Returns:
        Optional[Path]: 用户选择的路径，如果取消则返回None
    """
    
    while True:
        path_input = Prompt.ask(
            "\n请输入要处理的文件夹或文件路径",
            default=r"E:\1BACKUP\ehv\合集\todo"
        )
        
        if not path_input.strip():
            if not Confirm.ask("输入为空，是否退出？",default=False):
                continue
            return None
        
        path = Path(path_input.strip()).resolve()
        
        if not path.exists():
            console.print(f"[red]路径不存在: {path}[/red]")
            continue
        
        console.print(f"[green]选择的路径: {path}[/green]")
        
        if path.is_file():
            if path.suffix.lower() not in ARCHIVE_EXTENSIONS:
                console.print(f"[yellow]警告: {path.name} 不是支持的压缩包格式[/yellow]")
        
        if Confirm.ask("确认使用此路径？",default=True):
            return path


@app.command()
def extract(
    paths: List[Path] = typer.Argument(None, help="要处理的文件或文件夹路径列表"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取路径"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启用交互式界面"),
    delete: bool = typer.Option(True, "--delete/--no-delete", "-d", help="解压成功后删除原压缩包"),
    dissolve: bool = typer.Option(True, "--dissolve/--no-dissolve", help="重命名后解散压缩包文件夹"),
    password_file: Optional[str] = typer.Option("passwords.json", "--password-file", "-p", help="密码配置文件路径"),
):
    """解压压缩包文件"""
    
    # 如果使用交互式界面，或者不带任何参数
    if interactive or (len(sys.argv) == 1):
        run_interactive()
        return
    
    # 检查7z是否可用
    try:
        subprocess.run(['7z'], capture_output=True, check=False)
    except FileNotFoundError:
        console.print("[red]错误: 未找到 7z 命令，请确保已安装 7-Zip[/red]")
        raise typer.Exit(code=1)
    
    # 获取要处理的路径
    path_list = []
    
    if clipboard:
        path_list.extend(get_paths_from_clipboard())
    
    if paths:
        path_list.extend(paths)
    
    if not path_list:
        console.print("[red]错误: 未提供任何有效的路径[/red]")
        console.print("使用 --interactive 选项启动交互式界面，或使用 --clipboard 从剪贴板读取路径")
        raise typer.Exit(code=1)
    
    # 初始化解压器
    extractor = ArchiveExtractor(passwords_config_path=password_file)
    
    # 设置解压选项
    extractor.delete_after_extract = delete
    extractor.dissolve_folder = dissolve
    
    # 处理每个路径
    for target_path in path_list:
        console.print(f"\n[cyan]正在扫描路径: {target_path}[/cyan]")
        
        # 查找压缩包
        archives = extractor.find_archives(target_path)
        
        if not archives:
            console.print(f"[yellow]在 {target_path} 中未找到压缩包文件[/yellow]")
            continue
        
        # 处理压缩包
        extractor.process_archives(archives)
    
    logger.info("解压任务完成")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """压缩包批量解压工具主入口"""
    if ctx.invoked_subcommand is None:
        # 如果没有指定子命令，运行交互式界面
        run_interactive()


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        console.print(f"[red]程序执行出错: {e}[/red]")
        sys.exit(1)
