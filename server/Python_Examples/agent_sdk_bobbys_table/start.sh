#!/bin/bash

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating new virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements with no cache
echo "Installing requirements..."
pip install --no-cache-dir -r requirements.txt

# Run the application
echo "Starting the application..."
python reservation_agent.py 