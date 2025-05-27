import sqlite3
import hashlib
import secrets
import os

def hash_password(password: str):
    """Generate a salt and SHA-256 hash for the given password."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return pw_hash, salt

def init_db():
    # Remove existing database if it exists
    if os.path.exists('zen_cable.db'):
        os.remove('zen_cable.db')
        print("Removed existing database")

    db = sqlite3.connect('zen_cable.db')
    db.row_factory = sqlite3.Row

    # --- table creation ---
    db.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            first_name TEXT,
            last_name TEXT
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS customer_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (service_id) REFERENCES services (id),
            UNIQUE(customer_id, service_id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS modems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            mac_address TEXT NOT NULL,
            make TEXT,
            model TEXT,
            status TEXT DEFAULT 'online',
            last_seen TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            due_date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            technician_id INTEGER,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            notes TEXT,
            priority TEXT DEFAULT 'medium',
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sms_reminder BOOLEAN DEFAULT 1,
            job_number TEXT UNIQUE,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (technician_id) REFERENCES technicians (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS appointment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS appointment_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (appointment_id) REFERENCES appointments (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS service_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            action_date DATE NOT NULL,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expiry TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS modem_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    # --- seed test user with specific 6-digit ID ---
    TEST_CUSTOMER_ID = 8675309
    TEST_EMAIL       = "test@example.com"
    TEST_PASSWORD    = "password123"
    pw_hash, pw_salt = hash_password(TEST_PASSWORD)

    db.execute('''
        INSERT OR REPLACE INTO customers
          (id, name, email, phone, address, password_hash, password_salt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        TEST_CUSTOMER_ID,
        "Test User",
        TEST_EMAIL,
        "000-000-0000",
        "123 Test Lane",
        pw_hash,
        pw_salt
    ))

    db.commit()
    db.close()

    # Print credentials for your reference
    print("\n=== Test Account Credentials ===")
    print(f"Customer ID: {TEST_CUSTOMER_ID:06d}")
    print(f"Email:       {TEST_EMAIL}")
    print(f"Password:    {TEST_PASSWORD}")
    print("==============================\n")

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
