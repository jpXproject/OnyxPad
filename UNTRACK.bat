@echo off
:: ============================================================
:: UNTRACK.bat — Hapus file build/cache dari tracking Git
:: (jalankan SEKALI saja setelah CLEANUP.bat)
::
:: Cara pakai: double-klik di dalam folder notepadblack\
:: Syarat: Git sudah terinstall dan PATH sudah diset
:: ============================================================

echo.
echo ============================================================
echo  OnyxPad — Hapus file dari Git tracking
echo ============================================================
echo.
echo Perintah ini akan menjalankan:
echo   git rm -r --cached build/ dist/ __pycache__/ .pytest_cache/
echo   git rm -r --cached docs/demo/frames/
echo.
set /p CONFIRM=Lanjutkan? (y/n): 
if /i not "%CONFIRM%"=="y" (
    echo Dibatalkan.
    pause
    exit /b
)

echo.
echo Menghapus dari Git index...
git rm -r --cached build/ 2>nul
git rm -r --cached dist/ 2>nul
git rm -r --cached docs/demo/frames/ 2>nul
git rm -r --cached .pytest_cache/ 2>nul
for /d /r . %%d in (__pycache__) do (
    git rm -r --cached "%%d" 2>nul
)

echo.
echo Membuat commit pembersihan...
git add .gitignore
git commit -m "chore: remove build artifacts and cache from tracking"

echo.
echo ============================================================
echo  Selesai! File sudah tidak dilacak Git lagi.
echo  Lain kali build/ dist/ __pycache__ tidak akan ikut commit.
echo ============================================================
echo.
pause
