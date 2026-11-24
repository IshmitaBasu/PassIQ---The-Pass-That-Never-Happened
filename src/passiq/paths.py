from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Locate the repository from this installed source tree or current directory."""
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "manifests" / "source_data.json").exists():
            return candidate
    return Path(__file__).resolve().parents[2]

