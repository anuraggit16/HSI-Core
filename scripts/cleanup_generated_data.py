from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STANDARD_TARGETS = ["temp", "cache", ".cache", "build", "dist"]
PROTECTED_NAMES = {
    ".git",
    "acquisition",
    "backend",
    "frontend",
    "static",
    "docs",
    "scripts",
    "config.py",
    "README.md",
    "CHANGELOG.md",
}


def iter_generated_files(path: Path):
    if not path.exists():
        return
    if path.is_file():
        if path.name != ".gitkeep":
            yield path
        return
    for root, dirs, files in os.walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in files:
            if name == ".gitkeep":
                continue
            yield Path(root) / name


def safe_target(name: str) -> Path:
    path = (ROOT / name).resolve()
    if ROOT not in path.parents and path != ROOT:
        raise ValueError(f"Refusing path outside repository: {path}")
    if path.name in PROTECTED_NAMES:
        raise ValueError(f"Refusing protected path: {path}")
    return path


def remove_empty_dirs(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        return
    for root, dirs, _ in os.walk(path, topdown=False):
        for name in dirs:
            candidate = Path(root) / name
            try:
                if candidate.name != ".git" and not any(candidate.iterdir()):
                    candidate.rmdir()
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run cleanup for generated HSI-Core files.")
    parser.add_argument("--yes", action="store_true", help="Actually delete eligible temp/cache/build files.")
    parser.add_argument("--delete-scans", action="store_true", help="Include scans/. Requires --yes.")
    args = parser.parse_args()

    targets = [safe_target(name) for name in STANDARD_TARGETS]
    if args.delete_scans:
        targets.append(safe_target("scans"))

    files = []
    for target in targets:
        files.extend(list(iter_generated_files(target) or []))
    skipped_parts = {".git", ".venv", "venv", "node_modules"}
    for pycache in ROOT.rglob("__pycache__"):
        if any(part in skipped_parts for part in pycache.relative_to(ROOT).parts):
            continue
        files.extend(list(iter_generated_files(pycache) or []))

    total = sum(path.stat().st_size for path in files if path.exists())
    mode = "DELETE" if args.yes else "DRY RUN"
    print(f"{mode}: {len(files)} files selected, {total / 1024 / 1024:.2f} MB")
    for path in files[:300]:
        print(path.relative_to(ROOT))
    if len(files) > 300:
        print(f"... {len(files) - 300} more files")

    if not args.yes:
        print("\nNo files deleted. Re-run with --yes to delete temp/cache/build files.")
        if not args.delete_scans:
            print("Scan data is never included unless --delete-scans is also provided.")
        return 0

    if args.delete_scans:
        print("Deleting scan data because both --delete-scans and --yes were provided.")

    for path in files:
        resolved = path.resolve()
        if ROOT not in resolved.parents:
            raise RuntimeError(f"Refusing path outside repository: {resolved}")
        if resolved.exists() and resolved.is_file():
            resolved.unlink()

    for target in targets:
        remove_empty_dirs(target)

    print("Cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
