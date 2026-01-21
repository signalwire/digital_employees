import sqlite3
import os
from datetime import datetime

def init_db():
    """Initialize the database with schema and sample data."""
    db_path = 'instance/restaurant.db'
    
    # Create instance directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    # Clear existing data first
    cursor.execute('DELETE FROM order_items')
    cursor.execute('DELETE FROM orders')
    cursor.execute('DELETE FROM reservations')
    cursor.execute('DELETE FROM tables')
    cursor.execute('DELETE FROM menu_items')
    
    # Add sample tables
    tables = [
        (1, 2, 'available', 'Window'),
        (2, 4, 'available', 'Center'),
        (3, 6, 'available', 'Back'),
        (4, 2, 'available', 'Window'),
        (5, 4, 'available', 'Center'),
        (6, 8, 'available', 'Private Room')
    ]
    cursor.executemany('INSERT INTO tables (table_number, capacity, status, location) VALUES (?, ?, ?, ?)', tables)
    
    # Add sample menu items
    menu_items = [
        ('Classic Burger', 'Angus beef patty with lettuce, tomato, and special sauce', 12.99, 'Main Course'),
        ('Caesar Salad', 'Fresh romaine lettuce with parmesan and croutons', 8.99, 'Appetizer'),
        ('Chocolate Cake', 'Rich chocolate cake with ganache', 6.99, 'Dessert'),
        ('House Wine', 'Red wine blend', 7.99, 'Beverage'),
        ('Garlic Bread', 'Toasted bread with garlic butter', 4.99, 'Appetizer')
    ]
    cursor.executemany('INSERT INTO menu_items (name, description, price, category) VALUES (?, ?, ?, ?)', menu_items)
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")

if __name__ == '__main__':
    init_db() 