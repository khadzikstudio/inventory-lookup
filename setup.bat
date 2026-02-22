@echo off
echo ========================================
echo  Inventory Lookup - Setup
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
    echo ERROR: Python not found. Install Python 3.12 from python.org
    pause
    exit /b 1
)

echo Using: %PYTHON%
%PYTHON% --version
echo.
echo Installing dependencies (this may take several minutes)...
echo.
pip install -r requirements.txt
echo.
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)
echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Update image_folder in config.yaml to your local image path
echo   2. Run: python import_data.py
echo   3. Run: start.bat
echo.
pause
