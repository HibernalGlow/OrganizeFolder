import re
import shutil
from pathlib import Path
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TransferSpeedColumn, FileSizeColumn
# --- 添加导入 ---
import concurrent.futures
from threading import Lock
import pyperclip
# --- 导入结束 ---

# 初始化 Rich Console
console = Console()

def get_source_files_interactively() -> list[str]:
    """交互式地获取源文件路径列表。"""
    source_files = []
    prompt_message = "[bold cyan]请输入要迁移的源文件路径（每个路径一行，输入 'c' 从剪贴板读取，输入 'done' 或直接按 Enter 结束）：[/bold cyan]"
    console.print(prompt_message)
    while True:
        try:
            # 使用 Prompt.ask 获取输入，允许为空或 'done' 结束
            file_path_raw = Prompt.ask("  [dim]源文件路径[/dim]", default="done", show_default=False).strip()

            # --- 新增：处理剪贴板输入 ---
            if file_path_raw.lower() == 'c':

                try:
                    clipboard_content = pyperclip.paste()
                    if not clipboard_content:
                        console.print("[yellow]剪贴板为空。[/yellow]")
                        continue

                    paths_from_clipboard = [p.strip() for p in clipboard_content.splitlines() if p.strip()]
                    if not paths_from_clipboard:
                        console.print("[yellow]剪贴板内容解析后没有有效的路径。[/yellow]")
                        continue

                    added_count = 0
                    skipped_count = 0
                    error_count = 0
                    console.print(f"  [cyan]正在处理剪贴板中的 {len(paths_from_clipboard)} 个路径...[/cyan]")
                    for cb_path_raw in paths_from_clipboard:
                        cb_path = cb_path_raw.strip('\"\'') # 移除引号
                        p = Path(cb_path)
                        if p.exists() and p.is_file():
                            if cb_path not in source_files: # 避免重复添加
                                source_files.append(cb_path)
                                console.print(f"    [green]已添加:[/green] {cb_path}")
                                added_count += 1
                            else:
                                console.print(f"    [dim]已存在:[/dim] {cb_path}")
                                skipped_count +=1
                        elif p.exists() and not p.is_file():
                            console.print(f"    [yellow]警告:[/yellow] '{p.name}' 不是一个文件，已跳过。")
                            skipped_count += 1
                        else:
                            console.print(f"    [red]错误:[/red] 文件 '{cb_path_raw}' (或处理后的 '{cb_path}') 不存在或路径无效，已跳过。")
                            error_count += 1
                    console.print(f"  [cyan]剪贴板处理完成：添加 {added_count}, 跳过 {skipped_count}, 错误 {error_count}[/cyan]")

                except Exception as e:
                    console.print(f"[red]从剪贴板读取或处理时发生错误: {e}[/red]")
                continue # 处理完剪贴板后，继续等待下一个输入
            # --- 新增结束 ---


            if not file_path_raw or file_path_raw.lower() == 'done':
                if not source_files:
                    console.print("[yellow]警告：未输入任何源文件路径。[/yellow]")
                    # 使用 Confirm.ask 确认是否继续
                    if not Confirm.ask("确定要继续吗（不迁移任何文件）？", default=False):
                        console.print("[bold red]操作已取消。[/bold red]")
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
            if p.exists() and p.is_file():
                 if file_path not in source_files: # 避免重复添加
                     source_files.append(file_path) # 添加处理后的路径
                     console.print(f"  [green]已添加:[/green] {file_path}")
                 else:
                     console.print(f"  [dim]已存在:[/dim] {file_path}")
            elif p.exists() and not p.is_file():
                 console.print(f"  [yellow]警告:[/yellow] '{p.name}' 不是一个文件，已跳过。")
            else:
                 # 打印原始带引号的路径，如果去引号后仍找不到，方便调试
                 console.print(f"  [red]错误:[/red] 文件 '{file_path_raw}' (或处理后的 '{file_path}') 不存在或路径无效，已跳过。")

        except KeyboardInterrupt:
            console.print("\n[bold red]操作已中断。[/bold red]")
            exit()
        except Exception as e:
            console.print(f"[red]输入时发生错误: {e}[/red]")

    return source_files


