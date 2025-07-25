"""
migrate 包的命令行入口点，使用 Typer 实现命令行界面
"""
import re
import shutil
import sys
from pathlib import Path
import os
from typing import List, Optional, Tuple, Literal
import typer
from enum import Enum
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TransferSpeedColumn, FileSizeColumn
import concurrent.futures
from threading import Lock
import pyperclip
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

logger, config_info = setup_logger(app_name="migratef", console_output=True)

# 创建 Typer 应用
app = typer.Typer(help="文件迁移工具 - 保持目录结构迁移文件和文件夹")

# 初始化 Rich Console，用于用户交互
console = Console()

def get_source_paths_interactively() -> list[str]:
    """交互式地获取源文件和文件夹路径列表。"""
    source_paths = []
    prompt_message = "[bold cyan]请输入要迁移的源文件或文件夹路径（每个路径一行，输入 'c' 从剪贴板读取，输入 'done' 或直接按 Enter 结束）：[/bold cyan]"
    logger.info(prompt_message)
    while True:
        try:
            # 使用 Prompt.ask 获取输入，允许为空或 'done' 结束
            file_path_raw = Prompt.ask("  [dim]源路径（文件或文件夹）[/dim]", default="done", show_default=False).strip()

            # --- 新增：处理剪贴板输入 ---
            if file_path_raw.lower() == 'c':

                try:
                    clipboard_content = pyperclip.paste()
                    if not clipboard_content:
                        logger.warning("剪贴板为空")
                        # console.print("[yellow]剪贴板为空。[/yellow]")
                        continue

                    paths_from_clipboard = [p.strip() for p in clipboard_content.splitlines() if p.strip()]
                    if not paths_from_clipboard:
                        logger.warning("剪贴板内容解析后没有有效的路径")
                        # console.print("[yellow]剪贴板内容解析后没有有效的路径。[/yellow]")
                        continue

                    added_count = 0
                    skipped_count = 0
                    error_count = 0
                    logger.info(f"正在处理剪贴板中的 {len(paths_from_clipboard)} 个路径...")
                    # console.print(f"  [cyan]正在处理剪贴板中的 {len(paths_from_clipboard)} 个路径...[/cyan]")
                    for cb_path_raw in paths_from_clipboard:
                        cb_path = cb_path_raw.strip('\"\'') # 移除引号
                        p = Path(cb_path)
                        if p.exists() and (p.is_file() or p.is_dir()):
                            if cb_path not in source_paths: # 避免重复添加
                                source_paths.append(cb_path)
                                logger.info(f"已添加: {cb_path}")
                                # console.print(f"    [green]已添加:[/green] {cb_path}")
                                added_count += 1
                            else:
                                logger.debug(f"已存在: {cb_path}")
                                # console.print(f"    [dim]已存在:[/dim] {cb_path}")
                                skipped_count +=1
                        elif p.exists() and not (p.is_file() or p.is_dir()):
                            logger.warning(f"警告: '{p.name}' 不是文件或文件夹，已跳过")
                            # console.print(f"    [yellow]警告:[/yellow] '{p.name}' 不是文件或文件夹，已跳过。")
                            skipped_count += 1
                        else:
                            logger.error(f"错误: 路径 '{cb_path_raw}' (或处理后的 '{cb_path}') 不存在或路径无效，已跳过")
                            # console.print(f"    [red]错误:[/red] 路径 '{cb_path_raw}' (或处理后的 '{cb_path}') 不存在或路径无效，已跳过。")
                            error_count += 1
                    logger.info(f"剪贴板处理完成：添加 {added_count}, 跳过 {skipped_count}, 错误 {error_count}")
                    # console.print(f"  [cyan]剪贴板处理完成：添加 {added_count}, 跳过 {skipped_count}, 错误 {error_count}[/cyan]")

                except Exception as e:
                    logger.error(f"从剪贴板读取或处理时发生错误: {e}")
                    # console.print(f"[red]从剪贴板读取或处理时发生错误: {e}[/red]")
                continue # 处理完剪贴板后，继续等待下一个输入
            # --- 新增结束 ---


            if not file_path_raw or file_path_raw.lower() == 'done':
                if not source_paths:
                    logger.warning("警告：未输入任何源路径")
                    # console.print("[yellow]警告：未输入任何源路径。[/yellow]")
                    # 使用 Confirm.ask 确认是否继续
                    if not Confirm.ask("确定要继续吗（不迁移任何文件）？", default=False):
                        logger.error("操作已取消")
                        # console.print("[bold red]操作已取消。[/bold red]")
                        exit() # 或者返回空列表让主函数处理
                    else:
                        break # 确认继续，即使列表为空
                else:
                    break # 完成输入

            # --- 添加这行代码 ---
            # 移除首尾可能存在的双引号或单引号
            file_path = file_path_raw.strip('\"\'')
            # --- 修改结束 ---


            # 简单的路径有效性检查 (使用处理后的 file_path)
            p = Path(file_path)
            if p.exists() and (p.is_file() or p.is_dir()):
                 if file_path not in source_paths: # 避免重复添加
                     source_paths.append(file_path) # 添加处理后的路径
                     logger.info(f"已添加: {file_path}")
                     # console.print(f"  [green]已添加:[/green] {file_path}")
                 else:
                     logger.debug(f"已存在: {file_path}")
                     # console.print(f"  [dim]已存在:[/dim] {file_path}")
            elif p.exists() and not (p.is_file() or p.is_dir()):
                 logger.warning(f"警告: '{p.name}' 不是文件或文件夹，已跳过")
                 # console.print(f"  [yellow]警告:[/yellow] '{p.name}' 不是文件或文件夹，已跳过。")
            else:
                 # 打印原始带引号的路径，如果去引号后仍找不到，方便调试
                 logger.error(f"错误: 路径 '{file_path_raw}' (或处理后的 '{file_path}') 不存在或路径无效，已跳过")
                 # console.print(f"  [red]错误:[/red] 路径 '{file_path_raw}' (或处理后的 '{file_path}') 不存在或路径无效，已跳过。")

        except KeyboardInterrupt:
            logger.error("操作已中断")
            # console.print("\n[bold red]操作已中断。[/bold red]")
            exit()
        except Exception as e:
            logger.error(f"输入时发生错误: {e}")
            # console.print(f"[red]输入时发生错误: {e}[/red]")

    return source_paths


