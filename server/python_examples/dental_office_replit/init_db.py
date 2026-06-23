import sqlite3
import os

def init_db():
    if os.path.exists('dental_office.db'):
        os.remove('dental_office.db')
    
    conn = sqlite3.connect('dental_office.db')
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
