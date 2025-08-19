"""
嵌套文件夹解散模块

提供解散嵌套单一文件夹的功能
"""

import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.status import Status
from loguru import logger

console = Console()

def flatten_single_subfolder(path, exclude_keywords=None):
    """
    如果一个文件夹下只有一个文件夹，就将该文件夹的子文件夹释放掉，将其中的文件和文件夹移动到母文件夹

    参数:
    path (str/Path): 目标路径
    exclude_keywords (list): 排除关键词列表
    
    返回:
    int: 处理的文件夹数量
    """    # 初始化参数
    if exclude_keywords is None:
        exclude_keywords = []
    
    # 转换路径为Path对象
    if isinstance(path, str):
        path = Path(path)
      # 计数器
    processed_count = 0
    # 创建一个Rich状态指示器
    status = Status("正在扫描文件夹结构...", spinner="dots")
    status_started = False
    
    # 启动状态指示器
    status.start()
    status_started = True
    
    try:
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            
            # 检查当前路径是否包含排除关键词
            if any(keyword in str(root) for keyword in exclude_keywords):
                continue
              # 更新状态
            status.update(f"检查文件夹: {root_path.name}")
            # logger.info(f"检查文件夹: {root}")
            
            # 如果当前文件夹只有一个子文件夹且没有文件
            if len(dirs) == 1 and not files:
                subfolder_path = root_path / dirs[0]
                try:
                    while True:  # 处理嵌套的单文件夹
                        # 检查子文件夹中是否只有一个文件夹且没有文件
                        sub_items = list(subfolder_path.iterdir())
                        sub_dirs = [item for item in sub_items if item.is_dir()]
                        sub_files = [item for item in sub_items if item.is_file()]
                        
                        if len(sub_dirs) == 1 and not sub_files:
                            # 更新子文件夹路径到更深一层
                            subfolder_path = sub_dirs[0]
                            continue
                        break  # 如果不是单文件夹，退出循环
                    
                    # 移动最深层子文件夹中的所有内容到母文件夹
                    for item in subfolder_path.iterdir():
                        src_item_path = item
                        dst_item_path = root_path / item.name
                        
                        # 处理名称冲突
                        if dst_item_path.exists():
                            counter = 1
                            while dst_item_path.exists():
                                new_name = f"{item.stem}_{counter}{item.suffix}" if item.suffix else f"{item.name}_{counter}"
                                dst_item_path = root_path / new_name
                                counter += 1
                          # 移动文件
                        try:
                            shutil.move(str(src_item_path), str(dst_item_path))
                            # logger.info(f"已移动: {src_item_path} -> {dst_item_path}")
                            
                        except Exception as e:
                            logger.error(f"移动失败: {src_item_path} - {e}")
                            console.print(f"[red]移动失败[/red]: {src_item_path} - {e}")
                    
                    # 获取原始子文件夹的路径以便打印
                    original_subfolder = root_path / dirs[0]
                    
                    # 检查是否成功移动了所有内容
                    if not any(subfolder_path.iterdir()):                        # 删除空的子文件夹
                        try:
                            shutil.rmtree(str(subfolder_path))
                            processed_count += 1
                            
                            # logger.info(f"已解散嵌套文件夹: {original_subfolder}")
                            console.print(f"已解散嵌套文件夹: [cyan]{original_subfolder}[/cyan]")
                            
                        except Exception as e:
                            logger.error(f"删除文件夹失败: {subfolder_path} - {e}")
                            console.print(f"[red]删除文件夹失败[/red]: {subfolder_path} - {e}")
                    else:
                        # logger.info(f"文件夹不为空，无法删除: {subfolder_path}")
                        pass
                except Exception as e:                    
                    logger.error(f"处理文件夹失败: {root} - {e}")          # 打印处理结果
        if status_started:
            status.stop()
        logger.info(f"解散嵌套文件夹操作完成，共处理了 {processed_count} 个文件夹")
        
        return processed_count
    except Exception as e:
        logger.error(f"解散嵌套文件夹出错: {e}")
        if status_started:
            status.stop()
        console.print(f"[red]解散嵌套文件夹出错[/red]: {e}")
        return processed_count
    finally:
        # 确保状态指示器被停止
        if status_started:
            try:
                status.stop()
            except:
                pass

# 直接运行此文件时的入口点
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='解散嵌套的单一文件夹')
    parser.add_argument('path', type=str, help='要处理的路径')
    parser.add_argument('--exclude', type=str, help='排除关键词，用逗号分隔')
    
    args = parser.parse_args()
    
    # 处理排除关键词
    exclude_keywords = []
    if args.exclude:
        exclude_keywords = [keyword.strip() for keyword in args.exclude.split(',')]
    
    # 转换路径
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]错误：路径不存在[/red] - {path}")
        exit(1)
    
    console.print(f"开始处理路径: [cyan]{path}[/cyan]")
    count = flatten_single_subfolder(path, exclude_keywords)
    console.print(f"处理完成，共解散了 [green]{count}[/green] 个嵌套文件夹")