def migrate_paths_directly(source_paths: list[str], target_root_dir: str, action: str = 'copy'):
    """
    直接迁移文件和文件夹到目标目录（类似 mv 命令）
    
    Args:
        source_paths: 源文件和文件夹路径列表
        target_root_dir: 目标根目录
        action: 操作类型，'copy' 或 'move'
    """
    if not source_paths:
        logger.warning("没有需要迁移的文件或文件夹")
        return

    try:
        target_root = Path(target_root_dir).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"目标根目录: {target_root}")
        logger.info(f"迁移模式: 直接迁移")
    except Exception as e:
        logger.error(f"错误：无法创建或访问目标目录 '{target_root_dir}': {e}")
        return

    counters = {'migrated': 0, 'error': 0, 'skipped': 0}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[{task.completed}/{task.total}]"),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        task_id = progress.add_task("[cyan]正在迁移文件和文件夹...", total=len(source_paths))
        
        for source_path_str in source_paths:
            source_path = Path(source_path_str).resolve()
            item_name = source_path.name
            
            try:
                if not source_path.exists():
                    logger.warning(f"跳过: 源 '{item_name}' 不存在")
                    counters['skipped'] += 1
                    progress.update(task_id, advance=1, description=f"[yellow]跳过:[/yellow] [dim]{item_name}[/dim]")
                    continue
                
                target_path = target_root / item_name
                
                # 检查目标是否已存在
                if target_path.exists():
                    logger.warning(f"跳过: 目标 '{target_path}' 已存在")
                    counters['skipped'] += 1
                    progress.update(task_id, advance=1, description=f"[yellow]跳过(已存在):[/yellow] [dim]{item_name}[/dim]")
                    continue
                
                if action == 'move':
                    shutil.move(str(source_path), str(target_path))
                    counters['migrated'] += 1
                    progress.update(task_id, advance=1, description=f"[blue]移动:[/blue] [dim]{item_name}[/dim]")
                else:  # copy
                    if source_path.is_file():
                        shutil.copy2(source_path, target_path)
                    else:  # directory
                        shutil.copytree(source_path, target_path)
                    counters['migrated'] += 1
                    progress.update(task_id, advance=1, description=f"[green]复制:[/green] [dim]{item_name}[/dim]")
                    
            except Exception as e:
                action_verb = "移动" if action == 'move' else "复制"
                logger.error(f"错误: {action_verb} '{item_name}' 到 '{target_root}' 时出错: {e}")
                counters['error'] += 1
                progress.update(task_id, advance=1, description=f"[red]错误({action}):[/red] [dim]{item_name}[/dim]")
    
    # 输出总结
    action_verb_past = "移动" if action == 'move' else "复制"
    logger.info(f"迁移总结 ({action_verb_past}):")
    logger.info(f"  成功{action_verb_past}: {counters['migrated']} 个项目")
    if counters['skipped'] > 0:
        logger.warning(f"  跳过项目: {counters['skipped']} 个")
    if counters['error'] > 0:
        logger.error(f"  遇到错误: {counters['error']} 个项目")
    else:
        logger.info(f"  遇到错误: 0 个项目")