# --- 新增：处理单个文件的函数 ---
def process_single_file(source_file_str: str, target_root: Path, progress: Progress, task_id, lock: Lock, counters: dict, action: str = 'copy'):
    """处理单个文件的迁移逻辑。"""
    source_file = Path(source_file_str).resolve()
    file_name = source_file.name # 提前获取文件名，避免后续路径问题

    try:
        # 再次检查文件是否存在且是文件
        if not source_file.is_file():
            with lock:
                console.print(f"  [yellow]跳过:[/yellow] 源 '{file_name}' 在处理时不是文件或已消失。")
                counters['skipped'] += 1
            progress.update(task_id, advance=1, description=f"[yellow]跳过:[/yellow] [dim]{file_name}[/dim]")
            return "skipped"

        # --- 确定相对路径 ---
        try:
            drive, path_without_drive = os.path.splitdrive(source_file)
            relative_parts = path_without_drive.strip(os.sep).split(os.sep)
            relative_path = Path(*relative_parts)
        except Exception as e:
            with lock:
                console.print(f"  [red]错误:[/red] 无法确定文件 '{file_name}' 的相对路径: {e}。")
                counters['error'] += 1
            progress.update(task_id, advance=1, description=f"[red]错误(路径):[/red] [dim]{file_name}[/dim]")
            return "error"

        # --- 构造目标路径 ---
        target_file_path = target_root / relative_path

        # --- 创建目标目录 (需要加锁保护，防止多线程同时创建) ---
        try:
            # 加锁以确保目录创建的原子性，避免竞争条件
            with lock:
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            with lock:
                console.print(f"  [red]错误:[/red] 无法创建目标目录 '{target_file_path.parent}' : {e}。跳过文件 '{file_name}。")
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
                console.print(f"  [red]错误:[/red] {action_verb}文件 '{file_name}' 到 '{target_file_path}' 时出错: {e}")
                counters['error'] += 1
            progress.update(task_id, advance=1, description=f"[red]错误({action}):[/red] [dim]{file_name}[/dim]")
            return "error"

    except Exception as e:
        # 捕获处理单个文件的其他意外错误
        with lock:
            console.print(f"[bold red]处理文件 '{source_file_str}' 时发生意外错误: {e}[/bold red]")
            counters['error'] += 1
        progress.update(task_id, advance=1, description=f"[red]错误(未知):[/red] [dim]{file_name}[/dim]")
        return "error"
# --- 函数结束 ---


def migrate_files_with_structure(source_file_paths: list[str], target_root_dir: str, max_workers: int | None = None, action: str = 'copy'):
    """
    将指定的文件列表迁移（复制或移动）到目标根目录，并保留其原始的目录结构，
    使用 Rich 进行输出美化和进度显示，并支持多线程。

    Args:
        source_file_paths: 需要迁移的文件路径列表。
        target_root_dir: 文件将被迁移到的目标根目录路径。
        max_workers: 使用的最大线程数。默认为 None (os.cpu_count())。
        action: 操作类型，'copy' 或 'move'。默认为 'copy'。
    """
    if not source_file_paths:
        console.print("[yellow]没有需要迁移的文件。[/yellow]")
        return

    try:
        target_root = Path(target_root_dir).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        console.print(f"\n[bold green]目标根目录:[/bold green] {target_root}")
        console.print(f"[bold blue]使用线程数:[/bold blue] {max_workers or os.cpu_count()}") # 显示使用的线程数
    except Exception as e:
        console.print(f"[bold red]错误：无法创建或访问目标目录 '{target_root_dir}': {e}[/bold red]")
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
                executor.submit(process_single_file, file_path, target_root, progress, task_id, lock, counters, action) # 传递 action
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
    console.print(f"\n[bold underline]迁移总结 ({action_verb_past}):[/bold underline]")
    console.print(f"  成功{action_verb_past}: [bold green]{counters['migrated']}[/bold green] 个文件")
    if counters['skipped'] > 0:
        console.print(f"  跳过文件: [bold yellow]{counters['skipped']}[/bold yellow] 个")
    if counters['error'] > 0:
        console.print(f"  遇到错误: [bold red]{counters['error']}[/bold red] 个文件")
    else:
        console.print(f"  遇到错误: [bold green]0[/bold green] 个文件")

def get_target_dir_interactively():
    target_dir = ""
    while not target_dir:
        target_dir = Prompt.ask("[bold cyan]请输入目标根目录路径[/bold cyan]",default="E:\\2EHV").strip()
        if not target_dir:
            console.print("[yellow]目标目录不能为空，请重新输入。[/yellow]")
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
                 console.print(f"[red]错误：无法访问或写入目标目录 '{target_dir}': {e}。请检查路径和权限。[/red]")
                 target_dir = "" # 清空以便重新输入
            except Exception as e:
                 console.print(f"[red]验证目标目录时发生意外错误: {e}[/red]")
                 target_dir = "" # 清空以便重新输入
    return target_dir

if __name__ == "__main__":
    console.rule("[bold blue]文件结构迁移工具 (交互模式)[/bold blue]")

    # --- 新增：获取操作类型 ---
    action_choice = Prompt.ask(
        "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
        choices=["copy", "move"],
        default="move"
    ).lower()
    # --- 新增结束 ---

    # --- 新增：获取线程数 ---
    # num_threads_str = Prompt.ask(
    #     "[bold cyan]请输入要使用的最大线程数（留空则使用 CPU 核心数）[/bold cyan]",
    #     default=str(os.cpu_count()), # 默认显示 CPU 核心数
    #     show_default=True
    # )
    num_threads_str = "16"
    try:
        num_threads = int(num_threads_str) if num_threads_str else None
        if num_threads is not None and num_threads <= 0:
            console.print("[yellow]线程数必须大于 0，将使用默认值。[/yellow]")
            num_threads = None
    except ValueError:
        console.print("[yellow]无效的线程数输入，将使用默认值。[/yellow]")
        num_threads = None
    # --- 新增结束 ---


    # 交互式获取源文件
    source_files = get_source_files_interactively()
    # 交互式获取目标目录 (移到获取源文件之后，避免取消时也询问)
    if source_files:
        target_dir = get_target_dir_interactively()
        # 执行迁移
        migrate_files_with_structure(source_files, target_dir, max_workers=num_threads, action=action_choice) # 传递 action
    else:
        console.print("[yellow]没有有效的源文件被添加，迁移操作未执行。[/yellow]")

    console.rule("[bold blue]操作结束[/bold blue]")
