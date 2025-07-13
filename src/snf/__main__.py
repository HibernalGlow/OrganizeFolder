from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, TaskID
from rich.text import Text
from rich.layout import Layout
from rich import box

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
    
    # 有条件地添加控制台处理器（彩色格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            colorize=True
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

logger, config_info = setup_logger(app_name="snf", console_output=True)

# 创建Rich控制台实例
console = Console()

import re
import pyperclip
import subprocess

def run_preprocessing(path):
    """运行预处理脚本"""
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'archive', '013-删除空文件夹释放单独文件夹.py')
    if os.path.exists(script_path):
        try:
            # 将路径写入剪贴板
            pyperclip.copy(path)
            # 运行预处理脚本
            subprocess.run(['python', script_path, '-c', '-r'], check=True)
            logger.success("预处理完成")
        except Exception as e:
            logger.error(f"预处理失败: {str(e)}")
    else:
        logger.error(f"预处理脚本不存在: {script_path}")

def extract_number_and_name(folder_name):
    """从文件夹名称中提取序号和名称"""
    match = re.match(r'^(\d)[\.\s-]+(.+)$', folder_name)
    if match:
        return int(match.group(1)), match.group(2)
    return None, folder_name

def should_process_folder(folder_name):
    """判断文件夹是否需要处理（是否符合数字开头格式）"""
    return bool(re.match(r'^\d[\.\s-]+', folder_name))

def get_folder_priority(name):
    """根据文件夹名称获取优先级"""
    priority_keywords = ["同人志", "商业", "单行", "CG", "画集"]
    # 转换为小写进行比较
    name_lower = name.lower()
    for i, keyword in enumerate(priority_keywords):
        if keyword.lower() in name_lower:
            return i
    return len(priority_keywords)  # 没有关键词的排在最后

def is_sequence_continuous(folders):
    """检查文件夹序号是否连续"""
    numbers = [folder[0] for folder in folders]
    return all(numbers[i] == numbers[i-1] + 1 for i in range(1, len(numbers)))

def fix_folder_sequence(base_path):
    """修复文件夹的序号顺序，只在序号不连续时按关键词排序"""
    try:
        # 获取直接子文件夹
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
          # 提取需要处理的文件夹（数字开头的）
        numbered_folders = []
        for folder in folders:
            num, name = extract_number_and_name(folder)
            if num is not None:
                numbered_folders.append((num, name, folder))
        
        # 如果没有需要处理的文件夹，直接返回
        if not numbered_folders:
            logger.warning(f"目录 {base_path} 中没有发现需要处理的编号文件夹")
            return
        
        # 先按原序号排序
        numbered_folders.sort(key=lambda x: x[0])
        
        # 检查序号是否连续
        if is_sequence_continuous(numbered_folders):
            logger.success(f"目录 {base_path} 中的文件夹序号已经连续，无需调整")
            return
            
        # 序号不连续时，按关键词优先级排序
        numbered_folders.sort(key=lambda x: (get_folder_priority(x[1]), x[0]))
        
        # 重新编号
        changes = []
        for i, (_, name, old_folder) in enumerate(numbered_folders, 1):
            new_folder = f"{i}. {name}"
            if new_folder != old_folder:
                old_path = os.path.join(base_path, old_folder)
                new_path = os.path.join(base_path, new_folder)
                
                try:
                    # 保存原始时间戳
                    original_stat = os.stat(old_path)
                    
                    # 重命名文件夹
                    os.rename(old_path, new_path)
                    
                    # 恢复时间戳
                    os.utime(new_path, (original_stat.st_atime, original_stat.st_mtime))
                    changes.append((old_folder, new_folder))
                    logger.info(f"{old_folder} -> {new_folder}")
                except Exception as e:
                    logger.error(f"重命名文件夹失败 {old_folder}: {str(e)}")
        
        if changes:
            logger.success(f"成功修复了 {len(changes)} 个文件夹的序号")
        
    except Exception as e:
        logger.error(f"处理目录 {base_path} 时出错: {str(e)}")

def process_artist_folders(root_path):
    """处理所有画师文件夹"""
    try:
        # 先运行预处理脚本
        run_preprocessing(root_path)
        
        # 获取所有画师文件夹
        artist_folders = [f for f in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, f))]
        for artist_folder in artist_folders:
            artist_path = os.path.join(root_path, artist_folder)
            logger.info(f"处理画师文件夹: {artist_folder}")
            fix_folder_sequence(artist_path)
            
    except Exception as e:
        logger.error(f"处理根目录 {root_path} 时出错: {str(e)}")

