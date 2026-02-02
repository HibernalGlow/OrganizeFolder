from encodings.punycode import T
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
import os
import json
from synct.core.input_path import get_path, get_paths
from synct.core.extract_timestamp import extract_timestamp_from_name
from synct.core.sync_file_time import sync_folder_file_time
from synct.core.archive_folders import archive_folder, FORMATS
from synct.core.file_mode import scan_files_for_timestamp, categorize_files, archive_file
from datetime import datetime

console = Console()
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

logger, config_info = setup_logger(app_name="synct", console_output=True)

def get_first_level_folder_path(base_dst, format_key, dt):
    """获取一级文件夹的完整路径"""
    try:
        format_spec = FORMATS.get(format_key)
        if not format_spec:
            return None

        if isinstance(format_spec, list):
            # 多层格式，第一级是第一个格式
            first_level_name = dt.strftime(format_spec[0])
        else:
            # 单层格式，就是这个格式本身
            first_level_name = dt.strftime(format_spec)

        first_level_path = os.path.join(base_dst, first_level_name)
        return first_level_path

    except Exception as e:
        logger.warning(f"获取一级文件夹路径失败: {e}")
        return None

def is_timestamp_folder(folder_name, format_key):
    """检查文件夹名是否符合时间戳格式"""
    try:
        format_spec = FORMATS.get(format_key)
        if not format_spec:
            return False

        if isinstance(format_spec, list):
            # 多层格式，检查是否匹配第一层
            first_format = format_spec[0]
            datetime.strptime(folder_name, first_format)
            return True
        else:
            # 单层格式
            datetime.strptime(folder_name, format_spec)
            return True
    except ValueError:
        return False

def process_single_folder(path, base_dst, format_key, mode):
    """处理单个文件夹的归档操作"""
    operations = []
    folders_with_timestamp = []

    logger.info(f"处理文件夹: {path}")

    for name in os.listdir(path):
        item_path = os.path.join(path, name)

        # 检查文件夹是否存在（可能在扫描过程中被删除）
        if not os.path.exists(item_path):
            logger.warning(f"文件夹在处理过程中消失，跳过: {item_path}")
            continue

        # 如果base_dst等于path（直接创建模式），则跳过已经是时间戳格式的文件夹
        if item_path == base_dst:
            continue

        # 如果是直接创建模式，跳过已经是时间戳格式的文件夹
        if base_dst == path and os.path.isdir(item_path):
            # 检查是否是时间戳格式的文件夹
            if is_timestamp_folder(name, format_key):
                logger.debug(f"跳过时间戳格式文件夹: {name}")
                continue

        if mode == 2:
            # 模式2：全部用创建时间戳（包括文件和文件夹）
            ctime = os.stat(item_path).st_ctime
            dt = datetime.fromtimestamp(ctime)
            type_str = "文件夹" if os.path.isdir(item_path) else "文件"
            logger.info(f"模式2-用创建时间 {dt} 作为 {type_str} {name} 的时间戳")
            console.print(f"[yellow]模式2-用创建时间 {dt.strftime('%Y-%m-%d')} 作为 {type_str} {name} 的时间戳")
        else:
            if not os.path.isdir(item_path):
                continue
            dt = extract_timestamp_from_name(name)
            if not dt:
                # 兼容原有兜底逻辑
                ctime = os.stat(item_path).st_ctime
                dt = datetime.fromtimestamp(ctime)
                logger.warning(f"未识别到时间戳: {name}，已用创建时间 {dt} 作为时间戳")
                console.print(f"[yellow]未识别到时间戳: {name}，已用创建时间 {dt.strftime('%Y-%m-%d')} 作为时间戳")
            else:
                logger.debug(f"从文件夹名 {name} 识别到时间戳: {dt}")

        folders_with_timestamp.append((item_path, dt, name))

        # 预览
        preview_path = archive_folder(item_path, dt, base_dst, format_key, dry_run=True)

        # 提取相对路径，更好地展示变化
        rel_dst = os.path.relpath(preview_path, base_dst)

        operations.append({
            "folder": name,
            "timestamp": dt,
            "destination": preview_path,
            "rel_destination": rel_dst,
            "source_path": path
        })

    return operations, folders_with_timestamp


