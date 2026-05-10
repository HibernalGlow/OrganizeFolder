"""Quick classify CLI - classify folders by keyword recursively."""
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import typer
from rich.console import Console
from rich.prompt import Prompt
from loguru import logger

app = typer.Typer(help="快速分类工具 - 通过关键词递归分类文件夹")
console = Console()

def setup_logger(app_name="classq", project_root=None, console_output=True):
    """Configure Loguru logger."""
    if project_root is None:
        project_root = Path.cwd()
    
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{app_name}_{{time:YYYY-MM-DD}}.log"
    
    logger.remove()
    
    if console_output:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
    
    logger.add(
        str(log_file),
        rotation="00:00",
        retention="7 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")


def _quick_classify_by_keyword(
    base_dir: Path,
    keyword: str,
    wait_keyword: str = "wait",
    action: str = "move",
    existing_dir_behavior: str = "merge",
) -> Tuple[int, int]:
    """
    Quick classify: find folders containing keyword, move siblings to wait folder.
    
    Args:
        base_dir: The directory to scan
        keyword: The keyword to find (e.g., "already")
        wait_keyword: The name for wait folder (default: "wait")
        action: "move" or "copy"
        existing_dir_behavior: "merge" or "skip"
    
    Returns:
        (total_already_count, total_wait_count) - number of items moved
    """
    keyword_lower = keyword.lower()
    total_wait_count = 0
    total_already_count = 0
    
    def find_keyword_folders(root: Path) -> List[Path]:
        """Recursively find all folders containing the keyword."""
        found = []
        for item in root.rglob("*"):
            if item.is_dir() and keyword_lower in item.name.lower():
                found.append(item)
        return found
    
    keyword_folders = find_keyword_folders(base_dir)
    
    if not keyword_folders:
        logger.error(f"No folder containing keyword '{keyword}' found in {base_dir}")
        return 0, 0
    
    logger.info(f"Found {len(keyword_folders)} folders containing '{keyword}'")
    console.print(f"[green]找到 {len(keyword_folders)} 个包含 '{keyword}' 的文件夹[/green]")
    
    processed_parents: set = set()
    
    for keyword_dir in keyword_folders:
        parent_dir = keyword_dir.parent
        parent_key = str(parent_dir.resolve())
        
        if parent_key in processed_parents:
            continue
        processed_parents.add(parent_key)
        
        wait_dir = parent_dir / wait_keyword
        wait_candidates: List[str] = []
        
        for item in parent_dir.iterdir():
            if item.is_dir():
                if item.resolve() == keyword_dir.resolve():
                    continue
                if item.resolve() == wait_dir.resolve():
                    continue
                if keyword_lower in item.name.lower():
                    continue
                wait_candidates.append(str(item))
            elif item.is_file():
                wait_candidates.append(str(item))
        
        if not wait_candidates:
            logger.info(f"No items to move in {parent_dir}")
            continue
        
        logger.info(f"Moving {len(wait_candidates)} items from {parent_dir} to {wait_dir}")
        console.print(f"[cyan]移动 {len(wait_candidates)} 个项目从 {parent_dir.name} 到 {wait_keyword}/[/cyan]")
        
        _migrate_items(wait_candidates, str(wait_dir), action=action, existing_dir_behavior=existing_dir_behavior)
        total_wait_count += len(wait_candidates)
        total_already_count += 1
    
    logger.info(f"Quick classify complete: {total_already_count} keyword folders processed, {total_wait_count} items moved to wait")
    return total_already_count, total_wait_count


