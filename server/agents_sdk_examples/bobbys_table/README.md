
# Bobby's Table Restaurant Management System

A comprehensive restaurant management system with integrated web and voice interfaces powered by SignalWire Agents Python SDK.

## 🚀 Quick Start

### Run on Replit

Click the button below to import and run this project on Replit:

[![Run on Replit](https://replit.com/badge?theme=dark&variant=small)](https://replit.com/new/github/Len-PGH/agent_sdk_bobbys_table)

### Start the Integrated Service

```bash
# Start the integrated web and voice interface
python start_agents.py
```

This will start a single service on port 8080 with:
- **Web Interface**: http://localhost:8080 (Full restaurant management)
- **Voice Interface**: http://localhost:8080/receptionist (Phone-based ordering and reservations)
- **Kitchen Dashboard**: http://localhost:8080/kitchen (Order management)

### Test Voice Functions

```bash
# Test all SWAIG voice functions via HTTP
python test_swaig_functions.py
```

## 🎯 SWAIG Skills Architecture

Bobby's Table uses SignalWire's AI Gateway (SWAIG) with a modular skills-based architecture. Each skill provides specific functionality that can be combined for comprehensive restaurant operations.

### 📞 Voice Interface

**Primary SWAIG Endpoint**: `/receptionist`
- **URL**: `http://localhost:8080/receptionist`
- **Authentication**: Basic Auth (admin/admin)
- **Purpose**: Main voice interface for all restaurant functions

### 🛠️ Available Skills

#### Restaurant Reservation Skill (`skills/restaurant_reservation/skill.py`)

Provides comprehensive reservation management capabilities:

- **`create_reservation`** - Make new reservations with full details, pre-ordering support
- **`get_reservation`** - Search reservations by any criteria (name, phone, ID, date, party size)
- **`update_reservation`** - Modify existing reservations or add items to pre-orders
- **`cancel_reservation`** - Cancel reservations with verification
- **`add_to_reservation`** - Add food items to existing reservations
- **`pay_reservation`** - Process payments for reservations with pre-orders
- **`check_payment_status`** - Verify payment completion status
- **`retry_payment`** - Handle failed payment retries
- **`get_calendar_events`** - Retrieve calendar data for reservations
- **`get_todays_reservations`** - Get today's reservation schedule
- **`get_reservation_summary`** - Generate reservation analytics

#### Restaurant Menu Skill (`skills/restaurant_menu/skill.py`)

Handles all menu-related operations and ordering:

- **`get_menu`** - Browse menu items by category or view complete menu
- **`create_order`** - Place orders for pickup or delivery with intelligent item extraction
- **`add_item_to_order`** - Add additional items to orders being built
- **`finalize_order`** - Complete and confirm orders
- **`get_order_status`** - Check order preparation status
- **`update_order_status`** - Update order status (kitchen use)
- **`update_pending_order`** - Modify pending orders (add/remove items, change details)
- **`get_kitchen_orders`** - Kitchen dashboard order filtering
- **`get_order_queue`** - Current order queue organized by status
- **`get_kitchen_summary`** - Kitchen operations analytics
- **`pay_order`** - Process payments for orders

### 🔧 Skills Features

#### Advanced Natural Language Processing
- **Fuzzy Item Matching**: Handles misspellings and variations ("wings" → "Buffalo Wings")
- **Conversation Context**: Extracts information from natural conversation flow
- **Smart Suggestions**: Recommends complementary items (drinks with food orders)
- **Multi-format Support**: Handles various date/time formats and spoken numbers

#### Payment Integration
- **Stripe Integration**: Secure credit card processing via SignalWire pay verb
- **Payment Session Management**: Tracks payment states across conversation flows
- **SMS Receipts**: Automatic confirmation messages
- **Payment Retry**: Handles failed payments with appropriate user guidance

#### Real-time Synchronization
- **Shared Database**: All skills use the same SQLite database
- **Cross-skill Communication**: Reservations can include pre-orders processed by menu skill
- **Session Management**: Maintains context across skill transitions

## 🌐 Web Interface Features

The web interface provides a complete restaurant management dashboard:

- **Reservation Calendar**: Visual calendar with drag-and-drop functionality
- **Menu Management**: Browse and order from categorized menu items
- **Shopping Cart**: Add items to cart with quantity management
- **Order Tracking**: Real-time order status updates
- **Kitchen Dashboard**: Three-column workflow (Pending → Preparing → Ready)
- **Time Filtering**: Filter orders by date and time ranges
- **Payment Processing**: Integrated Stripe checkout

## 🏗️ Integrated Architecture

```
┌─────────────────┐    ┌─────────────────────────────────────┐
│   SignalWire    │    │         Flask App (Port 8080)       │
│   Platform      │◄──►│  ┌─────────────┐ ┌─────────────────┐ │
└─────────────────┘    │  │ Web Routes  │ │ SWAIG Skills    │ │
                       │  │             │ │ (/receptionist) │ │
                       │  └─────────────┘ └─────────────────┘ │
                       │              │                      │
                       │              ▼                      │
                       │         ┌─────────────────┐         │
                       │         │   SQLite DB     │         │
                       │         │   (Shared)      │         │
                       │         └─────────────────┘         │
                       └─────────────────────────────────────┘
```

## 📋 Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [API Endpoints](#api-endpoints)
5. [SWAIG Skills](#swaig-skills)
6. [Development](#development)
7. [Deployment](#deployment)

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- SignalWire account (for voice features)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bobbystable
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**
   ```bash
   python init_db.py
   python init_test_data.py  # Optional: Add sample data
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your SignalWire credentials
   ```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# SignalWire Configuration
SIGNALWIRE_PROJECT_ID=your_project_id
SIGNALWIRE_TOKEN=your_token
SIGNALWIRE_SPACE_URL=your_space_url
SIGNALWIRE_FROM_NUMBER=+1234567890

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your_secret_key

# Database
DATABASE_URL=sqlite:///instance/restaurant.db

# Payment Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
SIGNALWIRE_PAYMENT_CONNECTOR_URL=https://your-ngrok-url.ngrok.io
```

## 🚀 Usage

### Start the Integrated Service

```bash
# Start the integrated web and voice interface
python start_agents.py
```

### Alternative: Start Flask App Directly

```bash
# Start Flask app with integrated SWAIG functions
python app.py
```

### Access the Application

- **Web Interface**: http://localhost:8080
- **Voice Interface**: http://localhost:8080/receptionist
- **Kitchen Dashboard**: http://localhost:8080/kitchen

## 🔌 API Endpoints

### Reservations

- `GET /api/reservations` - List all reservations
- `POST /api/reservations` - Create new reservation
- `GET /api/reservations/<id>` - Get specific reservation
- `PUT /api/reservations/<id>` - Update reservation
- `DELETE /api/reservations/<id>` - Delete reservation
- `GET /api/reservations/calendar` - Get calendar events

### Menu Items

- `GET /api/menu_items` - List all menu items
- `GET /api/menu_items/<id>` - Get specific menu item

### Orders

- `GET /api/orders` - List all orders
- `POST /api/orders` - Create new order
- `PUT /api/orders/<id>/status` - Update order status

### SWAIG Endpoint

- `POST /receptionist` - Handle all voice function calls
- `GET /receptionist` - Get SWML document for agent configuration

## 📞 SWAIG Skills Documentation

### Reservation Management Skills

#### create_reservation
Creates new restaurant reservations with optional pre-ordering.

**Parameters:**
- `name` (string): Customer name
- `party_size` (integer): Number of people
- `date` (string): Reservation date (YYYY-MM-DD)
- `time` (string): Reservation time (HH:MM)
- `phone_number` (string): Customer phone number
- `special_requests` (string): Special requests
- `party_orders` (array): Optional pre-orders for party members

**Features:**
- Automatic phone number normalization
- Date/time validation and format conversion
- Duplicate reservation prevention
- SMS confirmation sending
- Pre-order integration with menu skill

#### get_reservation
Look up existing reservations using multiple search criteria.

**Parameters:**
- `phone_number` (string): Customer phone
- `name` (string): Customer name (full, first, or last)
- `reservation_number` (string): 6-digit reservation number
- `confirmation_number` (string): Payment confirmation number
- `date` (string): Reservation date
- `format` (string): Response format ("text" or "json")

**Features:**
- Fuzzy name matching
- Multiple phone number format support
- Conversation context extraction
- Payment status integration

### Menu & Ordering Skills

#### get_menu
Browse restaurant menu items with intelligent categorization.

**Parameters:**
- `category` (string): Menu category filter (optional)
- `format` (string): Response format ("text" or "json")

**Categories:**
- breakfast, appetizers, main-courses, desserts, drinks

**Features:**
- Voice-optimized text formatting
- Menu caching for performance
- Category-specific recommendations

#### create_order
Place orders with natural language item extraction.

**Parameters:**
- `items` (array): Menu items with quantities
- `customer_name` (string): Customer name
- `customer_phone` (string): Customer phone
- `order_type` (string): "pickup" or "delivery"
- `payment_preference` (string): "now" or "pickup"
- `special_instructions` (string): Special requests
- `customer_address` (string): Delivery address (for delivery orders)

**Features:**
- Natural language item parsing
- Drink suggestions based on food orders
- Automatic order number generation
- SMS order confirmation
- Payment integration

## 🧪 Testing

### Run All Tests

```bash
# Test SWAIG functions
python test_swaig_functions.py

# Test web functionality (manual testing via browser)
python app.py
```

### Test Individual Skills

```bash
# Test database models
python -c "from models import *; print('Models imported successfully')"

# Test skill imports
python -c "from skills.restaurant_reservation.skill import RestaurantReservationSkill; print('Reservation skill imported')"
python -c "from skills.restaurant_menu.skill import RestaurantMenuSkill; print('Menu skill imported')"
```

## 🔧 Development

### Project Structure

```
bobbystable/
├── app.py                     # Main Flask application with SWAIG integration
├── swaig_agents.py           # SignalWire agents with skills-based architecture
├── models.py                 # Database models
├── start_agents.py           # Startup script
├── skills/                   # Modular skills architecture
│   ├── restaurant_reservation/
│   │   ├── __init__.py
│   │   └── skill.py         # Reservation management skill
│   ├── restaurant_menu/
│   │   ├── __init__.py
│   │   └── skill.py         # Menu and ordering skill
│   └── utils.py             # Shared utilities
├── templates/               # HTML templates
├── static/                 # CSS, JS, images
├── instance/               # Database files
└── requirements.txt        # Python dependencies
```

### Adding New Skills

1. **Create skill directory**: `skills/your_skill/`
2. **Implement skill class**: Extend `SkillBase` from SignalWire Agents SDK
3. **Register tools**: Define SWAIG functions in `register_tools()`
4. **Add to agent**: Import and add skill in `swaig_agents.py`

Example skill structure:
```python
from signalwire_agents.core.skill_base import SkillBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class YourSkill(SkillBase):
    SKILL_NAME = "your_skill"
    SKILL_DESCRIPTION = "Description of your skill"
    
    def register_tools(self) -> None:
        self.agent.define_tool(
            name="your_function",
            description="Function description",
            parameters={...},
            handler=self._your_function_handler
        )
    
    def _your_function_handler(self, args, raw_data):
        # Implementation
        return SwaigFunctionResult("Response message")
```

### Adding New Features

1. **Web Features**: Add routes to `app.py`, templates to `templates/`, and static files to `static/`
2. **Voice Features**: Add methods to appropriate skill classes
3. **Database Changes**: Update `models.py` and create migration scripts

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions
- Include error handling and validation

## 🚀 Deployment on Replit

### Environment Configuration

1. **Set environment variables in Replit Secrets**:
   - `SIGNALWIRE_PROJECT_ID`
   - `SIGNALWIRE_TOKEN`
   - `SIGNALWIRE_SPACE_URL`
   - `SIGNALWIRE_FROM_NUMBER`
   - `STRIPE_PUBLISHABLE_KEY`
   - `STRIPE_SECRET_KEY`

2. **Configure webhook URLs**:
   - Use your Replit app URL for webhooks
   - Example: `https://your-repl-name.your-username.repl.co/receptionist`

### SignalWire Configuration

1. Create SignalWire project
2. Configure phone numbers
3. Set webhook URLs:
   - Voice: `https://your-repl-name.your-username.repl.co/receptionist`
   - SMS: `https://your-repl-name.your-username.repl.co/receptionist`


## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Bobby's Table** - Where technology meets hospitality! 🍽️📞
