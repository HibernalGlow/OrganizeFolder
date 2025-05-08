"""
OrganizeFolder 主包的命令行入口点
整合了所有子包的功能，提供统一的命令行界面和交互式界面
"""
import argparse
import sys
import time
import threading
from pathlib import Path
from enum import Enum
import os
from loguru import logger
from datetime import datetime

# 导入子包功能
from src.cleanf import remove_empty_folders, remove_backup_and_temp
from src.dissolvef import flatten_single_subfolder, release_single_media_folder, dissolve_folder
from src.migratef import migrate_files_with_structure
from src.organizef import __version__
from src.organizef.interactive import run_interactive

# 设置日志
def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统"""
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>"
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
        format="{time:YYYY-MM-DD HH:mm:ss} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

# 设置日志
setup_logger(app_name="organizefolder", console_output=True)

# 定义无限模式枚举
class InfiniteMode(Enum):
    NONE = "none"  # 不使用无限模式
    KEYBOARD = "keyboard"  # 键盘触发模式
    TIMER = "timer"  # 定时触发模式

def get_paths_from_clipboard():
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

def run_operations(paths, args, exclude_keywords):
    """执行所有操作的函数"""
    for path in paths:
        logger.info(f"\n处理目录: {path}")
        
        # 如果指定了dissolve模式，直接解散文件夹
        if args.dissolve:
            dissolve_folder(path, 
                          file_conflict=args.file_conflict,
                          dir_conflict=args.dir_conflict,
                          logger=logger)
            continue
        
        # 1. 释放单独媒体文件夹
        if args.release_media:
            logger.info("\n>>> 释放单独媒体文件夹...")
            release_single_media_folder(path, exclude_keywords, logger)
        
        # 2. 解散嵌套的单独文件夹
        if args.flatten:
            logger.info("\n>>> 解散嵌套的单独文件夹...")
            flatten_single_subfolder(path, exclude_keywords, logger)
        
        # 3. 删除空文件夹
        if args.remove_empty:
            logger.info("\n>>> 删除空文件夹...")
            remove_empty_folders(path, exclude_keywords, logger)
        
        # 4. 清理备份文件和临时文件夹
        if args.clean_backup:
            logger.info("\n>>> 清理备份文件和临时文件夹...")
            remove_backup_and_temp(path, exclude_keywords, logger)

def run_infinite_mode(paths, args, exclude_keywords):
    """运行无限模式"""
    logger.info("\n进入无限模式...")
    
    # 先执行一次操作
    run_operations(paths, args, exclude_keywords)
    
    if args.inf_mode == InfiniteMode.KEYBOARD:
        logger.info("按F2键重新执行操作，按Ctrl+C退出")
        
        try:
            import keyboard
            def on_f2_pressed(e):
                if e.name == 'f2':
                    logger.info("\n\n检测到F2按键，重新执行操作...")
                    run_operations(paths, args, exclude_keywords)
            
            # 注册F2按键事件
            keyboard.on_press(on_f2_pressed)
            
            # 保持程序运行
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("\n检测到Ctrl+C，程序退出")
                keyboard.unhook_all()
        except ImportError:
            logger.error("未安装keyboard模块，无法使用键盘触发模式。请使用 pip install keyboard 安装。")
            return
            
    elif args.inf_mode == InfiniteMode.TIMER:
        logger.info(f"每 {args.interval} 秒自动执行一次，按Ctrl+C退出")
        
        def timer_task():
            while True:
                time.sleep(args.interval)
                logger.info("\n\n定时触发，重新执行操作...")
                run_operations(paths, args, exclude_keywords)
        
        # 启动定时器线程
        timer_thread = threading.Thread(target=timer_task, daemon=True)
        timer_thread.start()
        
        # 保持主线程运行
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("\n检测到Ctrl+C，程序退出")

def main():
    """主函数：处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description='文件夹整理工具')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取路径')
    
    # 功能组
    function_group = parser.add_argument_group('功能选项')
    function_group.add_argument('--release-media', '-m', action='store_true', help='释放单独媒体文件夹')
    function_group.add.argument('--dissolve', '-d', action='store_true', help='直接解散指定文件夹')
    function_group.add.argument('--flatten', '-f', action='store_true', help='解散嵌套的单独文件夹')
    function_group.add.argument('--remove-empty', '-r', action='store_true', help='删除空文件夹')
    function_group.add.argument('--clean-backup', '-b', action='store_true', help='删除备份文件和临时文件夹')
    function_group.add.argument('--all', '-a', action='store_true', help='执行所有整理操作（不含直接解散）')
    
    # 冲突处理（仅用于直接解散模式）
    conflict_group = parser.add.argument_group('冲突处理（仅用于直接解散模式）')
    conflict_group.add.argument('--file-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                           default='auto', help='文件冲突处理方式 (默认: auto)')
    conflict_group.add.argument('--dir-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                          default='auto', help='文件夹冲突处理方式 (默认: auto)')
    
    # 无限模式相关参数
    inf_group = parser.add.argument_group('无限模式选项')
    inf_group.add.argument('--keyboard', action='store_true', help='无限模式-键盘触发(F2)')
    inf_group.add.argument('--timer', type=int, metavar='SECONDS', help='无限模式-定时触发(指定间隔秒数)')
    
    # 其他选项
    parser.add.argument('--exclude', help='排除关键词列表，用逗号分隔多个关键词')
    parser.add.argument('--version', '-v', action='version', version=f'OrganizeFolder {__version__}')
    parser.add.argument('--no-interactive', action='store_true', help='禁用交互式界面，使用传统命令行')
    
    # 判断是否需要交互式界面
    # 如果没有命令行参数（除了程序名称），则默认启用交互式界面
    if len(sys.argv) == 1:
        run_interactive()
        return

    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果没有指定 --no-interactive 并且没有指定任何操作，则启用交互式界面
    if not args.no_interactive and not any([
            args.release_media, args.dissolve, args.flatten, 
            args.remove_empty, args.clean_backup, args.all]):
        run_interactive()
        return
        
    # 从这里开始是传统的命令行处理逻辑
    logger.info(f"OrganizeFolder 命令行模式 (版本 {__version__})")
    
    # 处理解散模式参数
    if args.all:
        args.release_media = args.flatten = args.remove_empty = args.clean_backup = True
    
    # 处理无限模式参数
    args.inf_mode = InfiniteMode.NONE
    args.interval = 0
    if args.keyboard:
        args.inf_mode = InfiniteMode.KEYBOARD
    elif args.timer is not None:
        args.inf_mode = InfiniteMode.TIMER
        args.interval = args.timer

    # 获取要处理的路径
    paths = []
    
    if args.clipboard:
        paths.extend(get_paths_from_clipboard())
    
    if args.paths:
        for path_str in args.paths:
            path = Path(path_str.strip('"').strip("'"))
            if path.exists():
                paths.append(path)
            else:
                logger.warning(f"警告：路径不存在 - {path_str}")
    
    if not paths:
        logger.info("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            try:
                if line := input().strip():
                    path = Path(line.strip('"').strip("'"))
                    if path.exists():
                        paths.append(path)
                    else:
                        logger.warning(f"警告：路径不存在 - {line}")
                else:
                    break
            except KeyboardInterrupt:
                logger.info("\n操作已取消")
                return
    
    if not paths:
        logger.warning("未提供任何有效的路径")
        parser.print_help()
        return
    
    # 如果没有指定任何操作，提示用户
    if not any([args.release_media, args.flatten, args.remove_empty, 
                args.dissolve, args.clean_backup]):
        logger.warning("错误：未指定任何操作。请使用 -h 参数查看帮助信息。")
        return
    
    # 处理排除关键词
    exclude_keywords = ["单行"]  # 排除关键词
    if args.exclude:
        exclude_keywords.extend(args.exclude.split(','))
    
    # 执行操作
    if args.inf_mode != InfiniteMode.NONE:
        run_infinite_mode(paths, args, exclude_keywords)
    else:
        run_operations(paths, args, exclude_keywords)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        sys.exit(1)