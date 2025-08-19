"""
用户界面模块 - 负责与用户的交互
"""
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
from loguru import logger

from ..core.path_collector import PathCollector


class InteractiveUI:
    """交互式用户界面类"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.path_collector = PathCollector()
    
    def get_source_paths_interactively(self) -> List[str]:
        """交互式地获取源文件和文件夹路径列表"""
        prompt_message = "[bold cyan]请输入要迁移的源文件或文件夹路径（每个路径一行，输入 'c' 从剪贴板读取，输入 'done' 或直接按 Enter 结束）：[/bold cyan]"
        logger.info(prompt_message)
        
        while True:
            try:
                # 使用 Prompt.ask 获取输入，允许为空或 'done' 结束
                file_path_raw = Prompt.ask(
                    "  [dim]源路径（文件或文件夹）[/dim]", 
                    default="done", 
                    show_default=False
                ).strip()

                # 处理剪贴板输入
                if file_path_raw.lower() == 'c':
                    stats = self.path_collector.add_paths_from_clipboard()
                    continue  # 处理完剪贴板后，继续等待下一个输入

                if not file_path_raw or file_path_raw.lower() == 'done':
                    if self.path_collector.count() == 0:
                        logger.warning("警告：未输入任何源路径")
                        # 使用 Confirm.ask 确认是否继续
                        if not Confirm.ask("确定要继续吗（不迁移任何文件）？", default=False):
                            logger.error("操作已取消")
                            exit()
                        else:
                            break  # 确认继续，即使列表为空
                    else:
                        break  # 完成输入

                # 添加单个路径
                self.path_collector.add_path(file_path_raw)

            except KeyboardInterrupt:
                logger.error("操作已中断")
                exit()
            except Exception as e:
                logger.error(f"输入时发生错误: {e}")

        return self.path_collector.get_paths()
    
    def get_target_dir_interactively(self, default_path: str = "E:\\2EHV") -> str:
        """交互式获取目标目录"""
        target_dir = ""
        while not target_dir:
            target_dir = Prompt.ask(
                "[bold cyan]请输入目标根目录路径[/bold cyan]", 
                default=default_path
            ).strip()
            
            if not target_dir:
                logger.warning("目标目录不能为空，请重新输入")
            else:
                # 验证目标目录
                target_p = Path(target_dir)
                try:
                    # 尝试创建（如果不存在）或检查权限（如果存在）
                    target_p.mkdir(parents=True, exist_ok=True)
                    # 简单检查写权限
                    test_file = target_p / ".permission_test"
                    test_file.touch()
                    test_file.unlink()
                    break  # 验证通过
                except OSError as e:
                    logger.error(f"错误：无法访问或写入目标目录 '{target_dir}': {e}。请检查路径和权限")
                    target_dir = ""  # 清空以便重新输入
                except Exception as e:
                    logger.error(f"验证目标目录时发生意外错误: {e}")
                    target_dir = ""  # 清空以便重新输入
        return target_dir
    
    def get_migration_mode(self) -> str:
        """获取迁移模式选择"""
        self.console.print("[bold cyan]请选择迁移模式[/bold cyan]")
        self.console.print("  [bold blue]1[/bold blue] - preserve - 保持目录结构迁移")
        self.console.print("  [bold blue]2[/bold blue] - flat - 扁平迁移（只迁移文件，不保持目录结构）")
        self.console.print("  [bold blue]3[/bold blue] - direct - 直接迁移（类似mv命令，整个文件/文件夹作为单位）")
        
        migration_choice = Prompt.ask(
            "请输入选项编号",
            choices=["1", "2", "3"],
            default="1"
        )
        
        # 将数字选择转换为模式名称
        migration_modes = {"1": "preserve", "2": "flat", "3": "direct"}
        return migration_modes[migration_choice]
    
    def get_action_type(self) -> str:
        """获取操作类型选择"""
        action_choice = Prompt.ask(
            "[bold cyan]请选择操作类型 ([i]copy[/i]/[i]move[/i])[/bold cyan]",
            choices=["copy", "move"],
            default="move"
        ).lower()
        return action_choice
    
    def get_complete_migration_config(self) -> Tuple[List[str], str, str, str]:
        """获取完整的迁移配置
        
        Returns:
            Tuple[List[str], str, str, str]: (源路径列表, 目标目录, 迁移模式, 操作类型)
        """
        # 获取源路径
        source_paths = self.get_source_paths_interactively()
        if not source_paths:
            return [], "", "", ""
        
        # 获取目标目录
        target_dir = self.get_target_dir_interactively()
        
        # 获取迁移模式
        migration_mode = self.get_migration_mode()
        
        # 获取操作类型
        action_type = self.get_action_type()
        
        return source_paths, target_dir, migration_mode, action_type
