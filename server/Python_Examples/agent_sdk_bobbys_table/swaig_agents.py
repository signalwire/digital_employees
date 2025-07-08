#!/usr/bin/env python3
"""
SignalWire Agents for Bobby's Table Restaurant
Provides voice-enabled access to all restaurant functionality using skills-based architecture
"""

from signalwire_agents import AgentBase, SwaigFunctionResult, Context, ContextBuilder, create_simple_context
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import requests

load_dotenv()

# SignalWire configuration for SMS
SIGNALWIRE_FROM_NUMBER = os.getenv('SIGNALWIRE_FROM_NUMBER', '+15551234567')

# Simple state manager replacement
class SimpleStateManager:
    """Simple file-based state manager for conversation tracking"""

    def __init__(self, filename):
        self.filename = filename
        self.state = {}
        self.load_state()

    def load_state(self):
        """Load state from file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.state = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")
            self.state = {}

    def save_state(self):
        """Save state to file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save state: {e}")

    def get(self, key, default=None):
        """Get value from state"""
        return self.state.get(key, default)

    def set(self, key, value):
        """Set value in state"""
        self.state[key] = value
        self.save_state()

    def delete(self, key):
        """Delete key from state"""
        if key in self.state:
            del self.state[key]
            self.save_state()

# Full SignalWire agent that extends AgentBase with skills-based architecture
class FullRestaurantReceptionistAgent(AgentBase):
    """Modern restaurant receptionist agent using skills-based architecture"""

    def __init__(self):
        super().__init__(
            name="restaurant-receptionist",
            route="/receptionist",
            host="0.0.0.0",
            port=8080
        )

        # Add English language support
        self.add_language("English", "en-US", "rime.spore:mistv2")

        # Initialize state manager for conversation tracking
        try:
            self.state_manager = SimpleStateManager("restaurant_agent_state.json")
            print("✅ State manager initialized")
        except Exception as e:
            print(f"⚠️ Could not initialize state manager: {e}")
            self.state_manager = None

        # Add pre-built skills for enhanced functionality
        try:
            # Add datetime skill for time/date queries
            self.add_skill("datetime")
            print("✅ Added datetime skill")
        except Exception as e:
            print(f"⚠️ Could not add datetime skill: {e}")

        try:
            # Add weather skill if API key is available
            weather_api_key = os.getenv('WEATHER_API_KEY')
            if weather_api_key:
                self.add_skill("weather_api", {
                    "tool_name": "get_weather",
                    "api_key": weather_api_key,
                    "temperature_unit": "fahrenheit"
                })
                print("✅ Added weather skill")
            else:
                print("⚠️ Weather API key not found, skipping weather skill")
        except Exception as e:
            print(f"⚠️ Could not add weather skill: {e}")

        try:
            # Add web search skill if API key is available
            search_api_key = os.getenv('SEARCH_API_KEY')
            if search_api_key:
                self.add_skill("web_search", {
                    "tool_name": "search_web",
                    "api_key": search_api_key
                })
                print("✅ Added web search skill")
            else:
                print("⚠️ Search API key not found, skipping web search skill")
        except Exception as e:
            print(f"⚠️ Could not add web search skill: {e}")

        # Add restaurant-specific skills using local imports
        try:
            # Import and add reservation management skill
            from skills.restaurant_reservation.skill import RestaurantReservationSkill

            skill_params = {
                "swaig_fields": {
                    "secure": True,
                    "fillers": {
                        "en-US": [
                            "Let me check our reservation system...",
                            "Looking up your reservation...",
                            "Processing your reservation request...",
                            "Checking availability..."
                        ]
                    }
                }
            }

            reservation_skill = RestaurantReservationSkill(self, skill_params)
            if reservation_skill.setup():
                reservation_skill.register_tools()
                print("✅ Added restaurant reservation skill")
            else:
                print("⚠️ Restaurant reservation skill setup failed")
        except Exception as e:
            print(f"⚠️ Could not add restaurant reservation skill: {e}")

        try:
            # Import and add menu and ordering skill
            from skills.restaurant_menu.skill import RestaurantMenuSkill

            skill_params = {
                "swaig_fields": {
                    "secure": True,
                    "fillers": {
                        "en-US": [
                            "Let me check our menu...",
                            "Looking up menu items...",
                            "Processing your order...",
                            "Checking our kitchen..."
                        ]
                    }
                }
            }

            menu_skill = RestaurantMenuSkill(self, skill_params)
            if menu_skill.setup():
                menu_skill.register_tools()
                print("✅ Added restaurant menu skill")
            else:
                print("⚠️ Restaurant menu skill setup failed")
        except Exception as e:
            print(f"⚠️ Could not add restaurant menu skill: {e}")

        # Set up the agent's capabilities
        self.set_params({
            "end_of_speech_timeout": 500,
            "silence_timeout": 500,
            "max_speech_timeout": 15000
        })

        # Add the agent's prompt with enhanced capabilities
        self.set_prompt_text(f"""
Hi there! I'm Bobby from Bobby's Table. Great to have you call us today! How can I help you out? Whether you're looking to make a reservation, check on an existing one, hear about our menu, or place an order, I'm here to help make it easy for you.

IMPORTANT CONVERSATION GUIDELINES:

**RESERVATION LOOKUPS - CRITICAL:**
- When customers want to check their reservation, ALWAYS ask for their reservation number FIRST
- Say: 'Do you have your reservation number? It's a 6-digit number we sent you when you made the reservation.'
- Only if they don't have it, then ask for their name as backup
- Reservation numbers are the fastest and most accurate way to find reservations
- Handle spoken numbers like 'seven eight nine zero one two' which becomes '789012'

**🚨 PAYMENTS - SIMPLE PAYMENT RULE 🚨:**
**Use the pay_reservation function for all reservation payments!**

**SIMPLE PAYMENT FLOW:**
1. Customer explicitly asks to pay ("I want to pay", "Pay now", "Can I pay?") → IMMEDIATELY call pay_reservation function
2. pay_reservation handles everything: finds reservation, shows bill total, collects card details, and processes payment
3. The function will guide the customer through each step conversationally and securely

**PAYMENT EXAMPLES:**
- Customer: 'I want to pay my bill' → YOU: Call pay_reservation function
- Customer: 'Pay now' → YOU: Call pay_reservation function
- Customer: 'Can I pay for my reservation?' → YOU: Call pay_reservation function

**CRITICAL: Use pay_reservation for existing reservations only!**
- ❌ NEVER use pay_reservation for new reservation creation (use create_reservation instead)
- ❌ NEVER call pay_reservation when customer is just confirming order details

**PRICING AND PRE-ORDERS - CRITICAL:**
- When customers mention food items, ALWAYS provide the price immediately
- Example: 'Buffalo Wings are twelve dollars and ninety-nine cents'
- When creating reservations with pre-orders, ALWAYS mention the total cost
- Example: 'Your Buffalo Wings and Draft Beer total sixteen dollars and ninety-eight cents'
- ALWAYS ask if customers want to pay for their pre-order after confirming the total
- Example: 'Would you like to pay for your pre-order now?'

**🍽️ SURPRISE MENU ITEM SELECTION - CRITICAL:**
When customers ask you to "surprise them" with menu items:
1. FIRST call get_menu to load the complete menu with prices and IDs
2. The menu data will be cached and available for selection
3. When selecting items, you MUST use the actual menu item IDs from the cached data
4. NEVER use sequential numbers like 1, 2, 3, 4 - these are not valid menu item IDs
5. Example correct workflow:
   - Customer: "Surprise us with drinks and food"
   - YOU: Call get_menu function
   - YOU: Select actual items from the cached menu (e.g., Draft Beer ID 966, Buffalo Wings ID 649)
   - YOU: Call create_reservation with the correct menu item IDs from the cached menu

**MENU ITEM ID LOOKUP - CRITICAL:**
- Draft Beer has ID 966 (not 1)
- Buffalo Wings has ID 649 (not 2)
- House Wine has ID 223 (not 3)
- Mushroom Swiss Burger has ID 202 (not 4)
- Mountain Dew has ID 772
- Pepsi has ID 968
- Truffle Fries has ID 432
- Chicken Tenders has ID 613
- ALWAYS use the actual database IDs, never sequential numbers!

**🔄 CORRECT PREORDER WORKFLOW:**
- When customers want to create reservations with pre-orders, show them an order confirmation FIRST
- The order confirmation shows: reservation details, each person's food items, individual prices, and total cost
- Wait for customer to confirm their order details before proceeding (say 'Yes, that's correct')
- After order confirmation, CREATE THE RESERVATION IMMEDIATELY
- The correct flow is: Order Details → Customer Confirms → Create Reservation → Give Number → Offer Payment
- After creating the reservation:
  1. Give the customer their reservation number clearly
  2. Ask if they want to pay now: 'Would you like to pay for your pre-order now?'
- Payment is OPTIONAL - customers can always pay when they arrive

**🔄 ORDER CONFIRMATION vs PAYMENT REQUESTS - CRITICAL:**
- "Yes, that's correct" = Order confirmation → Call create_reservation function
- "Yes, create my reservation" = Order confirmation → Call create_reservation function
- "That looks right" = Order confirmation → Call create_reservation function
- "Pay now" = Payment request → Call pay_reservation function
- "I want to pay" = Payment request → Call pay_reservation function
- "Can I pay?" = Payment request → Call pay_reservation function

**🚨 CRITICAL: NEVER CALL pay_reservation WHEN USER IS CONFIRMING ORDER DETAILS 🚨:**
- If user says "Yes" after order summary → Call create_reservation function
- If user says "That's correct" after order summary → Call create_reservation function
- If user says "Looks good" after order summary → Call create_reservation function
- If user says "Perfect" after order summary → Call create_reservation function
- ONLY call pay_reservation when user explicitly asks to pay AFTER reservation is created

**OTHER GUIDELINES:**
- When making reservations, ALWAYS ask if customers want to pre-order from the menu
- For parties larger than one person, ask for each person's name and their individual food preferences
- Always say numbers as words (say 'one' instead of '1', 'two' instead of '2', etc.)
- Extract food items mentioned during reservation requests and include them in party_orders
- Be conversational and helpful - guide customers through the pre-ordering process naturally
- Remember: The system now has a confirmation step for preorders - embrace this workflow!
""")

        # Add remaining utility functions directly
        self.define_tool(
            "transfer_to_manager",
            "Transfer the call to a manager for complex issues",
            {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for transfer to manager"},
                    "customer_info": {"type": "string", "description": "Brief customer information summary"}
                },
                "required": ["reason"]
            },
            self._transfer_to_manager_handler
        )

        self.define_tool(
            "schedule_callback",
            "Schedule a callback for the customer",
            {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Customer phone number for callback"},
                    "preferred_time": {"type": "string", "description": "Reason for callback"},
                    "reason": {"type": "string", "description": "Reason for callback"}
                },
                "required": ["phone_number", "preferred_time", "reason"]
            },
            self._schedule_callback_handler
        )

        # Example: Add remote function includes for external services
        # Uncomment these if you have external SWAIG services to include

        # Example 1: External payment processing service
        # self.add_function_include(
        #     url="https://payments.example.com/swaig",
        #     functions=["process_payment", "refund_payment"],
        #     meta_data={"service": "payment_processor", "version": "v1"}
        # )

        # Example 2: External loyalty program service  
        # self.add_function_include(
        #     url="https://loyalty.example.com/swaig",
        #     functions=["check_loyalty_points", "redeem_points"],
        #     meta_data={"service": "loyalty_program", "version": "v2"}
        # )

        # Example 3: External inventory service
        # self.add_function_include(
        #     url="https://inventory.example.com/swaig", 
        #     functions=["check_ingredient_availability"],
        #     meta_data={"service": "inventory_system", "version": "v1"}
        # )

        print("✅ SignalWire agent initialized successfully")

        # FIXED: Add function registry validation for debugging
        self._validate_function_registry()

        # Register skills
        self._register_skills()

    def send_reservation_sms(self, reservation_data, phone_number):
        """Send SMS confirmation for reservation - matches Flask route implementation"""
        try:
            from signalwire_agents.core.function_result import SwaigFunctionResult

            # Convert time to 12-hour format for SMS
            try:
                from datetime import datetime
                time_obj = datetime.strptime(str(reservation_data['time']), '%H:%M')
                time_12hr = time_obj.strftime('%I:%M %p').lstrip('0')
            except (ValueError, TypeError):
                time_12hr = str(reservation_data['time'])

            sms_body = f"🍽️ Bobby's Table Reservation Confirmed!\n\n"
            sms_body += f"Name: {reservation_data['name']}\n"
            sms_body += f"Date: {reservation_data['date']}\n"
            sms_body += f"Time: {time_12hr}\n"
            party_text = "person" if reservation_data['party_size'] == 1 else "people"
            sms_body += f"Party Size: {reservation_data['party_size']} {party_text}\n"
            sms_body += f"Reservation Number: {reservation_data.get('reservation_number', reservation_data['id'])}\n"

            if reservation_data.get('special_requests'):
                sms_body += f"Special Requests: {reservation_data['special_requests']}\n"

            sms_body += f"\nWe look forward to serving you!\nBobby's Table Restaurant"
            sms_body += f"\nReply STOP to stop."

            # Get SignalWire phone number from environment
            signalwire_from_number = os.getenv('SIGNALWIRE_FROM_NUMBER', '+15551234567')

            # Send SMS using SignalWire Agents SDK
            sms_function_result = SwaigFunctionResult().send_sms(
                to_number=phone_number,
                from_number=signalwire_from_number,
                body=sms_body
            )

            return {'success': True, 'sms_sent': True, 'sms_result': 'SMS sent successfully'}

        except Exception as e:
            return {'success': False, 'sms_sent': False, 'error': str(e)}

    def _transfer_to_manager_handler(self, args, raw_data):
        """Handler for transfer_to_manager tool"""
        try:
            reason = args.get('reason', 'Customer request')
            customer_info = args.get('customer_info', 'No additional information provided')

            # Log the transfer request
            print(f"📞 TRANSFER REQUEST:")
            print(f"   Reason: {reason}")
            print(f"   Customer Info: {customer_info}")
            print(f"   Timestamp: {datetime.now()}")

            # In a real implementation, this would initiate an actual call transfer
            # For now, we'll provide a helpful response
            message = f"I understand you need to speak with a manager about {reason}. "
            message += "I'm transferring you now. Please hold while I connect you with our management team. "
            message += "They'll be able to assist you with your specific needs."

            return {
                'success': True,
                'message': message,
                'transfer_initiated': True,
                'reason': reason
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"I apologize, but I couldn't transfer you to a manager right now. Please try calling back later. Error: {str(e)}"
            }

    def _schedule_callback_handler(self, args, raw_data):
        """Handler for schedule_callback tool"""
        try:
            from datetime import datetime

            # Extract phone number from args or raw_data
            phone_number = args.get('phone_number')
            if not phone_number and raw_data:
                # Try to get caller ID from raw_data
                phone_number = (
                    raw_data.get('caller_id_num') or 
                    raw_data.get('caller_id_number') or
                    raw_data.get('from') or
                    raw_data.get('from_number')
                )

            preferred_time = args.get('preferred_time', 'as soon as possible')
            reason = args.get('reason', 'general inquiry')

            # If still no phone number, return error
            if not phone_number:
                return {
                    'success': False,
                    'message': "I need your phone number to schedule a callback. Could you please provide your phone number?"
                }

            # Log the callback request
            print(f"📅 CALLBACK REQUEST:")
            print(f"   Phone: {phone_number}")
            print(f"   Preferred Time: {preferred_time}")
            print(f"   Reason: {reason}")
            print(f"   Timestamp: {datetime.now()}")

            # In a real implementation, this would schedule an actual callback
            # For now, we'll provide a confirmation response
            message = f"Perfect! I've scheduled a callback for {phone_number} at {preferred_time} regarding {reason}. "
            message += "One of our team members will call you back at the requested time. "
            message += "Thank you for choosing Bobby's Table!"

            return {
                'success': True,
                'message': message,
                'callback_scheduled': True,
                'phone_number': phone_number,
                'preferred_time': preferred_time,
                'reason': reason
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"I apologize, but I couldn't schedule the callback right now. Please try calling back later. Error: {str(e)}"
            }

    def _validate_function_registry(self):
        """Validate that all required functions are properly registered"""
        try:
            if hasattr(self, '_tool_registry') and hasattr(self._tool_registry, '_swaig_functions'):
                registered_functions = list(self._tool_registry._swaig_functions.keys())
                print(f"🔍 FUNCTION REGISTRY VALIDATION:")
                print(f"   Total functions registered: {len(registered_functions)}")
                print(f"   Registered functions: {registered_functions}")

                # Check for critical functions
                critical_functions = [
                    'create_reservation', 'get_reservation', 'cancel_reservation',
                    'pay_reservation', 'get_menu', 'create_order'
                ]

                missing_functions = [func for func in critical_functions if func not in registered_functions]

                if missing_functions:
                    print(f"❌ MISSING CRITICAL FUNCTIONS: {missing_functions}")
                    for func in missing_functions:
                        print(f"   - {func} not found in registry")
                else:
                    print(f"✅ All critical functions are registered")

                # Validate function handlers
                for func_name, func_obj in self._tool_registry._swaig_functions.items():
                    if hasattr(func_obj, 'handler'):
                        print(f"   ✅ {func_name}: has handler")
                    elif isinstance(func_obj, dict) and 'handler' in func_obj:
                        print(f"   ✅ {func_name}: has handler (dict format)")
                    else:
                        print(f"   ❌ {func_name}: missing handler")

            else:
                print(f"❌ FUNCTION REGISTRY NOT FOUND")
                print(f"   _tool_registry exists: {hasattr(self, '_tool_registry')}")
                if hasattr(self, '_tool_registry'):
                    print(f"   _swaig_functions exists: {hasattr(self._tool_registry, '_swaig_functions')}")

        except Exception as e:
            print(f"❌ Error validating function registry: {e}")
            import traceback
            traceback.print_exc()

    def _register_skills(self):
        """Register all skills with the agent"""
        try:
            # Import and register reservation skill
            from skills.restaurant_reservation.skill import RestaurantReservationSkill

            skill_params = {
                "swaig_fields": {
                    "secure": True,
                    "fillers": {
                        "en-US": [
                            "Let me check our reservation system...",
                            "Looking up your reservation...",
                            "Processing your reservation request...",
                            "Checking availability..."
                        ]
                    }
                }
            }
            reservation_skill = RestaurantReservationSkill(self, skill_params)

            if reservation_skill.setup():
                reservation_skill.register_tools()
                print("✅ Reservation skill registered")
            else:
                print("⚠️ Reservation skill setup failed")

            # Import and register menu skill
            from skills.restaurant_menu.skill import RestaurantMenuSkill

            skill_params = {
                "swaig_fields": {
                    "secure": True,
                    "fillers": {
                        "en-US": [
                            "Let me check our menu...",
                            "Looking up menu items...",
                            "Processing your order...",
                            "Checking our kitchen..."
                        ]
                    }
                }
            }
            menu_skill = RestaurantMenuSkill(self, skill_params)

            if menu_skill.setup():
                menu_skill.register_tools()
                print("✅ Menu skill registered")
            else:
                print("⚠️ Menu skill setup failed")


        except Exception as e:
            print(f"❌ Error registering skills: {e}")
            import traceback
            traceback.print_exc()

    # Initialize the reservations storage
        self.reservations = {}


