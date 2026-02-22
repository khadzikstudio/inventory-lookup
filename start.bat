@echo off
echo ========================================
echo  Inventory Lookup - Starting Server
echo ========================================
echo.

:: Find Python
set "PYTHON="
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    if exist "C:\Users\khadzik\AppData\Local\Programs\Python\Python312\python.exe" (
        set "PYTHON=C:\Users\khadzik\AppData\Local\Programs\Python\Python312\python.exe"
        set "PATH=C:\Users\khadzik\AppData\Local\Programs\Python\Python312;C:\Users\khadzik\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"
    )
)
if not defined PYTHON (
    echo ERROR: Python not found.
    pause
    exit /b 1
)

%PYTHON% serve.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server exited with an error.
    pause
)
