"""
嵌套文件夹解散模块

提供解散嵌套单一文件夹的功能，支持相似度检测和撤销
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
import rich.status
from loguru import logger

from .similarity import check_similarity
from .undo import undo_manager

console = Console()


def flatten_single_subfolder(
    path,
    exclude_keywords: Optional[List[str]] = None,
    preview: bool = False,
    similarity_threshold: float = 0.0,
    protect_first_level: bool = True,
    enable_undo: bool = True,
    on_log: Optional[callable] = None
) -> Tuple[int, int]:
    """
    如果一个文件夹下只有一个文件夹，就将该文件夹的子文件夹释放掉，将其中的文件和文件夹移动到母文件夹

    参数:
        path (str/Path): 目标路径
        exclude_keywords (list): 排除关键词列表
        preview (bool): 如果为 True，只预览操作不实际执行
        similarity_threshold (float): 相似度阈值 (0.0-1.0)，0 表示不检测
        protect_first_level (bool): 是否保护输入路径下一级文件夹
        enable_undo (bool): 是否启用撤销记录
        on_log (callable): 日志回调函数，接收字符串参数
    
    返回:
        Tuple[int, int]: (处理的文件夹数量, 因相似度不足跳过的数量)
    """
    
    def _log(msg: str):
        """输出日志到控制台和回调"""
        console.print(msg)
        if on_log:
            # 移除 rich 标记
            import re
            clean_msg = re.sub(r'\[/?[^\]]+\]', '', msg)
            on_log(clean_msg)
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    if isinstance(path, str):
        path = Path(path)
    
    processed_count = 0
    skipped_count = 0
    
    # 创建状态指示器
    status = rich.status.Status("正在扫描文件夹结构...", spinner="dots")
    status_started = False
    
    if not preview:
        status.start()
        status_started = True
        # 开始撤销批次
        if enable_undo:
            undo_manager.start_batch('nested', str(path))
    
    if preview:
        _log(f"[bold cyan]预览模式:[/bold cyan] 不会实际移动文件")
    
    try:
        for root, dirs, files in os.walk(path):
            root_path = Path(root)

            # 保护输入路径下一级目录：不直接解散这些目录
            if protect_first_level and root_path != path and root_path.parent == path:
                continue
            
            # 检查当前路径是否包含排除关键词
            if any(keyword in str(root) for keyword in exclude_keywords):
                continue
            
            # 更新状态
            if status_started:
                status.update(f"检查文件夹: {root_path.name}")
            
            # 如果当前文件夹只有一个子文件夹且没有文件
            if len(dirs) == 1 and not files:
                subfolder_name = dirs[0]
                subfolder_path = root_path / subfolder_name
                parent_name = root_path.name
                
                # 相似度检测
                if similarity_threshold > 0:
                    passed, similarity = check_similarity(parent_name, subfolder_name, similarity_threshold)
                    if not passed:
                        skipped_count += 1
                        _log(f"  [yellow]跳过[/yellow]: [cyan]{parent_name}[/cyan]/[yellow]{subfolder_name}[/yellow] (相似度 {similarity:.0%} < {similarity_threshold:.0%})")
                        continue
                    else:
                        _log(f"  [green]匹配[/green]: [cyan]{parent_name}[/cyan]/[green]{subfolder_name}[/green] (相似度 {similarity:.0%})")
                
                try:
                    # 找到最深层的单一子文件夹
                    current_subfolder = subfolder_path
                    while True:
                        sub_items = list(current_subfolder.iterdir())
                        sub_dirs = [item for item in sub_items if item.is_dir()]
                        sub_files = [item for item in sub_items if item.is_file()]
                        
                        if len(sub_dirs) == 1 and not sub_files:
                            current_subfolder = sub_dirs[0]
                            continue
                        break
                    
                    # 移动最深层子文件夹中的所有内容到母文件夹
                    for item in current_subfolder.iterdir():
                        src_item_path = item
                        dst_item_path = root_path / item.name
                        
                        # 处理名称冲突
                        if dst_item_path.exists():
                            counter = 1
                            while dst_item_path.exists():
                                new_name = f"{item.stem}_{counter}{item.suffix}" if item.suffix else f"{item.name}_{counter}"
                                dst_item_path = root_path / new_name
                                counter += 1
                        
                        if not preview:
                            try:
                                shutil.move(str(src_item_path), str(dst_item_path))
                                # 记录撤销操作
                                if enable_undo:
                                    undo_manager.record_move(src_item_path, dst_item_path)
                            except Exception as e:
                                logger.error(f"移动失败: {src_item_path} - {e}")
                                _log(f"[red]移动失败[/red]: {src_item_path} - {e}")
                    
                    # 获取原始子文件夹的路径
                    original_subfolder = root_path / dirs[0]
                    
                    # 检查是否成功移动了所有内容
                    if not preview and not any(current_subfolder.iterdir()):
                        try:
                            shutil.rmtree(str(subfolder_path))
                            # 记录删除目录操作
                            if enable_undo:
                                undo_manager.record_delete_dir(subfolder_path)
                            processed_count += 1
                            _log(f"已解散嵌套文件夹: [cyan]{original_subfolder}[/cyan]")
                        except Exception as e:
                            logger.error(f"删除文件夹失败: {subfolder_path} - {e}")
                            _log(f"[red]删除文件夹失败[/red]: {subfolder_path} - {e}")
                    elif preview:
                        processed_count += 1
                        _log(f"将解散嵌套文件夹: [cyan]{original_subfolder}[/cyan]")
                        
                except Exception as e:
                    logger.error(f"处理文件夹失败: {root} - {e}")
        
        # 完成撤销批次
        if not preview and enable_undo:
            operation_id = undo_manager.finish_batch()
            if operation_id:
                _log(f"🔄 撤销 ID: [green]{operation_id}[/green]")
        
        if status_started:
            status.stop()
        
        result_msg = f"解散嵌套文件夹{'预览' if preview else '操作'}完成，共{'发现' if preview else '处理了'} {processed_count} 个文件夹"
        if skipped_count > 0:
            result_msg += f"，跳过 {skipped_count} 个（相似度不足）"
        logger.info(result_msg)
        _log(f"\n{result_msg}")
        
        return processed_count, skipped_count
        
    except Exception as e:
        logger.error(f"解散嵌套文件夹出错: {e}")
        if status_started:
            status.stop()
        _log(f"[red]解散嵌套文件夹出错[/red]: {e}")
        return processed_count, skipped_count
    finally:
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
    parser.add_argument('--preview', '-p', action='store_true', help='预览模式')
    parser.add_argument('--similarity', '-s', type=float, default=0.0, help='相似度阈值 (0.0-1.0)')
    
    args = parser.parse_args()
    
    exclude_keywords = []
    if args.exclude:
        exclude_keywords = [keyword.strip() for keyword in args.exclude.split(',')]
    
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]错误：路径不存在[/red] - {path}")
        exit(1)
    
    console.print(f"开始处理路径: [cyan]{path}[/cyan]")
    count, skipped = flatten_single_subfolder(
        path, exclude_keywords, 
        preview=args.preview,
        similarity_threshold=args.similarity
    )
    console.print(f"处理完成，共解散了 [green]{count}[/green] 个嵌套文件夹，跳过 [yellow]{skipped}[/yellow] 个")