def collect_files_from_paths(source_paths: list[str], preserve_structure: bool = True) -> list[str]:
    """从路径列表（文件和文件夹）中收集所有文件。
    
    Args:
        source_paths: 包含文件和文件夹路径的列表
        preserve_structure: 是否保持目录结构，如果为False则只处理直接输入的文件
        
    Returns:
        所有文件路径的列表
    """
    all_files = []
    
    for path_str in source_paths:
        path = Path(path_str)
        
        if path.is_file():
            # 如果是文件，直接添加
            all_files.append(str(path))
        elif path.is_dir():
            if preserve_structure:
                # 保持目录结构模式：递归收集所有文件
                try:
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            all_files.append(str(file_path))
                    logger.info(f"从文件夹 '{path}' 收集了 {len([f for f in path.rglob('*') if Path(f).is_file()])} 个文件")
                except Exception as e:
                    logger.error(f"扫描文件夹 '{path}' 时出错: {e}")
            else:
                # 扁平迁移模式：只收集第一层的文件
                try:
                    files_count = 0
                    for item in path.iterdir():
                        if item.is_file():
                            all_files.append(str(item))
                            files_count += 1
                    logger.info(f"从文件夹 '{path}' 的第一层收集了 {files_count} 个文件")
                except Exception as e:
                    logger.error(f"扫描文件夹 '{path}' 时出错: {e}")
        else:
            logger.warning(f"跳过无效路径: {path}")
    
    logger.info(f"总共收集了 {len(all_files)} 个文件")
    return all_files


