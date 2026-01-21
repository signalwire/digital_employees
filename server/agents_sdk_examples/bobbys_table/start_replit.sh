#!/bin/bash

# Exit on any error
set -e

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if init_db.py exists
if [ ! -f "init_db.py" ]; then
    echo "Error: init_db.py not found."
    exit 1
fi

# Initialize the database
echo "Running init_db.py to initialize the database..."
python init_db.py

# Check if init_test_data.py exists
if [ -f "init_test_data.py" ]; then
    echo "Running init_test_data.py to load test data..."
    python init_test_data.py
else
    echo "init_test_data.py not found, skipping test data loading..."
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found."
    exit 1
fi

# Run the application on the correct host and port for Autoscale deployment
echo "Starting the application..."

python app.py
