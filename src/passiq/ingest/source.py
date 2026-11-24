from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from passiq.paths import project_root

STATIC_FILES = {
    "competitions": "competitions.json",
    "matches": "matches/43/106.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(root: Path | None = None) -> dict:
    root = root or project_root()
    return json.loads((root / "manifests" / "source_data.json").read_text(encoding="utf-8"))


def save_manifest(manifest: dict, root: Path | None = None) -> None:
    root = root or project_root()
    target = root / "manifests" / "source_data.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def raw_path(relative_path: str, root: Path | None = None) -> Path:
    return (root or project_root()) / "data" / "raw" / relative_path


def fetch_file(relative_path: str, *, manifest: dict, root: Path | None = None) -> dict:
    """Fetch one immutable source file and record a checksum; reuse verified local copies."""
    root = root or project_root()
    target = raw_path(relative_path, root)
    known = manifest.setdefault("files", {}).get(relative_path)
    if target.exists() and known and sha256_file(target) == known["sha256"]:
        return {**known, "status": "verified-existing"}

    url = f"{manifest['source']['raw_base_url']}/{relative_path}"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".partial")
    with urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)
    temporary.replace(target)
    record = {
        "sha256": sha256_file(target),
        "url": url,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": manifest["source"]["commit"],
    }
    manifest["files"][relative_path] = record
    return {**record, "status": "downloaded"}


def match_ids_for_profile(profile: str, manifest: dict, root: Path | None = None) -> list[int]:
    configured = manifest["profiles"][profile]
    if isinstance(configured, list):
        return configured
    matches_path = raw_path(STATIC_FILES["matches"], root)
    if not matches_path.exists():
        fetch_file(STATIC_FILES["matches"], manifest=manifest, root=root)
    matches = json.loads(matches_path.read_text(encoding="utf-8"))
    return [int(match["match_id"]) for match in matches]


def fetch_profile(profile: str, root: Path | None = None) -> list[dict]:
    root = root or project_root()
    manifest = load_manifest(root)
    results = [fetch_file(path, manifest=manifest, root=root) for path in STATIC_FILES.values()]
    match_ids = match_ids_for_profile(profile, manifest, root)
    for match_id in match_ids:
        for relative_path in (f"events/{match_id}.json", f"three-sixty/{match_id}.json"):
            record = fetch_file(relative_path, manifest=manifest, root=root)
            results.append({"path": relative_path, **record})
    save_manifest(manifest, root)
    return results