# --- 新增：处理单个文件的函数 ---
def process_single_file(source_file_str: str, target_root: Path, progress: Progress, task_id, lock: Lock, counters: dict, action: str = 'copy', preserve_structure: bool = True):
    """处理单个文件的迁移逻辑。"""
    source_file = Path(source_file_str).resolve()
    file_name = source_file.name # 提前获取文件名，避免后续路径问题

    try:
        # 再次检查文件是否存在且是文件
        if not source_file.is_file():
            with lock:
                logger.warning(f"跳过: 源 '{file_name}' 在处理时不是文件或已消失")
                # console.print(f"  [yellow]跳过:[/yellow] 源 '{file_name}' 在处理时不是文件或已消失。")
                counters['skipped'] += 1
            progress.update(task_id, advance=1, description=f"[yellow]跳过:[/yellow] [dim]{file_name}[/dim]")
            return "skipped"

        # --- 确定目标路径 ---
        if preserve_structure:
            # 保持目录结构模式
            try:
                drive, path_without_drive = os.path.splitdrive(source_file)
                relative_parts = path_without_drive.strip(os.sep).split(os.sep)
                relative_path = Path(*relative_parts)
                target_file_path = target_root / relative_path
            except Exception as e:
                with lock:
                    logger.error(f"错误: 无法确定文件 '{file_name}' 的相对路径: {e}")
                    # console.print(f"  [red]错误:[/red] 无法确定文件 '{file_name}' 的相对路径: {e}。")
                    counters['error'] += 1
                progress.update(task_id, advance=1, description=f"[red]错误(路径):[/red] [dim]{file_name}[/dim]")
                return "error"
        else:
            # 扁平迁移模式 - 直接放到目标目录
            target_file_path = target_root / file_name

        # --- 创建目标目录 (需要加锁保护，防止多线程同时创建) ---
        try:
            # 加锁以确保目录创建的原子性，避免竞争条件
            with lock:
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            with lock:
                logger.error(f"错误: 无法创建目标目录 '{target_file_path.parent}' : {e}。跳过文件 '{file_name}")
                # console.print(f"  [red]错误:[/red] 无法创建目标目录 '{target_file_path.parent}' : {e}。跳过文件 '{file_name}。")
                counters['error'] += 1
            progress.update(task_id, advance=1, description=f"[red]错误(目录):[/red] [dim]{file_name}[/dim]")
            return "error"

        # --- 复制或移动文件 ---
        try:
            if action == 'move':
                shutil.move(str(source_file), target_file_path) # shutil.move 需要字符串路径
                with lock:
                    counters['migrated'] += 1
                progress.update(task_id, advance=1, description=f"[blue]移动:[/blue] [dim]{file_name}[/dim]")
            else: # 默认为 copy
                shutil.copy2(source_file, target_file_path)
                with lock:
                    counters['migrated'] += 1
                progress.update(task_id, advance=1, description=f"[green]复制:[/green] [dim]{file_name}[/dim]")
            return "success"
        except Exception as e:
            with lock:
                action_verb = "移动" if action == 'move' else "复制"
                logger.error(f"错误: {action_verb}文件 '{file_name}' 到 '{target_file_path}' 时出错: {e}")
                # console.print(f"  [red]错误:[/red] {action_verb}文件 '{file_name}' 到 '{target_file_path}' 时出错: {e}")
                counters['error'] += 1
            progress.update(task_id, advance=1, description=f"[red]错误({action}):[/red] [dim]{file_name}[/dim]")
            return "error"

    except Exception as e:
        # 捕获处理单个文件的其他意外错误
        with lock:
            logger.error(f"处理文件 '{source_file_str}' 时发生意外错误: {e}")
            # console.print(f"[bold red]处理文件 '{source_file_str}' 时发生意外错误: {e}[/bold red]")
            counters['error'] += 1
        progress.update(task_id, advance=1, description=f"[red]错误(未知):[/red] [dim]{file_name}[/dim]")
        return "error"
# --- 函数结束 ---


