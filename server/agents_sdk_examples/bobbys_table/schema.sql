-- Restaurant System Database Schema

-- Tables
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    party_size INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    status TEXT DEFAULT 'confirmed',
    special_requests TEXT,
    payment_status TEXT DEFAULT 'unpaid',
    payment_intent_id TEXT,
    payment_amount DECIMAL(10,2),
    payment_date TIMESTAMP,
    confirmation_number TEXT,
    payment_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    status TEXT DEFAULT 'available',
    location TEXT
);

CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category TEXT NOT NULL,
    is_available BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    reservation_id INTEGER,
    table_id INTEGER,
    person_name TEXT,
    status TEXT DEFAULT 'pending',
    total_amount DECIMAL(10,2),
    target_date TEXT,
    target_time TEXT,
    order_type TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    special_instructions TEXT,
    payment_status TEXT DEFAULT 'unpaid',
    payment_intent_id TEXT,
    payment_amount DECIMAL(10,2),
    payment_date TIMESTAMP,
    confirmation_number TEXT,
    payment_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES reservations(id),
    FOREIGN KEY (table_id) REFERENCES tables(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    menu_item_id INTEGER,
    quantity INTEGER NOT NULL,
    price_at_time DECIMAL(10,2) NOT NULL,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reservations_number ON reservations(reservation_number);
CREATE INDEX IF NOT EXISTS idx_reservations_date ON reservations(date);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);
CREATE INDEX IF NOT EXISTS idx_reservations_payment_status ON reservations(payment_status);
CREATE INDEX IF NOT EXISTS idx_tables_status ON tables(status);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status); 