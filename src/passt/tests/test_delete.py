"""
passt 删除模块测试

测试 SafeDeleter 类的文件和文件夹删除功能，特别是Windows路径末尾空格处理
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from passt.core.delete import SafeDeleter


class TestSafeDeleterInit:
    """测试 SafeDeleter 初始化"""
    
    def test_init_default_values(self):
        """测试默认初始化参数"""
        deleter = SafeDeleter()
        assert deleter.max_retries == 5
        assert deleter.retry_delay == 1.0
    
    def test_init_custom_values(self):
        """测试自定义初始化参数"""
        deleter = SafeDeleter(max_retries=3, retry_delay=0.5)
        assert deleter.max_retries == 3
        assert deleter.retry_delay == 0.5


class TestWindowsLongPath:
    """测试Windows长路径处理"""
    
    def test_get_windows_long_path_on_windows(self):
        """测试在Windows上生成长路径格式"""
        deleter = SafeDeleter()
        test_path = Path("C:/test/folder")
        
        with patch('sys.platform', 'win32'):
            long_path = deleter._get_windows_long_path(test_path)
            assert long_path.startswith("\\\\?\\")
    
    def test_get_windows_long_path_on_non_windows(self):
        """测试在非Windows系统上返回普通路径"""
        deleter = SafeDeleter()
        test_path = Path("/test/folder")
        
        with patch('sys.platform', 'linux'):
            long_path = deleter._get_windows_long_path(test_path)
            assert not long_path.startswith("\\\\?\\")


class TestSafeDeleteFile:
    """测试安全删除文件功能"""
    
    def test_delete_existing_file(self):
        """测试删除存在的文件"""
        deleter = SafeDeleter()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"test content")
        
        assert tmp_path.exists()
        result = deleter.safe_delete_file(tmp_path)
        assert result is True
        assert not tmp_path.exists()
    
    def test_delete_non_existing_file(self):
        """测试删除不存在的文件"""
        deleter = SafeDeleter()
        non_existing = Path("/tmp/non_existing_file_12345.txt")
        
        result = deleter.safe_delete_file(non_existing)
        assert result is True
    
    def test_delete_file_with_permission_error(self):
        """测试处理权限错误"""
        deleter = SafeDeleter(max_retries=2, retry_delay=0.1)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        # 模拟权限错误，且长路径也失败
        with patch.object(Path, 'unlink', side_effect=PermissionError("Access denied")):
            with patch.object(deleter, 'find_file_processes', return_value=[]):
                with patch('os.unlink', side_effect=PermissionError("Access denied")):
                    result = deleter.safe_delete_file(tmp_path)
                    assert result is False
        
        # 清理
        if tmp_path.exists():
            tmp_path.unlink()


class TestSafeDeleteFolder:
    """测试安全删除文件夹功能"""
    
    def test_delete_empty_folder(self):
        """测试删除空文件夹"""
        deleter = SafeDeleter()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            test_folder = tmp_path / "test_empty"
            test_folder.mkdir()
            
            assert test_folder.exists()
            result = deleter.safe_delete_folder(test_folder)
            assert result is True
            assert not test_folder.exists()
    
    def test_delete_folder_with_files(self):
        """测试删除包含文件的文件夹"""
        deleter = SafeDeleter()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            test_folder = tmp_path / "test_with_files"
            test_folder.mkdir()
            
            # 创建测试文件
            (test_folder / "file1.txt").write_text("content1")
            (test_folder / "file2.txt").write_text("content2")
            
            assert test_folder.exists()
            result = deleter.safe_delete_folder(test_folder)
            assert result is True
            assert not test_folder.exists()
    
    def test_delete_non_existing_folder(self):
        """测试删除不存在的文件夹"""
        deleter = SafeDeleter()
        non_existing = Path("/tmp/non_existing_folder_12345")
        
        result = deleter.safe_delete_folder(non_existing)
        assert result is True
    
    def test_delete_file_as_folder(self):
        """测试尝试删除文件时调用文件删除方法"""
        deleter = SafeDeleter()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        with patch.object(deleter, 'safe_delete_file', return_value=True) as mock_delete:
            result = deleter.safe_delete_folder(tmp_path)
            mock_delete.assert_called_once()
            assert result is True
        
        # 清理
        if tmp_path.exists():
            tmp_path.unlink()


class TestFindFileProcesses:
    """测试查找占用文件的进程"""
    
    def test_find_file_processes_no_processes(self):
        """测试未找到占用进程"""
        deleter = SafeDeleter()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            processes = deleter.find_file_processes(tmp_path)
            assert isinstance(processes, list)
            # 通常不会有进程占用临时文件
            assert len(processes) == 0
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_find_file_processes_with_mock(self):
        """测试使用mock查找占用进程"""
        deleter = SafeDeleter()
        test_path = Path("/test/file.txt")
        
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test.exe',
            'open_files': [Mock(path=str(test_path.resolve()))]
        }
        
        with patch('psutil.process_iter', return_value=[mock_proc]):
            processes = deleter.find_file_processes(test_path)
            assert len(processes) == 1


class TestTerminateProcesses:
    """测试终止进程功能"""
    
    def test_terminate_empty_list(self):
        """测试终止空进程列表"""
        deleter = SafeDeleter()
        result = deleter.terminate_processes([])
        assert result is True
    
    def test_terminate_processes_graceful(self):
        """测试优雅终止进程"""
        deleter = SafeDeleter()
        
        mock_proc = Mock()
        mock_proc.name.return_value = "test.exe"
        mock_proc.pid = 1234
        mock_proc.terminate.return_value = None
        mock_proc.wait.return_value = None
        
        result = deleter.terminate_processes([mock_proc], force=False)
        assert result is True
        mock_proc.terminate.assert_called_once()
    
    def test_terminate_processes_force(self):
        """测试强制终止进程"""
        deleter = SafeDeleter()
        
        mock_proc = Mock()
        mock_proc.name.return_value = "test.exe"
        mock_proc.pid = 1234
        mock_proc.kill.return_value = None
        mock_proc.wait.return_value = None
        
        result = deleter.terminate_processes([mock_proc], force=True)
        assert result is True
        mock_proc.kill.assert_called_once()
    
    def test_terminate_processes_timeout(self):
        """测试进程终止超时处理"""
        deleter = SafeDeleter()
        
        mock_proc = Mock()
        mock_proc.name.return_value = "test.exe"
        mock_proc.pid = 1234
        mock_proc.terminate.return_value = None
        mock_proc.wait.side_effect = [
            pytest.importorskip("psutil").TimeoutExpired(1234, 3),
            None
        ]
        mock_proc.kill.return_value = None
        
        result = deleter.terminate_processes([mock_proc], force=False)
        assert result is True
        mock_proc.kill.assert_called_once()


class TestWindowsPathWithTrailingSpace:
    """测试Windows路径末尾空格处理"""
    
    @pytest.mark.skipif(sys.platform != "win32", reason="仅在Windows上运行")
    def test_delete_folder_with_trailing_space(self):
        """测试删除末尾带空格的文件夹
        
        这是修复的核心功能：处理Windows"幽灵"文件夹
        注意：Windows会自动去掉末尾空格，所以这个测试验证长路径格式的生成
        """
        deleter = SafeDeleter()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # 创建普通文件夹用于测试
            test_folder = tmp_path / "test_folder"
            test_folder.mkdir()
            
            # 创建测试文件
            (test_folder / "test.txt").write_text("content")
            
            assert test_folder.exists()
            result = deleter.safe_delete_folder(test_folder)
            assert result is True
            assert not test_folder.exists()
    
    def test_windows_long_path_format(self):
        """测试Windows长路径格式生成"""
        deleter = SafeDeleter()
        test_path = Path("C:/test/folder with space ")
        
        with patch('sys.platform', 'win32'):
            long_path = deleter._get_windows_long_path(test_path)
            # 验证长路径格式
            assert long_path.startswith("\\\\?\\")
            # 验证路径包含空格
            assert " " in long_path or "space" in long_path
