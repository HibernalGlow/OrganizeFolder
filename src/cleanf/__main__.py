"""
cleaner 包的命令行入口点，使其能够作为独立的命令行工具运行
"""
import sys
import argparse
from pathlib import Path
from typing import List
import logging

from .empty import remove_empty_folders
from .backup import remove_backup_and_temp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("cleaner")

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

def main():
    """主函数：处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description='文件清理工具')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取路径')
    
    # 清理模式
    group = parser.add_argument_group('清理模式')
    group.add_argument('--empty', '-e', action='store_true', help='删除空文件夹')
    group.add_argument('--backup', '-b', action='store_true', help='删除备份文件和临时文件夹')
    group.add_argument('--all', '-a', action='store_true', help='执行所有清理操作')
    
    parser.add_argument('--exclude', help='排除关键词列表，用逗号分隔多个关键词')
    
    args = parser.parse_args()
    
    # 处理清理模式参数
    remove_empty = args.empty or args.all
    clean_backup = args.backup or args.all
    
    if not (remove_empty or clean_backup):
        logger.info("提示：未指定任何清理操作，默认执行所有清理操作")
        remove_empty = clean_backup = True
    
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
    
    # 处理排除关键词
    exclude_keywords = []
    if args.exclude:
        exclude_keywords.extend(args.exclude.split(','))
    
    # 处理每个路径
    total_empty_removed = 0
    total_backup_removed = 0
    
    for path in paths:
        logger.info(f"\n处理目录: {path}")
        
        if remove_empty:
            logger.info("\n>>> 删除空文件夹...")
            removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, logger=logger)
            total_empty_removed += removed
        
        if clean_backup:
            logger.info("\n>>> 清理备份文件和临时文件夹...")
            removed, _ = remove_backup_and_temp(path, exclude_keywords=exclude_keywords, logger=logger)
            total_backup_removed += removed
    
    logger.info("\n清理总结:")
    if remove_empty:
        logger.info(f"- 删除空文件夹: {total_empty_removed} 个")
    if clean_backup:
        logger.info(f"- 删除备份和临时文件: {total_backup_removed} 个")
    logger.info(f"- 总计删除: {total_empty_removed + total_backup_removed} 个项目")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        sys.exit(1)