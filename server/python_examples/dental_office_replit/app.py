from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, Response, g, send_from_directory, abort, send_file
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import hashlib
import secrets
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from signalwire_swaig.swaig import SWAIG, SWAIGArgument, SWAIGFunctionProperties
from signalwire_swaig.response import SWAIGResponse
from mfa_util import SignalWireMFA
import time
import traceback
import random
import string
import re
import uuid
import threading

app = Flask(__name__, static_folder=None)

# Load environment variables
load_dotenv(override=True)

# Debug CSRF environment variable loading
import sys
csrf_raw = os.getenv('ENABLE_CSRF')
csrf_default = os.getenv('ENABLE_CSRF', 'false')
csrf_lower = csrf_default.lower()
csrf_result = csrf_lower == 'true'
print(f"[DEBUG] CSRF Raw value: {repr(csrf_raw)}", file=sys.stderr)
print(f"[DEBUG] CSRF Default: {repr(csrf_default)}", file=sys.stderr)
print(f"[DEBUG] CSRF Lower: {repr(csrf_lower)}", file=sys.stderr)
print(f"[DEBUG] CSRF Result: {csrf_result}", file=sys.stderr)

SIGNALWIRE_PROJECT_ID = os.getenv('SIGNALWIRE_PROJECT_ID')
SIGNALWIRE_TOKEN = os.getenv('SIGNALWIRE_TOKEN')
SIGNALWIRE_AUTH_TOKEN = os.getenv('SIGNALWIRE_TOKEN')  # Same as SIGNALWIRE_TOKEN for consistency
SIGNALWIRE_SPACE = os.getenv('SIGNALWIRE_SPACE')

# Construct full SignalWire space URL from subdomain
if SIGNALWIRE_SPACE:
    SIGNALWIRE_SPACE = f"https://{SIGNALWIRE_SPACE}.signalwire.com"

SIGNALWIRE_PHONE_NUMBER = os.getenv('FROM_NUMBER')  # Same as FROM_NUMBER for consistency
PROJECT_URL = os.getenv('PROJECT_URL', 'http://localhost:8080')  # Default to localhost for development
HTTP_USERNAME = os.getenv('HTTP_USERNAME')
HTTP_PASSWORD = os.getenv('HTTP_PASSWORD')
C2C_API_KEY = os.getenv('C2C_API_KEY')
C2C_ADDRESS = os.getenv('C2C_ADDRESS')

# Initialize SWAIG before any @swaig.endpoint decorators
swaig = SWAIG(app, auth=(HTTP_USERNAME, HTTP_PASSWORD))

# Configuration - Use persistent SECRET_KEY from environment
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.secret_key = app.config['SECRET_KEY']  # Set Flask's secret_key to the same persistent value
app.config['ENABLE_CSRF'] = os.getenv('ENABLE_CSRF', 'false').lower() == 'true'

# Configure MIME types
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MIME_TYPES'] = {
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.min.css': 'text/css',
    '.min.js': 'application/javascript'
}

