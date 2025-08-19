"""
时间戳恢复工具的交互式界面模块
"""
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.rule import Rule
from loguru import logger

from .core.extract_date import extract_date_from_filename
from .core.restore_timestamp import restore_file_timestamp

class InteractiveUI:
    """交互式用户界面类"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def get_paths_from_clipboard(self) -> List[Path]:
        """从剪贴板获取路径列表"""
        try:
            import pyperclip
            clipboard_content = pyperclip.paste()
            paths = []
            if clipboard_content:
                for line in clipboard_content.splitlines():
                    if line := line.strip().strip('"').strip("'"):
                        path = Path(line)
                        if path.exists():
                            paths.append(path)
                            self.console.print(f"[green]✓ 已添加路径:[/green] {path}")
                        else:
                            self.console.print(f"[yellow]警告：路径不存在[/yellow] - {line}")
            return paths
        except ImportError:
            self.console.print("[yellow]警告：未安装pyperclip模块，无法从剪贴板读取[/yellow]")
            return []
        except Exception as e:
            self.console.print(f"[red]从剪贴板读取失败[/red]: {e}")
            return []
    
    def get_paths_interactively(self) -> List[Path]:
        """交互式获取要处理的路径"""
        self.console.print("\n[bold blue]== 选择要处理的路径 ==[/bold blue]")
        paths = []
        
        # 显示输入方式选项
        table = Table(title="路径输入方式")
        table.add_column("选项", style="cyan", width=5)
        table.add_column("说明", style="white")
        table.add_row("1", "从剪贴板读取路径")
        table.add_row("2", "手动输入路径")
        
        self.console.print(table)
        
        choice = Prompt.ask("请选择输入方式", choices=["1", "2"], default="1")
        
        if choice == "1":
            # 从剪贴板读取
            paths = self.get_paths_from_clipboard()
            
            if paths:
                path_table = Table(title="从剪贴板读取的路径")
                path_table.add_column("序号", style="cyan")
                path_table.add_column("路径", style="green")
                path_table.add_column("类型", style="yellow")
                
                for i, path in enumerate(paths, 1):
                    path_type = "📁 文件夹" if path.is_dir() else "📄 文件"
                    path_table.add_row(str(i), str(path), path_type)
                
                self.console.print(path_table)
            else:
                self.console.print("[yellow]未从剪贴板读取到任何有效路径[/yellow]")
                return []
        
        elif choice == "2":
            # 手动输入路径
            self.console.print("\n[yellow]请输入要处理的文件或文件夹路径 (输入空行结束):[/yellow]")
            while True:
                try:
                    line = Prompt.ask("路径", default="")
                    if not line:
                        break
                    
                    path = Path(line.strip().strip('"').strip("'"))
                    if path.exists():
                        paths.append(path)
                        path_type = "📁 文件夹" if path.is_dir() else "📄 文件"
                        self.console.print(f"[green]✓ 已添加路径:[/green] {path_type} {path}")
                    else:
                        self.console.print(f"[red]✗ 路径不存在:[/red] {line}")
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]操作已取消[/yellow]")
                    return []
        
        return paths
    
    def collect_files(self, paths: List[Path]) -> List[Path]:
        """收集所有文件"""
        all_files = []
        
        self.console.print("\n[bold]正在收集文件...[/bold]")
        
        for path in paths:
            if path.is_file():
                all_files.append(path)
            elif path.is_dir():
                for item in path.rglob('*'):
                    if item.is_file():
                        all_files.append(item)
        
        self.console.print(f"[cyan]找到 {len(all_files)} 个文件[/cyan]")
        return all_files
    
    def analyze_files(self, files: List[Path]) -> Tuple[List[Tuple[Path, any]], List[Path]]:
        """分析文件并提取日期"""
        processable_files = []
        skipped_files = []
        
        self.console.print("\n[bold]分析文件名中的日期...[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task("分析文件...", total=len(files))
            
            for file_path in files:
                progress.update(task, description=f"分析: {file_path.name}")
                
                extracted_date = extract_date_from_filename(file_path.name)
                if extracted_date:
                    processable_files.append((file_path, extracted_date))
                    logger.debug(f"从 '{file_path.name}' 提取到日期: {extracted_date}")
                else:
                    skipped_files.append(file_path)
                    logger.debug(f"未能从 '{file_path.name}' 提取日期")
                
                progress.advance(task)
        
        return processable_files, skipped_files
    
    def show_preview(self, processable_files: List[Tuple[Path, any]], skipped_files: List[Path]):
        """显示预览信息"""
        self.console.print(Rule("📊 分析结果"))
        
        # 显示统计信息
        stats_table = Table(title="统计信息")
        stats_table.add_column("类型", style="cyan")
        stats_table.add_column("数量", style="green")
        stats_table.add_row("可处理文件", str(len(processable_files)))
        stats_table.add_row("跳过文件", str(len(skipped_files)))
        
        self.console.print(stats_table)
        
        if not processable_files:
            self.console.print("[yellow]没有找到可处理的文件[/yellow]")
            return False
        
        # 显示可处理文件的预览
        self.console.print("\n[bold blue]== 可处理文件预览 ==[/bold blue]")
        
        preview_table = Table(show_header=True)
        preview_table.add_column("文件名", style="cyan", max_width=50)
        preview_table.add_column("识别日期", style="green")
        preview_table.add_column("当前修改时间", style="yellow")
        preview_table.add_column("文件路径", style="dim", max_width=40)
        
        # 显示前10个文件的详细信息
        show_count = min(10, len(processable_files))
        for file_path, extracted_date in processable_files[:show_count]:
            from datetime import datetime
            current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            preview_table.add_row(
                file_path.name,
                extracted_date.strftime("%Y-%m-%d"),
                current_mtime.strftime("%Y-%m-%d %H:%M:%S"),
                str(file_path.parent)
            )
        
        if len(processable_files) > 10:
            preview_table.add_row("...", "...", "...", "...")
            self.console.print(f"[dim]（还有 {len(processable_files) - 10} 个文件未显示）[/dim]")
        
        self.console.print(preview_table)
        
        # 显示跳过文件的示例
        if skipped_files:
            self.console.print("\n[bold yellow]== 跳过文件示例 ==[/bold yellow]")
            skip_table = Table(show_header=True)
            skip_table.add_column("文件名", style="yellow", max_width=50)
            skip_table.add_column("原因", style="red")
            
            show_skip_count = min(5, len(skipped_files))
            for file_path in skipped_files[:show_skip_count]:
                skip_table.add_row(file_path.name, "无法识别日期格式")
            
            if len(skipped_files) > 5:
                skip_table.add_row("...", "...")
                self.console.print(f"[dim]（还有 {len(skipped_files) - 5} 个跳过文件未显示）[/dim]")
            
            self.console.print(skip_table)
        
        return True
    
    def execute_restore(self, processable_files: List[Tuple[Path, any]]):
        """执行时间戳恢复"""
        self.console.print(Rule("🔄 执行时间戳恢复"))
        
        success_count = 0
        error_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task("恢复时间戳...", total=len(processable_files))
            
            for file_path, extracted_date in processable_files:
                progress.update(task, description=f"处理: {file_path.name}")
                
                try:
                    restore_file_timestamp(file_path, extracted_date)
                    success_count += 1
                    logger.info(f"已恢复 {file_path} 的时间戳为 {extracted_date}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"恢复 {file_path} 时间戳失败: {e}")
                    self.console.print(f"[red]错误[/red]: {file_path.name} - {e}")
                
                progress.advance(task)
        
        # 显示结果
        self.console.print(Panel.fit(
            f"[green]成功处理: {success_count}[/green]\n"
            f"[red]处理失败: {error_count}[/red]",
            title="📊 处理结果",
            border_style="green"
        ))
        
        return success_count, error_count
    
    def run_interactive(self):
        """运行完整的交互式界面"""
        # 显示欢迎信息
        self.console.print(Panel.fit(
            "[bold blue]文件时间戳恢复工具[/bold blue]\n\n"
            "从文件名中识别日期并恢复文件的时间戳\n"
            "支持多种日期格式：YYYY-MM-DD、YYYY.MM.DD、YYYYMMDD 等",
            title="🕒 RestoreT",
            border_style="blue"
        ))
        
        try:
            # 1. 获取要处理的路径
            paths = self.get_paths_interactively()
            if not paths:
                self.console.print("[yellow]未选择任何路径，操作取消[/yellow]")
                return
            
            # 2. 收集所有文件
            all_files = self.collect_files(paths)
            if not all_files:
                self.console.print("[yellow]未找到任何文件[/yellow]")
                return
            
            # 3. 分析文件并提取日期
            processable_files, skipped_files = self.analyze_files(all_files)
            
            # 4. 显示预览
            if not self.show_preview(processable_files, skipped_files):
                return
            
            # 5. 询问是否执行
            if not Confirm.ask("\n[bold]确认恢复这些文件的时间戳吗？[/bold]", default=False):
                self.console.print("[yellow]操作已取消[/yellow]")
                return
            
            # 6. 执行恢复操作
            success_count, error_count = self.execute_restore(processable_files)
            
            # 7. 询问是否继续
            if Confirm.ask("\n是否继续处理其他文件？", default=False):
                self.run_interactive()
            else:
                self.console.print("\n[bold green]感谢使用文件时间戳恢复工具！[/bold green]")
        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]操作已取消[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]发生错误:[/red] {e}")
            logger.error(f"交互式界面发生错误: {e}")


def run_interactive():
    """启动交互式界面"""
    ui = InteractiveUI()
    ui.run_interactive()