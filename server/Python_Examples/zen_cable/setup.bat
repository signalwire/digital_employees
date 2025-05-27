@echo off
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist .env (
    echo Creating .env file...
    (
        echo SIGNALWIRE_PROJECT_ID=your_project_id
        echo SIGNALWIRE_TOKEN=your_token
        echo SIGNALWIRE_SPACE=your_space
        echo HTTP_USERNAME=admin
        echo HTTP_PASSWORD=admin123
        echo HOST=127.0.0.1
        echo PORT=8080
        echo FLASK_ENV=development
    ) > .env
    echo Please update the .env file with your SignalWire credentials
)

echo Initializing database...
python -c "from app import init_db_if_needed; init_db_if_needed()"

echo Setup complete! You can now run the application with:
echo venv\Scripts\activate.bat
echo python app.py 