"""
OrganizeFolder 主包的命令行入口点
使用 Typer 实现 Git 风格的子命令结构
"""
import sys
import typer
from typing import List, Optional
from pathlib import Path
import importlib

from organizef.interactive import run_interactive

# 创建 Typer 应用
app = typer.Typer(
    help="OrganizeFolder - 一个功能丰富的文件夹整理工具，用于解散嵌套文件夹、清理空文件夹和备份文件等",
    no_args_is_help=False,
    add_completion=False,
    invoke_without_command=True
)

# 添加子命令组
clean_app = typer.Typer(help="清理文件夹 (删除空文件夹和备份文件)")
dissolve_app = typer.Typer(help="解散嵌套文件夹")
migrate_app = typer.Typer(help="迁移文件")
merge_app = typer.Typer(help="合并同名的part文件夹")

app.add_typer(clean_app, name="clean")
app.add_typer(dissolve_app, name="dissolve")
app.add_typer(migrate_app, name="migrate")
app.add_typer(merge_app, name="merge")

def version_callback(value: bool):
    """版本信息回调函数"""
    if value:
        # typer.echo(f"OrganizeFolder 版本 {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="显示版本信息并退出", callback=version_callback),
):
    """OrganizeFolder 主命令"""
    # 当没有子命令被调用时，自动运行交互式界面
    if ctx.invoked_subcommand is None:
        run_interactive()

# 删除这个命令，由回调函数处理无参数情况

@clean_app.callback(invoke_without_command=True)
def clean_main(ctx: typer.Context):
    """清理文件夹 (调用 cleanf 包的功能)"""
    if ctx.invoked_subcommand is None:
        try:
            # 导入 cleanf 子包的 app
            from cleanf.__main__ import app as clean_app
            typer.echo("正在执行清理操作...")
            clean_app()
        except ImportError as e:
            typer.echo(f"错误：无法导入 cleanf 包: {e}", err=True)
            raise typer.Exit(code=1)

@dissolve_app.callback(invoke_without_command=True)
def dissolve_main(ctx: typer.Context):
    """解散嵌套文件夹 (调用 dissolvef 包的功能)"""
    if ctx.invoked_subcommand is None:
        try:
            # 导入 dissolvef 子包的 app
            from dissolvef.__main__ import app as dissolve_app
            typer.echo("正在执行解散嵌套文件夹操作...")
            dissolve_app()
        except ImportError as e:
            typer.echo(f"错误：无法导入 dissolvef 包: {e}", err=True)
            raise typer.Exit(code=1)

@migrate_app.callback(invoke_without_command=True)
def migrate_main(ctx: typer.Context):
    """迁移文件 (调用 migratef 包的功能)"""
    if ctx.invoked_subcommand is None:
        try:
            # 导入 migratef 子包的 app
            from migratef.pipe.__main__ import app as migrate_app
            typer.echo("正在执行文件迁移操作...")
            migrate_app()
        except ImportError as e:
            typer.echo(f"错误：无法导入 migratef 包: {e}", err=True)
            raise typer.Exit(code=1)

@merge_app.callback(invoke_without_command=True)
def merge_main(ctx: typer.Context):
    """合并同名的part文件夹 (调用 mergef 包的功能)"""
    if ctx.invoked_subcommand is None:
        try:
            # 导入 mergef 子包的 app
            from mergef.__main__ import app as merge_app
            typer.echo("正在执行part文件夹合并操作...")
            merge_app()
        except ImportError as e:
            typer.echo(f"错误：无法导入 mergef 包: {e}", err=True)
            raise typer.Exit(code=1)


if __name__ == "__main__":
    try:
        # 直接使用 Typer 的 app() 函数作为入口点
        app()
    except KeyboardInterrupt:
        typer.echo("\n操作已取消")
    except Exception as e:
        typer.echo(f"发生错误: {e}", err=True)
        sys.exit(1)