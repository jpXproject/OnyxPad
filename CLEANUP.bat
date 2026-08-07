@echo off
:: ============================================================
:: CLEANUP.bat — Bersihkan file hasil build & cache dari folder
:: project OnyxPad sebelum dikemas / dikirim ke orang lain.
::
:: Cara pakai: double-klik file ini di dalam folder notepadblack\
:: ============================================================

echo.
echo ============================================================
echo  OnyxPad — Pembersih Folder Project
echo ============================================================
echo.
echo Folder yang akan dihapus:
echo   - build\
echo   - dist\
echo   - semua __pycache__\
echo   - .pytest_cache\
echo   - docs\demo\frames\
echo.
set /p CONFIRM=Lanjutkan? (y/n): 
if /i not "%CONFIRM%"=="y" (
    echo Dibatalkan.
    pause
    exit /b
)

echo.
echo Menghapus build\ ...
if exist build\ rd /s /q build\

echo Menghapus dist\ ...
if exist dist\ rd /s /q dist\

echo Menghapus semua __pycache__\ ...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)

echo Menghapus .pytest_cache\ ...
if exist .pytest_cache\ rd /s /q .pytest_cache\

echo Menghapus docs\demo\frames\ ...
if exist docs\demo\frames\ rd /s /q docs\demo\frames\

echo.
echo ============================================================
echo  Selesai! Folder sudah bersih.
echo ============================================================
echo.

:: Hapus file .bat ini sendiri setelah selesai (opsional)
:: del "%~f0"

pause
