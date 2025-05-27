from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, Response, g
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import hashlib
import secrets
from functools import wraps
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
from signalwire_swaig.swaig import SWAIG, SWAIGArgument, SWAIGFunctionProperties
from signalwire.rest import Client as SignalWireClient
import schedule
from signalwire.voice_response import VoiceResponse
import sys
from mfa_util import SignalWireMFA, is_valid_uuid, validate_phone
import requests
import random

# Global SignalWire configuration variables
SIGNALWIRE_PROJECT_ID = None
SIGNALWIRE_TOKEN = None
SIGNALWIRE_SPACE = None
HTTP_USERNAME = None
HTTP_PASSWORD = None
FROM_NUMBER = None
signalwire_client = None
swaig = None

# Global variables for MFA
LAST_MFA_ID = None
VERIFIED_CUSTOMER_DATA = {}

# Initialize MFA utility
mfa_util = None

# Add a global flag to track SWAIG endpoint registration
SWAIG_ENDPOINTS_REGISTERED = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Add CSRF enable/disable logic
ENABLE_CSRF = os.getenv('ENABLE_CSRF', 'false').lower() == 'true'
if ENABLE_CSRF:
    from flask_wtf import CSRFProtect
    csrf = CSRFProtect(app)
else:
    # Add a dummy csrf_token function when CSRF is disabled
    @app.context_processor
    def inject_csrf_token():
        def dummy_csrf_token():
            return ""
        return dict(csrf_token=dummy_csrf_token)

def setup_logging():
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/zen_cable.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Zen Cable startup')

def initialize_signalwire():
    global signalwire_client, swaig, SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN, SIGNALWIRE_SPACE, HTTP_USERNAME, HTTP_PASSWORD, FROM_NUMBER, mfa_util
    if os.path.exists('.env'):
        load_dotenv()
        SIGNALWIRE_PROJECT_ID = os.getenv('SIGNALWIRE_PROJECT_ID')
        SIGNALWIRE_TOKEN = os.getenv('SIGNALWIRE_TOKEN')
        SIGNALWIRE_SPACE = os.getenv('SIGNALWIRE_SPACE')
        HTTP_USERNAME = os.getenv('HTTP_USERNAME')
        HTTP_PASSWORD = os.getenv('HTTP_PASSWORD')
        FROM_NUMBER = os.getenv('FROM_NUMBER')
        if all([SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN, SIGNALWIRE_SPACE, HTTP_USERNAME, HTTP_PASSWORD, FROM_NUMBER]):
            try:
                signalwire_client = SignalWireClient(
                    SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN, signalwire_space_url=SIGNALWIRE_SPACE
                )
                swaig = SWAIG(app, auth=(HTTP_USERNAME, HTTP_PASSWORD))
                mfa_util = SignalWireMFA(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN, SIGNALWIRE_SPACE, FROM_NUMBER)
                app.logger.info("SignalWire client, SWAIG, and MFA utility initialized successfully")
                # Register SWAIG endpoints immediately after initialization
                register_swaig_endpoints()
            except Exception as e:
                app.logger.error(f"Failed to initialize SignalWire: {str(e)}")
                signalwire_client = None
                swaig = None
                mfa_util = None
        else:
            app.logger.warning("Missing environment variables; SignalWire not initialized")
    else:
        app.logger.info("No .env file found; SignalWire not initialized")

