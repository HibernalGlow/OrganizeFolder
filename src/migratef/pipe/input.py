"""
输入处理模块 - 处理各种输入源的文件路径获取
"""
import sys
from pathlib import Path
from typing import List
from rich.console import Console
from rich.prompt import Prompt
import pyperclip
from loguru import logger

"""
输入处理模块 - 处理各种输入源的文件路径获取
"""
import sys
from pathlib import Path
from typing import List
from rich.console import Console
from rich.prompt import Prompt
import pyperclip
from loguru import logger

console = Console()

# 全局变量存储管道输入，避免重复读取
_stdin_files = None
_stdin_read = False

def read_paths_from_stdin() -> List[str]:
    """从标准输入读取文件路径列表"""
    paths = []
    try:
        # 检查是否有标准输入数据
        if sys.stdin.isatty():
            return paths  # 没有管道输入
        
        logger.info("检测到管道输入，正在读取文件路径...")
        
        # 一次性读取所有标准输入内容
        stdin_content = sys.stdin.read()
        if not stdin_content.strip():
            logger.info("标准输入为空")
            return paths
        
        # 按行分割处理
        for line in stdin_content.strip().split('\n'):
            line = line.strip()
            if line:
                # 移除可能的引号
                path = line.strip('"\'')
                # 验证路径
                p = Path(path)
                if p.exists() and p.is_file():
                    paths.append(path)
                    logger.debug(f"从管道添加文件: {path}")
                else:
                    logger.warning(f"跳过无效路径: {path}")
        
        logger.info(f"从管道读取到 {len(paths)} 个有效文件路径")
        
    except Exception as e:
        logger.error(f"从标准输入读取路径时出错: {e}")
    
    return paths


def get_stdin_files() -> List[str]:
    """获取标准输入文件列表，确保只读取一次"""
    global _stdin_files, _stdin_read
    
    if not _stdin_read:
        _stdin_files = read_paths_from_stdin()
        _stdin_read = True
    
    return _stdin_files or []
    """从标准输入读取文件路径列表"""
    paths = []
    try:
        # 检查是否有标准输入数据
        if sys.stdin.isatty():
            return paths  # 没有管道输入
        
        logger.info("检测到管道输入，正在读取文件路径...")
        
        # 读取所有标准输入
        for line in sys.stdin:
            line = line.strip()
            if line:
                # 移除可能的引号
                path = line.strip('"\'')
                # 验证路径
                p = Path(path)
                if p.exists() and p.is_file():
                    paths.append(path)
                    logger.debug(f"从管道添加文件: {path}")
                else:
                    logger.warning(f"跳过无效路径: {path}")
        
        logger.info(f"从管道读取到 {len(paths)} 个有效文件路径")
        
    except Exception as e:
        logger.error(f"从标准输入读取路径时出错: {e}")
    
    return paths


