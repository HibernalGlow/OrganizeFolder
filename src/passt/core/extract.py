from loguru import logger
import psutil
from pathlib import Path
from typing import List,Text, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
import time
import shutil
from .delete import SafeDeleter
import subprocess
from rich.tree import Tree
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
import json
from rich.console import Console
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
        self.safe_deleter = SafeDeleter()  # 添加安全删除器
    def load_passwords(self, config_path: str) -> List[str]:
        """从JSON配置文件加载密码列表
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            List[str]: 密码列表
        """
        try:
            config_file = Path(__file__).parent / config_path
            logger.debug(f"尝试加载密码配置文件: {config_file}")
            
            if not config_file.exists():
                logger.error(f"密码配置文件不存在: {config_file}")
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
                
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            passwords = config.get('passwords', [''])
            logger.info(f"成功加载密码配置文件，共 {len(passwords)} 个密码")
            
            # 详细显示密码信息（隐藏敏感部分）
            for i, pwd in enumerate(passwords):
                if not pwd:
                    logger.debug(f"密码 {i+1}: [空密码]")
                else:
                    masked_pwd = pwd[:3] + "*" * (len(pwd) - 3) if len(pwd) > 3 else pwd
                    logger.debug(f"密码 {i+1}: {masked_pwd} (长度: {len(pwd)})")
            
            return passwords
        except Exception as e:
            logger.error(f"加载密码配置失败: {e}，使用默认密码")
            default_passwords = ["uohsoaixgnaixgnawab","mayuyu123",""]
            logger.info(f"使用默认密码列表，共 {len(default_passwords)} 个密码")
            return default_passwords
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
        process = None
        try:
            # 构建7z命令
            cmd = ['7z', 'x', str(archive_path), f'-o{extract_dir}', '-y']
            
            if password:
                cmd.append(f'-p{password}')
            logger.debug(f"执行命令: {' '.join(cmd)}")
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=300)  # 5分钟超时
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = stderr or stdout
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            # 超时时强制终止进程
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            return False, "解压超时"
        except Exception as e:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    pass
            return False, str(e)
        finally:
            # 确保进程已完全退出
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except:
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass
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
            if not Confirm.ask(f"目录 {extract_dir.name} 已存在，是否覆盖？", default=False):
                logger.info(f"跳过解压: {archive_path.name}")
                return False
            # 使用安全删除
            if not self.safe_deleter.safe_delete_folder(extract_dir):
                logger.error(f"无法删除现有目录: {extract_dir}")
                return False        
        extract_dir.mkdir(exist_ok=True)
        # 尝试所有密码
        for i, password in enumerate(self.passwords):
            if not password:
                password_display = f"无密码 (索引 {i+1})"
            else:
                password_display = f"密码 {i+1}: {password}" if len(password) > 3 else f"密码 {i+1}: {password}"
            
            logger.info(f"尝试解压 {archive_path.name} - {password_display}")
            
            success, error = self.try_extract_with_7z(archive_path, extract_dir, password)
            
            if success:
                logger.info(f"✅ 解压成功: {archive_path.name} ({password_display})")
                self.extracted_archives.append((archive_path, extract_dir, archive_name))
                
                # 安全删除压缩包（如果启用sdel）
                if use_sdel:
                    if self.safe_deleter.safe_delete_file(archive_path, force_terminate=True):
                        logger.info(f"🗑️ 已安全删除压缩包: {archive_path.name}")
                    else:
                        logger.error(f"删除压缩包失败 {archive_path.name}")
                
                return True
            else:
                logger.debug(f"密码失败: {password_display} - {error}")
          # 所有密码都失败
        logger.error(f"❌ 解压失败: {archive_path.name} - 所有密码都无效")
        # 安全删除空目录
        if extract_dir.exists() and not any(extract_dir.iterdir()):
            self.safe_deleter.safe_delete_folder(extract_dir)
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
              # 安全删除空目录
            if self.safe_deleter.safe_delete_folder(extract_dir):
                logger.info(f"✅ 已解散文件夹: {extract_dir.name}")
                return True
            else:
                logger.error(f"删除文件夹失败: {extract_dir.name}")
                return False
            
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
        
        if not Confirm.ask(f"\n是否开始解压这 {len(archives)} 个压缩包？",default=True):
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