def register_swaig_endpoints():
    global swaig, SWAIG_ENDPOINTS_REGISTERED
    if not swaig:
        app.logger.error("Cannot register SWAIG endpoints: SWAIG not initialized")
        return
    if SWAIG_ENDPOINTS_REGISTERED:
        app.logger.info("SWAIG endpoints already registered; skipping.")
        return
    SWAIG_ENDPOINTS_REGISTERED = True

    @swaig.endpoint(
        "Check the current balance and due date for the customer's account",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Checking your balance...",
                    "One moment please...",
                    "Retrieving billing information..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def check_balance(customer_id, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if not customer:
                return "I couldn't find your account. Please verify your account number.", []
            billing = db.execute('''
                SELECT * FROM billing 
                WHERE customer_id = ? 
                ORDER BY due_date DESC LIMIT 1
            ''', (customer_id,)).fetchone()
            db.close()
            if billing:
                return f"Your current balance is ${billing['amount']:.2f}, due on {billing['due_date']}.", []
            return "No billing information found for your account.", []
        except Exception as e:
            app.logger.error(f"Error in check_balance: {str(e)}")
            return "Error checking balance. Please try again later.", []

    @swaig.endpoint(
        "Make a payment on the customer's account",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Processing your payment...",
                    "One moment while I handle your payment...",
                    "Submitting payment..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        amount=SWAIGArgument(type="number", description="The amount to pay", required=True),
        payment_method=SWAIGArgument(type="string", description="Payment method", enum=["credit_card", "bank_transfer", "cash"], required=False),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def make_payment(customer_id, amount, payment_method=None, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if not customer:
                return "I couldn't find your account. Please verify your account number.", []
            if not amount or amount <= 0:
                return "Please provide a valid payment amount.", []
            # Insert payment record
            db.execute('''
                INSERT INTO payments (customer_id, amount, payment_date, payment_method, status, transaction_id)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'pending', ?)
            ''', (customer_id, amount, payment_method or 'phone', secrets.token_hex(16)))
            # Update balance
            current_balance = db.execute('SELECT amount FROM billing WHERE customer_id = ? ORDER BY due_date DESC LIMIT 1', (customer_id,)).fetchone()
            if current_balance:
                new_balance = current_balance['amount'] - amount
                db.execute('UPDATE billing SET amount = ? WHERE id = (SELECT id FROM billing WHERE customer_id = ? ORDER BY due_date DESC LIMIT 1)', 
                           (new_balance, customer_id))
            db.commit()
            db.close()
            return f"Payment of ${amount:.2f} initiated. Confirmation text incoming.", []
        except Exception as e:
            app.logger.error(f"Error in make_payment: {str(e)}")
            return "Error processing payment. Please try again.", []

    @swaig.endpoint(
        "Check the current status of the customer's modem",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Checking modem status...",
                    "Retrieving modem information...",
                    "Please wait..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def check_modem_status(customer_id, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if not customer:
                return "I couldn't find your account. Please verify your account number.", []
            modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (customer_id,)).fetchone()
            db.close()
            if modem:
                return f"Your modem is {modem['status']}. MAC: {modem['mac_address']}.", []
            return "No modem information found for your account.", []
        except Exception as e:
            app.logger.error(f"Error in check_modem_status: {str(e)}")
            return "Error checking modem status.", []

    @swaig.endpoint(
        "Reboot the customer's modem",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Rebooting your modem...",
                    "Initiating modem restart...",
                    "Please wait while I reboot..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def reboot_modem(customer_id, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if not customer:
                return "I couldn't find your account. Please verify your account number.", []

            modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (customer_id,)).fetchone()
            if not modem:
                return "No modem information found for your account.", []

            # Update modem status to rebooting
            db.execute('UPDATE modems SET status = "rebooting", last_seen = CURRENT_TIMESTAMP WHERE customer_id = ?', 
                      (customer_id,))
            db.commit()

            # Start the reboot simulation in a background thread
            thread = threading.Thread(target=simulate_modem_reboot, args=(customer_id,))
            thread.daemon = True
            thread.start()

            db.close()
            return "Modem reboot initiated. This will take about 30 seconds.", []
        except Exception as e:
            app.logger.error(f"Error in reboot_modem: {str(e)}")
            return "Error rebooting modem.", []

    @swaig.endpoint(
        "Schedule a service appointment",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Scheduling your appointment...",
                    "Arranging your service...",
                    "Please wait while I book it..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        type=SWAIGArgument(type="string", description="Type of appointment", enum=["installation", "repair", "upgrade", "modem_swap"], required=True),
        date=SWAIGArgument(type="string", description="Preferred date (YYYY-MM-DD)", required=True),
        time_slot=SWAIGArgument(type="string", description="Preferred time slot", enum=["morning", "afternoon", "evening", "all_day"], required=True),
        notes=SWAIGArgument(type="string", description="Notes for the appointment", required=False),
        make=SWAIGArgument(type="string", description="The make of the new modem (required for modem_swap)", required=False),
        model=SWAIGArgument(type="string", description="The model of the new modem (required for modem_swap)", required=False),
        mac_address=SWAIGArgument(type="string", description="The MAC address of the new modem (required for modem_swap)", required=False),
        sms_reminder=SWAIGArgument(type="boolean", description="Whether to send SMS reminders", required=False),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def schedule_appointment(customer_id, type, date, time_slot, notes=None, make=None, model=None, mac_address=None, sms_reminder=True, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            # Validate appointment type
            if type not in ['installation', 'repair', 'upgrade', 'modem_swap']:
                return "Invalid appointment type.", []
            # Validate time slot
            if time_slot not in ['morning', 'afternoon', 'evening', 'all_day']:
                return "Invalid time slot.", []
            # Parse date
            try:
                appointment_date = datetime.strptime(date, '%Y-%m-%d')
                if appointment_date < datetime.now():
                    return "Please select a future date.", []
            except ValueError:
                return "Invalid date format.", []
            # Check for existing appointments
            existing = db.execute('''
                SELECT * FROM appointments 
                WHERE customer_id = ? 
                AND date(start_time) = date(?)
            ''', (customer_id, appointment_date)).fetchone()
            if existing:
                return f"You already have an appointment on {date}. Would you like to reschedule it?", []
            # Set time slots
            time_slots = {
                'morning': ('08:00 AM', '11:00 AM'),
                'afternoon': ('02:00 PM', '04:00 PM'),
                'evening': ('06:00 PM', '08:00 PM'),
                'all_day': ('08:00 AM', '08:00 PM')
            }
            start_time, end_time = time_slots[time_slot]
            # Check if time slot is available
            slot_conflict = db.execute('''
                SELECT * FROM appointments 
                WHERE date(start_time) = date(?)
                AND (
                    (start_time <= ? AND end_time > ?) OR
                    (start_time < ? AND end_time >= ?) OR
                    (start_time >= ? AND end_time <= ?)
                )
            ''', (appointment_date, 
                  f"{date} {end_time}", f"{date} {start_time}",
                  f"{date} {end_time}", f"{date} {start_time}",
                  f"{date} {start_time}", f"{date} {end_time}")).fetchone()
            if slot_conflict:
                return f"The {time_slot} time slot on {date} is already booked. Please choose another time.", []
            # Generate job number
            job_number = generate_job_number()
            # Prepare appointment notes
            appointment_notes = notes or ""
            if type == "modem_swap":
                if not all([make, model, mac_address]):
                    return "For modem swap appointments, please provide the make, model, and MAC address of the new modem.", []
                formatted_mac = format_mac_address(mac_address)
                if not formatted_mac:
                    return "Invalid MAC address format. Please provide a valid MAC address.", []
                appointment_notes = f"New Modem Details - Make: {make}, Model: {model}, MAC: {formatted_mac}\n{appointment_notes}"
            # Insert appointment
            cursor = db.execute('''
                INSERT INTO appointments (customer_id, type, status, start_time, end_time, notes, sms_reminder, job_number)
                VALUES (?, ?, 'scheduled', ?, ?, ?, ?, ?)
            ''', (customer_id, type, 
                  f"{date} {start_time}", 
                  f"{date} {end_time}",
                  appointment_notes,
                  sms_reminder,
                  job_number))
            appointment_id = cursor.lastrowid
            # Get the created appointment
            appointment = db.execute('''
                SELECT a.*, t.name as technician_name
                FROM appointments a
                LEFT JOIN technicians t ON a.technician_id = t.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()
            # Schedule reminders if enabled
            if sms_reminder:
                schedule_reminders(dict(appointment))
            db.commit()
            # Send SMS notification about new appointment
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if customer:
                try:
                    compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                    appointment_time = appointment['start_time']
                    message = f"Your {appointment['type']} appointment (Job #{appointment['job_number']}) is scheduled for {appointment_time}. Call 1-800-ZEN-CABLE to reschedule."
                    payload = {
                        "From": FROM_NUMBER,
                        "To": customer['phone'],
                        "Body": message
                    }
                    response = requests.post(
                        compat_url,
                        data=payload,
                        auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    response.raise_for_status()
                except Exception as e:
                    app.logger.error(f"Error sending appointment SMS: {str(e)}")
            formatted_time = f"{date} {start_time[:5]} - {end_time[:5]}"
            response = f"Your {type} appointment has been scheduled for {formatted_time}. Your job number is {job_number}. "
            if sms_reminder:
                response += "You will receive a reminder 24 hours before your appointment. "
            response += "Call 1-800-ZEN-CABLE to reschedule."
            return response, []
        except Exception as e:
            app.logger.error(f"SWAIG error in schedule_appointment: {str(e)}")
            return "Error scheduling appointment.", []
        finally:
            db.close()

    @swaig.endpoint(
        "Reschedule an existing appointment",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Rescheduling your appointment...",
                    "Checking availability...",
                    "Updating your appointment..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        job_number=SWAIGArgument(type="string", description="The job number for the appointment to reschedule", required=False),
        appointment_id=SWAIGArgument(type="integer", description="The appointment ID to reschedule (optional, use job number if possible)", required=False),
        date=SWAIGArgument(type="string", description="New date (YYYY-MM-DD)", required=True),
        time_slot=SWAIGArgument(type="string", description="New time slot", enum=["morning", "afternoon", "evening", "all_day"], required=True),
        notes=SWAIGArgument(type="string", description="Notes for the appointment", required=False),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def reschedule_appointment(customer_id, date, time_slot, notes=None, job_number=None, appointment_id=None, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            # Look up appointment by job_number if provided
            if job_number:
                appt = db.execute('SELECT * FROM appointments WHERE customer_id = ? AND job_number = ?', (customer_id, job_number)).fetchone()
                if not appt:
                    db.close()
                    return f"No appointment found with job number {job_number}.", []
                appointment_id = appt['id']
            elif appointment_id:
                appt = db.execute('SELECT * FROM appointments WHERE id = ? AND customer_id = ?', (appointment_id, customer_id)).fetchone()
                if not appt:
                    db.close()
                    return "Appointment not found.", []
            else:
                db.close()
                return "Please provide the job number for the appointment you want to reschedule.", []
            # Validate time slot
            if time_slot not in ['morning', 'afternoon', 'evening', 'all_day']:
                db.close()
                return "Invalid time slot.", []
            # Parse date
            try:
                appointment_date = datetime.strptime(date, '%Y-%m-%d')
                if appointment_date < datetime.now():
                    db.close()
                    return "Please select a future date.", []
            except ValueError:
                db.close()
                return "Invalid date format.", []
            # Set time slots
            time_slots = {
                'morning': ('08:00 AM', '11:00 AM'),
                'afternoon': ('02:00 PM', '04:00 PM'),
                'evening': ('06:00 PM', '08:00 PM'),
                'all_day': ('08:00 AM', '08:00 PM')
            }
            start_time, end_time = time_slots[time_slot]
            # Check for slot conflict
            slot_conflict = db.execute('''
                SELECT * FROM appointments 
                WHERE customer_id = ? AND id != ? AND date(start_time) = date(?)
                AND (
                    (start_time <= ? AND end_time > ?) OR
                    (start_time < ? AND end_time >= ?) OR
                    (start_time >= ? AND end_time <= ?)
                )
            ''', (customer_id, appointment_id, appointment_date,
                  f"{date} {end_time}", f"{date} {start_time}",
                  f"{date} {end_time}", f"{date} {start_time}",
                  f"{date} {start_time}", f"{date} {end_time}")).fetchone()
            if slot_conflict:
                db.close()
                return f"The {time_slot} time slot is already booked.", []
            # Update appointment
            db.execute('''
                UPDATE appointments 
                SET start_time = ?, end_time = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                f"{date} {start_time}",
                f"{date} {end_time}",
                notes or appt['notes'],
                appointment_id
            ))
            # Log the reschedule
            db.execute('''
                INSERT INTO appointment_history (appointment_id, action, details, created_at)
                VALUES (?, 'rescheduled', ?, CURRENT_TIMESTAMP)
            ''', (appointment_id, json.dumps({
                'date': date,
                'time_slot': time_slot,
                'notes': notes or appt['notes'],
                'job_number': appt['job_number']
            })))
            db.commit()
            # Get updated appointment
            updated_appointment = db.execute('''
                SELECT a.*, t.name as technician_name
                FROM appointments a
                LEFT JOIN technicians t ON a.technician_id = t.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()
            # Send SMS notification about reschedule
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if customer:
                try:
                    compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                    appointment_time = updated_appointment['start_time']
                    message = f"Your {updated_appointment['type']} appointment (Job #{updated_appointment['job_number']}) has been rescheduled to {appointment_time}. Call 1-800-ZEN-CABLE to reschedule."
                    payload = {
                        "From": FROM_NUMBER,
                        "To": customer['phone'],
                        "Body": message
                    }
                    response = requests.post(
                        compat_url,
                        data=payload,
                        auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    response.raise_for_status()
                except Exception as e:
                    app.logger.error(f"Error sending reschedule appointment SMS: {str(e)}")
            db.close()
            return f"Your appointment has been rescheduled to {date} {start_time} - {end_time}.", []
        except Exception as e:
            app.logger.error(f"SWAIG error in reschedule_appointment: {str(e)}")
            return "Error rescheduling appointment.", []

    @swaig.endpoint(
        "Cancel an appointment",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Cancelling your appointment...",
                    "Processing cancellation..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        job_number=SWAIGArgument(type="string", description="The job number for the appointment to cancel", required=False),
        appointment_id=SWAIGArgument(type="integer", description="The appointment ID to cancel (optional, use job number if possible)", required=False),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def cancel_appointment(customer_id, job_number=None, appointment_id=None, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            # Look up appointment by job_number if provided
            if job_number:
                appt = db.execute('SELECT * FROM appointments WHERE customer_id = ? AND job_number = ?', (customer_id, job_number)).fetchone()
                if not appt:
                    db.close()
                    return f"No appointment found with job number {job_number}.", []
                appointment_id = appt['id']
            elif appointment_id:
                appt = db.execute('SELECT * FROM appointments WHERE id = ? AND customer_id = ?', (appointment_id, customer_id)).fetchone()
                if not appt:
                    db.close()
                    return "Appointment not found.", []
            else:
                db.close()
                return "Please provide the job number for the appointment you want to cancel.", []
            if appt['status'] == 'cancelled':
                db.close()
                return "Appointment is already cancelled.", []
            # Update appointment status
            db.execute('''
                UPDATE appointments 
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (appointment_id,))
            # Log the cancellation
            db.execute('''
                INSERT INTO appointment_history (appointment_id, action, details, created_at)
                VALUES (?, 'cancelled', ?, CURRENT_TIMESTAMP)
            ''', (appointment_id, json.dumps({
                'job_number': appt['job_number'],
                'reason': 'Customer requested cancellation'
            })))
            db.commit()
            # Get updated appointment
            updated_appointment = db.execute('''
                SELECT a.*, t.name as technician_name
                FROM appointments a
                LEFT JOIN technicians t ON a.technician_id = t.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()
            # Send SMS notification about cancellation
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if customer:
                try:
                    compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                    appointment_time = updated_appointment['start_time']
                    message = f"Your {updated_appointment['type']} appointment (Job #{updated_appointment['job_number']}) for {appointment_time} has been cancelled. Call 1-800-ZEN-CABLE to reschedule."
                    payload = {
                        "From": FROM_NUMBER,
                        "To": customer['phone'],
                        "Body": message
                    }
                    response = requests.post(
                        compat_url,
                        data=payload,
                        auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    response.raise_for_status()
                except Exception as e:
                    app.logger.error(f"Error sending cancel appointment SMS: {str(e)}")
            db.close()
            return "Your appointment has been cancelled.", []
        except Exception as e:
            app.logger.error(f"SWAIG error in cancel_appointment: {str(e)}")
            return "Error cancelling appointment.", []

    def format_mac_address(mac_address):
        """Format MAC address to XX:XX:XX:XX:XX:XX format."""
        # Remove any non-alphanumeric characters
        mac = ''.join(c for c in mac_address if c.isalnum())
        # Ensure we have exactly 12 characters
        if len(mac) != 12:
            return None
        # Format with colons
        return ':'.join(mac[i:i+2] for i in range(0, 12, 2))

    @swaig.endpoint(
        "Swap the customer's modem",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Processing modem swap...",
                    "Updating modem information...",
                    "Please wait while I update your modem..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        make=SWAIGArgument(type="string", description="The make of the new modem (e.g., Motorola, Netgear)", required=True),
        model=SWAIGArgument(type="string", description="The model of the new modem (e.g., MB8600, CM1000)", required=True),
        mac_address=SWAIGArgument(type="string", description="The MAC address of the new modem (format: XX:XX:XX:XX:XX:XX)", required=True),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def swap_modem(customer_id, make, model, mac_address, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
            if not customer:
                return "I couldn't find your account. Please verify your account number.", []

            # Format MAC address
            formatted_mac = format_mac_address(mac_address)
            if not formatted_mac:
                return "Invalid MAC address. Please provide a valid 12-character MAC address.", []

            # Check if MAC address is already in use
            existing = db.execute('SELECT * FROM modems WHERE mac_address = ? AND customer_id != ?', 
                                (formatted_mac, customer_id)).fetchone()
            if existing:
                return "This MAC address is already registered to another customer. Please provide a different MAC address.", []

            # Update modem information
            db.execute('''
                UPDATE modems 
                SET make = ?, model = ?, mac_address = ?, last_updated = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            ''', (make, model, formatted_mac, customer_id))

            # Log the modem swap
            db.execute('''
                INSERT INTO modem_history (customer_id, action, details, created_at)
                VALUES (?, 'swap', ?, CURRENT_TIMESTAMP)
            ''', (customer_id, json.dumps({
                'make': make,
                'model': model,
                'mac_address': formatted_mac
            })))

            db.commit()

            # Get updated modem info
            modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (customer_id,)).fetchone()
            db.close()

            return f"Modem information updated successfully. Your new modem is a {make} {model} with MAC address {formatted_mac}.", []

        except Exception as e:
            app.logger.error(f"Error in swap_modem: {str(e)}")
            return "Error updating modem information.", []

    @swaig.endpoint(
        "Check for existing appointments for the customer",
        SWAIGFunctionProperties(
            active=True,
            wait_for_fillers=True,
            fillers={
                "default": [
                    "Checking your upcoming appointments...",
                    "Retrieving your scheduled appointments...",
                    "One moment while I look up your appointments..."
                ]
            }
        ),
        customer_id=SWAIGArgument(type="string", description="The customer's account ID", required=True),
        meta_data=SWAIGArgument(type="object", description="Additional metadata", required=False),
        meta_data_token=SWAIGArgument(type="string", description="Metadata token", required=False)
    )
    def check_existing_appointments(customer_id, meta_data=None, meta_data_token=None):
        try:
            db = get_db()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            appointments = db.execute('''
                SELECT id, type, status, start_time, end_time, notes
                FROM appointments
                WHERE customer_id = ? AND start_time >= ?
                ORDER BY start_time ASC
            ''', (customer_id, now)).fetchall()
            db.close()
            if not appointments:
                return "You have no upcoming appointments.", []
            appt_list = []
            for appt in appointments:
                appt_list.append(f"{appt['type'].capitalize()} on {appt['start_time']} (Status: {appt['status'].capitalize()})")
            response = "You have the following upcoming appointments: " + "; ".join(appt_list)
            return response, []
        except Exception as e:
            app.logger.error(f"SWAIG error in check_existing_appointments: {str(e)}")
            return "Error checking appointments.", []

# Add template filters
@app.template_filter('status_color')
def status_color(status):
    colors = {
        'scheduled': 'primary',
        'completed': 'success',
        'cancelled': 'danger',
        'pending': 'warning'
    }
    return colors.get(status.lower(), 'secondary')

# Initialize and register endpoints
initialize_signalwire()

# Environment Configuration
HOST = '0.0.0.0'
PORT = 8080
DEBUG = os.getenv('FLASK_ENV') == 'development'

@app.route('/', methods=['GET'])
def index():
    if os.path.exists('.env') and all([SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN, SIGNALWIRE_SPACE]):
        return redirect(url_for('dashboard') if 'customer_id' in session else url_for('login'))
    return render_template('populate.html')

@app.route('/generate', methods=['POST'])
def generate_env():
    try:
        env_content = f"""HTTP_USERNAME={request.form['httpUsername']}
HTTP_PASSWORD={request.form['httpPassword']}
SIGNALWIRE_PROJECT_ID={request.form['signalwireProjectId']}
SIGNALWIRE_TOKEN={request.form['signalwireToken']}
SIGNALWIRE_SPACE={request.form['signalwireSpace']}
FROM_NUMBER={request.form['fromNumber']}
PORT=8080
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        app.logger.info("Generated .env file")
        flash('Configuration saved! Restart the app to apply changes.', 'success')
    except Exception as e:
        app.logger.error(f"Error generating .env: {str(e)}")
        flash('Failed to save configuration.', 'danger')
    return redirect(url_for('index'))

@app.route('/swaig', methods=['GET', 'POST'])
def swaig_endpoint():
    if not swaig:
        return jsonify({"error": "SWAIG not initialized"}), 503
    resp_body = swaig.handle_request(request)
    return Response(resp_body, mimetype='application/json')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('zen_cable.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db_if_needed():
    try:
        db = get_db()
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'").fetchone():
            from init_db import init_db
            from init_test_data import init_test_data
            print("Initializing database...")
            init_db()
            init_test_data()
            print("Database initialized!")
        db.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt

def verify_password(password, stored_hash, salt):
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest() == stored_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = request.form.get('remember', False)
        db = get_db()
        user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        db.close()
        if user and verify_password(password, user['password_hash'], user['password_salt']):
            session['customer_id'] = user['id']
            if remember:
                session.permanent = True
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            db.execute('INSERT INTO password_resets (customer_id, token, expiry) VALUES (?, ?, ?)',
                      (user['id'], token, expiry))
            db.commit()
            flash('Reset instructions sent to your email.', 'success')
        else:
            flash('Email not found.', 'danger')
        db.close()
    return render_template('forgot_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    services = db.execute('''
        SELECT s.* FROM services s
        JOIN customer_services cs ON s.id = cs.service_id
        WHERE cs.customer_id = ? AND cs.status = 'active'
    ''', (session['customer_id'],)).fetchall()
    modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (session['customer_id'],)).fetchone()
    billing = db.execute('''
        SELECT * FROM billing 
        WHERE customer_id = ? 
        ORDER BY due_date DESC LIMIT 1
    ''', (session['customer_id'],)).fetchone()
    db.close()

    # Create a default billing object if none exists
    if not billing:
        billing = {
            'amount': 0.00,
            'due_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'no_billing'
        }

    # Create a default modem object if none exists
    if not modem:
        modem = {
            'status': 'offline',
            'mac_address': 'No modem registered',
            'make': 'Unknown',
            'model': 'Unknown'
        }

    return render_template('dashboard.html', customer=customer, services=services, modem=modem, billing=billing)

@app.route('/api/modem/status', methods=['GET'])
@login_required
def get_modem_status():
    db = get_db()
    modem = db.execute('SELECT status FROM modems WHERE customer_id = ?', (session['customer_id'],)).fetchone()
    db.close()
    if modem:
        return jsonify({'status': modem['status']})
    return jsonify({'error': 'Modem not found'}), 404

@app.route('/api/billing/balance', methods=['GET'])
@login_required
def get_balance():
    db = get_db()
    billing = db.execute('''
        SELECT amount FROM billing 
        WHERE customer_id = ? 
        ORDER BY due_date DESC LIMIT 1
    ''', (session['customer_id'],)).fetchone()
    db.close()
    if billing:
        return jsonify({'balance': billing['amount']})
    return jsonify({'error': 'No billing information found'}), 404

@app.route('/api/appointments', methods=['GET'])
@login_required
def get_appointments():
    start = request.args.get('start')
    end = request.args.get('end')
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(max(1, request.args.get('per_page', 10, type=int)), 100)
    status = request.args.get('status')
    type_filter = request.args.get('type')
    technician = request.args.get('technician')
    priority = request.args.get('priority')
    sort_by = request.args.get('sort_by', 'start_time')
    sort_order = request.args.get('sort_order', 'desc')
    include_history = request.args.get('include_history', 'false').lower() == 'true'
    include_reminders = request.args.get('include_reminders', 'false').lower() == 'true'

    if not start or not end:
        return jsonify({'error': 'Start and end dates required'}), 400
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')
        if start_date > end_date or (end_date - start_date).days > 365:
            return jsonify({'error': 'Invalid date range'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    valid_statuses = ['scheduled', 'completed', 'cancelled', 'pending']
    valid_types = ['installation', 'repair', 'upgrade', 'modem_swap']
    valid_priorities = ['low', 'medium', 'high', 'urgent']
    valid_sort_fields = ['start_time', 'end_time', 'type', 'status', 'priority']
    valid_sort_orders = ['asc', 'desc']

    if status and status not in valid_statuses:
        return jsonify({'error': f'Invalid status: {valid_statuses}'}), 400
    if type_filter and type_filter not in valid_types:
        return jsonify({'error': f'Invalid type: {valid_types}'}), 400
    if priority and priority not in valid_priorities:
        return jsonify({'error': f'Invalid priority: {valid_priorities}'}), 400
    if sort_by not in valid_sort_fields:
        return jsonify({'error': f'Invalid sort field: {valid_sort_fields}'}), 400
    if sort_order not in valid_sort_orders:
        return jsonify({'error': f'Invalid sort order: {valid_sort_orders}'}), 400

    db = get_db()
    query = '''
        SELECT a.*, c.name as customer_name, c.phone as customer_phone, t.name as technician_name
        FROM appointments a
        LEFT JOIN customers c ON a.customer_id = c.id
        LEFT JOIN technicians t ON a.technician_id = t.id
        WHERE a.customer_id = ? AND a.start_time BETWEEN ? AND ?
    '''
    params = [session['customer_id'], start, end]
    if status:
        query += ' AND a.status = ?'
        params.append(status)
    if type_filter:
        query += ' AND a.type = ?'
        params.append(type_filter)
    if technician:
        query += ' AND t.name LIKE ?'
        params.append(f'%{technician}%')
    if priority:
        query += ' AND a.priority = ?'
        params.append(priority)
    query += f' ORDER BY a.{sort_by} {sort_order}'
    total = db.execute(f"SELECT COUNT(*) FROM ({query})", params).fetchone()[0]
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    appointments = db.execute(query, params).fetchall()
    result = [dict(appt) for appt in appointments]

    if include_history:
        for appt in result:
            history = db.execute('SELECT * FROM appointment_history WHERE appointment_id = ? ORDER BY created_at DESC', (appt['id'],)).fetchall()
            appt['history'] = [dict(h) for h in history]
    if include_reminders:
        for appt in result:
            reminders = db.execute('SELECT * FROM appointment_reminders WHERE appointment_id = ? ORDER BY sent_at DESC', (appt['id'],)).fetchall()
            appt['reminders'] = [dict(r) for r in reminders]
    db.close()
    return jsonify({
        'appointments': result,
        'pagination': {'total': total, 'page': page, 'per_page': per_page, 'total_pages': (total + per_page - 1) // per_page}
    })

@app.route('/appointments')
@login_required
def appointments():
    db = get_db()
    # Get all appointments for the customer
    appointments = db.execute('''
        SELECT a.*, t.name as technician_name
        FROM appointments a
        LEFT JOIN technicians t ON a.technician_id = t.id
        WHERE a.customer_id = ?
        ORDER BY a.start_time DESC
    ''', (session['customer_id'],)).fetchall()
    # Fetch customer details to include in the template context
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    db.close()

    return render_template('appointments.html', appointments=appointments, customer=customer)

@app.route('/billing')
@login_required
def billing():
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    current_balance = db.execute('''
        SELECT amount, due_date FROM billing 
        WHERE customer_id = ? 
        ORDER BY due_date DESC LIMIT 1
    ''', (session['customer_id'],)).fetchone()
    payment_methods = db.execute('''
        SELECT * FROM payment_methods 
        WHERE customer_id = ?
    ''', (session['customer_id'],)).fetchall()
    payment_history = db.execute('''
        SELECT * FROM payments 
        WHERE customer_id = ? 
        ORDER BY payment_date DESC
    ''', (session['customer_id'],)).fetchall()
    db.close()

    # Handle case when current_balance is None
    balance_amount = current_balance['amount'] if current_balance else 0
    due_date = current_balance['due_date'] if current_balance else datetime.now()

    return render_template('billing.html', 
                         customer=customer,
                         current_balance=balance_amount,
                         due_date=due_date,
                         payment_methods=payment_methods,
                         payment_history=payment_history)

@app.route('/api/modem/status', methods=['POST'])
@login_required
def modem_status():
    db = get_db()
    if request.method == 'POST':
        status = request.json.get('status') if request.json else None
        if status not in ['online', 'offline', 'rebooting']:
            return jsonify({'error': 'Invalid status'}), 400
        try:
            if status == 'rebooting':
                thread = threading.Thread(target=simulate_modem_reboot, args=(session['customer_id'],))
                thread.daemon = True
                thread.start()
            else:
                db.execute('UPDATE modems SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE customer_id = ?', 
                          (status, session['customer_id']))
                db.commit()
        except Exception as e:
            app.logger.error(f"Error updating modem status: {str(e)}")
            return jsonify({'error': 'Failed to update modem status'}), 500
    modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (session['customer_id'],)).fetchone()
    db.close()
    return jsonify(dict(modem)) if modem else jsonify({'error': 'Modem not found'}), 404

@app.route('/api/modem/swap', methods=['POST'])
@login_required
def swap_modem():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['make', 'model', 'mac_address']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    make = request.json['make'].strip()
    model = request.json['model'].strip()
    mac_address = request.json['mac_address'].strip()

    # Validate MAC address format
    import re
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac_address):
        return jsonify({'error': 'Invalid MAC address format'}), 400

    db = get_db()
    try:
        # Check if MAC address is already in use
        existing = db.execute('SELECT * FROM modems WHERE mac_address = ? AND customer_id != ?', 
                            (mac_address, session['customer_id'])).fetchone()
        if existing:
            return jsonify({'error': 'This MAC address is already registered to another customer'}), 400

        # Update modem information
        db.execute('''
            UPDATE modems 
            SET make = ?, model = ?, mac_address = ?, last_updated = CURRENT_TIMESTAMP
            WHERE customer_id = ?
        ''', (make, model, mac_address, session['customer_id']))

        # Log the modem swap
        db.execute('''
            INSERT INTO modem_history (customer_id, action, details, created_at)
            VALUES (?, 'swap', ?, CURRENT_TIMESTAMP)
        ''', (session['customer_id'], json.dumps({
            'make': make,
            'model': model,
            'mac_address': mac_address
        })))

        db.commit()

        # Get updated modem info
        modem = db.execute('SELECT * FROM modems WHERE customer_id = ?', (session['customer_id'],)).fetchone()
        db.close()

        return jsonify(dict(modem))

    except Exception as e:
        app.logger.error(f"Error swapping modem: {str(e)}")
        return jsonify({'error': 'Failed to update modem information'}), 500

def simulate_modem_reboot(customer_id):
    with app.app_context():
        db = get_db()
        try:
            db.execute('UPDATE modems SET status = "rebooting", last_seen = CURRENT_TIMESTAMP WHERE customer_id = ?', (customer_id,))
            db.commit()
            time.sleep(30)
            db.execute('UPDATE modems SET status = "online", last_seen = CURRENT_TIMESTAMP WHERE customer_id = ?', (customer_id,))
            db.commit()
        except Exception as e:
            app.logger.error(f"Error in modem reboot simulation: {str(e)}")
        finally:
            db.close()

def send_appointment_reminder(appointment, reminder_type='sms'):
    if not signalwire_client or not FROM_NUMBER:
        return False
    db = get_db()
    try:
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (appointment['customer_id'],)).fetchone()
        if not customer:
            return False
        appointment_time = datetime.strptime(appointment['start_time'], '%Y-%m-%d %H:%M:%S')
        formatted_time = appointment_time.strftime('%B %d, %Y at %I:%M %p')
        message = f"Reminder: Your {appointment['type']} appointment is on {formatted_time}. Call 1-800-ZEN-CABLE to reschedule."
        if reminder_type == 'sms':
            signalwire_client.messages.create(to=customer['phone'], from_=FROM_NUMBER, body=message)
        else:
            signalwire_client.calls.create(to=customer['phone'], from_=FROM_NUMBER, 
                                         url=f"{request.host_url}reminder_call/{appointment['id']}")
        db.execute('INSERT INTO appointment_reminders (appointment_id, reminder_type, sent_at, status) VALUES (?, ?, CURRENT_TIMESTAMP, "sent")', 
                  (appointment['id'], reminder_type))
        db.commit()
        return True
    except Exception as e:
        app.logger.error(f"Error sending {reminder_type} reminder: {str(e)}")
        return False
    finally:
        db.close()

def schedule_reminders(appointment):
    if not signalwire_client or not FROM_NUMBER:
        return
    appointment_time = datetime.strptime(appointment['start_time'], '%Y-%m-%d %H:%M:%S')
    sms_time = appointment_time - timedelta(hours=24)
    if sms_time > datetime.now():
        schedule.every().day.at(sms_time.strftime('%H:%M')).do(send_appointment_reminder, appointment, 'sms')
    call_time = appointment_time - timedelta(hours=1)
    if call_time > datetime.now():
        schedule.every().day.at(call_time.strftime('%H:%M')).do(send_appointment_reminder, appointment, 'call')

def log_appointment_history(appointment_id, action, details):
    db = get_db()
    try:
        db.execute('INSERT INTO appointment_history (appointment_id, action, details, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', 
                  (appointment_id, action, json.dumps(details)))
        db.commit()
    except Exception as e:
        app.logger.error(f"Error logging history: {str(e)}")
    finally:
        db.close()

@app.route('/settings')
@login_required
def settings():
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    db.close()
    return render_template('settings.html', customer=customer)

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['first_name', 'last_name', 'phone', 'address']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    db = get_db()
    try:
        db.execute('''
            UPDATE customers 
            SET first_name = ?, last_name = ?, phone = ?, address = ?
            WHERE id = ?
        ''', (request.json['first_name'], request.json['last_name'], 
              request.json['phone'], request.json['address'], 
              session['customer_id']))
        db.commit()
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
        db.close()
        return jsonify(dict(customer))
    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/api/password', methods=['PUT'])
@login_required
def change_password():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['current_password', 'new_password']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()

    if not verify_password(request.json['current_password'], customer['password_hash'], customer['password_salt']):
        return jsonify({'error': 'Current password is incorrect'}), 400

    try:
        password_hash, password_salt = hash_password(request.json['new_password'])
        db.execute('''
            UPDATE customers 
            SET password_hash = ?, password_salt = ?
            WHERE id = ?
        ''', (password_hash, password_salt, session['customer_id']))
        db.commit()
        db.close()
        return jsonify({'message': 'Password updated successfully'})
    except Exception as e:
        app.logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500

@app.route('/api/password/reset/initiate', methods=['POST'])
def initiate_password_reset():
    if not (SIGNALWIRE_PROJECT_ID and SIGNALWIRE_TOKEN and SIGNALWIRE_SPACE and FROM_NUMBER):
        return jsonify({'error': 'SignalWire client not initialized'}), 503
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
    db.close()
    if not customer or not customer['phone']:
        return jsonify({'error': 'No valid phone number found for this account'}), 400
    if not validate_phone(customer['phone']):
        return jsonify({'error': 'Invalid phone number format for this account.'}), 400
    try:
        mfa_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/relay/rest/mfa/sms"
        payload = {
            "to": customer['phone'],
            "from": FROM_NUMBER,
            "message": "Your Zen Cable password reset code is: {{code}}. This code will expire in 5 minutes.",
            "token_length": 6,
            "max_attempts": 3,
            "allow_alphas": False,
            "valid_for": 300
        }
        response = requests.post(
            mfa_url,
            json=payload,
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        mfa_data = response.json()
        mfa_id = mfa_data.get("id")
        if not mfa_id:
            return jsonify({'error': 'Failed to generate verification code'}), 500
        session['password_reset_mfa_id'] = mfa_id
        session['password_reset_customer_id'] = customer['id']
        return jsonify({'message': 'Verification code sent', 'mfa_id': mfa_id})
    except Exception as e:
        app.logger.error(f"Error initiating password reset: {str(e)}")
        return jsonify({'error': 'Failed to send verification code'}), 500

@app.route('/api/verify-mfa', methods=['POST'])
def verify_mfa():
    print(f"[MFA VERIFY] Session contents at start: {dict(session)}")
    if not (SIGNALWIRE_PROJECT_ID and SIGNALWIRE_TOKEN and SIGNALWIRE_SPACE):
        print("[MFA VERIFY] SignalWire client not initialized")
        return jsonify({'error': 'SignalWire client not initialized'}), 503
    if session.get('password_reset_verified'):
        print("[MFA VERIFY] Attempted double verification.")
        return jsonify({'error': 'MFA already verified for this session.'}), 400
    data = request.json
    code = data.get('code')
    mfa_id = session.get('password_reset_mfa_id')
    print(f"[MFA VERIFY] Received code: {code}, MFA ID: {mfa_id}")
    if not code or not mfa_id:
        print("[MFA VERIFY] No code or MFA session found")
        return jsonify({'error': 'No code or MFA session found'}), 400
    try:
        verify_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/relay/rest/mfa/{mfa_id}/verify"
        payload = {"token": code}
        print(f"[MFA VERIFY] Sending POST to {verify_url} with payload: {payload}")
        response = requests.post(
            verify_url,
            json=payload,
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        print(f"[MFA VERIFY] Response status: {response.status_code}")
        print(f"[MFA VERIFY] Response body: {response.text}")
        if response.status_code == 404:
            print("[MFA VERIFY] 404 Not Found: MFA code expired, already used, or invalid session.")
            return jsonify({'error': 'MFA code expired, already used, or invalid session.'}), 400
        response.raise_for_status()
        verify_data = response.json()
        if verify_data.get("success"):
            print("[MFA VERIFY] Success!")
            session['password_reset_verified'] = True
            session['password_reset_id'] = mfa_id  # Set this for the complete_password_reset endpoint
            return jsonify({'success': True})
        else:
            print(f"[MFA VERIFY] Failure: {verify_data.get('message', 'Invalid code')}")
            return jsonify({'error': verify_data.get('message', 'Invalid code')}), 400
    except Exception as e:
        print(f"[MFA VERIFY] Exception: {str(e)}")
        app.logger.error(f"Error verifying MFA code: {str(e)}")
        return jsonify({'error': 'Failed to verify code'}), 500

@app.route('/api/payments', methods=['POST'])
def process_payment():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['amount', 'payment_method']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    db = get_db()
    try:
        # Insert payment record
        transaction_id = secrets.token_hex(16)
        db.execute('''
            INSERT INTO payments (customer_id, amount, payment_method, status, transaction_id)
            VALUES (?, ?, ?, 'completed', ?)
        ''', (session['customer_id'], request.json['amount'], request.json['payment_method'], transaction_id))

        # Update balance
        current_balance = db.execute('SELECT amount FROM billing WHERE customer_id = ? ORDER BY due_date DESC LIMIT 1', 
                                   (session['customer_id'],)).fetchone()
        if current_balance:
            new_balance = current_balance['amount'] - float(request.json['amount'])
            db.execute('UPDATE billing SET amount = ? WHERE customer_id = ?', 
                      (new_balance, session['customer_id']))

        db.commit()
        return jsonify({'success': True, 'transaction_id': transaction_id})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error processing payment: {str(e)}")
        return jsonify({'error': 'Failed to process payment'}), 500
    finally:
        db.close()

@app.route('/api/password/reset/complete', methods=['POST'])
def complete_password_reset():
    if not session.get('password_reset_verified'):
        return jsonify({'error': 'Please verify your identity first'}), 400

    if not request.json or 'new_password' not in request.json:
        return jsonify({'error': 'No new password provided'}), 400

    customer_id = session.get('password_reset_customer_id')
    if not customer_id:
        return jsonify({'error': 'Invalid reset session'}), 401

    db = get_db()
    try:
        # Update the password
        password_hash, password_salt = hash_password(request.json['new_password'])
        db.execute('''
            UPDATE customers 
            SET password_hash = ?, password_salt = ?
            WHERE id = ?
        ''', (password_hash, password_salt, customer_id))

        # Clear used reset tokens
        db.execute('DELETE FROM password_resets WHERE customer_id = ?', (customer_id,))

        db.commit()
        db.close()

        # Clear session data
        session.pop('password_reset_verified', None)
        session.pop('password_reset_mfa_id', None)
        session.pop('password_reset_id', None)
        session.pop('password_reset_customer_id', None)

        return jsonify({'message': 'Password reset successfully'})
    except Exception as e:
        app.logger.error(f"Error completing password reset: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500

@app.route('/api/appointments/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment(appointment_id):
    db = get_db()
    appointment = db.execute('''
        SELECT a.*, t.name as technician_name
        FROM appointments a
        LEFT JOIN technicians t ON a.technician_id = t.id
        WHERE a.id = ? AND a.customer_id = ?
    ''', (appointment_id, session['customer_id'])).fetchone()
    include_history = request.args.get('include_history', 'false').lower() == 'true'
    history = []
    if appointment and include_history:
        history_rows = db.execute('SELECT * FROM appointment_history WHERE appointment_id = ? ORDER BY created_at DESC', (appointment_id,)).fetchall()
        history = [dict(h) for h in history_rows]
    db.close()
    if appointment:
        appt_dict = dict(appointment)
        if include_history:
            appt_dict['history'] = history
        return jsonify(appt_dict)
    return jsonify({'error': 'Appointment not found'}), 404

def generate_job_number():
    """Generate a unique 5-digit job number."""
    db = get_db()
    while True:
        # Generate a random 5-digit number
        job_number = str(random.randint(10000, 99999))
        # Check if it exists
        exists = db.execute('SELECT 1 FROM appointments WHERE job_number = ?', (job_number,)).fetchone()
        if not exists:
            return job_number

@app.route('/api/appointments', methods=['POST'])
@login_required
def create_appointment():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    required_fields = ['type', 'date', 'time_slot']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    db = get_db()
    try:
        # Validate appointment type
        if request.json['type'] not in ['installation', 'repair', 'upgrade', 'modem_swap']:
            return jsonify({'error': 'Invalid appointment type'}), 400

        # Validate time slot
        if request.json['time_slot'] not in ['morning', 'afternoon', 'evening', 'all_day']:
            return jsonify({'error': 'Invalid time slot'}), 400

        # Parse date
        try:
            appointment_date = datetime.strptime(request.json['date'], '%Y-%m-%d')
            if appointment_date < datetime.now():
                return jsonify({'error': 'Please select a future date'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # Check for existing appointments
        existing = db.execute('''
            SELECT * FROM appointments 
            WHERE customer_id = ? 
            AND date(start_time) = date(?)
        ''', (session['customer_id'], appointment_date)).fetchone()

        if existing:
            return jsonify({'error': f'You already have an appointment on {request.json["date"]}'}), 400

        # Set time slots
        time_slots = {
            'morning': ('08:00 AM', '11:00 AM'),
            'afternoon': ('02:00 PM', '04:00 PM'),
            'evening': ('06:00 PM', '08:00 PM'),
            'all_day': ('08:00 AM', '08:00 PM')
        }
        start_time, end_time = time_slots[request.json['time_slot']]

        # Check if time slot is available
        slot_conflict = db.execute('''
            SELECT * FROM appointments 
            WHERE date(start_time) = date(?)
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        ''', (appointment_date, 
              f"{request.json['date']} {end_time}", f"{request.json['date']} {start_time}",
              f"{request.json['date']} {end_time}", f"{request.json['date']} {start_time}",
              f"{request.json['date']} {start_time}", f"{request.json['date']} {end_time}")).fetchone()

        if slot_conflict:
            return jsonify({'error': f'The {request.json["time_slot"]} time slot on {request.json["date"]} is already booked'}), 400

        # Generate job number
        job_number = generate_job_number()

        # Insert appointment
        cursor = db.execute('''
            INSERT INTO appointments (customer_id, type, status, start_time, end_time, notes, sms_reminder, job_number)
            VALUES (?, ?, 'scheduled', ?, ?, ?, ?, ?)
        ''', (session['customer_id'], 
              request.json['type'],
              f"{request.json['date']} {start_time}",
              f"{request.json['date']} {end_time}",
              request.json.get('notes', ''),
              request.json.get('sms_reminder', True),
              job_number))

        appointment_id = cursor.lastrowid

        # Get the created appointment
        appointment = db.execute('''
            SELECT a.*, t.name as technician_name
            FROM appointments a
            LEFT JOIN technicians t ON a.technician_id = t.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()

        db.commit()

        # Schedule reminders if enabled
        if request.json.get('sms_reminder', True):
            schedule_reminders(dict(appointment))

        # Send SMS notification about new appointment
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
        if customer:
            try:
                compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                appointment_time = appointment['start_time']
                message = f"Your {appointment['type']} appointment (Job #{appointment['job_number']}) is scheduled for {appointment_time}. Call 1-800-ZEN-CABLE to reschedule."
                payload = {
                    "From": FROM_NUMBER,
                    "To": customer['phone'],
                    "Body": message
                }
                response = requests.post(
                    compat_url,
                    data=payload,
                    auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
            except Exception as e:
                app.logger.error(f"Error sending appointment SMS: {str(e)}")

        return jsonify({
            'success': True,
            'appointment': dict(appointment)
        })
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error creating appointment: {str(e)}")
        return jsonify({'error': 'Failed to create appointment'}), 500
    finally:
        db.close()

@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    db = get_db()
    try:
        # Get the appointment
        appointment = db.execute('''
            SELECT a.*, t.name as technician_name
            FROM appointments a
            LEFT JOIN technicians t ON a.technician_id = t.id
            WHERE a.id = ? AND a.customer_id = ?
        ''', (appointment_id, session['customer_id'])).fetchone()

        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        if appointment['status'] == 'cancelled':
            return jsonify({'error': 'Appointment is already cancelled'}), 400

        # Update appointment status
        db.execute('''
            UPDATE appointments 
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (appointment_id,))

        # Log the cancellation
        if request.is_json and request.json:
            reason = request.json.get('reason', 'Customer requested cancellation')
        else:
            reason = 'Customer requested cancellation'
        db.execute('''
            INSERT INTO appointment_history (appointment_id, action, details, created_at)
            VALUES (?, 'cancelled', ?, CURRENT_TIMESTAMP)
        ''', (appointment_id, json.dumps({
            'job_number': appointment['job_number'],
            'reason': reason
        })))

        db.commit()

        # Get updated appointment
        updated_appointment = db.execute('''
            SELECT a.*, t.name as technician_name
            FROM appointments a
            LEFT JOIN technicians t ON a.technician_id = t.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()

        # Send SMS notification about cancellation
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
        if customer:
            try:
                compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                appointment_time = updated_appointment['start_time']
                message = f"Your {updated_appointment['type']} appointment (Job #{updated_appointment['job_number']}) for {appointment_time} has been cancelled. Call 1-800-ZEN-CABLE to reschedule."
                payload = {
                    "From": FROM_NUMBER,
                    "To": customer['phone'],
                    "Body": message
                }
                response = requests.post(
                    compat_url,
                    data=payload,
                    auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
            except Exception as e:
                app.logger.error(f"Error sending cancel appointment SMS: {str(e)}")

        return jsonify({
            'success': True,
            'appointment': dict(updated_appointment)
        })
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error cancelling appointment: {str(e)}")
        return jsonify({'error': 'Failed to cancel appointment'}), 500
    finally:
        db.close()

@app.route('/api/appointments/<int:appointment_id>/reschedule', methods=['POST'])
@login_required
def reschedule_appointment(appointment_id):
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    required_fields = ['date', 'time_slot']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    db = get_db()
    try:
        # Validate time slot
        if request.json['time_slot'] not in ['morning', 'afternoon', 'evening', 'all_day']:
            return jsonify({'error': 'Invalid time slot'}), 400
        # Parse date
        try:
            appointment_date = datetime.strptime(request.json['date'], '%Y-%m-%d')
            if appointment_date < datetime.now():
                return jsonify({'error': 'Please select a future date'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        # Get the appointment
        appointment = db.execute('''
            SELECT a.*, t.name as technician_name
            FROM appointments a
            LEFT JOIN technicians t ON a.technician_id = t.id
            WHERE a.id = ? AND a.customer_id = ?
        ''', (appointment_id, session['customer_id'])).fetchone()
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        # Set time slots
        time_slots = {
            'morning': ('08:00 AM', '11:00 AM'),
            'afternoon': ('02:00 PM', '04:00 PM'),
            'evening': ('06:00 PM', '08:00 PM'),
            'all_day': ('08:00 AM', '08:00 PM')
        }
        start_time, end_time = time_slots[request.json['time_slot']]
        # Check for slot conflict
        slot_conflict = db.execute('''
            SELECT * FROM appointments 
            WHERE customer_id = ? AND id != ? AND date(start_time) = date(?)
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        ''', (session['customer_id'], appointment_id, appointment_date,
              f"{request.json['date']} {end_time}", f"{request.json['date']} {start_time}",
              f"{request.json['date']} {end_time}", f"{request.json['date']} {start_time}",
              f"{request.json['date']} {start_time}", f"{request.json['date']} {end_time}")).fetchone()
        if slot_conflict:
            return jsonify({'error': f'The {request.json["time_slot"]} time slot is already booked'}), 400
        # Update appointment
        db.execute('''
            UPDATE appointments 
            SET start_time = ?, end_time = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            f"{request.json['date']} {start_time}",
            f"{request.json['date']} {end_time}",
            request.json.get('notes', appointment['notes']),
            appointment_id
        ))
        # Log the reschedule
        db.execute('''
            INSERT INTO appointment_history (appointment_id, action, details, created_at)
            VALUES (?, 'rescheduled', ?, CURRENT_TIMESTAMP)
        ''', (appointment_id, json.dumps({
            'date': request.json['date'],
            'time_slot': request.json['time_slot'],
            'notes': request.json.get('notes', appointment['notes']),
            'job_number': appointment['job_number']
        })))
        db.commit()
        # Get updated appointment
        updated_appointment = db.execute('''
            SELECT a.*, t.name as technician_name
            FROM appointments a
            LEFT JOIN technicians t ON a.technician_id = t.id
            WHERE a.id = ?
        ''', (appointment_id,)).fetchone()
        # Send SMS notification about reschedule
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
        if customer:
            try:
                compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
                appointment_time = updated_appointment['start_time']
                message = f"Your {updated_appointment['type']} appointment (Job #{updated_appointment['job_number']}) has been rescheduled to {appointment_time}. Call 1-800-ZEN-CABLE to reschedule."
                payload = {
                    "From": FROM_NUMBER,
                    "To": customer['phone'],
                    "Body": message
                }
                response = requests.post(
                    compat_url,
                    data=payload,
                    auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
            except Exception as e:
                app.logger.error(f"Error sending reschedule appointment SMS: {str(e)}")
        return jsonify({
            'success': True,
            'appointment': dict(updated_appointment)
        })
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error rescheduling appointment: {str(e)}")
        return jsonify({'error': 'Failed to reschedule appointment'}), 500
    finally:
        db.close()

@app.route('/api/test-sms', methods=['POST'])
def test_sms():
    if not (SIGNALWIRE_PROJECT_ID and SIGNALWIRE_TOKEN and SIGNALWIRE_SPACE and FROM_NUMBER):
        return jsonify({'error': 'SignalWire client not initialized'}), 503
    if 'customer_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    db = sqlite3.connect('zen_cable.db')
    db.row_factory = sqlite3.Row
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    try:
        # Use the Compatibility API endpoint
        compat_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/laml/2010-04-01/Accounts/{SIGNALWIRE_PROJECT_ID}/Messages.json"
        payload = {
            "From": FROM_NUMBER,
            "To": customer['phone'],
            "Body": "This is a test SMS from Zen Cable. Your phone number is working correctly!"
        }
        print(f"[Compat SMS] POST to {compat_url} with payload: {payload}")
        response = requests.post(
            compat_url,
            data=payload,
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"[Compat SMS] Response status: {response.status_code}")
        print(f"[Compat SMS] Response body: {response.text}")
        response.raise_for_status()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[Compat SMS] Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-mfa', methods=['POST'])
def test_mfa():
    if not (SIGNALWIRE_PROJECT_ID and SIGNALWIRE_TOKEN and SIGNALWIRE_SPACE and FROM_NUMBER):
        return jsonify({'error': 'SignalWire client not initialized'}), 503
    if 'customer_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    db = sqlite3.connect('zen_cable.db')
    db.row_factory = sqlite3.Row
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    try:
        mfa_url = f"https://{SIGNALWIRE_SPACE}.signalwire.com/api/relay/rest/mfa/sms"
        payload = {
            "to": customer['phone'],
            "from": FROM_NUMBER,
            "message": "Your Zen Cable MFA test code is: {{code}}. This code will expire in 5 minutes.",
            "token_length": 6,
            "max_attempts": 3,
            "allow_alphas": False,
            "valid_for": 300
        }
        response = requests.post(
            mfa_url,
            json=payload,
            auth=(SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        mfa_data = response.json()
        mfa_id = mfa_data.get("id")
        if not mfa_id:
            return jsonify({'error': 'Failed to generate MFA code'}), 500
        session['password_reset_mfa_id'] = mfa_id
        print(f"Test MFA code sent to {customer['phone']} via MFA REST endpoint.")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error sending test MFA code via MFA REST endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db = get_db()
    db.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    setup_logging()
    with app.app_context():
        init_db_if_needed()
        initialize_signalwire()
    app.run(host='0.0.0.0', port=8080, debug=True)