def migrate_files_with_structure(source_file_paths: list[str], target_root_dir: str, max_workers: int | None = None, action: str = 'copy', preserve_structure: bool = True):
    """
    将指定的文件列表迁移（复制或移动）到目标根目录，并可选择保留其原始的目录结构，
    使用 Rich 进行输出美化和进度显示，并支持多线程。

    Args:
        source_file_paths: 需要迁移的文件路径列表。
        target_root_dir: 文件将被迁移到的目标根目录路径。
        max_workers: 使用的最大线程数。默认为 None (os.cpu_count())。
        action: 操作类型，'copy' 或 'move'。默认为 'copy'。
        preserve_structure: 是否保持目录结构。True为保持，False为扁平迁移。
    """
    if not source_file_paths:
        logger.warning("没有需要迁移的文件")
        # console.print("[yellow]没有需要迁移的文件。[/yellow]")
        return

    try:
        target_root = Path(target_root_dir).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        structure_mode = "保持目录结构" if preserve_structure else "扁平迁移"
        logger.info(f"目标根目录: {target_root}")
        logger.info(f"迁移模式: {structure_mode}")
        logger.info(f"使用线程数: {max_workers or os.cpu_count()}")
        # console.print(f"\n[bold green]目标根目录:[/bold green] {target_root}")
        # console.print(f"[bold blue]使用线程数:[/bold blue] {max_workers or os.cpu_count()}") # 显示使用的线程数
    except Exception as e:
        logger.error(f"错误：无法创建或访问目标目录 '{target_root_dir}': {e}")
        # console.print(f"[bold red]错误：无法创建或访问目标目录 '{target_root_dir}': {e}[/bold red]")
        return

    # --- 修改：使用线程安全的计数器和锁 ---
    counters = {'migrated': 0, 'error': 0, 'skipped': 0}
    lock = Lock()
    # --- 修改结束 ---

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        # FileSizeColumn(), # 单个文件大小在多线程进度条中意义不大
        # TransferSpeedColumn(), # 整体速度更难精确计算
        TextColumn("[{task.completed}/{task.total}]"), # 显示已完成/总数
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:

        task_id = progress.add_task("[cyan]正在迁移文件...", total=len(source_file_paths))

        # --- 修改：使用 ThreadPoolExecutor ---
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建 future 列表
            futures = [
                executor.submit(process_single_file, file_path, target_root, progress, task_id, lock, counters, action, preserve_structure) # 传递 preserve_structure
                for file_path in source_file_paths
            ]

            # 等待所有任务完成 (可以移除，因为 progress bar 会等待)
            # concurrent.futures.wait(futures)
        # --- 修改结束 ---

    # 完成后更新进度条描述
    progress.stop_task(task_id)
    progress.update(task_id, description="[bold green]迁移完成[/bold green]")
    progress.refresh()

    action_verb_past = "移动" if action == 'move' else "复制"
    logger.info(f"迁移总结 ({action_verb_past}):")
    logger.info(f"  成功{action_verb_past}: {counters['migrated']} 个文件")
    # console.print(f"\n[bold underline]迁移总结 ({action_verb_past}):[/bold underline]")
    # console.print(f"  成功{action_verb_past}: [bold green]{counters['migrated']}[/bold green] 个文件")
    if counters['skipped'] > 0:
        logger.warning(f"  跳过文件: {counters['skipped']} 个")
        # console.print(f"  跳过文件: [bold yellow]{counters['skipped']}[/bold yellow] 个")
    if counters['error'] > 0:
        logger.error(f"  遇到错误: {counters['error']} 个文件")
        # console.print(f"  遇到错误: [bold red]{counters['error']}[/bold red] 个文件")
    else:
        logger.info(f"  遇到错误: 0 个文件")
        # console.print(f"  遇到错误: [bold green]0[/bold green] 个文件")

