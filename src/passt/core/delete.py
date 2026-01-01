from loguru import logger
import psutil
from pathlib import Path
from typing import List
from rich.console import Console
from rich.prompt import Prompt, Confirm
import time
import shutil
import os
import sys


class SafeDeleter:
    """安全删除器，处理文件被占用的情况和Windows路径末尾空格问题"""
    
    def __init__(self, max_retries: int = 5, retry_delay: float = 1.0):
        """初始化安全删除器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _get_windows_long_path(self, path: Path) -> str:
        """获取Windows长路径格式，解决末尾空格问题
        
        使用 \\?\ 前缀强制Windows内核原样读取路径，不进行自动修剪
        
        Args:
            path: 原始路径
            
        Returns:
            str: Windows长路径格式的字符串
        """
        if sys.platform == "win32":
            abs_path = path.resolve()
            return f"\\\\?\\{abs_path}"
        return str(path.resolve())
    
    def find_file_processes(self, file_path: Path) -> List[psutil.Process]:
        """查找占用指定文件的进程
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[psutil.Process]: 占用文件的进程列表
        """
        processes = []
        file_path_str = str(file_path.resolve())
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    if proc.info['open_files']:
                        for file_info in proc.info['open_files']:
                            if file_info.path == file_path_str:
                                processes.append(proc)
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.debug(f"查找文件进程时出错: {e}")
        
        return processes
    
    def terminate_processes(self, processes: List[psutil.Process], force: bool = False) -> bool:
        """终止指定的进程
        
        Args:
            processes: 要终止的进程列表
            force: 是否强制终止
            
        Returns:
            bool: 是否成功终止所有进程
        """
        if not processes:
            return True
        
        success = True
        for proc in processes:
            try:
                proc_name = proc.name()
                proc_pid = proc.pid
                
                logger.info(f"尝试终止进程: {proc_name} (PID: {proc_pid})")
                
                if force:
                    proc.kill()
                    logger.info(f"强制终止进程: {proc_name} (PID: {proc_pid})")
                else:
                    proc.terminate()
                    logger.info(f"优雅终止进程: {proc_name} (PID: {proc_pid})")
                
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    if not force:
                        logger.warning(f"优雅终止超时，强制终止进程: {proc_name}")
                        proc.kill()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            logger.error(f"强制终止进程失败: {proc_name}")
                            success = False
                    else:
                        logger.error(f"强制终止进程失败: {proc_name}")
                        success = False
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.debug(f"进程已不存在或无权限: {e}")
            except Exception as e:
                logger.error(f"终止进程时出错: {e}")
                success = False
        
        return success
    
    def safe_delete_file(self, file_path: Path, force_terminate: bool = False) -> bool:
        """安全删除文件，支持Windows路径末尾空格处理
        
        Args:
            file_path: 要删除的文件路径
            force_terminate: 是否强制终止占用进程
            
        Returns:
            bool: 是否删除成功
        """
        if not file_path.exists():
            logger.debug(f"文件不存在，无需删除: {file_path}")
            return True
        
        for attempt in range(self.max_retries):
            try:
                file_path.unlink()
                logger.info(f"✅ 成功删除文件: {file_path.name}")
                return True
                
            except (PermissionError, OSError) as e:
                logger.warning(f"文件删除失败，尝试第 {attempt + 1}/{self.max_retries} 次: {file_path.name}")
                
                processes = self.find_file_processes(file_path)
                
                if processes:
                    logger.info(f"发现 {len(processes)} 个占用文件的进程")
                    for proc in processes:
                        try:
                            logger.info(f"占用进程: {proc.name()} (PID: {proc.pid})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    if attempt == 0 and not force_terminate:
                        if Confirm.ask(f"是否尝试关闭占用文件 {file_path.name} 的进程？", default=True):
                            force_terminate = True
                    
                    if force_terminate:
                        self.terminate_processes(processes, force=False)
                        time.sleep(1)
                        
                        remaining_processes = self.find_file_processes(file_path)
                        if remaining_processes:
                            logger.warning("仍有进程占用文件，尝试强制终止")
                            self.terminate_processes(remaining_processes, force=True)
                            time.sleep(1)
                else:
                    logger.debug("未发现占用进程，尝试使用Windows长路径格式")
                    if sys.platform == "win32":
                        try:
                            long_path = self._get_windows_long_path(file_path)
                            os.unlink(long_path)
                            logger.info(f"✅ 使用长路径格式成功删除文件: {file_path.name}")
                            return True
                        except Exception as long_path_error:
                            logger.debug(f"长路径删除也失败: {long_path_error}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"删除文件时出错: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"❌ 删除文件失败: {file_path.name}")
        return False
    
    def safe_delete_folder(self, folder_path: Path, force_terminate: bool = False) -> bool:
        """安全删除文件夹及其内容
        
        Args:
            folder_path: 要删除的文件夹路径
            force_terminate: 是否强制终止占用进程
            
        Returns:
            bool: 是否删除成功
        """
        if not folder_path.exists():
            logger.debug(f"文件夹不存在，无需删除: {folder_path}")
            return True
        
        if not folder_path.is_dir():
            return self.safe_delete_file(folder_path, force_terminate)
        
        # 递归删除文件夹内容
        for item in folder_path.rglob('*'):
            if item.is_file():
                if not self.safe_delete_file(item, force_terminate):
                    return False
        
        # 删除空文件夹
        for attempt in range(self.max_retries):
            try:
                folder_path.rmdir()
                logger.info(f"✅ 成功删除文件夹: {folder_path.name}")
                return True
            except OSError as e:
                logger.warning(f"删除文件夹失败，尝试第 {attempt + 1}/{self.max_retries} 次: {e}")
                
                # 在Windows上尝试长路径格式
                if sys.platform == "win32" and attempt == self.max_retries - 1:
                    try:
                        long_path = self._get_windows_long_path(folder_path)
                        os.rmdir(long_path)
                        logger.info(f"✅ 使用长路径格式成功删除文件夹: {folder_path.name}")
                        return True
                    except Exception as long_path_error:
                        logger.debug(f"长路径删除也失败: {long_path_error}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        # 最后尝试使用 shutil.rmtree
        try:
            shutil.rmtree(folder_path, ignore_errors=True)
            logger.info(f"✅ 使用 shutil.rmtree 删除文件夹: {folder_path.name}")
            return True
        except Exception as e:
            logger.error(f"❌ 删除文件夹失败: {e}")
            return False
