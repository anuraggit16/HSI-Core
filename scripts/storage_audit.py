from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOT = ROOT / "scans"
LOG_ROOT = ROOT / "logs"
CACHE_ROOTS = ["temp", "cache", ".cache", "build", "dist"]
CUBE_EXTENSIONS = {".npy", ".npz", ".h5", ".hdf5", ".mat"}
RAW_EXTENSIONS = {".tif", ".tiff", ".raw"}


def iter_files(path: Path):
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in files:
            yield Path(root) / name


def size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(file.stat().st_size for file in iter_files(path) or [])


def fmt_size(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def tracked_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def scan_sessions() -> list[dict]:
    sessions = []
    if not SCAN_ROOT.exists():
        return sessions
    for session in sorted([p for p in SCAN_ROOT.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        files = list(iter_files(session) or [])
        cube_files = [p for p in files if p.suffix.lower() in CUBE_EXTENSIONS]
        raw_files = [p for p in files if p.suffix.lower() in RAW_EXTENSIONS]
        sessions.append(
            {
                "name": session.name,
                "size": sum(p.stat().st_size for p in files),
                "files": len(files),
                "cube_files": cube_files,
                "raw_files": raw_files,
                "has_npy": any(p.suffix.lower() == ".npy" for p in cube_files),
                "has_npz": any(p.suffix.lower() == ".npz" for p in cube_files),
            }
        )
    return sorted(sessions, key=lambda item: item["size"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated HSI-Core storage without deleting data.")
    parser.add_argument("--top", type=int, default=20, help="Number of scan sessions to show.")
    args = parser.parse_args()

    tracked = tracked_files()
    sessions = scan_sessions()

    print("HSI-Core storage audit")
    print(f"Repository: {ROOT}")
    print(f"Total scans size: {fmt_size(size_bytes(SCAN_ROOT))}")
    print(f"Total logs size: {fmt_size(size_bytes(LOG_ROOT))}")
    for name in CACHE_ROOTS:
        path = ROOT / name
        print(f"Total {name}/ size: {fmt_size(size_bytes(path))}")

    print("\nLargest scan sessions")
    for session in sessions[: max(1, args.top)]:
        duplicate = "YES" if session["has_npy"] and session["has_npz"] else "no"
        print(
            f"- {session['name']}: {fmt_size(session['size'])}, "
            f"files={session['files']}, raw_images={len(session['raw_files'])}, "
            f"cube_files={len(session['cube_files'])}, duplicate_npy_npz={duplicate}"
        )
        for cube in sorted(session["cube_files"], key=lambda p: p.stat().st_size, reverse=True):
            print(f"  cube: {cube.relative_to(ROOT)} ({fmt_size(cube.stat().st_size)})")

    print("\nTracked generated-file warnings")
    generated_prefixes = ("scans/", "data/", "logs/", "temp/", "cache/", ".cache/", "dist/", "build/", ".venv/", "venv/", ".codex/")
    generated_suffixes = (".npy", ".npz", ".tif", ".tiff", ".raw", ".h5", ".hdf5", ".mat", ".log", ".jsonl", ".pyc")
    warnings = [
        path for path in sorted(tracked)
        if path.startswith(generated_prefixes) or path.endswith(generated_suffixes)
    ]
    if not warnings:
        print("- none")
    else:
        for path in warnings[:100]:
            print(f"- {path}")
        if len(warnings) > 100:
            print(f"- ... {len(warnings) - 100} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
