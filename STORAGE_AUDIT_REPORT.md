# HSI-Core Storage Audit Report

Date: 2026-06-19

## What I Understood

HSI-Core is producing very large local data folders, with current scan output around 40 GB. The goal is to reduce duplicate generated storage and memory pressure without removing scientific acquisition features, fake-scanning, or changing Basler/Thorlabs hardware behavior.

## Files And Subsystems Affected

- Scan acquisition storage: `acquisition/scan.py`
- Cube assembly and cube API backing store: `acquisition/data_cube.py`
- Legacy dataset manager: `acquisition/dataset.py`
- Logging persistence: `acquisition/error_logger.py`
- Storage configuration: `config.py`
- Cube HTTP APIs: `server_enhanced.py`
- Cube frontend behavior: `static/app.js`
- Git hygiene: `.gitignore`, git index
- Generated local folders: `scans/`, `logs/`, `dist/`, `venv/`, `.venv/`, `installer/`

## Largest Folders And File Types

Repository folder sizes observed:

- `.git`: about 40,808 MB
- `scans`: about 38,007 MB
- `dist`: about 8,454 MB
- `venv`: about 1,084 MB
- `.venv`: about 982 MB
- `installer`: about 930 MB
- `logs`: about 738 MB

Largest generated file types observed:

- `.npy`: about 17,644 MB across 108 files
- `.tiff`: about 16,452 MB across 7,508 files
- `.npz`: about 2,052 MB across 136 files
- `.mat`: about 1,404 MB across 557 files
- `.jsonl`: about 567 MB
- `.log`: about 58 MB

## Git Tracking Audit

Currently tracked generated/local-heavy files found:

- `logs/error_knowledge_base.md`, about 131 MB
- `.codex/environments/environment.toml`
- `acquisition/__pycache__/*.pyc`

Currently untracked but heavy/generated folders include `scans/`, `dist/`, `venv/`, `.venv/`, `installer/`, and most runtime logs. The `.git` folder being about 40 GB suggests generated files were likely committed historically or packed in repository history, even though current `scans/` files are not tracked.

## Current Disk Usage Behavior

`acquisition/scan.py` preserves the scan workflow and writes, per scan:

- Real TIFF frames under `scans/<session>/images/` when `save_tiff` is enabled.
- PNG preview/export images under `scans/<session>/images/` when `save_png` is enabled.
- Per-frame metadata sidecars under `scans/<session>/metadata/`.
- Session metadata under `scans/<session>/metadata/metadata.json`.
- Cube output under `scans/<session>/cube/`.

`acquisition/data_cube.py::DataCubeManager.finalize_scan()` always creates `cube/data_cube.npy` with `np.lib.format.open_memmap()`. If `COMPRESS_CUBES` is enabled and the `.npy` is under `CUBE_COMPRESS_MAX_BYTES`, it also writes `cube/data_cube.npz`. The manifest still points to the `.npy` as the primary cube, making `.npz` an additional duplicate instead of the canonical output.

Observed sessions confirm this pattern. Large scan sessions contain hundreds or thousands of TIFF files plus a full `data_cube.npy`, and many also contain `data_cube.npz`.

## Current Memory Behavior

Positive behavior:

- `.npy` cube loading already uses `np.load(..., mmap_mode="r")` in `acquisition/data_cube.py::_load_cube_array()`.
- Cube APIs return PNG slice previews, spectra, or bounded sampled volume payloads instead of a raw full 3D cube payload.
- Frontend slice and spectrum caches are bounded to 24 entries.

Pressure points:

- `.npz` cubes are not supported by `DataCubeManager._is_supported_cube_file()` or `_load_cube_array()`, so compressed cubes are not treated as canonical analysis sources.
- `finalize_scan()` writes `.npy` first and uses `np.asarray(cube)` during `.npz` compression, which can put pressure on memory for large cubes.
- `get_cube_summary()` computes RGB and band previews from the loaded cube. For `.npy` this is memmap-backed; for `.npz` support, caching must avoid repeatedly decompressing the full archive.
- `acquisition/dataset.py::DatasetManager.load_dataset()` returns `data["cube"]` from `.npz`, which fully loads that cube into memory for the legacy dataset path.

