"""
单媒体文件夹解散模块

提供释放单个媒体文件夹的功能，将文件夹中唯一的媒体文件（视频或压缩包）移动到上级目录
"""

import os
import shutil
from pathlib import Path
from rich.console import Console
import rich.status
from loguru import logger

console = Console()

# 支持的视频格式
VIDEO_FORMATS = {'.mp4','.nov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mov', '.m4v', '.mpg', '.mpeg', '.3gp', '.rmvb'}

# 支持的压缩包格式
ARCHIVE_FORMATS = {'.zip', '.rar', '.7z', '.cbz', '.cbr'}

def is_video_file(filename):
    """判断文件是否为视频文件"""
    return any(str(filename).lower().endswith(ext) for ext in VIDEO_FORMATS)

def is_archive_file(filename):
    """判断文件是否为压缩包文件"""
    return any(str(filename).lower().endswith(ext) for ext in ARCHIVE_FORMATS)

def release_single_media_folder(path, exclude_keywords=None, preview=False):
    """
    如果文件夹中只有一个视频文件或压缩包文件，将其释放到上层目录

    参数:
    path (str/Path): 目标路径
    exclude_keywords (list): 排除关键词列表
    preview (bool): 如果为True，只预览操作不实际执行
    
    返回:
    int: 处理的文件夹数量
    """
    # 初始化参数
    if exclude_keywords is None:
        exclude_keywords = []
        
    # 转换路径为Path对象
    if isinstance(path, str):
        path = Path(path)
          # 检查路径是否存在
    if not path.exists():
        logger.error(f"路径不存在: {path}")
        console.print(f"[red]错误:[/red] 路径不存在 - {path}")
        return 0
          # 计数器
    processed_count = 0
    # 创建一个Rich状态指示器
    status = rich.status.Status("正在扫描媒体文件夹...", spinner="dots")
    status_started = False
    if not preview:
        status.start()
        status_started = True
    
    if preview:
        console.print(f"[bold cyan]预览模式:[/bold cyan] 不会实际移动文件")
      # 记录开始处理
    message = f"{'预览' if preview else '开始处理'}单媒体文件夹: {path}"
    console.print(message)
    try:
        # 初始化结果消息，确保在任何路径都能访问到
        result_message = ""
        
        for root, dirs, files in os.walk(path, topdown=False):
            root_path = Path(root)
              # 检查当前路径是否包含排除关键词
            if any(keyword in str(root_path) for keyword in exclude_keywords):
                logger.info(f"跳过含有排除关键词的文件夹: {root}")
                continue
              # 更新状态
            if not preview:
                status.update(f"检查文件夹: {root_path.name}")
            # logger.info(f"检查文件夹: {root}")
            
            try:
                # 获取文件夹中的所有项目
                items = list(root_path.iterdir())
                
                # 分别统计文件和文件夹                files = [item for item in items if item.is_file()]
                dirs = [item for item in items if item.is_dir()]
                
                # logger.info(f"- 包含 {len(dirs)} 个子文件夹")
                # logger.info(f"- 包含 {len(files)} 个文件")
                
                # 过滤出视频文件和压缩包文件
                # 确保处理的是Path对象，避免字符串没有name属性的错误
                media_files = []
                for f in files:
                    try:
                        if isinstance(f, str):
                            f = Path(f)
                        if is_video_file(f.name) or is_archive_file(f.name):
                            media_files.append(f)
                    except Exception as e:
                        logger.warning(f"处理文件时出错: {f}, 错误: {str(e)}")
                        continue
                
                # 如果文件夹中只有一个媒体文件且没有其他文件和文件夹
                if len(media_files) == 1 and len(files) == 1 and len(dirs) == 0:
                    media_file = media_files[0]
                    media_type = "视频" if is_video_file(media_file.name) else "压缩包"
                    
                    console.print(f"\n找到符合条件的文件夹: [cyan]{root}[/cyan]")
                    console.print(f"- 单个{media_type}文件: [green]{media_file.name}[/green]")
                    
                    parent_dir = root_path.parent
                    target_path = parent_dir / media_file.name
                    
                    # 如果目标路径已存在，添加数字后缀
                    if target_path.exists():
                        counter = 1                        
                        while target_path.exists():
                            new_name = f"{media_file.stem}_{counter}{media_file.suffix}"
                            target_path = parent_dir / new_name
                            counter += 1
                            
                            logger.info(f"- 目标文件已存在，尝试新名称: {new_name}")
                      # 显示将要执行的操作
                    logger.info(f"- {'将' if preview else ''}移动文件: {media_file} -> {target_path}")
                    console.print(f"- {'将' if preview else ''}移动文件: [blue]{media_file.name}[/blue] -> [green]{target_path}[/green]")
                    
                    # 如果不是预览模式，实际执行移动
                    if not preview:
                        try:
                            # 移动文件到上层目录
                            shutil.move(str(media_file), str(target_path))
                            
                            # 删除空文件夹
                            os.rmdir(str(root_path))
                            processed_count += 1
                            
                            logger.info("- 文件移动成功")
                            logger.info("- 文件夹删除成功")
                            console.print("- [green]文件移动成功[/green]")
                            console.print("- [green]文件夹删除成功[/green]")
                                
                        except Exception as e:
                            logger.error(f"处理文件夹时出错 {root}:")
                            logger.error(f"错误信息: {str(e)}")
                            console.print(f"[red]处理文件夹时出错[/red] {root}:")
                            console.print(f"错误信息: {str(e)}")
                    else:
                        # 预览模式下，只计数不实际执行
                        processed_count += 1
                    if len(media_files) > 0 and preview:
                        logger.info(f"不符合处理条件: {root}")
                        logger.info(f"- 媒体文件数: {len(media_files)} (需要为1)")
                        logger.info(f"- 总文件数: {len(files)} (需要为1)")
                        logger.info(f"- 子文件夹数: {len(dirs)} (需要为0)")
                        console.print(f"[yellow]不符合处理条件[/yellow]: {root}")
                        console.print(f"- 媒体文件数: {len(media_files)} (需要为1)")
                        console.print(f"- 总文件数: {len(files)} (需要为1)")
                        console.print(f"- 子文件夹数: {len(dirs)} (需要为0)")
            except Exception as e:
                logger.error(f"处理文件夹时出错 {root}:")
                logger.error(f"错误信息: {str(e)}")
                console.print(f"[red]处理文件夹时出错[/red] {root}:")
                console.print(f"错误信息: {str(e)}")
          # 打印处理结果
        result_message = f"单媒体文件夹{'预览' if preview else '处理'}完成，共{'发现' if preview else '处理了'} {processed_count} 个文件夹"
        if processed_count == 0:
            result_message += " (没有找到符合条件的文件夹)"
            
        logger.info(result_message)
        if status_started:
            status.stop()
        console.print(f"\n{result_message}")
        
        return processed_count
    except Exception as e:
        logger.error(f"解散单媒体文件夹出错: {e}")
        if status_started:
            status.stop()
        console.print(f"[red]解散单媒体文件夹出错[/red]: {e}")
        return processed_count
    finally:
        # 确保状态指示器被停止
        if not preview and status_started:
            try:
                status.stop()
            except:
                pass

# 直接运行此文件时的入口点
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='解散单媒体文件夹')
    parser.add_argument('path', type=str, help='要处理的路径')
    parser.add_argument('--exclude', type=str, help='排除关键词，用逗号分隔')
    parser.add_argument('--preview', '-p', action='store_true', help='预览模式，不实际执行操作')
    
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
    count = release_single_media_folder(path, exclude_keywords, preview=args.preview)
    
    mode_text = "预览找到" if args.preview else "成功处理"
    console.print(f"处理完成，共{mode_text} [green]{count}[/green] 个单媒体文件夹")