@echo off
echo 🦷 SignalWire Dental Office Management System
echo ================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ⚠️  No .env file found!
    echo Please run: python setup.py
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements if needed
echo 📋 Checking dependencies...
pip install -r requirements.txt --quiet

REM Start the application
echo 🚀 Starting SignalWire Dental Office Management System...
echo.
echo 🌐 Application will be available at:
echo    http://127.0.0.1:8080
echo.
echo 👥 Default Login Credentials:
echo    Patient: jane.doe@email.com / patient123
echo    Dentist: dr.smith@dentaloffice.com / dentist123
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py 