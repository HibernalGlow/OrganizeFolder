"""
翻译结果整理工具
扫描翻译后的 original_images 文件夹，确保 result 目录完整且唯一
"""
import json
import shutil
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import send2trash
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

# Windows 控制台编码修复
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

console = Console(force_terminal=True)


@dataclass
class TranslationMap:
    """翻译映射数据"""
    original_images_dir: Path
    result_dir: Path
    translation_map_file: Path
    original_files: Set[str]
    result_files: Set[str]
    missing_files: Set[str]
    extra_files: Set[str]


class TransqProcessor:
    """翻译结果整理处理器"""
    
    def __init__(self, root_path: Path, dry_run: bool = False, verbose: bool = False):
        """
        初始化处理器
        
        Args:
            root_path: 根目录路径
            dry_run: 是否只预览不执行
            verbose: 是否显示详细错误信息
        """
        self.root_path = Path(root_path)
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            'scanned_dirs': 0,
            'copied_files': 0,
            'deleted_originals': 0,
            'deleted_work_files': 0,
            'errors': 0
        }
        self.results = []
        self.error_details = []
    
    def scan_original_images_dirs(self) -> List[Path]:
        """
        扫描所有 original_images 目录
        
        Returns:
            original_images 目录列表
        """
        original_images_dirs = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("扫描目录...", total=None)
            
            for original_images in self.root_path.rglob('original_images'):
                if original_images.is_dir():
                    result_dir = original_images / 'manga_translator_work' / 'result'
                    if result_dir.exists():
                        original_images_dirs.append(original_images)
                        progress.update(task, description=f"扫描目录... 找到 {len(original_images_dirs)} 个")
        
        console.print(f"[green]✓[/green] 共找到 [bold]{len(original_images_dirs)}[/bold] 个 original_images 目录")
        return original_images_dirs
    
    def load_translation_map(self, result_dir: Path) -> Dict:
        """
        加载 translation_map.json
        
        Args:
            result_dir: result 目录路径
            
        Returns:
            翻译映射字典
        """
        translation_map_file = result_dir / 'translation_map.json'
        
        if not translation_map_file.exists():
            return {}
        
        try:
            with open(translation_map_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception:
            return {}
    
    def analyze_directory(self, original_images_dir: Path) -> TranslationMap:
        """
        分析目录结构
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            翻译映射数据
        """
        result_dir = original_images_dir / 'manga_translator_work' / 'result'
        translation_map_file = result_dir / 'translation_map.json'
        
        original_files = {f.name for f in original_images_dir.iterdir() if f.is_file()}
        result_files = {f.name for f in result_dir.iterdir() if f.is_file() and f.name != 'translation_map.json'}
        
        translation_map = self.load_translation_map(result_dir)
        
        original_in_map = set(translation_map.keys())
        
        missing_files = original_in_map - result_files
        extra_files = result_files - original_in_map
        
        return TranslationMap(
            original_images_dir=original_images_dir,
            result_dir=result_dir,
            translation_map_file=translation_map_file,
            original_files=original_files,
            result_files=result_files,
            missing_files=missing_files,
            extra_files=extra_files
        )
    
    def copy_missing_files(self, trans_map: TranslationMap) -> int:
        """
        复制缺失的原图到 result 目录
        
        Args:
            trans_map: 翻译映射数据
            
        Returns:
            复制的文件数量
        """
        copied_count = 0
        
        for filename in trans_map.missing_files:
            src_file = trans_map.original_images_dir / filename
            dst_file = trans_map.result_dir / filename
            
            if src_file.exists():
                if self.dry_run:
                    copied_count += 1
                else:
                    try:
                        shutil.copy2(src_file, dst_file)
                        copied_count += 1
                    except Exception as e:
                        self.stats['errors'] += 1
                        error_msg = f"复制失败: {src_file} -> {dst_file}\n错误: {e}"
                        self.error_details.append(error_msg)
                        if self.verbose:
                            console.print(f"[red]✗ {error_msg}[/red]")
        
        return copied_count
    
    def delete_original_images_to_trash(self, trans_map: TranslationMap) -> int:
        """
        删除 original_images 目录到回收站
        
        Args:
            trans_map: 翻译映射数据
            
        Returns:
            删除的文件数量
        """
        if self.dry_run:
            return len(list(trans_map.original_images_dir.iterdir()))
        
        try:
            send2trash.send2trash(str(trans_map.original_images_dir))
            return len(trans_map.original_files)
        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"删除失败: {trans_map.original_images_dir}\n错误: {e}"
            self.error_details.append(error_msg)
            if self.verbose:
                console.print(f"[red]✗ {error_msg}[/red]")
            return 0
    
    def clean_manga_translator_work(self, original_images_dir: Path) -> Tuple[int, int]:
        """
        清理 manga_translator_work 目录下的 inpainted 和 json 文件
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            (删除的 inpainted 数量, 删除的 json 数量)
        """
        work_dir = original_images_dir / 'manga_translator_work'
        
        if not work_dir.exists():
            return 0, 0
        
        deleted_inpainted = 0
        deleted_json = 0
        
        for item in work_dir.iterdir():
            if item.is_dir() and item.name == 'inpainted':
                if self.dry_run:
                    deleted_inpainted += len(list(item.rglob('*')))
                else:
                    try:
                        send2trash.send2trash(str(item))
                        deleted_inpainted += 1
                    except Exception as e:
                        self.stats['errors'] += 1
                        error_msg = f"删除失败: {item}\n错误: {e}"
                        self.error_details.append(error_msg)
                        if self.verbose:
                            console.print(f"[red]✗ {error_msg}[/red]")
            
            elif item.is_file() and item.suffix == '.json':
                if self.dry_run:
                    deleted_json += 1
                else:
                    try:
                        send2trash.send2trash(str(item))
                        deleted_json += 1
                    except Exception as e:
                        self.stats['errors'] += 1
                        error_msg = f"删除失败: {item}\n错误: {e}"
                        self.error_details.append(error_msg)
                        if self.verbose:
                            console.print(f"[red]✗ {error_msg}[/red]")
        
        return deleted_inpainted, deleted_json
    
    def process_directory(self, original_images_dir: Path) -> bool:
        """
        处理单个目录
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            是否处理成功
        """
        try:
            trans_map = self.analyze_directory(original_images_dir)
            
            result_data = {
                'path': original_images_dir,
                'original_count': len(trans_map.original_files),
                'result_count': len(trans_map.result_files),
                'missing_count': len(trans_map.missing_files),
                'copied': 0,
                'deleted_work': 0,
                'moved': False
            }
            
            copied = self.copy_missing_files(trans_map)
            self.stats['copied_files'] += copied
            result_data['copied'] = copied
            
            deleted_inpainted, deleted_json = self.clean_manga_translator_work(original_images_dir)
            self.stats['deleted_work_files'] += deleted_inpainted + deleted_json
            result_data['deleted_work'] = deleted_inpainted + deleted_json
            
            parent_dir = original_images_dir.parent
            new_result_dir = parent_dir / 'result'
            
            if not self.dry_run:
                if not new_result_dir.exists():
                    try:
                        shutil.move(str(trans_map.result_dir), str(new_result_dir))
                        result_data['moved'] = True
                    except Exception as e:
                        self.stats['errors'] += 1
                        error_msg = f"移动失败: {trans_map.result_dir} -> {new_result_dir}\n错误: {e}"
                        self.error_details.append(error_msg)
                        if self.verbose:
                            console.print(f"[red]✗ {error_msg}[/red]")
            
            if copied > 0 or len(trans_map.missing_files) == 0:
                deleted = self.delete_original_images_to_trash(trans_map)
                self.stats['deleted_originals'] += deleted
            
            self.stats['scanned_dirs'] += 1
            self.results.append(result_data)
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"处理目录失败: {original_images_dir}\n错误: {e}"
            self.error_details.append(error_msg)
            if self.verbose:
                console.print(f"[red]✗ {error_msg}[/red]")
            return False
    
    def run(self) -> Dict:
        """
        运行整理任务
        
        Returns:
            统计数据
        """
        console.print(Panel.fit(
            "[bold cyan]翻译结果整理工具[/bold cyan]\n"
            f"扫描目录: [yellow]{self.root_path}[/yellow]\n"
            f"模式: [yellow]{'预览模式' if self.dry_run else '执行模式'}[/yellow]",
            border_style="cyan"
        ))
        
        original_images_dirs = self.scan_original_images_dirs()
        
        if not original_images_dirs:
            console.print("[yellow]⚠ 未找到任何 original_images 目录[/yellow]")
            return self.stats
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("处理目录...", total=len(original_images_dirs))
            
            for original_images_dir in original_images_dirs:
                self.process_directory(original_images_dir)
                progress.advance(task)
        
        self.print_summary()
        return self.stats
    
    def print_summary(self):
        """打印处理结果汇总"""
        console.print()
        
        if self.dry_run:
            console.print(Panel.fit(
                "[bold yellow]预览结果[/bold yellow]\n"
                "以下是将要执行的操作（未实际执行）",
                border_style="yellow"
            ))
        else:
            console.print(Panel.fit(
                "[bold green]处理完成[/bold green]",
                border_style="green"
            ))
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("统计项", style="cyan")
        table.add_column("数量", justify="right", style="green")
        
        table.add_row("扫描目录数", str(self.stats['scanned_dirs']))
        table.add_row("复制文件数", str(self.stats['copied_files']))
        table.add_row("删除原图数", str(self.stats['deleted_originals']))
        table.add_row("删除工作文件数", str(self.stats['deleted_work_files']))
        
        if self.stats['errors'] > 0:
            table.add_row("错误数", f"[red]{self.stats['errors']}[/red]")
        else:
            table.add_row("错误数", "[green]0[/green]")
        
        console.print(table)
        
        # 显示错误详情
        if self.stats['errors'] > 0 and self.error_details:
            console.print()
            console.print(Panel.fit(
                f"[bold red]错误详情 ({len(self.error_details)} 个)[/bold red]\n"
                "[dim]使用 --verbose 参数查看详细错误信息[/dim]",
                border_style="red"
            ))
            
            if self.verbose or len(self.error_details) <= 5:
                console.print()
                for i, error in enumerate(self.error_details[:10], 1):
                    console.print(f"[red]{i}.[/red] {error}")
                
                if len(self.error_details) > 10:
                    console.print(f"[dim]... 还有 {len(self.error_details) - 10} 个错误未显示[/dim]")
        
        if self.dry_run and self.stats['scanned_dirs'] > 0:
            console.print()
            console.print("[yellow]提示:[/yellow] 使用 [bold]--execute[/bold] 参数执行实际操作")
            console.print("[dim]示例: transq \"路径\" --execute[/dim]")


def main():
    """主函数"""
    import typer
    from rich.prompt import Prompt, Confirm
    
    app = typer.Typer(help="翻译结果整理工具")
    
    @app.callback(invoke_without_command=True)
    def callback(
        path: str = typer.Argument(None, help="要扫描的根目录路径"),
        execute: bool = typer.Option(False, "--execute", "-e", help="执行实际操作（默认为预览模式）"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细错误信息"),
        dry_run: bool = typer.Option(None, "--dry-run", help="预览模式（已废弃，默认就是预览）"),
    ):
        """
        翻译结果整理工具
        
        扫描翻译后的 original_images 文件夹，确保 result 目录完整且唯一
        """
        # 引导式输入路径
        if path is None:
            console.print(Panel.fit(
                "[bold cyan]翻译结果整理工具[/bold cyan]\n\n"
                "[dim]功能:[/dim]\n"
                "  • 扫描所有 original_images 目录\n"
                "  • 补全 result 内缺失的原图\n"
                "  • 删除工作文件到回收站\n"
                "  • 移动 result 到正确位置\n"
                "  • 删除 original_images 到回收站",
                border_style="cyan"
            ))
            console.print()
            
            path = Prompt.ask(
                "[yellow]请输入要扫描的根目录路径[/yellow]",
                default="."
            )
            
            if not path or path.strip() == "":
                console.print("[red]错误: 路径不能为空[/red]")
                raise typer.Exit(1)
        
        # 确定是否为预览模式
        is_dry_run = not execute
        if dry_run is not None:
            is_dry_run = dry_run
        
        # 验证路径是否存在
        path_obj = Path(path)
        if not path_obj.exists():
            console.print(f"[red]错误: 路径不存在: {path}[/red]")
            raise typer.Exit(1)
        
        if not path_obj.is_dir():
            console.print(f"[red]错误: 路径不是目录: {path}[/red]")
            raise typer.Exit(1)
        
        # 执行处理
        processor = TransqProcessor(path_obj, dry_run=is_dry_run, verbose=verbose)
        processor.run()
        
        # 预览结束后询问是否执行
        if is_dry_run and processor.stats['scanned_dirs'] > 0:
            console.print()
            if Confirm.ask("[yellow]是否立即执行实际操作？[/yellow]", default=False):
                console.print()
                console.print(Panel.fit(
                    "[bold green]开始执行实际操作...[/bold green]",
                    border_style="green"
                ))
                processor_execute = TransqProcessor(path_obj, dry_run=False, verbose=verbose)
                processor_execute.run()
    
    app()


if __name__ == '__main__':
    main()
