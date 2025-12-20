"""
撤销管理模块测试
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from dissolvef.undo import (
    UndoManager,
    UndoRecord,
    DissolveOperation
)


@pytest.fixture
def temp_undo_dir():
    """创建临时撤销目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def undo_manager(temp_undo_dir):
    """创建测试用的撤销管理器"""
    return UndoManager(undo_dir=temp_undo_dir)


@pytest.fixture
def temp_work_dir():
    """创建临时工作目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestDissolveOperation:
    """测试操作记录"""
    
    def test_create_move_operation(self):
        """测试创建移动操作"""
        op = DissolveOperation(
            type='move',
            src='/path/to/src',
            dst='/path/to/dst'
        )
        assert op.type == 'move'
        assert op.src == '/path/to/src'
        assert op.dst == '/path/to/dst'
        assert op.timestamp is not None
    
    def test_create_delete_dir_operation(self):
        """测试创建删除目录操作"""
        op = DissolveOperation(
            type='delete_dir',
            src='/path/to/dir'
        )
        assert op.type == 'delete_dir'
        assert op.src == '/path/to/dir'
        assert op.dst is None


class TestUndoRecord:
    """测试撤销记录"""
    
    def test_create_record(self):
        """测试创建记录"""
        ops = [
            DissolveOperation(type='move', src='/a', dst='/b'),
            DissolveOperation(type='delete_dir', src='/c')
        ]
        record = UndoRecord(
            id='test-001',
            timestamp='2024-01-01T00:00:00',
            mode='nested',
            path='/test/path',
            operations=ops
        )
        assert record.id == 'test-001'
        assert record.mode == 'nested'
        assert record.count == 2
    
    def test_auto_count(self):
        """测试自动计数"""
        ops = [DissolveOperation(type='move', src='/a', dst='/b')]
        record = UndoRecord(
            id='test-002',
            timestamp='2024-01-01T00:00:00',
            mode='archive',
            path='/test',
            operations=ops
        )
        assert record.count == 1


class TestUndoManager:
    """测试撤销管理器"""
    
    def test_start_and_finish_batch(self, undo_manager):
        """测试开始和完成批次"""
        undo_manager.start_batch('nested', '/test/path')
        undo_manager.record_move(Path('/a'), Path('/b'))
        undo_manager.record_delete_dir(Path('/c'))
        
        op_id = undo_manager.finish_batch()
        
        assert op_id is not None
        assert op_id.startswith('dissolve-')
    
    def test_empty_batch_returns_none(self, undo_manager):
        """测试空批次返回 None"""
        undo_manager.start_batch('nested', '/test')
        op_id = undo_manager.finish_batch()
        assert op_id is None
    
    def test_list_records(self, undo_manager):
        """测试列出记录"""
        # 创建多个记录
        for i in range(3):
            undo_manager.start_batch('nested', f'/test/{i}')
            undo_manager.record_move(Path(f'/a{i}'), Path(f'/b{i}'))
            undo_manager.finish_batch()
        
        records = undo_manager.list_records()
        assert len(records) == 3
    
    def test_list_records_limit(self, undo_manager):
        """测试列出记录数量限制"""
        for i in range(5):
            undo_manager.start_batch('nested', f'/test/{i}')
            undo_manager.record_move(Path(f'/a{i}'), Path(f'/b{i}'))
            undo_manager.finish_batch()
        
        records = undo_manager.list_records(limit=2)
        assert len(records) == 2
    
    def test_undo_move_operation(self, undo_manager, temp_work_dir):
        """测试撤销移动操作"""
        # 创建源文件
        src_dir = temp_work_dir / "src"
        src_dir.mkdir()
        src_file = src_dir / "test.txt"
        src_file.write_text("hello")
        
        # 移动文件
        dst_dir = temp_work_dir / "dst"
        dst_dir.mkdir()
        dst_file = dst_dir / "test.txt"
        shutil.move(str(src_file), str(dst_file))
        
        # 记录操作
        undo_manager.start_batch('nested', str(temp_work_dir))
        undo_manager.record_move(src_file, dst_file)
        op_id = undo_manager.finish_batch()
        
        # 执行撤销
        success, failed = undo_manager.undo(op_id)
        
        assert success == 1
        assert failed == 0
        assert src_file.exists()
        assert not dst_file.exists()
    
    def test_undo_delete_dir_operation(self, undo_manager, temp_work_dir):
        """测试撤销删除目录操作"""
        # 创建并删除目录
        test_dir = temp_work_dir / "test_dir"
        test_dir.mkdir()
        test_dir.rmdir()
        
        # 记录操作
        undo_manager.start_batch('nested', str(temp_work_dir))
        undo_manager.record_delete_dir(test_dir)
        op_id = undo_manager.finish_batch()
        
        # 执行撤销
        success, failed = undo_manager.undo(op_id)
        
        assert success == 1
        assert failed == 0
        assert test_dir.exists()
    
    def test_undo_latest(self, undo_manager, temp_work_dir):
        """测试撤销最新操作"""
        # 创建文件
        src_file = temp_work_dir / "src.txt"
        src_file.write_text("test")
        dst_file = temp_work_dir / "dst.txt"
        shutil.move(str(src_file), str(dst_file))
        
        # 记录操作
        undo_manager.start_batch('archive', str(temp_work_dir))
        undo_manager.record_move(src_file, dst_file)
        undo_manager.finish_batch()
        
        # 撤销最新（不指定 ID）
        success, failed = undo_manager.undo()
        
        assert success == 1
        assert src_file.exists()
    
    def test_undo_nonexistent_record(self, undo_manager):
        """测试撤销不存在的记录"""
        success, failed = undo_manager.undo('nonexistent-id')
        assert success == 0
        assert failed == 0
    
    def test_undo_removes_record(self, undo_manager, temp_work_dir):
        """测试撤销后删除记录"""
        # 创建操作
        src_file = temp_work_dir / "test.txt"
        src_file.write_text("test")
        dst_file = temp_work_dir / "moved.txt"
        shutil.move(str(src_file), str(dst_file))
        
        undo_manager.start_batch('nested', str(temp_work_dir))
        undo_manager.record_move(src_file, dst_file)
        op_id = undo_manager.finish_batch()
        
        # 撤销
        undo_manager.undo(op_id)
        
        # 记录应该被删除
        records = undo_manager.list_records()
        assert len(records) == 0


class TestUndoManagerEdgeCases:
    """测试边界情况"""
    
    def test_undo_missing_file(self, undo_manager, temp_work_dir):
        """测试撤销时文件不存在"""
        # 记录一个不存在的文件移动
        undo_manager.start_batch('nested', str(temp_work_dir))
        undo_manager.record_move(
            temp_work_dir / "nonexistent_src.txt",
            temp_work_dir / "nonexistent_dst.txt"
        )
        op_id = undo_manager.finish_batch()
        
        # 撤销应该失败但不崩溃
        success, failed = undo_manager.undo(op_id)
        assert failed == 1
    
    def test_multiple_operations_in_batch(self, undo_manager, temp_work_dir):
        """测试批次中多个操作"""
        # 创建多个文件
        files = []
        for i in range(3):
            src = temp_work_dir / f"src_{i}.txt"
            src.write_text(f"content {i}")
            dst = temp_work_dir / f"dst_{i}.txt"
            shutil.move(str(src), str(dst))
            files.append((src, dst))
        
        # 记录所有操作
        undo_manager.start_batch('nested', str(temp_work_dir))
        for src, dst in files:
            undo_manager.record_move(src, dst)
        op_id = undo_manager.finish_batch()
        
        # 撤销
        success, failed = undo_manager.undo(op_id)
        
        assert success == 3
        assert failed == 0
        for src, dst in files:
            assert src.exists()
            assert not dst.exists()