def file_main():
    """文件模式主入口"""
    logger.info("开始执行文件模式 - 根据文件名时间戳分类")
    paths = get_paths()
    if not paths:
        logger.warning("未获取到有效路径，程序退出")
        return

    if len(paths) == 1:
        logger.info(f"单文件夹模式，工作目录: {paths[0]}")
        console.print(f"[green]工作目录: {paths[0]}[/green]")
    else:
        logger.info(f"多文件夹模式，获取到 {len(paths)} 个工作目录")
        console.print(f"[green]多文件夹模式，获取到 {len(paths)} 个工作目录[/green]")
        for i, path in enumerate(paths, 1):
            console.print(f"  {i}. {path}")

    # 是否递归扫描
    recursive = Confirm.ask("是否递归扫描子目录？", default=False)
    logger.info(f"递归扫描: {recursive}")

    # 归档目录策略
    console.print("\n[bold]归档目录策略选择:[/bold]")
    console.print("1. 在文件夹内创建'归档'目录")
    console.print("2. 直接在当前文件夹下创建时间戳文件夹")
    strategy = IntPrompt.ask("请选择归档策略", choices=["1", "2"], default=2)
    use_archive_folder = strategy == 1

    # 格式选择
    console.print("\n[bold]可用的归档格式:[/bold]")
    format_table = Table(show_header=True)
    format_table.add_column("序号", style="cyan")
    format_table.add_column("格式名")
    format_table.add_column("类型")
    format_table.add_column("示例")

    format_index_map = {}
    format_index = 1

    for key, format_spec in FORMATS.items():
        if not isinstance(format_spec, list):
            sample = datetime.now().strftime(format_spec)
            format_table.add_row(str(format_index), key, "单层", sample)
            format_index_map[format_index] = key
            format_index += 1

    for key, format_spec in FORMATS.items():
        if isinstance(format_spec, list):
            example_path = ""
            for fmt in format_spec:
                example_path = os.path.join(example_path, datetime.now().strftime(fmt))
            format_table.add_row(str(format_index), key, "多层", example_path)
            format_index_map[format_index] = key
            format_index += 1

    console.print(format_table)

    format_choice = IntPrompt.ask("请输入序号选择归档格式", default=2)
    while format_choice not in format_index_map:
        console.print(f"[red]无效的序号，请输入1-{max(format_index_map.keys())}之间的数字")
        format_choice = IntPrompt.ask("请输入序号选择归档格式", default=2)

    format_key = format_index_map[format_choice]
    logger.info(f"选择格式: {format_key}")
    console.print(f"已选择格式: [green]{format_key}")

    # 扫描并收集所有文件
    all_operations = []
    for path in paths:
        if use_archive_folder:
            base_dst = os.path.join(path, '归档')
        else:
            base_dst = path

        console.print(f"\n[cyan]扫描: {path}[/cyan]")
        files = scan_files_for_timestamp(path, recursive=recursive)
        operations = categorize_files(files, base_dst, format_key)

        for op in operations:
            op['source_path'] = path
            op['base_dst'] = base_dst
        all_operations.extend(operations)

    if not all_operations:
        console.print("[yellow]没有找到符合条件的文件")
        return

    # 预览
    console.print(f"\n[bold cyan]═══ 操作预览 ═══[/bold cyan]")
    console.print(f"[bold]共 {len(all_operations)} 个文件将被移动[/bold]\n")
    
    # 统计目标目录
    target_dirs = {}
    for op in all_operations:
        rel_dir = os.path.dirname(op['rel_destination'])
        if rel_dir not in target_dirs:
            target_dirs[rel_dir] = []
        target_dirs[rel_dir].append(op['filename'])
    
    # 显示目标目录统计
    console.print("[bold]目标目录分布:[/bold]")
    for target_dir, files in sorted(target_dirs.items()):
        console.print(f"  [green]{target_dir}/[/green] ({len(files)} 个文件)")
    
    # 预览表格
    console.print("\n[bold]文件操作详情:[/bold]")
    preview_table = Table(show_header=True, header_style="bold")
    preview_table.add_column("原文件名", style="yellow")
    preview_table.add_column("识别时间", style="blue")
    preview_table.add_column("目标路径", style="green")
    
    preview_count = min(10, len(all_operations))
    for op in all_operations[:preview_count]:
        preview_table.add_row(
            op['filename'],
            op['timestamp'].strftime('%Y-%m-%d'),
            op['rel_destination']
        )
    
    console.print(preview_table)
    
    if len(all_operations) > preview_count:
        console.print(f"  [dim]... 还有 {len(all_operations) - preview_count} 个文件未显示[/dim]")

    # 确认执行
    if Confirm.ask("\n确认执行以上操作？", default=True):
        logger.info("用户确认执行文件归档操作")
        success_count = 0
        fail_count = 0

        for op in all_operations:
            try:
                archive_file(
                    op['source'],
                    op['timestamp'],
                    op['base_dst'],
                    format_key
                )
                success_count += 1
                console.print(f"[green]✓ {op['filename']}[/green]")
            except Exception as e:
                fail_count += 1
                logger.error(f"移动文件失败 {op['filename']}: {e}")
                console.print(f"[red]✗ {op['filename']}: {e}[/red]")

        console.print(f"\n[bold]完成: 成功 {success_count}, 失败 {fail_count}[/bold]")
    else:
        console.print("[yellow]操作已取消")