def get_paths_interactively():
    """使用Rich进行交互式路径获取"""
    paths = []
    
    # 显示欢迎界面
    console.print(Panel.fit(
        "[bold blue]文件夹序号修复工具[/bold blue]\n"
        "[dim]用于修复文件夹序号的连续性[/dim]",
        box=box.ROUNDED,
        border_style="blue"
    ))
    
    # 创建选项表格
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("选项", style="cyan", width=6)
    table.add_column("说明", style="white")
    table.add_row("1", "手动输入路径")
    table.add_row("2", "从剪贴板读取路径")
    table.add_row("3", "使用默认路径 (E:\\1EHV)")
    
    console.print("\n")
    console.print(table)
    
    while True:
        try:
            choice = Prompt.ask(
                "\n请选择输入方式",
                choices=["1", "2", "3"],
                default="1"
            )
            
            if choice == "1":
                # 手动输入路径
                console.print("\n[yellow]请输入要处理的路径 (输入空行结束):[/yellow]")
                while True:
                    path = Prompt.ask("路径", default="")
                    if not path:
                        break
                    
                    # 清理路径
                    path = path.strip().strip('"')
                    
                    if os.path.exists(path):
                        paths.append(path)
                        console.print(f"[green]✓ 已添加路径:[/green] {path}")
                    else:
                        console.print(f"[red]✗ 路径不存在:[/red] {path}")
                break
                
            elif choice == "2":
                # 从剪贴板读取
                try:
                    clipboard_content = pyperclip.paste().strip()
                    if not clipboard_content:
                        console.print("[yellow]⚠ 剪贴板为空[/yellow]")
                        continue
                    
                    # 显示剪贴板内容
                    console.print("\n[cyan]从剪贴板读取到以下内容:[/cyan]")
                    console.print(Panel(clipboard_content, border_style="cyan"))
                    
                    # 解析路径
                    for line in clipboard_content.splitlines():
                        path = line.strip().strip('"')
                        if path and os.path.exists(path):
                            paths.append(path)
                            console.print(f"[green]✓ 已添加路径:[/green] {path}")
                        elif path:
                            console.print(f"[red]✗ 路径不存在:[/red] {path}")
                    break
                except Exception as e:
                    console.print(f"[red]从剪贴板读取失败: {e}[/red]")
                    continue
                    
            elif choice == "3":
                # 使用默认路径
                default_path = r"E:\1EHV"
                if os.path.exists(default_path):
                    paths.append(default_path)
                    console.print(f"[green]✓ 使用默认路径:[/green] {default_path}")
                else:
                    console.print(f"[red]✗ 默认路径不存在:[/red] {default_path}")
                break
                
        except KeyboardInterrupt:
            console.print("\n[yellow]用户取消操作[/yellow]")
            return []
        except Exception as e:
            console.print(f"[red]输入错误: {e}[/red]")
    
    return paths

def display_paths_summary(paths):
    """显示路径汇总"""
    if not paths:
        return
    
    # 创建路径汇总表格
    path_table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
    path_table.add_column("序号", style="cyan", width=6)
    path_table.add_column("路径", style="white")
    path_table.add_column("状态", style="green", width=8)
    
    for i, path in enumerate(paths, 1):
        status = "✓ 有效" if os.path.exists(path) else "✗ 无效"
        status_style = "green" if os.path.exists(path) else "red"
        path_table.add_row(str(i), path, f"[{status_style}]{status}[/{status_style}]")
    
    console.print(f"\n[bold]将要处理 {len(paths)} 个路径:[/bold]")
    console.print(path_table)

def process_with_progress(paths):
    """使用进度条处理路径"""
    with Progress() as progress:
        main_task = progress.add_task("总体进度", total=len(paths))
        
        for i, path in enumerate(paths, 1):
            # 更新主任务描述
            progress.update(main_task, description=f"处理路径 {i}/{len(paths)}")
            
            console.print(f"\n[bold cyan]处理路径 [{i}/{len(paths)}]:[/bold cyan] {path}")
            
            try:
                process_artist_folders_with_progress(path, progress)
                console.print(f"[green]✓ 路径处理完成:[/green] {path}")
            except Exception as e:
                console.print(f"[red]✗ 路径处理失败:[/red] {path} - {e}")
                logger.error(f"处理路径失败 {path}: {e}")
            
            # 更新主进度
            progress.update(main_task, advance=1)

def process_artist_folders_with_progress(root_path, progress=None):
    """带进度条的画师文件夹处理"""
    try:
        # 先运行预处理脚本
        run_preprocessing(root_path)
        
        # 获取所有画师文件夹
        artist_folders = [f for f in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, f))]
        
        if not artist_folders:
            console.print(f"[yellow]⚠ 目录中没有发现子文件夹:[/yellow] {root_path}")
            return
        
        # 创建子任务
        if progress:
            artist_task = progress.add_task("处理画师文件夹", total=len(artist_folders))
        
        for artist_folder in artist_folders:
            artist_path = os.path.join(root_path, artist_folder)
            console.print(f"  [dim]处理画师文件夹:[/dim] {artist_folder}")
            
            fix_folder_sequence(artist_path)
            
            if progress:
                progress.update(artist_task, advance=1)
                
    except Exception as e:
        logger.error(f"处理根目录 {root_path} 时出错: {str(e)}")
        raise
def main():
    try:
        # 获取路径
        paths = get_paths_interactively()
        
        if not paths:
            console.print("[red]没有有效的路径可以处理[/red]")
            exit(1)
        
        # 显示路径汇总
        display_paths_summary(paths)
        
        # 使用Rich确认框进行确认
        confirm = Confirm.ask("\n确认开始处理吗？", default=True)
        if not confirm:
            console.print("[yellow]用户取消处理[/yellow]")
            exit(0)
        process_with_progress(paths)

        # 完成提示
        console.print(Panel.fit(
            "[bold green]所有路径处理完成！[/bold green]",
            border_style="green"
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]程序运行出错: {e}[/red]")
        logger.error(f"程序运行出错: {e}")
    finally:
        # 使用Rich询问是否退出
        try:
            Prompt.ask("\n按回车键退出", default="")
        except KeyboardInterrupt:
            pass
if __name__ == "__main__":
    main()