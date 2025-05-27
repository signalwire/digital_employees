-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    account_number TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password Resets table
CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Services table
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('cable', 'internet', 'phone'))
);

-- Customer Services (subscriptions)
CREATE TABLE IF NOT EXISTS customer_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    service_id INTEGER,
    status TEXT NOT NULL CHECK(status IN ('active', 'suspended', 'cancelled')),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (service_id) REFERENCES services(id)
);

-- Modems table
CREATE TABLE IF NOT EXISTS modems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    mac_address TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('online', 'offline', 'rebooting')),
    last_seen TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Appointments table
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    type TEXT NOT NULL CHECK(type IN ('installation', 'repair', 'upgrade', 'modem_swap')),
    status TEXT NOT NULL CHECK(status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    amount DECIMAL(10,2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    payment_method TEXT NOT NULL CHECK(payment_method IN ('credit_card', 'debit_card', 'bank_transfer', 'phone')),
    status TEXT NOT NULL CHECK(status IN ('pending', 'completed', 'failed')),
    transaction_id TEXT UNIQUE,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Billing table
CREATE TABLE IF NOT EXISTS billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    amount DECIMAL(10,2) NOT NULL,
    due_date TIMESTAMP NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'paid', 'overdue')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Service History table
CREATE TABLE IF NOT EXISTS service_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    service_id INTEGER,
    action TEXT NOT NULL CHECK(action IN ('added', 'removed', 'modified')),
    action_date TIMESTAMP NOT NULL,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (service_id) REFERENCES services(id)
); 