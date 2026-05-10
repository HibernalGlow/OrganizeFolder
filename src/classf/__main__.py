"""Pipeline CLI: samea -> crashu -> migratef."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from loguru import logger

app = typer.Typer(help="Run samea -> crashu -> migratef in one command")


def _infer_common_parent(source_paths: List[str]) -> Optional[Path]:
    """Infer a single common parent directory from source paths."""
    if not source_paths:
        return None
    parents = {Path(p).resolve().parent for p in source_paths}
    if len(parents) != 1:
        return None
    return next(iter(parents))


def _run_samea(
    *,
    clipboard: bool,
    path: Optional[List[str]],
    min_occurrences: int,
    ignore_blacklist: bool,
    centralize: bool,
    debug: bool,
) -> List[str]:
    try:
        import samea.__main__ as samea_main
    except Exception as exc:
        logger.error(f"samea import failed: {exc}")
        raise typer.Exit(code=1)

    paths: List[str] = []
    if path:
        paths = [samea_main.clean_path(p) for p in path if p]
    elif clipboard:
        paths = samea_main.get_paths_from_clipboard()

    if not paths:
        logger.warning("no valid samea paths")
        return []

    for p in paths:
        samea_main.process_directory(
            p,
            ignore_blacklist=ignore_blacklist,
            min_occurrences=min_occurrences,
            centralize=centralize,
            debug=debug,
        )

    return paths


def _collect_crashu_paths(
    *,
    auto_dir: Optional[str],
    source_paths: Optional[List[str]],
    similarity_threshold: Optional[float],
    output_choice: str,
) -> List[str]:
    try:
        from crashu.core.config import ConfigManager
        from crashu.core.folder_manager import FolderManager
        from crashu.core.output_manager import OutputManager
        import os
    except Exception as exc:
        logger.error(f"crashu import failed: {exc}")
        raise typer.Exit(code=1)

    config = ConfigManager().get_config()

    if not auto_dir:
        logger.error("crashu auto_dir is required")
        return []

    if not source_paths:
        source_paths = [config.default_source_path]
    similarity_threshold = (
        config.default_similarity_threshold
        if similarity_threshold is None
        else similarity_threshold
    )

    logger.info(f"crashu scanning: auto_dir={auto_dir} (target), source_paths={source_paths}")

    target_folder_names, target_folder_fullpaths = FolderManager.auto_get_target_folders(auto_dir)
    if not target_folder_names:
        logger.warning("crashu auto target folders not found")
        return []

    similar_folders = FolderManager.scan_similar_folders(
        source_paths,
        target_folder_names,
        target_folder_fullpaths,
        similarity_threshold,
        auto_get=True,
    )

    output_manager = OutputManager()
    return output_manager.generate_output_paths(
        similar_folders,
        output_choice,
        config.default_destination_path,
        auto_get=True,
    )


def _migrate_direct(
    paths: List[str],
    *,
    target_dir: Optional[str],
    action: str,
    existing_dir: str,
    classify: str,
) -> None:
    try:
        import migratef.__main__ as migrate_main
    except Exception as exc:
        logger.error(f"migratef import failed: {exc}")
        raise typer.Exit(code=1)

    if existing_dir not in {"merge", "skip"}:
        existing_dir = "merge"

    if classify in {"auto", "only"}:
        if target_dir:
            base_dir = Path(target_dir).parent
            already_dir = Path(target_dir)
        else:
            base_dir = _infer_common_parent(paths)
            if not base_dir:
                logger.error("classify mode requires all source paths in same parent dir or explicit --target")
                raise typer.Exit(code=1)
            already_dir = base_dir / "already"

        migrate_main.migrate_paths_directly(paths, str(already_dir), action=action, existing_dir_behavior=existing_dir)

        if classify == "auto":
            wait_dir = base_dir / "wait"
            wait_candidates = migrate_main._collect_wait_candidates(
                base_dir, paths, already_dir, wait_dir
            )
            if wait_candidates:
                migrate_main.migrate_paths_directly(wait_candidates, str(wait_dir), action=action, existing_dir_behavior=existing_dir)
    else:
        if not target_dir:
            logger.error("target directory required when classify is off")
            raise typer.Exit(code=1)
        migrate_main.migrate_paths_directly(paths, target_dir, action=action, existing_dir_behavior=existing_dir)


@app.command()
def run(
    target: Optional[Path] = typer.Option(None, "--target", "-t", help="Target already directory (optional when classify is auto/only)"),
    existing_dir: str = typer.Option(
        "merge",
        "--existing-dir",
        help="Direct mode existing dir policy: merge/skip",
        show_default=True,
    ),
    action: str = typer.Option("move", "--action", help="move or copy", show_default=True),
    classify: str = typer.Option(
        "auto",
        "--classify",
        help="Classify mode: off/auto/only. auto=move to already+wait, only=move to already only",
        show_default=True,
    ),
    samea_clipboard: bool = typer.Option(True, "--samea-clipboard/--no-samea-clipboard"),
    samea_path: Optional[List[str]] = typer.Option(None, "--samea-path"),
    samea_min_occurrences: int = typer.Option(1, "--samea-min-occurrences"),
    samea_ignore_blacklist: bool = typer.Option(False, "--samea-ignore-blacklist"),
    samea_centralize: bool = typer.Option(False, "--samea-centralize"),
    samea_debug: bool = typer.Option(False, "--samea-debug"),
    crashu_auto_dir: Optional[str] = typer.Option(None, "--crashu-auto-dir"),
    crashu_source: Optional[List[str]] = typer.Option(None, "--crashu-source"),
    crashu_similarity: Optional[float] = typer.Option(None, "--crashu-similarity"),
    crashu_output_choice: str = typer.Option("2", "--crashu-output-choice", help="1=source path, 2=target path"),
    skip_samea: bool = typer.Option(False, "--skip-samea"),
    skip_crashu: bool = typer.Option(False, "--skip-crashu"),
):
    """Run the pipeline and pass crashu paths internally to migratef."""
    if action not in {"move", "copy"}:
        logger.error("action must be move or copy")
        raise typer.Exit(code=1)
    if crashu_output_choice not in {"1", "2"}:
        logger.error("crashu output choice must be 1 or 2")
        raise typer.Exit(code=1)
    classify = classify.lower().strip()
    if classify not in {"off", "auto", "only"}:
        logger.error("classify must be off/auto/only")
        raise typer.Exit(code=1)

    samea_processed_paths: List[str] = []
    if not skip_samea:
        samea_processed_paths = _run_samea(
            clipboard=samea_clipboard,
            path=samea_path,
            min_occurrences=samea_min_occurrences,
            ignore_blacklist=samea_ignore_blacklist,
            centralize=samea_centralize,
            debug=samea_debug,
        )

    crashu_paths: List[str] = []
    if not skip_crashu:
        effective_auto_dir = crashu_auto_dir
        if not effective_auto_dir and samea_processed_paths:
            effective_auto_dir = samea_processed_paths[0]
        
        crashu_paths = _collect_crashu_paths(
            auto_dir=effective_auto_dir,
            source_paths=crashu_source,
            similarity_threshold=crashu_similarity,
            output_choice=crashu_output_choice,
        )

    if not crashu_paths:
        logger.warning("no crashu output paths to migrate")
        return

    _migrate_direct(
        crashu_paths,
        target_dir=str(target) if target else None,
        action=action,
        existing_dir=existing_dir,
        classify=classify,
    )


if __name__ == "__main__":
    app()
