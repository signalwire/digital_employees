"""
Restaurant Menu Skill for SignalWire AI Agents with Data Validation
"""

import os
import json
import copy
from datetime import datetime, timedelta
from signalwire_agents.core.skill_base import SkillBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class RestaurantMenuSkill(SkillBase):
    """Restaurant menu skill with data validation"""
    
    SKILL_NAME = "restaurant_menu"
    SKILL_DESCRIPTION = "Browse menu items with validation"
    SKILL_VERSION = "1.0.0"
    REQUIRED_PACKAGES = []
    REQUIRED_ENV_VARS = []

    def __init__(self, agent=None, skill_params=None):
        super().__init__(agent)
        self.skill_params = skill_params or {}
        self.description = "Restaurant menu system with data validation"

    def setup(self):
        """Setup method required by SkillBase"""
        return True

    def _ensure_menu_cached(self, raw_data):
        """Cache menu with validation"""
        try:
            import sys
            import os
            
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from app import app
            from models import MenuItem
            
            with app.app_context():
                meta_data = raw_data.get('meta_data', {}) if raw_data else {}
                cache_time = meta_data.get('menu_cached_at')
                cached_menu = meta_data.get('cached_menu', [])
                
                if cache_time and cached_menu:
                    try:
                        cached_at = datetime.fromisoformat(cache_time)
                        if datetime.now() - cached_at < timedelta(minutes=10):
                            if self._validate_menu_cache(cached_menu):
                                print("Menu cache valid, using cached data")
                                return cached_menu, meta_data
                            else:
                                print("Menu cache validation failed, refreshing")
                                cached_menu = []
                        else:
                            print("Menu cache expired, refreshing")
                            cached_menu = []
                    except ValueError:
                        print("Invalid cache timestamp, refreshing")
                        cached_menu = []
                
                if not cached_menu:
                    print("Caching menu with validation")
                    menu_items = MenuItem.query.filter_by(is_available=True).all()
                    menu_items = sorted(menu_items, key=lambda item: len(item.name.lower()), reverse=True)
                    
                    cached_menu = []
                    for item in menu_items:
                        try:
                            menu_item_data = {
                                'id': int(item.id),
                                'name': str(item.name).strip(),
                                'price': float(item.price),
                                'category': str(item.category).strip(),
                                'description': str(item.description).strip(),
                                'is_available': bool(item.is_available)
                            }
                            
                            if self._validate_menu_item(menu_item_data):
                                cached_menu.append(menu_item_data)
                            else:
                                print(f"Skipping invalid menu item: {item.id}")
                        except Exception as item_error:
                            print(f"Error processing menu item {item.id}: {item_error}")
                            continue
                    
                    if not self._validate_menu_cache(cached_menu):
                        print("Menu cache validation failed after creation")
                        return [], raw_data.get('meta_data', {}) if raw_data else {}
                    
                    cached_menu = copy.deepcopy(cached_menu)
                    meta_data['cached_menu'] = cached_menu
                    meta_data['menu_cached_at'] = datetime.now().isoformat()
                    meta_data['menu_item_count'] = len(cached_menu)
                    
                    print(f"Successfully cached {len(cached_menu)} validated menu items")
                else:
                    print(f"Using validated cached menu with {len(cached_menu)} items")
                
                return cached_menu, meta_data
                
        except Exception as e:
            print(f"Error ensuring menu cache: {e}")
            return [], raw_data.get('meta_data', {}) if raw_data else {}

    def _validate_menu_item(self, item_data):
        """Validate a single menu item"""
        try:
            if not isinstance(item_data, dict):
                return False
            
            required_fields = ['id', 'name', 'price', 'category', 'description', 'is_available']
            for field in required_fields:
                if field not in item_data:
                    return False
            
            if not isinstance(item_data['id'], int) or item_data['id'] <= 0:
                return False
            
            if not isinstance(item_data['name'], str) or len(item_data['name'].strip()) == 0:
                return False
            
            if not isinstance(item_data['price'], (int, float)) or item_data['price'] < 0:
                return False
            
            if not isinstance(item_data['category'], str) or len(item_data['category'].strip()) == 0:
                return False
            
            if not isinstance(item_data['description'], str):
                return False
            
            if not isinstance(item_data['is_available'], bool):
                return False
            
            return True
            
        except Exception:
            return False

    def _validate_menu_cache(self, cached_menu):
        """Validate the complete menu cache"""
        try:
            if not isinstance(cached_menu, list):
                return False
            
            if len(cached_menu) == 0:
                return False
            
            seen_ids = set()
            valid_items = 0
            
            for i, item in enumerate(cached_menu):
                if not self._validate_menu_item(item):
                    return False
                
                item_id = item.get('id')
                if item_id in seen_ids:
                    return False
                seen_ids.add(item_id)
                valid_items += 1
            
            if len(cached_menu) > 500:
                return False
            
            if valid_items < 5:
                return False
            
            print(f"Menu cache validation passed: {valid_items} valid items")
            return True
            
        except Exception:
            return False

    def register_tools(self):
        """Register menu tools"""
        try:
            # Get menu tool
            self.agent.define_tool(
                name="get_menu",
                description="Show restaurant menu with validation",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Menu category to filter by",
                            "enum": ["breakfast", "appetizers", "main-courses", "desserts", "drinks"]
                        },
                        "format": {
                            "type": "string",
                            "enum": ["text", "json"],
                            "description": "Response format",
                            "default": "text"
                        }
                    },
                    "required": []
                },
                handler=self._get_menu_handler
            )
            print("Registered get_menu tool with validation")
            
            # Create order tool
            self.agent.define_tool(
                name="create_order",
                description="Create a standalone food order for pickup or delivery",
                parameters={
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Menu item name"},
                                    "quantity": {"type": "integer", "description": "Quantity to order", "default": 1}
                                },
                                "required": ["name"]
                            },
                            "description": "List of menu items to order"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer name for the order"
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Customer phone number"
                        },
                        "order_type": {
                            "type": "string",
                            "enum": ["pickup", "delivery"],
                            "description": "Order type - pickup or delivery",
                            "default": "pickup"
                        },
                        "customer_address": {
                            "type": "string",
                            "description": "Customer address (required for delivery orders)"
                        },
                        "special_instructions": {
                            "type": "string",
                            "description": "Special instructions for the order"
                        },
                        "payment_preference": {
                            "type": "string",
                            "enum": ["now", "pickup"],
                            "description": "When customer wants to pay",
                            "default": "pickup"
                        }
                    },
                    "required": ["items", "customer_name", "customer_phone"]
                },
                handler=self._create_order_handler
            )
            print("Registered create_order tool with validation")
            
            # Send reservation SMS tool  
            self.agent.define_tool(
                name="send_reservation_sms",
                description="Send SMS confirmation for reservation with pre-order details",
                parameters={
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Customer phone number"
                        },
                        "reservation_number": {
                            "type": "string", 
                            "description": "Reservation number"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer name"
                        },
                        "party_size": {
                            "type": "integer",
                            "description": "Number of people"
                        },
                        "reservation_date": {
                            "type": "string",
                            "description": "Reservation date"
                        },
                        "reservation_time": {
                            "type": "string", 
                            "description": "Reservation time"
                        },
                        "pre_order_total": {
                            "type": "number",
                            "description": "Pre-order total amount"
                        },
                        "message_type": {
                            "type": "string",
                            "enum": ["confirmation", "reminder", "update"],
                            "description": "Type of SMS message",
                            "default": "confirmation"
                        }
                    },
                    "required": ["phone_number", "reservation_number"]
                },
                handler=self._send_reservation_sms_handler
            )
            print("Registered send_reservation_sms tool")
            
            # Send payment receipt SMS tool  
            self.agent.define_tool(
                name="send_payment_receipt",
                description="Send SMS payment receipt confirmation",
                parameters={
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Customer phone number"
                        },
                        "reservation_number": {
                            "type": "string",
                            "description": "Reservation number"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer name"
                        },
                        "payment_amount": {
                            "type": "number",
                            "description": "Payment amount"
                        },
                        "confirmation_number": {
                            "type": "string",
                            "description": "Payment confirmation number"
                        },
                        "reservation_date": {
                            "type": "string",
                            "description": "Reservation date"
                        },
                        "reservation_time": {
                            "type": "string",
                            "description": "Reservation time"
                        },
                        "party_size": {
                            "type": "integer",
                            "description": "Number of people in party"
                        }
                    },
                    "required": ["phone_number", "reservation_number", "payment_amount"]
                },
                handler=self._send_payment_receipt_handler
            )
            print("Registered send_payment_receipt tool")
            
            # Check order status tool
            self.agent.define_tool(
                name="check_order_status",
                description="Check the status of a to-go order for pickup or delivery",
                parameters={
                    "type": "object",
                    "properties": {
                        "order_number": {
                            "type": "string",
                                                            "description": "5-digit order number"
                        },
                        "customer_phone": {
                            "type": "string", 
                            "description": "Customer phone number to look up order"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer name (optional, for verification)"
                        }
                    },
                    "required": []
                },
                handler=self._check_order_status_handler
            )
            print("Registered check_order_status tool")
            
        except Exception as e:
            print(f"Error registering restaurant menu tools: {e}")
            import traceback
            traceback.print_exc()

    def _get_menu_handler(self, args, raw_data):
        """Menu handler with validation"""
        try:
            cached_menu, meta_data = self._ensure_menu_cached(raw_data)
            
            if not cached_menu:
                result = SwaigFunctionResult("Sorry, the menu is currently unavailable.")
                result.set_metadata(meta_data)
                return result
            
            if args.get('category'):
                category = args['category'].lower()
                filtered_items = [item for item in cached_menu if item['category'].lower() == category]
                
                if not filtered_items:
                    result = SwaigFunctionResult(f"No items found in the {category} category.")
                    result.set_metadata(meta_data)
                    return result
                
                message = f"Here are our {category} items: "
                item_list = []
                for item in filtered_items[:20]:
                    item_list.append(f"{item['name']} for ${item['price']:.2f}")
                message += ", ".join(item_list)
                
                if len(filtered_items) > 20:
                    message += f" and {len(filtered_items) - 20} more items"
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
            else:
                categories = {}
                for item in cached_menu:
                    if item['category'] not in categories:
                        categories[item['category']] = []
                    categories[item['category']].append(item)
                
                message = f"Here's our menu with {len(cached_menu)} items: "
                for category, items in categories.items():
                    category_display = category.replace('-', ' ').title()
                    message += f"{category_display}: "
                    limited_items = items[:10]
                    item_list = []
                    for item in limited_items:
                        item_list.append(f"{item['name']} (${item['price']:.2f})")
                    message += ", ".join(item_list)
                    if len(items) > 10:
                        message += f" and {len(items) - 10} more"
                    message += ". "
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
                
        except Exception as e:
            print(f"Error in get_menu handler: {e}")
            return SwaigFunctionResult("Sorry, there was an error retrieving the menu.")

    def _get_random_party_orders(self, raw_data, party_names, food_per_person=1, drinks_per_person=1):
        """Generate random party orders for multiple people"""
        import random
        
        try:
            cached_menu, meta_data = self._ensure_menu_cached(raw_data)
            
            if not cached_menu:
                return {'success': False, 'error': 'Menu not available'}
            
            # Separate categories
            food_categories = ['breakfast', 'appetizers', 'main-courses', 'desserts']
            drink_categories = ['drinks']
            
            food_items = [item for item in cached_menu if item['category'] in food_categories]
            drink_items = [item for item in cached_menu if item['category'] in drink_categories]
            
            party_orders = []
            used_items = set()
            total_amount = 0.0
            
            for person_name in party_names:
                person_items = []
                person_total = 0.0
                
                # Select random food items
                available_food = [item for item in food_items if item['id'] not in used_items]
                if available_food:
                    for _ in range(min(food_per_person, len(available_food))):
                        if available_food:
                            selected_food = random.choice(available_food)
                            available_food.remove(selected_food)
                            used_items.add(selected_food['id'])
                            
                            person_items.append({
                                'menu_item_id': selected_food['id'],
                                'name': selected_food['name'],
                                'price': selected_food['price'],
                                'category': selected_food['category'],
                                'quantity': 1
                            })
                            person_total += selected_food['price']
                
                # Select random drink items
                available_drinks = [item for item in drink_items if item['id'] not in used_items]
                if available_drinks:
                    for _ in range(min(drinks_per_person, len(available_drinks))):
                        if available_drinks:
                            selected_drink = random.choice(available_drinks)
                            available_drinks.remove(selected_drink)
                            used_items.add(selected_drink['id'])
                            
                            person_items.append({
                                'menu_item_id': selected_drink['id'],
                                'name': selected_drink['name'],
                                'price': selected_drink['price'],
                                'category': selected_drink['category'],
                                'quantity': 1
                            })
                            person_total += selected_drink['price']
                
                party_orders.append({
                    'person_name': person_name,
                    'items': person_items,
                    'person_total': person_total
                })
                total_amount += person_total
            
            return {
                'success': True,
                'party_orders': party_orders,
                'total_amount': total_amount,
                'party_count': len(party_orders)
            }
            
        except Exception as e:
            print(f"Error generating random party orders: {e}")
            return {'success': False, 'error': str(e)}

    def _create_order_handler(self, args, raw_data):
        """Create a standalone food order with data validation"""
        try:
            import sys
            import os
            from datetime import datetime
            
            # Add the parent directory to sys.path to import app
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from app import app
            from models import Order, OrderItem, MenuItem, db
            
            with app.app_context():
                # Ensure menu is cached for item validation
                cached_menu, meta_data = self._ensure_menu_cached(raw_data)
                
                if not cached_menu:
                    result = SwaigFunctionResult("Sorry, our menu system is temporarily unavailable. Please try again later.")
                    result.set_metadata(meta_data)
                    return result
                
                # Validate required fields
                items = args.get('items', [])
                customer_name = args.get('customer_name')
                customer_phone = args.get('customer_phone')
                order_type = args.get('order_type', 'pickup')
                customer_address = args.get('customer_address', '')
                special_instructions = args.get('special_instructions', '')
                payment_preference = args.get('payment_preference', 'pickup')
                
                if not items:
                    result = SwaigFunctionResult("Please specify which items you'd like to order.")
                    result.set_metadata(meta_data)
                    return result
                
                if not customer_name or not customer_phone:
                    result = SwaigFunctionResult("I need your name and phone number to create the order.")
                    result.set_metadata(meta_data)
                    return result
                
                if order_type == 'delivery' and not customer_address:
                    result = SwaigFunctionResult("I need your delivery address for delivery orders.")
                    result.set_metadata(meta_data)
                    return result
                
                # Create menu lookup for faster access
                menu_lookup = {item['name'].lower(): item for item in cached_menu}
                
                # Validate and process items
                order_items = []
                total_amount = 0.0
                
                for item_spec in items:
                    item_name = item_spec.get('name', '').strip()
                    quantity = item_spec.get('quantity', 1)
                    
                    if not item_name:
                        continue
                    
                    # Find menu item with validation
                    menu_item = None
                    item_name_lower = item_name.lower()
                    
                    # Try exact match first
                    if item_name_lower in menu_lookup:
                        menu_item_data = menu_lookup[item_name_lower]
                    else:
                        # Try fuzzy matching
                        best_match = None
                        best_score = 0
                        
                        for cached_item in cached_menu:
                            cached_name_lower = cached_item['name'].lower()
                            
                            # Check for partial matches
                            if item_name_lower in cached_name_lower or cached_name_lower in item_name_lower:
                                # Calculate match score
                                common_words = set(item_name_lower.split()) & set(cached_name_lower.split())
                                score = len(common_words) / max(len(cached_name_lower.split()), 1)
                                
                                if score > best_score and score > 0.3:
                                    best_match = cached_item
                                    best_score = score
                        
                        menu_item_data = best_match
                    
                    if not menu_item_data:
                        result = SwaigFunctionResult(f"Sorry, I couldn't find '{item_name}' on our menu. Please check the menu and try again.")
                        result.set_metadata(meta_data)
                        return result
                    
                    if not menu_item_data['is_available']:
                        result = SwaigFunctionResult(f"Sorry, {menu_item_data['name']} is currently unavailable.")
                        result.set_metadata(meta_data)
                        return result
                    
                    # Validate quantity
                    try:
                        quantity = int(quantity)
                        if quantity <= 0:
                            quantity = 1
                    except (ValueError, TypeError):
                        quantity = 1
                    
                    # Add to order
                    item_total = menu_item_data['price'] * quantity
                    order_items.append({
                        'menu_item_id': menu_item_data['id'],
                        'name': menu_item_data['name'],
                        'quantity': quantity,
                        'price': menu_item_data['price'],
                        'total': item_total
                    })
                    total_amount += item_total
                
                if not order_items:
                    result = SwaigFunctionResult("No valid items found to order. Please check our menu and try again.")
                    result.set_metadata(meta_data)
                    return result
                
                # Generate order number
                import random
                import string
                order_number = ''.join(random.choices(string.digits, k=6))
                
                # Create the order
                new_order = Order(
                    order_number=order_number,
                    person_name=customer_name,
                    status='pending',
                    total_amount=total_amount,
                    order_type=order_type,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    special_instructions=special_instructions,
                    payment_status='pending',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(new_order)
                db.session.flush()  # Get the order ID
                
                # Add order items
                for item_data in order_items:
                    order_item = OrderItem(
                        order_id=new_order.id,
                        menu_item_id=item_data['menu_item_id'],
                        quantity=item_data['quantity'],
                        price_at_time=item_data['price']
                    )
                    db.session.add(order_item)
                
                db.session.commit()
                
                # Build confirmation message
                message = f"🍽️ ORDER CONFIRMED! 🍽️\n\n"
                message += f"📋 Order Number: {order_number}\n"
                message += f"👤 Customer: {customer_name}\n"
                message += f"📱 Phone: {customer_phone}\n"
                message += f"📦 Type: {order_type.title()}\n"
                
                if order_type == 'delivery':
                    message += f"📍 Address: {customer_address}\n"
                
                message += f"\n🍽️ Order Details:\n"
                for item_data in order_items:
                    message += f"• {item_data['quantity']}x {item_data['name']} - ${item_data['total']:.2f}\n"
                
                message += f"\n💰 Total: ${total_amount:.2f}\n"
                
                if special_instructions:
                    message += f"📝 Instructions: {special_instructions}\n"
                
                estimated_time = 20 if order_type == 'pickup' else 35
                message += f"\n⏰ Estimated {order_type} time: {estimated_time} minutes\n"
                
                if payment_preference == 'now':
                    message += f"\n💳 Payment will be processed now. Please have your payment method ready.\n"
                else:
                    message += f"\n💳 Payment due at {order_type}.\n"
                
                message += f"\nThank you for choosing Bobby's Table! We'll have your order ready soon."
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
                
        except Exception as e:
            print(f"Error creating order: {e}")
            import traceback
            traceback.print_exc()
            return SwaigFunctionResult("Sorry, there was an error creating your order. Please try again or call us directly.")



    def _send_reservation_sms_handler(self, args, raw_data):
        """Handle sending reservation SMS confirmations"""
        try:
            phone_number = args.get('phone_number', '').strip()
            reservation_number = args.get('reservation_number', '').strip()
            customer_name = args.get('customer_name', '').strip()
            party_size = args.get('party_size', 1)
            reservation_date = args.get('reservation_date', '').strip()
            reservation_time = args.get('reservation_time', '').strip()
            pre_order_total = args.get('pre_order_total', 0)
            message_type = args.get('message_type', 'confirmation')
            
            print(f"📱 SMS Reservation Confirmation Request:")
            print(f"   Phone: {phone_number}")
            print(f"   Reservation: {reservation_number}")
            print(f"   Customer: {customer_name}")
            print(f"   Party Size: {party_size}")
            print(f"   Date: {reservation_date}")
            print(f"   Time: {reservation_time}")
            print(f"   Pre-order Total: ${pre_order_total}")
            print(f"   Message Type: {message_type}")
            
            # Validate required fields
            if not phone_number:
                return SwaigFunctionResult("Phone number is required to send SMS confirmation.")
            
            if not reservation_number:
                return SwaigFunctionResult("Reservation number is required to send SMS confirmation.")
            
            # Send the SMS
            sms_result = self._send_reservation_sms(
                phone_number=phone_number,
                reservation_number=reservation_number,
                customer_name=customer_name,
                party_size=party_size,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                pre_order_total=pre_order_total,
                message_type=message_type
            )
            
            if sms_result.get('success', False):
                message = f"✅ SMS confirmation sent successfully to {phone_number}! "
                message += f"You should receive your reservation details shortly."
                
                # Update metadata
                meta_data = raw_data.get('meta_data', {}) if raw_data else {}
                meta_data.update({
                    'sms_sent': True,
                    'sms_phone': phone_number,
                    'sms_reservation': reservation_number,
                    'sms_timestamp': datetime.now().isoformat()
                })
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
            else:
                error_msg = sms_result.get('error', 'Unknown error')
                return SwaigFunctionResult(f"❌ Sorry, I couldn't send the SMS confirmation. {error_msg} Please try again or contact us directly.")
                
        except Exception as e:
            print(f"Error sending reservation SMS: {e}")
            return SwaigFunctionResult("Sorry, there was an error sending your SMS confirmation. Please try again or contact us directly.")

    def _send_reservation_sms(self, phone_number, reservation_number, customer_name=None, 
                             party_size=1, reservation_date=None, reservation_time=None, 
                             pre_order_total=0, message_type='confirmation'):
        """Send SMS confirmation for reservation - internal helper method"""
        try:
            from datetime import datetime
            
            # Build SMS message based on type
            if message_type == 'confirmation':
                sms_body = f"🍽️ Bobby's Table - Reservation Confirmed!\n\n"
                sms_body += f"📋 Reservation: #{reservation_number}\n"
                
                if customer_name:
                    sms_body += f"👤 Name: {customer_name}\n"
                
                if party_size and party_size > 1:
                    sms_body += f"👥 Party Size: {party_size} people\n"
                else:
                    sms_body += f"👥 Party Size: 1 person\n"
                
                if reservation_date:
                    sms_body += f"📅 Date: {reservation_date}\n"
                
                if reservation_time:
                    sms_body += f"⏰ Time: {reservation_time}\n"
                
                if pre_order_total and pre_order_total > 0:
                    sms_body += f"💰 Pre-order Total: ${pre_order_total:.2f}\n"
                
                sms_body += f"\n📍 Location: Bobby's Table Restaurant\n"
                sms_body += f"📞 Call us: (412) 612-7565\n\n"
                sms_body += f"We look forward to serving you!\n"
                sms_body += f"Reply STOP to opt out."
                
            elif message_type == 'reminder':
                sms_body = f"🔔 Bobby's Table - Reservation Reminder\n\n"
                sms_body += f"📋 Reservation: #{reservation_number}\n"
                sms_body += f"⏰ Your reservation is coming up!\n"
                if reservation_date and reservation_time:
                    sms_body += f"📅 {reservation_date} at {reservation_time}\n"
                sms_body += f"\nSee you soon at Bobby's Table!"
                
            else:  # update
                sms_body = f"📝 Bobby's Table - Reservation Update\n\n"
                sms_body += f"📋 Reservation: #{reservation_number}\n"
                sms_body += f"Your reservation has been updated.\n"
                if reservation_date and reservation_time:
                    sms_body += f"📅 New time: {reservation_date} at {reservation_time}\n"
                sms_body += f"\nQuestions? Call us: (412) 612-7565"
            
            # Get SignalWire credentials from environment
            signalwire_from_number = os.getenv('SIGNALWIRE_FROM_NUMBER', '+14126127565')
            
            print(f"📱 Sending SMS via SignalWire:")
            print(f"   From: {signalwire_from_number}")
            print(f"   To: {phone_number}")
            print(f"   Region: us")
            print(f"   Body: {repr(sms_body)}")
            
            # Use SignalWire send_sms method
            result = SwaigFunctionResult()
            result = result.send_sms(
                to_number=phone_number,
                from_number=signalwire_from_number,
                body=sms_body,
                region="us"
            )
            
            print(f"✅ SMS sent successfully to {phone_number}")
            print(f"📱 Result type: {type(result)}")
            print(f"📱 Result: {result}")
            
            if hasattr(result, 'to_dict'):
                print(f"📱 Result dict: {json.dumps(result.to_dict(), indent=2)}")
            
            return {'success': True, 'result': result}
            
        except Exception as e:
            print(f"Error sending reservation SMS: {e}")
            return {'success': False, 'error': f"SMS sending failed: {str(e)}"}

    def _send_payment_receipt_handler(self, args, raw_data):
        """Handle sending payment receipt SMS"""
        try:
            phone_number = args.get('phone_number', '').strip()
            reservation_number = args.get('reservation_number', '').strip()
            customer_name = args.get('customer_name', '').strip()
            payment_amount = args.get('payment_amount', 0)
            confirmation_number = args.get('confirmation_number', '').strip()
            reservation_date = args.get('reservation_date', '').strip()
            reservation_time = args.get('reservation_time', '').strip()
            party_size = args.get('party_size', 1)
            
            print(f"📱 SMS Payment Receipt Request:")
            print(f"   Phone: {phone_number}")
            print(f"   Reservation: {reservation_number}")
            print(f"   Customer: {customer_name}")
            print(f"   Payment Amount: ${payment_amount}")
            print(f"   Confirmation: {confirmation_number}")
            print(f"   Date: {reservation_date}")
            print(f"   Time: {reservation_time}")
            print(f"   Party Size: {party_size}")
            
            # Validate required fields
            if not phone_number:
                return SwaigFunctionResult("Phone number is required to send payment receipt.")
            
            if not reservation_number:
                return SwaigFunctionResult("Reservation number is required to send payment receipt.")
            
            if not payment_amount or payment_amount <= 0:
                return SwaigFunctionResult("Payment amount is required to send payment receipt.")
            
            # Send the SMS
            sms_result = self._send_payment_receipt(
                phone_number=phone_number,
                reservation_number=reservation_number,
                customer_name=customer_name,
                payment_amount=payment_amount,
                confirmation_number=confirmation_number,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                party_size=party_size
            )
            
            if sms_result.get('success', False):
                message = f"✅ Payment receipt sent successfully to {phone_number}! "
                message += f"Your payment confirmation has been delivered."
                
                # Update metadata
                meta_data = raw_data.get('meta_data', {}) if raw_data else {}
                meta_data.update({
                    'payment_sms_sent': True,
                    'payment_sms_phone': phone_number,
                    'payment_sms_reservation': reservation_number,
                    'payment_sms_amount': payment_amount,
                    'payment_sms_timestamp': datetime.now().isoformat()
                })
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
            else:
                error_msg = sms_result.get('error', 'Unknown error')
                return SwaigFunctionResult(f"❌ Sorry, I couldn't send the payment receipt. {error_msg} Please try again or contact us directly.")
                
        except Exception as e:
            print(f"Error sending payment receipt SMS: {e}")
            return SwaigFunctionResult("Sorry, there was an error sending your payment receipt. Please try again or contact us directly.")

    def _send_payment_receipt(self, phone_number, reservation_number, customer_name=None, 
                             payment_amount=0, confirmation_number=None, reservation_date=None, 
                             reservation_time=None, party_size=1):
        """Send SMS payment receipt - internal helper method"""
        try:
            from datetime import datetime
            
            # Build SMS message for payment receipt
            sms_body = f"💳 Bobby's Table - Payment Receipt\n\n"
            sms_body += f"📋 Reservation: #{reservation_number}\n"
            
            if customer_name:
                sms_body += f"👤 Name: {customer_name}\n"
            
            if party_size and party_size > 1:
                sms_body += f"👥 Party Size: {party_size} people\n"
            else:
                sms_body += f"👥 Party Size: 1 person\n"
            
            if reservation_date:
                sms_body += f"📅 Date: {reservation_date}\n"
            
            if reservation_time:
                sms_body += f"⏰ Time: {reservation_time}\n"
            
            sms_body += f"💰 Amount Paid: ${payment_amount:.2f}\n"
            
            if confirmation_number:
                sms_body += f"🔖 Confirmation: {confirmation_number}\n"
            
            sms_body += f"✅ Payment Status: COMPLETED\n"
            sms_body += f"📅 Processed: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}\n\n"
            sms_body += f"📍 Bobby's Table Restaurant\n"
            sms_body += f"📞 Questions? Call: (412) 612-7565\n\n"
            sms_body += f"Thank you for dining with us!\n"
            sms_body += f"Reply STOP to opt out."
            
            # Get SignalWire credentials from environment
            signalwire_from_number = os.getenv('SIGNALWIRE_FROM_NUMBER', '+14126127565')
            
            print(f"📱 Sending Payment Receipt SMS via SignalWire:")
            print(f"   From: {signalwire_from_number}")
            print(f"   To: {phone_number}")
            print(f"   Region: us")
            print(f"   Body: {repr(sms_body)}")
            
            # Use SignalWire send_sms method
            result = SwaigFunctionResult()
            result = result.send_sms(
                to_number=phone_number,
                from_number=signalwire_from_number,
                body=sms_body,
                region="us"
            )
            
            print(f"✅ Payment receipt SMS sent successfully to {phone_number}")
            print(f"📱 Result type: {type(result)}")
            print(f"📱 Result: {result}")
            
            if hasattr(result, 'to_dict'):
                print(f"📱 Result dict: {json.dumps(result.to_dict(), indent=2)}")
            
            return {'success': True, 'result': result}
            
        except Exception as e:
            print(f"Error sending payment receipt SMS: {e}")
            return {'success': False, 'error': f"SMS sending failed: {str(e)}"}

    def _check_order_status_handler(self, args, raw_data):
        """Handle checking order status"""
        try:
            import sys
            import os
            from datetime import datetime, timedelta
            
            # Add the parent directory to sys.path to import app
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from app import app
            from models import Order, OrderItem, MenuItem, db
            
            order_number = args.get('order_number', '').strip()
            customer_phone = args.get('customer_phone', '').strip()
            customer_name = args.get('customer_name', '').strip()
            
            print(f"📋 Check Order Status Request:")
            print(f"   Order Number: {order_number}")
            print(f"   Customer Phone: {customer_phone}")
            print(f"   Customer Name: {customer_name}")
            
            # Validate input - need either order number or phone number
            if not order_number and not customer_phone:
                return SwaigFunctionResult("I need either your order number or phone number to check your order status.")
            
            with app.app_context():
                # Build query based on available information
                query = Order.query
                
                if order_number:
                    # Clean up order number (remove any non-digits)
                    order_number_clean = ''.join(filter(str.isdigit, order_number))
                    query = query.filter(Order.order_number == order_number_clean)
                
                if customer_phone:
                    # Clean up phone number
                    phone_clean = ''.join(filter(str.isdigit, customer_phone))
                    if len(phone_clean) == 10:
                        phone_clean = f"+1{phone_clean}"
                    elif len(phone_clean) == 11 and phone_clean.startswith('1'):
                        phone_clean = f"+{phone_clean}"
                    elif not phone_clean.startswith('+'):
                        phone_clean = f"+{phone_clean}"
                    
                    query = query.filter(Order.customer_phone == phone_clean)
                
                # Get orders, prioritizing recent ones
                orders = query.order_by(Order.created_at.desc()).limit(5).all()
                
                if not orders:
                    if order_number:
                        return SwaigFunctionResult(f"❌ No order found with number {order_number}. Please check your order number and try again.")
                    else:
                        return SwaigFunctionResult(f"❌ No orders found for phone number {customer_phone}. Please check your phone number and try again.")
                
                # If multiple orders, show the most recent one or ask for clarification
                if len(orders) > 1 and not order_number:
                    message = f"📋 I found {len(orders)} orders for your phone number:\n\n"
                    for order in orders[:3]:  # Show up to 3 recent orders
                        message += f"• Order #{order.order_number} - {order.status.title()} - ${order.total_amount:.2f}\n"
                        message += f"  Placed: {order.created_at.strftime('%m/%d/%Y %I:%M %p')}\n"
                        if order.target_date and order.target_time:
                            message += f"  Ready: {order.target_date} at {order.target_time}\n"
                        message += "\n"
                    
                    message += "Please provide your specific order number to get detailed status information."
                    return SwaigFunctionResult(message)
                
                # Get the order (first one if multiple)
                order = orders[0]
                
                # Verify customer name if provided
                if customer_name and order.person_name:
                    name_match = customer_name.lower() in order.person_name.lower() or order.person_name.lower() in customer_name.lower()
                    if not name_match:
                        return SwaigFunctionResult(f"❌ The name provided doesn't match our records for order #{order.order_number}. Please verify your information.")
                
                # Build status message
                status_emoji = {
                    'pending': '⏳',
                    'preparing': '👨‍🍳',
                    'ready': '✅',
                    'completed': '📦',
                    'cancelled': '❌'
                }
                
                status_descriptions = {
                    'pending': 'Order received, waiting to be prepared',
                    'preparing': 'Order is being prepared in the kitchen',
                    'ready': 'Order is ready for pickup/delivery',
                    'completed': 'Order has been picked up/delivered',
                    'cancelled': 'Order has been cancelled'
                }
                
                message = f"📋 **ORDER STATUS UPDATE**\n\n"
                message += f"🔢 Order Number: #{order.order_number}\n"
                message += f"👤 Customer: {order.person_name or 'N/A'}\n"
                message += f"📱 Phone: {order.customer_phone or 'N/A'}\n"
                message += f"📦 Type: {order.order_type.title() if order.order_type else 'Pickup'}\n\n"
                
                message += f"{status_emoji.get(order.status, '📋')} **Status: {order.status.upper()}**\n"
                message += f"   {status_descriptions.get(order.status, 'Status information not available')}\n\n"
                
                # Add timing information
                if order.target_date and order.target_time:
                    try:
                        target_datetime = datetime.strptime(f"{order.target_date} {order.target_time}", "%Y-%m-%d %H:%M")
                        now = datetime.now()
                        
                        if order.status == 'ready':
                            message += f"🎯 **Ready for {order.order_type or 'pickup'}!**\n"
                            if order.order_type == 'pickup':
                                message += f"📍 Please come to Bobby's Table to collect your order.\n"
                            else:
                                message += f"🚚 Your order is ready for delivery to {order.customer_address or 'your address'}.\n"
                        elif order.status == 'preparing':
                            time_diff = target_datetime - now
                            if time_diff.total_seconds() > 0:
                                minutes_left = int(time_diff.total_seconds() // 60)
                                message += f"⏰ Estimated ready time: {target_datetime.strftime('%I:%M %p')} ({minutes_left} minutes)\n"
                            else:
                                message += f"⏰ Should be ready soon!\n"
                        elif order.status == 'pending':
                            message += f"⏰ Target ready time: {target_datetime.strftime('%I:%M %p')}\n"
                        elif order.status == 'completed':
                            message += f"✅ Completed at: {target_datetime.strftime('%I:%M %p')}\n"
                        
                        message += f"📅 Date: {target_datetime.strftime('%A, %B %d, %Y')}\n\n"
                        
                    except ValueError:
                        message += f"📅 Target: {order.target_date} at {order.target_time}\n\n"
                
                # Add order items
                if order.items:
                    message += f"🍽️ **Order Items:**\n"
                    for item in order.items:
                        item_name = item.menu_item.name if item.menu_item else "Unknown Item"
                        message += f"• {item.quantity}x {item_name} - ${item.price_at_time * item.quantity:.2f}\n"
                        if item.notes:
                            message += f"  Note: {item.notes}\n"
                    
                    message += f"\n💰 **Total: ${order.total_amount:.2f}**\n"
                
                # Add special instructions
                if order.special_instructions:
                    message += f"\n📝 Special Instructions: {order.special_instructions}\n"
                
                # Add delivery address if applicable
                if order.order_type == 'delivery' and order.customer_address:
                    message += f"\n📍 Delivery Address: {order.customer_address}\n"
                
                # Add payment status
                if order.payment_status:
                    payment_emoji = {'paid': '✅', 'unpaid': '⏳', 'refunded': '🔄'}
                    message += f"\n💳 Payment: {payment_emoji.get(order.payment_status, '❓')} {order.payment_status.title()}\n"
                
                # Add helpful next steps
                message += f"\n📞 Questions? Call us at (412) 612-7565\n"
                message += f"🏪 Bobby's Table Restaurant"
                
                # Update metadata
                meta_data = raw_data.get('meta_data', {}) if raw_data else {}
                meta_data.update({
                    'order_status_checked': True,
                    'order_number': order.order_number,
                    'order_status': order.status,
                    'order_type': order.order_type,
                    'check_timestamp': datetime.now().isoformat()
                })
                
                result = SwaigFunctionResult(message)
                result.set_metadata(meta_data)
                return result
                
        except Exception as e:
            print(f"Error checking order status: {e}")
            import traceback
            traceback.print_exc()
            return SwaigFunctionResult("Sorry, there was an error checking your order status. Please try again or contact us directly at (412) 612-7565.") 