#!/usr/bin/env python3
"""
SignalWire Dental Office Management System Setup Script
"""

import os
import sys
import subprocess
import secrets

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version}")

def install_requirements():
    """Install required Python packages"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)

def create_env_file():
    """Create .env file with user input"""
    print("\n🔧 Setting up environment configuration...")
    
    if os.path.exists('.env'):
        response = input("📝 .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("⏭️  Skipping .env file creation")
            return
    
    print("\n🔑 Please provide your SignalWire credentials:")
    print("(You can find these in your SignalWire Dashboard)")
    
    # Collect SignalWire credentials
    project_id = input("📋 SignalWire Project ID: ").strip()
    token = input("🔐 SignalWire Auth Token: ").strip()
    space = input("🌐 SignalWire Space (subdomain only, e.g., 'myspace'): ").strip()
    from_number = input("📞 From Phone Number (E.164 format, e.g., +14155551234): ").strip()
    
    # Generate secure secret key
    secret_key = secrets.token_urlsafe(32)
    
    # Optional fields
    print("\n🔧 Optional configuration (press Enter to skip):")
    project_url = input("🌍 Project URL (default: http://localhost:8080): ").strip() or "http://localhost:8080"
    http_username = input("👤 HTTP API Username (for SWAIG): ").strip() or "testuser"
    http_password = input("🔒 HTTP API Password (for SWAIG): ").strip() or "testpass"
    
    # Create .env file
    env_content = f"""# SignalWire Configuration
SIGNALWIRE_PROJECT_ID={project_id}
SIGNALWIRE_TOKEN={token}
SIGNALWIRE_SPACE={space}
FROM_NUMBER={from_number}

# Application Configuration
SECRET_KEY={secret_key}
PROJECT_URL={project_url}
HTTP_USERNAME={http_username}
HTTP_PASSWORD={http_password}

# Optional: Call-to-Call API (leave empty if not used)
C2C_API_KEY=
C2C_ADDRESS=
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created successfully")

def initialize_database():
    """Initialize the SQLite database"""
    print("\n🗄️  Initializing database...")
    try:
        # Import and initialize
        from app import app, init_db_if_needed
        with app.app_context():
            init_db_if_needed()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

def main():
    """Main setup function"""
    print("🦷 SignalWire Dental Office Management System Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_requirements()
    
    # Create .env file
    create_env_file()
    
    # Initialize database
    initialize_database()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Default Login Credentials:")
    print("   Patient: jane.doe@email.com / patient123")
    print("   Dentist: dr.smith@dentaloffice.com / dentist123")
    print("\n🚀 To start the application:")
    print("   python app.py")
    print("\n🌐 Then visit: http://127.0.0.1:8080")

if __name__ == "__main__":
    main() 