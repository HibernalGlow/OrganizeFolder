"""
migrate 包的命令行入口点，使其能够作为独立的命令行工具运行
"""
import sys
import argparse
from pathlib import Path
from typing import List
import os
import logging

# 导入迁移功能
from .migrate import migrate_files_with_structure, get_source_files_interactively, get_target_dir_interactively

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("migrate")

def get_paths_from_clipboard() -> List[str]:
    """从剪贴板读取多行路径"""
    paths = []
    try:
        import pyperclip
        clipboard_content = pyperclip.paste()
        if clipboard_content:
            for line in clipboard_content.splitlines():
                if line := line.strip().strip('"').strip("'"):
                    path = Path(line)
                    if path.exists() and path.is_file():  # 确保是文件而非目录
                        paths.append(str(path))
                    else:
                        logger.warning(f"警告：路径不存在或不是文件 - {line}")
            
            logger.info(f"从剪贴板读取到 {len(paths)} 个有效文件路径")
    except ImportError:
        logger.warning("未安装pyperclip模块，无法从剪贴板读取。")
    except Exception as e:
        logger.warning(f"读取剪贴板失败: {e}")
    
    return paths

def main():
    """主函数：处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description='文件迁移工具')
    parser.add_argument('files', nargs='*', help='要迁移的文件列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取文件路径')
    parser.add_argument('--target', '-t', type=str, help='目标根目录路径')
    parser.add_argument('--action', '-a', choices=['copy', 'move'], default='copy', 
                       help='操作类型：copy(复制)或move(移动)，默认为copy')
    parser.add_argument('--threads', '-n', type=int, default=os.cpu_count(),
                       help=f'线程数，默认为CPU核心数({os.cpu_count()})')
    parser.add_argument('--interactive', '-i', action='store_true',
                      help='交互模式，使用富文本界面')
    
    args = parser.parse_args()
    
    # 如果指定了交互模式，调用原始的交互函数
    if args.interactive:
        # 使用原始的交互式界面
        from rich.console import Console
        from rich.rule import Rule

        console = Console()
        console.rule("[bold blue]文件结构迁移工具 (交互模式)[/bold blue]")

        # 获取操作类型
        from rich.prompt import Prompt
        action_choice = Prompt.ask(
            "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
            choices=["copy", "move"],
            default="copy"
        ).lower()
        
        # 获取线程数
        num_threads_str = Prompt.ask(
            "[bold cyan]请输入要使用的最大线程数（留空则使用 CPU 核心数）[/bold cyan]",
            default=str(os.cpu_count()), # 默认显示 CPU 核心数
            show_default=True
        )
        try:
            num_threads = int(num_threads_str) if num_threads_str else None
            if num_threads is not None and num_threads <= 0:
                console.print("[yellow]线程数必须大于 0，将使用默认值。[/yellow]")
                num_threads = None
        except ValueError:
            console.print("[yellow]无效的线程数输入，将使用默认值。[/yellow]")
            num_threads = None
        
        # 交互式获取源文件
        source_files = get_source_files_interactively()
        
        # 只有当有文件时才获取目标目录
        if source_files:
            target_dir = get_target_dir_interactively()
            # 执行迁移
            migrate_files_with_structure(source_files, target_dir, max_workers=num_threads, action=action_choice)
        else:
            console.print("[yellow]没有有效的源文件被添加，迁移操作未执行。[/yellow]")
            
        console.rule("[bold blue]操作结束[/bold blue]")
        return
    
    # 非交互模式下
    # 获取要迁移的文件
    files = []
    
    if args.clipboard:
        files.extend(get_paths_from_clipboard())
    
    if args.files:
        for file_str in args.files:
            path = Path(file_str.strip('"').strip("'"))
            if path.exists() and path.is_file():
                files.append(str(path))
            else:
                logger.warning(f"警告：路径不存在或不是文件 - {file_str}")
    
    if not files:
        logger.info("请输入要迁移的文件路径，每行一个，输入空行结束:")
        while True:
            try:
                if line := input().strip():
                    path = Path(line.strip('"').strip("'"))
                    if path.exists() and path.is_file():
                        files.append(str(path))
                    else:
                        logger.warning(f"警告：路径不存在或不是文件 - {line}")
                else:
                    break
            except KeyboardInterrupt:
                logger.info("\n操作已取消")
                return
    
    if not files:
        logger.warning("未提供任何有效的文件路径")
        parser.print_help()
        return
    
    # 获取目标目录
    target_dir = args.target
    if not target_dir:
        logger.info("请输入目标根目录路径:")
        target_dir = input().strip()
    
    if not target_dir:
        logger.warning("未提供目标目录")
        return
    
    # 确保目标目录存在
    target_path = Path(target_dir)
    try:
        target_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"创建目标目录失败: {e}")
        return
    
    logger.info(f"\n开始迁移文件:")
    logger.info(f"- 操作类型: {'复制' if args.action == 'copy' else '移动'}")
    logger.info(f"- 文件数量: {len(files)}")
    logger.info(f"- 目标目录: {target_dir}")
    logger.info(f"- 线程数量: {args.threads}")
    
    # 执行迁移
    try:
        migrate_files_with_structure(files, target_dir, max_workers=args.threads, action=args.action)
        logger.info("\n文件迁移完成")
    except Exception as e:
        logger.error(f"\n文件迁移过程中发生错误: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        sys.exit(1)