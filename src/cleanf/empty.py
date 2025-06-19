"""
空文件夹清理模块
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger

def scan_empty_folders(path, exclude_keywords=None) -> List[Path]:
    """
    扫描指定路径下的所有空文件夹，但不删除
    
    参数:
    path (str/Path): 目标路径
    exclude_keywords (list, 可选): 排除关键词列表
    
    返回:
    List[Path]: 要删除的空文件夹路径列表
    """
    path = Path(path) if isinstance(path, str) else path
    exclude_keywords = exclude_keywords or []
    empty_folders = []
    
    # 确保路径存在
    if not path.exists():
        return empty_folders
    
    # 由底向上遍历查找空文件夹
    for root, dirs, files in os.walk(path, topdown=False):
        # 检查当前路径是否包含排除关键词
        if any(keyword in root for keyword in exclude_keywords):
            continue

        # 检查每个子文件夹
        for dir_name in dirs:
            folder_path = Path(root) / dir_name
            try:
                # 检查文件夹是否为空
                if folder_path.exists() and not any(folder_path.iterdir()):
                    empty_folders.append(folder_path)
            except (FileNotFoundError, PermissionError):
                continue
    
    return empty_folders

def remove_empty_folders(path, exclude_keywords=None, preview_mode=False) -> Tuple[int, int]:
    """
    删除指定路径下的所有空文件夹
    
    参数:
    path (str/Path): 目标路径
    exclude_keywords (list, 可选): 排除关键词列表
    preview_mode (bool, 可选): 是否为预览模式，如果是则只返回要删除的文件列表
    
    返回:
    tuple: (已删除数量, 已跳过数量) 或 预览模式下返回 (要删除的文件列表, 0)
    """
    if preview_mode:
        empty_folders = scan_empty_folders(path, exclude_keywords)
        return empty_folders, 0
    
    path = Path(path) if isinstance(path, str) else path
    exclude_keywords = exclude_keywords or []
    removed_count = 0
    skipped_count = 0
    
    logger.info(f"\n开始删除空文件夹: {path}")
    
    # 确保路径存在
    if not path.exists():
        logger.info(f"路径不存在: {path}")
        return 0, 0
    
    # 由底向上遍历删除空文件夹
    for root, dirs, files in os.walk(path, topdown=False):
        # 检查当前路径是否包含排除关键词
        if any(keyword in root for keyword in exclude_keywords):
            skipped_count += 1
            logger.info(f"跳过含有排除关键词的文件夹: {root}")
            continue

        # 检查并删除每个子文件夹
        for dir_name in dirs:
            folder_path = os.path.join(root, dir_name)
            try:
                # 检查文件夹是否为空
                if os.path.exists(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
                    removed_count += 1
                    logger.info(f"已删除空文件夹: {folder_path}")
            except FileNotFoundError:
                logger.info(f"路径不存在: {folder_path}")
            except Exception as e:
                skipped_count += 1
                logger.info(f"删除文件夹失败: {folder_path} - {e}")
    
    # 最后输出汇总信息
    logger.info(f"空文件夹删除完成，共删除 {removed_count} 个空文件夹，跳过 {skipped_count} 个文件夹")
    
    return removed_count, skipped_count


if __name__ == "__main__":
    import argparse
    import sys
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='删除空文件夹')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('--exclude', help='排除关键词列表，用逗号分隔多个关键词')
    args = parser.parse_args()
    
    # 获取要处理的路径
    paths = []
    
    if args.clipboard:
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
                            print(f"警告：路径不存在 - {line}")
                
                print(f"从剪贴板读取到 {len(paths)} 个有效路径")
        except ImportError:
            print("警告：未安装pyperclip模块，无法从剪贴板读取。")
        except Exception as e:
            print(f"从剪贴板读取失败: {e}")
    
    if args.paths:
        for path_str in args.paths:
            path = Path(path_str.strip('"').strip("'"))
            if path.exists():
                paths.append(path)
            else:
                print(f"警告：路径不存在 - {path_str}")
    
    if not paths:
        print("请输入要处理的文件夹路径，每行一个，输入空行结束:")
        while True:
            if line := input().strip():
                path = Path(line.strip('"').strip("'"))
                if path.exists():
                    paths.append(path)
                else:
                    print(f"警告：路径不存在 - {line}")
            else:
                break
    
    if not paths:
        print("未提供任何有效的路径")
        sys.exit(1)
    
    # 处理排除关键词
    exclude_keywords = []
    if args.exclude:
        exclude_keywords.extend(args.exclude.split(','))
    
    # 处理每个路径
    total_removed = 0
    total_skipped = 0
    
    for path in paths:
        print(f"\n处理路径: {path}")
        removed, skipped = remove_empty_folders(path, exclude_keywords=exclude_keywords)
        total_removed += removed
        total_skipped += skipped
    
    print(f"\n删除完成，共删除 {total_removed} 个空文件夹，跳过 {total_skipped} 个文件夹")