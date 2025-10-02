import typer
from pathlib import Path
import pyperclip
import subprocess
import yaml
from typing import List
from rich.prompt import Prompt
from rich.console import Console
from rich.table import Table
from .generator import OrganizefGenerator
from .input import get_paths, get_path

app = typer.Typer()

@app.command()
def run(
    profile: str = typer.Option(None, help="Profile name from config.toml"),
    paths: List[str] = typer.Option(None, "--path", "-p", help="Path(s) to organize (repeatable option)"),
    interactive: bool = typer.Option(False, help="Use interactive mode to select multiple paths"),
    simulate: bool = typer.Option(False, help="Run in simulation mode"),
    dry_run: bool = typer.Option(False, help="Only generate and print YAML, do not run organize"),
    config_path: Path = typer.Option(Path(__file__).parent / "config.toml", help="Path to config.toml"),
    rules_dir: Path = typer.Option(Path(__file__).parent / "rules", help="Path to rules directory")
):
    generator = OrganizefGenerator(config_path, rules_dir)
    console = Console()

    # Select profile if not provided
    if profile is None:
        profiles = list(generator.config['profiles'].keys())
        if not profiles:
            typer.echo("No profiles found in config.toml")
            raise typer.Exit(1)
        
        colors = ["red", "green", "blue", "yellow", "magenta", "cyan", "bright_red", "bright_green", "bright_blue", "bright_yellow", "bright_magenta", "bright_cyan"]
        all_tags = sorted(set(tag for profile in generator.config['profiles'].values() for tag in profile.get('tags', [])))
        tag_colors = {tag: colors[i % len(colors)] for i, tag in enumerate(all_tags)}
        
        table = Table(title="Available Profiles")
        table.add_column("No.", style="cyan", no_wrap=True)
        table.add_column("Profile", style="magenta" , overflow="fold")
        table.add_column("Tags", style="white", overflow="fold")
        table.add_column("Description", style="white", overflow="fold")
        
        for i, p in enumerate(profiles, 1):
            desc = generator.config['profiles'][p].get('description', '')
            tags = generator.config['profiles'][p].get('tags', [])
            tags_str = ", ".join(f"[{tag_colors.get(tag, 'white')}]{tag}[/{tag_colors.get(tag, 'white')}]" for tag in tags)
            table.add_row(str(i), p, tags_str, desc)
        
        console.print(table)
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles)+1)])
        profile = profiles[int(choice) - 1]

    # Get paths
    if interactive:
        selected_paths = get_paths()
    elif paths:
        selected_paths = []
        for provided_path in paths:
            normalized = Path(provided_path.strip('"')).expanduser()
            if not normalized.exists():
                console.print(f"[red]路径无效: {normalized}[/red]")
                raise typer.Exit(1)
            selected_paths.append(str(normalized))
    else:
        selected_paths = get_paths()

    if not selected_paths:
        typer.echo("No paths selected")
        raise typer.Exit(1)

    yaml_content = generator.generate_yaml(profile, selected_paths)

    if dry_run:
        typer.echo(yaml_content)
        return

    # Write to temp file
    temp_yaml = Path("organize_config.yaml")
    with open(temp_yaml, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    # Run organize
    cmd = ["organize", "sim" if simulate else "run", str(temp_yaml)]
    subprocess.run(cmd)

if __name__ == "__main__":
    app()