def _migrate_items(
    source_paths: List[str],
    target_dir: str,
    action: str = "move",
    existing_dir_behavior: str = "merge",
) -> None:
    """Move or copy items to target directory."""
    import shutil
    
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    
    for src in source_paths:
        src_path = Path(src)
        if not src_path.exists():
            continue
        
        dest = target / src_path.name
        
        if dest.exists():
            if existing_dir_behavior == "skip":
                logger.warning(f"Skip existing: {dest}")
                continue
            elif dest.is_dir() and src_path.is_dir():
                shutil.copytree(src_path, dest, dirs_exist_ok=True)
                if action == "move":
                    shutil.rmtree(src_path)
                continue
        
        try:
            if action == "move":
                shutil.move(str(src_path), str(dest))
            else:
                if src_path.is_dir():
                    shutil.copytree(src_path, dest)
                else:
                    shutil.copy2(src_path, dest)
        except Exception as e:
            logger.error(f"Failed to {action} {src_path} to {dest}: {e}")


def get_source_paths_interactively() -> List[str]:
    """Interactively get source directory path."""
    paths = []
    console.print("[bold cyan]请输入要分类的目录路径[/bold cyan]")
    
    while True:
        path_str = Prompt.ask("路径", default="")
        if not path_str:
            break
        
        path = Path(path_str)
        if path.is_dir():
            paths.append(str(path))
            break
        else:
            console.print(f"[red]目录不存在: {path_str}[/red]")
    
    return paths


@app.command()
def classify(
    path: Optional[Path] = typer.Argument(None, help="要分类的目录路径"),
    keyword: str = typer.Option("", "--keyword", "-k", help="关键词(如already)"),
    wait_keyword: str = typer.Option("", "--wait", "-w", help="wait文件夹名称"),
    action: str = typer.Option("", "--action", "-a", help="操作类型: move/copy"),
    existing_dir: str = typer.Option("", "--existing-dir", "-e", help="目录已存在时的处理方式: merge/skip"),
):
    """快速分类: 递归查找包含关键词的文件夹，将同级其他文件夹移动到wait目录"""
    setup_logger()
    
    interactive_mode = not path or not keyword or not wait_keyword or not action
    
    if interactive_mode:
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]       快速分类工具 - 引导模式       [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        
        if not path:
            while True:
                path_str = Prompt.ask("[bold cyan]请输入要分类的目录路径[/bold cyan]")
                if path_str:
                    path = Path(path_str)
                    if path.is_dir():
                        break
                    console.print(f"[red]目录不存在: {path_str}[/red]")
                else:
                    console.print("[red]请输入有效路径[/red]")
        
        if not keyword:
            keyword = Prompt.ask(
                "[bold cyan]请输入关键词[/bold cyan] (用于查找目标文件夹)",
                default="already"
            )
        
        if not wait_keyword:
            wait_keyword = Prompt.ask(
                "[bold cyan]请输入wait文件夹名称[/bold cyan] (其他文件夹移动到此目录)",
                default="wait"
            )
        
        if not action:
            action = Prompt.ask(
                "[bold cyan]请选择操作类型[/bold cyan]",
                choices=["move", "copy"],
                default="move"
            ).lower()
        
        if not existing_dir:
            existing_dir = Prompt.ask(
                "[bold cyan]目录已存在时的处理方式[/bold cyan]",
                choices=["merge", "skip"],
                default="merge"
            ).lower()
    
    if not path or not path.is_dir():
        console.print(f"[red]目录不存在: {path}[/red]")
        raise typer.Exit(code=1)
    
    if action not in {"move", "copy"}:
        action = "move"
    
    if existing_dir not in {"merge", "skip"}:
        existing_dir = "merge"
    
    console.print(f"\n[bold]开始快速分类[/bold]")
    console.print(f"  目录: {path}")
    console.print(f"  关键词: {keyword}")
    console.print(f"  wait文件夹: {wait_keyword}")
    console.print(f"  操作: {action}")
    console.print(f"  已存在处理: {existing_dir}")
    
    already_count, wait_count = _quick_classify_by_keyword(
        path,
        keyword,
        wait_keyword=wait_keyword,
        action=action,
        existing_dir_behavior=existing_dir,
    )
    
    console.print(f"\n[bold green]分类完成[/bold green]")
    console.print(f"  处理了 {already_count} 个关键词文件夹")
    console.print(f"  移动了 {wait_count} 个项目到 {wait_keyword}/")


if __name__ == "__main__":
    app()
