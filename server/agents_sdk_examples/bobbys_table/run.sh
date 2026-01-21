#!/bin/bash

# Replit-optimized startup script for Bobby's Table Restaurant System
echo "🍽️  Bobby's Table Restaurant System - Replit Deployment"
echo "========================================================"

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found."
    exit 1
fi

# Initialize the database only once
echo "📊 Initializing database and loading test data..."
if [ -f "init_test_data.py" ]; then
    echo "Running init_test_data.py to load test data..."
    python init_test_data.py
else
    echo "init_test_data.py not found, running init_db.py instead..."
    if [ -f "init_db.py" ]; then
        echo "Running init_db.py to initialize the database..."
        python init_db.py
    else
        echo "❌ No database initialization script found!"
        exit 1
    fi
fi

echo "🚀 Starting the application..."
echo "🌐 Web Interface will be available at your Replit URL"
echo "📞 Voice Interface: /receptionist endpoint"
echo "🍳 Kitchen Dashboard: /kitchen endpoint"
echo "========================================================"

# Run the application on the correct host and port for Replit deployment
python app.py --host 0.0.0.0 --port 8080 