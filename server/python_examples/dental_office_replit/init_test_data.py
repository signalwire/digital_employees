import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
import random
import os
import json
from werkzeug.security import generate_password_hash

def hash_password(password):
    """Hash password with salt for secure storage"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt

def generate_unique_bill_number():
    """Generate a unique 6-digit bill number"""
    return str(random.randint(100000, 999999))

def init_test_data():
    """Initialize comprehensive test data for the SignalWire dental office system with single 7-digit patient IDs"""
    conn = sqlite3.connect('dental_office.db')
    cursor = conn.cursor()

    print("Initializing comprehensive test data with single 7-digit patient IDs...")

    # Read and execute schema.sql to recreate all tables
    with open('schema.sql', 'r') as f:
        schema = f.read()
        cursor.executescript(schema)

    # Clear all existing data to start fresh
    print("Clearing existing data...")
    tables_to_clear = [
        'insurance_claims', 'payments', 'billing', 'treatment_history', 
        'appointments', 'payment_methods', 'patients', 'dentists', 'dental_services'
    ]
    
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared {table} table")
        except sqlite3.Error as e:
            print(f"Note: Could not clear {table}: {e}")

    # Apply bill_number migration if it exists
    try:
        # Check if bill_number column already exists
        cursor.execute("PRAGMA table_info(billing)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'bill_number' not in columns:
            print("Adding bill_number column to billing table...")
            cursor.execute("ALTER TABLE billing ADD COLUMN bill_number TEXT")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_bill_number ON billing(bill_number)")
            conn.commit()
        else:
            print("bill_number column already exists")
    except sqlite3.Error as e:
        print(f"Migration note: {e}")
        pass  # Continue with data insertion

    # Insert comprehensive dental services
    services = [
        ('Regular Cleaning', 'Standard dental cleaning and checkup', 120.00, 'cleaning'),
        ('Deep Cleaning', 'Deep cleaning and scaling for gum disease', 250.00, 'cleaning'),
        ('Cavity Filling', 'Composite filling for cavities', 180.00, 'filling'),
        ('Root Canal', 'Root canal treatment for infected teeth', 950.00, 'root_canal'),
        ('Teeth Whitening', 'Professional teeth whitening treatment', 350.00, 'whitening'),
        ('Dental Checkup', 'Comprehensive dental examination', 85.00, 'checkup'),
        ('Crown Installation', 'Dental crown installation', 1200.00, 'other'),
        ('Tooth Extraction', 'Simple tooth extraction', 200.00, 'extraction'),
        ('Wisdom Tooth Removal', 'Surgical wisdom tooth extraction', 400.00, 'extraction'),
        ('Dental Implant', 'Single tooth implant with crown', 3500.00, 'other'),
        ('Braces Consultation', 'Orthodontic consultation and planning', 150.00, 'orthodontics'),
        ('Emergency Visit', 'Emergency dental treatment', 200.00, 'other')
    ]
    cursor.executemany('''
        INSERT INTO dental_services (name, description, price, type)
        VALUES (?, ?, ?, ?)
    ''', services)

    # Get the actual service IDs after insertion for proper referencing
    service_map = {}
    service_names = [
        'Regular Cleaning', 'Deep Cleaning', 'Cavity Filling', 'Root Canal',
        'Teeth Whitening', 'Dental Checkup', 'Crown Installation', 'Tooth Extraction',
        'Wisdom Tooth Removal', 'Dental Implant', 'Braces Consultation', 'Emergency Visit'
    ]
    
    for name in service_names:
        result = cursor.execute('SELECT id FROM dental_services WHERE name = ?', (name,)).fetchone()
        if result:
            service_map[name] = result[0]
    
    print(f"Service ID mapping: {service_map}")

    # Enhanced working hours for different dentists
    dr_smith_hours = json.dumps({
        "monday": {"morning": True, "afternoon": True, "evening": False},
        "tuesday": {"morning": True, "afternoon": True, "evening": False},
        "wednesday": {"morning": True, "afternoon": True, "evening": False},
        "thursday": {"morning": True, "afternoon": True, "evening": False},
        "friday": {"morning": True, "afternoon": True, "evening": False},
        "saturday": {"morning": False, "afternoon": False, "evening": False},
        "sunday": {"morning": False, "afternoon": False, "evening": False}
    })
    
    dr_johnson_hours = json.dumps({
        "monday": {"morning": True, "afternoon": True, "evening": True},
        "tuesday": {"morning": True, "afternoon": True, "evening": True},
        "wednesday": {"morning": True, "afternoon": True, "evening": True},
        "thursday": {"morning": True, "afternoon": True, "evening": True},
        "friday": {"morning": True, "afternoon": True, "evening": False},
        "saturday": {"morning": False, "afternoon": False, "evening": False},
        "sunday": {"morning": False, "afternoon": False, "evening": False}
    })
    
    dr_chen_hours = json.dumps({
        "monday": {"morning": True, "afternoon": True, "evening": False},
        "tuesday": {"morning": True, "afternoon": True, "evening": False},
        "wednesday": {"morning": True, "afternoon": True, "evening": False},
        "thursday": {"morning": True, "afternoon": True, "evening": False},
        "friday": {"morning": True, "afternoon": False, "evening": False},
        "saturday": {"morning": False, "afternoon": False, "evening": False},
        "sunday": {"morning": False, "afternoon": False, "evening": False}
    })

    # Insert comprehensive dentist data
    dentist_password_hash, dentist_password_salt = hash_password('dentist123')
    dentists = [
        ('Dr. John', 'Smith', 'dr.smith@test.tld', '555-0101', 
         'General Dentistry', 'DENT123456', 
         dentist_password_hash, dentist_password_salt, dr_smith_hours),
        ('Dr. Sarah', 'Johnson', 'dr.johnson@test.tld', '555-0103',
         'Orthodontics', 'DENT654321',
         dentist_password_hash, dentist_password_salt, dr_johnson_hours),
        ('Dr. Michael', 'Chen', 'dr.chen@test.tld', '555-0105',
         'Oral Surgery', 'DENT789012',
         dentist_password_hash, dentist_password_salt, dr_chen_hours)
    ]
    cursor.executemany('''
        INSERT INTO dentists (first_name, last_name, email, phone, specialization, 
                            license_number, password_hash, password_salt, working_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', dentists)

    # Define 7-digit patient IDs as primary keys (no internal auto-increment IDs)
    patient_ids = {
        'jane': 8675309,   # Famous phone number for testing
        'jim': 3703746,    # Random 7-digit
        'maria': 5569266,  # Random 7-digit  
        'robert': 2841975, # Random 7-digit
        'emily': 9157384   # Random 7-digit
    }

    # Insert comprehensive patient data using 7-digit IDs as primary keys
    patient_password_hash, patient_password_salt = hash_password('patient123')
    
    patients = [
        (patient_ids['jane'], 'Jane', 'Doe', 'jane.doe@test.tld', '555-0102', 
         '123 Main St, Anytown, USA', '1990-01-01',
         'No known allergies', 'Insurance Provider: DentalCare Plus, Policy: DC123456',
         patient_password_hash, patient_password_salt, str(patient_ids['jane'])),
        (patient_ids['jim'], 'Jim', 'Smith', 'jim.smith@test.tld', '555-0104',
         '456 Elm St, Anytown, USA', '1985-05-15',
         'Penicillin allergy', 'Insurance Provider: HealthFirst, Policy: HF789012',
         patient_password_hash, patient_password_salt, str(patient_ids['jim'])),
        (patient_ids['maria'], 'Maria', 'Garcia', 'maria.garcia@test.tld', '555-0106',
         '789 Oak Ave, Anytown, USA', '1992-08-22',
         'Latex allergy, diabetes', 'Insurance Provider: MediCare Dental, Policy: MD345678',
         patient_password_hash, patient_password_salt, str(patient_ids['maria'])),
        (patient_ids['robert'], 'Robert', 'Wilson', 'robert.wilson@test.tld', '555-0108',
         '321 Pine St, Anytown, USA', '1978-11-30',
         'High blood pressure, takes medication', 'Insurance Provider: DentalCare Plus, Policy: DC901234',
         patient_password_hash, patient_password_salt, str(patient_ids['robert'])),
        (patient_ids['emily'], 'Emily', 'Brown', 'emily.brown@test.tld', '555-0110',
         '654 Maple Dr, Anytown, USA', '1995-03-18',
         'No known allergies', 'No insurance',
         patient_password_hash, patient_password_salt, str(patient_ids['emily']))
    ]
    
    cursor.executemany('''
        INSERT INTO patients (id, first_name, last_name, email, phone, address, 
                            date_of_birth, medical_history, insurance_info, 
                            password_hash, password_salt, patient_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', patients)

    # Insert comprehensive payment methods using 7-digit patient IDs
    payment_methods = [
        # Jane Doe's payment methods (ID: 8675309)
        (patient_ids['jane'], 'credit_card', '4111111111111111', '12/25', 'Jane Doe', None, None, None, 1),
        (patient_ids['jane'], 'credit_card', '4532123456789014', '09/26', 'Jane Doe', None, None, None, 0),
        (patient_ids['jane'], 'banking', None, None, None, 'Chase Bank', '9876543210', '021000021', 0),
        
        # Jim Smith's payment methods (ID: 3703746)
        (patient_ids['jim'], 'credit_card', '4532123456789015', '03/26', 'Jim Smith', None, None, None, 1),
        (patient_ids['jim'], 'banking', None, None, None, 'Bank of America', '1234567890', '026009593', 0),
        
        # Maria Garcia's payment methods (ID: 5569266)
        (patient_ids['maria'], 'credit_card', '4000000000000002', '08/25', 'Maria Garcia', None, None, None, 1),
        (patient_ids['maria'], 'banking', None, None, None, 'Wells Fargo', '5555666677', '121000248', 0),
        
        # Robert Wilson's payment methods (ID: 2841975)
        (patient_ids['robert'], 'credit_card', '4242424242424242', '11/27', 'Robert Wilson', None, None, None, 1),
        
        # Emily Brown's payment methods (ID: 9157384)
        (patient_ids['emily'], 'credit_card', '4012888888881881', '05/25', 'Emily Brown', None, None, None, 1)
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO payment_methods 
    (patient_id, method_type, card_number, expiry_date, card_holder, bank_name, account_number, routing_number, is_default)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', payment_methods)

    # Insert comprehensive appointments using 7-digit patient IDs
    now = datetime.now()
    
    # Calculate dates for current week appointments
    current_weekday = now.weekday()
    week_start = now - timedelta(days=current_weekday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    days_until_week_end = (week_end.date() - now.date()).days
    
    if days_until_week_end >= 3:
        week_apt_1 = now + timedelta(days=1, hours=9)
        week_apt_2 = now + timedelta(days=2, hours=14)
        week_apt_3 = now + timedelta(days=3, hours=11)
    elif days_until_week_end >= 2:
        week_apt_1 = now + timedelta(hours=2)
        week_apt_2 = now + timedelta(days=1, hours=10)
        week_apt_3 = now + timedelta(days=2, hours=15)
    elif days_until_week_end >= 1:
        week_apt_1 = now + timedelta(hours=1)
        week_apt_2 = now + timedelta(hours=4)
        week_apt_3 = now + timedelta(days=1, hours=10)
    else:
        week_apt_1 = now + timedelta(hours=1)
        week_apt_2 = now + timedelta(hours=2)
        week_apt_3 = now + timedelta(hours=4)
    
    appointments = [
        # Current week appointments using 7-digit patient IDs
        (patient_ids['jane'], 1, service_map['Regular Cleaning'], 'cleaning', 'scheduled',
         week_apt_1.strftime('%Y-%m-%d %H:%M:%S'),
         (week_apt_1 + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
         'Regular 6-month cleaning - Current week appointment', 1),
        (patient_ids['jim'], 1, service_map['Cavity Filling'], 'filling', 'scheduled',
         week_apt_2.strftime('%Y-%m-%d %H:%M:%S'),
         (week_apt_2 + timedelta(hours=1, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
         'Cavity filling on molar - Current week appointment', 1),
        (patient_ids['maria'], 2, service_map['Braces Consultation'], 'orthodontics', 'scheduled',
         week_apt_3.strftime('%Y-%m-%d %H:%M:%S'),
         (week_apt_3 + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
         'Braces consultation - Current week appointment', 1),
        
        # Future appointments
        (patient_ids['robert'], 3, service_map['Tooth Extraction'], 'extraction', 'scheduled',
         (now + timedelta(days=8)).strftime('%Y-%m-%d 15:00:00'),
         (now + timedelta(days=8)).strftime('%Y-%m-%d 16:00:00'),
         'Wisdom tooth extraction', 1),
        (patient_ids['emily'], 1, service_map['Teeth Whitening'], 'whitening', 'scheduled',
         (now + timedelta(days=12)).strftime('%Y-%m-%d 11:00:00'),
         (now + timedelta(days=12)).strftime('%Y-%m-%d 12:30:00'),
         'Teeth whitening treatment', 1),
        
        # Today's appointments
        (patient_ids['jane'], 1, service_map['Dental Checkup'], 'checkup', 'scheduled',
         now.strftime('%Y-%m-%d %H:%M:%S'),
         (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
         'Annual checkup - happening now', 1),
        (patient_ids['emily'], 1, service_map['Emergency Visit'], 'other', 'scheduled',
         (now + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
         (now + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
         'Emergency toothache - later today', 1),
        
        # Recent completed appointments
        (patient_ids['jane'], 1, service_map['Regular Cleaning'], 'cleaning', 'completed',
         (now - timedelta(days=180)).strftime('%Y-%m-%d 09:00:00'),
         (now - timedelta(days=180)).strftime('%Y-%m-%d 10:00:00'),
         'Previous cleaning - excellent condition', 1),
        (patient_ids['jim'], 1, service_map['Dental Checkup'], 'checkup', 'completed',
         (now - timedelta(days=30)).strftime('%Y-%m-%d 13:00:00'),
         (now - timedelta(days=30)).strftime('%Y-%m-%d 14:00:00'),
         'Checkup revealed cavity', 1),
        (patient_ids['maria'], 2, service_map['Teeth Whitening'], 'whitening', 'completed',
         (now - timedelta(days=45)).strftime('%Y-%m-%d 16:00:00'),
         (now - timedelta(days=45)).strftime('%Y-%m-%d 17:30:00'),
         'Teeth whitening completed successfully', 1),
        (patient_ids['robert'], 1, service_map['Root Canal'], 'root_canal', 'in_progress',
         (now - timedelta(days=7)).strftime('%Y-%m-%d 10:00:00'),
         (now - timedelta(days=7)).strftime('%Y-%m-%d 12:00:00'),
         'Root canal treatment started', 1),
        
        # Cancelled appointment
        (patient_ids['emily'], 2, service_map['Regular Cleaning'], 'cleaning', 'cancelled',
         (now - timedelta(days=15)).strftime('%Y-%m-%d 14:00:00'),
         (now - timedelta(days=15)).strftime('%Y-%m-%d 15:00:00'),
         'Patient cancelled due to illness', 0)
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO appointments (patient_id, dentist_id, service_id, type, status,
                                start_time, end_time, notes, sms_reminder)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', appointments)

    # Insert comprehensive treatment history using 7-digit patient IDs
    treatments = [
        # Jane Doe's treatments (ID: 8675309)
        (patient_ids['jane'], 1, service_map['Regular Cleaning'], (now - timedelta(days=180)).strftime('%Y-%m-%d'),
         'Routine cleaning', 'Excellent oral hygiene. No issues found.', 
         (now + timedelta(days=180)).strftime('%Y-%m-%d'), 'TH001', 120.00),
        (patient_ids['jane'], 1, service_map['Dental Checkup'], (now - timedelta(days=30)).strftime('%Y-%m-%d'),
         'Annual checkup', 'Overall good health. Recommended whitening.', 
         (now + timedelta(days=180)).strftime('%Y-%m-%d'), 'TH002', 85.00),
         
        # Jim Smith's treatments (ID: 3703746)
        (patient_ids['jim'], 1, service_map['Dental Checkup'], (now - timedelta(days=30)).strftime('%Y-%m-%d'),
         'Checkup revealed cavity', 'Small cavity found in upper right molar',
         (now + timedelta(days=7)).strftime('%Y-%m-%d'), 'TH003', 85.00),
        (patient_ids['jim'], 1, service_map['Deep Cleaning'], (now - timedelta(days=90)).strftime('%Y-%m-%d'),
         'Deep cleaning', 'Moderate tartar buildup removed successfully',
         (now + timedelta(days=120)).strftime('%Y-%m-%d'), 'TH004', 250.00),
        (patient_ids['jim'], 1, service_map['Cavity Filling'], (now).strftime('%Y-%m-%d'),
         'Cavity filling', 'Composite filling placed in upper right molar',
         (now + timedelta(days=180)).strftime('%Y-%m-%d'), 'TH_FUTURE_001', 180.00),
        (patient_ids['jim'], 2, service_map['Braces Consultation'], (now - timedelta(days=5)).strftime('%Y-%m-%d'),
         'Braces consultation', 'Comprehensive orthodontic evaluation. Treatment plan developed.',
         (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'REF-1748809864233-356', 500.00),
         
        # Maria Garcia's treatments (ID: 5569266)
        (patient_ids['maria'], 2, service_map['Teeth Whitening'], (now - timedelta(days=45)).strftime('%Y-%m-%d'),
         'Teeth whitening', 'Professional whitening completed. Excellent results.',
         None, 'TH005', 350.00),
        (patient_ids['maria'], 2, service_map['Regular Cleaning'], (now - timedelta(days=120)).strftime('%Y-%m-%d'),
         'Regular cleaning', 'Good oral health maintained.',
         (now + timedelta(days=60)).strftime('%Y-%m-%d'), 'TH006', 120.00),
         
        # Robert Wilson's treatments (ID: 2841975)
        (patient_ids['robert'], 1, service_map['Root Canal'], (now - timedelta(days=7)).strftime('%Y-%m-%d'),
         'Root canal treatment', 'Root canal procedure initiated. Follow-up required.',
         (now + timedelta(days=14)).strftime('%Y-%m-%d'), 'TH007', 950.00),
        (patient_ids['robert'], 3, service_map['Tooth Extraction'], (now - timedelta(days=60)).strftime('%Y-%m-%d'),
         'Tooth extraction', 'Extracted damaged tooth #18',
         (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'TH008', 200.00),
         
        # Emily Brown's treatments (ID: 9157384)
        (patient_ids['emily'], 1, service_map['Emergency Visit'], (now - timedelta(days=5)).strftime('%Y-%m-%d'),
         'Emergency toothache', 'Provided pain relief and temporary filling',
         (now + timedelta(days=7)).strftime('%Y-%m-%d'), 'TH009', 200.00),
         
        # Additional overdue treatments
        (patient_ids['jane'], 1, service_map['Regular Cleaning'], (now - timedelta(days=90)).strftime('%Y-%m-%d'),
         'Previous cleaning', 'Routine cleaning performed successfully.',
         (now + timedelta(days=90)).strftime('%Y-%m-%d'), 'TH_OVERDUE_001', 150.00),
        (patient_ids['robert'], 1, service_map['Dental Checkup'], (now - timedelta(days=75)).strftime('%Y-%m-%d'),
         'Overdue checkup', 'Regular examination completed.',
         (now + timedelta(days=180)).strftime('%Y-%m-%d'), 'TH_OVERDUE_002', 85.00)
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO treatment_history (patient_id, dentist_id, service_id,
                                     treatment_date, diagnosis, treatment_notes,
                                     follow_up_date, reference_number, bill_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', treatments)

    # Insert comprehensive billing records using 7-digit patient IDs and 6-digit bill numbers
    billing = [
        # Jane Doe's bills (ID: 8675309) - Only 1 deep cleaning bill for SWAIG testing
        (patient_ids['jane'], 1, 1, service_map['Regular Cleaning'], 120.00, 80.00, 0.00, 'paid', 
         (now - timedelta(days=150)).strftime('%Y-%m-%d'), 'TH001', 
         (now - timedelta(days=180)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['jane'], 1, 5, service_map['Dental Checkup'], 85.00, 60.00, 0.00, 'paid', 
         (now).strftime('%Y-%m-%d'), 'TH002', 
         (now - timedelta(days=30)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
         
        # Jim Smith's bills (ID: 3703746) - NO deep cleaning bills to ensure only 1 total
        (patient_ids['jim'], 1, 8, service_map['Dental Checkup'], 85.00, 70.00, 15.00, 'partial', 
         (now).strftime('%Y-%m-%d'), 'TH003', 
         (now - timedelta(days=30)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['jim'], 1, None, service_map['Cavity Filling'], 180.00, 120.00, 60.00, 'pending', 
         (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'TH_FUTURE_001', 
         (now).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['jim'], 2, 13, service_map['Braces Consultation'], 500.00, 200.00, 300.00, 'partial', 
         (now + timedelta(days=15)).strftime('%Y-%m-%d'), 'REF-1748809864233-356', 
         (now - timedelta(days=5)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
         
        # Maria Garcia's bills (ID: 5569266)
        (patient_ids['maria'], 2, 9, service_map['Teeth Whitening'], 350.00, 0.00, 0.00, 'paid', 
         (now - timedelta(days=15)).strftime('%Y-%m-%d'), 'TH005', 
         (now - timedelta(days=45)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['maria'], 2, 6, service_map['Regular Cleaning'], 120.00, 80.00, 40.00, 'pending', 
         (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'TH006', 
         (now - timedelta(days=120)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
         
        # Robert Wilson's bills (ID: 2841975)
        (patient_ids['robert'], 1, 10, service_map['Root Canal'], 950.00, 600.00, 200.00, 'partial', 
         (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'TH007', 
         (now - timedelta(days=7)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['robert'], 3, 7, service_map['Tooth Extraction'], 200.00, 150.00, 0.00, 'paid', 
         (now - timedelta(days=30)).strftime('%Y-%m-%d'), 'TH008', 
         (now - timedelta(days=60)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
         
        # Emily Brown's bills (ID: 9157384) - no insurance
        (patient_ids['emily'], 1, 11, service_map['Emergency Visit'], 200.00, 0.00, 200.00, 'overdue', 
         (now - timedelta(days=10)).strftime('%Y-%m-%d'), 'TH009', 
         (now - timedelta(days=5)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
         
        # Additional overdue bills for testing
        (patient_ids['jane'], 1, None, service_map['Regular Cleaning'], 150.00, 100.00, 50.00, 'overdue', 
         (now - timedelta(days=45)).strftime('%Y-%m-%d'), 'TH_OVERDUE_001', 
         (now - timedelta(days=90)).strftime('%Y-%m-%d'), None, generate_unique_bill_number()),
        (patient_ids['robert'], 1, None, service_map['Dental Checkup'], 85.00, 85.00, 0.00, 'overdue', 
         (now - timedelta(days=30)).strftime('%Y-%m-%d'), 'TH_OVERDUE_002', 
         (now - timedelta(days=75)).strftime('%Y-%m-%d'), None, generate_unique_bill_number())
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO billing (patient_id, dentist_id, appointment_id, service_id, amount,
                           insurance_coverage, patient_portion, status, due_date, reference_number,
                           created_at, payment_id, bill_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', billing)

    # Get actual billing IDs and payment method IDs for payment records
    print("Getting actual billing and payment method IDs...")
    
    # Get billing ID mappings by reference number
    billing_map = {}
    billing_refs = ['TH001', 'TH002', 'TH003', 'TH_FUTURE_001', 'REF-1748809864233-356', 
                   'TH005', 'TH006', 'TH007', 'TH008', 'TH009', 'TH_OVERDUE_001', 'TH_OVERDUE_002']
    
    for ref in billing_refs:
        result = cursor.execute('SELECT id FROM billing WHERE reference_number = ?', (ref,)).fetchone()
        if result:
            billing_map[ref] = result[0]
    
    print(f"Billing ID mapping: {billing_map}")
    
    # Get payment method ID mappings by patient ID and method type
    pm_map = {}
    pm_queries = [
        (patient_ids['jane'], 'credit_card', 'jane_cc1'),
        (patient_ids['jane'], 'credit_card', 'jane_cc2'),  # Second card (non-default)
        (patient_ids['jim'], 'credit_card', 'jim_cc'),
        (patient_ids['jim'], 'banking', 'jim_bank'),
        (patient_ids['maria'], 'credit_card', 'maria_cc'),
        (patient_ids['robert'], 'credit_card', 'robert_cc'),
        (patient_ids['emily'], 'credit_card', 'emily_cc')
    ]
    
    for patient_id, method_type, key in pm_queries:
        if key.endswith('_cc1'):  # Get default credit card
            result = cursor.execute('SELECT id FROM payment_methods WHERE patient_id = ? AND method_type = ? AND is_default = 1', 
                                  (patient_id, method_type)).fetchone()
        elif key.endswith('_cc2'):  # Get non-default credit card
            result = cursor.execute('SELECT id FROM payment_methods WHERE patient_id = ? AND method_type = ? AND is_default = 0', 
                                  (patient_id, method_type)).fetchone()
        else:
            result = cursor.execute('SELECT id FROM payment_methods WHERE patient_id = ? AND method_type = ?', 
                                  (patient_id, method_type)).fetchone()
        if result:
            pm_map[key] = result[0]
    
    print(f"Payment method ID mapping: {pm_map}")

    # Insert comprehensive payment history using actual IDs
    payment_records = [
        # Jane Doe's payments (ID: 8675309) - using actual billing and PM IDs
        (billing_map.get('TH001'), patient_ids['jane'], 40.00, (now - timedelta(days=170)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('jane_cc1'), 'credit_card', 'completed', 'TXN100001', 'Paid insurance copay for cleaning'),
        (billing_map.get('TH002'), patient_ids['jane'], 25.00, (now - timedelta(days=25)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('jane_cc1'), 'credit_card', 'completed', 'TXN100002', 'Paid copay for checkup'),
        
        # Jim Smith's payments (ID: 3703746)
        (billing_map.get('TH003'), patient_ids['jim'], 70.00, (now - timedelta(days=25)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('jim_cc'), 'credit_card', 'completed', 'TXN100003', 'Partial payment for checkup'),
        (billing_map.get('TH_FUTURE_001'), patient_ids['jim'], 100.00, (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('jim_cc'), 'banking', 'completed', 'TXN100005', 'Partial payment for cavity filling'),
        (billing_map.get('REF-1748809864233-356'), patient_ids['jim'], 50.00, (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('jim_bank'), 'bank_transfer', 'completed', 'TXN100011', 'Payment for braces consultation'),
        
        # Maria Garcia's payments (ID: 5569266)
        (billing_map.get('TH005'), patient_ids['maria'], 350.00, (now - timedelta(days=40)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('maria_cc'), 'credit_card', 'completed', 'TXN100006', 'Full payment for teeth whitening'),
        
        # Robert Wilson's payments (ID: 2841975)
        (billing_map.get('TH008'), patient_ids['robert'], 50.00, (now - timedelta(days=25)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('robert_cc'), 'credit_card', 'completed', 'TXN100007', 'Paid copay for extraction'),
        (billing_map.get('TH007'), patient_ids['robert'], 200.00, (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('robert_cc'), 'credit_card', 'completed', 'TXN100008', 'Partial payment for root canal'),
        
        # Failed payment example (ID: 9157384)
        (billing_map.get('TH009'), patient_ids['emily'], 200.00, (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'), 
         pm_map.get('emily_cc'), 'credit_card', 'failed', 'TXN100009', 'Payment failed - insufficient funds')
    ]
    
    # Filter out records with None values (missing mappings)
    valid_payment_records = [record for record in payment_records if record[0] is not None and record[4] is not None]
    print(f"Inserting {len(valid_payment_records)} valid payment records...")
    
    cursor.executemany('''
        INSERT OR IGNORE INTO payments (billing_id, patient_id, amount, payment_date, 
                                      payment_method_id, payment_method_type, status, 
                                      transaction_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', valid_payment_records)

    # Insert comprehensive insurance claims using actual billing IDs
    insurance_claims = [
        (billing_map.get('TH001'), 80.00, 'approved', (now - timedelta(days=175)).strftime('%Y-%m-%d'), 
         (now - timedelta(days=165)).strftime('%Y-%m-%d'), 'Claim for routine cleaning approved'),
        (billing_map.get('TH002'), 60.00, 'approved', (now - timedelta(days=35)).strftime('%Y-%m-%d'), 
         (now - timedelta(days=20)).strftime('%Y-%m-%d'), 'Claim for checkup approved'),
        (billing_map.get('TH003'), 70.00, 'pending', (now - timedelta(days=25)).strftime('%Y-%m-%d'),
         None, 'Claim for checkup under review'),
        (billing_map.get('TH_FUTURE_001'), 120.00, 'pending', (now - timedelta(days=5)).strftime('%Y-%m-%d'),
         None, 'Claim for cavity filling submitted'),
        (billing_map.get('TH006'), 80.00, 'pending', (now - timedelta(days=115)).strftime('%Y-%m-%d'),
         None, 'Claim for cleaning under review'),
        (billing_map.get('TH007'), 600.00, 'pending', (now - timedelta(days=5)).strftime('%Y-%m-%d'),
         None, 'Claim for root canal submitted'),
        (billing_map.get('TH008'), 150.00, 'approved', (now - timedelta(days=55)).strftime('%Y-%m-%d'),
         (now - timedelta(days=40)).strftime('%Y-%m-%d'), 'Claim for extraction approved'),
        (billing_map.get('TH009'), 100.00, 'rejected', (now - timedelta(days=85)).strftime('%Y-%m-%d'),
         (now - timedelta(days=75)).strftime('%Y-%m-%d'), 'Claim rejected - not covered service'),
        (billing_map.get('TH_OVERDUE_002'), 85.00, 'approved', (now - timedelta(days=70)).strftime('%Y-%m-%d'),
         (now - timedelta(days=60)).strftime('%Y-%m-%d'), 'Claim for overdue checkup approved')
    ]
    
    # Filter out records with None values (missing billing IDs)
    valid_insurance_claims = [claim for claim in insurance_claims if claim[0] is not None]
    print(f"Inserting {len(valid_insurance_claims)} valid insurance claims...")
    
    cursor.executemany('''
        INSERT OR IGNORE INTO insurance_claims (billing_id, claim_amount, status, submission_date, 
                                    response_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', valid_insurance_claims)

    conn.commit()
    conn.close()
    
    print("\n=== Test Data Initialized Successfully with Single 7-Digit Patient IDs ===")
    print("Default Login Credentials:")
    print("Dentist: dr.smith@test.tld / dentist123")
    print("Patient: jane.doe@test.tld / patient123")
    print(f"Jane Doe Patient ID: {patient_ids['jane']} (8675309)")
    print(f"Jim Smith Patient ID: {patient_ids['jim']} (3703746)") 
    print(f"Maria Garcia Patient ID: {patient_ids['maria']} (5569266)")
    print(f"Robert Wilson Patient ID: {patient_ids['robert']} (2841975)")
    print(f"Emily Brown Patient ID: {patient_ids['emily']} (9157384)")
    print("IMPORTANT: Only Jane Doe should have Deep Cleaning bills for SWAIG testing")
    print("=============================================================================")

if __name__ == '__main__':
    init_test_data()