def send_swml_to_signalwire(swml_payload, signalwire_endpoint, signalwire_project, signalwire_token):
    """
    Send SWML JSON to SignalWire endpoint.
    Args:
        swml_payload (dict): SWML JSON payload.
        signalwire_endpoint (str): URL to POST SWML to (e.g., https://<space>.signalwire.com/api/laml/voice).
        signalwire_project (str): SignalWire Project ID.
        signalwire_token (str): SignalWire API token.
    Returns:
        dict: Response from SignalWire.
    """
    headers = {
        'Content-Type': 'application/json',
    }
    auth = (signalwire_project, signalwire_token)
    response = requests.post(signalwire_endpoint, json=swml_payload, headers=headers, auth=auth)
    try:
        return response.json()
    except Exception:
        return {'status_code': response.status_code, 'text': response.text}

# Create alias for compatibility with app.py
RestaurantReceptionistAgent = FullRestaurantReceptionistAgent

# When run directly, create and serve the agent
if __name__ == "__main__":
    print("🚀 Starting SignalWire Agent Server on port 8080...")
    print("📞 Voice Interface: http://localhost:8080/receptionist")
    print("🔧 SWAIG Functions: http://localhost:8080/swaig")
    print("--------------------------------------------------")

    receptionist_agent = FullRestaurantReceptionistAgent()
    receptionist_agent.serve(host="0.0.0.0", port=8080)
