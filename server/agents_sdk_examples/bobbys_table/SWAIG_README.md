# Bobby's Table - SignalWire Agent Integration

This document describes the voice interface capabilities powered by [SignalWire Agents](https://github.com/briankwest/signalwire-agents) that are integrated into the main Flask application.

## 🎯 Overview

Bobby's Table includes a comprehensive voice interface that allows customers to interact with the restaurant system via phone calls. The SWAIG (SignalWire AI Gateway) integration is now **fully integrated** into the main Flask application, providing:

- **Voice Reservations**: Make, check, modify, and cancel reservations
- **Voice Ordering**: Browse menu, place orders for pickup/delivery
- **Order Status**: Check order status and updates
- **Kitchen Management**: Voice interface for kitchen staff

## 🚀 Quick Start

### Start the Integrated Service

```bash
# Start the integrated web and voice interface
python start_agents.py
```

This will start a single service on port 8080 with:
- **Web Interface**: http://localhost:8080
- **Voice Interface**: http://localhost:8080/receptionist
- **Kitchen Dashboard**: http://localhost:8080/kitchen

### Test SWAIG Functions

```bash
# Test all voice functions via HTTP
python test_swaig_functions.py
```

## 📞 Voice Interface Endpoints

### Main SWAIG Endpoint
- **URL**: `/receptionist`
- **Method**: POST (for function calls), GET (for service info)
- **Purpose**: Unified endpoint for all voice interactions
- **Integration**: Fully integrated into Flask app

### Available SWAIG Functions

#### Reservation Management

1. **`create_reservation`**
   - Create new restaurant reservations
   - Parameters: name, party_size, date, time, phone_number, special_requests
   - Validates: date/time format, restaurant hours, party size

2. **`get_reservation`**
   - Look up existing reservations by phone number
   - Parameters: phone_number
   - Returns: reservation details with formatted times

#### Menu & Ordering

3. **`get_menu`**
   - Browse menu items by category or view all
   - Parameters: category (optional)
   - Categories: breakfast, appetizers, main-courses, desserts, drinks

4. **`create_order`**
   - Place orders for pickup or delivery
   - Parameters: customer_name, customer_phone, order_type, order_date, order_time, items, customer_address, special_instructions
   - Validates: order type, delivery address, menu items

5. **`get_order_status`**
   - Check order status by ID or phone number
   - Parameters: order_id OR customer_phone
   - Returns: detailed order information and status

#### Kitchen Management

6. **`update_order_status`**
   - Update order status (for kitchen staff)
   - Parameters: order_id, new_status
   - Valid statuses: pending, preparing, ready, completed

## 🗣️ Example Voice Interactions

### Making a Reservation

**Customer**: "I'd like to make a reservation"
**Agent**: "I'd be happy to help you with a reservation. What name should I put it under?"
**Customer**: "John Smith"
**Agent**: "Great! How many people will be dining with us?"
**Customer**: "Four people"
**Agent**: "Perfect! What date would you prefer?"
**Customer**: "Tomorrow at 7 PM"
**Agent**: "Let me book that for you... I'll need your phone number for the reservation."

### Placing an Order

**Customer**: "I'd like to place an order for pickup"
**Agent**: "I'd be happy to help you place an order. Would you like to hear our menu categories?"
**Customer**: "What do you have for breakfast?"
**Agent**: "Here are our breakfast items: Classic Eggs Benedict - $14.99, Blueberry Pancakes - $12.99..."
**Customer**: "I'll take two orders of Eggs Benedict"
**Agent**: "Excellent choice! When would you like to pick this up?"

### Checking Order Status

**Customer**: "I'd like to check on my order"
**Agent**: "I can help you with that. Do you have your order number, or should I look it up by phone number?"
**Customer**: "My phone number is +15551234567"
**Agent**: "I found your order #123. It's currently being prepared in the kitchen and should be ready for pickup at 2:30 PM."

## 🔧 Technical Implementation

### Integrated Architecture

```
┌─────────────────┐    ┌─────────────────────────────────────┐
│   SignalWire    │    │         Flask App (Port 8080)       │
│   Platform      │◄──►│  ┌─────────────┐ ┌─────────────────┐ │
└─────────────────┘    │  │ Web Routes  │ │ SWAIG Functions │ │
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

### Key Features

- **Single Port**: Both web and voice interfaces on port 8080
- **Shared Database**: Real-time synchronization between interfaces
- **Integrated Routes**: SWAIG functions as Flask routes
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **Time Formatting**: Automatic conversion between 24-hour and 12-hour formats
- **Restaurant Hours**: Enforces 9 AM - 9 PM operating hours

### SWAIG Function Integration

SWAIG functions are integrated as Flask routes:

```python
@app.route('/receptionist', methods=['POST'])
def swaig_receptionist():
    """Handle SWAIG requests for the receptionist agent"""
    data = request.get_json()
    function_name = data.get('function')
    params = data.get('argument', {})
    
    # Route to appropriate agent method
    if hasattr(receptionist_agent, function_name):
        method = getattr(receptionist_agent, function_name)
        result = method(params)
        return jsonify(result)
```

## 🧪 Testing

### Automated Testing

```bash
# Run comprehensive SWAIG function tests via HTTP
python test_swaig_functions.py
```

### Manual Testing via HTTP

```bash
# Test service info
curl http://localhost:8080/receptionist

# Test reservation creation
curl -X POST http://localhost:8080/receptionist \
  -H "Content-Type: application/json" \
  -d '{
    "function": "create_reservation",
    "argument": {
      "name": "John Doe",
      "party_size": 4,
      "date": "2025-06-07",
      "time": "19:00",
      "phone_number": "+1234567890"
    }
  }'