## Frontend/API Behavior

`server_enhanced.py` exposes slice-oriented APIs:

- `/api/datasets/{name}/cube/spatial`
- `/api/datasets/{name}/cube/y-lambda`
- `/api/datasets/{name}/cube/x-lambda`
- `/api/datasets/{name}/cube/spectrum`
- `/api/datasets/{name}/cube/volume`

The frontend uses those slice/spectrum/volume endpoints. It does not appear to request a full raw 3D cube array. The `/api/datasets/{name}/cube` summary endpoint returns preview PNGs, profile, histogram, and metadata, not the raw cube.

## Log Behavior

`acquisition/error_logger.py` appends indefinitely to:

- `logs/system.log`
- `logs/hardware_log.jsonl`
- `logs/error_knowledge_base.md`

Observed sizes:

- `logs/hardware_log.jsonl`: about 567 MB
- `logs/error_knowledge_base.md`: about 131 MB
- `logs/system.log`: about 39 MB

There is no size-based rotation before this patch.

## Temporary/Cache/Build Behavior

Heavy generated/local folders exist and should remain local-only:

- `dist/`: about 8.5 GB
- `venv/` and `.venv/`: about 2.1 GB combined
- `installer/`: about 930 MB
- `__pycache__/` and `*.pyc`

No automatic cleanup policy was found for temp/cache/build folders. Cleanup must remain explicit and dry-run by default.

## Root Cause

Primary root causes:

1. Completed scans save raw TIFF/PNG stacks plus a full `.npy` cube, and sometimes a duplicate `.npz` cube.
2. Compressed `.npz` cubes are written as secondary output but not used as the canonical loader path.
3. Logs grow indefinitely, especially structured hardware JSONL and the Markdown error knowledge base.
4. Git index currently tracks generated/local files including `__pycache__`, `.codex`, and a large generated log knowledge base.
5. Build/runtime folders are large and need stronger ignore hygiene.

## Hardware Safety Impact

The storage issue does not require changing stage movement, camera capture, scan locking, homing, emergency stop, or WebSocket telemetry. The safe fix is limited to generated-file policy after frames are captured, cube loader behavior, log rotation, git hygiene, and explicit cleanup tooling. No hardware-control logic should be modified.

## Performance Impact

Expected improvements:

- New scans avoid keeping both full `.npy` and `.npz` by default.
- `.npy` remains memory-mapped when explicitly enabled.
- `.npz` becomes the canonical compressed output and is cached rather than repeatedly decompressed for every preview request.
- Logs are capped by rotation.
- Cleanup/audit scripts help identify generated storage pressure before it becomes a multi-GB surprise.

Tradeoff:

- Compressed `.npz` cannot be memory-mapped like `.npy`; it reduces disk usage but may require a full decompression when opened. The loader must therefore cache only one active compressed cube reference and keep API payloads slice/downsample oriented.

## Safe Fix Strategy

1. Update `.gitignore` for generated scan data, cubes, logs, envs, build artifacts, cache/temp, and Codex local files while keeping `.gitkeep` placeholders.
2. Remove already-tracked generated/local files from the git index only, leaving disk files untouched.
3. Add an explicit storage policy to `config.py`.
4. Make `.npz` the default canonical cube output, with `.npy` saved only when `keep_npy_cube` is true.
5. Keep raw TIFF frames by default and do not delete old scans automatically.
6. Support `.npz` in the cube loader and avoid repeated full loads by caching the active loaded cube context.
7. Add safe log rotation before append operations.
8. Add dry-run audit and cleanup scripts.
9. Update docs with real generated-data behavior and safety notes.

## Risks Before Patching

- Existing old scans may still contain duplicate `.npy` and `.npz`; the patch should not delete those automatically.
- `.npz` analysis requires full decompression when first opened, unlike memory-mapped `.npy`.
- Git history remains large even after index cleanup; shrinking `.git` history requires an explicit history-rewrite operation and is outside this safe patch.
- Existing user changes are present in the worktree; patching must avoid reverting unrelated work.
