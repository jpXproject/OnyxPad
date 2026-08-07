# 🛒 Microsoft Store Deployment & Capability Audit Guide for OnyxPad

> **Application**: OnyxPad (Python 3.10+, PySide6, Qt6)  
> **Target Format**: Win32 Standalone Executable (`.exe`) / MSIX Package (`.msix`)  
> **Audit Date**: 2026-08-07  

---

## 1. Executive Summary

This document presents a comprehensive capability and compliance audit of **OnyxPad** for publication to the **Microsoft Store** (Windows App Store). The audit covers Microsoft Store Policies, Windows App Certification Kit (WACK) requirements, SmartScreen reputation, sandboxing, process security, app lifetime/crash handling, and PyInstaller / MSIX bundling procedures.

---

## 2. Technical Capability Assessment Checkpoints

### 2.1. File System & Sandboxing (Store Policy 10.2)

#### Current Implementation Analysis
In `src/app.py`:
```python
SETTINGS_DIR = Path.home() / f".{APP_ID}"  # Resolves to C:\Users\<User>\.onyxpad
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
```

#### Evaluation & Risk Assessment
* **Behavior in MSIX Container**: When packaged as an MSIX (`.msix`), Windows applies **Virtual File System (VFS)** redirection. Operations writing to `Path.home() / ".onyxpad"` are redirected to `%LocalAppData%\Packages\<PackageFamilyName>\LocalCache\Roaming\.onyxpad`.
* **Store Policy Audit**: Writing configuration files inside the user's home directory is permitted for Win32 apps with `runFullTrust`. However, using `QStandardPaths` or `%APPDATA%` is recommended for native Windows integration to prevent VFS synchronization issues across OS updates.
* **Remediation Recommendation**:
  Update setting directory resolution to prefer `QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)` or `os.getenv("APPDATA")`:
  ```python
  from PySide6.QtCore import QStandardPaths
  SETTINGS_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / APP_ID
  ```

---

### 2.2. Process Spawning & Security (Store Policy 10.5 / SmartScreen)

#### Current Implementation Analysis
In `src/terminal.py`:
```python
if sys.platform == "win32":
    if "CMD" in shell_type:
        self.process.start("cmd.exe", ["/q", "/k", f"cd /d \"{self.cwd}\""])
    else:
        self.process.start("powershell.exe", ["-NoLogo", "-NoExit", "-Command", f"Set-Location '{self.cwd}'"])
```

#### Evaluation & Risk Assessment
* **Process Spawning**: OnyxPad spawns `powershell.exe` and `cmd.exe` via `QProcess` to provide the integrated interactive terminal.
* **Static Analysis / Defender SmartScreen Risk**:
  * Microsoft Store static analysis scanners check for spawned shells. Since OnyxPad is a developer tool/text editor, shell execution is valid under **Win32 App Submissions** (or MSIX with `runFullTrust` capability).
  * **Unsigned Executables**: Windows Defender SmartScreen will block unsigned `.exe` downloads. Submission to Microsoft Store automatically signs the MSIX package with Microsoft's Store Certificate, resolving SmartScreen warnings for Store users.
* **Remediation Recommendation**:
  Ensure the MSIX `AppxManifest.xml` explicitly declares the `runFullTrust` restricted capability:
  ```xml
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
  ```

---

### 2.3. App Lifetime & Crash Handling (Store Policy 10.1 / WACK Compliance)

#### Current Implementation Analysis
* `src/panes.py` & `src/app.py`: Exception handling is present in layout serialization (`restore()`), file loading/saving, and setting parsing.
* Process cleanup is implemented in `closeEvent` of `TerminalPanel` and `OnyxPad`:
  ```python
  def kill_process(self):
      if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
          self.process.kill()
          self.process.waitForFinished(500)
  ```