def get_source_files_interactively() -> List[str]:
    """交互式地获取源文件路径列表。"""
    source_files = []
    prompt_message = "[bold cyan]请输入要迁移的源文件路径（每个路径一行，输入 'c' 从剪贴板读取，输入 'done' 或直接按 Enter 结束）：[/bold cyan]"
    logger.info(prompt_message)
    
    while True:
        try:
            # 使用 Prompt.ask 获取输入，允许为空或 'done' 结束
            file_path_raw = Prompt.ask("  [dim]源文件路径[/dim]", default="done", show_default=False).strip()

            # --- 新增：处理剪贴板输入 ---
            if file_path_raw.lower() == 'c':
                try:
                    clipboard_content = pyperclip.paste()
                    if not clipboard_content:
                        logger.warning("剪贴板为空")
                        continue

                    paths_from_clipboard = [p.strip() for p in clipboard_content.splitlines() if p.strip()]
                    if not paths_from_clipboard:
                        logger.warning("剪贴板内容解析后没有有效的路径")
                        continue

                    added_count = 0
                    skipped_count = 0
                    error_count = 0
                    logger.info(f"正在处理剪贴板中的 {len(paths_from_clipboard)} 个路径...")

                    for path_str in paths_from_clipboard:
                        try:
                            # 清理路径字符串
                            path_str = path_str.strip(' "\'')
                            if not path_str:
                                continue

                            # 尝试创建 Path 对象
                            file_path = Path(path_str)

                            # 检查路径是否存在且为文件
                            if file_path.exists() and file_path.is_file():
                                source_files.append(str(file_path.resolve()))
                                added_count += 1
                                logger.debug(f"添加文件: {file_path}")
                            else:
                                logger.warning(f"跳过无效路径: {path_str}")
                                skipped_count += 1

                        except Exception as path_error:
                            logger.error(f"处理路径时出错 {path_str}: {path_error}")
                            error_count += 1

                    # 显示处理结果
                    logger.info(f"从剪贴板导入完成：添加 {added_count} 个文件，跳过 {skipped_count} 个无效路径，{error_count} 个错误")
                    
                    if added_count > 0:
                        logger.info(f"当前总共有 {len(source_files)} 个源文件")

                except Exception as e:
                    logger.error(f"处理剪贴板内容时出错: {e}")

                continue

            # 如果输入为 'done' 或为空，结束输入
            if file_path_raw.lower() == 'done' or not file_path_raw:
                break

            # 处理普通文件路径输入
            try:
                # 清理路径字符串，移除引号
                file_path_raw = file_path_raw.strip(' "\'')
                
                # 创建 Path 对象
                file_path = Path(file_path_raw)
                
                # 检查路径是否存在且为文件
                if file_path.exists() and file_path.is_file():
                    source_files.append(str(file_path.resolve()))
                    logger.info(f"添加文件: {file_path}")
                else:
                    logger.warning(f"路径不存在或不是文件: {file_path_raw}")
                    
            except Exception as e:
                logger.error(f"处理路径时出错: {e}")

        except KeyboardInterrupt:
            logger.info("用户中断输入")
            break
        except Exception as e:
            logger.error(f"输入时发生错误: {e}")

    logger.info(f"最终收集到 {len(source_files)} 个源文件")
    return source_files


def get_target_dir_interactively() -> str:
    """交互式地获取目标目录路径。"""
    while True:
        try:
            target_dir_raw = Prompt.ask("[bold cyan]请输入目标目录路径[/bold cyan]").strip()
            
            # 清理路径字符串，移除引号
            target_dir_raw = target_dir_raw.strip(' "\'')
            
            if not target_dir_raw:
                logger.warning("目标目录路径不能为空")
                continue
            
            # 创建 Path 对象
            target_dir = Path(target_dir_raw)
            
            # 检查目标目录是否存在，如果不存在则询问是否创建
            if not target_dir.exists():
                if Prompt.ask(f"目标目录 '{target_dir}' 不存在，是否创建？", choices=["y", "n"], default="y").lower() == "y":
                    try:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"已创建目标目录: {target_dir}")
                    except Exception as e:
                        logger.error(f"创建目录失败: {e}")
                        continue
                else:
                    continue
            elif not target_dir.is_dir():
                logger.error(f"路径 '{target_dir}' 不是目录")
                continue
            
            return str(target_dir.resolve())
            
        except KeyboardInterrupt:
            logger.info("用户中断输入")
            raise
        except Exception as e:
            logger.error(f"输入目标目录时发生错误: {e}")


def get_paths_from_clipboard() -> List[str]:
    """从剪贴板读取文件路径列表"""
    paths = []
    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content:
            logger.warning("剪贴板为空")
            return paths

        for line in clipboard_content.strip().split('\n'):
            line = line.strip()
            if line:
                # 移除可能的引号
                path = line.strip('"\'')
                # 验证路径
                p = Path(path)
                if p.exists() and p.is_file():
                    paths.append(path)
                    logger.debug(f"从剪贴板添加文件: {path}")
                else:
                    logger.warning(f"跳过无效路径: {path}")
        
        logger.info(f"从剪贴板读取到 {len(paths)} 个有效文件路径")
        
    except Exception as e:
        logger.error(f"从剪贴板读取路径时出错: {e}")
    
    return paths
