#!/usr/bin/env python3
"""
Script to manually create the database and tables.
"""

from app import app, db
from models import Reservation, Table, MenuItem, Order, OrderItem

def create_database():
    """Create the database and all tables"""
    import os
    with app.app_context():
        print("Creating database and tables...")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Current directory: {os.getcwd()}")
        
        try:
            db.create_all()
            print("✅ Database created successfully!")
            
            # Check if file exists in current directory
            current_path = os.path.join(os.getcwd(), 'restaurant.db')
            if os.path.exists('restaurant.db'):
                print("✅ Database file exists!")
                print(f"File size: {os.path.getsize('restaurant.db')} bytes")
            elif os.path.exists(current_path):
                print(f"✅ Database file exists at: {current_path}")
                print(f"File size: {os.path.getsize(current_path)} bytes")
            else:
                print("❌ Database file not found!")
                # List all files in current directory
                print("Files in current directory:")
                for file in os.listdir('.'):
                    if file.endswith('.db') or 'restaurant' in file.lower():
                        print(f"  - {file}")
                
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_database()
