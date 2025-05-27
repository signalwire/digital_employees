#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Create .env file if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Creating .env file..."
    cat > "$SCRIPT_DIR/.env" << EOL
SIGNALWIRE_PROJECT_ID=your_project_id
SIGNALWIRE_TOKEN=your_token
SIGNALWIRE_SPACE=your_space
HTTP_USERNAME=admin
HTTP_PASSWORD=admin123
HOST=127.0.0.1
PORT=8080
FLASK_ENV=development
EOL
    echo "Please update the .env file with your SignalWire credentials"
fi

# Initialize database
echo "Initializing database..."
cd "$SCRIPT_DIR"
python -c "
from app import init_db_if_needed
init_db_if_needed()
"

echo "Setup complete! You can now run the application with:"
echo "source $SCRIPT_DIR/venv/bin/activate"
echo "python $SCRIPT_DIR/app.py" 