def main():
    logger.info("开始执行时间戳文件同步与归档工具")
    
    # 模式选择
    console.print("[bold]选择工作模式:[/bold]")
    console.print("1. 文件夹模式 - 根据文件夹名识别时间戳")
    console.print("2. 文件模式 - 根据文件名识别时间戳")
    work_mode = IntPrompt.ask("请选择模式", choices=["1", "2"], default=1)
    
    if work_mode == 2:
        file_main()
        return
    
    # 以下是原有的文件夹模式逻辑
    paths = get_paths()
    if not paths:
        logger.warning("未获取到有效路径，程序退出")
        return

    if len(paths) == 1:
        logger.info(f"单文件夹模式，工作目录: {paths[0]}")
        console.print(f"[green]工作目录: {paths[0]}[/green]")
    else:
        logger.info(f"多文件夹模式，获取到 {len(paths)} 个工作目录")
        console.print(f"[green]多文件夹模式，获取到 {len(paths)} 个工作目录[/green]")
        for i, path in enumerate(paths, 1):
            logger.info(f"工作目录 {i}: {path}")
            console.print(f"  {i}. {path}")

    # 归档目录策略选择
    console.print("\n[bold]归档目录策略选择:[/bold]")
    if len(paths) == 1:
        console.print("1. 在文件夹内创建'归档'目录")
        console.print("2. 直接在当前文件夹下创建时间戳文件夹（不创建归档目录）")

        strategy = IntPrompt.ask("请选择归档策略", choices=["1", "2"], default=2)

        if strategy == 1:
            archive_strategy = "independent"
            use_archive_folder = True
            logger.info("选择策略1：创建归档目录")
        else:
            archive_strategy = "independent"
            use_archive_folder = False
            logger.info("选择策略2：直接创建时间戳文件夹")
    else:
        console.print("1. 在每个文件夹内创建独立的'归档'目录")
        console.print("2. 统一归档到第一个文件夹的'归档'目录")
        console.print("3. 直接在各文件夹下创建时间戳文件夹（不创建归档目录）")

        strategy = IntPrompt.ask("请选择归档策略", choices=["1", "2", "3"], default=3)

        if strategy == 1:
            archive_strategy = "independent"
            use_archive_folder = True
            logger.info("选择策略1：每个文件夹独立归档")
        elif strategy == 2:
            archive_strategy = "unified"
            use_archive_folder = True
            unified_base_dst = os.path.join(paths[0], '归档')
            logger.info(f"选择策略2：统一归档到 {unified_base_dst}")
        else:
            archive_strategy = "independent"
            use_archive_folder = False
            logger.info("选择策略3：直接创建时间戳文件夹")
    
    # 使用rich展示可用格式
    console.print("[bold]可用的归档格式:[/bold]")

    # 创建单个表格，包含所有格式
    format_table = Table(show_header=True)
    format_table.add_column("序号", style="cyan")
    format_table.add_column("格式名")
    format_table.add_column("类型")
    format_table.add_column("说明")
    format_table.add_column("示例")

    # 将格式名称与序号映射
    format_index_map = {}
    format_index = 1

    # 先添加单层格式
    for key, format_spec in FORMATS.items():
        if not isinstance(format_spec, list):
            # 单层格式
            sample = datetime.now().strftime(format_spec)
            format_table.add_row(
                str(format_index),
                key,
                "单层",
                format_spec,
                sample
            )
            format_index_map[format_index] = key
            format_index += 1

    # 再添加多层格式
    for key, format_spec in FORMATS.items():
        if isinstance(format_spec, list):
            # 多层格式
            example_path = ""
            for fmt in format_spec:
                example_path = os.path.join(example_path, datetime.now().strftime(fmt))
            format_table.add_row(
                str(format_index),
                key,
                "多层",
                "→".join(format_spec),
                example_path
            )
            format_index_map[format_index] = key
            format_index += 1

    console.print(format_table)

    # 使用数字选择格式
    max_index = max(format_index_map.keys())
    format_index = IntPrompt.ask(
        "请输入序号选择归档格式",
        default=6,
        show_choices=False,
        show_default=True
    )

    # 验证输入的序号是否有效
    while format_index not in format_index_map:
        logger.warning(f"用户输入了无效的序号: {format_index}")
        console.print(f"[red]无效的序号，请输入1-{max_index}之间的数字")
        format_index = IntPrompt.ask(
            "请输入序号选择归档格式",
            default=1,
            show_choices=False,
            show_default=True
        )

    # 获取选择的格式
    format_key = format_index_map[format_index]
    logger.info(f"用户选择的归档格式: {format_key}")
    console.print(f"已选择格式: [green]{format_key}")

    # 新增：模式选择
    mode = IntPrompt.ask("请选择模式：1-按文件夹名识别时间戳，2-全部用创建时间戳", choices=["1", "2"], default=1)
    if mode == 2:
        logger.info("已选择模式2：全部用创建时间戳")
        console.print("[green]已选择模式2：全部用创建时间戳[/green]")
    else:
        logger.info("已选择模式1：按文件夹名识别时间戳")
        console.print("[green]已选择模式1：按文件夹名识别时间戳[/green]")

    # 收集所有操作用于预览
    all_operations = []
    all_folders_with_timestamp = []

    # 处理每个文件夹
    for path in paths:
        if archive_strategy == "independent":
            if use_archive_folder:
                base_dst = os.path.join(path, '归档')
            else:
                base_dst = path  # 直接在当前文件夹下创建
        else:  # unified
            base_dst = unified_base_dst

        operations, folders_with_timestamp = process_single_folder(path, base_dst, format_key, mode)
        all_operations.extend(operations)
        all_folders_with_timestamp.extend(folders_with_timestamp)

    # 创建JSON树结构
    preview_tree = {
        "处理模式": "多文件夹" if len(paths) > 1 else "单文件夹",
        "归档策略": "独立归档" if archive_strategy == "independent" else "统一归档",
        "使用归档文件夹": use_archive_folder,
        "格式": format_key,
        "格式详情": FORMATS[format_key],
        "一级文件夹": set(),  # 用于收集所有一级文件夹路径
        "文件夹": {}
    }

    # 按源路径分组显示
    for path in paths:
        path_operations = [op for op in all_operations if op["source_path"] == path]
        if path_operations:
            preview_tree["文件夹"][path] = {}

            # 确定当前路径的base_dst
            if archive_strategy == "independent":
                if use_archive_folder:
                    current_base_dst = os.path.join(path, '归档')
                else:
                    current_base_dst = path
            else:  # unified
                current_base_dst = unified_base_dst

            for op in path_operations:
                # 计算一级文件夹路径
                first_level_folder = get_first_level_folder_path(current_base_dst, format_key, op["timestamp"])
                if first_level_folder:
                    preview_tree["一级文件夹"].add(first_level_folder)

                preview_tree["文件夹"][path][op["folder"]] = {
                    "识别时间": op["timestamp"].strftime("%Y-%m-%d"),
                    "目标路径": op["rel_destination"],
                    "一级文件夹": first_level_folder
                }

    # 将set转换为sorted list以便JSON序列化
    preview_tree["一级文件夹"] = sorted(list(preview_tree["一级文件夹"]))
    
    # 显示预览表格
    if not all_operations:
        logger.warning("没有找到符合条件的文件夹")
        console.print("[yellow]没有找到符合条件的文件夹")
        return

    # 保存预览JSON到第一个路径
    preview_json_path = os.path.join(paths[0], "synct_preview.json")
    with open(preview_json_path, "w", encoding="utf-8") as f:
        json.dump(preview_tree, f, ensure_ascii=False, indent=2)
    logger.info(f"预览已保存到: {preview_json_path}")
    console.print(f"[blue]预览已保存到: {preview_json_path}")

    # 创建文件树形式的预览
    console.print("\n[bold]预览将要执行的操作:[/bold]")

    # 创建根树
    if len(paths) == 1:
        root_tree = Tree(f"[bold]{paths[0]}[/bold]")
    else:
        root_tree = Tree(f"[bold]多文件夹处理 ({len(paths)} 个文件夹)[/bold]")

    # 按路径分组显示预览
    for path in paths:
        path_operations = [op for op in all_operations if op["source_path"] == path]
        if path_operations:
            if len(paths) > 1:
                path_node = root_tree.add(f"[cyan]{path}[/cyan]")
            else:
                path_node = root_tree

            # 预览前三个文件夹（如果有的话）
            show_count = min(3, len(path_operations))
            for i, op in enumerate(path_operations[:show_count]):
                folder_node = path_node.add(f"[yellow]{op['folder']}[/yellow] -> [green]{op['rel_destination']}[/green]")
                folder_node.add(f"[blue]识别时间戳: {op['timestamp'].strftime('%Y-%m-%d')}[/blue]")

            # 如果有更多文件夹，显示省略信息
            if len(path_operations) > show_count:
                path_node.add(f"[dim]... 还有 {len(path_operations) - show_count} 个文件夹[/dim]")

    # 打印树
    rprint(root_tree)

    # 显示统计信息
    console.print(f"\n[bold]统计信息:[/bold]")
    console.print(f"总共处理 [cyan]{len(paths)}[/cyan] 个文件夹路径")
    console.print(f"总共找到 [cyan]{len(all_operations)}[/cyan] 个待归档项目")

    # 确认是否同步文件时间
    sync_time = Confirm.ask("是否同步文件时间？", default=True)
    logger.info(f"用户选择{'同步' if sync_time else '不同步'}文件时间")

    # 确认是否执行移动操作
    if Confirm.ask("确认执行以上操作？", default=True):
        logger.info("用户确认执行归档操作")

        # 按路径分组执行
        for path in paths:
            path_folders = [(folder_path, dt, name) for folder_path, dt, name in all_folders_with_timestamp
                           if any(op["source_path"] == path and op["folder"] == name for op in all_operations)]

            if not path_folders:
                continue

            console.print(f"\n[bold]处理路径: {path}[/bold]")

            # 确定归档目录（与预览阶段保持一致）
            if archive_strategy == "independent":
                if use_archive_folder:
                    current_base_dst = os.path.join(path, '归档')
                else:
                    current_base_dst = path  # 直接在当前文件夹下创建
            else:  # unified
                current_base_dst = unified_base_dst

            for folder_path, dt, name in path_folders:
                logger.info(f"处理文件夹: {name}, 时间戳: {dt}")
                console.print(f"[green]处理: {name} -> {dt}")

                # 检查源文件夹是否存在
                if not os.path.exists(folder_path):
                    logger.warning(f"源文件夹不存在，跳过: {folder_path}")
                    console.print(f"[yellow]⚠️ 源文件夹不存在，跳过: {name}")
                    continue

                try:
                    if sync_time:
                        logger.info(f"同步文件时间: {folder_path}")
                        sync_folder_file_time(folder_path, dt)
                        console.print(f"[blue]已同步文件时间: {folder_path}")

                    new_path = archive_folder(folder_path, dt, current_base_dst, format_key)
                    logger.info(f"已归档到: {new_path}")
                    console.print(f"[cyan]已归档到: {new_path}")
                except FileNotFoundError as e:
                    logger.warning(f"文件操作失败，跳过 {name}: {e}")
                    console.print(f"[yellow]⚠️ 文件操作失败，跳过: {name}")
                    continue
                except Exception as e:
                    logger.error(f"处理文件夹 {name} 时发生错误: {e}")
                    console.print(f"[red]❌ 处理文件夹 {name} 时发生错误: {e}")
                    continue
    else:
        logger.warning("用户取消了操作")
        console.print("[yellow]操作已取消")

if __name__ == "__main__":
    main()
