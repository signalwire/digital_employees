from app import app, db
from models import Reservation, Table, MenuItem, Order, OrderItem
from datetime import datetime, timedelta
import random

def generate_order_number():
    """Generate a unique 5-digit order number"""
    while True:
        # Generate a 5-digit number (10000 to 99999)
        number = str(random.randint(10000, 99999))

        # Check if this number already exists
        existing = Order.query.filter_by(order_number=number).first()
        if not existing:
            return number

def generate_menu_item_id():
    """Generate a unique 3-digit menu item ID (100-999)"""
    while True:
        # Generate a 3-digit number (100 to 999)
        number = str(random.randint(100, 999))

        # Check if this number already exists
        existing = MenuItem.query.filter_by(id=number).first()
        if not existing:
            return number

def init_test_data():
    """Initialize the database with test data."""
    with app.app_context():
        # Clear existing data
        OrderItem.query.delete()
        Order.query.delete()
        Reservation.query.delete()
        Table.query.delete()
        MenuItem.query.delete()

        # Add test tables
        tables = [
            Table(table_number=1, capacity=2, status='available', location='Window'),
            Table(table_number=2, capacity=4, status='available', location='Center'),
            Table(table_number=3, capacity=6, status='available', location='Back'),
            Table(table_number=4, capacity=2, status='available', location='Window'),
            Table(table_number=5, capacity=4, status='available', location='Center'),
            Table(table_number=6, capacity=8, status='available', location='Private Room')
        ]
        db.session.add_all(tables)

        # Populate menu items with random 3-digit IDs
        populate_menu_items()

        # Add test reservations with dynamic dates (today + next 3 days)
        today = datetime.now().date()
        reservations = [
            Reservation(
                reservation_number='123456', 
                name='Johnson Family', 
                party_size=4, 
                date=str(today), 
                time='19:00', 
                phone_number='+1234567890', 
                status='confirmed',
                special_requests='Anniversary dinner, window table preferred',
                payment_status='unpaid'
            ),
            Reservation(
                reservation_number='789012', 
                name='Smith Party', 
                party_size=2, 
                date=str(today + timedelta(days=1)), 
                time='18:30', 
                phone_number='+1987654321', 
                status='confirmed',
                special_requests='Wheelchair Accessible',
                payment_status='unpaid'
            ),
            Reservation(
                reservation_number='345678', 
                name='Wilson Group', 
                party_size=6, 
                date=str(today + timedelta(days=2)), 
                time='20:00', 
                phone_number='+1122334455', 
                status='confirmed',
                special_requests='Business dinner, quiet table please',
                payment_status='unpaid'
            )
        ]
        db.session.add_all(reservations)

        # Add comprehensive test orders with mixed statuses for kitchen view
        db.session.flush()  # Ensure reservations have IDs

        # Orders for Johnson Family reservation
        johnson_orders = [
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[0].id, 
                table_id=1, 
                person_name='John Johnson', 
                status='pending', 
                total_amount=24.99,  # Ribeye Steak
                payment_status='unpaid',
                target_date=str(today),
                target_time='19:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[0].id, 
                table_id=1, 
                person_name='Sarah Johnson', 
                status='preparing', 
                total_amount=18.99,  # Grilled Salmon
                payment_status='paid',
                payment_amount=18.99,
                payment_intent_id='pi_test_sarah_johnson_001',
                payment_date=datetime.now() - timedelta(minutes=15),
                confirmation_number='ORD1001',
                payment_method='credit-card',
                target_date=str(today),
                target_time='19:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[0].id, 
                table_id=1, 
                person_name='Mike Johnson', 
                status='ready', 
                total_amount=12.99,  # Buffalo Wings
                payment_status='paid',
                payment_amount=12.99,
                payment_intent_id='pi_test_mike_johnson_002',
                payment_date=datetime.now() - timedelta(minutes=30),
                confirmation_number='ORD1002',
                payment_method='credit-card',
                target_date=str(today),
                target_time='19:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[0].id, 
                table_id=1, 
                person_name='Emma Johnson', 
                status='pending', 
                total_amount=6.99,  # Chocolate Cake
                payment_status='unpaid',
                target_date=str(today),
                target_time='19:00',
                order_type='reservation'
            )
        ]
        db.session.add_all(johnson_orders)
        db.session.flush()

        # Order items for Johnson Family (lookup menu item IDs by name)
        johnson_order_items = [
            # John's order - Ribeye Steak
            OrderItem(
                order_id=johnson_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Ribeye Steak').first().id, 
                quantity=1, 
                price_at_time=24.99
            ),
            # Sarah's order - Grilled Salmon
            OrderItem(
                order_id=johnson_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='Grilled Salmon').first().id, 
                quantity=1, 
                price_at_time=18.99
            ),
            # Mike's order - Buffalo Wings
            OrderItem(
                order_id=johnson_orders[2].id, 
                menu_item_id=MenuItem.query.filter_by(name='Buffalo Wings').first().id, 
                quantity=1, 
                price_at_time=12.99
            ),
            # Emma's order - Chocolate Cake
            OrderItem(
                order_id=johnson_orders[3].id, 
                menu_item_id=MenuItem.query.filter_by(name='Chocolate Cake').first().id, 
                quantity=1, 
                price_at_time=6.99
            )
        ]
        db.session.add_all(johnson_order_items)

        # Orders for Smith Party reservation
        smith_orders = [
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[1].id, 
                table_id=2, 
                person_name='Jane Smith', 
                status='preparing', 
                total_amount=21.98,  # Chicken Caesar Salad + Pepsi
                payment_status='paid', 
                payment_amount=21.98,
                payment_intent_id='pi_test_jane_smith_003',
                payment_date=datetime.now() - timedelta(minutes=20),
                confirmation_number='ORD2001',
                payment_method='credit-card',
                target_date=str(today + timedelta(days=1)),
                target_time='18:30',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[1].id, 
                table_id=2, 
                person_name='David Smith', 
                status='ready', 
                total_amount=17.98,  # BBQ Ribs + Iced Tea
                payment_status='paid',
                payment_amount=17.98,
                payment_intent_id='pi_test_david_smith_004',
                payment_date=datetime.now() - timedelta(minutes=25),
                confirmation_number='ORD2002',
                payment_method='credit-card',
                target_date=str(today + timedelta(days=1)),
                target_time='18:30',
                order_type='reservation'
            )
        ]
        db.session.add_all(smith_orders)
        db.session.flush()

        # Order items for Smith Party
        smith_order_items = [
            # Jane's order - Chicken Caesar Salad + Pepsi
            OrderItem(
                order_id=smith_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Chicken Caesar Salad').first().id, 
                quantity=1, 
                price_at_time=13.99
            ),
            OrderItem(
                order_id=smith_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Pepsi').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # David's order - BBQ Ribs + Iced Tea
            OrderItem(
                order_id=smith_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='BBQ Ribs').first().id, 
                quantity=1, 
                price_at_time=19.99
            ),
            OrderItem(
                order_id=smith_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='Iced Tea').first().id, 
                quantity=1, 
                price_at_time=2.99
            )
        ]
        db.session.add_all(smith_order_items)

        # Orders for Wilson Group reservation (all 6 party members)
        wilson_orders = [
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Bob Wilson', 
                status='pending', 
                total_amount=39.98,  # Sous Vide Ribeye + Iced Tea
                payment_status='unpaid',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Alice Wilson', 
                status='preparing', 
                total_amount=25.98,  # New York Strip + Coffee
                payment_status='paid',
                payment_amount=25.98,
                payment_intent_id='pi_test_alice_wilson_008',
                payment_date=datetime.now() - timedelta(minutes=10),
                confirmation_number='ORD3004',
                payment_method='credit-card',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Charlie Wilson', 
                status='pending', 
                total_amount=21.98,  # Grilled Salmon + Draft Beer
                payment_status='unpaid',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Diana Wilson', 
                status='pending', 
                total_amount=15.98,  # Chicken Caesar Salad + House Wine
                payment_status='unpaid',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Edward Wilson', 
                status='pending', 
                total_amount=18.98,  # BBQ Ribs + Pepsi
                payment_status='unpaid',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            ),
            Order(
                order_number=generate_order_number(), 
                reservation_id=reservations[2].id, 
                table_id=3, 
                person_name='Fiona Wilson', 
                status='pending', 
                total_amount=11.98,  # Buffalo Wings + Mountain Dew
                payment_status='unpaid',
                target_date=str(today + timedelta(days=2)),
                target_time='20:00',
                order_type='reservation'
            )
        ]
        db.session.add_all(wilson_orders)
        db.session.flush()

        # Order items for Wilson Group (all 6 party members)
        wilson_order_items = [
            # Bob's order - Sous Vide Ribeye + Iced Tea
            OrderItem(
                order_id=wilson_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Sous Vide Ribeye').first().id, 
                quantity=1, 
                price_at_time=36.99
            ),
            OrderItem(
                order_id=wilson_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Iced Tea').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Alice's order - New York Strip + Coffee
            OrderItem(
                order_id=wilson_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='New York Strip').first().id, 
                quantity=1, 
                price_at_time=22.99
            ),
            OrderItem(
                order_id=wilson_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='Coffee').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Charlie's order - Grilled Salmon + Draft Beer
            OrderItem(
                order_id=wilson_orders[2].id, 
                menu_item_id=MenuItem.query.filter_by(name='Grilled Salmon').first().id, 
                quantity=1, 
                price_at_time=18.99
            ),
            OrderItem(
                order_id=wilson_orders[2].id, 
                menu_item_id=MenuItem.query.filter_by(name='Draft Beer').first().id, 
                quantity=1, 
                price_at_time=4.99
            ),
            # Diana's order - Chicken Caesar Salad + House Wine
            OrderItem(
                order_id=wilson_orders[3].id, 
                menu_item_id=MenuItem.query.filter_by(name='Chicken Caesar Salad').first().id, 
                quantity=1, 
                price_at_time=13.99
            ),
            OrderItem(
                order_id=wilson_orders[3].id, 
                menu_item_id=MenuItem.query.filter_by(name='House Wine').first().id, 
                quantity=1, 
                price_at_time=6.99
            ),
            # Edward's order - BBQ Ribs + Pepsi
            OrderItem(
                order_id=wilson_orders[4].id, 
                menu_item_id=MenuItem.query.filter_by(name='BBQ Ribs').first().id, 
                quantity=1, 
                price_at_time=19.99
            ),
            OrderItem(
                order_id=wilson_orders[4].id, 
                menu_item_id=MenuItem.query.filter_by(name='Pepsi').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Fiona's order - Buffalo Wings + Mountain Dew
            OrderItem(
                order_id=wilson_orders[5].id, 
                menu_item_id=MenuItem.query.filter_by(name='Buffalo Wings').first().id, 
                quantity=1, 
                price_at_time=12.99
            ),
            OrderItem(
                order_id=wilson_orders[5].id, 
                menu_item_id=MenuItem.query.filter_by(name='Mountain Dew').first().id, 
                quantity=1, 
                price_at_time=2.99
            )
        ]
        db.session.add_all(wilson_order_items)

        # Standalone orders (pickup/delivery without reservations)
        standalone_orders = [
            Order(
                order_number=generate_order_number(),
                person_name='Lisa Chen',
                status='pending',
                total_amount=27.97,  # Classic Cheeseburger + Loaded Fries + Mountain Dew
                target_date=str(today),
                target_time='19:30',
                order_type='pickup',
                customer_phone='+15551234567',
                special_instructions='Extra spicy, no pickles',
                payment_status='paid',
                payment_amount=27.97,
                payment_intent_id='pi_test_lisa_chen_005',
                payment_date=datetime.now() - timedelta(minutes=10),
                confirmation_number='ORD3001',
                payment_method='credit-card'
            ),
            Order(
                order_number=generate_order_number(),
                person_name='Mark Rodriguez',
                status='preparing',
                total_amount=20.98,  # Fish and Chips + Draft Beer
                target_date=str(today),
                target_time='20:00',
                order_type='delivery',
                customer_phone='+15559876543',
                customer_address='123 Main St, Anytown, ST 12345',
                special_instructions='Ring doorbell twice, leave at door',
                payment_status='paid',
                payment_amount=20.98,
                payment_intent_id='pi_test_mark_rodriguez_006',
                payment_date=datetime.now() - timedelta(minutes=35),
                confirmation_number='ORD3002',
                payment_method='credit-card'
            ),
            Order(
                order_number=generate_order_number(),
                person_name='Rachel Green',
                status='ready',
                total_amount=16.98,  # Caesar Salad + Coffee
                target_date=str(today),
                target_time='18:45',
                order_type='pickup',
                customer_phone='+15554567890',
                special_instructions='Extra croutons',
                payment_status='paid',
                payment_amount=16.98,
                payment_intent_id='pi_test_rachel_green_007',
                payment_date=datetime.now() - timedelta(minutes=45),
                confirmation_number='ORD3003',
                payment_method='credit-card'
            ),
            Order(
                order_number='123456',
                person_name='Jim Smith',
                status='pending',
                total_amount=15.98,  # Buffalo Wings + Pepsi
                target_date=str(today),
                target_time='18:00',
                order_type='pickup',
                customer_phone='+15555555555',
                special_instructions='Test order for Stripe payment integration',
                payment_status='unpaid'
            ),
            Order(
                order_number=generate_order_number(),
                person_name='Bobby Brown',
                status='pending',
                total_amount=34.97,  # Ribeye Steak + House Wine + Coffee
                target_date=str(today + timedelta(hours=2)),
                target_time='19:00',
                order_type='pickup',
                customer_phone='+15551111111',
                special_instructions='Test order for comprehensive payment flow',
                payment_status='unpaid'
            ),
            Order(
                order_number=generate_order_number(),
                person_name='Bobby Smith',
                status='pending',
                total_amount=31.97,  # Grilled Salmon + Caesar Salad + Iced Tea
                target_date=str(today + timedelta(hours=2)),
                target_time='19:00',
                order_type='pickup',
                customer_phone='+15552222222',
                special_instructions='Test order for comprehensive payment flow',
                payment_status='unpaid'
            )
        ]
        db.session.add_all(standalone_orders)
        db.session.flush()

        # Order items for standalone orders
        standalone_order_items = [
            # Lisa Chen's order - Classic Cheeseburger + Loaded Fries + Mountain Dew
            OrderItem(
                order_id=standalone_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Classic Cheeseburger').first().id, 
                quantity=1, 
                price_at_time=13.99
            ),
            OrderItem(
                order_id=standalone_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Loaded Fries').first().id, 
                quantity=1, 
                price_at_time=8.99
            ),
            OrderItem(
                order_id=standalone_orders[0].id, 
                menu_item_id=MenuItem.query.filter_by(name='Mountain Dew').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Mark Rodriguez's order - Fish and Chips + Draft Beer
            OrderItem(
                order_id=standalone_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='Fish and Chips').first().id, 
                quantity=1, 
                price_at_time=15.99
            ),
            OrderItem(
                order_id=standalone_orders[1].id, 
                menu_item_id=MenuItem.query.filter_by(name='Draft Beer').first().id, 
                quantity=1, 
                price_at_time=4.99
            ),
            # Rachel Green's order - Caesar Salad + Coffee
            OrderItem(
                order_id=standalone_orders[2].id, 
                menu_item_id=MenuItem.query.filter_by(name='Caesar Salad').first().id, 
                quantity=1, 
                price_at_time=9.99
            ),
            OrderItem(
                order_id=standalone_orders[2].id, 
                menu_item_id=MenuItem.query.filter_by(name='Coffee').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Jim Smith's test order - Buffalo Wings + Pepsi
            OrderItem(
                order_id=standalone_orders[3].id, 
                menu_item_id=MenuItem.query.filter_by(name='Buffalo Wings').first().id, 
                quantity=1, 
                price_at_time=12.99
            ),
            OrderItem(
                order_id=standalone_orders[3].id, 
                menu_item_id=MenuItem.query.filter_by(name='Pepsi').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Bobby Brown's test order - Ribeye Steak + House Wine + Coffee
            OrderItem(
                order_id=standalone_orders[4].id, 
                menu_item_id=MenuItem.query.filter_by(name='Ribeye Steak').first().id, 
                quantity=1, 
                price_at_time=24.99
            ),
            OrderItem(
                order_id=standalone_orders[4].id, 
                menu_item_id=MenuItem.query.filter_by(name='House Wine').first().id, 
                quantity=1, 
                price_at_time=6.99
            ),
            OrderItem(
                order_id=standalone_orders[4].id, 
                menu_item_id=MenuItem.query.filter_by(name='Coffee').first().id, 
                quantity=1, 
                price_at_time=2.99
            ),
            # Bobby Smith's test order - Grilled Salmon + Caesar Salad + Iced Tea
            OrderItem(
                order_id=standalone_orders[5].id, 
                menu_item_id=MenuItem.query.filter_by(name='Grilled Salmon').first().id, 
                quantity=1, 
                price_at_time=18.99
            ),
            OrderItem(
                order_id=standalone_orders[5].id, 
                menu_item_id=MenuItem.query.filter_by(name='Caesar Salad').first().id, 
                quantity=1, 
                price_at_time=9.99
            ),
            OrderItem(
                order_id=standalone_orders[5].id, 
                menu_item_id=MenuItem.query.filter_by(name='Iced Tea').first().id, 
                quantity=1, 
                price_at_time=2.99
            )
        ]
        db.session.add_all(standalone_order_items)

        db.session.commit()
        print("Test data initialized successfully!")

def populate_menu_items():
    """Populate menu items with random 3-digit IDs"""
    menu_items_data = [
        # BREAKFAST
        {'name': 'Classic Pancakes', 'description': 'Three fluffy buttermilk pancakes with maple syrup and butter', 'price': 8.99, 'category': 'breakfast'},
        {'name': 'Blueberry Pancakes', 'description': 'Pancakes loaded with fresh blueberries and whipped cream', 'price': 9.99, 'category': 'breakfast'},
        {'name': 'Western Omelette', 'description': 'Three-egg omelette with ham, peppers, onions, and cheese', 'price': 10.99, 'category': 'breakfast'},
        {'name': 'Veggie Omelette', 'description': 'Three-egg omelette with mushrooms, spinach, tomatoes, and cheese', 'price': 9.99, 'category': 'breakfast'},
        {'name': 'Breakfast Burrito', 'description': 'Scrambled eggs, bacon, hash browns, and cheese wrapped in a flour tortilla', 'price': 9.49, 'category': 'breakfast'},
        {'name': 'French Toast', 'description': 'Thick-cut brioche bread with cinnamon, vanilla, and maple syrup', 'price': 8.99, 'category': 'breakfast'},
        {'name': 'Eggs Benedict', 'description': 'Poached eggs on English muffins with Canadian bacon and hollandaise', 'price': 12.99, 'category': 'breakfast'},
        {'name': 'Breakfast Platter', 'description': 'Two eggs any style, bacon or sausage, hash browns, and toast', 'price': 11.99, 'category': 'breakfast'},

        # APPETIZERS
        {'name': 'Buffalo Wings', 'description': 'Crispy chicken wings tossed in spicy buffalo sauce with blue cheese', 'price': 12.99, 'category': 'appetizers'},
        {'name': 'BBQ Wings', 'description': 'Chicken wings glazed with tangy BBQ sauce', 'price': 12.99, 'category': 'appetizers'},
        {'name': 'Truffle Fries', 'description': 'Hand-cut fries with truffle oil, parmesan, and fresh herbs', 'price': 14.99, 'category': 'appetizers'},
        {'name': 'Ahi Tuna Tartare', 'description': 'Fresh ahi tuna with avocado, cucumber, and sesame oil', 'price': 16.99, 'category': 'appetizers'},
        {'name': 'Charred Octopus', 'description': 'Mediterranean octopus with chickpea purée and olive tapenade', 'price': 18.99, 'category': 'appetizers'},
        {'name': 'Loaded Nachos', 'description': 'Tortilla chips topped with cheese, jalapeños, sour cream, and guacamole', 'price': 11.99, 'category': 'appetizers'},
        {'name': 'Spinach Artichoke Dip', 'description': 'Creamy spinach and artichoke dip served with tortilla chips', 'price': 9.99, 'category': 'appetizers'},
        {'name': 'Potato Skins', 'description': 'Crispy potato skins loaded with cheese, bacon, and green onions', 'price': 9.99, 'category': 'appetizers'},
        {'name': 'Onion Rings', 'description': 'Beer-battered onion rings served with ranch dressing', 'price': 7.99, 'category': 'appetizers'},
        {'name': 'Jalapeño Poppers', 'description': 'Jalapeños stuffed with cream cheese, wrapped in bacon', 'price': 8.99, 'category': 'appetizers'},
        {'name': 'Loaded Fries', 'description': 'French fries topped with cheese, bacon bits, and green onions', 'price': 8.99, 'category': 'appetizers'},
        {'name': 'Calamari Rings', 'description': 'Crispy fried squid rings with marinara and lemon', 'price': 10.99, 'category': 'appetizers'},

        # MAIN COURSES
        {'name': 'Classic Cheeseburger', 'description': '8oz beef patty with American cheese, lettuce, tomato, onion, and pickles', 'price': 13.99, 'category': 'main-courses'},
        {'name': 'Bacon Cheeseburger', 'description': '8oz beef patty with bacon, cheddar cheese, lettuce, tomato, and onion', 'price': 15.99, 'category': 'main-courses'},
        {'name': 'BBQ Burger', 'description': '8oz beef patty with BBQ sauce, onion rings, and cheddar cheese', 'price': 15.99, 'category': 'main-courses'},
        {'name': 'Mushroom Swiss Burger', 'description': '8oz beef patty with sautéed mushrooms and Swiss cheese', 'price': 15.99, 'category': 'main-courses'},
        {'name': 'Ribeye Steak', 'description': '12oz ribeye steak grilled to perfection with garlic butter', 'price': 24.99, 'category': 'main-courses'},
        {'name': 'Sous Vide Ribeye', 'description': '14oz precision-cooked ribeye with herb compound butter and roasted vegetables', 'price': 36.99, 'category': 'main-courses'},
        {'name': 'New York Strip', 'description': '10oz New York strip steak with herb butter', 'price': 22.99, 'category': 'main-courses'},
        {'name': 'Lobster Tagliatelle', 'description': 'Fresh lobster with house-made pasta in a light cream sauce', 'price': 32.99, 'category': 'main-courses'},
        {'name': 'Miso Glazed Salmon', 'description': 'Atlantic salmon with miso glaze, bok choy, and jasmine rice', 'price': 26.99, 'category': 'main-courses'},
        {'name': 'Grilled Salmon', 'description': 'Atlantic salmon with lemon dill sauce and seasonal vegetables', 'price': 18.99, 'category': 'main-courses'},
        {'name': 'Grilled Chicken Breast', 'description': 'Seasoned grilled chicken breast with lemon herb sauce', 'price': 16.99, 'category': 'main-courses'},
        {'name': 'BBQ Ribs', 'description': 'Full rack of baby back ribs with BBQ sauce and coleslaw', 'price': 19.99, 'category': 'main-courses'},
        {'name': 'Fish and Chips', 'description': 'Beer-battered cod with french fries and tartar sauce', 'price': 15.99, 'category': 'main-courses'},
        {'name': 'Vegan Buddha Bowl', 'description': 'Quinoa, roasted vegetables, avocado, and tahini dressing', 'price': 16.99, 'category': 'main-courses'},
        {'name': 'Caesar Salad', 'description': 'Crisp romaine lettuce with Caesar dressing, croutons, and parmesan', 'price': 9.99, 'category': 'main-courses'},
        {'name': 'Chicken Caesar Salad', 'description': 'Caesar salad topped with grilled chicken breast', 'price': 13.99, 'category': 'main-courses'},
        {'name': 'Heirloom Tomato Salad', 'description': 'Fresh heirloom tomatoes with burrata, basil, and balsamic reduction', 'price': 14.99, 'category': 'main-courses'},
        {'name': 'Chicken Tenders', 'description': 'Crispy chicken tenders with honey mustard and french fries', 'price': 12.99, 'category': 'main-courses'},
        {'name': 'Club Sandwich', 'description': 'Turkey, ham, bacon, lettuce, tomato, and mayo on toasted bread', 'price': 11.99, 'category': 'main-courses'},
        {'name': 'Buffalo Chicken Wrap', 'description': 'Crispy buffalo chicken with lettuce, tomato, and ranch in a tortilla', 'price': 10.99, 'category': 'main-courses'},

        # DESSERTS
        {'name': 'New York Cheesecake', 'description': 'Rich and creamy cheesecake with graham cracker crust', 'price': 6.99, 'category': 'desserts'},
        {'name': 'Chocolate Lava Cake', 'description': 'Warm chocolate cake with molten center and vanilla ice cream', 'price': 8.99, 'category': 'desserts'},
        {'name': 'Affogato', 'description': 'Vanilla gelato "drowned" in hot espresso with amaretti cookies', 'price': 7.99, 'category': 'desserts'},
        {'name': 'Chocolate Cake', 'description': 'Rich chocolate layer cake with chocolate frosting', 'price': 6.99, 'category': 'desserts'},
        {'name': 'Tiramisu', 'description': 'Traditional Italian dessert with coffee-soaked ladyfingers and mascarpone', 'price': 8.99, 'category': 'desserts'},
        {'name': 'Key Lime Pie', 'description': 'Tangy key lime pie with whipped cream', 'price': 6.99, 'category': 'desserts'},
        {'name': 'Crème Brûlée', 'description': 'Classic French custard with caramelized sugar top', 'price': 9.99, 'category': 'desserts'},

        # DRINKS - Non-Alcoholic
        {'name': 'Coca-Cola', 'description': 'Classic Coca-Cola soft drink', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Pepsi', 'description': 'Classic Pepsi cola soft drink', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Diet Pepsi', 'description': 'Zero-calorie Pepsi cola', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Mountain Dew', 'description': 'Citrus-flavored Pepsi product', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Sierra Mist', 'description': 'Lemon-lime soda by Pepsi', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Iced Tea', 'description': 'Freshly brewed iced tea', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Coffee', 'description': 'Freshly brewed coffee', 'price': 2.99, 'category': 'drinks'},
        {'name': 'Orange Juice', 'description': 'Freshly squeezed orange juice', 'price': 3.99, 'category': 'drinks'},
        {'name': 'Lemonade', 'description': 'House-made lemonade with fresh herbs and seasonal fruit', 'price': 5.99, 'category': 'drinks'},

        # DRINKS - Alcoholic
        {'name': 'Draft Beer', 'description': 'Selection of draft beers on tap', 'price': 4.99, 'category': 'drinks'},
        {'name': 'House Wine', 'description': 'Red or white house wine by the glass', 'price': 6.99, 'category': 'drinks'},
        {'name': 'Cucumber Gimlet', 'description': 'Hendricks gin with muddled cucumber, lime, and simple syrup', 'price': 12.99, 'category': 'drinks'},
        {'name': 'Sparkling Water', 'description': 'Premium sparkling water with lime', 'price': 3.99, 'category': 'drinks'},
    ]

    # Create menu items with random 3-digit IDs
    for item_data in menu_items_data:
        menu_item = MenuItem(
            id=generate_menu_item_id(),
            name=item_data['name'],
            description=item_data['description'],
            price=item_data['price'],
            category=item_data['category']
        )
        db.session.add(menu_item)  # Use add instead of merge since IDs are generated
    db.session.commit()

def create_demo_reservation_with_party_orders():
    """Create a demo reservation with party orders"""
    reservation = Reservation(
        reservation_number='111222',
        name='Smith Family',
        party_size=3,
        date='2025-06-10',
        time='18:30',
        phone_number='+15551234567',
        status='confirmed',
        special_requests='Window seat',
        payment_status='unpaid'
    )
    db.session.add(reservation)
    db.session.flush()
    party = [
        {'name': 'Bill', 'items': [('Classic Pancakes', 1), ('Coffee', 2)]},
        {'name': 'Susan', 'items': [('Western Omelette', 1), ('Orange Juice', 1)]},
        {'name': 'Tommy', 'items': [('Chocolate Cake', 1), ('Pepsi', 1)]},
    ]
    for person in party:
        order = Order(
            order_number=generate_order_number(),
            reservation_id=reservation.id,
            person_name=person['name'],
            status='pending',
            total_amount=0.0,
            payment_status='unpaid'
        )
        db.session.add(order)
        total = 0.0
        for item_name, qty in person['items']:
            menu_item = MenuItem.query.filter_by(name=item_name).first()
            if menu_item:
                db.session.add(OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    quantity=qty,
                    price_at_time=menu_item.price
                ))
                total += menu_item.price * qty
        order.total_amount = total
    db.session.commit()

def create_additional_demo_reservations():
    """Create additional demo reservations"""
    from models import Reservation, Order, OrderItem, MenuItem, db
    # Reservation 2
    reservation2 = Reservation(
        reservation_number='333444',
        name='Johnson Group',
        party_size=2,
        date='2025-06-11',
        time='12:00',
        phone_number='+15555678901',
        status='confirmed',
        special_requests='Birthday celebration',
        payment_status='unpaid'
    )
    db.session.add(reservation2)
    db.session.flush()
    party2 = [
        {'name': 'Alice', 'items': [('Caesar Salad', 1), ('Diet Pepsi', 1)]},
        {'name': 'Bob', 'items': [('Ribeye Steak', 1), ('Draft Beer', 1)]},
    ]
    for person in party2:
        order = Order(
            order_number=generate_order_number(),
            reservation_id=reservation2.id,
            person_name=person['name'],
            status='pending',
            total_amount=0.0,
            payment_status='unpaid'
        )
        db.session.add(order)
        total = 0.0
        for item_name, qty in person['items']:
            menu_item = MenuItem.query.filter_by(name=item_name).first()
            if menu_item:
                db.session.add(OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    quantity=qty,
                    price_at_time=menu_item.price
                ))
                total += menu_item.price * qty
        order.total_amount = total
    # Reservation 3
    reservation3 = Reservation(
        reservation_number='555666',
        name='Lee Family',
        party_size=4,
        date='2025-06-12',
        time='19:15',
        phone_number='+15559012345',
        status='confirmed',
        special_requests='High chair needed',
        payment_status='unpaid'
    )
    db.session.add(reservation3)
    db.session.flush()
    party3 = [
        {'name': 'David', 'items': [('BBQ Ribs', 1), ('Draft Beer', 1)]},
        {'name': 'Emma', 'items': [('Chicken Caesar Salad', 1), ('Lemonade', 1)]},
        {'name': 'Olivia', 'items': [('New York Cheesecake', 1), ('Coffee', 1)]},
        {'name': 'Lucas', 'items': [('Buffalo Wings', 1), ('Mountain Dew', 1)]},
    ]
    for person in party3:
        order = Order(
            order_number=generate_order_number(),
            reservation_id=reservation3.id,
            person_name=person['name'],
            status='pending',
            total_amount=0.0,
            payment_status='unpaid'
        )
        db.session.add(order)
        total = 0.0
        for item_name, qty in person['items']:
            menu_item = MenuItem.query.filter_by(name=item_name).first()
            if menu_item:
                db.session.add(OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    quantity=qty,
                    price_at_time=menu_item.price
                ))
                total += menu_item.price * qty
        order.total_amount = total
    db.session.commit()

def clear_existing_data():
    """Clear existing data from all tables"""
    from models import OrderItem, Order, Reservation, MenuItem, Table, db

    try:
        # Delete in order to respect foreign key constraints
        OrderItem.query.delete()
        Order.query.delete()
        Reservation.query.delete()
        Table.query.delete()
        MenuItem.query.delete()
        db.session.commit()
        print("Existing data cleared.")
    except Exception as e:
        print(f"Error clearing data: {e}")
        db.session.rollback()

def main():
    """Main function to initialize test data"""
    with app.app_context():
        db.create_all()
        clear_existing_data()
        init_test_data()

if __name__ == "__main__":
    main()
