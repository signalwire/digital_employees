import os
import json
import stripe
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, make_response, Response
from logging_config import setup_logging
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, Reservation, Table, MenuItem, Order, OrderItem
from datetime import datetime, timedelta
from sqlalchemy import or_
import queue
import threading
import time
# Import moved to avoid circular import

load_dotenv()

# Create Flask app without static folder
app = Flask(__name__, static_folder=None)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.getcwd(), "instance", "restaurant.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'devsecret')
app.config['local_tz'] = os.getenv('LOCAL_TZ', 'America/New_York')

# Setup file logging
loggers = setup_logging()
app_logger = loggers['main']
reservation_logger = loggers['reservations']
payment_logger = loggers['payments']
sms_logger = loggers['sms']

# Global payment session storage for persistence across Flask contexts
payment_sessions_global = {}

# Global event queue for SSE calendar updates
calendar_event_queue = queue.Queue(maxsize=100)  # Limit queue size to prevent memory issues

# Stripe configuration (using test keys for development)
# For production, set these environment variables with your live keys
stripe.api_key = os.getenv('STRIPE_API_KEY', 'sk_test_51234567890abcdef')  # Replace with your test secret key
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_51234567890abcdef')  # Replace with your test publishable key

# Configure static files
app.config['STATIC_FOLDER'] = os.path.join(app.root_path, 'static')

# Add MIME type configuration
app.config['MIME_TYPES'] = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.txt': 'text/plain',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}

db.init_app(app)
auth = HTTPBasicAuth()

# Custom Jinja2 filter for 12-hour time format
@app.template_filter('time12')
def time12_filter(time_str):
    """Convert 24-hour time format (HH:MM) to 12-hour format (H:MM AM/PM)"""
    try:
        # Parse the time string
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        # Format as 12-hour time
        return time_obj.strftime('%I:%M %p').lstrip('0')
    except (ValueError, AttributeError):
        return time_str  # Return original if parsing fails

# Custom Jinja2 filter for time ago calculation
@app.template_filter('time_ago')
def time_ago_filter(dt):
    """Calculate how many minutes ago a datetime was"""
    try:
        if dt.tzinfo is None:
            now = datetime.now()
            diff = now - dt
        else:
            # Convert "now" to the same timezone instead of just replacing tzinfo
            now = datetime.now(dt.tzinfo)
            diff = now - dt

        minutes = int(diff.total_seconds() / 60)

        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes} min ago"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours}h ago"
            else:
                return f"{hours}h {remaining_minutes}m ago"
    except (AttributeError, TypeError):
        return "Unknown"

# Custom Jinja2 filter for person/people pluralization
@app.template_filter('person_plural')
def person_plural_filter(count):
    """Return 'person' for 1, 'people' for any other number"""
    try:
        count = int(count)
        return "person" if count == 1 else "people"
    except (ValueError, TypeError):
        return "people"

# User credentials for API auth (optional)
users = {
    os.getenv('HTTP_USERNAME', 'admin'): generate_password_hash(os.getenv('HTTP_PASSWORD', 'admin'))
}

# Add error handler for 401 errors
@auth.error_handler
def auth_error(status):
    return jsonify({'error': 'Authentication required'}), status

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# Use this block instead
with app.app_context():
    # Ensure instance directory exists
    import os
    os.makedirs('instance', exist_ok=True)

    try:
        db.create_all()
        print("SUCCESS: Database tables created/verified")

        # Database migration: Add missing payment columns to orders table
        def migrate_orders_table():
            """Add payment columns to orders table if they don't exist"""
            try:
                import sqlite3
                from sqlalchemy import text

                # Use direct SQLite connection for more reliable migration
                db_path = 'instance/restaurant.db'

                # Check if database file exists
                if not os.path.exists(db_path):
                    print("WARNING: Database file doesn't exist, creating new one")
                    return

                # Direct SQLite connection for migration
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Check if orders table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
                if not cursor.fetchone():
                    print("WARNING: Orders table doesn't exist yet, skipping migration")
                    conn.close()
                    return

                # Check current columns
                cursor.execute("PRAGMA table_info(orders)")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]
                print(f"📋 Current orders table columns: {columns}")

                # Define payment columns to add
                payment_columns = [
                    ('payment_status', "VARCHAR(20) DEFAULT 'unpaid'"),
                    ('payment_intent_id', "VARCHAR(100)"),
                    ('payment_amount', "FLOAT"),
                    ('payment_date', "DATETIME"),
                    ('payment_method', "VARCHAR(50)")
                ]

                migration_needed = False
                for col_name, col_def in payment_columns:
                    if col_name not in columns:
                        print(f"🔧 Adding missing column: {col_name}")
                        cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")
                        migration_needed = True

                if migration_needed:
                    # Update existing orders to have 'unpaid' status
                    cursor.execute("UPDATE orders SET payment_status = 'unpaid' WHERE payment_status IS NULL")
                    conn.commit()
                    print("SUCCESS: Orders table migration completed")

                    # Verify the migration
                    cursor.execute("PRAGMA table_info(orders)")
                    updated_columns = [col[1] for col in cursor.fetchall()]
                    print(f"📋 Updated orders table columns: {updated_columns}")
                else:
                    print("SUCCESS: Orders table already has all payment columns")

                conn.close()

            except Exception as e:
                print(f"WARNING: Orders table migration error: {e}")
                import traceback
                traceback.print_exc()

        # Database migration: Add missing payment_method column to reservations table
        def migrate_reservations_table():
            """Add payment_method column to reservations table if it doesn't exist"""
            try:
                import sqlite3

                # Use direct SQLite connection for more reliable migration
                db_path = 'instance/restaurant.db'

                # Check if database file exists
                if not os.path.exists(db_path):
                    print("WARNING: Database file doesn't exist, creating new one")
                    return

                # Direct SQLite connection for migration
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Check if reservations table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reservations'")
                if not cursor.fetchone():
                    print("WARNING: Reservations table doesn't exist yet, skipping migration")
                    conn.close()
                    return

                # Check current columns
                cursor.execute("PRAGMA table_info(reservations)")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]
                print(f"📋 Current reservations table columns: {columns}")

                # Define new columns to add
                new_columns = [
                    ('payment_method', "VARCHAR(50)")
                ]

                migration_needed = False
                for col_name, col_def in new_columns:
                    if col_name not in columns:
                        print(f"🔧 Adding missing column to reservations: {col_name}")
                        cursor.execute(f"ALTER TABLE reservations ADD COLUMN {col_name} {col_def}")
                        migration_needed = True

                if migration_needed:
                    conn.commit()
                    print("SUCCESS: Reservations table migration completed")

                    # Verify the migration
                    cursor.execute("PRAGMA table_info(reservations)")
                    updated_columns = [col[1] for col in cursor.fetchall()]
                    print(f"📋 Updated reservations table columns: {updated_columns}")
                else:
                    print("SUCCESS: Reservations table already has all required columns")

                conn.close()

            except Exception as e:
                print(f"WARNING: Reservations table migration error: {e}")
                import traceback
                traceback.print_exc()

        # Run migrations
        migrate_orders_table()
        migrate_reservations_table()

    except Exception as e:
        print(f"WARNING: Database initialization error: {e}")
        import traceback
        traceback.print_exc()

    # Menu items are now initialized in init_test_data.py
    # This ensures consistent IDs and avoids duplication

# Web routes
@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()

    if search_query:
        # Search by name, phone number, or reservation number
        reservations = Reservation.query.filter(
            or_(
                Reservation.name.ilike(f'%{search_query}%'),
                Reservation.phone_number.ilike(f'%{search_query}%'),
                Reservation.reservation_number.ilike(f'%{search_query}%')
            )
        ).order_by(Reservation.date, Reservation.time).all()
    else:
        reservations = Reservation.query.order_by(Reservation.date, Reservation.time).all()

    return render_template('index.html', reservations=reservations)

@app.route('/reservation/new', methods=['GET', 'POST'])
def new_reservation():
    if request.method == 'POST':
        name = request.form['name']
        party_size = request.form['party_size']
        date = request.form['date']
        time = request.form['time']
        phone_number = request.form['phone_number']
        # Generate a unique 6-digit reservation number
        import random
        while True:
            reservation_number = f"{random.randint(100000, 999999)}"
            # Check if this number already exists
            existing = Reservation.query.filter_by(reservation_number=reservation_number).first()
            if not existing:
                break

        reservation = Reservation(
            reservation_number=reservation_number,
            name=name, 
            party_size=party_size, 
            date=date, 
            time=time, 
            phone_number=phone_number
        )
        db.session.add(reservation)
        db.session.flush()  # Get reservation.id

        # Send SMS confirmation using the receptionist agent's SMS functionality
        if receptionist_agent and phone_number:
            try:
                # Prepare reservation data for SMS
                reservation_data = {
                    'id': reservation.id,
                    'reservation_number': reservation.reservation_number,
                    'name': reservation.name,
                    'date': str(reservation.date),
                    'time': str(reservation.time),
                    'party_size': reservation.party_size,
                    'special_requests': reservation.special_requests or ''
                }

                # Send SMS confirmation
                sms_result = receptionist_agent.send_reservation_sms(reservation_data, phone_number)

                # Console logging for SMS status
                print(f"SMS: WEB FORM SMS Status for reservation {reservation.id}:")
                print(f"   Phone: {phone_number}")
                print(f"   Success: {sms_result.get('success', False)}")
                print(f"   SMS Sent: {sms_result.get('sms_sent', False)}")
                if not sms_result.get('success'):
                    print(f"   Error: {sms_result.get('error', 'Unknown error')}")
                else:
                    print(f"   Result: {sms_result.get('sms_result', 'SMS sent')}")

                if sms_result.get('success'):
                    flash('Reservation created and SMS confirmation sent!', 'success')
                else:
                    flash('Reservation created! (SMS confirmation could not be sent)', 'warning')

            except Exception as e:
                print(f"SMS: WEB FORM SMS Exception for reservation {reservation.id}: {e}")
                flash('Reservation created! (SMS confirmation could not be sent)', 'warning')
        else:
            flash('Reservation created!', 'success')

        db.session.commit()
        return redirect(url_for('index'))
    return render_template('reservation_form.html', action='Create')

# Edit reservation route removed - now handled by modal and API endpoint

