@echo off
chcp 65001 > nul
title HTML2APK Studio — Build EXE

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   HTML2APK Studio — Build Portable EXE ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ── بررسی Python ──────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python پیدا نشد! Python 3.10+ نصب کن.
    pause & exit /b 1
)

REM ── نصب PyInstaller اگه نیاز بود ─────────────────────────
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] نصب PyInstaller ...
    python -m pip install pyinstaller
)

REM ── نصب دپندنسی‌های Python ───────────────────────────────
echo  [INFO] بررسی دپندنسی‌های Python ...
python -m pip install customtkinter Pillow --quiet

REM ── ساخت EXE ──────────────────────────────────────────────
echo  [INFO] ساخت EXE ...
echo.

python -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "HTML2APK_Studio" ^
    --add-data "android_template;android_template" ^
    --clean ^
    app.py

if errorlevel 1 (
    echo.
    echo  [ERROR] ساخت EXE شکست خورد!
    pause & exit /b 1
)

REM ── کپی tools/ کنار EXE ──────────────────────────────────
echo.
if exist "tools\" (
    echo  [INFO] کپی tools/ ...
    if exist "dist\HTML2APK_Studio\tools\" rmdir /s /q "dist\HTML2APK_Studio\tools"
    xcopy "tools\" "dist\HTML2APK_Studio\tools\" /E /I /Q /EXCLUDE:build_exe_exclude.txt 2>nul
    xcopy "tools\" "dist\HTML2APK_Studio\tools\" /E /I /Q 2>nul
    echo  [OK] tools/ کپی شد
) else (
    echo  [WARN] پوشه tools/ پیدا نشد.
    echo         setup_portable.py رو اول اجرا کن تا tools/ ساخته بشه.
)

REM ── نتیجه ─────────────────────────────────────────────────
echo.
echo  ═══════════════════════════════════════════
if exist "dist\HTML2APK_Studio\HTML2APK_Studio.exe" (
    echo  ✔  EXE آماده‌ست!
    echo.
    echo  مسیر: dist\HTML2APK_Studio\
    echo.
    echo  این پوشه رو zip کن و به دوستات بده.
    echo  فقط HTML2APK_Studio.exe رو اجرا کنن.
) else (
    echo  ✘  EXE ساخته نشد. خطاهای بالا رو بررسی کن.
)
echo  ═══════════════════════════════════════════
echo.
pause
