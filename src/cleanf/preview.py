"""
文件预览模块 - 用于在删除前预览要删除的文件树结构
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Set
from loguru import logger

try:
    from rich.tree import Tree
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logger.warning("Rich库未安装，将使用简单的文本预览")


class FileTreePreview:
    """文件树预览类"""
    
    def __init__(self, console=None):
        """初始化预览器"""
        self.console = console or (Console() if RICH_AVAILABLE else None)
    
    def find_common_root(self, paths: List[Path]) -> Path:
        """
        找到路径列表的最小公共父目录
        
        参数:
        paths: 路径列表
        
        返回:
        最小公共父目录
        """
        if not paths:
            return Path()
        
        if len(paths) == 1:
            return paths[0].parent
        
        # 获取所有路径的父目录集合
        all_parents = []
        for path in paths:
            parents = list(path.parents)
            parents.insert(0, path.parent)  # 包含直接父目录
            all_parents.append(parents)
        
        # 找到最小公共父目录
        common_root = None
        min_depth = min(len(parents) for parents in all_parents)
        
        for depth in range(min_depth):
            candidate = all_parents[0][depth]
            if all(parents[depth] == candidate for parents in all_parents):
                common_root = candidate
                break
        
        return common_root or Path()
    
    def build_tree_structure(self, files_to_delete: List[Path], common_root: Path) -> Dict:
        """
        构建文件树结构
        
        参数:
        files_to_delete: 要删除的文件列表
        common_root: 公共根目录
        
        返回:
        树结构字典
        """
        tree_data = {}
        
        for file_path in files_to_delete:
            # 计算相对于公共根目录的路径
            try:
                rel_path = file_path.relative_to(common_root)
            except ValueError:
                # 如果文件不在公共根目录下，使用绝对路径
                rel_path = file_path
            
            # 构建树结构
            current = tree_data
            parts = rel_path.parts
            
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {
                        '_is_file': i == len(parts) - 1 and file_path.is_file(),
                        '_full_path': file_path if i == len(parts) - 1 else None,
                        '_children': {}
                    }
                current = current[part]['_children']
        
        return tree_data
    
    def create_rich_tree(self, tree_data: Dict, common_root: Path) -> Tree:
        """
        创建Rich树结构
        
        参数:
        tree_data: 树结构数据
        common_root: 公共根目录
        
        返回:
        Rich Tree对象
        """
        if not RICH_AVAILABLE:
            return None
        
        # 创建根节点
        root_text = f"📁 {common_root.name or str(common_root)}"
        tree = Tree(Text(root_text, style="bold blue"))
        
        def add_nodes(parent_node, data_dict):
            for name, info in data_dict.items():
                if info['_is_file']:
                    # 文件节点
                    file_icon = self._get_file_icon(name)
                    node_text = Text(f"{file_icon} {name}", style="red")
                    parent_node.add(node_text)
                else:
                    # 文件夹节点
                    folder_text = Text(f"📁 {name}", style="yellow")
                    folder_node = parent_node.add(folder_text)
                    add_nodes(folder_node, info['_children'])
        
        add_nodes(tree, tree_data)
        return tree
    
    def _get_file_icon(self, filename: str) -> str:
        """根据文件扩展名获取图标"""
        ext = Path(filename).suffix.lower()
        icon_map = {
            '.txt': '📄', '.md': '📝', '.doc': '📄', '.docx': '📄',
            '.pdf': '📕', '.log': '📜', '.bak': '💾',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬',
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
            '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
            '.exe': '⚙️', '.msi': '⚙️',
        }
        return icon_map.get(ext, '📄')
    
    def create_text_tree(self, tree_data: Dict, common_root: Path, indent: str = "") -> List[str]:
        """
        创建文本格式的树结构
        
        参数:
        tree_data: 树结构数据
        common_root: 公共根目录
        indent: 缩进字符串
        
        返回:
        文本行列表
        """
        lines = []
        if not indent:  # 根节点
            lines.append(f"📁 {common_root.name or str(common_root)}")
        
        items = list(tree_data.items())
        for i, (name, info) in enumerate(items):
            is_last = i == len(items) - 1
            
            if info['_is_file']:
                # 文件
                icon = self._get_file_icon(name)
                prefix = "└── " if is_last else "├── "
                lines.append(f"{indent}{prefix}{icon} {name}")
            else:
                # 文件夹
                prefix = "└── " if is_last else "├── "
                lines.append(f"{indent}{prefix}📁 {name}")
                
                # 递归处理子项目
                next_indent = indent + ("    " if is_last else "│   ")
                sub_lines = self.create_text_tree(info['_children'], common_root, next_indent)
                lines.extend(sub_lines)
        
        return lines
    
    def show_preview(self, files_to_delete: List[Path], title: str = "要删除的文件预览") -> bool:
        """
        显示删除预览
        
        参数:
        files_to_delete: 要删除的文件列表
        title: 预览标题
        
        返回:
        用户是否确认删除
        """
        if not files_to_delete:
            if self.console and RICH_AVAILABLE:
                self.console.print("[yellow]没有找到要删除的文件[/yellow]")
            else:
                print("没有找到要删除的文件")
            return False
        
        # 找到公共根目录
        common_root = self.find_common_root(files_to_delete)
        
        # 构建树结构
        tree_data = self.build_tree_structure(files_to_delete, common_root)
        
        if RICH_AVAILABLE and self.console:
            # 使用Rich显示
            tree = self.create_rich_tree(tree_data, common_root)
            
            self.console.print(Panel.fit(
                tree,
                title=f"[bold red]{title}[/bold red]",
                border_style="red"
            ))
            
            # 显示统计信息
            file_count = sum(1 for p in files_to_delete if p.is_file())
            dir_count = sum(1 for p in files_to_delete if p.is_dir())
            
            stats_text = Text()
            stats_text.append("统计信息: ", style="bold")
            stats_text.append(f"{file_count} 个文件", style="red")
            stats_text.append(", ", style="white")
            stats_text.append(f"{dir_count} 个文件夹", style="yellow")
            
            self.console.print(Panel.fit(stats_text, border_style="blue"))
            
            # 确认删除
            return Confirm.ask("[bold red]确认删除以上文件吗?[/bold red]", default=False)
        
        else:
            # 使用文本显示
            print(f"\n{'='*50}")
            print(f"{title}")
            print(f"{'='*50}")
            
            text_lines = self.create_text_tree(tree_data, common_root)
            for line in text_lines:
                print(line)
            
            # 显示统计信息
            file_count = sum(1 for p in files_to_delete if p.is_file())
            dir_count = sum(1 for p in files_to_delete if p.is_dir())
            print(f"\n统计信息: {file_count} 个文件, {dir_count} 个文件夹")
            
            # 确认删除
            while True:
                try:
                    choice = input("\n确认删除以上文件吗? [y/N]: ").strip().lower()
                    if choice in ['y', 'yes']:
                        return True
                    elif choice in ['n', 'no', '']:
                        return False
                    else:
                        print("请输入 y 或 n")
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    return False
    
    def show_simple_list(self, files_to_delete: List[Path], title: str = "要删除的文件列表"):
        """
        显示简单的文件列表
        
        参数:
        files_to_delete: 要删除的文件列表
        title: 列表标题
        """
        if not files_to_delete:
            print("没有找到要删除的文件")
            return
        
        print(f"\n{title}:")
        print("-" * 50)
        
        for i, path in enumerate(files_to_delete, 1):
            file_type = "📁" if path.is_dir() else "📄"
            print(f"{i:3d}. {file_type} {path}")
        
        print(f"\n总计: {len(files_to_delete)} 个项目")


def preview_deletion(files_to_delete: List[Path], title: str = "删除预览", 
                     console=None) -> bool:
    """
    便捷的预览函数
    
    参数:
    files_to_delete: 要删除的文件列表
    title: 预览标题
    console: Rich控制台对象
    
    返回:
    用户是否确认删除
    """
    previewer = FileTreePreview(console)
    return previewer.show_preview(files_to_delete, title)


def show_deletion_list(files_to_delete: List[Path], title: str = "删除列表"):
    """
    便捷的列表显示函数
    
    参数:
    files_to_delete: 要删除的文件列表
    title: 列表标题
    """
    previewer = FileTreePreview()
    previewer.show_simple_list(files_to_delete, title)


if __name__ == "__main__":
    # 测试代码
    from pathlib import Path
    
    # 创建测试路径
    test_paths = [
        Path("/test/folder1/file1.txt"),
        Path("/test/folder1/file2.bak"),
        Path("/test/folder2/temp_folder"),
        Path("/test/file3.log"),
    ]
    
    # 测试预览功能
    previewer = FileTreePreview()
    previewer.show_preview(test_paths, "测试删除预览")
