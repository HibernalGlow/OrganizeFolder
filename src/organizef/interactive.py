"""
OrganizeFolder 交互式界面模块

提供基于 Rich 库的交互式界面，使用户可以通过可视化方式使用 OrganizeFolder 的各种功能。
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time
from pathlib import Path

# Rich 组件
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, TaskID
from rich.status import Status
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule
from rich.tree import Tree
from rich import box, print

# 导入功能模块
from cleanf.empty import remove_empty_folders
from cleanf.backup import remove_backup_and_temp
from dissolvef import flatten_single_subfolder, release_single_media_folder, dissolve_folder
from dissolvef.media import VIDEO_FORMATS, ARCHIVE_FORMATS
from migratef import migrate_files_with_structure
from . import __version__

# 创建控制台
console = Console()

# 预览功能状态
preview_mode = False

def set_preview_mode(mode: bool) -> None:
    """设置是否为预览模式"""
    global preview_mode
    preview_mode = mode
    
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
                        console.print(f"[yellow]警告：[/yellow]路径不存在 - {line}")
            
            console.print(f"从剪贴板读取到 [green]{len(paths)}[/green] 个有效路径")
    except ImportError:
        console.print("[yellow]警告：未安装 pyperclip 模块，无法从剪贴板读取。[/yellow]")
        console.print("提示: 可以通过 pip install pyperclip 安装")
    except Exception as e:
        console.print(f"[red]读取剪贴板失败:[/red] {e}")
    
    return paths


def browse_directory() -> Optional[Path]:
    """使用Rich交互式界面浏览和选择目录"""
    # 获取起始路径
    start_path = Path.home()
    current_path = start_path
    
    # Windows 系统下可以显示驱动器列表
    if sys.platform == "win32":
        import string
        drives = []
        for drive in string.ascii_uppercase:
            if os.path.exists(f"{drive}:"):
                drives.append(f"{drive}:")
    
    while True:
        console.clear()
        console.print(f"[bold blue]当前位置:[/bold blue] [green]{current_path}[/green]")
        console.print("[bold]请选择一个文件夹或使用特殊命令:[/bold]")
        console.print(".. - 返回上层目录")
        console.print("q  - 取消选择")
        
        # 在Windows系统下显示可用驱动器
        if sys.platform == "win32" and (current_path == start_path or len(current_path.parts) <= 1):
            console.print("[bold cyan]可用驱动器:[/bold cyan]")
            for i, drive in enumerate(drives):
                console.print(f"{i+1}. {drive}")
            console.print()
        
        # 显示当前目录下的所有文件夹
        dirs = []
        try:
            # 收集所有文件夹
            for item in sorted(current_path.iterdir()):
                if item.is_dir():
                    dirs.append(item)
                    
            if not dirs:
                console.print("[yellow]当前目录下没有文件夹[/yellow]")
            else:
                # 创建表格显示文件夹
                table = Table(box=box.SIMPLE)
                table.add_column("序号", style="cyan")
                table.add_column("文件夹名称", style="green")
                
                for i, dir_path in enumerate(dirs, 1):
                    table.add_row(str(i), dir_path.name)
                
                console.print(table)
        except PermissionError:
            console.print("[red]没有权限访问此目录[/red]")
            console.print("按 Enter 返回上层目录...")
            input()
            if current_path != current_path.parent:
                current_path = current_path.parent
            continue
        except Exception as e:
            console.print(f"[red]读取目录出错: {e}[/red]")
            console.print("按 Enter 返回上层目录...")
            input()
            if current_path != current_path.parent:
                current_path = current_path.parent
            continue
        
        # 获取用户输入
        choice = Prompt.ask("请选择 (序号、特殊命令或完整路径)", default="..")
        
        # 处理特殊命令
        if choice == "q":
            return None
        elif choice == "..":
            if current_path != current_path.parent:
                current_path = current_path.parent
            continue
            
        # 处理完整路径输入
        if os.path.sep in choice or (sys.platform == "win32" and ":" in choice):
            try:
                path = Path(choice)
                if path.exists() and path.is_dir():
                    return path
                else:
                    console.print("[red]无效的路径[/red]")
                    console.print("按 Enter 继续...")
                    input()
            except Exception:
                console.print("[red]无效的路径格式[/red]")
                console.print("按 Enter 继续...")
                input()
            continue
            
        # Windows系统下处理驱动器选择
        if sys.platform == "win32" and (current_path == start_path or len(current_path.parts) <= 1):
            try:
                drive_idx = int(choice) - 1
                if 0 <= drive_idx < len(drives):
                    current_path = Path(drives[drive_idx])
                    continue
            except ValueError:
                pass
        
        # 处理序号选择
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dirs):
                selected_dir = dirs[idx]
                
                # 如果用户选择了一个目录，询问是使用此目录还是进入其中
                if Confirm.ask(f"选择 [cyan]{selected_dir.name}[/cyan] 作为目标路径?", default=False):
                    return selected_dir
                else:
                    current_path = selected_dir
            else:
                console.print("[red]无效的选择[/red]")
                console.print("按 Enter 继续...")
                input()
        except ValueError:
            console.print("[red]请输入有效的序号或命令[/red]")
            console.print("按 Enter 继续...")
            input()
            
    return None


def select_paths() -> List[Path]:
    """交互式选择要处理的路径"""
    paths = []
    
    console.print("\n[bold blue]== 选择要处理的路径 ==[/bold blue]")
    console.print("请选择路径输入方式:")
    console.print("1. 从剪贴板读取路径")
    console.print("2. 手动输入路径")
    console.print("3. 浏览文件夹")
    
    choice = Prompt.ask("请选择", choices=["1", "2", "3"], default="1")
    
    if choice == "1":
        paths = get_paths_from_clipboard()
        
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
                return []
                
    elif choice == "3":
        # 使用Rich交互式目录浏览器选择路径
        console.print("[cyan]正在启动文件浏览器...[/cyan]")
        selected_path = browse_directory()
        if selected_path:
            paths.append(selected_path)
            console.print(f"已选择路径: [green]{selected_path}[/green]")
    
    # 显示选择的路径
    if paths:
        table = Table(title="已选择的路径")
        table.add_column("序号", style="cyan")
        table.add_column("路径", style="green")
        table.add_column("类型", style="magenta")
        table.add_column("状态", style="yellow")
        
        for i, path in enumerate(paths, 1):
            path_type = "文件夹" if path.is_dir() else "文件"
            status = "有效" if path.exists() else "无效"
            table.add_row(str(i), str(path), path_type, status)
            
        console.print(table)
        
        if not Confirm.ask("确认使用这些路径?", default=True):
            return select_paths()  # 重新选择路径
    else:
        console.print("[yellow]未选择任何路径[/yellow]")
        if Confirm.ask("是否重新选择?", default=True):
            return select_paths()  # 重新选择路径
    
    return paths


def select_exclude_keywords() -> List[str]:
    """交互式选择排除关键词"""
    exclude_keywords = ["单行"]  # 默认排除关键词
    
    if Confirm.ask("是否要添加排除关键词?", default=False):
        console.print("请输入排除关键词，多个关键词用逗号分隔:")
        keywords = input().strip()
        if keywords:
            exclude_keywords.extend([kw.strip() for kw in keywords.split(",")])
    
    return exclude_keywords


def select_operations() -> Dict[str, bool]:
    """交互式选择要执行的操作"""
    operations = {
        "release_media": False,
        "flatten": False,
        "dissolve": False,
        "remove_empty": False,
        "clean_backup": False,
    }
    
    console.print("\n[bold blue]== 选择要执行的操作 ==[/bold blue]")
    
    # 显示操作菜单
    table = Table(title="可用操作")
    table.add_column("序号", style="cyan", width=5)
    table.add_column("操作", style="green")
    table.add_column("说明", style="magenta")
    
    table.add_row("1", "释放单独媒体文件夹", "将只包含单个视频或压缩包的文件夹解散")
    table.add_row("2", "解散嵌套的单独文件夹", "解散只有一个子文件夹的嵌套文件夹")
    table.add_row("3", "直接解散指定文件夹", "将整个文件夹的内容移动到其父文件夹")
    table.add_row("4", "删除空文件夹", "删除所有空的文件夹")
    table.add_row("5", "删除备份和临时文件", "删除备份文件(.bak)和临时文件夹(temp_)")
    table.add_row("6", "全部功能(除直接解散)", "执行1、2、4、5操作")
    
    console.print(table)
    
    # 获取用户选择
    choice = Prompt.ask("请选择操作(多选请用逗号分隔，如1,2,4)", default="6")
    choices = [c.strip() for c in choice.split(",")]
    
    # 设置操作标志
    if "1" in choices or "6" in choices:
        operations["release_media"] = True
    if "2" in choices or "6" in choices:
        operations["flatten"] = True
    if "3" in choices:
        operations["dissolve"] = True
    if "4" in choices or "6" in choices:
        operations["remove_empty"] = True
    if "5" in choices or "6" in choices:
        operations["clean_backup"] = True
    
    # 如果选择了直接解散，就不能选择其他操作
    if operations["dissolve"] and any([operations["release_media"], operations["flatten"], operations["remove_empty"], operations["clean_backup"]]):
        console.print("[yellow]警告：直接解散指定文件夹与其他操作互斥，将只执行直接解散操作[/yellow]")
        operations["release_media"] = operations["flatten"] = operations["remove_empty"] = operations["clean_backup"] = False
    
    return operations


def select_conflict_handling() -> Tuple[str, str]:
    """交互式选择文件冲突处理方式"""
    console.print("\n[bold blue]== 文件冲突处理方式 ==[/bold blue]")
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
    
    console.print(f"文件冲突处理方式: [green]{file_conflict}[/green] (auto表示跳过)")
    console.print(f"文件夹冲突处理方式: [green]{dir_conflict}[/green] (auto表示合并)")
    
    return file_conflict, dir_conflict


def display_preview(paths: List[Path], operations: Dict[str, bool]) -> None:
    """显示预览信息"""
    console.print("\n[bold blue]== 操作预览 ==[/bold blue]")
    
    # 显示选择的路径
    console.print(f"[bold]将处理以下路径:[/bold]")
    for path in paths:
        console.print(f"- [green]{path}[/green]")
    
    # 显示选择的操作
    console.print("\n[bold]将执行以下操作:[/bold]")
    if operations["dissolve"]:
        console.print("- [cyan]直接解散指定文件夹[/cyan]")
    else:
        if operations["release_media"]:
            console.print("- [cyan]释放单独媒体文件夹[/cyan]")
        if operations["flatten"]:
            console.print("- [cyan]解散嵌套的单独文件夹[/cyan]")
        if operations["remove_empty"]:
            console.print("- [cyan]删除空文件夹[/cyan]")
        if operations["clean_backup"]:
            console.print("- [cyan]删除备份和临时文件[/cyan]")
    
    # 执行预览扫描
    if operations["dissolve"]:
        # 预览直接解散
        for path in paths:
            console.print(f"\n预览直接解散: [green]{path}[/green]")
            for item in path.iterdir():
                target = path.parent / item.name
                if target.exists():
                    console.print(f"- [yellow]{item.name}[/yellow] -> [yellow]目标已存在[/yellow]")
                else:
                    console.print(f"- {item.name} -> {target}")
    else:
        # 预览其他操作
        if operations["release_media"]:
            # 统计单媒体文件夹
            for path in paths:
                console.print(f"\n扫描单媒体文件夹: [green]{path}[/green]")
                single_media_count = 0
                with Status("正在扫描...") as status:
                    for root, dirs, files in os.walk(path):
                        status.update(f"扫描: {root}")
                        if len(dirs) == 0 and len(files) == 1:
                            file = Path(os.path.join(root, files[0]))
                            if any(file.name.lower().endswith(ext) for ext in VIDEO_FORMATS) or any(file.name.lower().endswith(ext) for ext in ARCHIVE_FORMATS):
                                single_media_count += 1
                console.print(f"找到 [cyan]{single_media_count}[/cyan] 个单媒体文件夹")
        
        if operations["flatten"]:
            # 统计嵌套单文件夹
            for path in paths:
                console.print(f"\n扫描嵌套单文件夹: [green]{path}[/green]")
                nested_count = 0
                with Status("正在扫描...") as status:
                    for root, dirs, files in os.walk(path):
                        status.update(f"扫描: {root}")
                        if len(dirs) == 1 and len(files) == 0:
                            nested_count += 1
                console.print(f"找到 [cyan]{nested_count}[/cyan] 个嵌套单文件夹")
        
        if operations["remove_empty"]:
            # 统计空文件夹
            for path in paths:
                console.print(f"\n扫描空文件夹: [green]{path}[/green]")
                empty_count = 0
                with Status("正在扫描...") as status:
                    for root, dirs, files in os.walk(path, topdown=False):
                        status.update(f"扫描: {root}")
                        for dir_name in dirs:
                            dir_path = Path(os.path.join(root, dir_name))
                            if dir_path.exists() and not any(dir_path.iterdir()):
                                empty_count += 1
                console.print(f"找到 [cyan]{empty_count}[/cyan] 个空文件夹")
        
        if operations["clean_backup"]:
            # 统计备份和临时文件
            for path in paths:
                console.print(f"\n扫描备份和临时文件: [green]{path}[/green]")
                backup_count = 0
                temp_count = 0
                with Status("正在扫描...") as status:
                    for root, dirs, files in os.walk(path):
                        status.update(f"扫描: {root}")
                        # 统计备份文件
                        for file in files:
                            if file.endswith('.bak'):
                                backup_count += 1
                        # 统计临时文件夹
                        for dir_name in dirs:
                            if dir_name.startswith('temp_'):
                                temp_count += 1
                console.print(f"找到 [cyan]{backup_count}[/cyan] 个备份文件和 [cyan]{temp_count}[/cyan] 个临时文件夹")


def execute_operations(paths: List[Path], operations: Dict[str, bool], exclude_keywords: List[str],
                      file_conflict: str = 'auto', dir_conflict: str = 'auto') -> None:
    """执行选定的操作"""
    console.print("\n[bold blue]== 执行操作 ==[/bold blue]")
    
    # 创建自定义日志记录器
    class RichLogger:
        def info(self, message):
            console.print(message)
        def warning(self, message):
            console.print(f"[yellow]{message}[/yellow]")
        def error(self, message):
            console.print(f"[red]{message}[/red]")
    
    rich_logger = RichLogger()
    
    # 如果是直接解散模式
    if operations["dissolve"]:
        for path in paths:
            console.print(Rule(f"直接解散文件夹: {path}"))
            dissolve_folder(
                path, 
                file_conflict=file_conflict, 
                dir_conflict=dir_conflict, 
                logger=rich_logger
            )
        return
        
    # 执行其他操作
    for path in paths:
        console.print(Rule(f"处理目录: {path}"))
        if operations["release_media"]:
            console.print("\n[bold cyan]>>> 释放单独媒体文件夹...[/bold cyan]")
            release_single_media_folder(path, exclude_keywords)
        if operations["flatten"]:
            console.print("\n[bold cyan]>>> 解散嵌套的单独文件夹...[/bold cyan]")
            flatten_single_subfolder(path, exclude_keywords)
        
        if operations["remove_empty"]:
            console.print("\n[bold cyan]>>> 删除空文件夹...[/bold cyan]")
            remove_empty_folders(path, exclude_keywords)
        
        if operations["clean_backup"]:
            console.print("\n[bold cyan]>>> 清理备份文件和临时文件夹...[/bold cyan]")
            remove_backup_and_temp(path, exclude_keywords)
    
    console.print("\n[bold green]所有操作已完成![/bold green]")


def check_requirements() -> None:
    """检查必要的依赖"""
    missing_deps = []
    
    # 检查 Rich
    try:
        import rich
    except ImportError:
        missing_deps.append("rich")
    
    # 检查 pyperclip (可选)
    try:
        import pyperclip
    except ImportError:
        console.print("[yellow]提示: pyperclip 模块未安装，从剪贴板读取功能将不可用[/yellow]")
        console.print("可以通过 pip install pyperclip 安装")
    
    # 如果缺少必要依赖，退出
    if missing_deps:
        console.print("[red]错误: 缺少必要的依赖[/red]")
        console.print(f"请安装以下库: {', '.join(missing_deps)}")
        console.print(f"可以使用: pip install {' '.join(missing_deps)}")
        sys.exit(1)


def show_welcome() -> None:
    """显示欢迎信息"""
    console.print(Panel.fit(
        Markdown("# OrganizeFolder 交互式界面"),
        title=f"版本 {__version__}",
        border_style="blue"
    ))
    
    console.print("\n[bold]OrganizeFolder[/bold] 是一个文件夹整理工具，提供以下功能:")
    console.print("- [cyan]释放单独媒体文件夹[/cyan]: 将只包含单个视频或压缩包的文件夹解散")
    console.print("- [cyan]解散嵌套的单独文件夹[/cyan]: 解散只有一个子文件夹的嵌套文件夹")
    console.print("- [cyan]直接解散指定文件夹[/cyan]: 将整个文件夹的内容移动到其父文件夹")
    console.print("- [cyan]删除空文件夹[/cyan]: 删除所有空的文件夹")
    console.print("- [cyan]删除备份和临时文件[/cyan]: 删除备份文件(.bak)和临时文件夹(temp_)")
    
    # console.print("\n按 [bold green]Enter[/bold green] 键继续...", end="")
    # input()


def run_interactive() -> None:
    """运行交互式界面 - 仅作为中转，显示子包选项"""
    # 检查依赖
    check_requirements()
    
    # 显示欢迎信息
    show_welcome()
    
    # 显示子包选项
    console.print("\n[bold blue]== 请选择要使用的功能 ==[/bold blue]")
    
    table = Table(title="可用功能模块")
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_column("说明", style="magenta")
    table.add_row("1", "交互式界面", "使用完整的交互式界面进行操作")
    table.add_row("2", "清理功能", "删除空文件夹和备份文件")
    table.add_row("3", "解散功能", "解散嵌套文件夹")
    table.add_row("4", "迁移功能", "迁移文件")
    table.add_row("5", "合并功能", "合并部分文件夹")
    table.add_row("6", "退出程序", "退出 OrganizeFolder")
    
    console.print(table)
    
    # 获取用户选择
    choice = Prompt.ask("请选择功能", choices=["1", "2", "3", "4", "5", "6"], default="4")
    
    if choice == "1":
        # 进入完整的交互式界面
        run_full_interactive()
    elif choice == "2":
        # 运行清理功能
        console.print("\n[cyan]启动清理功能...[/cyan]")
        try:
            from cleanf.__main__ import app as clean_app
            clean_app()
        except ImportError as e:
            console.print(f"[red]错误：无法导入清理模块: {e}[/red]")
    elif choice == "3":
        # 运行解散功能
        console.print("\n[cyan]启动解散功能...[/cyan]")
        try:
            from dissolvef.__main__ import app as dissolve_app
            dissolve_app()
        except ImportError as e:
            console.print(f"[red]错误：无法导入解散模块: {e}[/red]")    
    elif choice == "4":
        # 运行迁移功能
        console.print("\n[cyan]启动迁移功能...[/cyan]")
        try:
            from migratef.pipe.__main__ import app as migrate_app
            migrate_app()
        except ImportError as e:
            console.print(f"[red]错误：无法导入迁移模块: {e}[/red]")
    elif choice == "5":
        # 运行合并功能
        console.print("\n[cyan]启动合并功能...[/cyan]")
        try:
            from mergef.__main__ import app as merge_app
            merge_app()
        except ImportError as e:
            console.print(f"[red]错误：无法导入合并模块: {e}[/red]")
    elif choice == "6":
        # 退出程序
        console.print("\n[bold green]感谢使用 OrganizeFolder![/bold green]")
        return
    
    # 询问是否返回主菜单
    if Confirm.ask("\n是否返回主菜单?", default=True):
        run_interactive()
    else:
        console.print("\n[bold green]感谢使用 OrganizeFolder![/bold green]")


def run_full_interactive() -> None:
    """运行完整的交互式界面"""
    continue_loop = True
    while continue_loop:
        # 选择路径
        paths = select_paths()
        if not paths:
            console.print("[yellow]未选择任何路径，操作取消[/yellow]")
            break
        
        # 选择要执行的操作
        operations = select_operations()
        if not any(operations.values()):
            console.print("[yellow]未选择任何操作，程序退出[/yellow]")
            break
        
        # 选择排除关键词
        exclude_keywords = select_exclude_keywords()
        
        # 如果选择了直接解散，设置冲突处理方式
        file_conflict = dir_conflict = 'auto'
        if operations["dissolve"]:
            file_conflict, dir_conflict = select_conflict_handling()
        
        # 预览操作
        if Confirm.ask("是否先预览操作?", default=True):
            display_preview(paths, operations)
        
        # 确认执行
        if Confirm.ask("是否执行所选操作?", default=True):
            execute_operations(paths, operations, exclude_keywords, file_conflict, dir_conflict)
        else:
            console.print("[yellow]操作已取消[/yellow]")
        
        # 询问是否继续迭代
        continue_loop = Confirm.ask("是否继续迭代?", default=False)
    
    # 完成
    console.print("\n[bold green]感谢使用 OrganizeFolder![/bold green]")
    console.print("按 [bold green]Enter[/bold green] 键退出...", end="")
    input()


if __name__ == "__main__":
    try:
        run_interactive()
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]发生错误:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        console.print("\n按 [bold]Enter[/bold] 键退出...", end="")
        input()