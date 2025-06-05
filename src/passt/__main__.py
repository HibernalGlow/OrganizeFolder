#!/usr/bin/env python3
"""
压缩包批量解压工具 with 密码尝试和文件重命名

使用rich交互式输入，支持7z解压和文件重命名
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 导入Rich库
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table

from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
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
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="passt", console_output=True)


console = Console()

# 支持的压缩包格式
ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', 
    '.xz', '.tar.gz', '.tar.bz2', '.tar.xz',
    '.cbz', '.cbr'
}

class ArchiveExtractor:
    """压缩包解压器"""
    
    def __init__(self, passwords_config_path: str = "passwords.json"):
        """初始化解压器
        
        Args:
            passwords_config_path: 密码配置文件路径
        """
        self.passwords = self.load_passwords(passwords_config_path)
        self.console = Console()
        self.extracted_archives = []
        
    def load_passwords(self, config_path: str) -> List[str]:
        """从JSON配置文件加载密码列表
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            List[str]: 密码列表
        """
        try:
            config_file = Path(__file__).parent / config_path
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            passwords = config.get('passwords', [''])
            logger.info(f"已加载 {len(passwords)} 个密码")
            return passwords
        except Exception as e:
            logger.warning(f"加载密码配置失败: {e}，使用默认密码")
            return ['', '123456', 'password', '123']
    
    def find_archives(self, search_path: Path) -> List[Path]:
        """查找指定路径下的所有压缩包
        
        Args:
            search_path: 搜索路径
            
        Returns:
            List[Path]: 压缩包文件列表
        """
        archives = []
        
        if search_path.is_file():
            # 如果是单个文件，检查是否为压缩包
            if search_path.suffix.lower() in ARCHIVE_EXTENSIONS:
                archives.append(search_path)
        elif search_path.is_dir():
            # 如果是目录，递归查找所有压缩包
            for ext in ARCHIVE_EXTENSIONS:
                archives.extend(search_path.rglob(f'*{ext}'))
        
        logger.info(f"找到 {len(archives)} 个压缩包")
        return sorted(archives)
    
    def try_extract_with_7z(self, archive_path: Path, extract_dir: Path, password: str = "") -> Tuple[bool, str]:
        """使用7z尝试解压文件
        
        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目录
            password: 密码
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            # 构建7z命令
            cmd = ['7z', 'x', str(archive_path), f'-o{extract_dir}', '-y']
            
            if password:
                cmd.append(f'-p{password}')
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                return True, ""
            else:
                error_msg = result.stderr or result.stdout
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "解压超时"
        except Exception as e:
            return False, str(e)
    def extract_archive(self, archive_path: Path, use_sdel: bool = True, dissolve_folder: bool = True) -> bool:
        """解压单个压缩包，尝试所有密码
        
        Args:
            archive_path: 压缩包路径
            use_sdel: 是否在解压成功后删除压缩包
            dissolve_folder: 是否在重命名后解散文件夹
            
        Returns:
            bool: 是否解压成功
        """
        archive_name = archive_path.stem  # 不包含扩展名的文件名
        extract_dir = archive_path.parent / archive_name
        
        # 如果目录已存在，询问是否覆盖
        if extract_dir.exists():
            if not Confirm.ask(f"目录 {extract_dir.name} 已存在，是否覆盖？"):
                logger.info(f"跳过解压: {archive_path.name}")
                return False
            shutil.rmtree(extract_dir)
        
        extract_dir.mkdir(exist_ok=True)
          # 尝试所有密码
        for i, password in enumerate(self.passwords):
            password_display = "无密码" if not password else f"密码 {i+1}"
            logger.info(f"尝试解压 {archive_path.name} - {password_display}")
            
            success, error = self.try_extract_with_7z(archive_path, extract_dir, password)
            
            if success:
                logger.info(f"✅ 解压成功: {archive_path.name} ({password_display})")
                self.extracted_archives.append((archive_path, extract_dir, archive_name))
                
                # 删除压缩包（如果启用sdel）
                if use_sdel:
                    try:
                        archive_path.unlink()
                        logger.info(f"🗑️ 已删除压缩包: {archive_path.name}")
                    except Exception as e:
                        logger.error(f"删除压缩包失败 {archive_path.name}: {e}")
                
                return True
            else:
                logger.debug(f"密码失败: {password_display} - {error}")
          # 所有密码都失败
        logger.error(f"❌ 解压失败: {archive_path.name} - 所有密码都无效")
        # 删除空目录
        if extract_dir.exists() and not any(extract_dir.iterdir()):
            extract_dir.rmdir()
        return False
    
    def dissolve_folder(self, extract_dir: Path) -> bool:
        """解散文件夹，将所有文件移动到父目录
        
        Args:
            extract_dir: 要解散的目录
            
        Returns:
            bool: 是否成功解散
        """
        try:
            parent_dir = extract_dir.parent
            items = list(extract_dir.iterdir())
            
            # 移动所有文件和文件夹到父目录
            for item in items:
                target_path = parent_dir / item.name
                
                # 处理重名情况
                counter = 1
                while target_path.exists():
                    if item.is_dir():
                        target_path = parent_dir / f"{item.name}_{counter}"
                    else:
                        stem = item.stem
                        suffix = item.suffix
                        target_path = parent_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                shutil.move(str(item), str(target_path))
                logger.debug(f"移动: {item.name} -> {target_path.name}")
            
            # 删除空目录
            extract_dir.rmdir()
            logger.info(f"✅ 已解散文件夹: {extract_dir.name}")
            return True
            
        except Exception as e:
            logger.error(f"解散文件夹失败 {extract_dir.name}: {e}")
            return False
    
    def rename_extracted_files(self, extract_dir: Path, prefix: str) -> int:
        """为解压出的文件和文件夹添加前缀
        
        Args:
            extract_dir: 解压目录
            prefix: 前缀
            
        Returns:
            int: 重命名的文件数量
        """
        renamed_count = 0
        
        try:
            # 获取所有直接子项（文件和文件夹）
            items = list(extract_dir.iterdir())
            
            for item in items:
                old_name = item.name
                new_name = f"{prefix}@{old_name}"
                new_path = item.parent / new_name
                
                # 避免重名
                counter = 1
                while new_path.exists():
                    new_name = f"{prefix}@{old_name}_{counter}"
                    new_path = item.parent / new_name
                    counter += 1
                
                try:
                    item.rename(new_path)
                    logger.debug(f"重命名: {old_name} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    logger.error(f"重命名失败 {old_name}: {e}")
                    
        except Exception as e:
            logger.error(f"遍历目录失败 {extract_dir}: {e}")
        
        return renamed_count
    def process_archives(self, archives: List[Path], use_sdel: bool = True, dissolve_folder: bool = True) -> None:
        """批量处理压缩包
        
        Args:
            archives: 压缩包列表
            use_sdel: 是否在解压成功后删除压缩包
            dissolve_folder: 是否在重命名后解散文件夹
        """
        if not archives:
            console.print("[yellow]没有找到压缩包文件[/yellow]")
            return
        
        # 显示找到的压缩包
        console.print(f"\n[cyan]找到 {len(archives)} 个压缩包:[/cyan]")
        for i, archive in enumerate(archives[:10], 1):  # 只显示前10个
            console.print(f"  {i}. {archive.name}")
        if len(archives) > 10:
            console.print(f"  ... 还有 {len(archives) - 10} 个文件")
        
        if not Confirm.ask(f"\n是否开始解压这 {len(archives)} 个压缩包？"):
            console.print("[yellow]用户取消操作[/yellow]")
            return
        
        # 进度条处理
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("解压压缩包...", total=len(archives))
            
            success_count = 0
            total_renamed = 0
            for archive in archives:
                progress.update(task, description=f"解压: {archive.name}")
                
                if self.extract_archive(archive, use_sdel, dissolve_folder):
                    success_count += 1
                    # 找到对应的解压记录并重命名文件
                    for arch_path, extract_dir, arch_name in self.extracted_archives:
                        if arch_path == archive:
                            renamed = self.rename_extracted_files(extract_dir, arch_name)
                            total_renamed += renamed
                            
                            # 如果启用dissolve_folder，解散文件夹
                            if dissolve_folder:
                                self.dissolve_folder(extract_dir)
                            break
                
                progress.advance(task)
        
        # 显示结果
        result_table = Table(title="解压结果")
        result_table.add_column("项目", style="cyan")
        result_table.add_column("数量", style="green")
        
        result_table.add_row("总压缩包", str(len(archives)))
        result_table.add_row("解压成功", str(success_count))
        result_table.add_row("解压失败", str(len(archives) - success_count))
        result_table.add_row("重命名文件", str(total_renamed))
        
        console.print("\n")
        console.print(result_table)


def get_user_options() -> Tuple[bool, bool]:
    """获取用户的解压选项
    
    Returns:
        Tuple[bool, bool]: (use_sdel, dissolve_folder)
    """
    console.print("\n[cyan]解压选项配置:[/cyan]")
    
    # 询问是否使用sdel（删除原压缩包）
    use_sdel = Confirm.ask(
        "是否在解压成功后删除原压缩包 (sdel)?",
        default=True
    )
    
    # 询问是否解散文件夹
    dissolve_folder = Confirm.ask(
        "是否在重命名后解散压缩包文件夹（将内容移到父目录）?",
        default=True
    )
    
    return use_sdel, dissolve_folder


def get_user_input() -> Optional[Path]:
    """获取用户输入的路径
    
    Returns:
        Optional[Path]: 用户选择的路径，如果取消则返回None
    """
    console.print(Panel.fit(
        "[bold blue]压缩包批量解压工具[/bold blue]\n"
        "支持密码尝试和文件重命名功能\n"
        "支持格式: ZIP, RAR, 7Z, TAR, CBZ, CBR 等",
        title="🗜️ 压缩包解压器"
    ))
    
    while True:
        path_input = Prompt.ask(
            "\n请输入要处理的文件夹或文件路径",
            default="."
        )
        
        if not path_input.strip():
            if not Confirm.ask("输入为空，是否退出？"):
                continue
            return None
        
        path = Path(path_input.strip()).resolve()
        
        if not path.exists():
            console.print(f"[red]路径不存在: {path}[/red]")
            continue
        
        console.print(f"[green]选择的路径: {path}[/green]")
        
        if path.is_file():
            if path.suffix.lower() not in ARCHIVE_EXTENSIONS:
                console.print(f"[yellow]警告: {path.name} 不是支持的压缩包格式[/yellow]")
        
        if Confirm.ask("确认使用此路径？"):
            return path


def main():
    """主函数"""
    try:
        # 检查7z是否可用
        try:
            subprocess.run(['7z'], capture_output=True, check=False)
        except FileNotFoundError:
            console.print("[red]错误: 未找到 7z 命令，请确保已安装 7-Zip[/red]")
            return 1
        
        # 获取用户输入
        target_path = get_user_input()
        if target_path is None:
            console.print("[yellow]用户取消操作[/yellow]")
            return 0
        
        # 初始化解压器
        extractor = ArchiveExtractor()
        
        # 查找压缩包
        console.print(f"\n[cyan]正在扫描路径: {target_path}[/cyan]")
        archives = extractor.find_archives(target_path)
        
        # 处理压缩包
        extractor.process_archives(archives)
        
        logger.info("解压任务完成")
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
        return 1
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        console.print(f"[red]程序执行出错: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
