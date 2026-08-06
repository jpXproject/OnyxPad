@echo off
REM Build OnyxPad onefile dengan PyInstaller
cd /d "%~dp0"
python build.py %*
pause
