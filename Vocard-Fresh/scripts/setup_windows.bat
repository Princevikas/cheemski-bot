@echo off
REM =============================================================================
REM Cheemski Bot - Windows Installation Script
REM =============================================================================
REM This script sets up the bot on Windows
REM Run as Administrator for best results
REM =============================================================================

echo.
echo ================================================
echo   Cheemski Bot - Windows Installation
echo ================================================
echo.

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Please download Python 3.11+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Check for Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Java not found - needed for Lavalink
    echo Download Java 17+ from https://adoptium.net/
)

echo.
echo [1/4] Creating virtual environment...
python -m venv venv

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/4] Setting up configuration...
if not exist settings.json (
    if exist "settings Example.json" (
        copy "settings Example.json" settings.json
        echo [OK] Created settings.json from template
        echo [WARNING] Edit settings.json with your bot token!
    )
) else (
    echo [OK] settings.json already exists
)

REM Create run batch file
echo @echo off > run.bat
echo call venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat
echo pause >> run.bat
echo [OK] Created run.bat

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo Next steps:
echo   1. Edit settings.json with your Discord bot token
echo   2. Set up MongoDB (Atlas or local)
echo   3. Run Lavalink: cd lavalink ^& java -jar Lavalink.jar
echo   4. Run bot: run.bat
echo.
pause