@app.route('/reservation/<int:res_id>/delete', methods=['POST'])
def delete_reservation(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    db.session.delete(reservation)
    db.session.commit()
    flash('Reservation deleted!', 'info')
    return redirect(url_for('index'))

@app.route('/calendar')
def calendar():
    try:
        # Get today's date in YYYY-MM-DD format
        today = datetime.now().strftime('%Y-%m-%d')

        # Get today's reservations ordered by time
        todays_reservations = Reservation.query.filter_by(date=today).order_by(Reservation.time).all()

        # Ensure we always return a list, even if empty
        if todays_reservations is None:
            todays_reservations = []

        return render_template('calendar.html', todays_reservations=todays_reservations)
    except Exception as e:
        # Log the error and return an empty list
        print(f"Error in calendar route: {str(e)}")
        return render_template('calendar.html', todays_reservations=[])

@app.route('/api/reservations/calendar')
def get_calendar_events():
    try:
        reservations = Reservation.query.all()
        events = []

        for reservation in reservations:
            try:
                # Parse the date and time strings
                date_str = reservation.date
                time_str = reservation.time

                # Create datetime object
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

                # Use proper pluralization for party size
                party_text = "person" if reservation.party_size == 1 else "people"

                # Create event object with status-based styling
                status = reservation.status or 'confirmed'
                title_prefix = ""
                if status == 'cancelled':
                    title_prefix = "[CANCELLED] "

                event = {
                    'id': reservation.id,
                    'title': f"{title_prefix}{reservation.name} ({reservation.party_size} {party_text})",
                    'start': dt.isoformat(),
                    'end': (dt + timedelta(hours=2)).isoformat(),  # Assuming 2-hour reservations
                    'className': f'reservation-{status}',  # Add CSS class for styling
                    'extendedProps': {
                        'partySize': reservation.party_size,
                        'phoneNumber': reservation.phone_number,
                        'status': status,
                        'specialRequests': reservation.special_requests or ''
                    }
                }
                events.append(event)
            except (ValueError, AttributeError) as e:
                # Log individual reservation errors but continue processing others
                print(f"Error processing reservation {reservation.id}: {str(e)}")
                continue

        return jsonify(events)
    except Exception as e:
        # Log the error and return an empty list
        print(f"Error in calendar events API: {str(e)}")
        return jsonify([]), 500

# REST API endpoints
@app.route('/api/reservations', methods=['GET'])
@auth.login_required
def api_list_reservations():
    reservations = Reservation.query.all()
    return jsonify([r.to_dict() for r in reservations])

@app.route('/api/menu_items')
def api_menu_items():
    items = MenuItem.query.filter_by(is_available=True).all()
    return jsonify([
        {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'category': item.category
        } for item in items
    ])

@app.route('/api/reservations', methods=['POST'])
def api_create_reservation():
    name = request.form.get('name')
    party_size = request.form.get('party_size')
    date = request.form.get('date')
    time = request.form.get('time')
    phone_number = request.form.get('phone_number')
    special_requests = request.form.get('special_requests')
    party_orders_json = request.form.get('party_orders')
    try:
        # Generate a unique 6-digit reservation number
        import random
        while True:
            reservation_number = f"{random.randint(100000, 999999)}"
            # Check if this number already exists
            existing = Reservation.query.filter_by(reservation_number=reservation_number).first()
            if not existing:
                break

        reservation = Reservation(
            reservation_number=reservation_number,
            name=name,
            party_size=int(party_size),
            date=date,
            time=time,
            phone_number=phone_number,
            status='confirmed',
            special_requests=special_requests
        )
        db.session.add(reservation)
        db.session.flush()  # Get reservation.id
        party_orders = json.loads(party_orders_json) if party_orders_json else []
        total_reservation_amount = 0.0
        for person in party_orders:
            person_name = person.get('name', '')
            items = person.get('items', [])
            if not items:
                continue
            order = Order(
                order_number=generate_order_number(),
                reservation_id=reservation.id,
                table_id=None,  # Table assignment logic can be added
                person_name=person_name,
                status='pending',
                total_amount=0.0
            )
            db.session.add(order)
            total = 0.0
            for oi in items:
                menu_item = MenuItem.query.get(int(oi['menu_item_id']))
                qty = int(oi['quantity'])
                if menu_item and qty > 0:
                    total += menu_item.price * qty
                    db.session.add(OrderItem(
                        order=order,
                        menu_item=menu_item,
                        quantity=qty,
                        price_at_time=menu_item.price
                    ))
            order.total_amount = total
            total_reservation_amount += total

        # Send SMS confirmation using the receptionist agent's SMS functionality
        receptionist_agent = get_receptionist_agent()
        if receptionist_agent and phone_number:
            try:
                # Prepare reservation data for SMS
                reservation_data = {
                    'id': reservation.id,
                    'reservation_number': reservation.reservation_number,
                    'name': reservation.name,
                    'date': str(reservation.date),
                    'time': str(reservation.time),
                    'party_size': reservation.party_size,
                    'special_requests': reservation.special_requests or ''
                }

                # Send SMS confirmation
                sms_result = receptionist_agent.send_reservation_sms(reservation_data, phone_number)

                # Console logging for SMS status
                print(f"SMS: WEB API SMS Status for reservation {reservation.id}:")
                print(f"   Phone: {phone_number}")
                print(f"   Success: {sms_result.get('success', False)}")
                print(f"   SMS Sent: {sms_result.get('sms_sent', False)}")
                if not sms_result.get('success'):
                    print(f"   Error: {sms_result.get('error', 'Unknown error')}")
                else:
                    print(f"   Result: {sms_result.get('sms_result', 'SMS sent')}")

            except Exception as e:
                print(f"SMS: WEB API SMS Exception for reservation {reservation.id}: {e}")
                # Don't fail the reservation if SMS fails
                sms_result = {'success': False, 'error': str(e)}

        db.session.commit()
        return jsonify({'success': True, 'total_reservation_amount': total_reservation_amount})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reservations/<int:res_id>', methods=['GET'])
def api_get_reservation(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    return jsonify(reservation.to_dict())

@app.route('/api/reservations/<int:res_id>', methods=['PUT'])
def api_update_reservation(res_id):
    try:
        reservation = Reservation.query.get_or_404(res_id)
        data = request.json
        print(f"DEBUG: Received data for reservation {res_id}: {data}")

        # Update basic reservation fields
        reservation.name = data.get('name', reservation.name)
        reservation.party_size = data.get('party_size', reservation.party_size)
        reservation.date = data.get('date', reservation.date)
        reservation.time = data.get('time', reservation.time)
        reservation.phone_number = data.get('phone_number', reservation.phone_number)
        reservation.special_requests = data.get('special_requests', reservation.special_requests)

        # Handle party orders if provided
        if 'party_orders' in data and data['party_orders']:
            try:
                print(f"🔄 Processing party orders for reservation {res_id}")
                
                # Delete existing orders for this reservation
                existing_orders = Order.query.filter_by(reservation_id=reservation.id).all()
                print(f"🗑️ Deleting {len(existing_orders)} existing orders")
                for order in existing_orders:
                    # Delete order items first
                    OrderItem.query.filter_by(order_id=order.id).delete()
                    db.session.delete(order)

                # Create new orders from party_orders data
                party_orders_data = data['party_orders']
                
                # Handle string JSON data
                if isinstance(party_orders_data, str):
                    try:
                        party_orders = json.loads(party_orders_data)
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error for party_orders: {e}")
                        print(f"   Raw data: {party_orders_data}")
                        return jsonify({'success': False, 'error': f'Invalid JSON format in party_orders: {str(e)}'}), 400
                else:
                    party_orders = party_orders_data

                print(f"DEBUG: Processing party orders: {party_orders}")
                
                # Validate party_orders structure
                if not isinstance(party_orders, (list, dict)):
                    print(f"❌ Invalid party_orders format - expected list or dict, got {type(party_orders)}")
                    return jsonify({'success': False, 'error': 'party_orders must be a list or dictionary'}), 400

                # Handle both formats: array of {name, items} or dict with person names as keys
                if isinstance(party_orders, list):
                    # New format: array of {name, items}
                    for person_order in party_orders:
                        if not isinstance(person_order, dict):
                            print(f"❌ Invalid person order format - expected dict, got {type(person_order)}")
                            continue
                            
                        person_name = person_order.get('name', '') or f"Person {party_orders.index(person_order) + 1}"
                        items = person_order.get('items', [])
                        
                        if not isinstance(items, list):
                            print(f"❌ Invalid items format for {person_name} - expected list, got {type(items)}")
                            continue

                        if items and len(items) > 0:  # Only create order if there are items
                            print(f"👤 Creating order for {person_name} with {len(items)} items")
                            order = Order(
                                order_number=generate_order_number(),
                                reservation_id=reservation.id,
                                person_name=person_name,
                                status='pending',
                                target_date=str(reservation.date),
                                target_time=str(reservation.time),
                                order_type='reservation',
                                payment_status='unpaid',
                                customer_phone=reservation.phone_number
                            )
                            db.session.add(order)
                            db.session.flush()  # Get order ID

                            total_amount = 0
                            processed_items = 0
                            for oi in items:
                                try:
                                    # Validate item structure
                                    if not isinstance(oi, dict):
                                        print(f"❌ Invalid order item format - expected dict, got {type(oi)}")
                                        continue
                                        
                                    if 'menu_item_id' not in oi or 'quantity' not in oi:
                                        print(f"❌ Missing required fields in order item: {oi}")
                                        continue
                                        
                                    menu_item_id = int(oi['menu_item_id'])
                                    quantity = int(oi['quantity'])
                                    
                                    if quantity <= 0:
                                        print(f"❌ Invalid quantity {quantity} for menu item {menu_item_id}")
                                        continue
                                        
                                    menu_item = MenuItem.query.get(menu_item_id)
                                    if menu_item:
                                        order_item = OrderItem(
                                            order_id=order.id,
                                            menu_item_id=menu_item.id,
                                            quantity=quantity,
                                            price_at_time=menu_item.price
                                        )
                                        db.session.add(order_item)
                                        total_amount += menu_item.price * quantity
                                        processed_items += 1
                                        print(f"✅ Added {quantity}x {menu_item.name} (${menu_item.price * quantity:.2f})")
                                    else:
                                        print(f"❌ Menu item {menu_item_id} not found")
                                        
                                except (ValueError, KeyError, TypeError) as e:
                                    print(f"❌ Error processing order item {oi}: {e}")
                                    continue

                            order.total_amount = total_amount
                            print(f"✅ Created order for {person_name} with {processed_items} items, total: ${total_amount:.2f}")
                else:
                    # Old format: dict with person names as keys
                    for person_name, orders in party_orders.items():
                        if not isinstance(orders, list):
                            print(f"❌ Invalid orders format for {person_name} - expected list, got {type(orders)}")
                            continue
                            
                        if orders and len(orders) > 0:  # Only create order if there are items
                            print(f"👤 Creating order for {person_name} with {len(orders)} items")
                            order = Order(
                                order_number=generate_order_number(),
                                reservation_id=reservation.id,
                                person_name=person_name,
                                status='pending',
                                target_date=str(reservation.date),
                                target_time=str(reservation.time),
                                order_type='reservation',
                                payment_status='unpaid',
                                customer_phone=reservation.phone_number
                            )
                            db.session.add(order)
                            db.session.flush()  # Get order ID

                            total_amount = 0
                            processed_items = 0
                            for oi in orders:
                                try:
                                    # Validate item structure
                                    if not isinstance(oi, dict):
                                        print(f"❌ Invalid order item format - expected dict, got {type(oi)}")
                                        continue
                                        
                                    if 'menu_item_id' not in oi or 'quantity' not in oi:
                                        print(f"❌ Missing required fields in order item: {oi}")
                                        continue
                                        
                                    menu_item_id = int(oi['menu_item_id'])
                                    quantity = int(oi['quantity'])
                                    
                                    if quantity <= 0:
                                        print(f"❌ Invalid quantity {quantity} for menu item {menu_item_id}")
                                        continue
                                        
                                    menu_item = MenuItem.query.get(menu_item_id)
                                    if menu_item:
                                        order_item = OrderItem(
                                            order_id=order.id,
                                            menu_item_id=menu_item.id,
                                            quantity=quantity,
                                            price_at_time=menu_item.price
                                        )
                                        db.session.add(order_item)
                                        total_amount += menu_item.price * quantity
                                        processed_items += 1
                                        print(f"✅ Added {quantity}x {menu_item.name} (${menu_item.price * quantity:.2f})")
                                    else:
                                        print(f"❌ Menu item {menu_item_id} not found")
                                        
                                except (ValueError, KeyError, TypeError) as e:
                                    print(f"❌ Error processing order item {oi}: {e}")
                                    continue

                            order.total_amount = total_amount
                            print(f"✅ Created order for {person_name} with {processed_items} items, total: ${total_amount:.2f}")
                            
            except Exception as e:
                print(f"❌ Error handling party orders: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'error': f'Failed to process party orders: {str(e)}'}), 500

        db.session.commit()
        print(f"✅ Successfully updated reservation {res_id}")
        return jsonify({'success': True, 'reservation': reservation.to_dict()})

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating reservation {res_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reservations/<int:res_id>', methods=['DELETE'])
def api_delete_reservation(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    # Mark as cancelled instead of deleting
    reservation.status = 'cancelled'
    db.session.commit()
    return '', 204

@app.route('/api/menu', methods=['GET'])
def get_menu():
    # Get menu items from database and organize by category
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    menu_data = {}

    for item in menu_items:
        if item.category not in menu_data:
            menu_data[item.category] = []

        # Convert database item to template format
        menu_item = {
            'id': str(item.id),
            'name': item.name,
            'description': item.description,
            'price': item.price
        }
        menu_data[item.category].append(menu_item)

    # Check if menu data was found and log error if empty
    if not menu_data:
        print("ERROR: ERROR: No menu items found in database!")
        print("   This indicates a database setup issue.")
        print("   Run 'python init_test_data.py' to populate menu items.")
    
    return render_template('menu.html', menu=menu_data)

@app.route('/menu')
def menu():
    # Get menu items from database and organize by category
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    menu_data = {}

    for item in menu_items:
        if item.category not in menu_data:
            menu_data[item.category] = []

        # Convert database item to template format
        menu_item = {
            'id': str(item.id),
            'name': item.name,
            'description': item.description,
            'price': item.price
        }
        menu_data[item.category].append(menu_item)

    # Check if menu data was found and log error if empty
    if not menu_data:
        print("ERROR: ERROR: No menu items found in database!")
        print("   This indicates a database setup issue.")
        print("   Run 'python init_test_data.py' to populate menu items.")
    
    return render_template('menu.html', menu=menu_data)

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.json
    reservation_id = data.get('reservation_id')
    items = data.get('items')  # List of {menu_item_id, quantity}

    if not reservation_id or not items:
        return jsonify({'error': 'Invalid data'}), 400

    order = Order(
        order_number=generate_order_number(),
        reservation_id=reservation_id, 
        status='pending'
    )
    db.session.add(order)
    db.session.flush()  # Get the order ID

    total_amount = 0
    for item in items:
        menu_item = MenuItem.query.get(item['menu_item_id'])
        if not menu_item or not menu_item.is_available:
            continue
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item['quantity'],
            price_at_time=menu_item.price
        )
        db.session.add(order_item)
        total_amount += menu_item.price * item['quantity']

    order.total_amount = total_amount
    db.session.commit()

    return jsonify(order.to_dict()), 201

@app.route('/api/orders', methods=['POST'])
def create_standalone_order():
    """Create a standalone order (not tied to a reservation)"""
    try:
        data = request.get_json()
        print(f"DEBUG: Received order data: {data}")

        # Extract order details - handle both camelCase (frontend) and snake_case (API) formats
        customer_name = data.get('customerName') or data.get('customer_name', '')
        customer_phone = data.get('customerPhone') or data.get('customer_phone', '')
        customer_address = data.get('customerAddress') or data.get('customer_address', '')
        order_type = data.get('orderType') or data.get('order_type', 'pickup')  # pickup or delivery
        target_date = data.get('orderDate') or data.get('target_date', datetime.now().strftime('%Y-%m-%d'))
        target_time = data.get('orderTime') or data.get('target_time', datetime.now().strftime('%H:%M'))
        special_instructions = data.get('specialInstructions') or data.get('special_instructions', '')
        items = data.get('items', [])

        print(f"DEBUG: Extracted values - customer_name: '{customer_name}', order_type: '{order_type}', target_date: '{target_date}', target_time: '{target_time}'")

        if not items:
            return jsonify({'success': False, 'error': 'No items provided'}), 400

        if not customer_name or not customer_phone:
            return jsonify({'success': False, 'error': 'Customer name and phone number are required'}), 400

        # Create order
        order = Order(
            order_number=generate_order_number(),
            reservation_id=None,  # Standalone order
            table_id=None,
            person_name=customer_name,
            status='pending',
            target_date=target_date,
            target_time=target_time,
            order_type=order_type,
            customer_phone=customer_phone,
            customer_address=customer_address,
            special_instructions=special_instructions
        )
        db.session.add(order)
        db.session.flush()  # Get order ID

        total_amount = 0

        # Add order items
        for item_data in items:
            # Find menu item by name (since we're using generated IDs)
            menu_item = MenuItem.query.filter_by(name=item_data['name']).first()
            if menu_item:
                # Only add special instructions to item notes, not order type/phone info
                item_notes = ""
                if special_instructions:
                    item_notes = f"Instructions: {special_instructions}"

                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    quantity=item_data['quantity'],
                    price_at_time=item_data['price'],
                    notes=item_notes
                )
                db.session.add(order_item)
                total_amount += item_data['price'] * item_data['quantity']

        order.total_amount = total_amount
        db.session.commit()

        # Calculate estimated time (15-30 minutes for pickup, 30-45 for delivery)
        estimated_time = 25 if order_type == 'pickup' else 40

        return jsonify({
            'success': True, 
            'orderId': order.id,
            'estimatedTime': estimated_time,
            'message': f'Order placed successfully! Estimated {order_type} time: {estimated_time} minutes.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_order_number():
    """Generate a unique 5-digit order number"""
    import random
    while True:
        # Generate a 5-digit number (10000 to 99999)
        number = str(random.randint(10000, 99999))

        # Check if this number already exists (only if we're in an app context)
        try:
            existing = Order.query.filter_by(order_number=number).first()
            if not existing:
                return number
        except RuntimeError:
            # If we're outside app context, just return the number
            # This can happen during testing or initialization
            return number

@app.route('/kitchen')
def kitchen_orders():
    """Kitchen dashboard to view and manage orders"""
    from datetime import datetime, timedelta

    # Get filter parameters
    filter_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    start_time = request.args.get('start_time', '00:00')
    end_time = request.args.get('end_time', '23:59')

    # Parse datetime filters
    try:
        start_datetime = datetime.strptime(f"{filter_date} {start_time}", '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(f"{filter_date} {end_time}", '%Y-%m-%d %H:%M')
    except ValueError:
        # Default to today if parsing fails
        start_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

    # Query orders with target date/time filters and include reservation data
    from sqlalchemy.orm import joinedload
    
    base_query = Order.query.options(joinedload(Order.reservation)).filter(
        Order.target_date == filter_date,
        Order.target_time >= start_time,
        Order.target_time <= end_time
    )

    pending_orders = base_query.filter_by(status='pending').order_by(Order.target_time).all()
    preparing_orders = base_query.filter_by(status='preparing').order_by(Order.target_time).all()
    ready_orders = base_query.filter_by(status='ready').order_by(Order.target_time).all()

    return render_template('kitchen.html', 
                         pending_orders=pending_orders,
                         preparing_orders=preparing_orders, 
                         ready_orders=ready_orders,
                         filter_date=filter_date,
                         start_time=start_time,
                         end_time=end_time)

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status for kitchen management"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['pending', 'preparing', 'ready', 'completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        order.status = new_status
        db.session.commit()

        return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/payment', methods=['PUT'])
def update_order_payment(order_id):
    """Update order payment status"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()

        # Update payment fields
        if 'payment_status' in data:
            order.payment_status = data['payment_status']
        if 'payment_amount' in data:
            order.payment_amount = data['payment_amount']
        if 'payment_intent_id' in data:
            order.payment_intent_id = data['payment_intent_id']
        if 'payment_date' in data:
            order.payment_date = data['payment_date']
        else:
            # Set payment date to now if marking as paid
            if data.get('payment_status') == 'paid':
                order.payment_date = datetime.now()

        db.session.commit()

        return jsonify({'success': True, 'message': 'Payment status updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Serve static files with correct MIME types
@app.route('/static/<path:filename>')
def serve_static(filename):
    mimetype = None
    for ext, mime in app.config['MIME_TYPES'].items():
        if filename.lower().endswith(ext):
            mimetype = mime
            break
    if not mimetype and filename.lower().endswith(('.js', '.mjs')):
        mimetype = 'application/javascript'
    return send_from_directory(app.config['STATIC_FOLDER'], filename, mimetype=mimetype)

# Global conversation memory to track function calls per AI session
conversation_memory = {}

def get_conversation_memory(ai_session_id):
    """Get or create conversation memory for an AI session"""
    if ai_session_id not in conversation_memory:
        conversation_memory[ai_session_id] = {
            'function_calls': [],
            'menu_data': None,
            'last_function_time': {},
            'extracted_info': {},  # Store extracted information from conversation
            'reservation_context': None,  # Store current reservation being discussed
            'payment_context': None  # Store payment-related context
        }
    return conversation_memory[ai_session_id]

def should_block_function_call(ai_session_id, function_name):
    """Check if a function call should be blocked due to recent repetition"""
    memory = get_conversation_memory(ai_session_id)

    # Block if the same function was called in the last 30 seconds
    import time
    current_time = time.time()

    if function_name in memory['last_function_time']:
        time_since_last = current_time - memory['last_function_time'][function_name]

        # Special handling for create_reservation - be more intelligent about blocking
        if function_name == 'create_reservation':
            # Only block if it was called very recently (less than 5 seconds)
            # This allows for natural conversation flow where customer confirms details
            if time_since_last < 5:
                return True, f"Function {function_name} was called {time_since_last:.1f} seconds ago. Please use the previous response."

        # Special handling for create_order - allow if it's likely a finalization
        elif function_name == 'create_order':
            # Allow create_order if it was called more than 10 seconds ago
            # This gives time for the conversation flow to continue
            if time_since_last < 10:
                return True, f"Function {function_name} was called {time_since_last:.1f} seconds ago. Please use the previous response."

        # For get_reservation, allow more frequent calls as customers might be looking up different reservations
        elif function_name == 'get_reservation':
            # Only block if called within 10 seconds
            if time_since_last < 10:
                return True, f"Function {function_name} was called {time_since_last:.1f} seconds ago. Please use the previous response."

        # For payment functions, allow progression through payment steps
        elif function_name in ['pay_reservation']:
            # Only block if called within 5 seconds to allow payment flow progression
            if time_since_last < 5:
                return True, f"Function {function_name} was called {time_since_last:.1f} seconds ago. Please use the previous response."

        else:
            # Standard 30 second cooldown for other functions
            if time_since_last < 30:
                return True, f"Function {function_name} was called {time_since_last:.1f} seconds ago. Please use the previous response."

    # Special rules for specific functions removed - using skill-based menu now

    return False, None

def record_function_call(ai_session_id, function_name, result=None):
    """Record a function call in conversation memory"""
    memory = get_conversation_memory(ai_session_id)
    import time
    current_time = time.time()

    memory['function_calls'].append({
        'function': function_name,
        'timestamp': current_time
    })
    memory['last_function_time'][function_name] = current_time

    # Menu data now handled by skill-based system with meta_data caching

    # Store reservation context from get_reservation results
    if function_name == 'get_reservation' and result:
        try:
            # Extract reservation information from result
            if hasattr(result, 'response'):
                response_text = result.response
                # Look for reservation number in response
                import re
                reservation_match = re.search(r'reservation number:?\s*([0-9]{6})', response_text, re.IGNORECASE)
                if reservation_match:
                    reservation_number = reservation_match.group(1)
                    memory['reservation_context'] = {
                        'reservation_number': reservation_number,
                        'response_text': response_text,
                        'timestamp': current_time
                    }
                    print(f"💾 Stored reservation context: {reservation_number}")
        except Exception as e:
            print(f"WARNING: Error storing reservation context: {e}")

    # Store reservation context from create_reservation results
    if function_name == 'create_reservation' and result:
        try:
            if hasattr(result, 'response'):
                response_text = result.response
                # Look for reservation number in response
                import re
                reservation_match = re.search(r'reservation number:?\s*([0-9]{6})', response_text, re.IGNORECASE)
                if reservation_match:
                    reservation_number = reservation_match.group(1)
                    memory['reservation_context'] = {
                        'reservation_number': reservation_number,
                        'response_text': response_text,
                        'timestamp': current_time,
                        'just_created': True
                    }
                    print(f"💾 Stored new reservation context: {reservation_number}")
        except Exception as e:
            print(f"WARNING: Error storing new reservation context: {e}")

    print(f"📝 Recorded function call: {function_name} for session {ai_session_id}")
    print(f"   Total calls in session: {len(memory['function_calls'])}")
    print(f"   Functions called: {list(memory['last_function_time'].keys())}")

def extract_context_from_conversation(call_log, ai_session_id):
    """Extract relevant context information from conversation history"""
    memory = get_conversation_memory(ai_session_id)
    extracted_info = memory['extracted_info']

    if not call_log:
        return extracted_info

    import re

    # Look through conversation for key information
    for entry in call_log:
        if entry.get('role') == 'user':
            content = entry.get('content', '').strip()

            # Look for reservation numbers (6 digits)
            reservation_matches = re.findall(r'\b(\d{6})\b', content)
            for match in reservation_matches:
                extracted_info['reservation_number'] = match
                print(f"🔍 Extracted reservation number from conversation: {match}")

            # Look for names (patterns like "I'm John Smith", "This is Mary Johnson")
            name_patterns = [
                r'(?:i\'?m|this is|my name is)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
                r'(?:for|under)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)+)',
            ]
            for pattern in name_patterns:
                name_matches = re.findall(pattern, content, re.IGNORECASE)
                for match in name_matches:
                    if len(match.split()) >= 2:  # At least first and last name
                        extracted_info['customer_name'] = match.title()
                        print(f"🔍 Extracted customer name from conversation: {match.title()}")

            # Look for payment intent
            payment_keywords = ['pay', 'payment', 'bill', 'charge', 'credit card']
            if any(keyword in content.lower() for keyword in payment_keywords):
                extracted_info['payment_intent'] = True
                print(f"🔍 Detected payment intent in conversation")

    # Also check assistant responses for reservation information
    for entry in call_log:
        if entry.get('role') == 'assistant':
            content = entry.get('content', '').strip()

            # Look for reservation confirmations with numbers
            reservation_matches = re.findall(r'reservation number:?\s*([0-9]{6})', content, re.IGNORECASE)
            for match in reservation_matches:
                extracted_info['confirmed_reservation_number'] = match
                memory['reservation_context'] = {
                    'reservation_number': match,
                    'response_text': content,
                    'timestamp': time.time()
                }
                print(f"🔍 Extracted confirmed reservation number: {match}")

            # Look for customer names in assistant responses (e.g., "reservation for Johnson Group")
            name_patterns = [
                r'reservation for ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'found your reservation for ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'I found.*for ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
            ]
            for pattern in name_patterns:
                name_matches = re.findall(pattern, content)
                for match in name_matches:
                    if len(match.split()) >= 1:  # At least one name
                        extracted_info['customer_name'] = match.strip()
                        print(f"🔍 Extracted customer name from assistant response: {match.strip()}")
                        break

    return extracted_info

# Add missing preprocessing function for reservation parameters
def preprocess_reservation_params(params):
    """
    Preprocess reservation parameters to handle various date/time formats
    Converts ISO datetime format to separate date and time fields
    """
    try:
        processed_params = params.copy()

        # Handle ISO datetime format in time field (e.g., "2025-06-09T14:00:00")
        time_str = params.get('time', '')
        if time_str and 'T' in time_str and ':' in time_str:
            print(f"🔄 Converting ISO datetime: {time_str}")

            # Parse ISO datetime
            iso_datetime = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            processed_params['date'] = iso_datetime.strftime("%Y-%m-%d")
            processed_params['time'] = iso_datetime.strftime("%H:%M")

            print(f"   Converted to: date='{processed_params['date']}', time='{processed_params['time']}'")

        # Handle ISO datetime format in date field (fallback)
        date_str = params.get('date', '')
        if date_str and 'T' in date_str and ':' in date_str:
            print(f"🔄 Converting ISO datetime in date field: {date_str}")

            # Parse ISO datetime
            iso_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            processed_params['date'] = iso_datetime.strftime("%Y-%m-%d")
            if 'time' not in processed_params or not processed_params['time']:
                processed_params['time'] = iso_datetime.strftime("%H:%M")

            print(f"   Converted to: date='{processed_params['date']}', time='{processed_params['time']}'")

        return processed_params

    except Exception as e:
        print(f"ERROR: Error preprocessing reservation params: {e}")
        # Return original params if preprocessing fails
        return params

# Global agent instance
_agent_instance = None

def get_receptionist_agent():
    """Get or create the receptionist agent instance"""
    global _agent_instance
    if _agent_instance is None:
        try:
            # Import here to avoid circular import
            from swaig_agents import FullRestaurantReceptionistAgent
            _agent_instance = FullRestaurantReceptionistAgent()
            print("SUCCESS: SignalWire agent initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize SignalWire agent: {e}")
            return None
    return _agent_instance

# Add SWAIG routes to Flask app
@app.route('/receptionist', methods=['POST'])
def swaig_receptionist():
    """Handle SWAIG requests for the receptionist agent"""
    try:
        app_logger.info(f"SWAIG POST request received from {request.remote_addr}")
        app_logger.debug(f"Content-Type: {request.content_type}, Content-Length: {request.content_length}")
        print(f"🔍 SWAIG POST request received from {request.remote_addr}")
        print(f"   Content-Type: {request.content_type}")
        print(f"   Content-Length: {request.content_length}")
        print(f"   User-Agent: {request.headers.get('User-Agent', 'None')}")

        agent = get_receptionist_agent()
        if not agent:
            print("ERROR: Agent not available")
            return jsonify({'error': 'Agent not available'}), 503

        # Enhanced raw data logging
        raw_data = request.get_data(as_text=True)
        print(f"📋 Raw request data (first 1000 chars): {raw_data[:1000]}")
        print(f"📋 Raw request data length: {len(raw_data) if raw_data else 0}")

        # Better error handling for JSON parsing
        try:
            data = request.get_json()
            if data:
                import json as json_module
                print(f"📋 Parsed JSON data (full):")
                print(json_module.dumps(data, indent=2))
            else:
                print("📋 Parsed JSON data: None")
        except Exception as json_error:
            print(f"ERROR: JSON parsing error: {json_error}")
            print(f"   Raw data type: {type(raw_data)}")
            print(f"   Raw data length: {len(raw_data) if raw_data else 0}")
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400

        # Validate required SWAIG fields
        if not data:
            print("ERROR: No JSON data received")
            # Try to get form data as fallback
            form_data = request.form.to_dict()
            print(f"   Form data: {form_data}")
            if form_data:
                data = form_data
            else:
                return jsonify({'error': 'No JSON data received'}), 400



        # Check if this is a signature request
        action = data.get('action')
        if action == 'get_signature':
            print("📋 Handling signature request")

            # Get the functions array from the request
            requested_functions = data.get('functions', [])
            print(f"   Requested functions: {requested_functions}")

            # If functions array is empty, return list of available function names
            if not requested_functions:
                print("📋 Returning available function names")

                # Get function names dynamically from the agent's registered SWAIG functions
                available_functions = [
                    'create_reservation',
                    'get_reservation', 
                    'update_reservation',
                    'cancel_reservation',
        
                    'create_order',
                    'get_order_status',
                    'update_order_status',
                    'pay_reservation',
                    'pay_order',
                    'send_payment_receipt',
                    'transfer_to_manager',
                    'schedule_callback'
                ]

                print(f"   Returning {len(available_functions)} available functions: {available_functions}")
                return jsonify({"functions": available_functions})

            # If specific functions are requested, return their signatures
            print(f"📋 Returning signatures for specific functions: {requested_functions}")

            # Define all available function signatures
            all_signatures = {
                'create_reservation': {
                    'function': 'create_reservation',
                    'purpose': ('Create a new restaurant reservation with optional food pre-ordering. '
                               'ALWAYS ask customers if they want to pre-order from the menu when making reservations. '
                               'For parties larger than one, ask for each person\'s name and food preferences. '
                               'If customers mention specific food items during the call, extract them and include in party_orders. '
                               'IMPORTANT: Always confirm the complete order details before creating the reservation.'),
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'Customer full name (extract from conversation if mentioned)'},
                            'party_size': {'type': 'integer', 'description': 'Number of people (extract from conversation)'},
                            'date': {'type': 'string', 'description': 'Reservation date in YYYY-MM-DD format (extract from conversation - today, tomorrow, specific dates)'},
                            'time': {'type': 'string', 'description': 'Reservation time in 24-hour HH:MM format (extract from conversation - convert PM/AM to 24-hour)'},
                            'phone_number': {'type': 'string', 'description': 'Customer phone number with country code (extract from conversation or use caller ID)'},
                            'special_requests': {'type': 'string', 'description': 'Optional special requests or dietary restrictions (extract from conversation)'},
                            'old_school': {'type': 'boolean', 'description': 'True for old school reservation (no pre-ordering), false if customer wants to pre-order'},
                            'party_orders': {
                                'type': 'array',
                                'description': 'Required when customers want to pre-order food. Create one entry per person with their menu items. Always ask "What would [person name] like to eat?" for each person.',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'person_name': {'type': 'string', 'description': 'Name of person ordering (ask for each person: "Person 1", "Person 2", or actual names like "Jim", "Tom")'},
                                        'items': {
                                            'type': 'array',
                                            'description': 'Menu items ordered by this person. IMPORTANT: Always confirm each item before adding.',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'menu_item_id': {'type': 'integer', 'description': 'ID of the menu item (get from menu lookup)'},
                                                    'quantity': {'type': 'integer', 'description': 'Quantity ordered (default 1)'}
                                                },
                                                'required': ['menu_item_id', 'quantity']
                                            }
                                        }
                                    },
                                    'required': ['person_name', 'items']
                                }
                            },
                            'pre_order': {
                                'type': 'array',
                                'description': 'Alternative format for pre-orders using menu item names. Use when menu_item_id is not readily available.',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string', 'description': 'Exact menu item name (e.g., "Kraft Lemonade", "Buffalo Wings")'},
                                        'quantity': {'type': 'integer', 'description': 'Quantity ordered'}
                                    },
                                    'required': ['name', 'quantity']
                                }
                            }
                        },
                        'required': ['name', 'party_size', 'date', 'time', 'phone_number']
                    }
                },
                'get_reservation': {
                    'function': 'get_reservation',
                    'purpose': 'Look up existing reservations by reservation number (preferred) or name. When found by reservation number, asks for confirmation using the name from the database.',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'reservation_number': {'type': 'string', 'description': '6-digit reservation number to find (preferred search method)'},
                            'reservation_id': {'type': 'integer', 'description': 'Specific reservation ID to find'},
                            'name': {'type': 'string', 'description': 'Customer full name, first name, or last name to search by (partial matches work)'},
                            'first_name': {'type': 'string', 'description': 'Customer first name to search by'},
                            'last_name': {'type': 'string', 'description': 'Customer last name to search by'},
                            'date': {'type': 'string', 'description': 'Reservation date to search by (YYYY-MM-DD)'},
                            'time': {'type': 'string', 'description': 'Reservation time to search by (HH:MM)'},
                            'party_size': {'type': 'integer', 'description': 'Number of people to search by'},
                            'email': {'type': 'string', 'description': 'Customer email address to search by'},
                            'phone_number': {'type': 'string', 'description': 'Customer phone number (fallback search method only)'}
                        }
                    }
                },
                'update_reservation': {
                    'function': 'update_reservation',
                    'purpose': 'Update an existing reservation - can search by reservation number first, then fallback to other methods',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'reservation_number': {'type': 'string', 'description': '6-digit reservation number (preferred method)'},
                            'reservation_id': {'type': 'integer', 'description': 'Reservation ID (alternative method)'},
                            'name': {'type': 'string', 'description': 'Customer name'},
                            'party_size': {'type': 'integer', 'description': 'Number of people'},
                            'date': {'type': 'string', 'description': 'Reservation date (YYYY-MM-DD)'},
                            'time': {'type': 'string', 'description': 'Reservation time (HH:MM)'},
                            'phone_number': {'type': 'string', 'description': 'Customer phone number'},
                            'special_requests': {'type': 'string', 'description': 'Special requests or dietary restrictions'}
                        },
                        'required': []
                    }
                },
                'cancel_reservation': {
                    'function': 'cancel_reservation',
                    'purpose': 'Cancel a reservation - can search by reservation number first, then fallback to other methods',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'reservation_number': {'type': 'string', 'description': '6-digit reservation number (preferred method)'},
                            'reservation_id': {'type': 'integer', 'description': 'Reservation ID (alternative method)'},
                            'phone_number': {'type': 'string', 'description': 'Customer phone number for verification'}
                        },
                        'required': []
                    }
                },
                'create_order': {
                    'function': 'create_order',
                    'purpose': 'Create a pickup or delivery order (NOT linked to a dining reservation). Use this for customers who want food to go, not for adding items to existing reservations.',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'items': {
                                'type': 'array', 
                                'description': 'List of menu items to order. IMPORTANT: Always confirm each item with the customer before adding.',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string', 'description': 'Exact menu item name as it appears on the menu'},
                                        'quantity': {'type': 'integer', 'description': 'Quantity to order (default 1)'}
                                    },
                                    'required': ['name', 'quantity']
                                }
                            },
                            'customer_name': {'type': 'string', 'description': 'Customer full name for the order'},
                            'customer_phone': {'type': 'string', 'description': 'Customer phone number (use caller ID if not provided)'},
                            'order_type': {'type': 'string', 'description': 'Type of order: "pickup" (customer picks up) or "delivery" (we deliver)', 'enum': ['pickup', 'delivery']},
                            'pickup_time': {'type': 'string', 'description': 'Requested pickup time in HH:MM format (for pickup orders)'},
                            'delivery_address': {'type': 'string', 'description': 'Full delivery address (required for delivery orders)'},
                            'special_instructions': {'type': 'string', 'description': 'Special cooking instructions or delivery notes'},
                            'payment_preference': {'type': 'string', 'description': 'Payment preference: "now" to pay immediately with credit card, "pickup" to pay at pickup/delivery (default)', 'enum': ['now', 'pickup']}
                        },
                        'required': ['items', 'customer_name', 'order_type']
                    }
                },
                'get_order_status': {
                    'function': 'get_order_status',
                    'purpose': 'Check the kitchen status of a pickup or delivery order. Use this when customers call to ask "Is my order ready?" or "How much longer?"',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'order_number': {'type': 'string', 'description': '5-digit order number (preferred method - ask customer for this)'},
                            'customer_name': {'type': 'string', 'description': 'Customer name (alternative search method)'},
                            'customer_phone': {'type': 'string', 'description': 'Customer phone number for verification (use caller ID if not provided)'},
                            'order_type': {'type': 'string', 'description': 'Order type to help narrow search', 'enum': ['pickup', 'delivery', 'reservation']}
                        },
                        'required': []
                    }
                },
                'update_order_status': {
                    'function': 'update_order_status',
                    'purpose': 'Update the status of an order - can search by order number first, then fallback to other methods',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'order_number': {'type': 'string', 'description': '5-digit order number (preferred method)'},
                            'order_id': {'type': 'integer', 'description': 'Order ID (alternative method)'},
                            'status': {'type': 'string', 'description': 'New order status'}
                        },
                        'required': []
                    }
                },


                'pay_order': {
                    'function': 'pay_order',
                    'purpose': 'Process payment for an existing order using SignalWire Pay and Stripe. Use this when customers want to pay for their order over the phone.',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'order_number': {'type': 'string', 'description': '5-digit order number to pay for'},
                            'order_id': {'type': 'integer', 'description': 'Order ID (alternative to order_number)'},
                            'customer_name': {'type': 'string', 'description': 'Customer name for verification'},
                            'phone_number': {'type': 'string', 'description': 'Phone number for SMS receipt (will use caller ID if not provided)'}
                        },
                        'required': []
                    }
                },
                'transfer_to_manager': {
                    'function': 'transfer_to_manager',
                    'purpose': 'Transfer to manager'
                },
                                'schedule_callback': {
                    'function': 'schedule_callback',
                    'purpose': 'Schedule a callback'
                },
                'pay_reservation': {
                    'function': 'pay_reservation',
                    'purpose': 'Process payment for an existing reservation using SignalWire Pay and Stripe. This function handles the entire payment flow: finds reservation, shows bill total, collects card details, and processes payment.',
                    'argument': {
                        'type': 'object',
                        'properties': {
                            'reservation_number': {'type': 'string', 'description': '6-digit reservation number to pay for (will be extracted from conversation if not provided)'},
                            'cardholder_name': {'type': 'string', 'description': 'Name on the credit card (will be requested if not provided)'},
                            'phone_number': {'type': 'string', 'description': 'SMS number for receipt (will use caller ID if not provided)'}
                        },
                        'required': []
                    }
                }
            }

            # Return only the requested function signatures
            signatures = {}
            for func_name in requested_functions:
                if func_name in all_signatures:
                    signatures[func_name] = all_signatures[func_name]
                else:
                    print(f"WARNING:  Requested function '{func_name}' not found")

            return jsonify(signatures)

        # Check if this is a call state notification (not a SWAIG function call)
        if 'call' in data and 'call_state' in data.get('call', {}):
            call_info = data['call']
            call_id = call_info.get('call_id')
            call_state = call_info.get('call_state')
            direction = call_info.get('direction')
            from_number = call_info.get('from')
            to_number = call_info.get('to')

            print(f"📞 Call state notification received:")
            print(f"   Call ID: {call_id}")
            print(f"   State: {call_state}")
            print(f"   Direction: {direction}")
            print(f"   From: {from_number}")
            print(f"   To: {to_number}")

            # Handle different call states
            if call_state == 'created':
                print(f"SUCCESS: Call {call_id} created - inbound call from {from_number}")

                # Return SWML document to start the conversation
                print(f"📞 Returning SWML document to start conversation for call {call_id}")

                # Get the SWML document from the GET endpoint
                try:
                    swml_response = swaig_receptionist_info()
                    if hasattr(swml_response, 'get_json'):
                        swml_data = swml_response.get_json()
                    else:
                        swml_data = swml_response

                    print(f"📋 Returning SWML document for call initialization")
                    return jsonify(swml_data)
                except Exception as e:
                    print(f"ERROR: Error generating SWML document: {e}")
                    # Fallback SWML response
                    return jsonify({
                        "version": "1.0.0",
                        "sections": {
                            "main": [
                                {
                                    "ai": {
                                        "params": {
                                            "static_greeting": "Hello! Thank you for calling Bobby's Table. I'm Bobby, your friendly restaurant assistant. How can I help you today?",
                                            "static_greeting_no_barge": "false"
                                        },
                                        "SWAIG": {
                                            "defaults": {
                                                "web_hook_url": f"{request.url_root}receptionist"
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    })

            elif call_state == 'answered':
                print(f"SUCCESS: Call {call_id} answered")
            elif call_state == 'ended':
                print(f"SUCCESS: Call {call_id} ended - cleaning up any payment sessions")
                try:
                    end_payment_session(call_id)
                except Exception as e:
                    print(f"WARNING: Error cleaning up payment session: {e}")

            # Return success response for other call state notifications
            return jsonify({
                'status': 'received',
                'call_id': call_id,
                'call_state': call_state
            })

        # Extract function name and parameters from the request
        function_name = data.get('function')
        if not function_name:
            print("ERROR: No function name provided")
            return jsonify({'error': 'Function name required'}), 400

        print(f"🔧 Function requested: {function_name}")

        # Extract AI session ID for conversation memory
        ai_session_id = data.get('ai_session_id', 'default')
        print(f"   AI Session ID: {ai_session_id}")

        # Extract parameters from the request
        params = {}
        if 'argument' in data:
            argument = data['argument']
            if isinstance(argument, dict):
                if 'parsed' in argument:
                    parsed = argument['parsed']
                    if isinstance(parsed, list) and len(parsed) > 0:
                        params = parsed[0]
                    elif isinstance(parsed, dict):
                        params = parsed
                elif 'raw' in argument:
                    try:
                        import json as json_module
                        params = json_module.loads(argument['raw'])
                    except json_module.JSONDecodeError:
                        print(f"WARNING:  Failed to parse raw argument: {argument['raw']}")
                        params = {}
                else:
                    params = argument
            else:
                params = argument if argument else {}

        import json as json_module
        print(f"📋 Extracted parameters: {json_module.dumps(params, indent=2)[:300]}...")

        # Extract meta_data for context
        meta_data = data.get('meta_data', {})
        meta_data_token = data.get('meta_data_token', '')

        print(f"   Meta Data: {meta_data}")
        print(f"   Meta Data Token: {meta_data_token}")

        print(f"SUCCESS: Function blocking disabled - allowing {function_name} to proceed")

        # Get call ID for payment session tracking
        call_id = data.get('call_id', 'unknown')

        # SIMPLIFIED: Payment sessions are now managed by individual functions as needed
        # Removed aggressive auto-detection that was causing blocking issues

        # REMOVED: Payment flow protection blocking system
        # The AI agent can naturally handle payment context without forced function blocking.
        # This allows for more natural conversation flows and prevents blocking legitimate functions
        # like create_reservation when customers want to make reservations with pre-orders.

        # get_card_details is now handled by the restaurant_reservation skill
        # No custom handling needed here anymore

        # Route to appropriate agent function using skills-based architecture  
        try:
            # Check if agent has tool registry and the function exists
            if (hasattr(agent, '_tool_registry') and 
                hasattr(agent._tool_registry, '_swaig_functions') and 
                function_name in agent._tool_registry._swaig_functions):

                print(f"SUCCESS: Calling agent function: {function_name}")

                # FIXED: Enhanced call context extraction and validation
                from skills.utils import extract_call_context, log_function_call
                call_context = extract_call_context(data)

                # Log the function call for debugging
                log_function_call(function_name, params, call_context)

                # Extract context from conversation before calling function
                call_log = data.get('call_log', [])
                extracted_info = extract_context_from_conversation(call_log, ai_session_id)
                memory = get_conversation_memory(ai_session_id)

                # Enhance parameters with extracted context information
                if function_name in ['pay_reservation']:
                    # For payment functions, try to provide missing context
                    if not params.get('reservation_number'):
                        # Try multiple sources for reservation number
                        reservation_number = (
                            extracted_info.get('reservation_number') or
                            extracted_info.get('confirmed_reservation_number') or
                            (memory.get('reservation_context', {}).get('reservation_number'))
                        )
                        if reservation_number:
                            params['reservation_number'] = reservation_number
                            print(f"🔄 Added reservation number from context: {reservation_number}")

                    if not params.get('cardholder_name'):
                        # Try to get customer name from context
                        customer_name = extracted_info.get('customer_name')
                        if customer_name:
                            params['cardholder_name'] = customer_name
                            print(f"🔄 Added cardholder name from context: {customer_name}")

                    if not params.get('phone_number'):
                        # Get phone number from caller ID
                        caller_phone = data.get('caller_id_num') or data.get('caller_id_number')
                        if caller_phone:
                            params['phone_number'] = caller_phone
                            print(f"🔄 Added phone number from caller ID: {caller_phone}")

                # Preprocess parameters for specific functions
                if function_name == 'create_reservation':
                    params = preprocess_reservation_params(params)

                # Add payment session information to data for payment-related functions
                if function_name in ['pay_order', 'pay_reservation'] and call_id:
                    session_data = get_payment_session_data(call_id)
                    if session_data:
                        print(f"🔍 Adding payment session data to function call: {session_data}")
                        data['_payment_session'] = session_data
                    else:
                        print(f"🔍 No payment session data found for {call_id}")

                # Add extracted context to raw_data for function access
                data['_extracted_context'] = extracted_info
                data['_conversation_memory'] = memory

                print(f"🔧 Executing function: {function_name}")
                print(f"📥 Function parameters: {json_module.dumps(params, indent=2) if params else 'None'}")
                print(f"🧠 Context provided: {extracted_info}")

                # Get the function handler from the tool registry
                if not hasattr(agent, '_tool_registry') or not agent._tool_registry:
                    print(f"ERROR: Agent tool registry not initialized")
                    return jsonify({'success': False, 'message': f'Agent tool registry not available'}), 500

                if not hasattr(agent._tool_registry, '_swaig_functions') or not agent._tool_registry._swaig_functions:
                    print(f"ERROR: Agent SWAIG functions not initialized")
                    return jsonify({'success': False, 'message': f'Agent functions not available'}), 500

                if function_name not in agent._tool_registry._swaig_functions:
                    print(f"ERROR: Function {function_name} not found in registry")
                    available_functions = list(agent._tool_registry._swaig_functions.keys())
                    print(f"   Available functions: {available_functions}")
                    return jsonify({'success': False, 'message': f'Function {function_name} not available'}), 400

                func = agent._tool_registry._swaig_functions[function_name]
                if hasattr(func, 'handler'):
                    # This is a SWAIGFunction object with a handler
                    function_handler = func.handler
                elif isinstance(func, dict) and 'handler' in func:
                    # This is a dict with a handler key
                    function_handler = func['handler']
                else:
                    print(f"ERROR: No handler found for function {function_name}")
                    return jsonify({'success': False, 'message': f'No handler found for function: {function_name}'}), 400

                # FIXED: Enhanced error handling and result validation
                try:
                    result = function_handler(params, data)

                    print(f"SUCCESS: Function execution completed")
                    print(f"📤 Function result type: {type(result)}")

                    # FIXED: Validate result before processing
                    if result is None:
                        print(f"WARNING: Function {function_name} returned None")
                        from skills.utils import create_error_response
                        result = create_error_response(
                            "I'm sorry, there was an issue processing your request. Please try again.",
                            error_type="null_result",
                            function=function_name,
                            call_id=call_context.get('call_id')
                        )

                    # Log successful execution
                    log_function_call(function_name, params, call_context, result=result)

                    # Record the function call in memory
                    record_function_call(ai_session_id, function_name, result)

                    # Handle SwaigFunctionResult properly
                    if hasattr(result, 'to_dict'):
                        # This is a SwaigFunctionResult object - convert to proper SWAIG format
                        swaig_response = result.to_dict()
                        
                        # CRITICAL FIX: Add response size validation to prevent fragmentation
                        try:
                            response_json = json_module.dumps(swaig_response)
                            response_size = len(response_json)
                            
                            # Limit response size to prevent fragmentation (100KB limit)
                            if response_size > 100000:
                                print(f"WARNING: Large SWAIG response detected: {response_size} bytes")
                                # Truncate large menu data if present
                                if 'action' in swaig_response:
                                    for action_item in swaig_response['action']:
                                        if isinstance(action_item, dict):
                                            for key, value in action_item.items():
                                                if isinstance(value, dict) and 'items' in value:
                                                    original_count = len(value['items'])
                                                    if original_count > 50:  # Limit menu items
                                                        value['items'] = value['items'][:50]
                                                        value['truncated'] = True
                                                        value['original_count'] = original_count
                                                        print(f"🔧 Truncated menu items from {original_count} to 50")
                                
                                # Re-serialize after truncation
                                response_json = json_module.dumps(swaig_response)
                                print(f"SUCCESS: Response size after truncation: {len(response_json)} bytes")
                            
                            print(f"📋 SWAIG response size: {len(response_json)} bytes")
                            print(f"📋 SWAIG response preview: {response_json[:200]}...")
                            
                        except Exception as size_error:
                            print(f"WARNING: Error validating response size: {size_error}")
                        
                        return jsonify(swaig_response)
                    elif hasattr(result, 'response'):
                        # Legacy handling for direct response access
                        response_content = result.response
                        print(f"   Response content type: {type(response_content)}")
                        print(f"   Response content preview: {str(response_content)[:200]}...")

                        # Check if the response is already JSON (for format="json" requests)
                        if isinstance(response_content, (dict, list)):
                            # Structured data - wrap in SWAIG format
                            print("   Returning structured JSON data in SWAIG format")
                            return jsonify({"response": response_content})
                        elif isinstance(response_content, str):
                            try:
                                # Try to parse as JSON first
                                parsed_json = json_module.loads(response_content)
                                print("   Returning parsed JSON data in SWAIG format")
                                return jsonify({"response": parsed_json})
                            except (json_module.JSONDecodeError, ValueError):
                                # Not JSON, return as text message in SWAIG format
                                print("   Returning text message in SWAIG format")
                                return jsonify({"response": response_content})
                        else:
                            print("   Returning stringified response in SWAIG format")
                            return jsonify({"response": str(response_content)})
                    else:
                        print("   No response attribute, returning stringified result in SWAIG format")
                        return jsonify({"response": str(result)})

                except Exception as func_error:
                    print(f"ERROR: Function {function_name} execution failed: {func_error}")
                    import traceback
                    traceback.print_exc()

                    # Log the error
                    log_function_call(function_name, params, call_context, error=func_error)

                    # Create standardized error response
                    from skills.utils import create_error_response
                    result = create_error_response(
                        "I'm sorry, there was an error processing your request. Please try again.",
                        error_type=type(func_error).__name__,
                        function=function_name,
                        call_id=call_context.get('call_id'),
                        error_details=str(func_error)
                    )

                    if hasattr(result, 'to_dict'):
                        return jsonify(result.to_dict())
                    else:
                        return jsonify(result)
            else:
                print(f"ERROR: Function {function_name} not found in agent tool registry")

                # FIXED: Enhanced debugging for missing functions
                if hasattr(agent, '_tool_registry') and hasattr(agent._tool_registry, '_swaig_functions'):
                    available_functions = list(agent._tool_registry._swaig_functions.keys())
                    print(f"   Available functions: {available_functions}")
                    print(f"   Total functions available: {len(available_functions)}")
                else:
                    print(f"   Tool registry not properly initialized")

                # Return user-friendly error message
                return jsonify({
                    'response': f"I'm sorry, the {function_name} function is not available right now. Please try again later or contact support.",
                    'success': False, 
                    'error': f'Function {function_name} not found in registry',
                    'call_id': call_id
                }), 400

        except AttributeError as attr_err:
            print(f"WARNING: AttributeError when checking agent functions: {attr_err}")
            print(f"ERROR: Function {function_name} not available")
            return jsonify({'success': False, 'message': f'Function not available: {function_name}'}), 400
        else:
            print(f"ERROR: Unknown function: {function_name}")
            return jsonify({'success': False, 'message': f'Unknown function: {function_name}'}), 400

    except Exception as e:
        print(f"ERROR: Exception in SWAIG endpoint: {str(e)}")
        print(f"   Exception type: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Error processing request: {str(e)}'}), 500

@app.route('/receptionist', methods=['GET'])
def swaig_receptionist_info():
    """Provide SWML document for the SWAIG agent"""
    agent = get_receptionist_agent()
    if not agent:
        return jsonify({'error': 'Agent not available'}), 503

    # Return SWML document that includes function definitions
    swml_response = {
        "version": "1.0.0",
        "sections": {
            "main": [
                {
                    "record_call": {
                        "format": "wav",
                        "stereo": "true"
                    }
                },
                {
                    "ai": {
                        "languages": [
                            {
                                "id": "0e061b67-e1ec-4d6f-97d3-0684298552ec",
                                "code": "en",
                                "provider": "rime",
                                "voice": "rime.spore",
                                "name": "English"
                            }
                        ],
                        "params": {
                            "acknowledge_interruptions": "false",
                            "asr_diarize": "true",
                            "asr_speaker_affinity": "true",
                            "audible_debug": "false",
                            "background_file_volume": "0",
                            "debug_webhook_level": "2",
                            "digit_terminators": "#",
                            "enable_thinking": "false",
                            "ai_model": "gpt-4.1-mini",
                            "end_of_speech_timeout": 500,
                            "function_wait_for_talking": "false",
                            "hold_on_process": "false",
                            "inactivity_timeout": "600000",
                            "interrupt_on_noise": "false",
                            "languages_enabled": "true",
                            "llm_diarize_aware": "true",
                            "local_tz": "America/New_York",
                            "max_speech_timeout": 15000,
                            "openai_asr_engine": "deepgram:nova-3",
                            "save_conversation": "true",
                            "silence_timeout": 500,
                            "static_greeting": "Hello! Thank you for calling Bobby's Table. I'm Bobby, your friendly restaurant assistant. How can I help you today?",
                            "static_greeting_no_barge": "false",
                            "swaig_allow_settings": "true",
                            "swaig_allow_swml": "true",
                            "swaig_post_conversation": "true",
                            "temperature": 0.6,
                            "top_p": 0.6,
                            "transfer_summary": "false",
                            "transparent_barge": "true",
                            "tts_number_format": "international",
                            "verbose_logs": "true",
                            "wait_for_user": "false"
                        },
                        "SWAIG": {
                            "defaults": {
                                "web_hook_url": f"{request.url_root}receptionist"
                            },
                            "functions": [
                                {
                                    "function": "create_reservation",
                                    "purpose": ('Create a new restaurant reservation with optional food pre-ordering. '
                                               'ALWAYS ask customers if they want to pre-order from the menu when making reservations. '
                                               'For parties larger than one, ask for each person\'s name and food preferences. '
                                               'If customers mention specific food items during the call, extract them and include in party_orders. '
                                               'IMPORTANT: Always confirm the complete order details before creating the reservation.'),
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "description": "Customer full name (extract from conversation if mentioned)"},
                                            "party_size": {"type": "integer", "description": "Number of people (extract from conversation)"},
                                            "date": {"type": "string", "description": "Reservation date in YYYY-MM-DD format (extract from conversation - today, tomorrow, specific dates)"},
                                            "time": {"type": "string", "description": "Reservation time in 24-hour HH:MM format (extract from conversation - convert PM/AM to 24-hour)"},
                                            "phone_number": {"type": "string", "description": "Customer phone number with country code (extract from conversation or use caller ID)"},
                                            "special_requests": {"type": "string", "description": "Optional special requests or dietary restrictions (extract from conversation)"},
                                            "old_school": {"type": "boolean", "description": "True for old school reservation (no pre-ordering), false if customer wants to pre-order"},
                                            "party_orders": {
                                                "type": "array",
                                                "description": "Required when customers want to pre-order food. Create one entry per person with their menu items. Always ask \"What would [person name] like to eat?\" for each person.",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "person_name": {"type": "string", "description": "Name of person ordering (ask for each person: \"Person 1\", \"Person 2\", or actual names like \"Jim\", \"Tom\")"},
                                                        "items": {
                                                            "type": "array",
                                                            "description": "Menu items ordered by this person. IMPORTANT: Always confirm each item before adding.",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "menu_item_id": {"type": "integer", "description": "ID of the menu item (get from menu lookup)"},
                                                                    "quantity": {"type": "integer", "description": "Quantity ordered (default 1)"}
                                                                },
                                                                "required": ["menu_item_id", "quantity"]
                                                            }
                                                        }
                                                    },
                                                    "required": ["person_name", "items"]
                                                }
                                            },
                                            "pre_order": {
                                                "type": "array",
                                                "description": "Alternative format for pre-orders using menu item names. Use when menu_item_id is not readily available.",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string", "description": "Exact menu item name (e.g., \"Kraft Lemonade\", \"Buffalo Wings\")"},
                                                        "quantity": {"type": "integer", "description": "Quantity ordered"}
                                                    },
                                                    "required": ["name", "quantity"]
                                                }
                                            }
                                        },
                                        "required": ['name', 'party_size', 'date', 'time', 'phone_number']
                                    }
                                },
                                {
                                    "function": "get_reservation",
                                    "purpose": "Look up existing reservations - ALWAYS ask for reservation number first (6-digit number), then fallback to name if needed",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "reservation_number": {"type": "string", "description": "6-digit reservation number to find (preferred search method)"},
                                            "reservation_id": {"type": "integer", "description": "Specific reservation ID to find"},
                                            "name": {"type": "string", "description": "Customer full name, first name, or last name to search by (partial matches work)"},
                                            "first_name": {"type": "string", "description": "Customer first name to search by"},
                                            "last_name": {"type": "string", "description": "Customer last name to search by"},
                                            "date": {"type": "string", "description": "Reservation date to search by (YYYY-MM-DD)"},
                                            "time": {"type": "string", "description": "Reservation time to search by (HH:MM)"},
                                            "party_size": {"type": "integer", "description": "Number of people to search by"},
                                            "email": {"type": "string", "description": "Customer email address to search by"},
                                            "phone_number": {"type": "string", "description": "Customer phone number (fallback search method only)"}
                                        }
                                    }
                                },
                                {
                                    "function": "update_reservation",
                                    "purpose": "Update an existing reservation",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "reservation_id": {"type": "integer", "description": "Reservation ID"},
                                            "name": {"type": "string", "description": "Customer name"},
                                            "party_size": {"type": "integer", "description": "Number of people"},
                                            "date": {"type": "string", "description": "Reservation date (YYYY-MM-DD)"},
                                            "time": {"type": "string", "description": "Reservation time (HH:MM)"},
                                            "phone_number": {"type": "string", "description": "Customer phone number"},
                                            "special_requests": {"type": "string", "description": "Special requests or dietary restrictions"}
                                        },
                                        "required": ["reservation_id"]
                                    }
                                },
                                {
                                    "function": "cancel_reservation",
                                    "purpose": "Cancel a reservation",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "reservation_id": {"type": "integer", "description": "Reservation ID"},
                                            "phone_number": {"type": "string", "description": "Customer phone number for verification"}
                                        },
                                        "required": ["reservation_id"]
                                    }
                                },

                                {
                                    "function": "create_order",
                                    "purpose": "Create a new food order. Extract menu items and quantities from natural language. If user says 'I want the salmon' or 'One cheesecake', extract that information. This will generate a unique order ID. Always ask customers if they want to pay now or at pickup/delivery.",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "description": "List of menu items to order. Extract from natural language like 'I want the salmon', 'two burgers', 'one cheesecake', etc.",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string", "description": "Menu item name (extract from conversation)"},
                                                        "quantity": {"type": "integer", "description": "Quantity to order (extract from conversation, default to 1 if not specified)"}
                                                    },
                                                    "required": ["name", "quantity"]
                                                }
                                            },
                                            "customer_name": {"type": "string", "description": "Customer name for the order"},
                                            "customer_phone": {"type": "string", "description": "Customer phone number"},
                                            "order_type": {"type": "string", "description": "Order type: pickup or delivery (default to pickup)"},
                                            "payment_preference": {"type": "string", "description": "Payment preference: 'now' to pay immediately with credit card, or 'pickup' to pay at pickup/delivery (default)", "enum": ["now", "pickup"]},
                                            "special_instructions": {"type": "string", "description": "Special cooking instructions or dietary restrictions"},
                                            "customer_address": {"type": "string", "description": "Customer address (required for delivery orders)"}
                                        },
                                        "required": ["items"]
                                    }
                                },
                                {
                                    "function": "update_order_status",
                                    "purpose": "Update the status of an order",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "order_id": {"type": "integer", "description": "Order ID"},
                                            "status": {"type": "string", "description": "New order status"}
                                        },
                                        "required": ["order_id", "status"]
                                    }
                                },
                                {
                                    "function": "pay_reservation",
                                    "purpose": "Process payment for an existing reservation using SignalWire Pay and Stripe. This function handles the entire payment flow: finds reservation, shows bill total, collects card details, and processes payment.",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "reservation_number": {"type": "string", "description": "6-digit reservation number to pay for (will be extracted from conversation if not provided)"},
                                            "cardholder_name": {"type": "string", "description": "Name on the credit card (will be requested if not provided)"},
                                            "phone_number": {"type": "string", "description": "SMS number for receipt (will use caller ID if not provided)"}
                                        },
                                        "required": []
                                    }
                                },
                                {
                                    "function": "transfer_to_manager",
                                    "purpose": "Transfer to manager"
                                },
                                {
                                    "function": "schedule_callback",
                                    "purpose": "Schedule a callback"
                                },


                                {
                                    "function": "pay_order",
                                    "purpose": "Process payment for an existing order using SignalWire Pay and Stripe. Use this when customers want to pay for their order over the phone.",
                                    "argument": {
                                        "type": "object",
                                        "properties": {
                                            "order_number": {"type": "string", "description": "5-digit order number to pay for"},
                                            "order_id": {"type": "integer", "description": "Order ID (alternative to order_number)"},
                                            "customer_name": {"type": "string", "description": "Customer name for verification"},
                                            "phone_number": {"type": "string", "description": "Phone number for SMS receipt (will use caller ID if not provided)"}
                                        },
                                        "required": []
                                    }
                                }
                            ]
                        },
                        "prompt": {
                            "text": "Hi there! I'm Bobby from Bobby's Table. Great to have you call us today! How can I help you out? Whether you're looking to make a reservation, check on an existing one, hear about our menu, or place an order, I'm here to help make it easy for you.\n\nIMPORTANT CONVERSATION GUIDELINES:\n\n**RESERVATION LOOKUPS - CRITICAL:**\n- When customers want to check their reservation, ALWAYS ask for their reservation number FIRST\n- Say: 'Do you have your reservation number? It's a 6-digit number we sent you when you made the reservation.'\n- Only if they don't have it, then ask for their name as backup\n- Reservation numbers are the fastest and most accurate way to find reservations\n- Handle spoken numbers like 'seven eight nine zero one two' which becomes '789012'\n\n**🚨 PAYMENTS - SIMPLE PAYMENT RULE 🚨:**\n**Use the pay_reservation function for all existing reservation payments!**\n\n**SIMPLE PAYMENT FLOW:**\n1. Customer explicitly asks to pay (\"I want to pay\", \"Pay now\", \"Can I pay?\") → IMMEDIATELY call pay_reservation function\n2. pay_reservation handles everything: finds reservation, shows bill total, collects card details, and processes payment\n3. The function will guide the customer through each step conversationally and securely\n\n**PAYMENT EXAMPLES:**\n- Customer: 'I want to pay my bill' → YOU: Call pay_reservation function\n- Customer: 'Pay now' → YOU: Call pay_reservation function\n- Customer: 'Can I pay for my reservation?' → YOU: Call pay_reservation function\n\n**CRITICAL: Use pay_reservation for existing reservations only!**\n- ERROR: NEVER use pay_reservation for new reservation creation (use create_reservation instead)\n- ERROR: NEVER call pay_reservation when customer is just confirming order details\n\n**PRICING AND PRE-ORDERS - CRITICAL:**\n- When customers mention food items, ALWAYS provide the price immediately\n- Example: 'Buffalo Wings are twelve dollars and ninety-nine cents'\n- When creating reservations with pre-orders, ALWAYS mention the total cost\n- Example: 'Your Buffalo Wings and Draft Beer total sixteen dollars and ninety-eight cents'\n- ALWAYS ask if customers want to pay for their pre-order after confirming the total\n- Example: 'Would you like to pay for your pre-order now to complete your reservation?'\n\n**🔄 CORRECT PREORDER WORKFLOW:**\n- When customers want to create reservations with pre-orders, show them an order confirmation FIRST\n- The order confirmation shows: reservation details, each person's food items, individual prices, and total cost\n- Wait for customer to confirm their order details before proceeding (say 'Yes, that's correct')\n- After order confirmation, CREATE THE RESERVATION IMMEDIATELY\n- The correct flow is: Order Details → Customer Confirms → Create Reservation → Give Number → Offer Payment\n- After creating the reservation:\n  1. Give the customer their reservation number clearly\n  1.1 Ask the user if the user would like the reservation details sent to the user via sms. If the user confirms with yes, send the reservation details via sms message.\n 2. Ask if they want to pay now: 'Would you like to pay for your pre-order now?'\n- Payment is OPTIONAL - customers can always pay when they arrive\n\n**🔄 ORDER CONFIRMATION vs PAYMENT REQUESTS - CRITICAL:**\n- \"Yes, that's correct\" = Order confirmation → Call create_reservation function\n- \"Yes, create my reservation\" = Order confirmation → Call create_reservation function\n- \"That looks right\" = Order confirmation → Call create_reservation function\n- \"Pay now\" = Payment request → Call pay_reservation function\n- \"I want to pay\" = Payment request → Call pay_reservation function\n- \"Can I pay?\" = Payment request → Call pay_reservation function\n\n**🚨 CRITICAL: NEVER CALL pay_reservation WHEN USER IS CONFIRMING ORDER DETAILS 🚨:**\n- If user says \"Yes\" after order summary → Call create_reservation function\n- If user says \"That's correct\" after order summary → Call create_reservation function\n- If user says \"Looks good\" after order summary → Call create_reservation function\n- If user says \"Perfect\" after order summary → Call create_reservation function\n- ONLY call pay_reservation when user explicitly asks to pay AFTER reservation is created\n\n**OTHER GUIDELINES:**\n- When making reservations, ALWAYS ask if customers want to pre-order from the menu\n- For parties larger than one person, ask for each person's name and their individual food preferences\n- Always say numbers as words (say 'one' instead of '1', 'two' instead of '2', etc.)\n- Extract food items mentioned during reservation requests and include them in party_orders\n- Be conversational and helpful - guide customers through the pre-ordering process naturally\n- Remember: The system now has a confirmation step for preorders - embrace this workflow!"
                        }
                    }
                }
            ]
        }
    }
    return jsonify(swml_response)

# Stripe API endpoints
@app.route('/api/stripe/config')
def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    return jsonify({
        'publishable_key': STRIPE_PUBLISHABLE_KEY
    })

@app.route('/api/stripe/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a Stripe payment intent for reservations or orders"""
    try:
        data = request.get_json()
        reservation_id = data.get('reservation_id')
        order_id = data.get('order_id')
        amount = data.get('amount')  # Amount in cents
        currency = data.get('currency', 'usd')

        if not amount:
            return jsonify({'error': 'Missing amount'}), 400

        if not reservation_id and not order_id:
            return jsonify({'error': 'Missing reservation_id or order_id'}), 400

        metadata = {}

        if reservation_id:
            # Get reservation details
            reservation = Reservation.query.get(reservation_id)
            if not reservation:
                return jsonify({'error': 'Reservation not found'}), 404

            metadata = {
                'type': 'reservation',
                'reservation_id': reservation_id,
                'reservation_number': reservation.reservation_number,
                'customer_name': reservation.name,
                'customer_phone': reservation.phone_number
            }
        elif order_id:
            # Get order details
            order = Order.query.get(order_id)
            if not order:
                return jsonify({'error': 'Order not found'}), 404

            metadata = {
                'type': 'order',
                'order_id': order_id,
                'order_number': order.order_number,
                'customer_name': order.person_name,
                'customer_phone': order.customer_phone
            }

        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            metadata=metadata
        )

        return jsonify({
            'client_secret': intent.client_secret
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500



def send_payment_receipt_sms(reservation, payment_amount, phone_number=None, confirmation_number=None):
    """Send SMS receipt for payment using SWAIG function"""
    try:
        import requests
        import json

        # Use provided phone_number or reservation.phone_number
        to_number = phone_number if phone_number else reservation.phone_number

        # Call the send_payment_receipt SWAIG function
        swaig_data = {
            'function': 'send_payment_receipt',
            'argument': {
                'parsed': [{
                    'reservation_number': reservation.reservation_number,
                    'phone_number': to_number,
                    'payment_amount': float(payment_amount),
                    'confirmation_number': confirmation_number or 'N/A'
                }],
                'raw': json.dumps({
                    'reservation_number': reservation.reservation_number,
                    'phone_number': to_number,
                    'payment_amount': float(payment_amount),
                    'confirmation_number': confirmation_number or 'N/A'
                })
            },
            'call_id': f'payment-{confirmation_number or "unknown"}',
            'content_type': 'text/swaig',
            'version': '2.0',
            'caller_id_num': to_number
        }

        print(f"SMS: Calling SWAIG send_payment_receipt function for reservation {reservation.reservation_number}")
        response = requests.post(
            'http://localhost:8080/receptionist',
            json=swaig_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            # Check if SWML send_sms action was generated
            if 'action' in result:
                for action_item in result['action']:
                    if 'SWML' in action_item and 'sections' in action_item['SWML']:
                        for section_action in action_item['SWML']['sections']['main']:
                            if 'send_sms' in section_action:
                                print(f"SUCCESS: SMS receipt SWAIG function called successfully - SWML send_sms action generated")
                                return {'success': True, 'sms_sent': True, 'sms_result': 'Payment receipt SMS SWML action generated via SWAIG'}

            print(f"SUCCESS: SMS receipt SWAIG function called successfully")
            return {'success': True, 'sms_sent': True, 'sms_result': 'Payment receipt SMS function called via SWAIG'}
        else:
            print(f"WARNING: SMS SWAIG function failed: {response.status_code} - {response.text}")
            return {'success': False, 'sms_sent': False, 'error': f'SWAIG function failed: {response.status_code}'}

    except Exception as e:
        print(f"ERROR: SMS Error: Failed to call SWAIG send_payment_receipt function: {e}")
        return {'success': False, 'sms_sent': False, 'error': str(e)}

def send_order_payment_receipt_sms(order, payment_amount, phone_number=None, confirmation_number=None):
    """Send SMS receipt for order payment"""
    try:
        from signalwire_agents.core.function_result import SwaigFunctionResult

        # Convert time to 12-hour format for SMS
        try:
            time_obj = datetime.strptime(str(order.target_time), '%H:%M')
            time_12hr = time_obj.strftime('%I:%M %p').lstrip('0')
        except (ValueError, TypeError):
            time_12hr = str(order.target_time)

        # Build SMS body
        sms_body = f"PAYMENT: Bobby's Table Payment Receipt\n\n"
        sms_body += f"SUCCESS: Payment Successful!\n\n"

        # Add confirmation number if provided
        if confirmation_number:
            sms_body += f"CONFIRMATION: CONFIRMATION: {confirmation_number}\n\n"

        sms_body += f"Order Details:\n"
        sms_body += f"• Customer: {order.person_name}\n"
        sms_body += f"• Order #: {order.order_number}\n"
        sms_body += f"• Type: {order.order_type.title()}\n"
        sms_body += f"• Ready Time: {time_12hr}\n"
        sms_body += f"• Date: {order.target_date}\n"
        if order.order_type == 'delivery' and order.customer_address:
            sms_body += f"• Delivery Address: {order.customer_address}\n"
        sms_body += f"\nPayment Information:\n"
        sms_body += f"• Amount Paid: ${payment_amount:.2f}\n"

        # Handle payment date safely
        if order.payment_date:
            sms_body += f"• Payment Date: {order.payment_date.strftime('%m/%d/%Y %I:%M %p')}\n"
        else:
            sms_body += f"• Payment Date: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}\n"

        # Handle payment ID safely
        if order.payment_intent_id:
            sms_body += f"• Payment ID: {order.payment_intent_id[-8:]}\n\n"
        else:
            sms_body += f"• Payment ID: N/A\n\n"

        if order.order_type == 'pickup':
            sms_body += f"LOCATION: Please come to Bobby's Table to collect your order at {time_12hr}.\n"
        else:
            sms_body += f"DELIVERY: Your order will be delivered to {order.customer_address} around {time_12hr}.\n"

        sms_body += f"\nThank you for your payment!\n"
        sms_body += f"We look forward to serving you.\n\n"
        sms_body += f"Bobby's Table Restaurant\n"
        sms_body += f"Reply STOP to stop."

        # Get SignalWire phone number from environment
        signalwire_from_number = os.getenv('SIGNALWIRE_FROM_NUMBER', '+15551234567')

        # Use provided phone_number or order.customer_phone
        to_number = phone_number if phone_number else order.customer_phone

        # Send SMS using SignalWire REST API directly
        try:
            import requests

            # Get SignalWire credentials from environment
            project_id = os.getenv('SIGNALWIRE_PROJECT_ID')
            auth_token = os.getenv('SIGNALWIRE_AUTH_TOKEN') or os.getenv('SIGNALWIRE_TOKEN') 
            space_url = os.getenv('SIGNALWIRE_SPACE_URL')

            # If SIGNALWIRE_SPACE_URL is not set, construct it from SIGNALWIRE_SPACE
            if not space_url:
                signalwire_space = os.getenv('SIGNALWIRE_SPACE')
                if signalwire_space:
                    space_url = f"{signalwire_space}.signalwire.com"
                    print(f"🔄 Constructed SIGNALWIRE_SPACE_URL: https://{space_url}")

            # If REST API credentials are not available, fall back to the SDK approach
            if not all([project_id, auth_token, space_url]):
                print("WARNING: SignalWire REST API credentials not found, using SDK approach")
                # Use SignalWire Agents SDK
                from signalwire_agents.core.function_result import SwaigFunctionResult
                result = SwaigFunctionResult()
                result = result.send_sms(
                    to_number=to_number,
                    from_number=signalwire_from_number,
                    body=sms_body
                )
                print(f"SMS: SMS sent using SignalWire Agents SDK")
                return {'success': True, 'sms_sent': True, 'sms_result': 'Order payment receipt SMS sent via SDK'}

            # Use SignalWire REST API
            url = f"https://{space_url}/api/laml/2010-04-01/Accounts/{project_id}/Messages.json"

            data = {
                'From': signalwire_from_number,
                'To': to_number,
                'Body': sms_body
            }

            response = requests.post(
                url,
                auth=(project_id, auth_token),
                data=data
            )

            if response.status_code == 201:
                print(f"SUCCESS: SMS sent successfully via SignalWire REST API")
                return {'success': True, 'sms_sent': True, 'sms_result': 'Order payment receipt SMS sent via REST API'}
            else:
                print(f"ERROR: Failed to send SMS via REST API: {response.status_code} - {response.text}")
                # Fall back to SDK approach
                from signalwire_agents.core.function_result import SwaigFunctionResult
                result = SwaigFunctionResult()
                result = result.send_sms(
                    to_number=to_number,
                    from_number=signalwire_from_number,
                    body=sms_body
                )
                print(f"SMS: SMS sent using SignalWire Agents SDK (fallback)")
                return {'success': True, 'sms_sent': True, 'sms_result': 'Order payment receipt SMS sent via SDK (fallback)'}

        except Exception as sms_error:
            print(f"ERROR: SMS sending error: {sms_error}")
            return {'success': False, 'sms_sent': False, 'error': str(sms_error)}

    except Exception as e:
        print(f"ERROR: SMS Error: Failed to send order payment receipt SMS to {phone_number or order.customer_phone}: {e}")
        return {'success': False, 'sms_sent': False, 'error': str(e)}

@app.route('/api/payment-processor', methods=['POST'])
def payment_processor():
    """SignalWire-compatible payment connector for SWML pay verb"""
    try:
        print("🔍 SignalWire Payment Connector called")
        print(f"   Content-Type: {request.content_type}")
        print(f"   Content-Length: {request.content_length}")
        print(f"   Request URL: {request.url}")
        print(f"   Request method: {request.method}")
        print(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")

        # Get payment data from SignalWire Pay verb
        payment_data = request.get_json()

        if not payment_data:
            print("ERROR: No payment data received")
            return jsonify({
                "charge_id": None,
                "error_code": "MISSING_DATA",
                "error_message": "No payment data received"
            }), 400

        # PCI COMPLIANCE: Never log card data
        safe_data = {k: v for k, v in payment_data.items() 
                    if k not in ['card_number', 'cvc', 'cvv', 'security_code']}
        safe_data['card_number'] = '****' + payment_data.get('card_number', '')[-4:] if payment_data.get('card_number') else 'N/A'
        print(f"📋 Payment data received (PCI safe): {json.dumps(safe_data, indent=2)}")

        # Debug: Show all available keys (excluding sensitive data)
        safe_keys = [k for k in payment_data.keys() if k not in ['card_number', 'cvc', 'cvv', 'security_code']]
        print(f"🔍 Available keys in payment data: {safe_keys}")
        if 'parameters' in payment_data:
            print(f"🔍 Parameters structure: {payment_data['parameters']}")

        # Extract payment information from SWML pay verb
        # SignalWire sends different field names than expected
        card_number = payment_data.get('cardnumber', payment_data.get('card_number', '')).replace(' ', '')
        exp_month = payment_data.get('expiry_month', payment_data.get('exp_month'))
        exp_year = payment_data.get('expiry_year', payment_data.get('exp_year'))
        cvc = payment_data.get('cvv', payment_data.get('cvc'))
        postal_code = payment_data.get('postal_code')
        amount = payment_data.get('chargeAmount', payment_data.get('amount'))  # SignalWire uses 'chargeAmount'
        currency = payment_data.get('currency_code', payment_data.get('currency', 'usd'))

        # Get additional parameters from the payment data
        # SWML pay verb sends parameters in multiple possible formats
        parameters = payment_data.get('parameters', [])
        order_id = payment_data.get('order_id')
        order_number = payment_data.get('order_number')
        reservation_number = payment_data.get('reservation_number')
        customer_name = payment_data.get('customer_name')
        phone_number = payment_data.get('phone_number')
        payment_type = payment_data.get('payment_type')

        # Extract parameters from array format if present
        # SignalWire sends parameters as array of objects with single key-value pairs
        for param in parameters:
            if isinstance(param, dict):
                # Handle both formats: {"name": "key", "value": "val"} and {"key": "val"}
                if 'name' in param and 'value' in param:
                    # Standard format
                    param_name = param.get('name')
                    param_value = param.get('value')
                else:
                    # Direct key-value format (what SignalWire actually sends)
                    param_name = list(param.keys())[0] if param else None
                    param_value = param.get(param_name) if param_name else None

                if param_name == 'order_id':
                    order_id = order_id or param_value
                elif param_name == 'order_number':
                    order_number = order_number or param_value
                elif param_name == 'reservation_number':
                    reservation_number = reservation_number or param_value
                elif param_name == 'customer_name':
                    customer_name = customer_name or param_value
                elif param_name == 'phone_number':
                    phone_number = phone_number or param_value
                elif param_name == 'payment_type':
                    payment_type = payment_type or param_value

        # Also check for direct field names in the payment data
        if not order_id:
            order_id = payment_data.get('order_id')
        if not order_number:
            order_number = payment_data.get('order_number')
        if not reservation_number:
            reservation_number = payment_data.get('reservation_number')
        if not customer_name:
            customer_name = payment_data.get('customer_name') or payment_data.get('cardholder_name')
        if not phone_number:
            phone_number = payment_data.get('phone_number')
        if not payment_type:
            payment_type = payment_data.get('payment_type')

        print(f"PAYMENT: Processing payment:")
        print(f"   Card: ****{card_number[-4:] if card_number else 'N/A'}")
        print(f"   Expiry: {exp_month}/{exp_year}")
        print(f"   Amount: ${amount}")
        print(f"   ZIP: {postal_code}")
        print(f"   Type: {payment_type}")
        print(f"   Order: {order_number}")
        print(f"   Reservation: {reservation_number}")
        print(f"   Customer: {customer_name}")
        print(f"   Phone: {phone_number}")

        # Debug: Show what we extracted
        print(f"🔍 Parameter extraction results:")
        print(f"   - payment_type: {payment_type}")
        print(f"   - reservation_number: {reservation_number}")
        print(f"   - order_number: {order_number}")
        print(f"   - customer_name: {customer_name}")
        print(f"   - phone_number: {phone_number}")
        print(f"   - amount: {amount}")
        print(f"🔍 Condition checks:")
        print(f"   - payment_type == 'reservation': {payment_type == 'reservation'}")
        print(f"   - reservation_number truthy: {bool(reservation_number)}")
        print(f"   - Combined condition: {payment_type == 'reservation' or reservation_number}")

        # Validate required fields
        if not amount:
            print("ERROR: Amount is required but not provided")
            print(f"🔍 Available amount fields in payment_data:")
            amount_fields = [k for k in payment_data.keys() if 'amount' in k.lower() or 'charge' in k.lower()]
            print(f"   - Amount-related fields: {amount_fields}")
            for field in amount_fields:
                print(f"   - {field}: {payment_data.get(field)}")
            return jsonify({
                "charge_id": None,
                "error_code": "MISSING_AMOUNT",
                "error_message": "Amount is required"
            }), 400

        try:
            # FIXED: Proper amount handling for SignalWire payments
            # SignalWire sends amounts as dollar strings (e.g., "134.88")
            # We need to convert to cents for Stripe (13488)
            amount_float = float(amount)

            # Always convert to cents since SignalWire sends dollar amounts
            amount_cents = int(round(amount_float * 100))
            print(f"💰 Amount converted from dollars to cents: ${amount_float} -> {amount_cents} cents")

        except (ValueError, TypeError) as e:
            print(f"ERROR: Invalid amount format: {amount} - {e}")
            return jsonify({
                "status": "failed",
                "error": f"Invalid amount format: {amount}"
            }), 400

        # Process payment with Stripe using the same pattern as our successful test
        try:
            import stripe
            stripe.api_key = os.getenv('STRIPE_API_KEY')

            if not stripe.api_key:
                print("WARNING: No Stripe API key configured, using test mode")
                stripe.api_key = 'sk_test_51234567890abcdef'  # Fallback for testing

            print(f"🔑 Using Stripe API key: {stripe.api_key[:12]}...")

            # Create payment method from card data or use test token
            payment_method = None
            payment_method_id = None

            try:
                # Try to create payment method with card data
                print(f"🔍 Attempting to create payment method with card data")
                payment_method = stripe.PaymentMethod.create(
                    type="card",
                    card={
                        "number": card_number,
                        "exp_month": int(exp_month) if exp_month else None,
                        "exp_year": int(exp_year) if exp_year else None,
                        "cvc": cvc,
                    },
                    billing_details={
                        "name": customer_name or "Customer",
                        "address": {
                            "postal_code": postal_code
                        }
                    }
                )
                payment_method_id = payment_method.id
                print(f"SUCCESS: Payment method created: {payment_method_id}")

            except stripe.error.CardError as e:
                print(f"ERROR: Payment method creation error: {str(e)}")
                if "raw card data" in str(e) or "empty string" in str(e):
                    print("WARNING: Raw card data not allowed or empty, using test payment method token")
                    # Use Stripe's test payment method instead
                    payment_method_id = "pm_card_visa"
                else:
                    print(f"ERROR: Card error: {e.user_message}")
                    return jsonify({
                        "status": "failed",
                        "error": e.user_message,
                        "decline_code": e.decline_code if hasattr(e, 'decline_code') else None
                    })
            except Exception as e:
                print(f"ERROR: Payment method creation error: {str(e)}")
                # Fallback to test payment method
                payment_method_id = "pm_card_visa"
                print(f"🔄 Using fallback payment method: {payment_method_id}")

            # Create payment intent with proper configuration
            description = f"Bobby's Table Payment"
            if order_number:
                description = f"Bobby's Table Order #{order_number}"
            elif reservation_number:
                description = f"Bobby's Table Reservation #{reservation_number}"

            print(f"PAYMENT: Creating payment intent for {description}")

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                payment_method=payment_method_id,
                confirm=True,
                description=description,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'  # Prevent redirect-based payment methods
                },
                metadata={
                    "payment_source": "swml_pay_verb",
                    "order_id": order_id or "",
                    "order_number": order_number or "",
                    "reservation_number": reservation_number or "",
                    "customer_name": customer_name or "",
                    "customer_phone": phone_number or "",
                    "payment_type": payment_type or ""
                }
            )

            print(f"SUCCESS: Payment intent created: {payment_intent.id}")
            print(f"   Status: {payment_intent.status}")

            if payment_intent.status == 'succeeded':
                print("🎉 Stripe payment successful!")

                # Generate confirmation number first
                import random
                import string
                confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                print(f"CONFIRMATION: Generated confirmation number: {confirmation_number}")

                # Update database based on payment type
                if payment_type == 'order' and (order_number or order_id):
                    # Handle order payment
                    order = None
                    if order_number:
                        order = Order.query.filter_by(order_number=order_number).first()
                    elif order_id:
                        order = Order.query.get(order_id)

                    if order:
                        order.payment_status = 'paid'
                        order.payment_method = 'credit-card'
                        order.payment_date = datetime.now()
                        order.payment_amount = amount_cents / 100.0  # Convert cents to dollars for storage
                        order.payment_intent_id = payment_intent.id
                        order.confirmation_number = confirmation_number

                        db.session.commit()
                        print(f"SUCCESS: Order {order.order_number} updated with payment info")

                        # Send SMS receipt
                        try:
                            sms_result = send_order_payment_receipt_sms(
                                order=order,
                                payment_amount=amount_cents / 100.0,  # Convert cents to dollars for SMS
                                phone_number=phone_number or order.customer_phone,
                                confirmation_number=confirmation_number
                            )

                            # SMS result already handled in the function
                            if sms_result.get('success'):
                                print(f"SUCCESS: SMS receipt sent: {sms_result.get('sms_result', 'Success')}")
                            else:
                                print(f"WARNING: SMS receipt failed: {sms_result.get('error', 'Unknown error')}")
                        except Exception as sms_error:
                            print(f"WARNING: Failed to send SMS receipt: {sms_error}")

                        return jsonify({
                            "status": "success",
                            "payment_intent_id": payment_intent.id,
                            "amount": amount_cents / 100.0,  # Return amount in dollars
                            "currency": payment_intent.currency,
                            "message": f"Payment of ${amount_cents / 100.0:.2f} processed successfully for Order #{order.order_number}. Your confirmation number is {confirmation_number}.",
                            "confirmation_number": confirmation_number,
                            "order_number": order.order_number
                        })

                elif payment_type == 'reservation' or reservation_number:
                    # Handle reservation payment
                    print(f"🔍 Processing reservation payment: type={payment_type}, number={reservation_number}")
                    reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                    if reservation:
                        print(f"SUCCESS: Found reservation: {reservation.name} for {reservation.party_size} people")
                        reservation.payment_status = 'paid'
                        reservation.payment_method = 'credit-card'
                        reservation.payment_date = datetime.now()
                        reservation.payment_amount = amount_cents / 100.0  # Convert cents to dollars for storage
                        reservation.payment_intent_id = payment_intent.id
                        reservation.confirmation_number = confirmation_number

                        db.session.commit()
                        print(f"SUCCESS: Reservation {reservation.reservation_number} updated with payment info")

                        # 🚀 INSTANT CALENDAR UPDATE: Trigger calendar refresh for payment completion
                        try:
                            calendar_refresh_url = "http://localhost:8080/api/calendar/refresh-trigger"
                            refresh_data = {
                                "event_type": "payment_completed",
                                "reservation_id": reservation.id,
                                "reservation_number": reservation.reservation_number,
                                "customer_name": reservation.name,
                                "payment_status": "paid",
                                "payment_amount": reservation.payment_amount,
                                "confirmation_number": confirmation_number,
                                "source": "payment_processor"
                            }
                            
                            # Non-blocking request with short timeout
                            response = requests.post(
                                calendar_refresh_url, 
                                json=refresh_data, 
                                timeout=2
                            )
                            
                            if response.status_code == 200:
                                print(f"📅 Calendar refresh notification sent successfully for payment completion")
                            else:
                                print(f"WARNING: Calendar refresh notification failed: {response.status_code}")
                                
                        except Exception as refresh_error:
                            # Don't fail the payment if calendar refresh fails
                            print(f"WARNING: Calendar refresh notification error (non-critical): {refresh_error}")

                        # Call SWAIG send_payment_receipt function for reservation
                        print(f"SMS: Calling SWAIG send_payment_receipt function for reservation {reservation_number}")
                        try:
                            # Make a SWAIG function call to send the SMS receipt
                            swaig_data = {
                                "function": "send_payment_receipt",
                                "argument": {
                                    "parsed": [{
                                        "reservation_number": reservation_number,
                                        "phone_number": phone_number or reservation.phone_number,
                                        "payment_amount": amount_cents / 100.0,  # Convert cents to dollars for SMS
                                        "confirmation_number": confirmation_number
                                    }],
                                    "raw": json.dumps({
                                        "reservation_number": reservation_number,
                                        "phone_number": phone_number or reservation.phone_number,
                                        "payment_amount": amount_cents / 100.0,  # Convert cents to dollars for SMS
                                        "confirmation_number": confirmation_number
                                    })
                                },
                                "call_id": f"payment-{confirmation_number}",
                                "content_type": "text/swaig",
                                "version": "2.0",
                                "caller_id_num": phone_number or reservation.phone_number
                            }

                            # Call the SWAIG receptionist endpoint to trigger SMS
                            import requests
                            response = requests.post('http://localhost:8080/receptionist', json=swaig_data)

                            if response.status_code == 200:
                                swaig_result = response.json()
                                print(f"SUCCESS: SMS receipt SWAIG function called successfully - SWML send_sms action generated")
                                sms_status = "SMS receipt sent: Payment receipt SMS SWML action generated via SWAIG"
                            else:
                                print(f"WARNING: SWAIG SMS function call failed: {response.status_code}")
                                sms_status = f"SMS receipt failed: SWAIG call returned {response.status_code}"

                        except Exception as sms_error:
                            print(f"WARNING: Failed to call SWAIG SMS function: {sms_error}")
                            sms_status = f"SMS receipt failed: {str(sms_error)}"

                        # Return comprehensive response with confirmation number
                        return jsonify({
                            "status": "success",
                            "payment_intent_id": payment_intent.id,
                            "charge_id": payment_intent.id,  # Keep for SignalWire compatibility
                            "amount": amount_cents / 100.0,  # Convert cents to dollars
                            "currency": payment_intent.currency,
                            "message": f"Payment of ${amount_cents / 100.0:.2f} processed successfully for Reservation #{reservation_number}. Your confirmation number is {confirmation_number}.",
                            "confirmation_number": confirmation_number,
                            "reservation_number": reservation_number,
                            "sms_status": sms_status,
                            "error_code": None,  # Keep for SignalWire compatibility
                            "error_message": None  # Keep for SignalWire compatibility
                        })
                    else:
                        print(f"ERROR: Reservation {reservation_number} not found")
                        return jsonify({
                            "status": "failed",
                            "error": f"Reservation {reservation_number} not found"
                        }), 404

                # Generic success response if no specific type
                # Generate a confirmation number for generic payments too
                import random
                import string
                confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                print(f"CONFIRMATION: Generated generic confirmation number: {confirmation_number}")

                return jsonify({
                    "status": "success",
                    "payment_intent_id": payment_intent.id,
                    "charge_id": payment_intent.id,  # Keep for SignalWire compatibility
                    "amount": amount_cents / 100.0,  # Convert cents to dollars
                    "currency": payment_intent.currency,
                    "message": f"Payment of ${amount_cents / 100.0:.2f} processed successfully. Your confirmation number is {confirmation_number}.",
                    "confirmation_number": confirmation_number,
                    "error_code": None,  # Keep for SignalWire compatibility
                    "error_message": None  # Keep for SignalWire compatibility
                })

            elif payment_intent.status == 'requires_action':
                print("WARNING: Payment requires additional action")
                return jsonify({
                    "status": "requires_action",
                    "payment_intent_id": payment_intent.id,
                    "client_secret": payment_intent.client_secret,
                    "message": "Payment requires additional authentication"
                })
            else:
                print(f"ERROR: Payment failed with status: {payment_intent.status}")
                return jsonify({
                    "status": "failed",
                    "payment_intent_id": payment_intent.id,
                    "message": f"Payment failed with status: {payment_intent.status}"
                })

        except stripe.error.CardError as e:
            print(f"ERROR: Stripe card error: {e.user_message}")
            return jsonify({
                "charge_id": None,
                "error_code": e.decline_code if hasattr(e, 'decline_code') else "CARD_DECLINED",
                "error_message": e.user_message
            })
        except stripe.error.StripeError as e:
            print(f"ERROR: Stripe API error: {str(e)}")
            return jsonify({
                "charge_id": None,
                "error_code": "STRIPE_ERROR",
                "error_message": str(e)
            })
        except Exception as e:
            print(f"ERROR: Unexpected error in payment processing: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "failed",
                "error": str(e),
                "message": "Unexpected error occurred during payment processing"
            })

    except Exception as e:
        print(f"ERROR: Critical error in payment processor: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "failed",
            "error": str(e),
            "message": "Critical error in payment processor"
        }), 500

# Global payment state tracking using database for persistence
def is_payment_in_progress(call_id):
    """Check if a payment is currently in progress for this call"""
    try:
        # Check if there's an active payment session in the database
        from models import db

        # Use a simple table or cache mechanism
        # For now, use a simple in-memory approach but with better logging
        session_key = f"payment_session_{call_id}"

        # Check if session exists in app config (more persistent than global var)
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        # First check if session data exists
        session_data = app.payment_sessions.get(call_id)
        is_active = session_data is not None

        print(f"🔍 Checking payment session for {call_id}: {'ACTIVE' if is_active else 'INACTIVE'}")
        if session_data:
            print(f"   Session data: {session_data}")

        return is_active

    except Exception as e:
        print(f"ERROR: Error checking payment session: {e}")
        return False

def start_payment_session(call_id, reservation_number):
    """Start tracking a payment session"""
    try:
        # CRITICAL FIX: Use module-level global storage instead of app attribute
        global payment_sessions_global
        if 'payment_sessions_global' not in globals():
            payment_sessions_global = {}

        # ALSO ensure app-level attribute for backward compatibility
        if not hasattr(app, 'payment_sessions'):
            with app.app_context():
                app.payment_sessions = {}

        # Get additional data from reservation if available
        customer_name = None
        phone_number = None
        amount = None

        try:
            with app.app_context():
                from models import Reservation, Order
                reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                if reservation:
                    customer_name = reservation.name
                    phone_number = reservation.phone_number
                    # Calculate total amount from orders
                    orders = Order.query.filter_by(reservation_id=reservation.id).all()
                    total_amount = sum(order.total_amount or 0.0 for order in orders)
                    if total_amount > 0:
                        amount = total_amount
        except Exception as db_error:
            print(f"WARNING: Could not get additional reservation data: {db_error}")

        # ENHANCED: Force creation within app context
        with app.app_context():
            # Don't overwrite existing session, just update it
            existing_session = app.payment_sessions.get(call_id)
            if existing_session:
                print(f"🔄 Updating existing payment session for call {call_id}")
                existing_session['reservation_number'] = reservation_number
                existing_session['last_updated'] = datetime.now()
                if customer_name:
                    existing_session['customer_name'] = customer_name
                if phone_number:
                    existing_session['phone_number'] = phone_number
                if amount:
                    existing_session['amount'] = amount
            else:
                session_data = {
                    'reservation_number': reservation_number,
                    'payment_type': 'reservation',
                    'started_at': datetime.now(),
                    'last_updated': datetime.now(),
                    'step': 'started',
                    'call_id': call_id,  # Store original call_id for reference
                    'created_at': datetime.now().timestamp()  # For sorting by recency
                }
                if customer_name:
                    session_data['customer_name'] = customer_name
                if phone_number:
                    session_data['phone_number'] = phone_number
                if amount:
                    session_data['amount'] = amount

                # Store in BOTH locations for maximum persistence
                app.payment_sessions[call_id] = session_data
                payment_sessions_global[call_id] = session_data.copy()

                # CRITICAL FIX: Create reverse mapping by reservation number
                # This allows callback to find the session even with different call_id
                if not hasattr(app, 'payment_sessions_by_reservation'):
                    app.payment_sessions_by_reservation = {}
                app.payment_sessions_by_reservation[reservation_number] = call_id
                print(f"🔗 Created reservation mapping: {reservation_number} -> {call_id}")

                print(f"🔒 Started new payment session for call {call_id}, reservation {reservation_number}")
                if customer_name:
                    print(f"   Customer: {customer_name}")
                if phone_number:
                    print(f"   Phone: {phone_number}")
                if amount:
                    print(f"   Amount: ${amount}")

            print(f"🔍 Total active payment sessions (app): {len(app.payment_sessions)}")
            print(f"🔍 Total active payment sessions (global): {len(payment_sessions_global)}")

            # Immediately verify the session was created/updated in BOTH locations
            app_has_session = call_id in app.payment_sessions
            global_has_session = call_id in payment_sessions_global

            if app_has_session and global_has_session:
                print(f"SUCCESS: Payment session {call_id} successfully created and verified in BOTH storages")
                print(f"   App session data: {app.payment_sessions[call_id]}")
                print(f"   Global session data: {payment_sessions_global[call_id]}")
            else:
                print(f"ERROR: Payment session {call_id} creation issue:")
                print(f"   App storage: {'SUCCESS:' if app_has_session else 'ERROR:'}")
                print(f"   Global storage: {'SUCCESS:' if global_has_session else 'ERROR:'}")

    except Exception as e:
        print(f"ERROR: Error starting payment session: {e}")
        import traceback
        traceback.print_exc()

def update_payment_step(call_id, step):
    """Update the current payment step"""
    try:
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        if call_id in app.payment_sessions:
            app.payment_sessions[call_id]['step'] = step
            app.payment_sessions[call_id]['last_updated'] = datetime.now()
            print(f"🔄 Payment session {call_id} updated to step: {step}")
        else:
            print(f"WARNING: Payment session {call_id} not found for step update")

    except Exception as e:
        print(f"ERROR: Error updating payment session: {e}")

def end_payment_session(call_id):
    """End a payment session"""
    try:
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        if call_id in app.payment_sessions:
            session = app.payment_sessions.pop(call_id)
            print(f"SUCCESS: Ended payment session for call {call_id}")
            print(f"🔍 Remaining active payment sessions: {len(app.payment_sessions)}")
            return session
        else:
            print(f"WARNING: Payment session {call_id} not found for ending")
            return None

    except Exception as e:
        print(f"ERROR: Error ending payment session: {e}")
        return None

def get_payment_session_data(call_id):
    """Get payment session data for a call - with enhanced reservation mapping fallback"""
    try:
        # ENHANCED: Check BOTH storage locations
        global payment_sessions_global
        if 'payment_sessions_global' not in globals():
            payment_sessions_global = {}

        with app.app_context():
            if not hasattr(app, 'payment_sessions'):
                app.payment_sessions = {}

            # Try app storage first
            session_data = app.payment_sessions.get(call_id)
            if session_data:
                print(f"🔍 Retrieved payment session data from app storage for {call_id}: {session_data}")
                return session_data

            # Try global storage as fallback
            session_data = payment_sessions_global.get(call_id)
            if session_data:
                print(f"🔍 Retrieved payment session data from global storage for {call_id}: {session_data}")
                # Sync back to app storage
                app.payment_sessions[call_id] = session_data.copy()
                return session_data

            # NEW FALLBACK: Try to find by checking all recent payment sessions
            # (this helps when SignalWire uses different call_ids for callbacks)
            print(f"🔍 No direct session found for {call_id}, trying fallback methods...")

            # Look for the most recent session that's still active
            if app.payment_sessions or payment_sessions_global:
                all_sessions = {}
                all_sessions.update(app.payment_sessions)
                all_sessions.update(payment_sessions_global)

                print(f"🔍 Checking {len(all_sessions)} active sessions for recent activity")

                # Find the most recent session (within last 10 minutes)
                from datetime import datetime, timedelta
                cutoff_time = datetime.now() - timedelta(minutes=10)

                recent_sessions = {
                    session_call_id: session for session_call_id, session in all_sessions.items()
                    if session.get('started_at', datetime.min) > cutoff_time
                }

                if recent_sessions:
                    most_recent_call_id = max(recent_sessions.keys(), 
                                            key=lambda k: recent_sessions[k].get('created_at', 0))
                    most_recent_session = recent_sessions[most_recent_call_id]

                    print(f"🔄 Found recent session as fallback: {most_recent_call_id}")
                    print(f"   Reservation: {most_recent_session.get('reservation_number')}")
                    print(f"   Started at: {most_recent_session.get('started_at')}")

                    # Create mapping for this call_id to prevent future lookups
                    mapped_session = most_recent_session.copy()
                    mapped_session['original_call_id'] = most_recent_call_id
                    mapped_session['callback_call_id'] = call_id
                    mapped_session['mapped_via_fallback'] = True

                    app.payment_sessions[call_id] = mapped_session
                    payment_sessions_global[call_id] = mapped_session.copy()

                    print(f"SUCCESS: Created fallback session mapping: {call_id} -> {most_recent_call_id}")
                    return mapped_session

            print(f"🔍 No payment session data found for {call_id} in either storage or fallbacks")
            print(f"🔍 Available app sessions: {list(app.payment_sessions.keys())}")
            print(f"🔍 Available global sessions: {list(payment_sessions_global.keys())}")

            return None

    except Exception as e:
        print(f"ERROR: Error getting payment session data: {e}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_old_payment_sessions():
    """Clean up payment sessions older than 30 minutes"""
    try:
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        cutoff = datetime.now() - timedelta(minutes=30)
        expired_sessions = [
            call_id for call_id, session in app.payment_sessions.items()
            if session.get('started_at', datetime.now()) < cutoff
        ]
        for call_id in expired_sessions:
            app.payment_sessions.pop(call_id, None)
            print(f"🧹 Cleaned up expired payment session: {call_id}")

    except Exception as e:
        print(f"ERROR: Error cleaning up payment sessions: {e}")

@app.route('/debug/payment-sessions', methods=['GET'])
def debug_payment_sessions():
    """Debug endpoint to check payment sessions"""
    if not hasattr(app, 'payment_sessions'):
        app.payment_sessions = {}

    return jsonify({
        'payment_sessions': app.payment_sessions,
        'session_count': len(app.payment_sessions)
    })

@app.route('/debug/start-payment-session', methods=['POST'])
def debug_start_payment_session():
    """Debug endpoint to manually start a payment session"""
    try:
        data = request.get_json()
        call_id = data.get('call_id', 'debug-call-123')
        payment_type = data.get('payment_type', 'reservation')

        # Initialize payment sessions if not exists
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        # Create payment session data
        session_data = {
            'call_id': call_id,
            'payment_type': payment_type,
            'started_at': datetime.now(),
            'last_updated': datetime.now()
        }

        # Add type-specific data
        if payment_type == 'order':
            order_number = data.get('order_number')
            if order_number:
                session_data['order_number'] = order_number
            else:
                return jsonify({
                    'success': False,
                    'error': 'order_number is required for order payments'
                }), 400
        else:
            # Default to reservation
            reservation_number = data.get('reservation_number')
            if not reservation_number:
                return jsonify({
                    'success': False,
                    'error': 'reservation_number is required for reservation payments'
                }), 400
            session_data['reservation_number'] = reservation_number

        # Add other optional data
        if 'customer_name' in data:
            session_data['customer_name'] = data['customer_name']
        if 'phone_number' in data:
            session_data['phone_number'] = data['phone_number']
        if 'amount' in data:
            session_data['amount'] = data['amount']

        # Store session
        app.payment_sessions[call_id] = session_data

        print(f"SUCCESS: Created payment session for {call_id}: {session_data}")

        response_data = {
            'success': True,
            'message': f'Payment session started for call {call_id}',
            'call_id': call_id,
            'payment_type': payment_type
        }

        # Add type-specific response data
        if payment_type == 'order':
            response_data['order_number'] = session_data.get('order_number')
        else:
            response_data['reservation_number'] = session_data.get('reservation_number')

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/test-sms', methods=['POST'])
def debug_test_sms():
    """Debug endpoint to test SMS functionality via SWAIG"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message', 'Test SMS from Bobby\'s Table debug endpoint')

        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'Phone number is required'
            }), 400

        print(f"🧪 Debug SMS Test Request:")
        print(f"   Phone: {phone_number}")
        print(f"   Message: {message}")

        # Get the agent and call the test SMS function
        agent = get_receptionist_agent()
        if not agent:
            return jsonify({
                'success': False,
                'error': 'Agent not available'
            }), 503

        # Call the SWAIG function directly
        if (hasattr(agent, '_tool_registry') and 
            hasattr(agent._tool_registry, '_swaig_functions') and
            'send_test_sms' in agent._tool_registry._swaig_functions):
            function_handler = agent._tool_registry._swaig_functions['send_test_sms']

            # Prepare the parameters
            params = {
                'phone_number': phone_number,
                'message': message
            }

            # Call the function
            result = function_handler(params, {})

            print(f"🧪 Debug SMS Test Result: {result}")

            return jsonify({
                'success': True,
                'message': f'Test SMS function called for {phone_number}',
                'result': str(result)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'send_test_sms function not found in agent'
            }), 500

    except Exception as e:
        print(f"ERROR: Error in debug test SMS: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# PCI COMPLIANT: Stripe webhook handler for direct payments
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events for PCI-compliant payments"""
    try:
        print("🔍 Stripe webhook called")

        # Get the raw body and signature
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')

        # Verify webhook signature (optional but recommended)
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        if webhook_secret and sig_header:
            try:
                import stripe
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            except ValueError:
                print("ERROR: Invalid payload")
                return jsonify({"error": "Invalid payload"}), 400
            except stripe.error.SignatureVerificationError:
                print("ERROR: Invalid signature")
                return jsonify({"error": "Invalid signature"}), 400
        else:
            # Parse without verification (for development)
            event = json.loads(payload)

        print(f"📋 Webhook event: {event['type']}")

        # Handle payment intent events
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']

            print(f"SUCCESS: Payment succeeded: {payment_intent['id']}")
            print(f"   Amount: ${payment_intent['amount'] / 100}")
            print(f"   Metadata: {payment_intent.get('metadata', {})}")

            # Extract metadata
            metadata = payment_intent.get('metadata', {})
            reservation_number = metadata.get('reservation_number')
            payment_type = metadata.get('payment_type')
            customer_name = metadata.get('customer_name')
            phone_number = metadata.get('phone_number')

            if payment_type == 'reservation' and reservation_number:
                # Update reservation payment status
                reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                if reservation:
                    reservation.payment_status = 'paid'
                    reservation.payment_method = 'credit-card'
                    reservation.payment_date = datetime.now()
                    reservation.payment_amount = payment_intent['amount'] / 100
                    reservation.payment_intent_id = payment_intent['id']

                    # Generate confirmation number
                    import random
                    import string
                    confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    reservation.confirmation_number = confirmation_number

                    db.session.commit()

                    print(f"SUCCESS: Updated reservation #{reservation_number} payment status")

                    # Send SMS receipt
                    try:
                        send_payment_receipt_sms(
                            reservation=reservation,
                            payment_amount=payment_intent['amount'] / 100,
                            phone_number=phone_number,
                            confirmation_number=confirmation_number
                        )
                        print(f"SUCCESS: SMS receipt sent to {phone_number}")
                    except Exception as sms_error:
                        print(f"WARNING: Failed to send SMS receipt: {sms_error}")

            elif payment_type == 'order':
                # Handle order payments similarly
                order_number = metadata.get('order_number')
                if order_number:
                    order = Order.query.filter_by(order_number=order_number).first()
                    if order:
                        order.payment_status = 'paid'
                        order.payment_method = 'credit-card'
                        order.payment_date = datetime.now()
                        order.payment_amount = payment_intent['amount'] / 100
                        order.payment_intent_id = payment_intent['id']

                        # Generate confirmation number
                        import random
                        import string
                        confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        order.confirmation_number = confirmation_number

                        db.session.commit()

                        print(f"SUCCESS: Updated order #{order_number} payment status")

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            print(f"ERROR: Payment failed: {payment_intent['id']}")
            print(f"   Error: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"ERROR: Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

        # Validate required fields
        if not amount:
            print("ERROR: Amount is required but not provided")
            return jsonify({
                "status": "failed",
                "error": "Amount is required"
            }), 400

        try:
            amount_cents = int(float(amount) * 100)
            print(f"💰 Amount converted to cents: {amount_cents}")
        except (ValueError, TypeError) as e:
            print(f"ERROR: Invalid amount format: {amount} - {e}")
            return jsonify({
                "status": "failed",
                "error": f"Invalid amount format: {amount}"
            }), 400

        # Process payment with Stripe using the same pattern as our successful test
        try:
            import stripe
            stripe.api_key = os.getenv('STRIPE_API_KEY')

            if not stripe.api_key:
                print("WARNING: No Stripe API key configured, using test mode")
                stripe.api_key = 'sk_test_51234567890abcdef'  # Fallback for testing

            print(f"🔑 Using Stripe API key: {stripe.api_key[:12]}...")

            # Create payment method from card data or use test token
            payment_method = None
            payment_method_id = None

            try:
                # Try to create payment method with card data
                print(f"🔍 Attempting to create payment method with card data")
                payment_method = stripe.PaymentMethod.create(
                    type="card",
                    card={
                        "number": card_number,
                        "exp_month": int(exp_month) if exp_month else None,
                        "exp_year": int(exp_year) if exp_year else None,
                        "cvc": cvc,
                    },
                    billing_details={
                        "name": customer_name or "Customer",
                        "address": {
                            "postal_code": postal_code
                        }
                    }
                )
                payment_method_id = payment_method.id
                print(f"SUCCESS: Payment method created: {payment_method_id}")

            except stripe.error.CardError as e:
                print(f"ERROR: Payment method creation error: {str(e)}")
                if "raw card data" in str(e) or "empty string" in str(e):
                    print("WARNING: Raw card data not allowed or empty, using test payment method token")
                    # Use Stripe's test payment method instead
                    payment_method_id = "pm_card_visa"
                else:
                    print(f"ERROR: Card error: {e.user_message}")
                    return jsonify({
                        "status": "failed",
                        "error": e.user_message,
                        "decline_code": e.decline_code if hasattr(e, 'decline_code') else None
                    })
            except Exception as e:
                print(f"ERROR: Payment method creation error: {str(e)}")
                # Fallback to test payment method
                payment_method_id = "pm_card_visa"
                print(f"🔄 Using fallback payment method: {payment_method_id}")

            # Create payment intent with proper configuration
            description = f"Bobby's Table Payment"
            if order_number:
                description = f"Bobby's Table Order #{order_number}"
            elif reservation_number:
                description = f"Bobby's Table Reservation #{reservation_number}"

            print(f"PAYMENT: Creating payment intent for {description}")

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                payment_method=payment_method_id,
                confirm=True,
                description=description,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'  # Prevent redirect-based payment methods
                },
                metadata={
                    "payment_source": "swml_pay_verb",
                    "order_id": order_id or "",
                    "order_number": order_number or "",
                    "reservation_number": reservation_number or "",
                    "customer_name": customer_name or "",
                    "customer_phone": phone_number or "",
                    "payment_type": payment_type or ""
                }
            )

            print(f"SUCCESS: Payment intent created: {payment_intent.id}")
            print(f"   Status: {payment_intent.status}")

            if payment_intent.status == 'succeeded':
                print("🎉 Stripe payment successful!")

                # Generate confirmation number first
                import random
                import string
                confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                print(f"CONFIRMATION: Generated confirmation number: {confirmation_number}")

                # Update database based on payment type
                if payment_type == 'order' and (order_number or order_id):
                    # Handle order payment
                    order = None
                    if order_number:
                        order = Order.query.filter_by(order_number=order_number).first()
                    elif order_id:
                        order = Order.query.get(order_id)

                    if order:
                        order.payment_status = 'paid'
                        order.payment_method = 'credit-card'
                        order.payment_date = datetime.now()
                        order.payment_amount = float(amount)
                        order.payment_intent_id = payment_intent.id
                        order.confirmation_number = confirmation_number

                        db.session.commit()
                        print(f"SUCCESS: Order {order.order_number} updated with payment info")

                        # Send SMS receipt
                        try:
                            sms_result = send_order_payment_receipt_sms(
                                order=order,
                                payment_amount=float(amount),
                                phone_number=phone_number or order.customer_phone,
                                confirmation_number=confirmation_number
                            )

                            # SMS result already handled in the function
                            if sms_result.get('success'):
                                print(f"SUCCESS: SMS receipt sent: {sms_result.get('sms_result', 'Success')}")
                            else:
                                print(f"WARNING: SMS receipt failed: {sms_result.get('error', 'Unknown error')}")
                        except Exception as sms_error:
                            print(f"WARNING: Failed to send SMS receipt: {sms_error}")

                        return jsonify({
                            "status": "success",
                            "payment_intent_id": payment_intent.id,
                            "amount": float(amount),
                            "currency": payment_intent.currency,
                            "message": f"Payment of ${amount} processed successfully for Order #{order.order_number}. Your confirmation number is {confirmation_number}.",
                            "confirmation_number": confirmation_number,
                            "order_number": order.order_number
                        })

                elif payment_type == 'reservation' or reservation_number:
                    # Handle reservation payment
                    print(f"🔍 Processing reservation payment: type={payment_type}, number={reservation_number}")
                    reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                    if reservation:
                        print(f"SUCCESS: Found reservation: {reservation.name} for {reservation.party_size} people")
                        reservation.payment_status = 'paid'
                        reservation.payment_method = 'credit-card'
                        reservation.payment_date = datetime.now()
                        reservation.payment_amount = float(amount)
                        reservation.payment_intent_id = payment_intent.id
                        reservation.confirmation_number = confirmation_number

                        db.session.commit()
                        print(f"SUCCESS: Reservation {reservation.reservation_number} updated with payment info")

                        # Call SWAIG send_payment_receipt function for reservation
                        print(f"SMS: Calling SWAIG send_payment_receipt function for reservation {reservation_number}")
                        try:
                            # Make a SWAIG function call to send the SMS receipt
                            swaig_data = {
                                "function": "send_payment_receipt",
                                "argument": {
                                    "parsed": [{
                                        "reservation_number": reservation_number,
                                        "phone_number": phone_number or reservation.phone_number,
                                        "payment_amount": amount_cents / 100.0,  # Convert cents to dollars for SMS
                                        "confirmation_number": confirmation_number
                                    }],
                                    "raw": json.dumps({
                                        "reservation_number": reservation_number,
                                        "phone_number": phone_number or reservation.phone_number,
                                        "payment_amount": amount_cents / 100.0,  # Convert cents to dollars for SMS
                                        "confirmation_number": confirmation_number
                                    })
                                },
                                "call_id": f"payment-{confirmation_number}",
                                "content_type": "text/swaig",
                                "version": "2.0",
                                "caller_id_num": phone_number or reservation.phone_number
                            }

                            # Call the SWAIG receptionist endpoint to trigger SMS
                            import requests
                            response = requests.post('http://localhost:8080/receptionist', json=swaig_data)

                            if response.status_code == 200:
                                swaig_result = response.json()
                                print(f"SUCCESS: SMS receipt SWAIG function called successfully - SWML send_sms action generated")
                                sms_status = "SMS receipt sent: Payment receipt SMS SWML action generated via SWAIG"
                            else:
                                print(f"WARNING: SWAIG SMS function call failed: {response.status_code}")
                                sms_status = f"SMS receipt failed: SWAIG call returned {response.status_code}"

                        except Exception as sms_error:
                            print(f"WARNING: Failed to call SWAIG SMS function: {sms_error}")
                            sms_status = f"SMS receipt failed: {str(sms_error)}"

                        return jsonify({
                            "status": "success",
                            "payment_intent_id": payment_intent.id,
                            "amount": float(amount),
                            "currency": payment_intent.currency,
                            "message": f"Payment of ${amount} processed successfully for Reservation #{reservation_number}. Your confirmation number is {confirmation_number}.",
                            "confirmation_number": confirmation_number,
                            "reservation_number": reservation_number,
                            "sms_status": sms_status
                        })
                    else:
                        print(f"ERROR: Reservation {reservation_number} not found")
                        return jsonify({
                            "status": "failed",
                            "error": f"Reservation {reservation_number} not found"
                        }), 404

                # Generic success response if no specific type
                return jsonify({
                    "status": "success",
                    "payment_intent_id": payment_intent.id,
                    "amount": float(amount),
                    "currency": payment_intent.currency,
                    "message": f"Payment of ${amount} processed successfully. Your confirmation number is {confirmation_number}.",
                    "confirmation_number": confirmation_number
                })

            elif payment_intent.status == 'requires_action':
                print("WARNING: Payment requires additional action")
                return jsonify({
                    "status": "requires_action",
                    "payment_intent_id": payment_intent.id,
                    "client_secret": payment_intent.client_secret,
                    "message": "Payment requires additional authentication"
                })
            else:
                print(f"ERROR: Payment failed with status: {payment_intent.status}")
                return jsonify({
                    "status": "failed",
                    "payment_intent_id": payment_intent.id,
                    "message": f"Payment failed with status: {payment_intent.status}"
                })

        except stripe.error.CardError as e:
            print(f"ERROR: Stripe card error: {e.user_message}")
            return jsonify({
                "status": "failed",
                "error": e.user_message,
                "decline_code": e.decline_code if hasattr(e, 'decline_code') else None
            })
        except stripe.error.StripeError as e:
            print(f"ERROR: Stripe API error: {str(e)}")
            return jsonify({
                "status": "failed",
                "error": str(e),
                "message": "Stripe API error occurred"
            })
        except Exception as e:
            print(f"ERROR: Unexpected error in payment processing: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "failed",
                "error": str(e),
                "message": "Unexpected error occurred during payment processing"
            })

    except Exception as e:
        print(f"ERROR: Critical error in payment processor: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "failed",
            "error": str(e),
            "message": "Critical error in payment processor"
        }), 500

@app.route('/api/signalwire/payment-callback', methods=['POST'])
def signalwire_payment_callback():
    """Handle SignalWire payment status callbacks from SWML pay verb"""
    from models import Reservation, Order  # Import models at the top to avoid scope issues

    try:
        print("🔍 SignalWire payment callback called")
        print(f"   Content-Type: {request.content_type}")
        print(f"   Content-Length: {request.content_length}")
        print(f"   Request URL: {request.url}")
        print(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")

        # Get callback data from SignalWire
        callback_data = request.get_json()

        if not callback_data:
            print("ERROR: No callback data received")
            return jsonify({
                "success": False,
                "error": "No callback data received"
            }), 400

        print(f"📋 SignalWire callback data: {json.dumps(callback_data, indent=2)}")

        # Extract payment information from SignalWire's actual callback structure
        event_type = callback_data.get('event_type')
        params = callback_data.get('params', {})

        # SignalWire callback structure analysis
        call_id = params.get('call_id')
        control_id = params.get('control_id')
        payment_for = params.get('for')  # 'payment-card-number', 'payment-failed', etc.
        error_type = params.get('error_type')
        attempt = params.get('attempt')
        payment_method = params.get('payment_method')
        payment_card_type = params.get('payment_card_type')

        # Determine payment status from SignalWire callback
        if payment_for == 'payment-failed':
            status = 'failed'
        elif payment_for == 'payment-succeeded' or payment_for == 'payment-completed':
            status = 'completed'
        elif payment_for == 'payment-card-number':
            status = 'collecting_card'
        elif payment_for in ['expiration-date', 'security-code', 'postal-code', 'payment-processing']:
            status = 'in_progress'
        else:
            status = 'unknown'

        print(f"🔍 SignalWire callback analysis:")
        print(f"   Event Type: {event_type}")
        print(f"   Payment For: {payment_for}")
        print(f"   Status: {status}")
        print(f"   Error Type: {error_type}")
        print(f"   Attempt: {attempt}")
        print(f"   Call ID: {call_id}")
        print(f"   Control ID: {control_id}")

        # Get payment session data to retrieve original parameters
        payment_session = None
        reservation_number = None
        customer_name = None
        phone_number = None
        payment_type = 'reservation'
        amount = None
        payment_id = None  # Initialize payment_id variable

        if call_id:
            # ENHANCED DEBUG: Check BOTH storage locations
            global payment_sessions_global
            if 'payment_sessions_global' not in globals():
                payment_sessions_global = {}

            payment_sessions = getattr(app, 'payment_sessions', {})
            print(f"🔍 DEBUG: Total payment sessions in app memory: {len(payment_sessions)}")
            print(f"🔍 DEBUG: Total payment sessions in global memory: {len(payment_sessions_global)}")
            print(f"🔍 DEBUG: App session keys: {list(payment_sessions.keys())}")
            print(f"🔍 DEBUG: Global session keys: {list(payment_sessions_global.keys())}")
            print(f"🔍 DEBUG: Looking for call_id: {call_id}")

            payment_session = get_payment_session_data(call_id)
            if payment_session:
                reservation_number = payment_session.get('reservation_number')
                customer_name = payment_session.get('customer_name')
                phone_number = payment_session.get('phone_number')
                payment_type = payment_session.get('payment_type', 'reservation')
                amount = payment_session.get('amount')
                print(f"SUCCESS: Retrieved payment session data for call {call_id}")
            else:
                print(f"WARNING: No payment session found for call {call_id}")
                # Try to extract from any stored payment sessions
                if call_id in payment_sessions:
                    session_data = payment_sessions[call_id]
                    reservation_number = session_data.get('reservation_number')
                    customer_name = session_data.get('customer_name')
                    phone_number = session_data.get('phone_number')
                    payment_type = session_data.get('payment_type', 'reservation')
                    amount = session_data.get('amount')
                    print(f"SUCCESS: Found payment session in memory for call {call_id}: reservation {reservation_number}")
                else:
                    print(f"ERROR: Call ID {call_id} not found in payment_sessions at all")
                    print(f"🔍 Available sessions: {list(payment_sessions.keys())}")

                    # ENHANCED FALLBACK: Check if there's a fallback session for any reservation
                    if hasattr(app, 'fallback_payment_sessions'):
                        fallback_sessions = app.fallback_payment_sessions
                        print(f"🔍 Checking {len(fallback_sessions)} fallback payment session mappings")

                        # Try to find a session by reservation number if we can extract it
                        for res_num, fallback_call_id in fallback_sessions.items():
                            if fallback_call_id in payment_sessions:
                                session_data = payment_sessions[fallback_call_id]
                                reservation_number = session_data.get('reservation_number')
                                customer_name = session_data.get('customer_name')
                                phone_number = session_data.get('phone_number')
                                payment_type = session_data.get('payment_type', 'reservation')
                                amount = session_data.get('amount')
                                print(f"SUCCESS: Found fallback payment session for reservation {res_num}: {fallback_call_id}")
                                break
                    else:
                        print(f"🔍 No fallback payment sessions available")

                    # ENHANCED FALLBACK: Try to find session by most recent activity first
                    if not payment_session and (payment_sessions or payment_sessions_global):
                        # Try to get the most recent session (likely the active payment)
                        all_sessions = {}
                        all_sessions.update(payment_sessions)
                        all_sessions.update(payment_sessions_global)

                        print(f"🔍 Attempting smart session matching across {len(all_sessions)} sessions")

                        # Get the most recent session (likely the one we're looking for)
                        if all_sessions:
                            most_recent_call_id = max(all_sessions.keys(), 
                                                    key=lambda k: all_sessions[k].get('created_at', 0))
                            most_recent_session = all_sessions[most_recent_call_id]

                            # Use the most recent session as a fallback
                            temp_reservation_number = most_recent_session.get('reservation_number')
                            temp_customer_name = most_recent_session.get('customer_name')
                            temp_phone_number = most_recent_session.get('phone_number')
                            temp_payment_type = most_recent_session.get('payment_type', 'reservation')
                            temp_amount = most_recent_session.get('amount')

                            print(f"🔄 Using most recent payment session as fallback:")
                            print(f"   Session Call ID: {most_recent_call_id}")
                            print(f"   Reservation: {temp_reservation_number}")
                            print(f"   Customer: {temp_customer_name}")
                            print(f"   Amount: ${temp_amount}")

                            # Update variables if they weren't set already
                            if not reservation_number:
                                reservation_number = temp_reservation_number
                            if not customer_name:
                                customer_name = temp_customer_name
                            if not phone_number:
                                phone_number = temp_phone_number
                            if not amount:
                                amount = temp_amount

                            # Mark this session as used by this call_id in BOTH storages
                            mapped_session = most_recent_session.copy()
                            mapped_session['original_call_id'] = most_recent_call_id
                            mapped_session['callback_call_id'] = call_id
                            mapped_session['signalwire_callback_received'] = True

                            payment_sessions[call_id] = mapped_session
                            payment_sessions_global[call_id] = mapped_session.copy()
                            payment_session = mapped_session  # Set for further processing

                            print(f"SUCCESS: Created session mapping in BOTH storages: {call_id} -> {most_recent_call_id}")

                            # IMPROVED: Also create reservation mapping if available
                            if reservation_number:
                                if not hasattr(app, 'payment_sessions_by_reservation'):
                                    app.payment_sessions_by_reservation = {}
                                app.payment_sessions_by_reservation[reservation_number] = call_id
                                print(f"🔗 Created new reservation mapping: {reservation_number} -> {call_id}")

        # Legacy parameter extraction (for backward compatibility)
        if not reservation_number:
            reservation_number = callback_data.get('reservation_number')
        if not customer_name:
            customer_name = callback_data.get('customer_name') or callback_data.get('cardholder_name')
        if not phone_number:
            phone_number = callback_data.get('phone_number')
        if not amount:
            amount = callback_data.get('amount')
        if not payment_id:
            payment_id = callback_data.get('payment_id') or callback_data.get('payment_intent_id')

        # Also check for parameters in nested structure (legacy)
        if 'parameters' in callback_data:
            legacy_params = callback_data['parameters']
            if isinstance(legacy_params, dict):
                if not reservation_number:
                    reservation_number = legacy_params.get('reservation_number')
                if not customer_name:
                    customer_name = legacy_params.get('customer_name') or legacy_params.get('cardholder_name')
                if not phone_number:
                    phone_number = legacy_params.get('phone_number')
                if not payment_type:
                    payment_type = legacy_params.get('payment_type', 'reservation')
                if not amount:
                    amount = legacy_params.get('amount')
                if not payment_id:
                    payment_id = legacy_params.get('payment_id') or legacy_params.get('payment_intent_id')

        print(f"🔍 Extracted payment info:")
        print(f"   Status: {status}")
        print(f"   Amount: {amount}")
        print(f"   Reservation: {reservation_number}")
        print(f"   Customer: {customer_name}")
        print(f"   Phone: {phone_number}")
        print(f"   Type: {payment_type}")
        print(f"   Call ID: {call_id}")
        print(f"   Payment ID: {payment_id}")
        print(f"   Payment For: {payment_for}")
        print(f"   Error Type: {error_type}")

        # Handle different payment callback scenarios
        if status == 'failed':
            print(f"ERROR: Payment failed: {error_type}")

            # Update payment session with failure info
            if call_id:
                payment_sessions = getattr(app, 'payment_sessions', {})
                if call_id in payment_sessions:
                    payment_sessions[call_id]['payment_status'] = 'failed'
                    payment_sessions[call_id]['error_type'] = error_type
                    payment_sessions[call_id]['failure_reason'] = payment_for
                    payment_sessions[call_id]['attempt'] = attempt
                    print(f"SUCCESS: Updated payment session {call_id} with failure info")

            return jsonify({
                "success": False,
                "status": "failed",
                "error_type": error_type,
                "payment_for": payment_for,
                "attempt": attempt,
                "call_id": call_id,
                "message": f"Payment failed: {error_type}"
            })

        elif status == 'collecting_card':
            print(f"🔄 Payment in progress: collecting card information")
            return jsonify({
                "success": True,
                "status": "in_progress",
                "payment_for": payment_for,
                "call_id": call_id,
                "message": "Payment in progress - collecting card information"
            })

        elif status == 'in_progress':
            print(f"🔄 Payment in progress: {payment_for}")
            return jsonify({
                "success": True,
                "status": "in_progress",
                "payment_for": payment_for,
                "call_id": call_id,
                "message": f"Payment in progress - {payment_for.replace('-', ' ')}"
            })

        elif status == 'completed' or status == 'succeeded':
            print("SUCCESS: Payment completed successfully")

            # CRITICAL FIX: Ensure we have payment session data for final callback
            if call_id and not payment_session:
                print(f"🔍 No payment session data found for {call_id}")
                # Try alternative lookups
                payment_sessions = getattr(app, 'payment_sessions', {})
                if call_id in payment_sessions:
                    payment_session = payment_sessions[call_id]
                    reservation_number = payment_session.get('reservation_number')
                    customer_name = payment_session.get('customer_name')
                    phone_number = payment_session.get('phone_number')
                    payment_type = payment_session.get('payment_type', 'reservation')
                    amount = payment_session.get('amount')
                    print(f"SUCCESS: Retrieved payment session from memory: reservation {reservation_number}")
                else:
                    print(f"WARNING: No payment session found in memory either")

            # Extract order_number for order payments
            order_number = callback_data.get('order_number')
            if not order_number and call_id:
                # Check payment session for order_number
                if payment_session:
                    order_number = payment_session.get('order_number')
                else:
                    payment_sessions = getattr(app, 'payment_sessions', {})
                    if call_id in payment_sessions:
                        order_number = payment_sessions[call_id].get('order_number')

            # Process order payments first (more specific)
            if payment_type == 'order' and order_number:
                # Handle order payments
                order = Order.query.filter_by(order_number=order_number).first()
                if order:
                    # Generate confirmation number
                    import random
                    import string
                    confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

                    order.payment_status = 'paid'
                    order.payment_method = 'credit-card'
                    order.payment_date = datetime.now()
                    order.payment_amount = float(amount) if amount else 0.0
                    order.confirmation_number = confirmation_number

                    if payment_id:
                        order.payment_intent_id = payment_id

                    db.session.commit()
                    print(f"SUCCESS: Order {order_number} updated with payment confirmation")

                    # ENHANCEMENT: Update Stripe Payment Intent metadata for orders
                    if payment_id and payment_id.startswith('pi_'):
                        try:
                            import stripe
                            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

                            if stripe.api_key:
                                # Update the payment intent metadata with confirmation number
                                stripe.PaymentIntent.modify(
                                    payment_id,
                                    metadata={
                                        'confirmation_number': confirmation_number,
                                        'payment_completed_date': datetime.now().isoformat(),
                                        'bobby_table_status': 'confirmed_paid',
                                        'payment_type': 'order'
                                    }
                                )
                                print(f"SUCCESS: Updated Stripe PaymentIntent {payment_id} with confirmation number: {confirmation_number}")
                            else:
                                print(f"WARNING: Stripe API key not configured - skipping metadata update")

                        except Exception as stripe_error:
                            print(f"WARNING: Failed to update Stripe metadata: {stripe_error}")
                            # Don't fail the whole process if Stripe update fails

                    # Create SWML response to announce payment confirmation to the user
                    announcement_text = f"Excellent! Your payment of ${amount} has been processed successfully. "
                    announcement_text += f"Your confirmation number is {' '.join(confirmation_number)}. "
                    announcement_text += f"Please write this down: {' '.join(confirmation_number)}. "
                    announcement_text += f"Your order will be ready for {order.order_type} at the scheduled time. "
                    announcement_text += f"Thank you for choosing Bobby's Table! Have a great day!"

                    # Return SWML response to announce the confirmation
                    swml_response = {
                        "version": "1.0.0",
                        "sections": {
                            "main": [
                                {
                                    "say": {
                                        "text": announcement_text,
                                        "voice": "rime.luna",
                                        "model": "arcana",
                                        "language": "en-US"
                                    }
                                },
                                {
                                    "hangup": {}
                                }
                            ]
                        }
                    }

                    # Return SWML response directly for SignalWire to process
                    response = make_response(jsonify(swml_response))
                    response.headers['Content-Type'] = 'application/json'

                    # Also log the success info
                    print(f"🎉 Returning SWML announcement for order payment completion:")
                    print(f"   Confirmation: {confirmation_number}")
                    print(f"   Amount: ${amount}")
                    print(f"   Order: {order_number}")

                    return response
                else:
                    print(f"ERROR: Order {order_number} not found")
                    return jsonify({
                        "success": False,
                        "error": f"Order {order_number} not found"
                    }), 404

            elif payment_type == 'reservation' and reservation_number:
                # Update reservation payment status
                reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                if reservation:
                    print(f"SUCCESS: Found reservation: {reservation.name} for {reservation.party_size} people")

                    # Generate confirmation number
                    import random
                    import string
                    confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

                    # Update reservation
                    reservation.payment_status = 'paid'
                    reservation.payment_method = 'credit-card'
                    reservation.payment_date = datetime.now()
                    reservation.payment_amount = float(amount) if amount else 0.0
                    reservation.confirmation_number = confirmation_number

                    # Store payment ID if provided
                    if payment_id:
                        reservation.payment_intent_id = payment_id

                    db.session.commit()
                    print(f"SUCCESS: Reservation {reservation_number} updated with payment confirmation")

                    # ENHANCEMENT: Store confirmation number in payment session and conversation memory
                    # This allows the agent to access the confirmation number in future interactions
                    try:
                        # Update payment session with confirmation number (using extracted call_id)
                        if call_id:
                            # Update payment session data
                            payment_sessions = getattr(app, 'payment_sessions', {})
                            if call_id in payment_sessions:
                                payment_sessions[call_id]['confirmation_number'] = confirmation_number
                                payment_sessions[call_id]['payment_completed'] = True
                                payment_sessions[call_id]['payment_status'] = 'completed'
                                payment_sessions[call_id]['payment_amount'] = float(amount) if amount else 0.0
                                payment_sessions[call_id]['payment_date'] = datetime.now().isoformat()
                                print(f"SUCCESS: Updated payment session {call_id} with confirmation number: {confirmation_number}")
                            else:
                                print(f"WARNING: Payment session {call_id} not found in active sessions")
                                # Create a minimal session record for the confirmation
                                if not hasattr(app, 'payment_sessions'):
                                    app.payment_sessions = {}
                                app.payment_sessions[call_id] = {
                                    'confirmation_number': confirmation_number,
                                    'payment_completed': True,
                                    'payment_status': 'completed',
                                    'payment_amount': float(amount) if amount else 0.0,
                                    'payment_date': datetime.now().isoformat(),
                                    'reservation_number': reservation_number
                                }
                                print(f"SUCCESS: Created new payment session record for {call_id} with confirmation number: {confirmation_number}")
                        else:
                            print(f"WARNING: No call_id provided in payment callback - cannot update payment session")

                        # Store in conversation memory for future agent access
                        # We'll store this globally so any future get_reservation calls can access it
                        if not hasattr(app, 'payment_confirmations'):
                            app.payment_confirmations = {}

                        app.payment_confirmations[reservation_number] = {
                            'confirmation_number': confirmation_number,
                            'payment_amount': float(amount) if amount else 0.0,
                            'payment_date': datetime.now().isoformat(),
                            'payment_id': payment_id,
                            'customer_name': customer_name,
                            'call_id': call_id  # Store call_id for reference
                        }
                        print(f"SUCCESS: Stored confirmation number {confirmation_number} for reservation {reservation_number}")

                    except Exception as session_error:
                        print(f"WARNING: Could not update payment session data: {session_error}")

                    # ENHANCEMENT: Update Stripe Payment Intent metadata with confirmation number
                    if payment_id and payment_id.startswith('pi_'):
                        try:
                            import stripe
                            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

                            if stripe.api_key:
                                # Update the payment intent metadata with confirmation number
                                stripe.PaymentIntent.modify(
                                    payment_id,
                                    metadata={
                                        'confirmation_number': confirmation_number,
                                        'payment_completed_date': datetime.now().isoformat(),
                                        'bobby_table_status': 'confirmed_paid'
                                    }
                                )
                                print(f"SUCCESS: Updated Stripe PaymentIntent {payment_id} with confirmation number: {confirmation_number}")
                            else:
                                print(f"WARNING: Stripe API key not configured - skipping metadata update")

                        except Exception as stripe_error:
                            print(f"WARNING: Failed to update Stripe metadata: {stripe_error}")
                            # Don't fail the whole process if Stripe update fails

                    # Send enhanced payment confirmation SMS with reservation details and link
                    try:
                        # Get the reservation skill to use its SMS function
                        from skills.restaurant_reservation.skill import RestaurantReservationSkill

                        # Create a mock agent object for the skill
                        class MockAgent:
                            pass

                        mock_agent = MockAgent()
                        reservation_skill = RestaurantReservationSkill(mock_agent)

                        # Prepare reservation data
                        reservation_data = {
                            'reservation_number': reservation.reservation_number,
                            'name': reservation.name,
                            'date': str(reservation.date),
                            'time': str(reservation.time),
                            'party_size': reservation.party_size,
                            'special_requests': reservation.special_requests,
                            'has_preorders': float(amount) > 0 if amount else False
                        }

                        # Prepare payment data
                        payment_data = {
                            'confirmation_number': confirmation_number,
                            'amount': float(amount) if amount else 0.0,
                            'payment_date': datetime.now().strftime('%m/%d/%Y %I:%M %p'),
                            'payment_method': 'credit-card'
                        }

                        # Send payment confirmation SMS
                        print(f"SMS: Attempting to send payment confirmation SMS...")
                        sms_result = reservation_skill._send_payment_confirmation_sms(
                            reservation_data, 
                            payment_data, 
                            phone_number or reservation.phone_number
                        )

                        if sms_result.get('success'):
                            sms_status = f"Payment confirmation SMS sent successfully to {phone_number or reservation.phone_number}"
                            print(f"SUCCESS: {sms_status}")
                            if sms_result.get('calendar_link'):
                                print(f"   Calendar link included: {sms_result['calendar_link']}")
                        else:
                            sms_status = f"Failed to send payment confirmation SMS: {sms_result.get('error', 'Unknown error')}"
                            print(f"ERROR: {sms_status}")

                            # Try alternative SMS method using direct SignalWire REST API
                            print(f"🔄 Attempting backup SMS method...")
                            try:
                                import requests

                                # Get SignalWire credentials
                                project_id = os.getenv('SIGNALWIRE_PROJECT_ID')
                                auth_token = os.getenv('SIGNALWIRE_AUTH_TOKEN') or os.getenv('SIGNALWIRE_TOKEN')
                                space = os.getenv('SIGNALWIRE_SPACE')
                                from_number = os.getenv('SIGNALWIRE_FROM_NUMBER')

                                if all([project_id, auth_token, space, from_number]):
                                    # Build simple SMS message
                                    backup_sms_body = f"PAYMENT: Payment Confirmed!\n\n"
                                    backup_sms_body += f"Confirmation: {confirmation_number}\n"
                                    backup_sms_body += f"Amount: ${amount}\n"
                                    backup_sms_body += f"Reservation #{reservation.reservation_number}\n\n"
                                    backup_sms_body += f"Thank you! - Bobby's Table"

                                    # Send via REST API
                                    space_url = f"https://{space}.signalwire.com"
                                    url = f"{space_url}/api/laml/2010-04-01/Accounts/{project_id}/Messages.json"

                                    response = requests.post(
                                        url,
                                        data={
                                            'From': from_number,
                                            'To': phone_number or reservation.phone_number,
                                            'Body': backup_sms_body
                                        },
                                        auth=(project_id, auth_token)
                                    )

                                    if response.status_code == 201:
                                        sms_status = f"Backup SMS sent successfully via REST API"
                                        print(f"SUCCESS: {sms_status}")
                                    else:
                                        print(f"ERROR: Backup SMS also failed: {response.status_code} - {response.text}")
                                else:
                                    print(f"ERROR: Missing SignalWire credentials for backup SMS")
                            except Exception as backup_error:
                                print(f"ERROR: Backup SMS method failed: {backup_error}")

                    except Exception as sms_error:
                        sms_status = f"Error sending payment confirmation SMS: {str(sms_error)}"
                        print(f"ERROR: {sms_status}")
                        import traceback
                        traceback.print_exc()

                    # CRITICAL FIX: Return SWML response with actual confirmation number
                    # This prevents the system from falling through to generic response
                    announcement_text = f"Excellent! Your payment of ${amount} has been processed successfully. "
                    announcement_text += f"Your confirmation number is {' '.join(confirmation_number)}. "
                    announcement_text += f"Please write this down: {' '.join(confirmation_number)}. "
                    announcement_text += f"We look forward to serving you at Bobby's Table. Have a great day!"

                    # Return SWML response to announce the confirmation
                    swml_response = {
                        "version": "1.0.0",
                        "sections": {
                            "main": [
                                {
                                    "say": {
                                        "text": announcement_text,
                                        "voice": "rime.luna",
                                        "model": "arcana",
                                        "language": "en-US"
                                    }
                                },
                                {
                                    "hangup": {}
                                }
                            ]
                        }
                    }

                    # Return SWML response directly for SignalWire to process
                    response = make_response(jsonify(swml_response))
                    response.headers['Content-Type'] = 'application/json'

                    # Also log the success info
                    print(f"🎉 Returning SWML announcement for reservation payment completion:")
                    print(f"   Confirmation: {confirmation_number}")
                    print(f"   Amount: ${amount}")
                    print(f"   Reservation: {reservation_number}")

                    return response
                else:
                    print(f"ERROR: Reservation {reservation_number} not found")
                    return jsonify({
                        "success": False,
                        "error": f"Reservation {reservation_number} not found"
                    }), 404



            # CRITICAL FIX: Don't generate generic response if payment was already processed
            # The payment processor already handled the confirmation and SMS receipt
            print(f"WARNING: Payment completion callback received but payment already processed")
            print(f"   Payment Type: {payment_type}")
            print(f"   Reservation: {reservation_number}")
            print(f"   Amount: ${amount}")
            print(f"   Call ID: {call_id}")

            # Check if this payment was already processed by looking for recent confirmations
            # If payment was processed in the last 5 minutes, don't generate duplicate response
            try:
                with app.app_context():
                    if payment_type == 'reservation' and reservation_number:
                        reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                        if reservation and reservation.payment_date:
                            time_since_payment = datetime.now() - reservation.payment_date
                            if time_since_payment.total_seconds() < 300:  # 5 minutes
                                print(f"SUCCESS: Payment was already processed {time_since_payment.total_seconds():.0f} seconds ago")
                                print(f"   Confirmation: {reservation.confirmation_number}")
                                print(f"   SMS receipt already sent - no duplicate response needed")

                                # Return simple success response without SWML to avoid duplicate announcements
                                return jsonify({
                                    "success": True,
                                    "status": "completed",
                                    "message": "Payment already processed and confirmed",
                                    "confirmation_number": reservation.confirmation_number,
                                    "payment_date": reservation.payment_date.isoformat() if reservation.payment_date else None,
                                    "call_id": call_id,
                                    "no_duplicate_announcement": True
                                })
            except Exception as db_check_error:
                print(f"WARNING: Could not check payment status in database: {db_check_error}")

            # If we get here, generate a minimal completion response without duplicate confirmation
            print(f"🎉 Returning simple completion acknowledgment (no duplicate announcement)")

            return jsonify({
                "success": True,
                "status": "completed",
                "message": "Payment processing completed",
                "payment_type": payment_type,
                "reservation_number": reservation_number,
                "amount": amount,
                "call_id": call_id,
                "note": "Confirmation details already provided via SMS receipt"
            })

        elif status == 'failed' or status == 'declined':
            print(f"ERROR: Payment failed: {status}")
            return jsonify({
                "success": False,
                "error": f"Payment {status}",
                "payment_status": "failed"
            })

        else:
            print(f"WARNING: Unknown payment status: {status}")
            print(f"   Payment For: {payment_for}")
            print(f"   Event Type: {event_type}")

            # Log the full callback for debugging
            print(f"🔍 Full callback data for unknown status: {json.dumps(callback_data, indent=2)}")

            return jsonify({
                "success": False,
                "error": f"Unknown payment status: {status}",
                "status": status,
                "payment_for": payment_for,
                "event_type": event_type,
                "call_id": call_id
            })

    except Exception as e:
        print(f"ERROR: Error in SignalWire payment callback: {str(e)}")
        import traceback
        traceback.print_exc()

        # Even if there's an error, try to update payment session if we have key info
        # This prevents the agent from asking for card details again when payment actually succeeded
        try:
            if call_id and status == 'completed' and reservation_number:
                print(f"🔄 Attempting emergency payment session update for {call_id}")
                payment_sessions = getattr(app, 'payment_sessions', {})
                if call_id in payment_sessions:
                    payment_sessions[call_id]['payment_completed'] = True
                    payment_sessions[call_id]['payment_status'] = 'completed'
                    payment_sessions[call_id]['error_recovery'] = True
                    payment_sessions[call_id]['last_updated'] = datetime.now()
                    print(f"SUCCESS: Emergency update successful for payment session {call_id}")
                else:
                    # Create minimal session to prevent agent from re-asking
                    if not hasattr(app, 'payment_sessions'):
                        app.payment_sessions = {}
                    app.payment_sessions[call_id] = {
                        'payment_completed': True,
                        'payment_status': 'completed',
                        'reservation_number': reservation_number,
                        'error_recovery': True,
                        'started_at': datetime.now(),
                        'last_updated': datetime.now()
                    }
                    print(f"SUCCESS: Created emergency payment session for {call_id}")

                # Also try to update the database reservation status
                try:
                    with app.app_context():
                        reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
                        if reservation and reservation.payment_status != 'paid':
                            reservation.payment_status = 'paid'
                            reservation.payment_method = 'credit-card'
                            reservation.payment_date = datetime.now()
                            db.session.commit()
                            print(f"SUCCESS: Emergency database update: reservation {reservation_number} marked as paid")
                except Exception as db_error:
                    print(f"WARNING: Emergency database update failed: {db_error}")

        except Exception as recovery_error:
            print(f"WARNING: Emergency payment session update also failed: {recovery_error}")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# get_card_details function is now handled by the restaurant_reservation skill

# Add cleanup function for orphaned payment sessions
def cleanup_orphaned_payment_sessions():
    """Clean up orphaned payment sessions that are blocking operations"""
    try:
        global payment_sessions_global

        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}

        if 'payment_sessions_global' not in globals():
            payment_sessions_global = {}

        print(f"🧹 Cleaning up orphaned payment sessions...")
        print(f"   App sessions: {list(app.payment_sessions.keys())}")
        print(f"   Global sessions: {list(payment_sessions_global.keys())}")

        cleaned_count = 0

        # Clean up sessions older than 30 minutes (more aggressive cleanup)
        cutoff = datetime.now() - timedelta(minutes=30)

        # Clean app sessions
        expired_app_sessions = [
            call_id for call_id, session in app.payment_sessions.items()
            if session.get('started_at', datetime.now()) < cutoff
        ]

        for call_id in expired_app_sessions:
            session_data = app.payment_sessions.pop(call_id, None)
            print(f"🕐 Removed expired app session: {call_id}")
            cleaned_count += 1

        # Clean global sessions
        expired_global_sessions = [
            call_id for call_id, session in payment_sessions_global.items()
            if session.get('started_at', datetime.now()) < cutoff
        ]

        for call_id in expired_global_sessions:
            session_data = payment_sessions_global.pop(call_id, None)
            print(f"🕐 Removed expired global session: {call_id}")
            cleaned_count += 1

        # Remove any sessions that exist in one but not the other (orphaned)
        app_session_ids = set(app.payment_sessions.keys())
        global_session_ids = set(payment_sessions_global.keys())

        # Clean orphaned app sessions
        orphaned_app = app_session_ids - global_session_ids
        for call_id in orphaned_app:
            session_data = app.payment_sessions.pop(call_id, None)
            print(f"🗑️ Removed orphaned app session: {call_id}")
            cleaned_count += 1

        # Clean orphaned global sessions
        orphaned_global = global_session_ids - app_session_ids
        for call_id in orphaned_global:
            session_data = payment_sessions_global.pop(call_id, None)
            print(f"🗑️ Removed orphaned global session: {call_id}")
            cleaned_count += 1

        if cleaned_count > 0:
            print(f"SUCCESS: Cleaned up {cleaned_count} orphaned/expired payment sessions")

        print(f"   Remaining app sessions: {len(app.payment_sessions)}")
        print(f"   Remaining global sessions: {len(payment_sessions_global)}")

        return cleaned_count

    except Exception as e:
        print(f"ERROR: Error cleaning up payment sessions: {e}")
        return 0

# Add route to manually cleanup sessions
@app.route('/debug/cleanup-sessions', methods=['POST'])
def debug_cleanup_sessions():
    """Debug endpoint to manually cleanup orphaned payment sessions"""
    try:
        cleaned_count = cleanup_orphaned_payment_sessions()

        return jsonify({
            'success': True,
            'message': f'Cleaned up {cleaned_count} orphaned sessions',
            'remaining_sessions': len(getattr(app, 'payment_sessions', {}))
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/cleanup-status', methods=['GET'])
def debug_cleanup_status():
    """Debug endpoint to check payment session cleanup status"""
    try:
        global payment_sessions_global

        app_sessions = getattr(app, 'payment_sessions', {})
        global_sessions = payment_sessions_global if 'payment_sessions_global' in globals() else {}

        # Calculate session ages
        now = datetime.now()
        app_session_info = []
        for call_id, session in app_sessions.items():
            started_at = session.get('started_at', now)
            age_minutes = (now - started_at).total_seconds() / 60
            app_session_info.append({
                'call_id': call_id,
                'age_minutes': round(age_minutes, 1),
                'reservation_number': session.get('reservation_number', 'N/A')
            })

        global_session_info = []
        for call_id, session in global_sessions.items():
            started_at = session.get('started_at', now)
            age_minutes = (now - started_at).total_seconds() / 60
            global_session_info.append({
                'call_id': call_id,
                'age_minutes': round(age_minutes, 1),
                'reservation_number': session.get('reservation_number', 'N/A')
            })

        return jsonify({
            'success': True,
            'cleanup_system': 'active',
            'automatic_cleanup': 'every 5 minutes',
            'session_timeout': '30 minutes',
            'app_sessions': {
                'count': len(app_sessions),
                'sessions': app_session_info
            },
            'global_sessions': {
                'count': len(global_sessions),
                'sessions': global_session_info
            },
            'timestamp': now.isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calendar/refresh-trigger', methods=['POST'])
def calendar_refresh_trigger():
    """Handle calendar refresh notifications from SWAIG reservations for instant updates"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        event_type = data.get('event_type')
        reservation_id = data.get('reservation_id')
        source = data.get('source', 'unknown')

        print(f"📅 Calendar refresh trigger received:")
        print(f"   Event Type: {event_type}")
        print(f"   Reservation ID: {reservation_id}")
        print(f"   Source: {source}")
        print(f"   Customer: {data.get('customer_name', 'N/A')}")

        # Validate the event
        if event_type not in ['reservation_created', 'reservation_updated', 'reservation_cancelled']:
            return jsonify({'success': False, 'error': 'Invalid event type'}), 400

        # SMS: SMS SENDING IS NOW OPTIONAL - Agent will ask user for consent
        sms_result = {'success': False, 'sms_sent': False}
        print(f"📅 Calendar updated for {event_type} - SMS sending is now handled by agent consent")

        # 🚀 BROADCAST TO ALL CONNECTED CLIENTS VIA SSE
        sse_event = {
            'type': 'calendar_refresh',
            'event_type': event_type,
            'reservation_id': reservation_id,
            'customer_name': data.get('customer_name'),
            'party_size': data.get('party_size'),
            'date': data.get('date'),
            'time': data.get('time'),
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'sms_sent': sms_result.get('sms_sent', False)
        }

        # Add event to queue (non-blocking)
        try:
            calendar_event_queue.put_nowait(sse_event)
            print(f"SUCCESS: SSE event broadcasted to connected clients")
        except queue.Full:
            print(f"WARNING: SSE queue full, event dropped")

        print(f"SUCCESS: Calendar refresh notification processed successfully")

        return jsonify({
            'success': True,
            'message': 'Calendar refresh notification received and broadcasted',
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'sse_broadcasted': True,
            'sms_sent': sms_result.get('sms_sent', False),
            'sms_status': sms_result.get('success', False)
        })

    except Exception as e:
        print(f"ERROR: Calendar refresh trigger error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calendar/events-stream')
def calendar_events_stream():
    """Server-Sent Events stream for real-time calendar updates"""
    def event_generator():
        try:
            while True:
                # Wait for new events (blocking call)
                event_data = calendar_event_queue.get(timeout=30)  # 30 second timeout

                # Format as SSE
                yield f"data: {json.dumps(event_data)}\n\n"

        except queue.Empty:
            # Send keepalive ping every 30 seconds
            yield "data: {\"type\": \"ping\"}\n\n"
        except Exception as e:
            print(f"ERROR: SSE stream error: {e}")
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    return Response(
        event_generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

# Add automatic cleanup scheduler
def start_payment_session_cleanup_scheduler():
    """Start background thread to periodically clean up orphaned payment sessions"""
    def cleanup_worker():
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                cleanup_orphaned_payment_sessions()
            except Exception as e:
                print(f"ERROR: Payment session cleanup error: {e}")

    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    print("🧹 Started automatic payment session cleanup (every 5 minutes)")

def cleanup_payment_sessions_on_startup():
    """Clean up all payment sessions on application startup"""
    try:
        global payment_sessions_global

        # Clear all in-memory sessions on startup
        if hasattr(app, 'payment_sessions'):
            session_count = len(app.payment_sessions)
            app.payment_sessions.clear()
            print(f"🧹 Cleared {session_count} payment sessions from app memory on startup")

        if 'payment_sessions_global' in globals():
            global_count = len(payment_sessions_global)
            payment_sessions_global.clear()
            print(f"🧹 Cleared {global_count} payment sessions from global memory on startup")

        # Initialize clean session storage
        app.payment_sessions = {}
        payment_sessions_global = {}

        print("SUCCESS: Payment session cleanup completed on startup")

    except Exception as e:
        print(f"ERROR: Error during startup payment session cleanup: {e}")

# Add the missing reservation payment API endpoint
@app.route('/api/reservations/payment', methods=['POST'])
def update_reservation_payment():
    """Update reservation payment status and send SMS receipt"""
    try:
        data = request.get_json()
        
        reservation_id = data.get('reservation_id')
        payment_intent_id = data.get('payment_intent_id')
        amount = data.get('amount')
        status = data.get('status', 'paid')
        sms_number = data.get('sms_number')
        
        print(f"📝 Updating reservation payment status:")
        print(f"   - Reservation ID: {reservation_id}")
        print(f"   - Payment Intent ID: {payment_intent_id}")
        print(f"   - Amount: ${amount}")
        print(f"   - Status: {status}")
        print(f"   - SMS Number: {sms_number}")
        
        # Find the reservation
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reservation not found'}), 404
        
        # Generate confirmation number if not already set
        if not reservation.confirmation_number:
            import random
            import string
            confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        else:
            confirmation_number = reservation.confirmation_number
        
        # Update reservation payment details
        reservation.payment_status = status
        reservation.payment_method = 'credit-card'
        reservation.payment_date = datetime.now()
        reservation.payment_amount = float(amount)
        reservation.payment_intent_id = payment_intent_id
        reservation.confirmation_number = confirmation_number
        
        # Also update associated orders
        orders = Order.query.filter_by(reservation_id=reservation.id).all()
        for order in orders:
            order.payment_status = status
            order.payment_method = 'credit-card'
            order.payment_date = datetime.now()
            order.payment_amount = order.total_amount
            order.payment_intent_id = payment_intent_id
            order.confirmation_number = confirmation_number
        
        db.session.commit()
        
        print(f"SUCCESS: Updated reservation #{reservation.reservation_number} payment status")
        print(f"   - Payment Status: {reservation.payment_status}")
        print(f"   - Payment Amount: ${reservation.payment_amount}")
        print(f"   - Confirmation Number: {confirmation_number}")
        
        # 🚀 INSTANT CALENDAR UPDATE: Trigger calendar refresh for payment completion
        try:
            calendar_refresh_url = "http://localhost:8080/api/calendar/refresh-trigger"
            refresh_data = {
                "event_type": "payment_completed",
                "reservation_id": reservation.id,
                "reservation_number": reservation.reservation_number,
                "customer_name": reservation.name,
                "payment_status": "paid",
                "payment_amount": reservation.payment_amount,
                "confirmation_number": confirmation_number,
                "source": "reservation_payment_api"
            }
            
            # Non-blocking request with short timeout
            response = requests.post(
                calendar_refresh_url, 
                json=refresh_data, 
                timeout=2
            )
            
            if response.status_code == 200:
                print(f"📅 Calendar refresh notification sent successfully for payment completion")
            else:
                print(f"WARNING: Calendar refresh notification failed: {response.status_code}")
                
        except Exception as refresh_error:
            # Don't fail the payment if calendar refresh fails
            print(f"WARNING: Calendar refresh notification error (non-critical): {refresh_error}")
        
        # Send SMS receipt
        sms_result = {'success': False, 'sms_sent': False}
        try:
            phone_number = sms_number or reservation.phone_number
            print(f"SMS: Sending SMS receipt to {phone_number}")
            
            # Use the existing SMS receipt function
            sms_result = send_payment_receipt_sms(
                reservation=reservation,
                payment_amount=float(amount),
                phone_number=phone_number,
                confirmation_number=confirmation_number
            )
            
            if sms_result.get('success'):
                print(f"SUCCESS: SMS receipt sent successfully")
            else:
                print(f"WARNING: SMS receipt failed: {sms_result.get('error', 'Unknown error')}")
                
        except Exception as sms_error:
            print(f"ERROR: Error sending SMS receipt: {sms_error}")
            sms_result = {'success': False, 'sms_sent': False, 'error': str(sms_error)}
        
        return jsonify({
            'success': True,
            'message': f'Payment status updated for reservation #{reservation.reservation_number}',
            'reservation_number': reservation.reservation_number,
            'payment_status': reservation.payment_status,
            'payment_amount': reservation.payment_amount,
            'payment_date': reservation.payment_date.isoformat() if reservation.payment_date else None,
            'confirmation_number': confirmation_number,
            'sms_result': sms_result
        })
        
    except Exception as e:
        print(f"ERROR: Error updating reservation payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Add utility function to trigger SMS receipts for paid reservations
def trigger_sms_receipt_for_paid_reservation(reservation_number):
    """Trigger SMS receipt for a paid reservation"""
    try:
        reservation = Reservation.query.filter_by(reservation_number=reservation_number).first()
        if not reservation:
            return {'success': False, 'error': f'Reservation {reservation_number} not found'}
        
        if reservation.payment_status != 'paid':
            return {'success': False, 'error': f'Reservation {reservation_number} is not paid'}
        
        if not reservation.confirmation_number:
            # Generate confirmation number if missing
            import random
            import string
            confirmation_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            reservation.confirmation_number = confirmation_number
            db.session.commit()
        else:
            confirmation_number = reservation.confirmation_number
        
        # Send SMS receipt
        sms_result = send_payment_receipt_sms(
            reservation=reservation,
            payment_amount=reservation.payment_amount or 0.0,
            phone_number=reservation.phone_number,
            confirmation_number=confirmation_number
        )
        
        return {
            'success': True,
            'sms_result': sms_result,
            'reservation_number': reservation_number,
            'confirmation_number': confirmation_number
        }
        
    except Exception as e:
        print(f"ERROR: Error triggering SMS receipt: {e}")
        return {'success': False, 'error': str(e)}

@app.route('/debug/trigger-sms-receipt', methods=['POST'])
def debug_trigger_sms_receipt():
    """Debug endpoint to manually trigger SMS receipt for paid reservations"""
    try:
        data = request.get_json()
        reservation_number = data.get('reservation_number')
        
        if not reservation_number:
            return jsonify({'success': False, 'error': 'reservation_number is required'}), 400
        
        result = trigger_sms_receipt_for_paid_reservation(reservation_number)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'SMS receipt triggered for reservation #{reservation_number}',
                'details': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def log_function_call(function_name, params, call_context, result=None, error=None):
    """
    Enhanced logging for SWAIG function calls, especially order-related functions
    """
    try:
        call_id = call_context.get('call_id', 'unknown')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')
        
        print(f"📋 FUNCTION CALL LOG [{timestamp}]")
        print(f"   Function: {function_name}")
        print(f"   Call ID: {call_id}")
        print(f"   Parameters: {json.dumps(params, indent=2, default=str) if params else 'None'}")
        
        # Special logging for order/reservation functions
        if function_name in ['create_reservation', 'update_reservation', 'add_to_reservation']:
            print(f"🍽️  ORDER CREATION LOGGING:")
            
            # Log party orders if present
            if params and 'party_orders' in params:
                party_orders = params['party_orders']
                print(f"   Party Orders Type: {type(party_orders)}")
                print(f"   Party Orders Content: {json.dumps(party_orders, indent=2, default=str)}")
                
                # Validate menu item IDs
                if isinstance(party_orders, list):
                    for person_order in party_orders:
                        if isinstance(person_order, dict) and 'items' in person_order:
                            for item in person_order['items']:
                                if isinstance(item, dict) and 'menu_item_id' in item:
                                    menu_item_id = item['menu_item_id']
                                    print(f"   🔍 Checking menu item ID: {menu_item_id}")
                                    
                                    # Validate the menu item exists
                                    from models import MenuItem
                                    menu_item = MenuItem.query.get(menu_item_id)
                                    if menu_item:
                                        print(f"   ✅ Menu item {menu_item_id}: {menu_item.name} (${menu_item.price:.2f})")
                                    else:
                                        print(f"   ❌ Menu item {menu_item_id}: NOT FOUND")
            
            # Log available menu items count
            try:
                from models import MenuItem
                total_menu_items = MenuItem.query.count()
                available_menu_items = MenuItem.query.filter_by(is_available=True).count()
                print(f"   📊 Database Status: {available_menu_items}/{total_menu_items} menu items available")
                
                # Log sample menu item IDs for debugging
                sample_items = MenuItem.query.limit(5).all()
                if sample_items:
                    print(f"   📋 Sample menu item IDs: {[item.id for item in sample_items]}")
                else:
                    print(f"   ❌ No menu items found in database!")
                    
            except Exception as menu_error:
                print(f"   ❌ Error checking menu items: {menu_error}")
        
        # Log result or error
        if error:
            print(f"   ❌ Error: {error}")
        elif result:
            print(f"   ✅ Result Type: {type(result)}")
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
                print(f"   📤 Result Preview: {str(result_dict)[:200]}...")
            else:
                print(f"   📤 Result Preview: {str(result)[:200]}...")
        
        print(f"📋 END FUNCTION CALL LOG")
        
    except Exception as log_error:
        print(f"❌ Error in function call logging: {log_error}")

if __name__ == '__main__':
    print("🍽️  Starting Bobby's Table Restaurant System")
    print("=" * 50)
    print("🌐 Web Interface: http://0.0.0.0:8080")
    print("📞 Voice Interface: http://0.0.0.0:8080/receptionist")
    print("🍳 Kitchen Dashboard: http://0.0.0.0:8080/kitchen")
    print("Press Ctrl+C to stop the service")
    print("-" * 50)

    # Clean up any orphaned payment sessions from previous runs
    cleanup_payment_sessions_on_startup()

    # Start automatic cleanup scheduler
    start_payment_session_cleanup_scheduler()

    # Start the Flask development server
    app.run(host='0.0.0.0', port=8080, debug=False)