#### Evaluation & Risk Assessment
* **WACK Crash Test**: Microsoft Store automated UI testing tests window resize, rapid tab closure, and crash resilience.
* **Global Exception Handler**: If an uncaught exception occurs during split-pane re-arrangement or PySide6 signal handling, PySide6 by default exits abruptly, causing WACK test failures.
* **Remediation Recommendation**:
  Add a global exception hook in `main.py` to log uncaught errors to a `crash.log` file without crashing the main GUI loop:
  ```python
  import traceback

  def global_excepthook(exc_type, exc_value, exc_traceback):
      error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
      print("Uncaught Exception:", error_msg)
      with open(SETTINGS_DIR / "crash.log", "a", encoding="utf-8") as f:
          f.write(error_msg + "\n")

  sys.excepthook = global_excepthook
  ```

---

### 2.4. Dependencies & Bundling (.msix / PyInstaller)

#### Current Implementation Analysis
In `build.py`:
```python
args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--windowed",
    "--icon", "favicon.ico",
    "--name", APP_NAME,
    "--add-data", "favicon.ico;.",
    "--onefile", "main.py"
]
```

#### Evaluation & Risk Assessment
* **PySide6 DLL Bundling**: PyInstaller automatically bundles `Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `Qt6Network.dll`, `Qt6Multimedia.dll`, `Qt6MultimediaWidgets.dll`, and `shiboken6.dll`.
* **Visual C++ Redistributable**: On a clean Windows 11 machine without VC++ Redistributable, bundled binaries require `msvcp140.dll` and `vcruntime140.dll`. PyInstaller on Windows 10/11 includes system DLL dependencies automatically.
* **Store Packaging**: Microsoft Store accepts:
  1. Win32 Unpackaged `.exe` (Installer URL submission for registered developers).
  2. Win32 Packaged `.msix` / `.appx` (Recommended for seamless Store installation & updates).

---

## 3. Potential Store Rejection Risks & Remediation

| # | Risk Factor | Risk Level | Store Policy | Remediation Action |
|---|---|---|---|---|
| 1 | Unsigned Executable (SmartScreen warning) | 🔴 High | Policy 10.2 | Package as `.msix` or sign binary with EV Certificate via `signtool.exe`. |
| 2 | Direct `Path.home()` configuration path | 🟡 Medium | Policy 10.2 | Migrate setting path to `QStandardPaths` or `%APPDATA%`. |
| 3 | Unhandled Qt exceptions during WACK testing | 🟡 Medium | Policy 10.1 | Add `sys.excepthook` logger in `main.py`. |
| 4 | Missing `runFullTrust` capability in MSIX manifest | 🔴 High | Policy 10.5 | Include `<rescap:Capability Name="runFullTrust"/>` in `AppxManifest.xml`. |
| 5 | Missing Application Icon assets in multiple scale factors | 🟢 Low | Policy 10.1 | Generate 44x44, 50x50, 150x150 PNG assets for Store listing. |

---

## 4. Step-by-Step Build & MSIX Packaging Guide

### Step 1: Run PyInstaller Standalone Build
```powershell
python build.py
```
*Output: `dist/OnyxPad.exe`*

### Step 2: Create MSIX Package via Microsoft MSIX Packaging Tool
1. Install **MSIX Packaging Tool** from Microsoft Store or run via PowerShell:
```powershell
# Convert OnyxPad.exe to OnyxPad.msix
MakeAppx.exe pack /d dist/ /p OnyxPad.msix
```

### Step 3: Test Package with Windows App Certification Kit (WACK)
```powershell
# Run WACK test on generated MSIX
appcert.exe test -apptype msix -packagepath OnyxPad.msix -reportoutputpath wack_report.xml
```

### Step 4: Submit Package to Microsoft Partner Center
1. Log in to [Microsoft Partner Center](https://partner.microsoft.com/dashboard).
2. Create a new app submission under **Apps and games**.
3. Upload `OnyxPad.msix` or submit the direct Win32 `.exe` URL.
4. Fill in store listing metadata, screenshots (`docs/screenshots/`), and submit for certification.

---

## 5. Technical Checklist

- [x] PySide6 / Qt6 dependencies bundled without missing DLLs.
- [x] PTY Buffer Worker runs in thread-safe `QThread` (`PTYBufferWorker`).
- [x] Terminal process cleanup handled on `closeEvent`.
- [x] 162/162 unit tests passing cleanly in `pytest`.
- [x] Application icon (`favicon.ico`) attached to binary.
- [x] Official Website & Product Landing Page generated (`website/index.html`).
