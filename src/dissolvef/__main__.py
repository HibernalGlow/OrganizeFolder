"""
dissolve 包的命令行入口点，使其能够作为独立的命令行工具运行
"""
import sys
import argparse
from pathlib import Path
from typing import List
import logging

from .nested import flatten_single_subfolder
from .media import release_single_media_folder
from .direct import dissolve_folder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("dissolve")

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
    parser = argparse.ArgumentParser(description='文件夹解散工具')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取路径')
    
    # 解散模式
    group = parser.add_argument_group('解散模式（至少选择一项）')
    group.add_argument('--direct', '-d', action='store_true', help='直接解散指定文件夹')
    group.add_argument('--nested', '-n', action='store_true', help='解散嵌套的单一文件夹')
    group.add_argument('--media', '-m', action='store_true', help='解散单媒体文件夹')
    group.add_argument('--all', '-a', action='store_true', help='执行所有解散操作（不含直接解散）')
    
    # 冲突处理（仅用于直接解散模式）
    conflict_group = parser.add_argument_group('冲突处理（仅用于直接解散模式）')
    conflict_group.add_argument('--file-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                           default='auto', help='文件冲突处理方式 (默认: auto)')
    conflict_group.add_argument('--dir-conflict', choices=['auto', 'skip', 'overwrite', 'rename'], 
                          default='auto', help='文件夹冲突处理方式 (默认: auto)')
    
    # 其他选项
    parser.add_argument('--exclude', help='排除关键词列表，用逗号分隔多个关键词')
    parser.add_argument('--preview', '-p', action='store_true', help='预览模式，不实际执行操作')
    
    args = parser.parse_args()
    
    # 处理解散模式参数
    nested_mode = args.nested or args.all
    media_mode = args.media or args.all
    
    # 至少选择一种模式
    if not (args.direct or nested_mode or media_mode):
        logger.info("提示：未指定任何解散操作，默认执行单媒体文件夹解散")
        media_mode = True
    
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
    total_dissolved_folders = 0
    total_dissolved_files = 0
    total_dissolved_dirs = 0
    total_flattened_nested = 0
    total_released_media = 0
    
    if args.direct:
        # 直接解散模式
        logger.info("\n>>> 执行直接解散文件夹操作...")
        for path in paths:
            logger.info(f"\n处理目录: {path}")
            success, files_count, dirs_count = dissolve_folder(
                path, 
                file_conflict=args.file_conflict,
                dir_conflict=args.dir_conflict,
                logger=logger,
                preview=args.preview
            )
            if success or args.preview:
                total_dissolved_folders += 1
                total_dissolved_files += files_count
                total_dissolved_dirs += dirs_count
    else:
        # 其他解散模式
        for path in paths:
            logger.info(f"\n处理目录: {path}")
            
            if media_mode:
                logger.info("\n>>> 解散单媒体文件夹...")
                count = release_single_media_folder(path, exclude_keywords, logger, args.preview)
                total_released_media += count
            
            if nested_mode:
                logger.info("\n>>> 解散嵌套的单一文件夹...")
                count = flatten_single_subfolder(path, exclude_keywords, logger)
                total_flattened_nested += count
    
    # 输出操作总结
    logger.info("\n解散操作总结:")
    mode_prefix = "将" if args.preview else "已"
    
    if args.direct:
        logger.info(f"- {mode_prefix}解散 {total_dissolved_folders} 个文件夹")
        logger.info(f"- {mode_prefix}移动 {total_dissolved_files} 个文件")
        logger.info(f"- {mode_prefix}移动 {total_dissolved_dirs} 个文件夹")
    else:
        if media_mode:
            logger.info(f"- {mode_prefix}解散 {total_released_media} 个单媒体文件夹")
        if nested_mode:
            logger.info(f"- {mode_prefix}解散 {total_flattened_nested} 个嵌套文件夹")
    
    if args.preview:
        logger.info("注意：这是预览模式，实际操作未执行")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        sys.exit(1)