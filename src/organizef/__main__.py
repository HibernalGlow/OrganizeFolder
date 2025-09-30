import typer
from pathlib import Path
import pyperclip
import subprocess
import yaml
from rich.prompt import Prompt
from rich.console import Console
from .generator import OrganizefGenerator
from .input import get_paths, get_path

app = typer.Typer()

@app.command()
def run(
    profile: str = typer.Option(None, help="Profile name from config.toml"),
    path: str = typer.Option(None, help="Path to organize (default: clipboard)"),
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
        console.print("[bold blue]Available profiles:[/bold blue]")
        for i, p in enumerate(profiles, 1):
            desc = generator.config['profiles'][p].get('description', '')
            console.print(f"{i}. {p} - {desc}")
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles)+1)])
        profile = profiles[int(choice) - 1]

    # Get paths
    if interactive or (path is None and not interactive):
        paths = get_paths()
        if not paths:
            typer.echo("No paths selected")
            raise typer.Exit(1)
    else:
        paths = [path]

    yaml_content = generator.generate_yaml(profile, paths)

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