def get_target_dir_interactively():
    target_dir = ""
    while not target_dir:
        target_dir = Prompt.ask("[bold cyan]请输入目标根目录路径[/bold cyan]",default="E:\\2EHV").strip()
        if not target_dir:
            logger.warning("目标目录不能为空，请重新输入")
            # console.print("[yellow]目标目录不能为空，请重新输入。[/yellow]")
        else:
            # 可以添加更多验证，例如检查是否是有效路径格式或是否可写
            target_p = Path(target_dir)
            try:
                # 尝试创建（如果不存在）或检查权限（如果存在）
                target_p.mkdir(parents=True, exist_ok=True)
                # 简单检查写权限 (在Windows上可能不完全可靠)
                test_file = target_p / ".permission_test"
                test_file.touch()
                test_file.unlink()
                break # 验证通过
            except OSError as e:
                 logger.error(f"错误：无法访问或写入目标目录 '{target_dir}': {e}。请检查路径和权限")
                 # console.print(f"[red]错误：无法访问或写入目标目录 '{target_dir}': {e}。请检查路径和权限。[/red]")
                 target_dir = "" # 清空以便重新输入
            except Exception as e:
                 logger.error(f"验证目标目录时发生意外错误: {e}")
                 # console.print(f"[red]验证目标目录时发生意外错误: {e}[/red]")
                 target_dir = "" # 清空以便重新输入
    return target_dir

