import shutil
import tempfile
from pathlib import Path
import pytest
from dissolvef.nested import flatten_single_subfolder

def make_nested_dirs(base, structure):
    """
    递归创建嵌套目录结构。
    structure: list or str, e.g. ["a", ["b", ["c"]]]
    """
    if isinstance(structure, str):
        d = base / structure
        d.mkdir()
        return d
    elif isinstance(structure, list) and structure:
        d = base / structure[0]
        d.mkdir()
        if len(structure) > 1:
            return make_nested_dirs(d, structure[1])
        return d
    return base

def test_flatten_single_subfolder_max_depth():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 创建 a/b/c/d 四级嵌套
        make_nested_dirs(root, ["a", ["b", ["c", ["d"]]]])
        # 在最深层放一个文件
        file_path = root / "a" / "b" / "c" / "d" / "test.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello")
        # 限制只解散2层
        count = flatten_single_subfolder(root / "a", max_depth=2)
        # a/b/c/d 应变为 a/b/c/d，a/b/c 仍然存在
        assert (root / "a" / "b" / "c").exists()
        assert (root / "a" / "b" / "c" / "d").exists()
        # 文件未被移动到a
        assert not (root / "a" / "test.txt").exists()
        # 只解散了2层
        assert count >= 1

def test_flatten_single_subfolder_no_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        make_nested_dirs(root, ["a", ["b", ["c", ["d"]]]])
        file_path = root / "a" / "b" / "c" / "d" / "test.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello")
        # 不限制层数
        count = flatten_single_subfolder(root / "a")
        # a/b/c/d 应被解散，test.txt 应在 a 下
        assert (root / "a" / "test.txt").exists()
        assert not (root / "a" / "b").exists()
        assert count >= 1
