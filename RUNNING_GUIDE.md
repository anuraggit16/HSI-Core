# HSI-Core Running Guide

## Running after copying project to a new PC

Windows virtual environments are machine-specific. Files such as
`.venv\pyvenv.cfg` and some launchers under `.venv\Scripts` contain absolute
paths to the Python installation that created them. Copying `.venv` from
another PC can therefore leave it pointing to an old Windows user profile.

HSI-Core requires Python 3.10 or newer. Python 3.12 is preferred for the lab
configuration. Install Python from python.org and tick **Add Python to PATH**
during installation.

From the project root, run:

```powershell
.\RUN_HSI_CORE.bat
```

The launcher resolves the project from its own location, tries `py -3.12`,
then `py -3`, then `python`, and prints the selected Python version and
executable. It validates `.venv\Scripts\python.exe` by running it. If the
environment is missing or still points to another PC, the launcher removes
only `.venv`, recreates it, and installs `requirements.txt`.

Do not copy or reuse `.venv` between PCs. Vendor device drivers and runtimes
for the Basler camera and Thorlabs controller must also be installed on the
new PC; package or driver errors are shown and are not silently ignored.

### Manual recovery

The safest manual recovery is:

```powershell
Remove-Item -Recurse -Force .venv
.\RUN_HSI_CORE.bat
```

This deletes only the generated project environment. It does not delete
source code, scans, datasets, or hardware configuration.

### Verify the active Python

Run the launcher check without starting the backend:

```powershell
.\RUN_HSI_CORE.bat --check
```

Confirm that `[PYTHON] Base executable` names the current PC's Python and that
`[VENV] Executable` points inside the current project folder. Neither line
should contain `C:\Users\sadhu`.

You can also verify the environment directly:

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
Get-Content .\.venv\pyvenv.cfg
```

## Dashboard access and Windows Firewall

Start HSI-Core from the project root:

```powershell
.\RUN_HSI_CORE.bat
```

The normal launcher opens the detected LAN dashboard by default and prints
both available addresses. To force the browser to use the same-PC loopback
address, run:

```powershell
.\RUN_HSI_CORE.bat --local
```

The local dashboard is:

```text
http://127.0.0.1:8000
```

The backend remains bound to `0.0.0.0:8000` so LAN access is possible, but
the backend health check continues to use the local address. If no active LAN
IPv4 address can be detected, browser launch safely falls back to the local
dashboard.

Access from another computer may require allowing Python/Uvicorn or inbound
TCP port 8000 through Windows Firewall. The launcher only prints this
guidance during normal startup; it does not change or disable firewall
settings.

LAN access should only be enabled on trusted lab/private networks. Do not
expose this server to public networks.

Run startup diagnostics without launching another backend:

```powershell
.\RUN_HSI_CORE.bat --check
```

The check reports the Python and venv executables, required imports, backend
host and port, local and LAN URLs, the PID using port 8000, and whether
`/api/status` returns HTTP 200.

Manual verification:

```powershell
netstat -ano | findstr :8000
```

Then open:

```text
http://127.0.0.1:8000/api/status
```

The expected result is HTTP 200 with the HSI-Core status JSON.

## Storage Management

Generated scan sessions are stored in `scans/` unless `SAVE_FOLDER` is changed
in `config.py`. Raw TIFF frames remain enabled by default for scientific
traceability. New cube assembly writes canonical compressed `data_cube.npz` and
only writes duplicate `data_cube.npy` when
`config.STORAGE_POLICY["keep_npy_cube"]` is set to `True`.

Run a non-destructive storage audit from the project root:

```powershell
.\.venv\Scripts\python.exe .\scripts\storage_audit.py
```

Preview cleanup of generated temp/cache/build folders:

```powershell
.\.venv\Scripts\python.exe .\scripts\cleanup_generated_data.py
```

Actually delete only those generated temp/cache/build files:

```powershell
.\.venv\Scripts\python.exe .\scripts\cleanup_generated_data.py --yes
```

Scan data is protected. It is only selected when `--delete-scans` is combined
with `--yes` after reviewing the dry-run output.

### Enable LAN firewall access explicitly

Open PowerShell as Administrator, change to the HSI-Core project folder, and
run:

```powershell
.\RUN_HSI_CORE.bat --allow-lan-firewall
```

This explicit mode creates only this inbound Windows Firewall rule:

- Name: `HSI-Core Dashboard TCP 8000`
- Protocol and port: TCP 8000
- Network profile: Private only

Normal `.\RUN_HSI_CORE.bat` startup does not require Administrator permission
and does not modify the firewall.

The equivalent manual Administrator command is:

```powershell
netsh advfirewall firewall add rule name="HSI-Core Dashboard TCP 8000" dir=in action=allow protocol=TCP localport=8000 profile=private
```

Check the lab PC address and listener with:

```powershell
ipconfig
netstat -ano | findstr :8000
```

Both devices must be connected to the same trusted lab network. Use the LAN
URL printed by the launcher, not an address copied from another PC or an old
network session.

If the launcher reports that the active Windows profile is `Public`, change
that trusted lab connection to `Private` in Windows network settings before
using the Private-profile firewall rule. The launcher does not change the
network profile automatically.
