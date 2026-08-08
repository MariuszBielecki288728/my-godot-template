"""Repository-root discovery for commands run from the installed tools package."""

from pathlib import Path


def discover_repository_root(start: Path | None = None) -> Path:
    """Find the outer Godot repository from a path inside it."""
    candidate = (start or Path(__file__)).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / "project.godot").is_file() and (directory / "dependencies.json").is_file():
            return directory
    raise RuntimeError(
        "Could not find the Godot repository root (expected project.godot and dependencies.json)."
    )
