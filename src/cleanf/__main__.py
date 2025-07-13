"""
cleaner 包的命令行入口点，使用 Typer 实现命令行界面
"""
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import logging
import typer
from rich.console import Console

from cleanf.empty import remove_empty_folders
from cleanf.backup import remove_backup_and_temp

# 创建 Typer 应用
app = typer.Typer(help="文件清理工具 - 删除空文件夹和备份文件")

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

logger, config_info = setup_logger(app_name="cleanf", console_output=True)


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
        from rich.columns import Columns
    except ImportError:
        logger.warning("未安装rich模块，无法使用交互式界面，将使用命令行模式")
        logger.info("提示: 可以通过 pip install rich 安装")
        return False
        
    # 创建控制台
    console = Console()
    
    # 导入配置
    from cleanf.config import CLEANING_PRESETS, PRESET_COMBINATIONS
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "# 文件清理工具\n\n一个用于清理文件夹的工具，提供多种清理预设和自定义组合功能",
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
    
    # 选择清理模式
    console.print("\n[bold blue]== 选择清理模式 ==[/bold blue]")
    console.print("1. 使用预设组合")
    console.print("2. 自定义选择清理项目")
    
    mode = Prompt.ask("请选择清理模式", choices=["1", "2"], default="1")
    
    selected_presets = []
    
    if mode == "1":
        # 显示预设组合
        console.print("\n[bold green]== 可用的预设组合 ==[/bold green]")
        
        combo_table = Table(title="预设组合")
        combo_table.add_column("序号", style="cyan", width=4)
        combo_table.add_column("名称", style="green", width=15)
        combo_table.add_column("说明", style="magenta", width=40)
        combo_table.add_column("包含项目", style="yellow", width=20)
        
        combo_list = list(PRESET_COMBINATIONS.items())
        for i, (key, combo) in enumerate(combo_list, 1):
            preset_names = [CLEANING_PRESETS[p]["name"] for p in combo["presets"] if p in CLEANING_PRESETS]
            combo_table.add_row(
                str(i), 
                combo["name"], 
                combo["description"],
                "\n".join(preset_names[:3]) + ("..." if len(preset_names) > 3 else "")
            )
        
        console.print(combo_table)
        
        combo_choice = Prompt.ask(
            f"请选择预设组合 (1-{len(combo_list)})", 
            choices=[str(i) for i in range(1, len(combo_list) + 1)], 
            default="2"
        )
        
        selected_combo = combo_list[int(combo_choice) - 1][1]
        selected_presets = selected_combo["presets"]
        
        console.print(f"\n[green]已选择预设组合: {selected_combo['name']}[/green]")
        
    else:
        # 自定义选择清理项目
        console.print("\n[bold green]== 自定义选择清理项目 ==[/bold green]")
        
        preset_table = Table(title="可用的清理项目")
        preset_table.add_column("序号", style="cyan", width=4)
        preset_table.add_column("名称", style="green", width=20)
        preset_table.add_column("说明", style="magenta", width=35)
        preset_table.add_column("默认", style="yellow", width=6)
        
        preset_list = list(CLEANING_PRESETS.items())
        for i, (key, preset) in enumerate(preset_list, 1):
            preset_table.add_row(
                str(i),
                preset["name"],
                preset["description"], 
                "✓" if preset["enabled"] else "✗"
            )
        
        console.print(preset_table)
        
        console.print("\n[yellow]提示: 输入序号选择项目，多个项目用逗号分隔，如: 1,2,3[/yellow]")
        console.print("[yellow]      按回车键使用默认启用的项目[/yellow]")
        
        choice_input = Prompt.ask("请选择要执行的清理项目", default="")
        
        if choice_input.strip():
            try:
                choices = [int(c.strip()) for c in choice_input.split(",")]
                selected_presets = [preset_list[i-1][0] for i in choices if 1 <= i <= len(preset_list)]
            except ValueError:
                console.print("[red]输入格式错误，将使用默认配置[/red]")
                selected_presets = [key for key, preset in CLEANING_PRESETS.items() if preset["enabled"]]
        else:
            # 使用默认启用的预设
            selected_presets = [key for key, preset in CLEANING_PRESETS.items() if preset["enabled"]]
    
    # 显示选中的清理项目
    if selected_presets:
        console.print("\n[bold cyan]== 将执行以下清理项目 ==[/bold cyan]")
        for preset_key in selected_presets:
            if preset_key in CLEANING_PRESETS:
                preset = CLEANING_PRESETS[preset_key]
                console.print(f"• [green]{preset['name']}[/green]: {preset['description']}")
    
    # 选择排除关键词
    exclude_keywords = []
    if Confirm.ask("\n是否要排除某些文件夹/文件?", default=False):
        console.print("请输入排除关键词，多个关键词用逗号分隔:")
        keywords = input().strip()
        if keywords:
            exclude_keywords.extend([kw.strip() for kw in keywords.split(",")])
      # 最终确认
    if not Confirm.ask(f"\n确认开始清理 {len(paths)} 个路径?", default=True):
        console.print("[yellow]操作已取消[/yellow]")
        return False
    
    # 预览模式 - 收集所有要删除的文件
    console.print("\n[bold cyan]== 正在扫描要删除的文件... ==[/bold cyan]")
    all_files_to_delete = []
    
    for path in paths:
        for preset_key in selected_presets:
            if preset_key not in CLEANING_PRESETS:
                continue
                
            preset = CLEANING_PRESETS[preset_key]
            
            try:
                if preset["function"] == "remove_empty_folders":
                    files_to_delete, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, preview_mode=True)
                elif preset["function"] == "remove_backup_and_temp":
                    # 使用预设中定义的patterns
                    patterns = preset.get("patterns", [])
                    files_to_delete, _ = remove_backup_and_temp(
                        path, 
                        exclude_keywords=exclude_keywords,
                        custom_patterns=patterns,
                        preview_mode=True
                    )
                else:
                    continue
                
                # 添加标记信息到文件路径
                for file_path in files_to_delete:
                    all_files_to_delete.append((file_path, preset['name']))
                
            except Exception as e:
                console.print(f"[red]扫描 {preset['name']} 时出错: {e}[/red]")
    
    # 显示预览
    if all_files_to_delete:
        from cleanf.preview import preview_deletion
        
        # 只传递路径，不包含预设信息
        files_only = [item[0] for item in all_files_to_delete]
        
        # 显示预览并询问确认
        if not preview_deletion(files_only, "文件删除预览", console):
            console.print("[yellow]用户取消了删除操作[/yellow]")
            return True
    else:
        console.print("[yellow]没有找到要删除的文件[/yellow]")
        return True
    
    # 执行清理操作
    total_removed = {}
    
    for path in paths:
        console.print(Rule(f"处理目录: {path}"))
        
        for preset_key in selected_presets:
            if preset_key not in CLEANING_PRESETS:
                continue
                
            preset = CLEANING_PRESETS[preset_key]
            console.print(f"\n[bold cyan]>>> {preset['name']}...[/bold cyan]")
            
            try:
                if preset["function"] == "remove_empty_folders":
                    removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords)
                elif preset["function"] == "remove_backup_and_temp":
                    # 使用预设中定义的patterns
                    patterns = preset.get("patterns", [])
                    removed, _ = remove_backup_and_temp(
                        path, 
                        exclude_keywords=exclude_keywords,
                        custom_patterns=patterns
                    )
                else:
                    console.print(f"[red]未知的清理函数: {preset['function']}[/red]")
                    continue
                
                if preset_key not in total_removed:
                    total_removed[preset_key] = 0
                total_removed[preset_key] += removed
                
            except Exception as e:
                console.print(f"[red]执行 {preset['name']} 时出错: {e}[/red]")
    
    # 输出总结信息
    console.print("\n[bold blue]== 清理总结 ==[/bold blue]")
    total_count = 0
    for preset_key, count in total_removed.items():
        if preset_key in CLEANING_PRESETS:
            preset_name = CLEANING_PRESETS[preset_key]["name"]
            console.print(f"• {preset_name}: [green]{count}[/green] 个")
            total_count += count
    
    console.print(f"\n[bold green]总计删除: {total_count} 个项目[/bold green]")
    console.print(f"日志文件: {config_info.get('log_file', 'N/A')}")
    
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
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="使用预设组合 (basic/standard/advanced/development/system/complete)"),
    list_presets: bool = typer.Option(False, "--list-presets", help="列出所有可用的预设"),
    preview: bool = typer.Option(False, "--preview", help="预览要删除的文件（不实际删除）"),
    exclude: Optional[str] = typer.Option(None, help="排除关键词列表，用逗号分隔多个关键词")
):
    """清理文件夹：删除空文件夹和备份文件"""
    
    # 如果请求列出预设
    if list_presets:
        from cleanf.config import CLEANING_PRESETS, PRESET_COMBINATIONS
        
        logger.info("=== 可用的清理预设 ===")
        for key, preset in CLEANING_PRESETS.items():
            status = "✓" if preset["enabled"] else "✗"
            logger.info(f"{status} {preset['name']}: {preset['description']}")
        
        logger.info("\n=== 可用的预设组合 ===")
        for key, combo in PRESET_COMBINATIONS.items():
            logger.info(f"• {combo['name']}: {combo['description']}")
            preset_names = [CLEANING_PRESETS[p]["name"] for p in combo["presets"] if p in CLEANING_PRESETS]
            logger.info(f"  包含: {', '.join(preset_names)}")
        return
    
    # 如果使用交互式界面，或者不带任何参数
    if interactive or (len(sys.argv) == 1):
        if run_interactive():
            return
        # 如果交互式界面失败或返回False，继续使用命令行模式
    
    # 命令行模式
    from cleanf.config import CLEANING_PRESETS, PRESET_COMBINATIONS
    
    # 处理预设
    selected_presets = []
    if preset:
        if preset in PRESET_COMBINATIONS:
            selected_presets = PRESET_COMBINATIONS[preset]["presets"]
            logger.info(f"使用预设组合: {PRESET_COMBINATIONS[preset]['name']}")
        else:
            logger.info(f"未知的预设组合: {preset}")
            logger.info("可用的预设组合: " + ", ".join(PRESET_COMBINATIONS.keys()))
            raise typer.Exit(code=1)
    else:
        # 处理传统的清理模式参数
        remove_empty = empty or all
        clean_backup = backup or all
        
        if not (remove_empty or clean_backup):
            logger.info("提示：未指定任何清理操作，默认执行基础清理操作")
            selected_presets = ["empty_folders", "backup_files"]
        else:
            if remove_empty:
                selected_presets.append("empty_folders")
            if clean_backup:
                selected_presets.append("backup_files")
    
    # 获取要处理的路径
    path_list = []
    
    if clipboard:
        path_list.extend(get_paths_from_clipboard())
    
    if paths:
        path_list.extend(paths)
    
    if not path_list:
        logger.info("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            try:
                line = input().strip()
                if not line:
                    break
                
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    path_list.append(path)
                else:
                    logger.info(f"警告：路径不存在 - {line}", err=True)
            except KeyboardInterrupt:
                logger.info("\n操作已取消")
                return
    
    if not path_list:
        logger.info("未提供任何有效的路径", err=True)
        raise typer.Exit(code=1)
    
    # 处理排除关键词
    exclude_keywords = []
    if exclude:
        exclude_keywords.extend(exclude.split(','))
      # 显示将要执行的操作
    logger.info("将执行以下清理操作:")
    for preset_key in selected_presets:
        if preset_key in CLEANING_PRESETS:
            preset = CLEANING_PRESETS[preset_key]
            logger.info(f"• {preset['name']}: {preset['description']}")
    
    # 预览模式 - 收集所有要删除的文件
    if preview:
        logger.info("\n正在扫描要删除的文件...")
        all_files_to_delete = []
        
        for path in path_list:
            for preset_key in selected_presets:
                if preset_key not in CLEANING_PRESETS:
                    continue
                    
                preset = CLEANING_PRESETS[preset_key]
                
                try:
                    if preset["function"] == "remove_empty_folders":
                        files_to_delete, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, preview_mode=True)
                    elif preset["function"] == "remove_backup_and_temp":
                        # 使用预设中定义的patterns
                        patterns = preset.get("patterns", [])
                        files_to_delete, _ = remove_backup_and_temp(
                            path, 
                            exclude_keywords=exclude_keywords,
                            custom_patterns=patterns,
                            preview_mode=True
                        )
                    else:
                        continue
                    
                    all_files_to_delete.extend(files_to_delete)
                    
                except Exception as e:
                    logger.info(f"扫描 {preset['name']} 时出错: {e}")
        
        # 显示预览
        if all_files_to_delete:
            from cleanf.preview import preview_deletion
            
            # 显示预览并询问确认
            if not preview_deletion(all_files_to_delete, "文件删除预览"):
                logger.info("用户取消了删除操作")
                return
        else:
            logger.info("没有找到要删除的文件")
            return
    
    # 执行清理操作
    total_removed = {}
    
    for path in path_list:
        logger.info(f"\n处理目录: {path}")
        
        for preset_key in selected_presets:
            if preset_key not in CLEANING_PRESETS:
                continue
                
            preset = CLEANING_PRESETS[preset_key]
            logger.info(f"\n>>> {preset['name']}...")
            
            try:
                if preset["function"] == "remove_empty_folders":
                    removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords)
                elif preset["function"] == "remove_backup_and_temp":
                    # 使用预设中定义的patterns
                    patterns = preset.get("patterns", [])
                    removed, _ = remove_backup_and_temp(
                        path, 
                        exclude_keywords=exclude_keywords,
                        custom_patterns=patterns
                    )
                else:
                    logger.info(f"未知的清理函数: {preset['function']}")
                    continue
                
                if preset_key not in total_removed:
                    total_removed[preset_key] = 0
                total_removed[preset_key] += removed
                
            except Exception as e:
                logger.info(f"执行 {preset['name']} 时出错: {e}")
    
    # 输出总结信息
    logger.info("\n清理总结:")
    total_count = 0
    for preset_key, count in total_removed.items():
        if preset_key in CLEANING_PRESETS:
            preset_name = CLEANING_PRESETS[preset_key]["name"]
            logger.info(f"• {preset_name}: {count} 个")
            total_count += count
    
    logger.info(f"总计删除: {total_count} 个项目")

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
        logger.info("\n操作已取消")
    except Exception as e:
        logger.info(f"发生错误: {e}", err=True)
        sys.exit(1)