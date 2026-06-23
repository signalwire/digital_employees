-- Patients table
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    medical_history TEXT,
    insurance_info TEXT,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    patient_id TEXT UNIQUE NOT NULL, -- Random 7-digit string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dentists table
CREATE TABLE IF NOT EXISTS dentists (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    specialization TEXT,
    license_number TEXT UNIQUE NOT NULL,
    working_hours TEXT NOT NULL DEFAULT '{"monday":{"start":"09:00","end":"17:00"},"tuesday":{"start":"09:00","end":"17:00"},"wednesday":{"start":"09:00","end":"17:00"},"thursday":{"start":"09:00","end":"17:00"},"friday":{"start":"09:00","end":"17:00"}}',
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password Resets table
CREATE TABLE IF NOT EXISTS password_resets (
    id TEXT PRIMARY KEY,  -- UUID for the reset request
    user_id INTEGER NOT NULL,
    user_type TEXT NOT NULL CHECK(user_type IN ('patient', 'dentist')),
    email TEXT NOT NULL,
    mfa_code TEXT NOT NULL,  -- 6-digit MFA code
    expires_at TEXT NOT NULL,  -- ISO format timestamp
    verified BOOLEAN NOT NULL DEFAULT 0,  -- Whether MFA code has been verified
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dental Services table
CREATE TABLE IF NOT EXISTS dental_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('cleaning', 'filling', 'extraction', 'root_canal', 'whitening', 'orthodontics', 'checkup', 'other'))
);

-- Appointments table
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    dentist_id INTEGER,
    service_id INTEGER,
    type TEXT NOT NULL CHECK(type IN ('checkup', 'cleaning', 'filling', 'extraction', 'root_canal', 'whitening', 'orthodontics', 'other')),
    status TEXT NOT NULL CHECK(status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    notes TEXT,
    sms_reminder BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (dentist_id) REFERENCES dentists(id),
    FOREIGN KEY (service_id) REFERENCES dental_services(id)
);

-- Billing table
CREATE TABLE IF NOT EXISTS billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    dentist_id INTEGER,
    appointment_id INTEGER,
    service_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    insurance_coverage DECIMAL(10,2) DEFAULT 0,
    patient_portion DECIMAL(10,2) NOT NULL, -- Amount the patient owes and is decremented as payments are made
    status TEXT NOT NULL CHECK(status IN ('pending', 'paid', 'overdue', 'cancelled', 'partial')),
    due_date TIMESTAMP NOT NULL,
    reference_number TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_id INTEGER, -- Link to last payment if needed
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (dentist_id) REFERENCES dentists(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (service_id) REFERENCES dental_services(id)
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billing_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    payment_method_id INTEGER,
    payment_method_type TEXT NOT NULL CHECK(payment_method_type IN ('credit_card', 'banking')),
    status TEXT NOT NULL CHECK(status IN ('pending', 'completed', 'failed', 'refunded')),
    transaction_id TEXT UNIQUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (billing_id) REFERENCES billing(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
);

-- Payment Methods table
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    method_type TEXT NOT NULL CHECK(method_type IN ('credit_card', 'banking')),
    card_number TEXT,
    expiry_date TEXT,
    card_holder TEXT,
    bank_name TEXT,
    account_number TEXT,
    routing_number TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Insurance Claims table
CREATE TABLE IF NOT EXISTS insurance_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billing_id INTEGER NOT NULL,
    claim_amount DECIMAL(10,2) NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'paid')),
    submission_date TIMESTAMP NOT NULL,
    response_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (billing_id) REFERENCES billing(id)
);

-- Treatment History table
CREATE TABLE IF NOT EXISTS treatment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    dentist_id INTEGER,
    service_id INTEGER,
    treatment_date TIMESTAMP NOT NULL,
    diagnosis TEXT,
    treatment_notes TEXT,
    follow_up_date TIMESTAMP,
    reference_number TEXT,
    bill_amount DECIMAL(10,2),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (dentist_id) REFERENCES dentists(id),
    FOREIGN KEY (service_id) REFERENCES dental_services(id)
);

-- Create indexes for better search performance
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_patients_email ON patients(email);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
CREATE INDEX IF NOT EXISTS idx_dentists_name ON dentists(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_dentists_email ON dentists(email);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_dentist ON appointments(dentist_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(start_time);
CREATE INDEX IF NOT EXISTS idx_billing_patient ON billing(patient_id);
CREATE INDEX IF NOT EXISTS idx_billing_status ON billing(status);
CREATE INDEX IF NOT EXISTS idx_payments_billing ON payments(billing_id);
CREATE INDEX IF NOT EXISTS idx_insurance_claims_billing ON insurance_claims(billing_id); 