# Setup logging
def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a rotating file handler - use timed rotation for better Windows compatibility
    # This rotates daily instead of by size to avoid file locking issues
    file_handler = TimedRotatingFileHandler(
        'logs/dental_office.log',
        when='midnight',  # Rotate at midnight
        interval=1,  # Every 1 day
        backupCount=7,  # Keep 7 days of logs
        delay=True,  # Delay file creation until first write
        encoding='utf-8'
    )
    
    # Set up a formatter with more detailed information
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Add the new handler
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SignalWire Dental Office Management System startup')
    
    # Log CSRF protection status
    csrf_enabled = app.config.get('ENABLE_CSRF', False)
    if csrf_enabled:
        app.logger.info('CSRF Protection: ENABLED - All POST requests will be validated for CSRF tokens')
    else:
        app.logger.info('CSRF Protection: DISABLED - No CSRF token validation will occur')
    app.logger.info(f'CSRF Configuration: ENABLE_CSRF={csrf_enabled}')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('dental_office.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db_if_needed():
    if not os.path.exists('dental_office.db'):
        with app.app_context():
            db = get_db()
            with app.open_resource('schema.sql') as f:
                db.executescript(f.read().decode('utf8'))
            db.commit()
            app.logger.info('Database initialized')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_unique_bill_number():
    """Generate a unique 6-digit bill number"""
    import random
    max_attempts = 100
    
    db = get_db()
    
    for _ in range(max_attempts):
        # Generate random 6-digit number (100000 to 999999)
        bill_number = str(random.randint(100000, 999999))
        
        # Check if this number already exists
        existing = db.execute('SELECT id FROM billing WHERE bill_number = ?', (bill_number,)).fetchone()
        if not existing:
            return bill_number
    
    # Fallback: if we can't find a unique number, raise an error
    raise Exception("Unable to generate unique bill number after 100 attempts")

def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt

def verify_password(password, stored_hash, salt):
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest() == stored_hash

@app.route('/static/<path:filename>')
def serve_static(filename):
    response = send_from_directory('static', filename)
    if filename.endswith('.js') or filename.endswith('.min.js'):
        response.headers['Content-Type'] = 'application/javascript'
    elif filename.endswith('.css') or filename.endswith('.min.css'):
        response.headers['Content-Type'] = 'text/css'
    return response

@app.route('/favicon.ico')
def favicon():
    try:
        # Try to serve from static directory first
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except FileNotFoundError:
        try:
            # Fallback to root directory
            return send_from_directory(app.root_path,
                                       'favicon.ico', mimetype='image/vnd.microsoft.icon')
        except FileNotFoundError:
            # Return empty response to prevent 404 errors
            app.logger.info('Favicon not found, returning empty response')
            return '', 204

@app.route('/')
def index():
    if not os.path.exists('.env'):
        return render_template('first_run.html')
    return redirect(url_for('patient_dashboard' if session.get('user_type') == 'patient' else 'dentist_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user_type = request.form['user_type']
        
        db = get_db()
        if user_type == 'patient':
            user = db.execute('SELECT * FROM patients WHERE LOWER(email) = ?', (email,)).fetchone()
        else:
            user = db.execute('SELECT * FROM dentists WHERE LOWER(email) = ?', (email,)).fetchone()
        
        if user and verify_password(password, user['password_hash'], user['password_salt']):
            session['user_id'] = user['id']
            session['user_type'] = user_type
            session['name'] = user['first_name'] + ' ' + user['last_name']
            return redirect(url_for('patient_dashboard' if user_type == 'patient' else 'dentist_dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    try:
        app.logger.info('Accessing patient dashboard')
        user = get_current_user()
        if not user:
            app.logger.error('No user found in session')
            return redirect(url_for('login'))
        app.logger.info(f'Loading dashboard for patient: {user["id"]}')
        db = get_db()
        
        # Get next appointment (first upcoming appointment)
        next_appointment = db.execute('''
            SELECT a.*, s.name as service_name, 
                   CASE 
                       WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                       ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                   END as dentist_name
        FROM appointments a
        JOIN dental_services s ON a.service_id = s.id
            JOIN dentists d ON a.dentist_id = d.id
            WHERE a.patient_id = ? AND date(a.start_time) >= date('now')
            ORDER BY a.start_time
            LIMIT 1
        ''', (user['id'],)).fetchone()
        app.logger.info(f'Next appointment: {next_appointment}')
        
        # Get recent treatments
        treatments = db.execute('''
            SELECT th.*, s.name as service_name, 
                   CASE 
                       WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                       ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                   END as dentist_name
            FROM treatment_history th
            JOIN dental_services s ON th.service_id = s.id
            JOIN dentists d ON th.dentist_id = d.id
            WHERE th.patient_id = ?
            ORDER BY th.treatment_date DESC
            LIMIT 5
        ''', (user['id'],)).fetchall()
        
        # Convert treatments to list of dicts and parse dates
        treatments_list = []
        for treatment in treatments:
            treatment_dict = dict(treatment)
            treatment_dict['treatment_date'] = datetime.strptime(treatment_dict['treatment_date'], '%Y-%m-%d')
            treatments_list.append(treatment_dict)
            
        app.logger.info(f'Found {len(treatments_list)} recent treatments')
        
        # Get current balance
        balance = db.execute('''
            SELECT COALESCE(SUM(patient_portion), 0) as total
            FROM billing
            WHERE patient_id = ? AND status != 'paid'
        ''', (user['id'],)).fetchone()
        app.logger.info(f'Current balance: {balance["total"]}')
        
        return render_template('patient_dashboard.html',
                             next_appointment=next_appointment,
                             recent_treatments=treatments_list,
                             balance=balance['total'],
                             today=datetime.now().strftime('%Y-%m-%d'),
                             patient_id=user['patient_id'])
    except Exception as e:
        app.logger.error(f'Error in patient dashboard: {str(e)}', exc_info=True)
        flash('An error occurred while loading the dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/dentist/dashboard')
@login_required
def dentist_dashboard():
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    
    # Get all appointments for this dentist
    appointments = db.execute('''
        SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.dentist_id = ?
        ORDER BY a.start_time DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get today's appointments
    today_appointments = db.execute('''
        SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.dentist_id = ? AND date(a.start_time) = date('now')
        ORDER BY a.start_time ASC
    ''', (session['user_id'],)).fetchall()
    
    # Get total patients count for this dentist
    total_patients = db.execute('''
        SELECT COUNT(DISTINCT p.id) as count
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE a.dentist_id = ?
    ''', (session['user_id'],)).fetchone()['count']
    
    # Get pending treatments (scheduled appointments that haven't been completed)
    pending_treatments = db.execute('''
        SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.dentist_id = ? AND a.status IN ('scheduled', 'in_progress')
        ORDER BY a.start_time ASC
    ''', (session['user_id'],)).fetchall()
    
    # Get recent patients (patients with recent appointments)
    recent_patients = db.execute('''
        SELECT DISTINCT p.*, MAX(a.start_time) as last_appointment
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE a.dentist_id = ?
        GROUP BY p.id
        ORDER BY last_appointment DESC
        LIMIT 6
    ''', (session['user_id'],)).fetchall()
    
    # Get recent treatments
    recent_treatments = db.execute('''
        SELECT th.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM treatment_history th
        JOIN patients p ON th.patient_id = p.id
        JOIN dental_services s ON th.service_id = s.id
        WHERE th.dentist_id = ?
        ORDER BY th.treatment_date DESC
        LIMIT 6
    ''', (session['user_id'],)).fetchall()
    
    # Calculate monthly_revenue for this dentist using direct dentist_id
    monthly_revenue = db.execute('''
        SELECT COALESCE(SUM(b.amount), 0)
        FROM billing b
        WHERE b.dentist_id = ? AND strftime('%Y-%m', b.due_date) = strftime('%Y-%m', 'now')
    ''', (session['user_id'],)).fetchone()[0]
    
    return render_template(
        'dentist_dashboard.html',
        appointments=appointments,
        today_appointments=today_appointments,
        total_patients=total_patients,
        pending_treatments=pending_treatments,
        recent_patients=recent_patients,
        recent_treatments=recent_treatments,
        monthly_revenue=monthly_revenue
    )

@app.route('/patient/appointments')
@login_required
def patient_appointments():
    if session['user_type'] != 'patient':
        return redirect(url_for('dentist_dashboard'))
    try:
        app.logger.info('Accessing patient appointments page')
        user = get_current_user()
        if not user:
            app.logger.error('No user found in session')
            return redirect(url_for('login'))
        
        app.logger.info(f'Loading appointments for patient: {user["id"]}')
        db = get_db()
        
        # Get all appointments
        appointments = db.execute('''
            SELECT a.*, s.name as service_name, 
                   CASE 
                       WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                       ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                   END as dentist_name
            FROM appointments a
            JOIN dental_services s ON a.service_id = s.id
            JOIN dentists d ON a.dentist_id = d.id
            WHERE a.patient_id = ?
            ORDER BY a.start_time DESC
        ''', (user['id'],)).fetchall()
        app.logger.info(f'Found {len(appointments)} total appointments')
        
        # Get available services
        services = db.execute('SELECT * FROM dental_services ORDER BY name').fetchall()
        app.logger.info(f'Found {len(services)} available services')
        
        # Get available dentists
        dentists = db.execute('SELECT * FROM dentists ORDER BY name').fetchall()
        app.logger.info(f'Found {len(dentists)} available dentists')
        
        return render_template('patient_appointments.html',
                             appointments=appointments,
                             services=services,
                             dentists=dentists)
    except Exception as e:
        app.logger.error(f'Error in patient appointments: {str(e)}', exc_info=True)
        flash('An error occurred while loading appointments', 'error')
        return redirect(url_for('index'))

@app.route('/patient/billing')
@login_required
def patient_billing():
    if session['user_type'] != 'patient':
        return redirect(url_for('dentist_dashboard'))
    app.logger.info('Accessing patient billing page')
    db = get_db()
    # Calculate current balance
    bill = db.execute('''
        SELECT COALESCE(SUM(patient_portion), 0) as total_due
        FROM billing
        WHERE patient_id = ? AND status != 'paid'
    ''', (session['user_id'],)).fetchone()
    current_balance = bill['total_due'] if bill and bill['total_due'] is not None else 0.0

    # Get next due date
    next_bill = db.execute('''
        SELECT due_date
        FROM billing
        WHERE patient_id = ? AND status != 'paid'
        ORDER BY due_date ASC
        LIMIT 1
    ''', (session['user_id'],)).fetchone()
    due_date = next_bill['due_date'] if next_bill else None

    # Fetch all bills for the patient
    bills = db.execute('''
        SELECT b.*, 
               s.name as service_name, s.description as service_description, s.price as service_price,
               CASE 
                   WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                   ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
               END as dentist_name,
               th.diagnosis, th.treatment_notes, th.treatment_date,
               (b.amount - COALESCE(b.insurance_coverage, 0)) as calculated_patient_portion
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
        LEFT JOIN dentists d ON b.dentist_id = d.id
        LEFT JOIN treatment_history th ON b.reference_number = th.reference_number
        WHERE b.patient_id = ?
        ORDER BY b.due_date DESC
    ''', (session['user_id'],)).fetchall()

    # Fetch payment methods
    payment_methods = db.execute('''
        SELECT id, method_type,
               CASE 
                   WHEN method_type = 'credit_card' THEN '**** **** **** ' || substr(card_number, -4)
                   WHEN method_type = 'banking' THEN bank_name || ' - ****' || substr(account_number, -4)
               END as details,
               is_default
        FROM payment_methods
        WHERE patient_id = ?
        ORDER BY is_default DESC, created_at DESC
    ''', (session['user_id'],)).fetchall()

    # Fetch payment history
    payment_history = db.execute('''
        SELECT p.*, pm.method_type as payment_method
        FROM payments p
        JOIN payment_methods pm ON p.payment_method_id = pm.id
        WHERE p.patient_id = ?
        ORDER BY p.payment_date DESC
    ''', (session['user_id'],)).fetchall()

    return render_template('patient_billing.html',
                         current_balance=current_balance,
                         due_date=due_date,
                         bills=bills,
                         payment_methods=payment_methods,
                         payment_history=payment_history)

@app.route('/patient/history')
@login_required
def patient_treatment_history():
    if session['user_type'] != 'patient':
        return redirect(url_for('dentist_dashboard'))
    
    db = get_db()
    # Get patient information
    patient = db.execute('SELECT * FROM patients WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get appointments
    appointments = db.execute('''
        SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM appointments a
        JOIN dentists d ON a.dentist_id = d.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.patient_id = ?
        ORDER BY a.start_time DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get treatments
    treatments = db.execute('''
        SELECT th.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM treatment_history th
        JOIN dentists d ON th.dentist_id = d.id
        JOIN dental_services s ON th.service_id = s.id
        WHERE th.patient_id = ?
        ORDER BY th.treatment_date DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get bills
    bills = db.execute('''
        SELECT b.*, s.name as service_name
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
        WHERE b.patient_id = ?
        ORDER BY b.due_date DESC
    ''', (session['user_id'],)).fetchall()
    
    return render_template('patient_history.html',
                         patient=patient,
                         appointments=appointments,
                         treatments=treatments,
                         bills=bills)

@app.route('/patient/profile')
@login_required
def patient_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if session['user_type'] == 'patient':
        return render_template('patient_profile.html', patient=user)
    else:
        return render_template('dentist_profile.html', dentist=user)

@app.route('/setup', methods=['POST'])
def setup():
    # Only allow setup if .env does not exist
    if os.path.exists('.env'):
        return redirect(url_for('index'))
    config = request.form.to_dict()
    # Remove any email-related keys if present
    for key in list(config.keys()):
        if key.startswith('MAIL_'):
            del config[key]
    # Write to .env
    with open('.env', 'w') as f:
        for key, value in config.items():
            f.write(f'{key}={value}\n')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.template_filter('status_color')
def status_color(status):
    colors = {
        'scheduled': 'success',
        'completed': 'primary',
        'cancelled': 'danger',
        'in_progress': 'warning',
        'pending': 'warning',
        'paid': 'success',
        'overdue': 'danger'
    }
    return colors.get(status, 'secondary')

@app.template_filter('format_date')
def format_date(date_str, format_type='short'):
    """Format a date string from SQLite into a readable format"""
    if not date_str:
        return 'N/A'
    
    try:
        from datetime import datetime
        # Parse SQLite date string (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
        if ' ' in str(date_str):
            # Has time component
            dt = datetime.strptime(str(date_str)[:19], '%Y-%m-%d %H:%M:%S')
        else:
            # Date only
            dt = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        
        if format_type == 'short':
            return dt.strftime('%b %d, %Y')  # Jan 15, 2024
        elif format_type == 'long':
            return dt.strftime('%B %d, %Y')  # January 15, 2024
        elif format_type == 'datetime':
            return dt.strftime('%B %d, %Y at %I:%M %p')  # January 15, 2024 at 2:30 PM
        elif format_type == 'time':
            return dt.strftime('%I:%M %p')   # 2:30 PM
        elif format_type == 'date_only':
            return dt.strftime('%Y-%m-%d')   # 2024-01-15
        else:
            return dt.strftime('%b %d, %Y')
    except (ValueError, TypeError):
        # If parsing fails, return the first 10 characters (date part)
        return str(date_str)[:10] if date_str else 'N/A'

@app.template_filter('service_class')
def service_class(service_type_or_name):
    """
    Convert service type or name to appropriate CSS class for color coordination.
    Usage: {{ service.type|service_class }} or {{ service.name|service_class }}
    """
    if not service_type_or_name:
        return 'other'
    
    service_input = str(service_type_or_name).lower()
    
    # Direct type mappings
    type_mappings = {
        'cleaning': 'cleaning',
        'filling': 'filling', 
        'whitening': 'whitening',
        'root_canal': 'root_canal',
        'extraction': 'extraction',
        'orthodontics': 'orthodontics',
        'checkup': 'checkup',
        'other': 'other'
    }
    
    # Check direct type match first
    if service_input in type_mappings:
        return type_mappings[service_input]
    
    # Name-based mappings for when service name is passed instead of type
    name_mappings = {
        'regular cleaning': 'cleaning',
        'deep cleaning': 'cleaning',
        'dental cleaning': 'cleaning',
        'cavity filling': 'filling',
        'composite filling': 'filling',
        'teeth whitening': 'whitening',
        'professional whitening': 'whitening',
        'tooth whitening': 'whitening',
        'root canal': 'root_canal',
        'root canal treatment': 'root_canal',
        'tooth extraction': 'extraction',
        'dental extraction': 'extraction',
        'braces': 'orthodontics',
        'orthodontic': 'orthodontics',
        'dental checkup': 'checkup',
        'regular checkup': 'checkup',
        'examination': 'checkup'
    }
    
    # Check name-based mappings
    for name_pattern, service_type in name_mappings.items():
        if name_pattern in service_input:
            return service_type
    
    # Default to 'other' if no match found
    return 'other'

@app.route('/api/services', methods=['GET'])
@login_required
def get_services():
    db = get_db()
    services = db.execute('SELECT * FROM dental_services ORDER BY name').fetchall()
    return jsonify([dict(service) for service in services])

@app.route('/api/dentists', methods=['GET'])
@login_required
def get_dentists():
    db = get_db()
    dentists = db.execute('SELECT id, first_name, last_name FROM dentists ORDER BY last_name').fetchall()
    return jsonify([dict(dentist) for dentist in dentists])

@app.route('/api/appointments', methods=['GET'])
@login_required
def get_appointments():
    db = get_db()
    app.logger.info(f"API: Fetching appointments for user_id={session['user_id']} user_type={session['user_type']}")
    if session['user_type'] == 'patient':
        appointments = db.execute('''
            SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN dentists d ON a.dentist_id = d.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.patient_id = ?
            ORDER BY a.start_time DESC
        ''', (session['user_id'],)).fetchall()
        app.logger.info(f"API: Raw appointments fetched: {appointments}")
        appointments = [dict(appt) for appt in appointments]
        for appt in appointments:
            appt['dentist_name'] = f"{appt.get('dentist_first_name', '')} {appt.get('dentist_last_name', '')}".strip()
    else:
        appointments = db.execute('''
            SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.dentist_id = ?
            ORDER BY a.start_time DESC
        ''', (session['user_id'],)).fetchall()
        app.logger.info(f"API: Raw appointments fetched: {appointments}")
        appointments = [dict(appt) for appt in appointments]
        for appt in appointments:
            appt['dentist_name'] = user['first_name'] + ' ' + user['last_name'] if 'user' in locals() else ''
    result = []
    for appt in appointments:
        appt_dict = dict(appt)
        appt_dict['appointment_id'] = appt_dict.get('id', None)
        appt_dict['sms_reminder'] = appt_dict.get('sms_reminder', True)
        result.append(appt_dict)
    app.logger.info(f"API: Returning appointments JSON: {result}")
    return jsonify(result)

@app.route('/api/appointments/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment(appointment_id):
    db = get_db()
    app.logger.info(f"API: Fetching appointment {appointment_id} for user_id={session['user_id']} user_type={session['user_type']}")
    
    # Get appointment with related data
    appointment = db.execute('''
        SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM appointments a
        JOIN dentists d ON a.dentist_id = d.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()
    
    if not appointment:
        app.logger.warning(f"API: Appointment {appointment_id} not found")
        return jsonify({'error': 'Appointment not found'}), 404
    
    # Check authorization
    if session['user_type'] == 'patient' and appointment['patient_id'] != session['user_id']:
        app.logger.warning(f"API: Unauthorized access attempt to appointment {appointment_id} by patient {session['user_id']}")
        return jsonify({'error': 'Unauthorized'}), 403
    elif session['user_type'] == 'dentist' and appointment['dentist_id'] != session['user_id']:
        app.logger.warning(f"API: Unauthorized access attempt to appointment {appointment_id} by dentist {session['user_id']}")
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Convert to dict and add computed fields
    appointment_dict = dict(appointment)
    appointment_dict['dentist_name'] = f"{appointment['dentist_first_name']} {appointment['dentist_last_name']}"
    appointment_dict['sms_reminder'] = bool(appointment['sms_reminder'])
    
    app.logger.info(f"API: Returning appointment JSON: {appointment_dict}")
    return jsonify(appointment_dict)

@app.route('/api/appointments', methods=['POST'])
@login_required
def create_appointment():
    data = request.get_json()
    required_fields = ['service_id', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    db = get_db()
    try:
        if session['user_type'] == 'patient':
            # For patients, they can only create appointments for themselves
            patient_id = session['user_id']
            dentist_id = data.get('dentist_id')
            if not dentist_id:
                return jsonify({'error': 'Dentist ID is required'}), 400
        else:
            # For dentists, they can create appointments for any patient
            dentist_id = session['user_id']
            patient_id = data.get('patient_id')
            if not patient_id:
                return jsonify({'error': 'Patient ID is required'}), 400
        
        cursor = db.execute('''
            INSERT INTO appointments (
                patient_id, dentist_id, service_id, type, status, start_time, end_time,
                notes, sms_reminder
            ) VALUES (?, ?, ?, ?, 'scheduled', ?, ?, ?, ?)
        ''', (
            patient_id,
            dentist_id,
            data['service_id'],
            data.get('type', 'checkup'),
            data['start_time'],
            data['end_time'],
            data.get('notes', ''),
            int(data.get('sms_reminder', True))
        ))
        db.commit()
        
        appointment_id = cursor.lastrowid
        appointment = db.execute('''
            SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN dentists d ON a.dentist_id = d.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()
        
        # Send SMS reminder if enabled
        if int(data.get('sms_reminder', True)):
            # Fetch patient phone and appointment details
            patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
            dentist = db.execute('SELECT * FROM dentists WHERE id = ?', (dentist_id,)).fetchone()
            service = db.execute('SELECT * FROM dental_services WHERE id = ?', (data['service_id'],)).fetchone()
            if patient and dentist and service:
                try:
                    mfa = SignalWireMFA(
                        SIGNALWIRE_PROJECT_ID,
                        SIGNALWIRE_TOKEN,
                        SIGNALWIRE_SPACE,
                        os.getenv('FROM_NUMBER')
                    )
                    appt_date = data['start_time'][:10]
                    appt_time = data['start_time'][11:16]
                    sms_body = f"Your appointment for {service['name']} with Dr. {dentist['first_name']} {dentist['last_name']} is scheduled for {appt_date} at {appt_time}."
                    mfa.client.messages.create(
                        from_=os.getenv('FROM_NUMBER'),
                        to=patient['phone'],
                        body=sms_body
                    )
                except Exception as e:
                    app.logger.error(f"Failed to send SMS reminder: {e}")
        
        return jsonify(dict(appointment)), 201
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment(appointment_id):
    db = get_db()
    appointment = db.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
    
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404
    
    if session['user_type'] == 'patient' and appointment['patient_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    elif session['user_type'] == 'dentist' and appointment['dentist_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    allowed_fields = ['status', 'notes']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    try:
        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        query = f'UPDATE appointments SET {set_clause} WHERE id = ?'
        db.execute(query, list(updates.values()) + [appointment_id])
        db.commit()
        
        updated_appointment = db.execute('''
            SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN dentists d ON a.dentist_id = d.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()
        
        # Send SMS reminder if enabled
        if int(data.get('sms_reminder', True)):
            # Fetch patient phone and appointment details
            patient = db.execute('SELECT * FROM patients WHERE id = ?', (appointment['patient_id'],)).fetchone()
            dentist = db.execute('SELECT * FROM dentists WHERE id = ?', (appointment['dentist_id'],)).fetchone()
            service = db.execute('SELECT * FROM dental_services WHERE id = ?', (appointment['service_id'],)).fetchone()
            if patient and dentist and service:
                try:
                    mfa = SignalWireMFA(
                        SIGNALWIRE_PROJECT_ID,
                        SIGNALWIRE_TOKEN,
                        SIGNALWIRE_SPACE,
                        os.getenv('FROM_NUMBER')
                    )
                    appt_date = appointment['start_time'][:10]
                    appt_time = appointment['start_time'][11:16]
                    sms_body = f"Your appointment for {service['name']} with Dr. {dentist['first_name']} {dentist['last_name']} has been rescheduled to {appt_date} at {appt_time}."
                    mfa.client.messages.create(
                        from_=os.getenv('FROM_NUMBER'),
                        to=patient['phone'],
                        body=sms_body
                    )
                except Exception as e:
                    app.logger.error(f"Failed to send SMS reminder: {e}")
        
        return jsonify(dict(updated_appointment))
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def delete_appointment(appointment_id):
    db = get_db()
    appointment = db.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
    
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404
    
    if session['user_type'] == 'patient' and appointment['patient_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    elif session['user_type'] == 'dentist' and appointment['dentist_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
        db.commit()
        return '', 204
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment_api(appointment_id):
    db = get_db()
    appointment = db.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
    
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404
    
    if session['user_type'] == 'patient' and appointment['patient_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    elif session['user_type'] == 'dentist' and appointment['dentist_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Update appointment status to cancelled instead of deleting
        db.execute('UPDATE appointments SET status = ? WHERE id = ?', ('cancelled', appointment_id))
        db.commit()
        
        # Get updated appointment details for response
        updated_appointment = db.execute('''
            SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN dentists d ON a.dentist_id = d.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()
        
        # Send SMS notification if enabled
        if appointment['sms_reminder']:
            try:
                patient = db.execute('SELECT * FROM patients WHERE id = ?', (appointment['patient_id'],)).fetchone()
                if patient and patient['phone']:
                    mfa = SignalWireMFA(
                        SIGNALWIRE_PROJECT_ID,
                        SIGNALWIRE_TOKEN,
                        SIGNALWIRE_SPACE,
                        os.getenv('FROM_NUMBER')
                    )
                    
                    # Format the appointment time for SMS
                    appt_date = datetime.fromisoformat(appointment['start_time']).strftime('%A, %B %d, %Y')
                    appt_time = datetime.fromisoformat(appointment['start_time']).strftime('%I:%M %p')
                    
                    sms_body = f"Your appointment for {updated_appointment['service_name']} with Dr. {updated_appointment['dentist_first_name']} {updated_appointment['dentist_last_name']} scheduled for {appt_date} at {appt_time} has been cancelled."
                    
                    mfa.client.messages.create(
                        from_=os.getenv('FROM_NUMBER'),
                        to=patient['phone'],
                        body=sms_body
                    )
                    app.logger.info(f"SMS cancellation notification sent to {patient['phone']}")
            except Exception as sms_error:
                app.logger.error(f"Failed to send SMS cancellation notification: {sms_error}")
                # Don't fail the cancellation if SMS fails
        
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': dict(updated_appointment)
        }), 200
        
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments/<int:appointment_id>/reschedule', methods=['POST'])
@login_required
def reschedule_appointment(appointment_id):
    db = get_db()
    data = request.get_json()
    
    # Get the existing appointment
    appointment = db.execute('''
        SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM appointments a
        JOIN dentists d ON a.dentist_id = d.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()
    
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404
    
    # Check authorization
    if session['user_type'] == 'patient' and appointment['patient_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    elif session['user_type'] == 'dentist' and appointment['dentist_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Parse the new date and time slot
        new_date = data.get('date')
        time_slot = data.get('time_slot')
        notes = data.get('notes', '')
        
        if not new_date or not time_slot:
            return jsonify({'error': 'Date and time slot are required'}), 400
        
        # Convert time slot to actual times
        start_time = None
        end_time = None
        if time_slot == 'morning':
            start_time = f"{new_date}T08:00:00"
            end_time = f"{new_date}T11:00:00"
        elif time_slot == 'afternoon':
            start_time = f"{new_date}T14:00:00"
            end_time = f"{new_date}T16:00:00"
        elif time_slot == 'evening':
            start_time = f"{new_date}T18:00:00"
            end_time = f"{new_date}T20:00:00"
        elif time_slot == 'all_day':
            start_time = f"{new_date}T08:00:00"
            end_time = f"{new_date}T20:00:00"
        else:
            logging.warning(f"[SWAIG] Invalid time slot: {time_slot}")
            return SWAIGResponse("Invalid time slot", status=400)
        
        # Update the appointment
        db.execute('''
            UPDATE appointments 
            SET start_time = ?, end_time = ?, notes = ?
            WHERE id = ?
        ''', (start_time, end_time, notes, appointment_id))
        db.commit()
        
        # Get the updated appointment
        updated_appointment = db.execute('''
            SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN dentists d ON a.dentist_id = d.id
            JOIN dental_services s ON a.service_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()
        
        # Send SMS reminder if enabled
        if appointment['sms_reminder']:
            try:
                patient = db.execute('SELECT * FROM patients WHERE id = ?', (appointment['patient_id'],)).fetchone()
                if patient:
                    mfa = SignalWireMFA(
                        SIGNALWIRE_PROJECT_ID,
                        SIGNALWIRE_TOKEN,
                        SIGNALWIRE_SPACE,
                        os.getenv('FROM_NUMBER')
                    )
                    sms_body = f"Your appointment for {updated_appointment['service_name']} with Dr. {updated_appointment['dentist_first_name']} {updated_appointment['dentist_last_name']} has been rescheduled to {new_date} at {start_time[11:16]}."
                    mfa.client.messages.create(
                        from_=os.getenv('FROM_NUMBER'),
                        to=patient['phone'],
                        body=sms_body
                    )
            except Exception as e:
                app.logger.error(f"Failed to send SMS reminder: {e}")
        
        return jsonify(dict(updated_appointment))
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/treatment-history', methods=['GET'])
@login_required
def get_treatment_history():
    db = get_db()
    if session['user_type'] == 'patient':
        history = db.execute('''
            SELECT th.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   s.name as service_name
            FROM treatment_history th
            JOIN dentists d ON th.dentist_id = d.id
            JOIN dental_services s ON th.service_id = s.id
            WHERE th.patient_id = ?
            ORDER BY th.treatment_date DESC
        ''', (session['user_id'],)).fetchall()
    else:
        history = db.execute('''
            SELECT th.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
                   s.name as service_name
            FROM treatment_history th
            JOIN patients p ON th.patient_id = p.id
            JOIN dental_services s ON th.service_id = s.id
            WHERE th.dentist_id = ?
            ORDER BY th.treatment_date DESC
        ''', (session['user_id'],)).fetchall()
    return jsonify([dict(record) for record in history])

@app.route('/api/billing', methods=['GET'])
@login_required
def get_billing():
    db = get_db()
    if session['user_type'] == 'patient':
        bills = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, s.name as service_name
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            WHERE b.patient_id = ?
            ORDER BY b.due_date DESC
        ''', (session['user_id'],)).fetchall()
    else:
        bills = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, s.name as service_name
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            WHERE b.dentist_id = ?
            ORDER BY b.due_date DESC
        ''', (session['user_id'],)).fetchall()
    return jsonify([dict(record) for record in bills])

@app.route('/api/insurance-claims', methods=['GET'])
@login_required
def get_insurance_claims():
    if session['user_type'] != 'patient':
        return jsonify({'error': 'Only patients can view insurance claims'}), 403
    
    db = get_db()
    claims = db.execute('''
        SELECT ic.*, s.name as service_name
        FROM insurance_claims ic
        JOIN dental_services s ON ic.service_id = s.id
        WHERE ic.patient_id = ?
        ORDER BY ic.submission_date DESC
    ''', (session['user_id'],)).fetchall()
    return jsonify([dict(claim) for claim in claims])

@app.route('/api/calendar/available-slots', methods=['GET'])
@login_required
def get_available_slots():
    dentist_id = request.args.get('dentist_id')
    date = request.args.get('date')
    
    if not dentist_id or not date:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    db = get_db()
    
    # Get dentist's working hours
    dentist = db.execute('SELECT working_hours FROM dentists WHERE id = ?', (dentist_id,)).fetchone()
    if not dentist:
        return jsonify({'error': 'Dentist not found'}), 404
    
    working_hours = json.loads(dentist['working_hours'])
    day_of_week = date_obj.strftime('%A').lower()
    
    if day_of_week not in working_hours:
        return jsonify({'error': 'Dentist not available on this day'}), 400
    
    # Get booked appointments for the day
    booked_slots = db.execute('''
        SELECT start_time
        FROM appointments
        WHERE dentist_id = ? AND date(start_time) = ? AND status != 'cancelled'
    ''', (dentist_id, date)).fetchall()
    booked_times = [datetime.fromisoformat(slot['start_time']).strftime('%H:%M') for slot in booked_slots]
    
    # Generate available slots
    available_slots = []
    start_time = datetime.strptime(working_hours[day_of_week]['start'], '%H:%M')
    end_time = datetime.strptime(working_hours[day_of_week]['end'], '%H:%M')
    slot_duration = timedelta(minutes=30)  # 30-minute slots
    
    current_time = start_time
    while current_time + slot_duration <= end_time:
        slot_time = current_time.strftime('%H:%M')
        if slot_time not in booked_times:
            available_slots.append(slot_time)
        current_time += slot_duration
    
    return jsonify(available_slots)

@app.route('/api/calendar/dentist-schedule', methods=['GET'])
@login_required
def get_dentist_schedule():
    dentist_id = request.args.get('dentist_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not all([dentist_id, start_date, end_date]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    db = get_db()
    
    # Get dentist's working hours
    dentist = db.execute('SELECT working_hours FROM dentists WHERE id = ?', (dentist_id,)).fetchone()
    if not dentist:
        return jsonify({'error': 'Dentist not found'}), 404
    
    working_hours = json.loads(dentist['working_hours'])
    
    # Get appointments for the date range
    appointments = db.execute('''
        SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.dentist_id = ? AND a.appointment_date BETWEEN ? AND ?
        ORDER BY a.appointment_date, a.appointment_time
    ''', (dentist_id, start_date, end_date)).fetchall()
    
    schedule = []
    current_date = start_date_obj
    while current_date <= end_date_obj:
        day_of_week = current_date.strftime('%A').lower()
        date_str = current_date.strftime('%Y-%m-%d')
        
        if day_of_week in working_hours:
            day_schedule = {
                'date': date_str,
                'working_hours': working_hours[day_of_week],
                'appointments': []
            }
            
            # Add appointments for this day
            for appointment in appointments:
                if appointment['appointment_date'] == date_str:
                    day_schedule['appointments'].append(dict(appointment))
            
            schedule.append(day_schedule)
        
        current_date += timedelta(days=1)
    
    return jsonify(schedule)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/api/password/reset/lookup', methods=['POST'])
def api_password_reset_lookup():
    """Look up user by email for password reset"""
    try:
        data = request.get_json()
        app.logger.info(f'Password reset lookup request: {data}')
        
        if not data:
            app.logger.error('No JSON data received')
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        user_type = data.get('user_type', 'patient')  # Default to patient if not specified
        
        app.logger.info(f'Extracted email: "{email}", user_type: "{user_type}"')
        
        if not email:
            app.logger.error('Email field is empty or missing')
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        db = get_db()
        
        # Look up user in appropriate table
        if user_type == 'dentist':
            user = db.execute('SELECT id, first_name, last_name, email, phone FROM dentists WHERE LOWER(email) = ?', (email,)).fetchone()
        else:
            user = db.execute('SELECT id, first_name, last_name, email, phone FROM patients WHERE LOWER(email) = ?', (email,)).fetchone()
        
        if not user:
            # Don't reveal whether user exists for security
            return jsonify({'success': False, 'error': 'No user found with that email address'}), 404
            
        # Check if user has a phone number
        if not user['phone']:
            return jsonify({'success': False, 'error': 'No phone number on file for this account'}), 400
            
        return jsonify({
            'success': True,
            'message': 'User found',
            'has_phone': bool(user['phone'])
        })
        
    except Exception as e:
        app.logger.error(f'Password reset lookup error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/password/reset/initiate', methods=['POST'])
def api_password_reset_initiate():
    """Send MFA code for password reset using SignalWire MFA system"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        user_type = data.get('user_type', 'patient')
        action = data.get('action', 'forgot_password')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        db = get_db()
        
        # Look up user
        if user_type == 'dentist':
            user = db.execute('SELECT id, first_name, last_name, email, phone FROM dentists WHERE LOWER(email) = ?', (email,)).fetchone()
        else:
            user = db.execute('SELECT id, first_name, last_name, email, phone FROM patients WHERE LOWER(email) = ?', (email,)).fetchone()
        
        if not user:
            # Don't reveal whether user exists for security
            return jsonify({'success': False, 'error': 'No user found with that email address'}), 404
            
        # Check if user has a phone number
        if not user['phone']:
            return jsonify({'success': False, 'error': 'No phone number on file for this account'}), 400
            
        # Use SignalWire MFA system (same as test-mfa)
        try:
            mfa = SignalWireMFA(
                SIGNALWIRE_PROJECT_ID,
                SIGNALWIRE_TOKEN,
                SIGNALWIRE_SPACE,
                os.getenv('FROM_NUMBER')
            )
            response = mfa.send_mfa(user['phone'])
            mfa_id = response.get('id')
            
            if not mfa_id:
                app.logger.error('MFA ID not found in SignalWire response')
                return jsonify({'success': False, 'error': 'Failed to send verification code'}), 500
            
            # Store the password reset request in our database for tracking
            reset_id = str(uuid.uuid4())
            expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            
            db.execute('''
                INSERT INTO password_resets (id, user_id, user_type, email, mfa_code, expires_at, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (reset_id, user['id'], user_type, email, mfa_id, expires_at, False))
            db.commit()
            
            app.logger.info(f'Password reset MFA sent to {user["phone"]} for {email}')
            
            return jsonify({
                'success': True,
                'mfa_id': mfa_id,
                'message': f'Verification code sent to {user["phone"]}'
            })
            
        except Exception as e:
            app.logger.error(f'Failed to send MFA for password reset: {e}')
            return jsonify({'success': False, 'error': 'Failed to send verification code'}), 500
            
    except Exception as e:
        app.logger.error(f'Password reset initiate error: {e}')
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@app.route('/api/password/reset/complete', methods=['POST'])
def api_password_reset_complete():
    """Verify MFA code and optionally reset password using SignalWire MFA system"""
    try:
        data = request.get_json()
        mfa_id = data.get('mfa_id')
        code = data.get('code')
        new_password = data.get('new_password')
        action = data.get('action', 'reset_password')
        reset_token = data.get('reset_token')  # For password reset after MFA verification
        
        app.logger.info(f'Password reset request: action={action}, mfa_id={mfa_id}, has_reset_token={bool(reset_token)}')
        
        db = get_db()
        
        # If we have a reset_token, this is the final password reset step
        if reset_token and new_password:
            # Find the verified reset request using the token
            reset_request = db.execute('''
                SELECT * FROM password_resets 
                WHERE id = ? AND verified = 1
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (reset_token,)).fetchone()
            
            if not reset_request:
                return jsonify({'success': False, 'error': 'Invalid or expired reset session'}), 404
            
            # Check if request has expired
            expires_at = datetime.fromisoformat(reset_request['expires_at'])
            if datetime.utcnow() > expires_at:
                return jsonify({'success': False, 'error': 'Reset session has expired'}), 400
            
            # Validate new password
            if len(new_password) < 8:
                return jsonify({'success': False, 'error': 'Password must be at least 8 characters long'}), 400
            
            # Hash the new password
            password_hash, salt = hash_password(new_password)
            
            # Update password in appropriate table
            if reset_request['user_type'] == 'dentist':
                db.execute('UPDATE dentists SET password_hash = ?, password_salt = ? WHERE id = ?', 
                          (password_hash, salt, reset_request['user_id']))
            else:
                db.execute('UPDATE patients SET password_hash = ?, password_salt = ? WHERE id = ?', 
                          (password_hash, salt, reset_request['user_id']))
            
            # Clean up the reset request
            db.execute('DELETE FROM password_resets WHERE id = ?', (reset_request['id'],))
            db.commit()
            
            app.logger.info(f'Password reset completed for {reset_request["user_type"]} {reset_request["email"]}')
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully! You can now log in with your new password.'
            })
        
        # Otherwise, this is MFA verification step
        if not mfa_id or not code:
            return jsonify({'success': False, 'error': 'Missing MFA ID or verification code'}), 400
        
        app.logger.info(f'Password reset MFA verification attempt for MFA ID: {mfa_id}')
        
        # Check if we have a valid password reset request
        reset_request = db.execute('''
            SELECT * FROM password_resets 
            WHERE mfa_code = ? AND verified = 0
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (mfa_id,)).fetchone()
        
        if not reset_request:
            return jsonify({'success': False, 'error': 'Password reset request not found or already used'}), 404
        
        # Check if request has expired (15 minutes)
        expires_at = datetime.fromisoformat(reset_request['expires_at'])
        if datetime.utcnow() > expires_at:
            return jsonify({
                'success': False, 
                'error': 'Verification session has expired. Please request a new password reset.',
                'expired': True
            }), 400
        
        # Verify the MFA code using SignalWire (only once!)
        try:
            mfa = SignalWireMFA(
                SIGNALWIRE_PROJECT_ID,
                SIGNALWIRE_TOKEN,
                SIGNALWIRE_SPACE,
                os.getenv('FROM_NUMBER')
            )
            result = mfa.verify_mfa(mfa_id, code)
            
            if not result.get('success'):
                error_msg = result.get('message', 'Invalid verification code')
                app.logger.warning(f'SignalWire MFA verification failed: {error_msg}')
                return jsonify({'success': False, 'error': error_msg}), 401
                
        except Exception as e:
            app.logger.error(f'SignalWire MFA verification failed: {e}')
            
            # Check if this is a 404 error (expired MFA session)
            if "404" in str(e):
                return jsonify({
                    'success': False, 
                    'error': 'Verification code has expired. Please request a new password reset.',
                    'expired': True
                }), 401
            else:
                return jsonify({'success': False, 'error': 'Verification failed. Please try again.'}), 500
        
        # MFA verification successful - mark as verified
        db.execute('UPDATE password_resets SET verified = 1 WHERE id = ?', (reset_request['id'],))
        db.commit()
        
        app.logger.info(f'Password reset MFA verified successfully for {reset_request["email"]}')
        
        # Return the reset token for the password reset step
        return jsonify({
            'success': True, 
            'message': 'Verification successful',
            'reset_token': reset_request['id']  # Use the reset request ID as the token
        })
        
    except Exception as e:
        app.logger.error(f'Password reset complete error: {e}')
        return jsonify({'success': False, 'error': 'An error occurred processing your request'}), 500

@app.route('/appointments')
def appointments():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user['role'] == 'patient':
        return render_template('patient_appointments.html', appointments=get_patient_appointments(user['id']), patient=user)
    elif user['role'] == 'dentist':
        return render_template('dentist_appointments.html', appointments=get_dentist_appointments(user['id']), patient=user)
    else:
        return render_template('patient_appointments.html', appointments=[], patient=user)

@app.route('/billing')
def billing():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user['role'] == 'patient':
        return render_template('patient_billing.html', bills=get_patient_bills(user['id']), patient=user)
    elif user['role'] == 'dentist':
        return render_template('dentist_billing.html', bills=get_dentist_bills(user['id']), patient=user)
    else:
        return render_template('patient_billing.html', bills=[], patient=user)

# CSRF Protection
def csrf_protect():
    csrf_enabled = app.config['ENABLE_CSRF']
    app.logger.debug(f'[CSRF] Protection check - CSRF enabled: {csrf_enabled}, Path: {request.path}, Method: {request.method}')
    
    if csrf_enabled:
        # Skip CSRF protection for SWAIG endpoints
        if request.path == '/swaig':
            app.logger.debug('[CSRF] Skipping CSRF protection for SWAIG endpoint')
            return None
            
        # Skip CSRF protection for password reset endpoints
        if request.path.startswith('/api/password/reset/'):
            app.logger.debug('[CSRF] Skipping CSRF protection for password reset endpoint')
            return None
            
        # Skip CSRF protection for first-run setup
        if request.path == '/setup':
            app.logger.debug('[CSRF] Skipping CSRF protection for setup endpoint')
            return None
            
        if request.method == "POST":
            app.logger.info(f'[CSRF] Validating POST request to {request.path}')
            
            # Check for CSRF token in form data first
            token = request.form.get('csrf_token')
            token_source = 'form data'
            
            # If not found in form data, check headers
            if not token:
                token = request.headers.get('X-CSRFToken')
                token_source = 'headers'
            
            # If still not found and request has JSON data, check there too
            if not token and request.is_json:
                try:
                    data = request.get_json()
                    if data:
                        token = data.get('csrf_token')
                        token_source = 'JSON data'
                except:
                    pass
            
            session_token = session.get('csrf_token')
            
            app.logger.info(f'[CSRF] Token from {token_source}: {token[:8] + "..." if token and len(token) > 8 else token}')
            app.logger.info(f'[CSRF] Session token: {session_token[:8] + "..." if session_token and len(session_token) > 8 else session_token}')
            
            if not token or token != session_token:
                app.logger.warning(f'[CSRF] VALIDATION FAILED - Expected: {session_token}, Got: {token}, Source: {token_source}')
                abort(403)
            else:
                app.logger.info(f'[CSRF] VALIDATION SUCCESSFUL - Token matched from {token_source}')
    else:
        app.logger.debug('[CSRF] Protection disabled - skipping validation')
    return None

@app.before_request
def before_request():
    if app.config['ENABLE_CSRF']:
        if 'csrf_token' not in session:
            new_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            session['csrf_token'] = new_token
            app.logger.info(f'[CSRF] Generated new CSRF token: {new_token[:8]}...')
        else:
            app.logger.debug(f'[CSRF] Using existing CSRF token: {session["csrf_token"][:8]}...')
        csrf_protect()
    else:
        app.logger.debug('[CSRF] CSRF protection disabled - skipping before_request checks')

@app.context_processor
def inject_csrf_token():
    if app.config['ENABLE_CSRF']:
        return dict(csrf_token=lambda: session.get('csrf_token'))
    # Provide a dummy token if CSRF is disabled
    return dict(csrf_token=lambda: "FAKE_CSRF_TOKEN")

@app.route('/dentist/appointments')
@login_required
def dentist_appointments():
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    appointments = db.execute('''
        SELECT a.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.dentist_id = ?
        ORDER BY a.start_time DESC
    ''', (session['user_id'],)).fetchall()
    return render_template('dentist_appointments.html', appointments=appointments)

@app.route('/dentist/patients')
@login_required
def dentist_patients():
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    # Get all unique patients who have appointments with this dentist
    patients = db.execute('''
        SELECT DISTINCT p.*
        FROM patients p
        JOIN appointments a ON a.patient_id = p.id
        WHERE a.dentist_id = ?
        ORDER BY p.last_name, p.first_name
    ''', (session['user_id'],)).fetchall()
    return render_template('dentist_patients.html', patients=patients)

@app.route('/dentist/treatment-records')
@login_required
def dentist_treatment_records():
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    treatments = db.execute('''
        SELECT th.*, p.first_name as patient_first_name, p.last_name as patient_last_name,
               s.name as service_name
        FROM treatment_history th
        JOIN patients p ON th.patient_id = p.id
        JOIN dental_services s ON th.service_id = s.id
        WHERE th.dentist_id = ?
        ORDER BY th.treatment_date DESC
    ''', (session['user_id'],)).fetchall()
    return render_template('dentist_treatment_records.html', treatments=treatments)

@app.route('/dentist/billing')
@login_required
def dentist_billing():
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    
    # Calculate total outstanding balance for all patients of this dentist
    balance = db.execute('''
        SELECT COALESCE(SUM(b.patient_portion), 0) as total
        FROM billing b
        WHERE b.dentist_id = ? AND b.status != 'paid'
    ''', (session['user_id'],)).fetchone()
    current_balance = balance['total'] if balance and balance['total'] is not None else 0.0

    # Get next due date
    next_bill = db.execute('''
        SELECT b.due_date
        FROM billing b
        WHERE b.dentist_id = ? AND b.status != 'paid'
        ORDER BY b.due_date ASC
        LIMIT 1
    ''', (session['user_id'],)).fetchone()
    due_date = next_bill['due_date'] if next_bill else None

    # Fetch all bills for the dentist's patients
    bills = db.execute('''
        SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, s.name as service_name,
               p.first_name || ' ' || p.last_name as patient_name
        FROM billing b
        LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
        JOIN dental_services s ON b.service_id = s.id
        JOIN patients p ON b.patient_id = p.id
        WHERE b.dentist_id = ?
        ORDER BY b.due_date DESC
    ''', (session['user_id'],)).fetchall()

    # Fetch payment history
    payment_history = db.execute('''
        SELECT p.*, pm.method_type as payment_method,
               pat.first_name || ' ' || pat.last_name as patient_name
        FROM payments p
        JOIN payment_methods pm ON p.payment_method_id = pm.id
        JOIN billing b ON p.billing_id = b.id
        JOIN patients pat ON b.patient_id = pat.id
        WHERE b.dentist_id = ?
        ORDER BY p.payment_date DESC
    ''', (session['user_id'],)).fetchall()

    return render_template('dentist_billing.html',
                         current_balance=current_balance,
                         due_date=due_date,
                         bills=bills,
                         payment_history=payment_history)

@app.route('/dentist/profile')
@login_required
def dentist_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if session['user_type'] == 'dentist':
        return render_template('dentist_profile.html', dentist=user)
    else:
        return render_template('patient_profile.html', patient=user)

@app.route('/dentist/profile/update', methods=['POST'])
@login_required
def update_dentist_profile():
    if session['user_type'] != 'dentist':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    db = get_db()
    user_id = session['user_id']
    # Get form data
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    specialization = request.form.get('specialization')
    working_hours = request.form.get('working_hours')
    try:
        db.execute('''
            UPDATE dentists SET first_name=?, last_name=?, email=?, phone=?, specialization=?, working_hours=?
            WHERE id=?
        ''', (first_name, last_name, email, phone, specialization, working_hours, user_id))
        db.commit()
        session['name'] = f"{first_name} {last_name}"
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})

def get_current_user():
    if 'user_id' not in session or 'user_type' not in session:
        return None
    db = get_db()
    if session['user_type'] == 'patient':
        return db.execute('SELECT * FROM patients WHERE id = ?', (session['user_id'],)).fetchone()
    elif session['user_type'] == 'dentist':
        return db.execute('SELECT * FROM dentists WHERE id = ?', (session['user_id'],)).fetchone()
    return None

@app.route('/api/make-payment', methods=['POST'])
@login_required
def make_payment():
    data = request.get_json()
    billing_id = data.get('billing_id')
    payment_method_id = data.get('payment_method_id')
    amount = data.get('amount')
    notes = data.get('notes', '')

    if not all([billing_id, payment_method_id, amount]):
        return jsonify({'error': 'Missing required fields'}), 400

    db = get_db()
    try:
        # Fetch payment method type
        method = db.execute('SELECT method_type FROM payment_methods WHERE id = ?', (payment_method_id,)).fetchone()
        if not method:
            return jsonify({'error': 'Invalid payment method'}), 400
        payment_method_type = method['method_type']

        # Fetch current patient_portion and status
        bill = db.execute('SELECT patient_portion, status FROM billing WHERE id = ?', (billing_id,)).fetchone()
        if not bill:
            return jsonify({'error': 'Invalid bill'}), 400

        new_portion = bill['patient_portion'] - amount
        if new_portion > 0:
            new_status = 'partial'
        else:
            new_status = 'paid'
            new_portion = 0

        # Insert payment record
        cursor = db.execute('''
            INSERT INTO payments (billing_id, patient_id, amount, payment_date, payment_method_id, payment_method_type, status, transaction_id, notes)
            VALUES (?, ?, ?, datetime('now'), ?, ?, 'completed', ?, ?)
        ''', (billing_id, session['user_id'], amount, payment_method_id, payment_method_type, secrets.token_hex(8), notes))
        db.commit()

        # Update billing record
        db.execute('UPDATE billing SET patient_portion = ?, status = ? WHERE id = ?', (new_portion, new_status, billing_id))
        db.commit()

        # Send SMS confirmation for payment
        try:
            # Get payment and bill details for SMS
            payment_details = db.execute('''
                SELECT b.*, s.name as service_name, p.phone, pm.method_type,
                       CASE 
                           WHEN pm.method_type = 'credit_card' THEN '**** **** **** ' || substr(pm.card_number, -4)
                           WHEN pm.method_type = 'banking' THEN pm.bank_name || ' - ****' || substr(pm.account_number, -4)
                       END as payment_method_details
                FROM billing b
                JOIN dental_services s ON b.service_id = s.id
                JOIN patients p ON b.patient_id = p.id
                JOIN payment_methods pm ON pm.id = ?
                WHERE b.id = ?
            ''', (payment_method_id, billing_id)).fetchone()
            
            if payment_details and payment_details['phone']:
                # Convert to dict for easier access
                payment_details_dict = dict(payment_details)
                
                mfa = SignalWireMFA(
                    SIGNALWIRE_PROJECT_ID,
                    SIGNALWIRE_TOKEN,
                    SIGNALWIRE_SPACE,
                    os.getenv('FROM_NUMBER')
                )
                
                sms_body = f"Payment confirmation: ${amount:.2f} payment received for {payment_details_dict['service_name']}. "
                if new_portion > 0:
                    sms_body += f"Remaining balance: ${new_portion:.2f}."
                else:
                    sms_body += "Bill is now fully paid."
                
                sms_body += f" Payment Ref: {secrets.token_hex(4).upper()}"
                if payment_details_dict['reference_number']:
                    sms_body += f" | Bill Ref: {payment_details_dict['reference_number']}"
                
                mfa.client.messages.create(
                    from_=os.getenv('FROM_NUMBER'),
                    to=payment_details_dict['phone'],
                    body=sms_body
                )
                print(f"[SWAIG][CONSOLE] SMS payment confirmation sent to {payment_details_dict['phone']}")
                logging.info(f"[SWAIG] SMS payment confirmation sent to {payment_details_dict['phone']}")
        except Exception as sms_error:
            print(f"[SWAIG][CONSOLE] Failed to send SMS payment confirmation: {sms_error}")
            logging.error(f"[SWAIG] Failed to send SMS payment confirmation: {sms_error}")
            # Don't fail the payment if SMS fails
        
        print(f"[SWAIG][CONSOLE] Payment successful for bill {billing_id}, patient {session['user_id']}, amount ${amount}")
        logging.info(f"[SWAIG] Payment successful for bill {billing_id}, patient {session['user_id']}, amount ${amount}")
        return jsonify({'success': True, 'message': f"Payment of ${amount:.2f} processed successfully. Remaining balance: ${new_portion:.2f}", 'patient_id': session['user_id'], 'amount_paid': amount, 'remaining_balance': new_portion})
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-payment-method', methods=['POST'])
@login_required
def add_payment_method():
    if session['user_type'] != 'patient':
        return jsonify({'error': 'Only patients can add payment methods'}), 403
    
    data = request.get_json()
    method_type = data.get('method_type')
    
    if method_type not in ['credit_card', 'banking']:
        return jsonify({'error': 'Invalid payment method type'}), 400
    
    db = get_db()
    try:
        if method_type == 'credit_card':
            card_number = data.get('card_number')
            expiry_date = data.get('expiry_date')
            card_holder = data.get('card_holder')
            
            if not all([card_number, expiry_date, card_holder]):
                return jsonify({'error': 'Missing required credit card fields'}), 400
            
            # Store only last 4 digits for security
            masked_card_number = '**** **** **** ' + card_number[-4:]
            
            db.execute('''
                INSERT INTO payment_methods (patient_id, method_type, card_number, expiry_date, card_holder)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], method_type, card_number, expiry_date, card_holder))
        
        else:  # banking
            bank_name = data.get('bank_name')
            account_number = data.get('account_number')
            routing_number = data.get('routing_number')
            
            if not all([bank_name, account_number, routing_number]):
                return jsonify({'error': 'Missing required banking fields'}), 400
            
            db.execute('''
                INSERT INTO payment_methods (patient_id, method_type, bank_name, account_number, routing_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], method_type, bank_name, account_number, routing_number))
        
        db.commit()
        return jsonify({'success': True, 'message': 'Payment method added successfully'})
    
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/remove-payment-method', methods=['POST'])
@login_required
def remove_payment_method():
    if session['user_type'] != 'patient':
        return jsonify({'error': 'Only patients can remove payment methods'}), 403
    
    data = request.get_json()
    method_id = data.get('method_id')
    
    if not method_id:
        return jsonify({'error': 'Payment method ID required'}), 400
    
    db = get_db()
    try:
        # Verify the payment method belongs to the current patient
        method = db.execute('SELECT id FROM payment_methods WHERE id = ? AND patient_id = ?', 
                          (method_id, session['user_id'])).fetchone()
        
        if not method:
            return jsonify({'error': 'Payment method not found or access denied'}), 404
        
        # Check if this payment method is being used in any pending transactions
        pending_payments = db.execute('''
            SELECT COUNT(*) as count FROM payments 
            WHERE payment_method_id = ? AND status = 'pending'
        ''', (method_id,)).fetchone()
        
        if pending_payments['count'] > 0:
            return jsonify({'error': 'Cannot remove payment method with pending transactions'}), 400
        
        db.execute('DELETE FROM payment_methods WHERE id = ? AND patient_id = ?', 
                  (method_id, session['user_id']))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Payment method removed successfully'})
    
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bill-payments/<int:bill_id>', methods=['GET'])
@login_required
def bill_payments(bill_id):
    """Get payment history for a specific bill"""
    db = get_db()
    
    # Verify the bill belongs to the current user
    if session['user_type'] == 'patient':
        bill = db.execute('SELECT * FROM billing WHERE id = ? AND patient_id = ?', 
                         (bill_id, session['user_id'])).fetchone()
    else:
        bill = db.execute('SELECT * FROM billing WHERE id = ? AND dentist_id = ?', 
                         (bill_id, session['user_id'])).fetchone()
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    # Get payment history
    payments = db.execute('''
        SELECT payment_date, amount, 
               (SELECT COALESCE(SUM(amount), 0) FROM payments p2 
                WHERE p2.billing_id = p.billing_id AND p2.payment_date <= p.payment_date) as cumulative_paid,
               (? - (SELECT COALESCE(SUM(amount), 0) FROM payments p2 
                     WHERE p2.billing_id = p.billing_id AND p2.payment_date <= p.payment_date)) as balance_after
        FROM payments p
        WHERE billing_id = ?
        ORDER BY payment_date ASC
    ''', (bill['patient_portion'], bill_id)).fetchall()
    
    return jsonify([dict(payment) for payment in payments])

@app.route('/api/bill-details/<int:bill_id>', methods=['GET'])
@login_required
def get_bill_details(bill_id):
    """Get detailed information for a specific bill"""
    db = get_db()
    
    # Verify the bill belongs to the current user and get detailed information
    if session['user_type'] == 'patient':
        bill = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, 
                   s.name as service_name, d.first_name as dentist_first_name, 
                   d.last_name as dentist_last_name,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   p.email as patient_email, p.phone as patient_phone,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN dentists d ON b.dentist_id = d.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.patient_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    else:
        bill = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, 
                   s.name as service_name, d.first_name as dentist_first_name, 
                   d.last_name as dentist_last_name,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   p.email as patient_email, p.phone as patient_phone,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN dentists d ON b.dentist_id = d.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.dentist_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    # Convert to dict and add calculated fields
    bill_dict = dict(bill)
    
    # Add dentist full name
    if bill_dict.get('dentist_first_name') and bill_dict.get('dentist_last_name'):
        bill_dict['dentist_name'] = f"{bill_dict['dentist_first_name']} {bill_dict['dentist_last_name']}"
    else:
        bill_dict['dentist_name'] = 'Not assigned'
    
    return jsonify(bill_dict)

@app.route('/api/bill-pdf/<int:bill_id>', methods=['GET'])
@login_required
def download_bill_pdf(bill_id):
    """Generate and download a PDF for a specific bill"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from io import BytesIO
    import os
    
    db = get_db()
    
    # Get bill details (same query as above)
    if session['user_type'] == 'patient':
        bill = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, 
                   s.name as service_name, d.first_name as dentist_first_name, 
                   d.last_name as dentist_last_name, p.first_name as patient_first_name,
                   p.last_name as patient_last_name, p.phone, p.email,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN dentists d ON b.dentist_id = d.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.patient_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    else:
        bill = db.execute('''
            SELECT b.*, t.diagnosis, t.treatment_notes, t.treatment_date, 
                   s.name as service_name, d.first_name as dentist_first_name, 
                   d.last_name as dentist_last_name, p.first_name as patient_first_name,
                   p.last_name as patient_last_name, p.phone, p.email,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN dentists d ON b.dentist_id = d.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.dentist_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the PDF content
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#2563eb')
    )
    
    # Title
    story.append(Paragraph("DENTAL OFFICE BILL", title_style))
    story.append(Spacer(1, 12))
    
    # Bill Information Table
    bill_data = [
        ['Bill #:', str(bill['bill_number'])],
        ['Reference Number:', bill['reference_number'] or 'N/A'],
        ['Bill Date:', bill['created_at'][:10] if bill['created_at'] else 'N/A'],
        ['Due Date:', bill['due_date'][:10] if bill['due_date'] else 'N/A'],
        ['Status:', bill['status'].title() if bill['status'] else 'N/A']
    ]
    
    bill_table = Table(bill_data, colWidths=[2*inch, 3*inch])
    bill_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(bill_table)
    story.append(Spacer(1, 20))
    
    # Patient Information
    story.append(Paragraph("Patient Information", styles['Heading2']))
    patient_data = [
        ['Name:', f"{bill['patient_first_name']} {bill['patient_last_name']}"],
        ['Phone:', bill['phone'] or 'N/A'],
        ['Email:', bill['email'] or 'N/A']
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 3*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Service Information
    story.append(Paragraph("Service Details", styles['Heading2']))
    service_data = [
        ['Service:', bill['service_name'] or 'N/A'],
        ['Treatment Date:', bill['treatment_date'][:10] if bill['treatment_date'] else 'N/A'],
        ['Dentist:', f"{bill['dentist_first_name']} {bill['dentist_last_name']}" if bill['dentist_first_name'] else 'N/A'],
        ['Diagnosis:', bill['diagnosis'] or 'N/A']
    ]
    
    service_table = Table(service_data, colWidths=[2*inch, 3*inch])
    service_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(service_table)
    story.append(Spacer(1, 20))
    
    # Amount Breakdown
    story.append(Paragraph("Amount Breakdown", styles['Heading2']))
    total_amount = float(bill['amount']) if bill['amount'] else 0
    patient_portion = float(bill['patient_portion']) if bill['patient_portion'] else 0
    insurance_portion = total_amount - patient_portion
    amount_paid = float(bill['amount_paid']) if bill['amount_paid'] else 0
    remaining_balance = patient_portion - amount_paid
    
    amount_data = [
        ['Total Amount:', f"${total_amount:.2f}"],
        ['Insurance Portion:', f"${insurance_portion:.2f}"],
        ['Patient Portion:', f"${patient_portion:.2f}"],
        ['Amount Paid:', f"${amount_paid:.2f}"],
        ['Remaining Balance:', f"${remaining_balance:.2f}"]
    ]
    
    amount_table = Table(amount_data, colWidths=[2*inch, 3*inch])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(amount_table)
    
    # Build PDF
    doc.build(story)
    
    # Return PDF
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'bill_{bill_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/patient/profile/update', methods=['POST'])
@login_required
def update_patient_profile():
    if session['user_type'] != 'patient':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    db = get_db()
    user_id = session['user_id']
    # Get form data
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    date_of_birth = request.form.get('date_of_birth')
    address = request.form.get('address')
    try:
        db.execute('''
            UPDATE patients SET first_name=?, last_name=?, email=?, phone=?, date_of_birth=?, address=?
            WHERE id=?
        ''', (first_name, last_name, email, phone, date_of_birth, address, user_id))
        db.commit()
        session['name'] = f"{first_name} {last_name}"
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/call_popup')
def call_popup():
    # Extract the space name from SIGNALWIRE_SPACE URL for template
    signalwire_space = SIGNALWIRE_SPACE
    if signalwire_space and signalwire_space.startswith('https://'):
        # Extract just the space name from URL like https://spacename.signalwire.com
        signalwire_space = signalwire_space.replace('https://', '').split('.')[0]
    elif signalwire_space and signalwire_space.startswith('http://'):
        # Handle http URLs
        signalwire_space = signalwire_space.replace('http://', '').split('.')[0]
    
    return render_template('call_popup.html',
                         signalwire_space=signalwire_space or 'your-space',
                         c2c_api_key=C2C_API_KEY or 'your-c2c-api-key',
                         c2c_address=C2C_ADDRESS or 'your-c2c-address')

# --- MFA State Management (demo only, not for production) ---
VERIFIED_PATIENTS = {}
VERIFIED_PATIENT_DATA = {}  # Maintain backward compatibility
ACTIVE_MFA_SESSIONS = {}
CHALLENGE_TOKENS = {}  # New: Store challenge token -> patient data mappings
LAST_MFA_ID = None

def clear_mfa_session(mfa_id):
    """Clear MFA session data"""
    global VERIFIED_PATIENTS, ACTIVE_MFA_SESSIONS
    if mfa_id in VERIFIED_PATIENTS:
        del VERIFIED_PATIENTS[mfa_id]
    if mfa_id in ACTIVE_MFA_SESSIONS:
        del ACTIVE_MFA_SESSIONS[mfa_id]
    print(f"[SWAIG][CONSOLE] Cleared MFA session: {mfa_id}")
    logging.info(f"[SWAIG] Cleared MFA session: {mfa_id}")

def get_verified_patient(mfa_id):
    """Get verified patient data for MFA session"""
    return VERIFIED_PATIENTS.get(mfa_id) or VERIFIED_PATIENT_DATA.get(mfa_id)

def is_patient_verified(mfa_id):
    """Check if patient is verified for this MFA session"""
    is_verified = mfa_id and (mfa_id in VERIFIED_PATIENTS or mfa_id in VERIFIED_PATIENT_DATA)
    print(f"[SWAIG][CONSOLE] is_patient_verified({mfa_id}): {is_verified}")
    print(f"[SWAIG][CONSOLE] VERIFIED_PATIENTS keys: {list(VERIFIED_PATIENTS.keys())}")
    print(f"[SWAIG][CONSOLE] VERIFIED_PATIENT_DATA keys: {list(VERIFIED_PATIENT_DATA.keys())}")
    logging.info(f"[SWAIG] is_patient_verified({mfa_id}): {is_verified}")
    return is_verified

def store_verified_patient(mfa_id, patient_data):
    """Store verified patient data for MFA session"""
    global VERIFIED_PATIENTS, VERIFIED_PATIENT_DATA, ACTIVE_MFA_SESSIONS
    VERIFIED_PATIENTS[mfa_id] = patient_data
    VERIFIED_PATIENT_DATA[mfa_id] = patient_data  # Maintain backward compatibility
    ACTIVE_MFA_SESSIONS[mfa_id] = {
        'patient_id': patient_data.get('patient_id'),
        'verified_at': datetime.now().isoformat(),
        'phone': patient_data.get('phone')
    }
    print(f"[SWAIG][CONSOLE] Stored verified patient data for session {mfa_id}: Patient {patient_data.get('patient_id', 'Unknown')}")
    logging.info(f"[SWAIG] Stored verified patient data for session {mfa_id}: Patient {patient_data.get('patient_id', 'Unknown')}")

def validate_phone(phone):
    """Validate phone number is in E.164 format: +[country code][number]"""
    import re
    if not phone:
        return False
    # E.164 format: + followed by 1-3 digit country code, then 4-14 digits
    # Total length should be 8-18 characters (+ plus 7-17 digits)
    pattern = r'^\+[1-9]\d{6,14}$'
    return bool(re.match(pattern, str(phone).strip()))

def format_to_e164(phone, default_country_code='1'):
    """Format phone number to E.164 format"""
    if not phone:
        return None
    
    # Clean the phone number - remove all non-digit characters except +
    cleaned = ''.join(char for char in str(phone) if char.isdigit() or char == '+')
    
    # If already starts with +, validate and return if valid
    if cleaned.startswith('+'):
        if validate_phone(cleaned):
            return cleaned
        else:
            return None
    
    # If it's a 10-digit number (US format), add +1
    if len(cleaned) == 10 and cleaned.isdigit():
        formatted = f'+{default_country_code}{cleaned}'
        return formatted if validate_phone(formatted) else None
    
    # If it's an 11-digit number starting with 1 (US format with country code)
    if len(cleaned) == 11 and cleaned.startswith('1'):
        formatted = f'+{cleaned}'
        return formatted if validate_phone(formatted) else None
    
    # If it's just digits and reasonable length, try adding default country code
    if cleaned.isdigit() and 7 <= len(cleaned) <= 14:
        formatted = f'+{default_country_code}{cleaned}'
        return formatted if validate_phone(formatted) else None
    
    return None

def is_valid_uuid(val):
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

def store_challenge_token(challenge_token, patient_data):
    """Store challenge token with associated patient data"""
    global CHALLENGE_TOKENS
    CHALLENGE_TOKENS[challenge_token] = patient_data
    print(f"[SWAIG][CONSOLE] Stored challenge token {challenge_token[:20]}... for patient {patient_data.get('patient_id', 'Unknown')}")
    logging.info(f"[SWAIG] Stored challenge token {challenge_token[:20]}... for patient {patient_data.get('patient_id', 'Unknown')}")

def get_patient_by_challenge_token(challenge_token):
    """Get patient data by challenge token"""
    return CHALLENGE_TOKENS.get(challenge_token)

def is_challenge_token_valid(challenge_token):
    """Check if challenge token is valid and has associated patient data"""
    is_valid = challenge_token and challenge_token in CHALLENGE_TOKENS
    print(f"[SWAIG][CONSOLE] is_challenge_token_valid({challenge_token}): {is_valid}")
    print(f"[SWAIG][CONSOLE] CHALLENGE_TOKENS keys: {list(CHALLENGE_TOKENS.keys())}")
    logging.info(f"[SWAIG] is_challenge_token_valid({challenge_token}): {is_valid}")
    return is_valid

@swaig.endpoint(
    "Check Balance",
    challenge_token=SWAIGArgument(
        type="string", 
        description="Challenge token",
        required=True
    )
)
def swaig_check_balance(challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_check_balance called with challenge_token={challenge_token}")
    logging.info(f"[SWAIG] swaig_check_balance called with challenge_token={challenge_token}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        print(f"[SWAIG][CONSOLE] Patient not found: {patient_id}")
        logging.warning(f"[SWAIG] Patient not found: {patient_id}")
        return "Patient account not found", {}
    
    balance = db.execute('SELECT COALESCE(SUM(patient_portion), 0) as total FROM billing WHERE patient_id = ? AND status != "paid"', (patient['id'],)).fetchone()
    print(f"[SWAIG][CONSOLE] Returning balance for patient {patient_id}: ${balance['total']}")
    logging.info(f"[SWAIG] Returning balance for patient {patient_id}: ${balance['total']}")
    return f"Your current outstanding balance is ${balance['total']:.2f}", {'balance': balance['total'], 'patient_id': patient_id}

@swaig.endpoint(
    "Get Bills",
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    ),
    service_name=SWAIGArgument(
        type="string",
        description="Filter by service name (e.g., 'cleaning', 'whitening', 'braces')",
        required=False
    ),
    status=SWAIGArgument(
        type="string", 
        description="Filter by bill status (paid, pending, overdue, partial)",
        required=False
    ),
    amount_min=SWAIGArgument(
        type="number",
        description="Minimum amount filter",
        required=False
    ),
    amount_max=SWAIGArgument(
        type="number", 
        description="Maximum amount filter",
        required=False
    ),
    due_date=SWAIGArgument(
        type="string",
        description="Filter by specific due date (YYYY-MM-DD format)",
        required=False
    ),
    reference_number=SWAIGArgument(
        type="string",
        description="Filter by bill reference number (full or partial)",
        required=False
    )
)
def swaig_get_bills(challenge_token=None, service_name=None, status=None, amount_min=None, amount_max=None, due_date=None, reference_number=None, meta_data_token=None, **kwargs):
    filter_desc = []
    if service_name: filter_desc.append(f"service '{service_name}'")
    if status: filter_desc.append(f"status '{status}'")
    if amount_min or amount_max: filter_desc.append(f"amount ${amount_min or 0}-${amount_max or 999999}")
    if due_date: filter_desc.append(f"due date '{due_date}'")
    if reference_number: filter_desc.append(f"reference '{reference_number}'")
    
    filter_text = f" with filters: {', '.join(filter_desc)}" if filter_desc else ""
    print(f"[SWAIG][CONSOLE] swaig_get_bills called{filter_text}")
    logging.info(f"[SWAIG] swaig_get_bills called{filter_text}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    print(f"[SWAIG][CONSOLE] Retrieved patient_data: {patient_data}")
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    # Use the patient data directly from challenge token instead of database lookup
    patient_internal_id = patient_data.get('id')
    print(f"[SWAIG][CONSOLE] Patient internal ID: {patient_internal_id}")
    if not patient_internal_id:
        print(f"[SWAIG][CONSOLE] No internal patient ID in challenge token for patient {patient_id}")
        logging.warning(f"[SWAIG] No internal patient ID in challenge token for patient {patient_id}")
        return "Patient session data incomplete. Please verify your identity again.", {}
    
    db = get_db()
    
    # Build comprehensive SQL query to get all bill details including payment history
    base_query = '''
        SELECT b.*, 
               s.name as service_name, s.description as service_description, s.price as service_price,
               CASE 
                   WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                   ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
               END as dentist_name,
               th.diagnosis, th.treatment_notes, th.treatment_date,
               (b.amount - COALESCE(b.insurance_coverage, 0)) as calculated_patient_portion
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
        LEFT JOIN dentists d ON b.dentist_id = d.id
        LEFT JOIN treatment_history th ON b.reference_number = th.reference_number
        WHERE b.patient_id = ?
    '''
    
    conditions = []
    params = [patient_internal_id]
    
    # Service name filter (case insensitive, partial match)
    if service_name:
        conditions.append("UPPER(s.name) LIKE ? OR UPPER(s.description) LIKE ?")
        service_search = f"%{service_name.upper()}%"
        params.extend([service_search, service_search])
    
    # Status filter
    if status:
        status_lower = status.lower()
        if status_lower in ['paid', 'pending', 'overdue', 'partial']:
            if status_lower == 'paid':
                conditions.append("b.status = 'paid'")
            elif status_lower == 'overdue':
                conditions.append("b.due_date < date('now') AND b.status != 'paid'")
            elif status_lower == 'pending':
                conditions.append("(b.status = 'pending' OR (b.status != 'paid' AND b.status != 'partial' AND b.due_date >= date('now')))")
            elif status_lower == 'partial':
                conditions.append("b.status = 'partial'")
    
    # Amount range filters (check both total amount and patient portion)
    if amount_min is not None:
        conditions.append("(b.amount >= ? OR b.patient_portion >= ?)")
        params.extend([amount_min, amount_min])
    
    if amount_max is not None:
        conditions.append("(b.amount <= ? OR b.patient_portion <= ?)")
        params.extend([amount_max, amount_max])
    
    # Due date filter
    if due_date:
        conditions.append("b.due_date = ?")
        params.append(due_date)
    
    # Reference number filter (flexible matching)
    if reference_number:
        ref_search = reference_number.strip().upper()
        conditions.append("UPPER(b.reference_number) LIKE ?")
        params.append(f'%{ref_search}%')
    
    # Add conditions to query
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    base_query += " ORDER BY b.due_date DESC"
    
    # DEBUG: Log the exact query and parameters being used
    print(f"[SWAIG][DEBUG] Query: {base_query}")
    print(f"[SWAIG][DEBUG] Params: {params}")
    logging.info(f"[SWAIG][DEBUG] Query: {base_query}")
    logging.info(f"[SWAIG][DEBUG] Params: {params}")
    
    bills = db.execute(base_query, params).fetchall()
    
    # DEBUG: Log what bills were actually returned
    print(f"[SWAIG][DEBUG] Raw bills returned: {len(bills)}")
    for bill in bills:
        print(f"[SWAIG][DEBUG] Bill ID: {bill['id']}, Patient ID: {bill['patient_id']}, Bill #: {bill['bill_number']}")
    logging.info(f"[SWAIG][DEBUG] Raw bills returned: {len(bills)}")
    
    # Get payment history for each bill
    enhanced_bills = []
    for bill in bills:
        bill_dict = dict(bill)
        
        # Get payment history for this bill
        payments = db.execute('''
            SELECT payment_date, amount, payment_method_type, transaction_id
            FROM payments
            WHERE billing_id = ?
            ORDER BY payment_date DESC
        ''', (bill['id'],)).fetchall()
        
        # Calculate payment totals and remaining balance
        total_paid = sum(float(p['amount']) for p in payments) if payments else 0
        patient_portion = float(bill['patient_portion']) if bill['patient_portion'] else float(bill['calculated_patient_portion'])
        remaining_balance = max(0, patient_portion - total_paid)
        
        # Add enhanced information to bill
        bill_dict.update({
            'payment_history': [dict(p) for p in payments],
            'total_paid': total_paid,
            'remaining_balance': remaining_balance,
            'payment_count': len(payments),
            'is_fully_paid': remaining_balance == 0,
            'patient_portion_calculated': patient_portion
        })
        
        enhanced_bills.append(bill_dict)
    
    print(f"[SWAIG][CONSOLE] Returning {len(enhanced_bills)} bills with full details for patient {patient_id}{filter_text}")
    logging.info(f"[SWAIG] Returning {len(enhanced_bills)} bills with full details for patient {patient_id}{filter_text}")
    
    if enhanced_bills:
        bills_summary = f"Found {len(enhanced_bills)} bill(s)"
        if filter_desc:
            bills_summary += f" matching {', '.join(filter_desc)}"
        bills_summary += ". "
        
        pending_bills = [b for b in enhanced_bills if b['status'] != 'paid']
        if pending_bills:
            total_due = sum(b['remaining_balance'] for b in pending_bills)
            bills_summary += f"Total amount due: ${total_due:.2f}.\n"
            
            bills_summary += f"\nDetailed Bill Information:\n"
            
            # Add comprehensive bill information
            for i, bill in enumerate(enhanced_bills, 1):
                status_text = f" ({bill['status'].title()})" if bill['status'] != 'pending' else ""
                patient_portion = bill['patient_portion_calculated']
                remaining = bill['remaining_balance']
                
                bills_summary += f"\n{i}. Bill #{bill['bill_number']} - {bill['service_name']}\n"
                bills_summary += f"   Reference: {bill['reference_number']}\n"
                bills_summary += f"   Total Amount: ${float(bill['amount']):.2f}\n"
                bills_summary += f"   Insurance Coverage: ${float(bill['insurance_coverage'] or 0):.2f}\n"
                bills_summary += f"   Patient Portion: ${patient_portion:.2f}\n"
                bills_summary += f"   Amount Paid: ${bill['total_paid']:.2f}\n"
                bills_summary += f"   Remaining Balance: ${remaining:.2f}{status_text}\n"
                
                if bill['dentist_name']:
                    bills_summary += f"   Provider: {bill['dentist_name']}\n"
                
                if bill['service_description']:
                    bills_summary += f"   Service Details: {bill['service_description']}\n"
                
                if bill['diagnosis']:
                    bills_summary += f"   Diagnosis: {bill['diagnosis']}\n"
                
                if bill['due_date']:
                    bills_summary += f"   Due Date: {bill['due_date']}\n"
                
                if bill['payment_history']:
                    bills_summary += f"   Payment History: {bill['payment_count']} payment(s)\n"
                    for payment in bill['payment_history'][:2]:  # Show last 2 payments
                        bills_summary += f"     - ${float(payment['amount']):.2f} on {payment['payment_date']} via {payment['payment_method_type']}\n"
                    if len(bill['payment_history']) > 2:
                        bills_summary += f"     - ... and {len(bill['payment_history']) - 2} more payment(s)\n"
                else:
                    bills_summary += f"   Payment History: No payments yet\n"
                
                if bill['treatment_notes']:
                    bills_summary += f"   Treatment Notes: {bill['treatment_notes']}\n"
        else:
            bills_summary += "All matching bills are paid.\n\nDetailed Bill Information:\n"
            for i, bill in enumerate(enhanced_bills, 1):
                patient_portion = bill['patient_portion_calculated']
                bills_summary += f"\n{i}. Bill #{bill['bill_number']} - {bill['service_name']}: ${patient_portion:.2f} (Paid)\n"
                bills_summary += f"   Reference: {bill['reference_number']}\n"
                bills_summary += f"   Total Paid: ${bill['total_paid']:.2f}\n"
                if bill['payment_history']:
                    bills_summary += f"   Last Payment: ${float(bill['payment_history'][0]['amount']):.2f} on {bill['payment_history'][0]['payment_date']}\n"
        
        return bills_summary, {
            'bills': enhanced_bills, 
            'patient_id': patient_id, 
            'filters_applied': filter_desc,
            'total_bills': len(enhanced_bills),
            'total_amount_due': sum(b['remaining_balance'] for b in pending_bills) if pending_bills else 0,
            'bills_with_payments': len([b for b in enhanced_bills if b['payment_count'] > 0])
        }
    else:
        no_results_msg = "No bills found"
        if filter_desc:
            no_results_msg += f" matching {', '.join(filter_desc)}"
        no_results_msg += " on your account."
        
        # If filters were used but no results, suggest trying without filters
        if filter_desc:
            no_results_msg += " Try removing some filters to see more bills."
            
        return no_results_msg, {'bills': [], 'patient_id': patient_id, 'filters_applied': filter_desc}

@swaig.endpoint(
    "Schedule Appointment",
    dentist_id=SWAIGArgument(
        type="string",
        description="Dentist ID",
        required=True
    ),
    service_id=SWAIGArgument(
        type="string",
        description="Service ID",
        required=True
    ),
    date=SWAIGArgument(
        type="string",
        description="Date (YYYY-MM-DD)",
        required=True
    ),
    time_slot=SWAIGArgument(
        type="string",
        description="Time slot",
        enum=["morning", "afternoon", "evening", "all_day"],
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_schedule_appointment(dentist_id=None, service_id=None, date=None, time_slot=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_schedule_appointment called with dentist_id={dentist_id}, service_id={service_id}, date={date}, time_slot={time_slot}")
    logging.info(f"[SWAIG] swaig_schedule_appointment called with dentist_id={dentist_id}, service_id={service_id}, date={date}, time_slot={time_slot}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        print(f"[SWAIG][CONSOLE] Patient not found: {patient_id}")
        logging.warning(f"[SWAIG] Patient not found: {patient_id}")
        return "Patient account not found", {}
    
    # Smart service_id resolution - handle both numeric IDs and service names
    resolved_service_id = None
    if service_id.isdigit():
        # It's a numeric ID, validate it exists
        resolved_service_id = int(service_id)
        service = db.execute('SELECT * FROM dental_services WHERE id = ?', (resolved_service_id,)).fetchone()
        if not service:
            return f"Service ID {service_id} not found", {}
    else:
        # It's a service name or type, try to resolve it
        service = None
        # First try exact name match (case insensitive)
        service = db.execute('SELECT * FROM dental_services WHERE LOWER(name) = LOWER(?)', (service_id,)).fetchone()
        if not service:
            # Try type match (for common abbreviations like "cleaning", "whitening")
            service = db.execute('SELECT * FROM dental_services WHERE LOWER(type) = LOWER(?)', (service_id,)).fetchone()
        if not service:
            # Try partial name match
            service = db.execute('SELECT * FROM dental_services WHERE LOWER(name) LIKE LOWER(?)', (f'%{service_id}%',)).fetchone()
        
        if service:
            resolved_service_id = service['id']
            print(f"[SWAIG][CONSOLE] Resolved service '{service_id}' to '{service['name']}' (ID: {resolved_service_id})")
            logging.info(f"[SWAIG] Resolved service '{service_id}' to '{service['name']}' (ID: {resolved_service_id})")
        else:
            return f"Service '{service_id}' not found. Available services include: Regular Cleaning, Teeth Whitening, Braces Consultation, Emergency Visit", {}
    
    # Smart dentist_id resolution and auto-assignment
    resolved_dentist_id = None
    if dentist_id.isdigit():
        # It's a numeric ID, validate it exists
        resolved_dentist_id = int(dentist_id)
        dentist = db.execute('SELECT * FROM dentists WHERE id = ?', (resolved_dentist_id,)).fetchone()
        if not dentist:
            return f"Dentist ID {dentist_id} not found", {}
    else:
        # Try to resolve dentist by name
        dentist = db.execute('''
            SELECT * FROM dentists 
            WHERE LOWER(first_name || ' ' || last_name) LIKE LOWER(?)
        ''', (f'%{dentist_id}%',)).fetchone()
        
        if dentist:
            resolved_dentist_id = dentist['id']
            print(f"[SWAIG][CONSOLE] Resolved dentist '{dentist_id}' to Dr. {dentist['first_name']} {dentist['last_name']} (ID: {resolved_dentist_id})")
            logging.info(f"[SWAIG] Resolved dentist '{dentist_id}' to Dr. {dentist['first_name']} {dentist['last_name']} (ID: {resolved_dentist_id})")
        else:
            # Auto-assign dentist based on service type (smart recommendations)
            if resolved_service_id:
                service = db.execute('SELECT * FROM dental_services WHERE id = ?', (resolved_service_id,)).fetchone()
                if service['type'] == 'whitening':
                    resolved_dentist_id = 2  # Dr. Sarah Johnson
                elif service['type'] == 'orthodontics':
                    resolved_dentist_id = 3  # Dr. Michael Chen  
                else:
                    resolved_dentist_id = 1  # Dr. John Smith (default)
                
                auto_dentist = db.execute('SELECT * FROM dentists WHERE id = ?', (resolved_dentist_id,)).fetchone()
                print(f"[SWAIG][CONSOLE] Auto-assigned Dr. {auto_dentist['first_name']} {auto_dentist['last_name']} for {service['name']}")
                logging.info(f"[SWAIG] Auto-assigned Dr. {auto_dentist['first_name']} {auto_dentist['last_name']} for {service['name']}")
            else:
                return f"Dentist '{dentist_id}' not found. Available dentists: Dr. John Smith, Dr. Sarah Johnson, Dr. Michael Chen", {}
    
    # Use resolved IDs
    dentist_id = resolved_dentist_id
    service_id = resolved_service_id
    
    # Convert time slot to actual times
    if time_slot == 'morning':
        start_time = f"{date}T08:00:00"
        end_time = f"{date}T11:00:00"
    elif time_slot == 'afternoon':
        start_time = f"{date}T14:00:00"
        end_time = f"{date}T16:00:00"
    elif time_slot == 'evening':
        start_time = f"{date}T18:00:00"
        end_time = f"{date}T20:00:00"
    elif time_slot == 'all_day':
        start_time = f"{date}T08:00:00"
        end_time = f"{date}T20:00:00"
    else:
        print(f"[SWAIG][CONSOLE] Invalid time slot: {time_slot}")
        logging.warning(f"[SWAIG] Invalid time slot: {time_slot}")
        return "Invalid time slot", {}
    
    try:
        db.execute('''
            INSERT INTO appointments (patient_id, dentist_id, service_id, type, status, start_time, end_time, notes, sms_reminder)
            VALUES (?, ?, ?, ?, 'scheduled', ?, ?, '', 1)
        ''', (patient['id'], dentist_id, service_id, 'checkup', start_time, end_time))
        db.commit()
        
        # Send SMS confirmation
        try:
            # Get appointment details for SMS
            dentist = db.execute('SELECT first_name, last_name FROM dentists WHERE id = ?', (dentist_id,)).fetchone()
            service = db.execute('SELECT name FROM dental_services WHERE id = ?', (service_id,)).fetchone()
            
            if dentist and service and patient.get('phone'):
                mfa = SignalWireMFA(
                    SIGNALWIRE_PROJECT_ID,
                    SIGNALWIRE_TOKEN,
                    SIGNALWIRE_SPACE,
                    os.getenv('FROM_NUMBER')
                )
                
                # Format the appointment time for SMS
                appt_date = datetime.fromisoformat(start_time).strftime('%A, %B %d, %Y')
                appt_time = datetime.fromisoformat(start_time).strftime('%I:%M %p')
                
                sms_body = f"Your appointment for {service['name']} with Dr. {dentist['first_name']} {dentist['last_name']} is scheduled for {appt_date} at {appt_time}."
                
                mfa.client.messages.create(
                    from_=os.getenv('FROM_NUMBER'),
                    to=patient['phone'],
                    body=sms_body
                )
                print(f"[SWAIG][CONSOLE] SMS confirmation sent for scheduled appointment to {patient['phone']}")
                logging.info(f"[SWAIG] SMS confirmation sent for scheduled appointment to {patient['phone']}")
        except Exception as sms_error:
            print(f"[SWAIG][CONSOLE] Failed to send SMS confirmation: {sms_error}")
            logging.error(f"[SWAIG] Failed to send SMS confirmation: {sms_error}")
            # Don't fail the appointment creation if SMS fails
        
        print(f"[SWAIG][CONSOLE] Appointment scheduled for patient {patient_id} with dentist {dentist_id} on {date} ({time_slot})")
        logging.info(f"[SWAIG] Appointment scheduled for patient {patient_id} with dentist {dentist_id} on {date} ({time_slot})")
        return f"Appointment scheduled successfully for {date} in the {time_slot} time slot", {'patient_id': patient_id, 'date': date, 'time_slot': time_slot}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Failed to schedule appointment: {e}")
        logging.error(f"[SWAIG] Failed to schedule appointment: {e}")
        db.rollback()
        return f"Failed to schedule appointment: {str(e)}", {}

@swaig.endpoint(
    "Reschedule Appointment",
    appointment_id=SWAIGArgument(
        type="string",
        description="Appointment ID",
        required=True
    ),
    date=SWAIGArgument(
        type="string",
        description="Date (YYYY-MM-DD)",
        required=True
    ),
    time_slot=SWAIGArgument(
        type="string",
        description="Time slot",
        enum=["morning", "afternoon", "evening", "all_day"],
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_reschedule_appointment(appointment_id=None, date=None, time_slot=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_reschedule_appointment called with appointment_id={appointment_id}, date={date}, time_slot={time_slot}")
    logging.info(f"[SWAIG] swaig_reschedule_appointment called with appointment_id={appointment_id}, date={date}, time_slot={time_slot}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    
    # Get the appointment and verify it belongs to the authenticated patient
    appt = db.execute('''
        SELECT a.*, p.patient_id as patient_external_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()
    
    if not appt:
        print(f"[SWAIG][CONSOLE] Appointment not found: {appointment_id}")
        logging.warning(f"[SWAIG] Appointment not found: {appointment_id}")
        return "Appointment not found", {}
    
    # Verify the appointment belongs to the authenticated patient
    if appt['patient_external_id'] != patient_id:
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} does not belong to patient {patient_id}")
        logging.warning(f"[SWAIG] Appointment {appointment_id} does not belong to patient {patient_id}")
        return "You can only reschedule your own appointments", {}
    
    # Check if the appointment is already cancelled
    if appt['status'] == 'cancelled':
        print(f"[SWAIG][CONSOLE] Cannot reschedule cancelled appointment: {appointment_id}")
        logging.warning(f"[SWAIG] Cannot reschedule cancelled appointment: {appointment_id}")
        return "Cannot reschedule a cancelled appointment. Please schedule a new appointment instead.", {}
    
    # Convert time slot to actual times
    if time_slot == 'morning':
        start_time = f"{date}T08:00:00"
        end_time = f"{date}T11:00:00"
    elif time_slot == 'afternoon':
        start_time = f"{date}T14:00:00"
        end_time = f"{date}T16:00:00"
    elif time_slot == 'evening':
        start_time = f"{date}T18:00:00"
        end_time = f"{date}T20:00:00"
    elif time_slot == 'all_day':
        start_time = f"{date}T08:00:00"
        end_time = f"{date}T20:00:00"
    else:
        print(f"[SWAIG][CONSOLE] Invalid time slot: {time_slot}")
        logging.warning(f"[SWAIG] Invalid time slot: {time_slot}")
        return "Invalid time slot", {}
    
    try:
        db.execute('UPDATE appointments SET start_time = ?, end_time = ? WHERE id = ?', (start_time, end_time, appointment_id))
        db.commit()
        
        # Send SMS confirmation for rescheduled appointment
        try:
            # Get appointment details for SMS
            updated_appt = db.execute('''
                SELECT a.*, d.first_name, d.last_name, s.name as service_name, p.phone
                FROM appointments a
                JOIN dentists d ON a.dentist_id = d.id
                JOIN dental_services s ON a.service_id = s.id
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()
            
            if updated_appt and updated_appt['phone']:
                mfa = SignalWireMFA(
                    SIGNALWIRE_PROJECT_ID,
                    SIGNALWIRE_TOKEN,
                    SIGNALWIRE_SPACE,
                    os.getenv('FROM_NUMBER')
                )
                
                # Format the appointment time for SMS
                appt_date = datetime.fromisoformat(start_time).strftime('%A, %B %d, %Y')
                appt_time = datetime.fromisoformat(start_time).strftime('%I:%M %p')
                
                sms_body = f"Your appointment for {updated_appt['service_name']} with Dr. {updated_appt['first_name']} {updated_appt['last_name']} has been rescheduled to {appt_date} at {appt_time}."
                
                mfa.client.messages.create(
                    from_=os.getenv('FROM_NUMBER'),
                    to=updated_appt['phone'],
                    body=sms_body
                )
                print(f"[SWAIG][CONSOLE] SMS confirmation sent for rescheduled appointment to {updated_appt['phone']}")
                logging.info(f"[SWAIG] SMS confirmation sent for rescheduled appointment to {updated_appt['phone']}")
        except Exception as sms_error:
            print(f"[SWAIG][CONSOLE] Failed to send SMS confirmation: {sms_error}")
            logging.error(f"[SWAIG] Failed to send SMS confirmation: {sms_error}")
            # Don't fail the reschedule if SMS fails
        
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} rescheduled to {date} ({time_slot}) for patient {patient_id}")
        logging.info(f"[SWAIG] Appointment {appointment_id} rescheduled to {date} ({time_slot}) for patient {patient_id}")
        return f"Appointment rescheduled successfully to {date} in the {time_slot} time slot", {'patient_id': patient_id, 'appointment_id': appointment_id, 'date': date, 'time_slot': time_slot}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Failed to reschedule appointment: {e}")
        logging.error(f"[SWAIG] Failed to reschedule appointment: {e}")
        db.rollback()
        return f"Failed to reschedule appointment: {str(e)}", {}

@swaig.endpoint(
    "Cancel Appointment",
    appointment_id=SWAIGArgument(
        type="string",
        description="Appointment ID",
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_cancel_appointment(appointment_id=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_cancel_appointment called with appointment_id={appointment_id}")
    logging.info(f"[SWAIG] swaig_cancel_appointment called with appointment_id={appointment_id}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    
    # Get the appointment and verify it belongs to the authenticated patient
    appt = db.execute('''
        SELECT a.*, p.patient_id as patient_external_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()
    
    if not appt:
        print(f"[SWAIG][CONSOLE] Appointment not found: {appointment_id}")
        logging.warning(f"[SWAIG] Appointment not found: {appointment_id}")
        return "Appointment not found", {}
    
    # Verify the appointment belongs to the authenticated patient
    if appt['patient_external_id'] != patient_id:
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} does not belong to patient {patient_id}")
        logging.warning(f"[SWAIG] Appointment {appointment_id} does not belong to patient {patient_id}")
        return "You can only cancel your own appointments", {}
    
    # Check if the appointment is already cancelled
    if appt['status'] == 'cancelled':
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} is already cancelled")
        logging.info(f"[SWAIG] Appointment {appointment_id} is already cancelled")
        return "This appointment has already been cancelled.", {}
    
    try:
        db.execute('UPDATE appointments SET status = ? WHERE id = ?', ('cancelled', appointment_id))
        db.commit()
        
        # Send SMS confirmation for cancelled appointment
        try:
            # Get appointment details for SMS
            cancelled_appt = db.execute('''
                SELECT a.*, d.first_name, d.last_name, s.name as service_name, p.phone
                FROM appointments a
                JOIN dentists d ON a.dentist_id = d.id
                JOIN dental_services s ON a.service_id = s.id
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()
            
            if cancelled_appt and cancelled_appt['phone']:
                mfa = SignalWireMFA(
                    SIGNALWIRE_PROJECT_ID,
                    SIGNALWIRE_TOKEN,
                    SIGNALWIRE_SPACE,
                    os.getenv('FROM_NUMBER')
                )
                
                # Format the appointment time for SMS
                appt_date = datetime.fromisoformat(cancelled_appt['start_time']).strftime('%A, %B %d, %Y')
                appt_time = datetime.fromisoformat(cancelled_appt['start_time']).strftime('%I:%M %p')
                
                sms_body = f"Your appointment for {cancelled_appt['service_name']} with Dr. {cancelled_appt['first_name']} {cancelled_appt['last_name']} scheduled for {appt_date} at {appt_time} has been cancelled."
                
                mfa.client.messages.create(
                    from_=os.getenv('FROM_NUMBER'),
                    to=cancelled_appt['phone'],
                    body=sms_body
                )
                print(f"[SWAIG][CONSOLE] SMS confirmation sent for cancelled appointment to {cancelled_appt['phone']}")
                logging.info(f"[SWAIG] SMS confirmation sent for cancelled appointment to {cancelled_appt['phone']}")
        except Exception as sms_error:
            print(f"[SWAIG][CONSOLE] Failed to send SMS confirmation: {sms_error}")
            logging.error(f"[SWAIG] Failed to send SMS confirmation: {sms_error}")
            # Don't fail the cancellation if SMS fails
        
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} cancelled for patient {patient_id}")
        logging.info(f"[SWAIG] Appointment {appointment_id} cancelled for patient {patient_id}")
        return "Appointment cancelled successfully", {'patient_id': patient_id, 'appointment_id': appointment_id}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Failed to cancel appointment: {e}")
        logging.error(f"[SWAIG] Failed to cancel appointment: {e}")
        db.rollback()
        return f"Failed to cancel appointment: {str(e)}", {}

@swaig.endpoint(
    "Make Payment (Full or Partial)",
    bill_id=SWAIGArgument(
        type="string",
        description="Bill ID or Reference Number",
        required=True
    ),
    amount=SWAIGArgument(
        type="number",
        description="Payment amount (minimum $5.00). You can make partial payments - you don't need to pay the full balance at once.",
        required=True
    ),
    payment_method_id=SWAIGArgument(
        type="string",
        description="Payment Method ID",
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_make_payment(bill_id=None, amount=None, payment_method_id=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_make_payment called with bill_id={bill_id}, amount={amount}, payment_method_id={payment_method_id}")
    logging.info(f"[SWAIG] swaig_make_payment called with bill_id={bill_id}, amount={amount}, payment_method_id={payment_method_id}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Validate minimum payment amount
    try:
        payment_amount = float(amount)
        if payment_amount < 5.00:
            print(f"[SWAIG][CONSOLE] Payment amount ${payment_amount:.2f} is below minimum of $5.00")
            logging.warning(f"[SWAIG] Payment amount ${payment_amount:.2f} is below minimum of $5.00")
            return "The minimum payment amount is $5.00. Please enter a payment amount of at least $5.00.", {}
    except (ValueError, TypeError):
        print(f"[SWAIG][CONSOLE] Invalid payment amount: {amount}")
        logging.warning(f"[SWAIG] Invalid payment amount: {amount}")
        return "Invalid payment amount. Please enter a valid dollar amount.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        print(f"[SWAIG][CONSOLE] Patient not found: {patient_id}")
        logging.warning(f"[SWAIG] Patient not found: {patient_id}")
        return "Patient account not found", {}
    
    try:
        # Handle both bill_id and reference number - determine which one was provided
        actual_bill_id = None
        is_reference_number = False
        
        # First try to find bill by ID (numeric)
        if bill_id.isdigit():
            bill_lookup = db.execute('SELECT id, patient_portion, status, reference_number FROM billing WHERE id = ? AND patient_id = ?', (bill_id, patient['patient_id'])).fetchone()
            if bill_lookup:
                actual_bill_id = bill_id
                print(f"[SWAIG][CONSOLE] Found bill by ID: {actual_bill_id}")
            else:
                # Try by bill_number if not found by ID
                bill_lookup = db.execute('SELECT id, patient_portion, status, reference_number FROM billing WHERE bill_number = ? AND patient_id = ?', (bill_id, patient['patient_id'])).fetchone()
                if bill_lookup:
                    actual_bill_id = str(bill_lookup['id'])
                    print(f"[SWAIG][CONSOLE] Found bill by bill_number: {bill_id} -> Bill ID {actual_bill_id}")
                else:
                    print(f"[SWAIG][CONSOLE] Bill ID/Number {bill_id} not found, trying as reference number")
        
        # If not found by ID or not numeric, try as reference number
        if not actual_bill_id:
            # Try exact reference number match first
            bill_lookup = db.execute('SELECT id, patient_portion, status, reference_number FROM billing WHERE reference_number = ? AND patient_id = ?', (bill_id, patient['patient_id'])).fetchone()
            if bill_lookup:
                actual_bill_id = str(bill_lookup['id'])
                is_reference_number = True
                print(f"[SWAIG][CONSOLE] Found bill by exact reference number: {bill_id} -> Bill ID {actual_bill_id}")
            else:
                # Try flexible reference number matching (case insensitive, partial)
                ref_search = bill_id.strip().upper()
                bill_lookup = db.execute('''
                    SELECT id, patient_portion, status, reference_number 
                    FROM billing 
                    WHERE patient_id = ? AND (
                        UPPER(reference_number) = ? OR 
                        UPPER(SUBSTR(reference_number, -8)) = ? OR
                        UPPER(reference_number) LIKE ? OR
                        UPPER(REPLACE(reference_number, '_', '')) LIKE ?
                    )
                ''', (patient['patient_id'], ref_search, ref_search[-8:] if len(ref_search) >= 8 else ref_search, f'%{ref_search}%', f'%{ref_search}%')).fetchone()
                
                if bill_lookup:
                    actual_bill_id = str(bill_lookup['id'])
                    is_reference_number = True
                    print(f"[SWAIG][CONSOLE] Found bill by flexible reference number matching: {bill_id} -> Bill ID {actual_bill_id} (Reference: {bill_lookup['reference_number']})")
        
        if not actual_bill_id or not bill_lookup:
            print(f"[SWAIG][CONSOLE] No bill found for {bill_id} (tried as both ID and reference number) for patient {patient_id}")
            logging.warning(f"[SWAIG] No bill found for {bill_id} for patient {patient_id}")
            return f"No bill found with {'reference number' if not bill_id.isdigit() else 'ID or reference number'} '{bill_id}' for your account", {}
        
        # Verify payment method belongs to this patient
        method = db.execute('SELECT method_type FROM payment_methods WHERE id = ? AND patient_id = ?', (payment_method_id, patient['patient_id'])).fetchone()
        if not method:
            print(f"[SWAIG][CONSOLE] Invalid payment method {payment_method_id} for patient {patient_id}")
            logging.warning(f"[SWAIG] Invalid payment method {payment_method_id} for patient {patient_id}")
            return "Invalid payment method or payment method does not belong to your account", {}
        payment_method_type = method['method_type']
        
        # Use the found bill data
        bill = bill_lookup
        
        # Validate payment doesn't exceed remaining balance
        remaining_balance = float(bill['patient_portion'])
        if payment_amount > remaining_balance:
            print(f"[SWAIG][CONSOLE] Payment amount ${payment_amount:.2f} exceeds remaining balance ${remaining_balance:.2f}")
            logging.warning(f"[SWAIG] Payment amount ${payment_amount:.2f} exceeds remaining balance ${remaining_balance:.2f}")
            return f"Payment amount ${payment_amount:.2f} exceeds the remaining balance of ${remaining_balance:.2f}. The maximum payment for this bill is ${remaining_balance:.2f}.", {}
        
        new_portion = bill['patient_portion'] - float(amount)
        if new_portion > 0:
            new_status = 'partial'
        else:
            new_status = 'paid'
            new_portion = 0
        
        # Process payment
        payment_reference = f"PAY_{secrets.token_hex(4).upper()}"
        db.execute('''
            INSERT INTO payments (billing_id, patient_id, amount, payment_date, payment_method_id, payment_method_type, status, transaction_id, notes)
            VALUES (?, ?, ?, datetime('now'), ?, ?, 'completed', ?, ?)
        ''', (actual_bill_id, patient['patient_id'], amount, payment_method_id, payment_method_type, payment_reference, ''))
        db.commit()
        
        # Update billing record
        db.execute('UPDATE billing SET patient_portion = ?, status = ? WHERE id = ?', (new_portion, new_status, actual_bill_id))
        db.commit()
        
        # Send SMS confirmation for payment
        try:
            # Get payment and bill details for SMS
            payment_details = db.execute('''
                SELECT b.*, s.name as service_name, p.phone, pm.method_type,
                       CASE 
                           WHEN pm.method_type = 'credit_card' THEN '**** **** **** ' || substr(pm.card_number, -4)
                           WHEN pm.method_type = 'banking' THEN pm.bank_name || ' - ****' || substr(pm.account_number, -4)
                       END as payment_method_details
                FROM billing b
                JOIN dental_services s ON b.service_id = s.id
                JOIN patients p ON b.patient_id = p.id
                JOIN payment_methods pm ON pm.id = ?
                WHERE b.id = ?
            ''', (payment_method_id, actual_bill_id)).fetchone()
            
            if payment_details and payment_details['phone']:
                mfa = SignalWireMFA(
                    SIGNALWIRE_PROJECT_ID,
                    SIGNALWIRE_TOKEN,
                    SIGNALWIRE_SPACE,
                    os.getenv('FROM_NUMBER')
                )
                
                sms_body = f"Payment confirmation: ${amount:.2f} payment received for {payment_details['service_name']}. "
                if new_portion > 0:
                    sms_body += f"Remaining balance: ${new_portion:.2f}."
                else:
                    sms_body += "Bill is now fully paid."
                
                sms_body += f" Payment Ref: {payment_reference}"
                if payment_details['reference_number']:
                    sms_body += f" | Bill Ref: {payment_details['reference_number']}"
                
                mfa.client.messages.create(
                    from_=os.getenv('FROM_NUMBER'),
                    to=payment_details['phone'],
                    body=sms_body
                )
                print(f"[SWAIG][CONSOLE] SMS payment confirmation sent to {payment_details['phone']}")
                logging.info(f"[SWAIG] SMS payment confirmation sent to {payment_details['phone']}")
        except Exception as sms_error:
            print(f"[SWAIG][CONSOLE] Failed to send SMS payment confirmation: {sms_error}")
            logging.error(f"[SWAIG] Failed to send SMS payment confirmation: {sms_error}")
            # Don't fail the payment if SMS fails
        
        # Create response message
        response_msg = f"Payment of ${amount:.2f} processed successfully for bill reference {bill['reference_number']}. Remaining balance: ${new_portion:.2f}"
        
        print(f"[SWAIG][CONSOLE] Payment successful for bill {actual_bill_id} (input: {bill_id}), patient {patient_id}, amount ${amount}")
        logging.info(f"[SWAIG] Payment successful for bill {actual_bill_id} (input: {bill_id}), patient {patient_id}, amount ${amount}")
        return response_msg, {'patient_id': patient_id, 'amount_paid': amount, 'remaining_balance': new_portion, 'bill_id': actual_bill_id, 'reference_number': bill['reference_number'], 'payment_reference': payment_reference}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Payment failed: {e}")
        logging.error(f"[SWAIG] Payment failed: {e}")
        db.rollback()
        return f"Payment failed: {str(e)}", {}

@swaig.endpoint(
    "Send MFA Code",
    to_number=SWAIGArgument(
        type="string",
        description="Phone number in E.164 format (e.g., +1234567890) - optional if patient_id provided"
    ),
    patient_id=SWAIGArgument(
        type="integer",
        description="Patient ID to lookup phone number (optional)"
    ),
    first_name=SWAIGArgument(
        type="string",
        description="Patient first name (optional if patient_id not provided)"
    ),
    last_name=SWAIGArgument(
        type="string",
        description="Patient last name (optional if patient_id not provided)"
    )
)
def send_mfa_code(to_number=None, patient_id=None, first_name=None, last_name=None, meta_data=None, **kwargs):
    global LAST_MFA_ID, PENDING_PATIENT_DATA
    print(f"[SWAIG][CONSOLE] send_mfa_code called with to_number={to_number}, patient_id={patient_id}, first_name={first_name}, last_name={last_name}, meta_data={meta_data}")
    logging.info(f"[SWAIG] send_mfa_code called with to_number={to_number}, patient_id={patient_id}, first_name={first_name}, last_name={last_name}, meta_data={meta_data}")
    
    db = get_db()
    patient = None
    found_patient_data = None
    
    # Try to get phone number from patient record first
    if patient_id:
        print(f"[SWAIG][CONSOLE] Looking up patient with patient_id: {patient_id} (type: {type(patient_id)})")
        # Convert patient_id to string for database comparison since patient_id field is TEXT
        patient_id_str = str(patient_id)
        # Try both id and patient_id fields
        patient = db.execute("SELECT * FROM patients WHERE id = ? OR patient_id = ?", (patient_id, patient_id_str)).fetchone()
        if patient:
            found_patient_data = dict(patient)
            print(f"[SWAIG][CONSOLE] Found patient by patient_id {patient_id}: {found_patient_data.get('first_name')} {found_patient_data.get('last_name')} (ID: {found_patient_data.get('id')}, Patient ID: {found_patient_data.get('patient_id')}, Phone: {found_patient_data.get('phone')})")
            
            # Check if patient has a phone number
            if not found_patient_data.get('phone'):
                print(f"[SWAIG][CONSOLE] Patient {patient_id} found but has no phone number in record")
                return f"Patient {patient_id} found but no phone number on file. Please provide your phone number to receive the verification code.", {}
        else:
            print(f"[SWAIG][CONSOLE] No patient found with patient_id: {patient_id}")
            # Let's also check what patients do exist for debugging
            all_patients = db.execute("SELECT id, patient_id, first_name, last_name, phone FROM patients LIMIT 5").fetchall()
            print(f"[SWAIG][CONSOLE] Available patients in database: {[dict(p) for p in all_patients]}")
            return f"Patient ID {patient_id} not found in our records. Please check your patient ID or provide your first and last name instead.", {}
    elif first_name and last_name:
        print(f"[SWAIG][CONSOLE] Starting name search for first_name='{first_name}', last_name='{last_name}'")
        
        # Try exact match first
        print(f"[SWAIG][CONSOLE] Attempting exact match: first_name='{first_name.lower().strip()}', last_name='{last_name.lower().strip()}'")
        matches = db.execute("SELECT * FROM patients WHERE LOWER(TRIM(first_name)) = ? AND LOWER(TRIM(last_name)) = ?", (first_name.lower().strip(), last_name.lower().strip())).fetchall()
        print(f"[SWAIG][CONSOLE] Found {len(matches)} patient(s) with exact match first_name='{first_name}', last_name='{last_name}'")
        
        if len(matches) == 1:
            patient = matches[0]
            found_patient_data = dict(patient)
            print(f"[SWAIG][CONSOLE] Exact match found: {found_patient_data.get('first_name')} {found_patient_data.get('last_name')}")
        elif len(matches) > 1:
            print("[SWAIG][CONSOLE] Multiple patients found with exact name match; patient_id required.")
            logging.warning("[SWAIG] Multiple patients found with the same first and last name; patient_id required.")
            return "Multiple patients found with the same first and last name. Please provide patient_id.", {}
        else:
            # Try reversed name order in case names were switched
            print(f"[SWAIG][CONSOLE] No exact match found. Attempting reversed match: first_name='{last_name.lower().strip()}', last_name='{first_name.lower().strip()}'")
            matches_reversed = db.execute("SELECT * FROM patients WHERE LOWER(TRIM(first_name)) = ? AND LOWER(TRIM(last_name)) = ?", (last_name.lower().strip(), first_name.lower().strip())).fetchall()
            print(f"[SWAIG][CONSOLE] Trying reversed names: first='{last_name}', last='{first_name}' - Found {len(matches_reversed)} match(es)")
            
            if len(matches_reversed) == 1:
                patient = matches_reversed[0]
                found_patient_data = dict(patient)
                print(f"[SWAIG][CONSOLE] Found with reversed names: {found_patient_data.get('first_name')} {found_patient_data.get('last_name')}")
            elif len(matches_reversed) > 1:
                print("[SWAIG][CONSOLE] Multiple patients found with reversed names; patient_id required.")
                logging.warning("[SWAIG] Multiple patients found with reversed names; patient_id required.")
                return "Multiple patients found. Please provide patient_id for exact identification.", {}
            else:
                print(f"[SWAIG][CONSOLE] No patient found with names '{first_name} {last_name}' or '{last_name} {first_name}'")
                # Additional debugging: show what patients DO exist
                all_patients_for_debug = db.execute("SELECT first_name, last_name, phone FROM patients").fetchall()
                print(f"[SWAIG][CONSOLE] Available patients for comparison: {[(p['first_name'], p['last_name']) for p in all_patients_for_debug]}")
                return f"No patient found with name '{first_name} {last_name}'. Please check the spelling or provide patient_id.", {}
    
    # Determine the phone number to use
    phone_to_use = None
    
    if patient and patient['phone']:
        phone_to_use = patient['phone']
        print(f"[SWAIG][CONSOLE] Using patient's phone number from record: {phone_to_use}")
        logging.info(f"[SWAIG] Using patient's phone number from record: {phone_to_use}")
    elif to_number:
        phone_to_use = to_number
        print(f"[SWAIG][CONSOLE] Using provided phone number: {phone_to_use}")
        logging.info(f"[SWAIG] Using provided phone number: {phone_to_use}")
    else:
        # Fallback to caller ID from meta_data
        caller_id = meta_data.get('caller_id') if meta_data else None
        if caller_id:
            phone_to_use = caller_id
            print(f"[SWAIG][CONSOLE] Fallback to caller ID from meta_data: {phone_to_use}")
            logging.info(f"[SWAIG] Fallback to caller ID from meta_data: {phone_to_use}")
            # Try to find patient by caller ID if we don't have patient data yet
            if not found_patient_data:
                caller_phone = format_to_e164(caller_id)
                if caller_phone:
                    caller_patient = db.execute('SELECT * FROM patients WHERE phone = ?', (caller_phone,)).fetchone()
                    if caller_patient:
                        found_patient_data = dict(caller_patient)
                        print(f"[SWAIG][CONSOLE] Found patient by caller ID: {found_patient_data.get('first_name')} {found_patient_data.get('last_name')}")
        else:
            print("[SWAIG][CONSOLE] No phone number provided or found")
            logging.warning("[SWAIG] No phone number provided or found")
            return "No phone number provided or found. Please provide a phone number or patient_id.", {}
    
    # Format phone number to E.164
    e164_phone = format_to_e164(phone_to_use)
    if not e164_phone:
        print(f"[SWAIG][CONSOLE] Invalid phone number format: {phone_to_use}")
        logging.warning(f"[SWAIG] Invalid phone number format: {phone_to_use}")
        return f"Invalid phone number format: {phone_to_use}. Please provide a valid phone number in E.164 format (e.g., +1234567890).", {}
    
    print(f"[SWAIG][CONSOLE] Formatted phone number to E.164: {e164_phone}")
    logging.info(f"[SWAIG] Formatted phone number to E.164: {e164_phone}")
    
    try:
        mfa = SignalWireMFA(
            SIGNALWIRE_PROJECT_ID,
            SIGNALWIRE_TOKEN,
            SIGNALWIRE_SPACE,
            os.getenv('FROM_NUMBER')
        )
        response = mfa.send_mfa(e164_phone)
        mfa_id = response.get("id")
        if not mfa_id:
            print("[SWAIG][CONSOLE] MFA ID not found in response")
            logging.error("[SWAIG] MFA ID not found in response")
            return "MFA ID not found in response", {}
        LAST_MFA_ID = mfa_id
        
        # Store patient data temporarily for verification step
        if found_patient_data:
            print(f"[SWAIG][CONSOLE] Storing patient data for MFA session {mfa_id}: Patient {found_patient_data.get('patient_id', 'Unknown')}")
            # Store in a temporary location that verify_mfa_code can access
            # This simulates what would normally come through meta_data
            global PENDING_PATIENT_DATA
            if 'PENDING_PATIENT_DATA' not in globals():
                PENDING_PATIENT_DATA = {}
            PENDING_PATIENT_DATA[mfa_id] = found_patient_data
        
        print(f"[SWAIG][CONSOLE] MFA code sent successfully to {e164_phone}, mfa_id={mfa_id}")
        logging.info(f"[SWAIG] MFA code sent successfully to {e164_phone}, mfa_id={mfa_id}")
        
        patient_info = ""
        if found_patient_data:
            patient_info = f" for {found_patient_data.get('first_name', '')} {found_patient_data.get('last_name', '')}"
        
        return f"6-digit verification code sent successfully to {e164_phone}{patient_info}", {"mfa_id": mfa_id, "phone_number": e164_phone, "patient_found": bool(found_patient_data)}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Failed to send MFA code to {e164_phone}: {e}")
        logging.error(f"[SWAIG] Failed to send MFA code to {e164_phone}: {e}")
        return f"Failed to send MFA code: {str(e)}", {}

@swaig.endpoint(
    "Verify MFA Code",
    token=SWAIGArgument(
        type="string",
        description="The 6-digit code from SMS",
        required=True
    )
)
def verify_mfa_code(token=None, meta_data=None, **kwargs):
    import uuid
    global LAST_MFA_ID, PENDING_PATIENT_DATA
    print(f"[SWAIG][CONSOLE] verify_mfa_code called with token={token}, meta_data={meta_data}")
    logging.info(f"[SWAIG] verify_mfa_code called with token={token}, meta_data={meta_data}")
    
    if not LAST_MFA_ID or not is_valid_uuid(LAST_MFA_ID):
        print("[SWAIG][CONSOLE] No valid MFA session")
        logging.warning("[SWAIG] No valid MFA session")
        return "No valid MFA session", {}
    
    try:
        mfa = SignalWireMFA(
            SIGNALWIRE_PROJECT_ID,
            SIGNALWIRE_TOKEN,
            SIGNALWIRE_SPACE,
            os.getenv('FROM_NUMBER')
        )
        verification_response = mfa.verify_mfa(LAST_MFA_ID, token)
        print(f"[SWAIG][CONSOLE] Verification response: {verification_response}")
        logging.info(f"[SWAIG] Verification response: {verification_response}")
        
        if "mfa_id" not in verification_response:
            verification_response["mfa_id"] = LAST_MFA_ID
        
        if verification_response.get("success"):
            # Extract patient data from multiple sources
            patient_data = None
            
            # First, try to get from pending patient data (stored during send_mfa_code)
            if 'PENDING_PATIENT_DATA' in globals() and LAST_MFA_ID in PENDING_PATIENT_DATA:
                patient_data = PENDING_PATIENT_DATA[LAST_MFA_ID]
                print(f"[SWAIG][CONSOLE] Using patient data from send_mfa_code: {patient_data.get('patient_id', 'Unknown')}")
                # Clean up pending data
                del PENDING_PATIENT_DATA[LAST_MFA_ID]
            
            # Then try meta_data if we don't have patient data yet
            if not patient_data and meta_data:
                print(f"[SWAIG][CONSOLE] Checking meta_data for patient info: {list(meta_data.keys()) if isinstance(meta_data, dict) else type(meta_data)}")
                
                # Try different ways patient data might be provided in meta_data
                if isinstance(meta_data, dict):
                    if 'search_patient_result' in meta_data:
                        patient_data = meta_data['search_patient_result']
                        print("[SWAIG][CONSOLE] Found patient data in search_patient_result")
                    elif 'patient_data' in meta_data:
                        patient_data = meta_data['patient_data']
                        print("[SWAIG][CONSOLE] Found patient data in patient_data")
                    elif 'patient_id' in meta_data:
                        # If we have patient_id, look up the full patient record
                        db = get_db()
                        patient_record = db.execute('SELECT * FROM patients WHERE patient_id = ? OR id = ?', (meta_data['patient_id'], meta_data['patient_id'])).fetchone()
                        if patient_record:
                            patient_data = dict(patient_record)
                            print(f"[SWAIG][CONSOLE] Found patient by patient_id from meta_data: {patient_data.get('patient_id')}")
                    elif 'caller_id' in meta_data:
                        # Try to find patient by phone number
                        caller_phone = format_to_e164(meta_data['caller_id'])
                        if caller_phone:
                            db = get_db()
                            patient_record = db.execute('SELECT * FROM patients WHERE phone = ?', (caller_phone,)).fetchone()
                            if patient_record:
                                patient_data = dict(patient_record)
                                print(f"[SWAIG][CONSOLE] Found patient by caller_id from meta_data: {patient_data.get('patient_id')}")
                    
                    # Try direct fields in meta_data
                    if not patient_data and ('first_name' in meta_data or 'last_name' in meta_data):
                        first_name = meta_data.get('first_name')
                        last_name = meta_data.get('last_name')
                        if first_name and last_name:
                            db = get_db()
                            # Try exact match
                            patient_record = db.execute('SELECT * FROM patients WHERE LOWER(TRIM(first_name)) = ? AND LOWER(TRIM(last_name)) = ?', (first_name.lower().strip(), last_name.lower().strip())).fetchone()
                            if patient_record:
                                patient_data = dict(patient_record)
                                print(f"[SWAIG][CONSOLE] Found patient by name from meta_data: {patient_data.get('patient_id')}")
            
            # Store the verified patient data using new session management
            if patient_data:
                store_verified_patient(LAST_MFA_ID, patient_data)
                
                # Generate a challenge token for subsequent API calls
                challenge_token = str(uuid.uuid4())
                
                # Store the challenge token with patient data for protected functions
                store_challenge_token(challenge_token, patient_data)
                
                print(f"[SWAIG][CONSOLE] Generated challenge token: {challenge_token}")
                print(f"[SWAIG][CONSOLE] AI should use this challenge token for subsequent calls: {challenge_token}")
                logging.info(f"[SWAIG] Generated challenge token for patient {patient_data.get('patient_id')}")
                logging.info(f"[SWAIG] AI should use challenge token {challenge_token} for subsequent calls")
                
                return f"MFA verified successfully for patient {patient_data.get('patient_id', 'Unknown')} ({patient_data.get('first_name', '')} {patient_data.get('last_name', '')}). You can now access your account. Use challenge token {challenge_token} for subsequent requests.", {
                    "mfa_id": LAST_MFA_ID, 
                    "patient_verified": True, 
                    "patient_id": patient_data.get('patient_id'),
                    "challenge_token": challenge_token
                }
            else:
                print("[SWAIG][CONSOLE] MFA verified but no patient data found in meta_data or pending data")
                logging.warning("[SWAIG] MFA verified but no patient data found in meta_data or pending data")
                return "MFA verified successfully, but patient data not found. Please provide patient information or try sending the MFA code again with your name or patient ID.", {"mfa_id": LAST_MFA_ID, "patient_verified": False}
        else:
            error_message = verification_response.get("message", "Invalid MFA code. Please try again.")
            print(f"[SWAIG][CONSOLE] MFA verification failed: {error_message}")
            logging.warning(f"[SWAIG] MFA verification failed: {error_message}")
            return error_message, {"mfa_id": LAST_MFA_ID}
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Verification failed: {e}")
        logging.error(f"[SWAIG] Verification failed: {e}")
        return f"Verification failed: {str(e)}", {"mfa_id": LAST_MFA_ID if LAST_MFA_ID else None}

@app.route('/api/test-sms', methods=['POST'])
@login_required
def api_test_sms():
    db = get_db()
    user = get_current_user()
    if not user or 'phone' not in user.keys() or not user['phone']:
        return jsonify({'success': False, 'error': 'No phone number found for user'}), 400
    try:
        mfa = SignalWireMFA(
            SIGNALWIRE_PROJECT_ID,
            SIGNALWIRE_TOKEN,
            SIGNALWIRE_SPACE,
            os.getenv('FROM_NUMBER')
        )
        mfa.client.messages.create(
            from_=os.getenv('FROM_NUMBER'),
            to=user['phone'],
            body='This is a test SMS from your SignalWire Dental Office System.'
        )
        return jsonify({'success': True}), 200
    except Exception as e:
        app.logger.error(f"Failed to send test SMS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-mfa', methods=['POST'])
@login_required
def api_test_mfa():
    db = get_db()
    user = get_current_user()
    if not user or 'phone' not in user.keys() or not user['phone']:
        return jsonify({'success': False, 'error': 'No phone number found for user'}), 400
    try:
        mfa = SignalWireMFA(
            SIGNALWIRE_PROJECT_ID,
            SIGNALWIRE_TOKEN,
            SIGNALWIRE_SPACE,
            os.getenv('FROM_NUMBER')
        )
        response = mfa.send_mfa(user['phone'])
        mfa_id = response.get('id')
        if not mfa_id:
            return jsonify({'success': False, 'error': 'MFA ID not found in response'}), 500
        return jsonify({'success': True, 'mfa_id': mfa_id}), 200
    except Exception as e:
        app.logger.error(f"Failed to send test MFA: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-mfa', methods=['POST'])
@login_required
def api_verify_mfa():
    data = request.get_json()
    mfa_id = data.get('mfa_id')
    code = data.get('code')
    if not mfa_id or not code:
        return jsonify({'success': False, 'error': 'Missing MFA ID or code'}), 400
    try:
        mfa = SignalWireMFA(
            SIGNALWIRE_PROJECT_ID,
            SIGNALWIRE_TOKEN,
            SIGNALWIRE_SPACE,
            os.getenv('FROM_NUMBER')
        )
        result = mfa.verify_mfa(mfa_id, code)
        if result.get('success'):
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': result.get('message', 'Invalid MFA code')}), 401
    except Exception as e:
        app.logger.error(f"Failed to verify MFA: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patients/<int:patient_id>', methods=['GET', 'PUT'])
@login_required
def api_get_patient(patient_id):
    if request.method == 'GET':
        db = get_db()
        # First try to find by database ID
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        
        # If not found, try to find by patient_id field (7-digit ID)
        if not patient:
            patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (str(patient_id),)).fetchone()
            
        if not patient:
            return jsonify({'message': 'Patient not found'}), 404
        return jsonify(dict(patient))
    
    elif request.method == 'PUT':
        if session['user_type'] != 'dentist':
            return jsonify({'success': False, 'message': 'Unauthorized - Dentist access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        db = get_db()
        
        # First try to find by database ID
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        use_db_id = True
        
        # If not found, try to find by patient_id field (7-digit ID)
        if not patient:
            patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (str(patient_id),)).fetchone()
            use_db_id = False
            
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        try:
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 
                            'date_of_birth', 'medical_history', 'insurance_info']
            
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    params.append(data[field])
            
            if not update_fields:
                return jsonify({'success': False, 'message': 'No valid fields to update'}), 400
            
            # Add patient identifier to params for WHERE clause
            params.append(str(patient_id))
            query = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
            
            db.execute(query, params)
            db.commit()
            
            # Return updated patient data
            updated_patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (str(patient_id),)).fetchone()
            
            return jsonify({'success': True, 'message': 'Patient updated successfully', 'patient': dict(updated_patient)})
            
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/patient/<int:patient_id>/history')
@login_required
def patient_history_for_dentist(patient_id):
    if session['user_type'] != 'dentist':
        return redirect(url_for('patient_dashboard'))
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
    if not patient:
        return render_template('404.html'), 404
    appointments = db.execute('''
        SELECT a.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM appointments a
        JOIN dentists d ON a.dentist_id = d.id
        JOIN dental_services s ON a.service_id = s.id
        WHERE a.patient_id = ?
        ORDER BY a.start_time DESC
    ''', (patient_id,)).fetchall()
    treatments = db.execute('''
        SELECT th.*, d.first_name as dentist_first_name, d.last_name as dentist_last_name,
               s.name as service_name
        FROM treatment_history th
        JOIN dentists d ON th.dentist_id = d.id
        JOIN dental_services s ON th.service_id = s.id
        WHERE th.patient_id = ?
        ORDER BY th.treatment_date DESC
    ''', (patient_id,)).fetchall()
    bills = db.execute('''
        SELECT b.*, s.name as service_name
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
        WHERE b.patient_id = ?
        ORDER BY b.due_date DESC
    ''', (patient_id,)).fetchall()
    return render_template('patient_history.html',
                         patient=patient,
                         appointments=appointments,
                         treatments=treatments,
                         bills=bills)

@app.route('/api/patients', methods=['GET'])
@login_required
def api_get_patients():
    db = get_db()
    patients = db.execute('SELECT id, first_name, last_name, patient_id FROM patients ORDER BY last_name, first_name').fetchall()
    return jsonify([dict(p) for p in patients])

@app.route('/api/treatments', methods=['POST'])
@login_required
def api_create_treatment():
    if session['user_type'] != 'dentist':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    required_fields = ['patient_id', 'service_id', 'treatment_date', 'diagnosis', 'treatment_notes']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Robustly handle follow_up_date
    follow_up_date = data.get('follow_up_date')
    if not follow_up_date or str(follow_up_date).strip().lower() in ('', 'null', 'none'):
        follow_up_date = None

    db = get_db()
    try:
        # Insert treatment
        db.execute('''
            INSERT INTO treatment_history (patient_id, dentist_id, service_id, treatment_date, diagnosis, treatment_notes, follow_up_date, reference_number, bill_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['patient_id'],
            session['user_id'],
            data['service_id'],
            data['treatment_date'],
            data['diagnosis'],
            data['treatment_notes'],
            follow_up_date,
            data.get('reference_number'),
            data.get('bill_amount', 0.0)
        ))

        # Generate unique bill number
        bill_number = generate_unique_bill_number()

        # Insert corresponding bill
        db.execute('''
            INSERT INTO billing (
                patient_id, dentist_id, service_id, amount, insurance_coverage, patient_portion,
                status, due_date, reference_number, bill_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['patient_id'],
            session['user_id'],
            data['service_id'],
            data.get('bill_amount', 0.0),
            0.0,  # insurance_coverage
            data.get('bill_amount', 0.0),  # patient_portion
            'pending',
            data['treatment_date'],  # due_date
            data.get('reference_number'),
            bill_number,
            data['treatment_date']
        ))

        db.commit()
        return jsonify({'success': True, 'message': 'Treatment and bill saved successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@swaig.endpoint(
    "Get Appointments",
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    ),
    service_type=SWAIGArgument(
        type="string",
        description="Optional service type to filter appointments (e.g., 'teeth whitening', 'cleaning', 'checkup', 'orthodontics')",
        required=False
    )
)
def swaig_get_appointments(challenge_token=None, service_type=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_get_appointments called with challenge_token={challenge_token}, service_type={service_type}")
    logging.info(f"[SWAIG] swaig_get_appointments called with challenge_token={challenge_token}, service_type={service_type}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        print(f"[SWAIG][CONSOLE] Patient not found: {patient_id}")
        logging.warning(f"[SWAIG] Patient not found: {patient_id}")
        return "Patient account not found", {}
    
    # Build query with optional service filtering
    query = '''
        SELECT a.*, s.name as service_name, s.type as service_type,
               CASE 
                   WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                   ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
               END as dentist_name
        FROM appointments a
        JOIN dental_services s ON a.service_id = s.id
        JOIN dentists d ON a.dentist_id = d.id
        WHERE a.patient_id = ? AND a.status != 'cancelled'
    '''
    
    params = [patient['id']]
    
    # Add service type filtering if provided
    if service_type:
        # Flexible matching: check service name, type, and partial matches
        query += '''
            AND (UPPER(s.name) LIKE ? OR 
                 UPPER(s.type) LIKE ? OR 
                 UPPER(s.name) LIKE ? OR 
                 UPPER(s.description) LIKE ?)
        '''
        service_search = f"%{service_type.upper()}%"
        # Handle common variations
        if 'whitening' in service_type.lower():
            service_variations = ['%TEETH%WHITENING%', '%WHITENING%', '%TEETH%WHITENING%', '%WHITENING%']
        elif 'cleaning' in service_type.lower():
            service_variations = ['%CLEANING%', '%CLEAN%', '%HYGIENE%', '%CLEANING%']
        elif 'checkup' in service_type.lower():
            service_variations = ['%CHECKUP%', '%CHECK%', '%EXAM%', '%CHECKUP%']
        elif 'orthodont' in service_type.lower():
            service_variations = ['%ORTHODONT%', '%BRACES%', '%ORTHODONT%', '%BRACES%']
        else:
            service_variations = [service_search, service_search, service_search, service_search]
        
        params.extend(service_variations)
    
    query += ' ORDER BY a.start_time ASC'
    
    appointments = db.execute(query, params).fetchall()
    
    # Also get count of cancelled appointments for informational purposes
    cancelled_count = db.execute('''
        SELECT COUNT(*) as count
        FROM appointments
        WHERE patient_id = ? AND status = 'cancelled'
    ''', (patient['id'],)).fetchone()['count']
    
    print(f"[SWAIG][CONSOLE] Returning {len(appointments)} appointments for patient {patient_id}" + 
          (f" (filtered by service_type: {service_type})" if service_type else ""))
    logging.info(f"[SWAIG] Returning {len(appointments)} appointments for patient {patient_id}" + 
                (f" (filtered by service_type: {service_type})" if service_type else ""))
    
    if appointments:
        from datetime import datetime
        
        now = datetime.now()
        upcoming_appointments = []
        past_appointments = []
        
        for appt in appointments:
            # Convert sqlite3.Row to dict for easier access
            appt_dict = dict(appt)
            
            # Parse appointment datetime
            try:
                if 'T' in appt_dict['start_time']:
                    appt_datetime = datetime.fromisoformat(appt_dict['start_time'].replace('T', ' '))
                else:
                    appt_datetime = datetime.strptime(appt_dict['start_time'], '%Y-%m-%d %H:%M:%S')
                
                if appt_datetime >= now:
                    upcoming_appointments.append(appt_dict)
                else:
                    past_appointments.append(appt_dict)
            except:
                # If parsing fails, assume it's in the future for safety
                upcoming_appointments.append(appt_dict)
        
        # Build detailed response based on filtering
        if service_type:
            # Filtered response - focus on the specific service
            if upcoming_appointments:
                response = f"You have {len(upcoming_appointments)} upcoming {service_type} appointment(s):"
                
                for i, appt in enumerate(upcoming_appointments):
                    try:
                        if 'T' in appt['start_time']:
                            appt_datetime = datetime.fromisoformat(appt['start_time'].replace('T', ' '))
                        else:
                            appt_datetime = datetime.strptime(appt['start_time'], '%Y-%m-%d %H:%M:%S')
                        
                        appt_date = appt_datetime.strftime('%A, %B %d, %Y')
                        appt_time = appt_datetime.strftime('%I:%M %p')
                    except:
                        appt_date = appt['start_time']
                        appt_time = "Time TBD"
                    
                    response += f"\n{i+1}. {appt_date} at {appt_time} - {appt['service_name']} with {appt['dentist_name']} (ID: {appt['id']})"
                    if appt.get('notes'):
                        response += f"\n   Notes: {appt['notes']}"
                
                if past_appointments:
                    response += f"\n\nYou also have {len(past_appointments)} past {service_type} appointments."
            else:
                past_info = f" You have {len(past_appointments)} past {service_type} appointments." if past_appointments else ""
                response = f"You have no upcoming {service_type} appointments scheduled.{past_info}"
        else:
            # Standard response - show all appointments
            if upcoming_appointments:
                next_appointment = upcoming_appointments[0]
                
                # Format next appointment details
                try:
                    if 'T' in next_appointment['start_time']:
                        next_appt_datetime = datetime.fromisoformat(next_appointment['start_time'].replace('T', ' '))
                    else:
                        next_appt_datetime = datetime.strptime(next_appointment['start_time'], '%Y-%m-%d %H:%M:%S')
                    
                    formatted_date = next_appt_datetime.strftime('%A, %B %d, %Y')
                    formatted_time = next_appt_datetime.strftime('%I:%M %p')
                except:
                    formatted_date = next_appointment['start_time']
                    formatted_time = "Time TBD"
                
                response = f"Your next appointment is scheduled for {formatted_date} at {formatted_time}. "
                response += f"It's a {next_appointment['service_name']} appointment with {next_appointment['dentist_name']}. "
                response += f"(Appointment ID: {next_appointment['id']})"
                
                if next_appointment.get('notes'):
                    response += f" Notes: {next_appointment['notes']}"
                
                # If there are multiple upcoming appointments, list them all
                if len(upcoming_appointments) > 1:
                    response += f"\n\nYou have {len(upcoming_appointments)} total upcoming appointments:"
                    
                    for i, appt in enumerate(upcoming_appointments):
                        try:
                            if 'T' in appt['start_time']:
                                appt_datetime = datetime.fromisoformat(appt['start_time'].replace('T', ' '))
                            else:
                                appt_datetime = datetime.strptime(appt['start_time'], '%Y-%m-%d %H:%M:%S')
                            
                            appt_date = appt_datetime.strftime('%A, %B %d, %Y')
                            appt_time = appt_datetime.strftime('%I:%M %p')
                        except:
                            appt_date = appt['start_time']
                            appt_time = "Time TBD"
                        
                        response += f"\n{i+1}. {appt_date} at {appt_time} - {appt['service_name']} with {appt['dentist_name']} (ID: {appt['id']})"
                    
                    if len(past_appointments) > 0:
                        response += f"\n\nYou also have {len(past_appointments)} past appointments."
                    
                    if cancelled_count > 0:
                        response += f" ({cancelled_count} cancelled appointments not shown)"
                elif len(past_appointments) > 0:
                    response += f"\n\nYou also have {len(past_appointments)} past appointments."
                    if cancelled_count > 0:
                        response += f" ({cancelled_count} cancelled appointments not shown)"
            else:
                response = f"You have no upcoming appointments scheduled. You have {len(past_appointments)} past appointments."
                if cancelled_count > 0:
                    response += f" ({cancelled_count} cancelled appointments not shown)"
        
        return response, {
            'appointments': [dict(a) for a in appointments], 
            'patient_id': patient_id,
            'service_type_filter': service_type,
            'total_count': len(appointments),
            'upcoming_count': len(upcoming_appointments),
            'past_count': len(past_appointments),
            'cancelled_count': cancelled_count,
            'next_appointment': upcoming_appointments[0] if upcoming_appointments else None
        }
    else:
        if service_type:
            cancelled_info = f" ({cancelled_count} cancelled appointments not shown)" if cancelled_count > 0 else ""
            return f"You have no {service_type} appointments scheduled.{cancelled_info}", {
                'appointments': [], 
                'patient_id': patient_id,
                'service_type_filter': service_type,
                'cancelled_count': cancelled_count
            }
        else:
            cancelled_info = f" ({cancelled_count} cancelled appointments not shown)" if cancelled_count > 0 else ""
            return f"You have no appointments scheduled.{cancelled_info}", {
                'appointments': [], 
                'patient_id': patient_id,
                'cancelled_count': cancelled_count
            }

@swaig.endpoint(
    "Get Payment Methods",
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_get_payment_methods(challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_get_payment_methods called with challenge_token={challenge_token}")
    logging.info(f"[SWAIG] swaig_get_payment_methods called with challenge_token={challenge_token}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        print(f"[SWAIG][CONSOLE] Patient not found: {patient_id}")
        logging.warning(f"[SWAIG] Patient not found: {patient_id}")
        return "Patient account not found", {}
    
    # Fetch payment methods
    payment_methods = db.execute('''
        SELECT id, method_type,
               CASE 
                   WHEN method_type = 'credit_card' THEN '**** **** **** ' || substr(card_number, -4)
                   WHEN method_type = 'banking' THEN bank_name || ' - ****' || substr(account_number, -4)
               END as details,
               is_default
        FROM payment_methods
        WHERE patient_id = ?
        ORDER BY is_default DESC, created_at DESC
    ''', (patient['id'],)).fetchall()
    
    print(f"[SWAIG][CONSOLE] Returning {len(payment_methods)} payment methods for patient {patient_id}")
    logging.info(f"[SWAIG] Returning {len(payment_methods)} payment methods for patient {patient_id}")
    
    if payment_methods:
        methods_list = []
        for method in payment_methods:
            method_info = f"ID {method['id']}: {method['details']}"
            if method['is_default']:
                method_info += " (Default)"
            methods_list.append(method_info)
        
        summary = f"You have {len(payment_methods)} payment method(s) on file: " + ", ".join(methods_list)
        return summary, {
            'payment_methods': [dict(m) for m in payment_methods], 
            'patient_id': patient_id,
            'count': len(payment_methods)
        }
    else:
        return "You have no payment methods on file. Please add a payment method to make payments.", {'payment_methods': [], 'patient_id': patient_id}

@swaig.endpoint(
    "Get Appointment Details",
    appointment_id=SWAIGArgument(
        type="string",
        description="Appointment ID to get details for",
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_get_appointment_details(appointment_id=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_get_appointment_details called with appointment_id={appointment_id}")
    logging.info(f"[SWAIG] swaig_get_appointment_details called with appointment_id={appointment_id}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    db = get_db()
    
    # Get the appointment with all details and verify it belongs to the authenticated patient
    appointment = db.execute('''
        SELECT a.*, 
               s.name as service_name, s.description as service_description, s.price as service_price,
               CASE 
                   WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                   ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
               END as dentist_name,
               d.specialization as dentist_specialization,
               p.patient_id as patient_external_id
        FROM appointments a
        JOIN dental_services s ON a.service_id = s.id
        JOIN dentists d ON a.dentist_id = d.id
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()
    
    if not appointment:
        print(f"[SWAIG][CONSOLE] Appointment not found: {appointment_id}")
        logging.warning(f"[SWAIG] Appointment not found: {appointment_id}")
        return "Appointment not found", {}
    
    # Verify the appointment belongs to the authenticated patient
    if appointment['patient_external_id'] != patient_id:
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} does not belong to patient {patient_id}")
        logging.warning(f"[SWAIG] Appointment {appointment_id} does not belong to patient {patient_id}")
        return "You can only view details of your own appointments", {}
    
    # Check if the appointment is cancelled
    if appointment['status'] == 'cancelled':
        print(f"[SWAIG][CONSOLE] Appointment {appointment_id} is cancelled")
        logging.info(f"[SWAIG] Appointment {appointment_id} is cancelled")
        return f"Appointment #{appointment_id} has been cancelled and is no longer active. Please schedule a new appointment if needed.", {
            'appointment': dict(appointment),
            'patient_id': patient_id,
            'appointment_id': appointment_id,
            'status': 'cancelled'
        }
    
    # Format the appointment details
    appt_dict = dict(appointment)
    
    # Parse dates and times for user-friendly display
    start_datetime = datetime.fromisoformat(appointment['start_time'].replace(' ', 'T'))
    end_datetime = datetime.fromisoformat(appointment['end_time'].replace(' ', 'T'))
    
    date_str = start_datetime.strftime('%A, %B %d, %Y')
    start_time_str = start_datetime.strftime('%I:%M %p')
    end_time_str = end_datetime.strftime('%I:%M %p')
    
    # Determine time slot
    time_slot = "Custom Time"
    if appointment['start_time'].endswith('08:00:00') and appointment['end_time'].endswith('11:00:00'):
        time_slot = "Morning (8:00 AM - 11:00 AM)"
    elif appointment['start_time'].endswith('14:00:00') and appointment['end_time'].endswith('16:00:00'):
        time_slot = "Afternoon (2:00 PM - 4:00 PM)"
    elif appointment['start_time'].endswith('18:00:00') and appointment['end_time'].endswith('20:00:00'):
        time_slot = "Evening (6:00 PM - 8:00 PM)"
    elif appointment['start_time'].endswith('08:00:00') and appointment['end_time'].endswith('20:00:00'):
        time_slot = "All Day (8:00 AM - 8:00 PM)"
    
    # Create detailed response
    details = f"Appointment #{appointment_id} Details:\n"
    details += f"Date: {date_str}\n"
    details += f"Time: {time_slot}\n"
    details += f"Service: {appointment['service_name']}"
    if appointment['service_description']:
        details += f" - {appointment['service_description']}"
    details += f"\nDentist: {appointment['dentist_name']}"
    if appointment['dentist_specialization']:
        details += f" ({appointment['dentist_specialization']})"
    details += f"\nStatus: {appointment['status'].title()}"
    if appointment['notes']:
        details += f"\nNotes: {appointment['notes']}"
    details += f"\nSMS Reminders: {'Enabled' if appointment['sms_reminder'] else 'Disabled'}"
    
    print(f"[SWAIG][CONSOLE] Returning appointment details for appointment {appointment_id}, patient {patient_id}")
    logging.info(f"[SWAIG] Returning appointment details for appointment {appointment_id}, patient {patient_id}")
    
    return details, {
        'appointment': appt_dict,
        'patient_id': patient_id,
        'appointment_id': appointment_id,
        'formatted_date': date_str,
        'formatted_time_slot': time_slot,
        'start_time': start_time_str,
        'end_time': end_time_str
    }

@swaig.endpoint(
    "Get Bill Details",
    bill_id=SWAIGArgument(
        type="string",
        description="Bill ID to get details for",
        required=True
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_get_bill_details(bill_id=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_get_bill_details called with bill_id={bill_id}")
    logging.info(f"[SWAIG] swaig_get_bill_details called with bill_id={bill_id}")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    print(f"[SWAIG][CONSOLE] Retrieved patient_data: {patient_data}")
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    # Use the patient data directly from session instead of database lookup
    patient_internal_id = patient_data.get('id')
    print(f"[SWAIG][CONSOLE] Patient internal ID: {patient_internal_id}")
    if not patient_internal_id:
        print(f"[SWAIG][CONSOLE] No internal patient ID in session for patient {patient_id}")
        logging.warning(f"[SWAIG] No internal patient ID in session for patient {patient_id}")
        return "Patient session data incomplete. Please verify your identity again.", {}
    
    db = get_db()
    
    # Get the bill with all details and verify it belongs to the authenticated patient
    # Handle numeric bill IDs, bill numbers, and reference numbers
    bill = None
    
    # First try as numeric bill ID
    if bill_id.isdigit():
        bill_id_int = int(bill_id)
        bill = db.execute('''
            SELECT b.*, 
                   s.name as service_name, s.description as service_description, s.price as service_price,
                   th.diagnosis, th.treatment_notes, th.treatment_date,
                   CASE 
                       WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                       ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                   END as dentist_name
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN treatment_history th ON b.reference_number = th.reference_number
            LEFT JOIN dentists d ON b.dentist_id = d.id
            WHERE b.id = ? AND b.patient_id = ?
        ''', (bill_id_int, patient_internal_id)).fetchone()
        
        # If not found by ID, try by bill_number
        if not bill:
            print(f"[SWAIG][CONSOLE] Bill ID {bill_id} not found, trying as bill_number")
            bill = db.execute('''
                SELECT b.*, 
                       s.name as service_name, s.description as service_description, s.price as service_price,
                       th.diagnosis, th.treatment_notes, th.treatment_date,
                       CASE 
                           WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                           ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                       END as dentist_name
                FROM billing b
                JOIN dental_services s ON b.service_id = s.id
                LEFT JOIN treatment_history th ON b.reference_number = th.reference_number
                LEFT JOIN dentists d ON b.dentist_id = d.id
                WHERE b.bill_number = ? AND b.patient_id = ?
            ''', (bill_id, patient_internal_id)).fetchone()
            if bill:
                print(f"[SWAIG][CONSOLE] Found bill by bill_number: {bill_id}")
    
    # If still not found, try as reference number
    if not bill:
        print(f"[SWAIG][CONSOLE] Treating {bill_id} as reference number")
        bill = db.execute('''
            SELECT b.*, 
                   s.name as service_name, s.description as service_description, s.price as service_price,
                   th.diagnosis, th.treatment_notes, th.treatment_date,
                   CASE 
                       WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                       ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
                   END as dentist_name
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            LEFT JOIN treatment_history th ON b.reference_number = th.reference_number
            LEFT JOIN dentists d ON b.dentist_id = d.id
            WHERE b.reference_number = ? AND b.patient_id = ?
        ''', (bill_id, patient_internal_id)).fetchone()
    
    if not bill:
        print(f"[SWAIG][CONSOLE] Bill not found: {bill_id} for patient internal ID {patient_internal_id}")
        logging.warning(f"[SWAIG] Bill not found: {bill_id} for patient internal ID {patient_internal_id}")
        return "Bill not found or does not belong to your account", {}
    
    print(f"[SWAIG][CONSOLE] Found bill: {dict(bill)}")
    
    # Format the bill details
    bill_dict = dict(bill)
    
    # Parse dates for user-friendly display
    due_date_str = "Not specified"
    treatment_date_str = "Not specified"
    created_date_str = "Not specified"
    
    if bill['due_date']:
        try:
            due_date_obj = datetime.strptime(bill['due_date'], '%Y-%m-%d')
            due_date_str = due_date_obj.strftime('%A, %B %d, %Y')
        except:
            due_date_str = bill['due_date']
    
    if bill['treatment_date']:
        try:
            treatment_date_obj = datetime.strptime(bill['treatment_date'], '%Y-%m-%d')
            treatment_date_str = treatment_date_obj.strftime('%A, %B %d, %Y')
        except:
            treatment_date_str = bill['treatment_date']
    
    if bill['created_at']:
        try:
            created_date_obj = datetime.strptime(bill['created_at'], '%Y-%m-%d')
            created_date_str = created_date_obj.strftime('%A, %B %d, %Y')
        except:
            created_date_str = bill['created_at']
    
    # Calculate patient portion (amount minus insurance coverage)
    patient_portion = float(bill['amount']) - float(bill['insurance_coverage'] or 0)
    
    # Get payment history for this bill
    payments = db.execute('''
        SELECT payment_date, amount, payment_method_type
        FROM payments
        WHERE billing_id = ?
        ORDER BY payment_date DESC
    ''', (bill['id'],)).fetchall()
    
    total_paid = sum(float(p['amount']) for p in payments)
    remaining_balance = max(0, patient_portion - total_paid)
    
    # Create detailed response
    details = f"Bill Verified - Reference #{bill['reference_number']}:\n"
    details += f"Bill #: {bill['bill_number'] if 'bill_number' in bill else bill['id']}\n"
    details += f"Service: {bill['service_name']}"
    if bill['service_description']:
        details += f" - {bill['service_description']}"
    details += f"\nTotal Amount: ${float(bill['amount']):.2f}"
    details += f"\nInsurance Coverage: ${float(bill['insurance_coverage'] or 0):.2f}"
    details += f"\nPatient Portion: ${patient_portion:.2f}"
    details += f"\nRemaining Balance: ${remaining_balance:.2f}"
    details += f"\nStatus: {bill['status'].title()}"
    details += f"\nDue Date: {due_date_str}"
    details += f"\nBill Date: {created_date_str}"
    
    if bill['dentist_name']:
        details += f"\nProvider: {bill['dentist_name']}"
    
    if payments:
        details += f"\nPayments Made: {len(payments)} payment(s), Total: ${total_paid:.2f}"
    else:
        details += f"\nPayments Made: No payments yet"
    
    print(f"[SWAIG][CONSOLE] Returning bill details for bill {bill_id}, patient {patient_id}")
    logging.info(f"[SWAIG] Returning bill details for bill {bill_id}, patient {patient_id}")
    
    return details, {
        'bill': bill_dict,
        'patient_id': patient_id,
        'bill_id': bill_id,
        'formatted_due_date': due_date_str,
        'formatted_treatment_date': treatment_date_str,
        'formatted_created_date': created_date_str,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
        'payments': [dict(p) for p in payments]
    }

@swaig.endpoint(
    "Verify Bill Reference",
    reference_number=SWAIGArgument(
        type="string",
        description="Bill reference number (full or last 8 characters, case insensitive)",
        required=False
    ),
    service_name=SWAIGArgument(
        type="string",
        description="Service name to search for (e.g., 'cleaning', 'filling', 'whitening')",
        required=False
    ),
    status=SWAIGArgument(
        type="string",
        description="Bill status to search for (paid, pending, overdue)",
        required=False
    ),
    date=SWAIGArgument(
        type="string",
        description="Specific date to search for (YYYY-MM-DD format) - searches bill date, due date, and treatment date",
        required=False
    ),
    due_date=SWAIGArgument(
        type="string",
        description="Specific due date (YYYY-MM-DD format)",
        required=False
    ),
    amount=SWAIGArgument(
        type="number",
        description="Specific amount to search for",
        required=False
    ),
    amount_min=SWAIGArgument(
        type="number",
        description="Minimum amount to search for",
        required=False
    ),
    amount_max=SWAIGArgument(
        type="number",
        description="Maximum amount to search for",
        required=False
    ),
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_verify_bill_reference(reference_number=None, service_name=None, status=None, date=None, due_date=None, amount=None, amount_min=None, amount_max=None, challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_verify_bill_reference called with reference_number={reference_number}, service_name={service_name}, status={status}, date={date}, due_date={due_date}, amount={amount}")
    logging.info(f"[SWAIG] swaig_verify_bill_reference called with multiple search criteria")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    # Get verified patient data using challenge token
    patient_data = get_patient_by_challenge_token(challenge_token)
    patient_id = patient_data.get('patient_id')
    
    if not patient_id:
        print("[SWAIG][CONSOLE] No patient ID in challenge token data")
        logging.warning("[SWAIG] No patient ID in challenge token data")
        return "Patient information not found. Please verify your identity again.", {}
    
    # Use the patient data directly from session instead of database lookup
    patient_internal_id = patient_data.get('id')
    if not patient_internal_id:
        print(f"[SWAIG][CONSOLE] No internal patient ID in session for patient {patient_id}")
        logging.warning(f"[SWAIG] No internal patient ID in session for patient {patient_id}")
        return "Patient session data incomplete. Please verify your identity again.", {}

    db = get_db()
    
    # Check if any search criteria provided
    has_criteria = any([reference_number, service_name, status, date, due_date, amount, amount_min, amount_max])
    if not has_criteria:
        return "Please provide at least one search criteria: reference number, service name, status, date, due date, or amount.", {}
    
    # Build dynamic SQL query based on provided criteria
    base_query = '''
        SELECT b.*, 
               s.name as service_name, s.description as service_description,
               CASE 
                   WHEN d.first_name LIKE 'Dr.%' THEN d.first_name || ' ' || d.last_name
                   ELSE 'Dr. ' || d.first_name || ' ' || d.last_name
               END as dentist_name,
               (b.amount - COALESCE(b.insurance_coverage, 0)) as patient_portion,
               CASE 
                   WHEN b.status = 'paid' THEN 'Paid'
                   WHEN b.due_date < date('now') AND b.status != 'paid' THEN 'Overdue'
                   ELSE 'Pending'
               END as display_status
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
        LEFT JOIN dentists d ON b.dentist_id = d.id
        WHERE b.patient_id = ?
    '''
    
    conditions = []
    params = [patient_internal_id]
    
    # Reference number search (flexible matching)
    if reference_number:
        ref_search = reference_number.strip().upper()
        conditions.append("""(
            UPPER(b.reference_number) = ? OR 
            UPPER(SUBSTR(b.reference_number, -8)) = ? OR
            UPPER(b.reference_number) LIKE ? OR
            UPPER(REPLACE(b.reference_number, '_', '')) LIKE ?
        )""")
        params.extend([ref_search, ref_search[-8:] if len(ref_search) >= 8 else ref_search, f'%{ref_search}%', f'%{ref_search}%'])
    
    # Service name search (case insensitive, partial match)
    if service_name:
        conditions.append("UPPER(s.name) LIKE ? OR UPPER(s.description) LIKE ?")
        service_search = f"%{service_name.upper()}%"
        params.extend([service_search, service_search])
    
    # Status search
    if status:
        status_lower = status.lower()
        if status_lower in ['paid', 'pending', 'overdue', 'partial']:
            if status_lower == 'paid':
                conditions.append("b.status = 'paid'")
            elif status_lower == 'overdue':
                # Overdue: past due date AND not paid
                conditions.append("b.due_date < date('now') AND b.status != 'paid'")
            elif status_lower == 'pending':
                # Pending: specifically pending status OR (not paid and not overdue)
                conditions.append("(b.status = 'pending' OR (b.status != 'paid' AND b.status != 'partial' AND b.due_date >= date('now')))")
            elif status_lower == 'partial':
                conditions.append("b.status = 'partial'")
    
    # Date search (searches bill created date and due date only)
    if date:
        conditions.append("(b.created_at = ? OR b.due_date = ?)")
        params.extend([date, date])
    
    # Specific due date search
    if due_date:
        conditions.append("b.due_date = ?")
        params.append(due_date)
    
    # Amount search (exact amount or range) - use calculated patient_portion
    if amount is not None:
        conditions.append("(b.amount = ? OR (b.amount - COALESCE(b.insurance_coverage, 0)) = ?)")
        params.extend([amount, amount])
    
    if amount_min is not None:
        conditions.append("(b.amount >= ? OR (b.amount - COALESCE(b.insurance_coverage, 0)) >= ?)")
        params.extend([amount_min, amount_min])
    
    if amount_max is not None:
        conditions.append("(b.amount <= ? OR (b.amount - COALESCE(b.insurance_coverage, 0)) <= ?)")
        params.extend([amount_max, amount_max])
    
    # Add conditions to query
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    base_query += " ORDER BY b.created_at DESC"
    
    bills = db.execute(base_query, params).fetchall()
    
    print(f"[SWAIG][CONSOLE] Found {len(bills)} bills matching search criteria for patient {patient_id}")
    logging.info(f"[SWAIG] Found {len(bills)} bills matching search criteria for patient {patient_id}")
    
    if not bills:
        # Provide user-friendly feedback about what was searched
        criteria_desc = []
        if reference_number: criteria_desc.append(f"reference '{reference_number}'")
        if service_name: criteria_desc.append(f"service '{service_name}'")
        if status: criteria_desc.append(f"status '{status}'")
        if date: criteria_desc.append(f"date '{date}'")
        if due_date: criteria_desc.append(f"due date '{due_date}'")
        if amount is not None: criteria_desc.append(f"amount ${amount:.2f}")
        if amount_min is not None or amount_max is not None:
            amount_range = f"amount ${amount_min or 0:.2f} to ${amount_max or 999999:.2f}"
            criteria_desc.append(amount_range)
        
        criteria_text = ", ".join(criteria_desc)
        
        # Get all bills for suggestions if no matches found
        all_bills = db.execute('''
            SELECT b.reference_number, s.name as service_name, b.amount, 
                   (b.amount - COALESCE(b.insurance_coverage, 0)) as patient_portion, 
                   b.status, b.due_date
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            WHERE b.patient_id = ?
            ORDER BY b.created_at DESC
        ''', (patient_internal_id,)).fetchall()
        
        suggestion_text = f"No bills found matching {criteria_text}. "
        if all_bills:
            suggestion_text += f"Your available bills are:\n"
            for bill in all_bills[:5]:  # Show up to 5 bills
                due_date_display = bill['due_date'] or "N/A"
                patient_portion = float(bill['patient_portion'])
                suggestion_text += f"- {bill['service_name']}: ${patient_portion:.2f} ({bill['status']}, due {due_date_display}) - Ref: {bill['reference_number']}\n"
            if len(all_bills) > 5:
                suggestion_text += f"... and {len(all_bills) - 5} more bills\n"
        else:
            suggestion_text += "You have no bills on your account."
        
        return suggestion_text, {'bills': [], 'patient_id': patient_id, 'search_criteria': {
            'reference_number': reference_number,
            'service_name': service_name,
            'status': status,
            'date': date,
            'due_date': due_date,
            'amount': amount,
            'amount_min': amount_min,
            'amount_max': amount_max
        }}
    
    # If multiple bills found, show summary
    if len(bills) > 1:
        bills_summary = f"Found {len(bills)} bills matching your search criteria:\n"
        total_amount = 0
        pending_amount = 0
        
        for i, bill in enumerate(bills[:10], 1):  # Show first 10 matches
            # Format dates
            created_date = "N/A"
            due_date_display = "N/A"
            
            if bill['created_at']:
                try:
                    created_date = datetime.strptime(bill['created_at'], '%Y-%m-%d').strftime('%m/%d/%Y')
                except:
                    created_date = bill['created_at']
            
            if bill['due_date']:
                try:
                    due_date_display = datetime.strptime(bill['due_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
                except:
                    due_date_display = bill['due_date']
            
            amount = float(bill['patient_portion'])
            total_amount += amount
            if bill['display_status'] != 'Paid':
                pending_amount += amount
            
            bills_summary += f"\n{i}. Bill #{bill['id']} - {bill['service_name']}\n"
            bills_summary += f"   Date: {created_date} | Due: {due_date_display}"
            bills_summary += f"\n   Amount: ${amount:.2f} | Status: {bill['display_status']}"
            bills_summary += f"\n   Reference: {bill['reference_number']}"
            if bill['dentist_name']:
                bills_summary += f"\n   Provider: {bill['dentist_name']}"
            
            if i < len(bills) and i < 10:
                bills_summary += "\n"
        
        if len(bills) > 10:
            bills_summary += f"\n\n... and {len(bills) - 10} more bills"
        
        bills_summary += f"\n\nSummary: Total Amount: ${total_amount:.2f}"
        if pending_amount > 0:
            bills_summary += f" | Pending: ${pending_amount:.2f}"
        
        print(f"[SWAIG][CONSOLE] Multiple bills found matching criteria, patient {patient_id}")
        logging.info(f"[SWAIG] Multiple bills found matching criteria, patient {patient_id}")
        
        return bills_summary, {
            'bills': [dict(b) for b in bills],
            'patient_id': patient_id,
            'total_amount': total_amount,
            'pending_amount': pending_amount,
            'match_count': len(bills),
            'search_criteria': {
                'reference_number': reference_number,
                'service_name': service_name,
                'status': status,
                'date': date,
                'due_date': due_date,
                'amount': amount,
                'amount_min': amount_min,
                'amount_max': amount_max
            }
        }
    
    # Single bill found - return detailed information (same as before)
    bill = bills[0]
    bill_dict = dict(bill)
    
    # Format dates for display
    due_date_str = "Not specified"
    created_date_str = "Not specified"
    
    if bill['due_date']:
        try:
            due_date_obj = datetime.strptime(bill['due_date'], '%Y-%m-%d')
            due_date_str = due_date_obj.strftime('%A, %B %d, %Y')
        except:
            due_date_str = bill['due_date']
    
    if bill['created_at']:
        try:
            created_date_obj = datetime.strptime(bill['created_at'], '%Y-%m-%d')
            created_date_str = created_date_obj.strftime('%A, %B %d, %Y')
        except:
            created_date_str = bill['created_at']
    
    # Get payment history for this bill
    payments = db.execute('''
        SELECT payment_date, amount, payment_method_type
        FROM payments
        WHERE billing_id = ?
        ORDER BY payment_date DESC
    ''', (bill['id'],)).fetchall()
    
    total_paid = sum(float(p['amount']) for p in payments)
    remaining_balance = max(0, float(bill['patient_portion']))
    
    # Create detailed response
    details = f"Bill Verified - Reference #{bill['reference_number']}:\n"
    details += f"Bill #: {bill['bill_number'] if 'bill_number' in bill else bill['id']}\n"
    details += f"Service: {bill['service_name']}"
    if bill['service_description']:
        details += f" - {bill['service_description']}"
    details += f"\nTotal Amount: ${float(bill['amount']):.2f}"
    details += f"\nPatient Portion: ${float(bill['patient_portion']):.2f}"
    details += f"\nRemaining Balance: ${remaining_balance:.2f}"
    details += f"\nStatus: {bill['display_status']}"
    details += f"\nDue Date: {due_date_str}"
    details += f"\nBill Date: {created_date_str}"
    
    if bill['dentist_name']:
        details += f"\nProvider: {bill['dentist_name']}"
    
    if payments:
        details += f"\nPayments Made: {len(payments)} payment(s), Total: ${total_paid:.2f}"
    else:
        details += f"\nPayments Made: No payments yet"
    
    print(f"[SWAIG][CONSOLE] Bill verified by search criteria -> Bill {bill['id']} for patient {patient_id}")
    logging.info(f"[SWAIG] Bill verified by search criteria -> Bill {bill['id']} for patient {patient_id}")
    
    return details, {
        'bill': bill_dict,
        'patient_id': patient_id,
        'reference_number': bill['reference_number'],
        'bill_id': bill['id'],
        'verified': True,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
        'payments': [dict(p) for p in payments],
        'search_criteria': {
            'reference_number': reference_number,
            'service_name': service_name,
            'status': status,
            'date': date,
            'due_date': due_date,
            'amount': amount,
            'amount_min': amount_min,
            'amount_max': amount_max
        }
    }

@app.route('/api/send-bill-sms', methods=['POST'])
@login_required
def send_bill_sms():
    """Send bill summary via SMS instead of PDF (PDFs are too large for SMS)"""
    data = request.get_json()
    bill_id = data.get('bill_id')
    
    if not bill_id:
        return jsonify({'error': 'Bill ID is required'}), 400
    
    db = get_db()
    
    # Get bill details and patient phone
    if session['user_type'] == 'patient':
        bill = db.execute('''
            SELECT b.*, s.name as service_name, p.phone,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.patient_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    else:
        bill = db.execute('''
            SELECT b.*, s.name as service_name, p.phone,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            JOIN patients p ON b.patient_id = p.id
            WHERE b.id = ? AND b.dentist_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    if not bill['phone']:
        return jsonify({'error': 'No phone number found for patient'}), 400
    
    # Format phone number to E.164 format
    patient_phone = format_to_e164(bill['phone'])
    if not patient_phone:
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    # Calculate amounts
    total_amount = float(bill['amount']) if bill['amount'] else 0
    patient_portion = float(bill['patient_portion']) if bill['patient_portion'] else 0
    amount_paid = float(bill['amount_paid']) if bill['amount_paid'] else 0
    remaining_balance = patient_portion - amount_paid
    
    # Create concise SMS message (SMS has 160 char limit, so keep it brief)
    sms_message = f"""🏥 DENTAL OFFICE BILL #{bill['bill_number']}
📋 Service: {bill['service_name']}
💰 Amount Due: ${bill['patient_portion']:.2f}
📅 Due Date: {bill['due_date'][:10] if bill['due_date'] else 'N/A'}
🏥 Reference: {bill['reference_number'] or 'N/A'}

💳 Pay online at {PROJECT_URL} or call {SIGNALWIRE_PHONE_NUMBER}
Thank you for choosing our dental practice!"""
    
    try:
        # Use existing SMS infrastructure
        import requests
        
        # Use SignalWire SMS API
        response = requests.post(
            f"{SIGNALWIRE_SPACE}/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages",
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_AUTH_TOKEN),
            data={
                'From': SIGNALWIRE_PHONE_NUMBER,
                'To': patient_phone,
                'Body': sms_message
            }
        )
        
        if response.status_code == 201:
            return jsonify({
                'success': True, 
                'message': f'Bill summary sent to {patient_phone}',
                'sms_length': len(sms_message)
            })
        else:
            app.logger.error(f"SMS sending failed: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to send SMS'}), 500
            
    except Exception as e:
        app.logger.error(f"Error sending bill SMS: {str(e)}")
        return jsonify({'error': f'SMS sending failed: {str(e)}'}), 500

@app.route('/api/send-bill-mms', methods=['POST'])
@login_required
def send_bill_mms():
    """Generate bill as JPG image and send via MMS (much smaller than PDF)"""
    data = request.get_json()
    bill_id = data.get('bill_id')
    
    if not bill_id:
        return jsonify({'error': 'Bill ID is required'}), 400
    
    db = get_db()
    
    # Get bill details and patient phone
    if session['user_type'] == 'patient':
        bill = db.execute('''
            SELECT b.*, s.name as service_name, p.phone,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   t.diagnosis, t.treatment_notes, t.treatment_date,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
        FROM billing b
        JOIN dental_services s ON b.service_id = s.id
            JOIN patients p ON b.patient_id = p.id
        LEFT JOIN dentists d ON b.dentist_id = d.id
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            WHERE b.id = ? AND b.patient_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    else:
        bill = db.execute('''
            SELECT b.*, s.name as service_name, p.phone,
                   p.first_name as patient_first_name, p.last_name as patient_last_name,
                   d.first_name as dentist_first_name, d.last_name as dentist_last_name,
                   t.diagnosis, t.treatment_notes, t.treatment_date,
                   COALESCE(
                       (SELECT SUM(amount) FROM payments WHERE billing_id = b.id), 
                       0
                   ) as amount_paid
            FROM billing b
            JOIN dental_services s ON b.service_id = s.id
            JOIN patients p ON b.patient_id = p.id
            LEFT JOIN dentists d ON b.dentist_id = d.id
            LEFT JOIN treatment_history t ON b.reference_number = t.reference_number
            WHERE b.id = ? AND b.dentist_id = ?
        ''', (bill_id, session['user_id'])).fetchone()
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    if not bill['phone']:
        return jsonify({'error': 'No phone number found for patient'}), 400
    
    # Format phone number to E.164 format
    patient_phone = format_to_e164(bill['phone'])
    if not patient_phone:
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    try:
        # Generate JPG image of the bill
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        import base64
        import tempfile
        import os
        
        # Create image (portrait orientation, good for mobile viewing)
        img_width = 600
        img_height = 800
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use better fonts, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 24)
            header_font = ImageFont.truetype("arial.ttf", 18)
            normal_font = ImageFont.truetype("arial.ttf", 14)
            small_font = ImageFont.truetype("arial.ttf", 12)
        except:
            # Fallback to default font
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Calculate amounts
        total_amount = float(bill['amount']) if bill['amount'] else 0
        patient_portion = float(bill['patient_portion']) if bill['patient_portion'] else 0
        insurance_portion = total_amount - patient_portion
        amount_paid = float(bill['amount_paid']) if bill['amount_paid'] else 0
        remaining_balance = patient_portion - amount_paid
        
        # Drawing helper function
        y_pos = 20
        def draw_text(text, font, color='black', y_offset=0):
            nonlocal y_pos
            y_pos += y_offset
            draw.text((20, y_pos), text, fill=color, font=font)
            y_pos += 25
            return y_pos
        
        def draw_section_header(text):
            nonlocal y_pos
            y_pos += 10
            draw.rectangle([(10, y_pos), (img_width-10, y_pos+30)], fill='#f3f4f6')
            draw.text((20, y_pos+5), text, fill='#2563eb', font=header_font)
            y_pos += 40
        
        # Title with Bill Number prominently displayed
        draw_text(f"DENTAL OFFICE BILL #{bill['bill_number']}", title_font, '#2563eb', 10)
        y_pos += 10
        
        # Bill Information
        draw_section_header("Bill Information")
        draw_text(f"Reference: {bill['reference_number'] or 'N/A'}", normal_font)
        draw_text(f"Date: {bill['created_at'][:10] if bill['created_at'] else 'N/A'}", normal_font)
        draw_text(f"Due Date: {bill['due_date'][:10] if bill['due_date'] else 'N/A'}", normal_font)
        draw_text(f"Status: {bill['status'].upper() if bill['status'] else 'N/A'}", normal_font)
        
        # Patient Information
        draw_section_header("Patient Information")
        draw_text(f"Name: {bill['patient_first_name']} {bill['patient_last_name']}", normal_font)
        draw_text(f"Phone: {bill['phone'] or 'N/A'}", normal_font)
        
        # Service Details
        draw_section_header("Service Details")
        draw_text(f"Service: {bill['service_name'] or 'N/A'}", normal_font)
        draw_text(f"Treatment Date: {bill['treatment_date'][:10] if bill['treatment_date'] else 'N/A'}", normal_font)
        if bill['dentist_first_name']:
            draw_text(f"Dentist: {bill['dentist_first_name']} {bill['dentist_last_name']}", normal_font)
        
        # Amount Breakdown
        draw_section_header("Amount Breakdown")
        draw_text(f"Total Amount: ${total_amount:.2f}", normal_font)
        draw_text(f"Insurance Portion: ${insurance_portion:.2f}", normal_font)
        draw_text(f"Patient Portion: ${patient_portion:.2f}", normal_font, '#2563eb')
        draw_text(f"Amount Paid: ${amount_paid:.2f}", normal_font)
        
        # Remaining Balance (highlighted)
        balance_color = '#059669' if remaining_balance <= 0 else '#dc2626'
        draw_text(f"Remaining Balance: ${remaining_balance:.2f}", normal_font, balance_color)
        
        # Footer
        y_pos = img_height - 60
        draw_text("Questions? Call our office", small_font, '#6b7280')
        draw_text("Thank you for choosing our dental practice!", small_font, '#6b7280')
        
        # Save image to static directory for public access
        import uuid
        image_filename = f"{uuid.uuid4()}.jpg"
        static_path = os.path.join('static', 'temp')
        
        # Create temp directory if it doesn't exist
        os.makedirs(static_path, exist_ok=True)
        
        image_path = os.path.join(static_path, image_filename)
        
        # Save optimized image
        img.save(image_path, 'JPEG', quality=85, optimize=True)
        file_size = os.path.getsize(image_path)
        
        # If file is too large, reduce quality
        if file_size > 300000:  # 300KB limit
            img.save(image_path, 'JPEG', quality=60, optimize=True)
            file_size = os.path.getsize(image_path)
        
        # If still too large, reduce image dimensions
        if file_size > 300000:
            img_resized = img.resize((400, 533), Image.Resampling.LANCZOS)
            img_resized.save(image_path, 'JPEG', quality=70, optimize=True)
            file_size = os.path.getsize(image_path)
        
        # Create public URL for the image
        # Uses PROJECT_URL environment variable for deployment flexibility
        public_image_url = f"{PROJECT_URL}/static/temp/{image_filename}"
        
        # Send MMS via SignalWire
        import requests
        import threading
        import time
        
        response = requests.post(
            f"{SIGNALWIRE_SPACE}/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages",
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_AUTH_TOKEN),
            data={
                'From': SIGNALWIRE_PHONE_NUMBER,
                'To': patient_phone,
                'Body': f'Your dental bill #{bill['bill_number']} is attached.',
                'MediaUrl': public_image_url
            }
        )
        
        # Schedule cleanup after delay to allow SignalWire to fetch the image
        def delayed_cleanup():
            time.sleep(30)  # Wait 30 seconds for SignalWire to fetch the image
            try:
                if os.path.exists(image_path):
                    os.unlink(image_path)
                    app.logger.info(f"Cleaned up image file: {image_path}")
            except Exception as cleanup_error:
                app.logger.warning(f"Failed to cleanup image file {image_path}: {cleanup_error}")
        
        # Start cleanup in background thread
        cleanup_thread = threading.Thread(target=delayed_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        if response.status_code == 201:
            return jsonify({
                'success': True, 
                'message': f'Bill image sent to {patient_phone}',
                'image_size': f'{file_size//1024}KB'
            })
        else:
            app.logger.error(f"MMS sending failed: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to send MMS'}), 500
            
    except Exception as e:
        app.logger.error(f"Error sending bill MMS: {str(e)}")
        return jsonify({'error': f'MMS sending failed: {str(e)}'}), 500

@app.route('/api/patients/by-patient-id/<patient_id>', methods=['GET', 'PUT'])
@login_required
def api_patient_by_patient_id(patient_id):
    if request.method == 'GET':
        db = get_db()
        patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'message': 'Patient not found'}), 404
        return jsonify(dict(patient))
    
    elif request.method == 'PUT':
        if session['user_type'] != 'dentist':
            return jsonify({'success': False, 'message': 'Unauthorized - Dentist access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        db = get_db()
        
        # Check if patient exists
        patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        try:
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 
                            'date_of_birth', 'medical_history', 'insurance_info']
            
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    params.append(data[field])
            
            if not update_fields:
                return jsonify({'success': False, 'message': 'No valid fields to update'}), 400
            
            # Add patient identifier to params for WHERE clause
            params.append(str(patient_id))
            query = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
            
            db.execute(query, params)
            db.commit()
            
            # Return updated patient data
            updated_patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (str(patient_id),)).fetchone()
            
            return jsonify({'success': True, 'message': 'Patient updated successfully', 'patient': dict(updated_patient)})
            
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/patients/<int:patient_id>/password', methods=['PUT'])
@login_required
def api_change_patient_password(patient_id):
    if session['user_type'] != 'dentist':
        return jsonify({'success': False, 'message': 'Unauthorized - Dentist access required'}), 403
    
    data = request.get_json()
    if not data or 'new_password' not in data:
        return jsonify({'success': False, 'message': 'New password is required'}), 400
    
    new_password = data['new_password']
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
    
    db = get_db()
    
    try:
        # First try to find by database ID
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        use_db_id = True
        
        # If not found, try to find by patient_id field (7-digit ID)
        if not patient:
            patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (str(patient_id),)).fetchone()
            use_db_id = False
            
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        # Hash the new password
        password_hash, salt = hash_password(new_password)
        
        # Update password in database
        if use_db_id:
            db.execute('UPDATE patients SET password_hash = ?, password_salt = ? WHERE id = ?', 
                      (password_hash, salt, patient_id))
        else:
            db.execute('UPDATE patients SET password_hash = ?, password_salt = ? WHERE patient_id = ?', 
                      (password_hash, salt, str(patient_id)))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Failed to change password: {str(e)}'}), 500

def cleanup_old_temp_files():
    """Clean up temp files older than 1 hour"""
    try:
        temp_dir = os.path.join('static', 'temp')
        if not os.path.exists(temp_dir):
            return
        
        current_time = time.time()
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > 3600:  # 1 hour in seconds
                    try:
                        os.unlink(file_path)
                        app.logger.info(f"Cleaned up old temp file: {file_path}")
                    except Exception as e:
                        app.logger.warning(f"Failed to cleanup old temp file {file_path}: {e}")
    except Exception as e:
        app.logger.warning(f"Error during temp file cleanup: {e}")

def schedule_cleanup_job():
    """Schedule periodic cleanup of temp files"""
    def cleanup_worker():
        while True:
            time.sleep(1800)  # Run every 30 minutes
            cleanup_old_temp_files()
    
    cleanup_thread = threading.Thread(target=cleanup_worker)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    app.logger.info("Scheduled temp file cleanup job")

@swaig.endpoint(
    "Get Available Services and Dentists",
    challenge_token=SWAIGArgument(
        type="string",
        description="Challenge token",
        required=True
    )
)
def swaig_get_services_and_dentists(challenge_token=None, meta_data_token=None, **kwargs):
    print(f"[SWAIG][CONSOLE] swaig_get_services_and_dentists called")
    logging.info(f"[SWAIG] swaig_get_services_and_dentists called")
    
    # Check if user is authenticated via challenge token
    if not is_challenge_token_valid(challenge_token):
        print("[SWAIG][CONSOLE] Invalid or missing challenge token")
        logging.warning("[SWAIG] Invalid or missing challenge token")
        return "Please verify your identity first by providing the 6-digit code sent to your phone.", {}
    
    db = get_db()
    
    try:
        # Get all dentists
        dentists = db.execute('SELECT id, first_name, last_name FROM dentists ORDER BY id').fetchall()
        
        # Get all services
        services = db.execute('SELECT id, name, type FROM dental_services ORDER BY id').fetchall()
        
        # Build response
        response = "Available dental services and dentists:\n\n"
        
        # List services
        response += "**Available Services:**\n"
        for service in services:
            response += f"- {service['name']} (Service ID: {service['id']}, Type: {service['type']})\n"
        
        response += "\n**Available Dentists:**\n"
        for dentist in dentists:
            response += f"- Dr. {dentist['first_name']} {dentist['last_name']} (Dentist ID: {dentist['id']})\n"
        
        response += "\n**Common Service Recommendations:**\n"
        response += "- Regular Cleaning (ID: 1) → Dr. John Smith (ID: 1)\n"
        response += "- Teeth Whitening (ID: 5) → Dr. Sarah Johnson (ID: 2)\n"
        response += "- Braces Consultation (ID: 11) → Dr. Michael Chen (ID: 3)\n"
        response += "- Emergency Visit (ID: 12) → Any available dentist\n"
        
        response += "\nTo schedule an appointment, provide the Service ID and Dentist ID."
        
        print(f"[SWAIG][CONSOLE] Successfully retrieved services and dentists")
        logging.info(f"[SWAIG] Successfully retrieved services and dentists")
        
        return response, {
            'services': [dict(s) for s in services],
            'dentists': [dict(d) for d in dentists]
        }
        
    except Exception as e:
        print(f"[SWAIG][CONSOLE] Error retrieving services and dentists: {e}")
        logging.error(f"[SWAIG] Error retrieving services and dentists: {e}")
        return f"Error retrieving services and dentists: {str(e)}", {}

if __name__ == '__main__':
    setup_logging()
    init_db_if_needed()
    schedule_cleanup_job()
    print("=== Default Login Credentials ===")
    print("Patient: jane.doe@test.tld / patient123")
    print("Dentist: dr.smith@test.tld / dentist123")
    print("=" * 30)
    app.run(host='0.0.0.0', port=8080, debug=True)