```

### Testing with SignalWire Platform

1. Configure SignalWire webhook to point to: `https://yourdomain.com:8080/receptionist`
2. Make test calls to your SignalWire phone number
3. Interact with the voice interface naturally

## 🔐 Configuration

### Environment Variables

Create a `.env` file with:

```env
# SignalWire Configuration
SIGNALWIRE_PROJECT_ID=your_project_id
SIGNALWIRE_TOKEN=your_token
SIGNALWIRE_SPACE_URL=your_space_url

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your_secret_key

# Database
DATABASE_URL=sqlite:///instance/restaurant.db
```

## 📊 Monitoring & Logging

The integrated system provides logging for:

- Flask request/response cycles
- SWAIG function calls and parameters
- Database operations
- Error conditions
- Performance metrics

Monitor logs to track:
- Popular voice interactions
- Common error patterns
- Performance metrics
- Integration health

## 🚀 Deployment

### Production Deployment

1. **Set up SignalWire Project**
   - Create account at SignalWire
   - Get project credentials
   - Configure phone numbers

2. **Deploy Application**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Set environment variables
   export SIGNALWIRE_PROJECT_ID=your_project_id
   export SIGNALWIRE_TOKEN=your_token
   
   # Start integrated service
   python start_agents.py
   ```

3. **Configure Webhooks**
   - Point SignalWire webhooks to your SWAIG endpoint
   - Example: `https://yourdomain.com:8080/receptionist`

### Production WSGI Server

```bash
# Use Gunicorn for production
gunicorn app:app --bind 0.0.0.0:8080 --workers 4
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["python", "start_agents.py"]
```

## 🤝 Integration Benefits

### For Customers
- **Single Point of Access**: One URL for all interactions
- **Seamless Experience**: Voice and web data perfectly synchronized
- **Natural Language**: Speak naturally, no complex menus
- **Instant Updates**: Real-time status across all channels

### For Restaurant Staff
- **Unified Dashboard**: Single interface for all operations
- **Reduced Complexity**: One service to manage and monitor
- **Data Consistency**: Single source of truth
- **Easy Deployment**: One application to deploy and scale

### For Business
- **Cost Efficiency**: Single server instance for all features
- **Simplified Architecture**: Easier to maintain and debug
- **Better Performance**: No inter-service communication overhead
- **Scalability**: Scale web and voice together

## 📈 Future Enhancements

Potential improvements for the integrated system:

1. **WebSocket Integration**: Real-time updates between web and voice
2. **Multi-language Support**: Spanish, French, etc.
3. **Voice Biometrics**: Customer identification by voice
4. **Advanced Analytics**: Cross-channel interaction tracking
5. **Load Balancing**: Multiple instances with shared state
6. **Caching Layer**: Redis for improved performance

## 🆘 Troubleshooting

### Common Issues

1. **Service Not Starting**
   ```bash
   # Check if port 8080 is available
   netstat -an | grep 8080
   
   # Check for import errors
   python -c "from app import app; print('App imported successfully')"
   ```

2. **SWAIG Functions Not Working**
   ```bash
   # Test the endpoint directly
   curl http://localhost:8080/receptionist
   
   # Check agent initialization
   python -c "from swaig_agents import RestaurantReceptionistAgent; print('Agent imported successfully')"
   ```

3. **Database Connection Errors**
   ```bash
   # Ensure database is initialized
   python init_db.py
   python init_test_data.py
   ```

### Debug Mode

Enable debug logging in Flask:

```python
app.run(host="0.0.0.0", port=8080, debug=True)
```

## 📚 Resources

- [SignalWire Agents Documentation](https://github.com/briankwest/signalwire-agents)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SignalWire Platform Docs](https://docs.signalwire.com/)
- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)

---

**Bobby's Table** - Where technology meets hospitality! 🍽️📞 