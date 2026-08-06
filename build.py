"""Skrip build OnyxPad dengan PyInstaller.

Pemakaian:
    python build.py            # build satu file  -> dist/OnyxPad.exe
    python build.py folder     # build folder     -> dist/OnyxPad/OnyxPad.exe

Bisa juga double-click build.bat (memanggil skrip ini).
"""

import importlib.util
import os
import subprocess
import sys

from src.version import APP_NAME

# Windows memakai ';' sebagai pemisah path (Linux/macOS: ':')
ADD_DATA = "favicon.ico;."


def _check_pyinstaller():
    if importlib.util.find_spec("PyInstaller") is None:
        print("PyInstaller belum terpasang. Jalankan:  pip install pyinstaller")
        sys.exit(1)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "onefile"
    if mode not in ("onefile", "folder"):
        print(f"Mode tidak dikenal: {mode} (pilih 'onefile' atau 'folder')")
        sys.exit(2)

    _check_pyinstaller()

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--windowed",
        "--icon", "favicon.ico",
        "--name", APP_NAME,
        "--add-data", ADD_DATA,
    ]
    if mode == "folder":
        args.append("main.py")
        out = os.path.join("dist", APP_NAME, APP_NAME + ".exe")
    else:
        args += ["--onefile", "main.py"]
        out = os.path.join("dist", APP_NAME + ".exe")

    print(">>", " ".join(args))
    subprocess.run(args, check=True)
    print(f"\nSelesai! Hasil: {out}")


if __name__ == "__main__":
    main()
