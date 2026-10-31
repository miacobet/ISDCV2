@echo off
title ISDC Decommissioning Cost Tool - Windows Installer
color 1F
echo.
echo ============================================================
echo  ISDC Decommissioning Cost Estimation Tool - Installer
echo  NEA/OECD ISDC 2012 (NEA No. 7088)
echo ============================================================
echo.

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Python is not installed or not on your PATH.
        echo  Install Python 3.9+ from https://www.python.org/downloads/
        echo  and tick "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON=py
    )
) else (
    set PYTHON=python
)
echo  Found Python.
echo.

echo [2/4] Upgrading pip...
%PYTHON% -m pip install --upgrade pip --quiet
echo  Done.
echo.

echo [3/4] Installing required packages (PyQt5, openpyxl, reportlab)...
%PYTHON% -m pip install PyQt5 openpyxl reportlab --quiet
if %errorlevel% neq 0 (
    echo  ERROR: Package installation failed. Try running as Administrator.
    pause
    exit /b 1
)
echo  Done.
echo.

echo [4/4] Creating launch shortcut...
(
    echo @echo off
    echo title ISDC Decommissioning Cost Estimation Tool
    echo cd /d "%%~dp0"
    echo %PYTHON% main.py
    echo if %%errorlevel%% neq 0 pause
) > "%~dp0Launch_Tool.bat"
echo  Launch_Tool.bat created.
echo.

color 2F
echo ============================================================
echo  Installation complete! Double-click Launch_Tool.bat to run.
echo ============================================================
echo.
choice /c YN /n /m "Launch now? (Y/N): "
if %errorlevel% equ 1 (
    cd /d "%~dp0"
    %PYTHON% main.py
)
pause