@app.command()
def migrate(
    files: List[Path] = typer.Argument(None, help="要迁移的文件和文件夹列表"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="从剪贴板读取文件和文件夹路径"),
    target: Optional[Path] = typer.Option(None, "--target", "-t", help="目标文件夹路径"),
    threads: Optional[int] = typer.Option(None, "--threads", help="使用的线程数量"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启用交互式界面"),
    copy: bool = typer.Option(False, "--copy", help="复制文件而不是移动"),
    move: bool = typer.Option(True, "--move", help="移动文件而不是复制"),
    flat: bool = typer.Option(False, "--flat", "-f", help="扁平迁移模式，不保持目录结构（类似mv命令）"),
    direct: bool = typer.Option(False, "--direct", "-d", help="直接迁移模式，整个文件/文件夹作为一个单位迁移"),
):
    """迁移文件和文件夹，支持保持目录结构或扁平迁移"""    # 如果指定了交互式界面或没有任何参数，启动交互式界面
    if interactive or not files:
        # 交互式获取源路径（文件和文件夹）
        source_paths = get_source_paths_interactively()
        # 交互式获取目标目录
        if source_paths:
            target_dir = get_target_dir_interactively()
            
            # 询问迁移模式
            console.print("[bold cyan]请选择迁移模式[/bold cyan]")
            console.print("  [bold blue]1[/bold blue] - preserve - 保持目录结构迁移")
            console.print("  [bold blue]2[/bold blue] - flat - 扁平迁移（只迁移文件，不保持目录结构）")
            console.print("  [bold blue]3[/bold blue] - direct - 直接迁移（类似mv命令，整个文件/文件夹作为单位）")
            
            migration_choice = Prompt.ask(
                "请输入选项编号",
                choices=["1", "2", "3"],
                default="1"
            )
            
            # 将数字选择转换为模式名称
            migration_modes = {"1": "preserve", "2": "flat", "3": "direct"}
            migration_mode = migration_modes[migration_choice]
            
            # 询问操作类型
            action_choice = Prompt.ask(
                "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
                choices=["copy", "move"],
                default="move"
            ).lower()
            
            # 根据迁移模式执行不同的逻辑
            if migration_mode == "direct":
                # 直接迁移模式
                migrate_paths_directly(source_paths, target_dir, action=action_choice)
            else:
                # 文件级迁移模式
                preserve_structure = (migration_mode == "preserve")
                source_files = collect_files_from_paths(source_paths, preserve_structure=preserve_structure)
                # 询问线程数
                num_threads = 16
                # 执行迁移
                migrate_files_with_structure(source_files, target_dir, max_workers=num_threads, action=action_choice, preserve_structure=preserve_structure)
        return
    
    # 命令行模式
    source_paths = []
      # 从剪贴板获取文件路径
    if clipboard:
        try:
            clipboard_content = pyperclip.paste()
            paths_from_clipboard = [p.strip() for p in clipboard_content.splitlines() if p.strip()]
            for path_str in paths_from_clipboard:
                path = Path(path_str)
                if path.exists() and (path.is_file() or path.is_dir()):
                    source_paths.append(str(path))
        except Exception as e:
            logger.error(f"从剪贴板读取路径时出错: {e}")
            # typer.echo(f"从剪贴板读取路径时出错: {e}", err=True)
    
    # 添加命令行指定的文件和文件夹
    if files:
        for file_path in files:
            if file_path.exists() and (file_path.is_file() or file_path.is_dir()):
                source_paths.append(str(file_path))
    
    # 确保有文件要迁移
    if not source_paths:
        logger.error("错误: 没有有效的源文件或文件夹。使用 --interactive 选项启动交互式界面")
        # typer.echo("错误: 没有有效的源文件。使用 --interactive 选项启动交互式界面。", err=True)
        raise typer.Exit(code=1)
    
    # 确保有目标目录
    if not target:
        logger.error("错误: 未指定目标目录。请使用 --target 选项指定目标目录")
        # typer.echo("错误: 未指定目标目录。请使用 --target 选项指定目标目录。", err=True)
        raise typer.Exit(code=1)
    
    # 确保目标目录有效
    if not target.exists():
        try:
            target.mkdir(parents=True)
        except Exception as e:
            logger.error(f"错误: 无法创建目标目录 {target}: {e}")
            # typer.echo(f"错误: 无法创建目标目录 {target}: {e}", err=True)
            raise typer.Exit(code=1)
    
    # 确定操作类型
    action = "copy" if copy else "move"
    
    # 根据模式执行迁移
    if direct:
        # 直接迁移模式
        migrate_paths_directly(source_paths, str(target), action=action)
    else:
        # 文件级迁移模式
        preserve_structure = not flat  # flat为True时，preserve_structure为False
        source_files = collect_files_from_paths(source_paths, preserve_structure=preserve_structure)
        
        if not source_files:
            logger.error("错误: 没有找到可迁移的文件")
            raise typer.Exit(code=1)
        
        # 执行迁移
        migrate_files_with_structure(source_files, str(target), max_workers=threads, action=action, preserve_structure=preserve_structure)

def main():
    """主入口函数"""
    # 检查是否没有提供任何参数，直接启动交互式界面
    if len(sys.argv) == 1:
        # 交互式获取源路径（文件和文件夹）
        source_paths = get_source_paths_interactively()
        # 交互式获取目标目录
        if source_paths:
            target_dir = get_target_dir_interactively()
            
            # 询问迁移模式
            console.print("[bold cyan]请选择迁移模式[/bold cyan]")
            console.print("  [bold blue]1[/bold blue] - preserve - 保持目录结构迁移")
            console.print("  [bold blue]2[/bold blue] - flat - 扁平迁移（只迁移文件，不保持目录结构）")
            console.print("  [bold blue]3[/bold blue] - direct - 直接迁移（类似mv命令，整个文件/文件夹作为单位）")
            
            migration_choice = Prompt.ask(
                "请输入选项编号",
                choices=["1", "2", "3"],
                default="1"
            )
            
            # 将数字选择转换为模式名称
            migration_modes = {"1": "preserve", "2": "flat", "3": "direct"}
            migration_mode = migration_modes[migration_choice]
            
            # 询问操作类型
            action_choice = Prompt.ask(
                "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
                choices=["copy", "move"],
                default="move"
            ).lower()
            
            # 根据迁移模式执行不同的逻辑
            if migration_mode == "direct":
                # 直接迁移模式
                migrate_paths_directly(source_paths, target_dir, action=action_choice)
            else:
                # 文件级迁移模式
                preserve_structure = (migration_mode == "preserve")
                source_files = collect_files_from_paths(source_paths, preserve_structure=preserve_structure)
                # 执行迁移
                migrate_files_with_structure(source_files, target_dir, max_workers=16, action=action_choice, preserve_structure=preserve_structure)
        return
    
    # 使用 Typer 处理命令行
    app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.error("操作已中断")
        # console.print("\n[bold red]操作已中断。[/bold red]")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        # console.print(f"[bold red]发生错误: {e}[/bold red]")
        sys.exit(1)