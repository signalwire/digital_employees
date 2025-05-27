import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
import random

def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt

def init_test_data():
    db = sqlite3.connect('zen_cable.db')
    cursor = db.cursor()

    # Add test services if not present
    services = cursor.execute('SELECT * FROM services').fetchall()
    if not services:
        cursor.execute('INSERT INTO services (name, price, type) VALUES (?, ?, ?)', ('Basic Cable', 49.99, 'cable'))
        cursor.execute('INSERT INTO services (name, price, type) VALUES (?, ?, ?)', ('High-Speed Internet', 39.99, 'internet'))
        db.commit()
        services = cursor.execute('SELECT * FROM services').fetchall()

    # Create test customer account
    test_customer = {
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
        'phone': '+16504071011',
        'first_name': 'Test',
        'last_name': 'User',
        'address': '123 Test St, Test City, USA'
    }

    # Check if test customer exists
    existing = cursor.execute('SELECT id FROM customers WHERE email = ?', (test_customer['email'],)).fetchone()
    if not existing:
        password_hash, password_salt = hash_password(test_customer['password'])
        cursor.execute('''
            INSERT INTO customers (name, email, password_hash, password_salt, phone, first_name, last_name, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_customer['name'], test_customer['email'], password_hash, password_salt, 
              test_customer['phone'], test_customer['first_name'], test_customer['last_name'], test_customer['address']))
        customer_id = cursor.lastrowid
    else:
        customer_id = existing[0]

    # Add active services for the test customer
    for service in services:
        exists = cursor.execute('SELECT * FROM customer_services WHERE customer_id = ? AND service_id = ?', (customer_id, service[0])).fetchone()
        if not exists:
            cursor.execute('INSERT INTO customer_services (customer_id, service_id, status) VALUES (?, ?, ?)', (customer_id, service[0], 'active'))
    db.commit()

    # Add a modem
    cursor.execute(
        '''
        INSERT OR IGNORE INTO modems 
            (customer_id, mac_address, make, model, status, last_seen)
        VALUES (?, '00:11:22:33:44:55', 'Motorola', 'MB8600', 'online', CURRENT_TIMESTAMP)
        ''', (customer_id,)
    )

    # Add current and past billing
    current_date = datetime.now()
    due_date = current_date + timedelta(days=15)

    cursor.execute(
        '''
        INSERT OR IGNORE INTO billing (customer_id, amount, due_date, status)
        VALUES (?, 89.98, ?, 'pending')
        ''', (customer_id, due_date.strftime('%Y-%m-%d'))
    )

    past_billing = [
        (customer_id, 89.98, (current_date - timedelta(days=days)).strftime('%Y-%m-%d'), 'paid')
        for days in (30, 60, 90)
    ]
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO billing (customer_id, amount, due_date, status)
        VALUES (?, ?, ?, ?)
        ''', past_billing
    )

    # Add payment methods
    payment_methods = [
        (customer_id, 'credit_card', 'Card ending in 1234'),
        (customer_id, 'bank_transfer', 'Account ending in 5678')
    ]
    
    for cust_id, type, details in payment_methods:
        if not cursor.execute('SELECT * FROM payment_methods WHERE customer_id = ? AND details = ?',
                         (cust_id, details)).fetchone():
            cursor.execute('''
                INSERT INTO payment_methods (customer_id, type, details)
                VALUES (?, ?, ?)
            ''', (cust_id, type, details))

    # Add past payments
    past_payments = []
    for days, method, trx in [(25, 'credit_card', 'TRX001'),
                              (55, 'debit_card', 'TRX002'),
                              (85, 'bank_transfer', 'TRX003')]:
        date_str = (current_date - timedelta(days=days)).strftime('%Y-%m-%d')
        past_payments.append((customer_id, 89.98, date_str, method, 'completed', trx))

    cursor.executemany(
        '''
        INSERT OR IGNORE INTO payments 
            (customer_id, amount, payment_date, payment_method, status, transaction_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', past_payments
    )

    # Add appointments
    appointments = []
    for desc, status, offset in [('installation', 'completed', -120),
                                 ('repair', 'scheduled', 7),
                                 ('upgrade', 'scheduled', 14)]:
        start = (current_date + timedelta(days=offset)).strftime('%Y-%m-%d %H:00:00')
        end = (current_date + timedelta(days=offset)).strftime('%Y-%m-%d %H:00:00')
        job_number = str(random.randint(10000, 99999))  # Generate a unique 5-digit job number
        appointments.append(
            (customer_id, desc, status, start, end, f'{desc.capitalize()} service event', job_number)
        )
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO appointments 
            (customer_id, type, status, start_time, end_time, notes, job_number)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', appointments
    )

    # Add service history
    service_history = [
        (customer_id, 1, 'added', (current_date - timedelta(days=120)).strftime('%Y-%m-%d'), 'Initial cable service activation'),
        (customer_id, 2, 'added', (current_date - timedelta(days=120)).strftime('%Y-%m-%d'), 'Initial internet service activation'),
        (customer_id, 2, 'modified', (current_date - timedelta(days=30)).strftime('%Y-%m-%d'), 'Upgraded to 100 Mbps plan')
    ]
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO service_history 
            (customer_id, service_id, action, action_date, notes)
        VALUES (?, ?, ?, ?, ?)
        ''', service_history
    )

    db.commit()
    db.close()
    print("Test data initialized successfully")
    print(f"Test account credentials:\nCustomer ID: {customer_id}\nEmail: {test_customer['email']}\nPassword: {test_customer['password']}")

if __name__ == '__main__':
    init_test_data()
