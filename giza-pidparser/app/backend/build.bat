@echo off
setlocal

:: Ensure Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH. Exiting...
    exit /b 1
)

:: Define the base directory where manage.py is located
set "BASE_DIR=%~dp0"
echo Base directory is "%BASE_DIR%"

:: Delete existing virtual environment if it exists
IF EXIST "C:\temp\temp_venv" (
    echo Deleting existing virtual environment...
    rmdir /S /Q "C:\temp\temp_venv"
    if errorlevel 1 (
        echo Failed to delete existing virtual environment. Exiting...
        exit /b 1
    )
)

:: Create a new virtual environment in C:\temp
echo Creating new virtual environment in C:\temp...
python -m venv "C:\temp\temp_venv"
if errorlevel 1 (
    echo Failed to create virtual environment. Exiting...
    exit /b 1
)

:: Wait for a few seconds to ensure the virtual environment setup is complete
timeout /t 5 /nobreak >nul

:: Check if activation script exists
set count=0
:check_activation
if exist "C:\temp\temp_venv\Scripts\activate.bat" (
    echo Activation script found.
) else (
    set /a count+=1
    if %count% geq 10 (
        echo Activation script not found after multiple attempts. Exiting...
        exit /b 1
    )
    echo Waiting for activation script to be created...
    timeout /t 1 /nobreak >nul
    goto check_activation
)

:: Activate the virtual environment
echo Activating virtual environment...
call "C:\temp\temp_venv\Scripts\activate.bat"
if errorlevel 1 (
    echo Failed to activate virtual environment. Exiting...
    exit /b 1
)

:: Upgrade pip, setuptools, and wheel
echo Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo Failed to upgrade pip, setuptools, or wheel. Exiting...
    exit /b 1
)

:: Navigate to the AI-service folder where requirements.txt is located
cd /d "%BASE_DIR%\..\AI-service"
if errorlevel 1 (
    echo Failed to navigate to the AI-service directory. Exiting...
    exit /b 1
)

:: Install dependencies from requirements.txt
echo Installing dependencies...
pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies. Exiting...
    exit /b 1
)

:: Navigate back to the base directory (where manage.py is located)
cd /d "%BASE_DIR%"
if errorlevel 1 (
    echo Failed to navigate to the base directory. Exiting...
    exit /b 1
)

:: Run Django migrations
echo Running Django migrations...
python manage.py migrate
if errorlevel 1 (
    echo Django migrations failed. Exiting...
    exit /b 1
)

:: Start Django server
echo Starting Django server...
python manage.py runserver
if errorlevel 1 (
    echo Failed to start Django server. Exiting...
    exit /b 1
)

pause
