from signalwire_agents import AgentBase
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swaig_function import swaig_function
from models import Reservation
from signalwire_agents import route

load_dotenv()

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

SIGNALWIRE_FROM_NUMBER = os.getenv('SIGNALWIRE_FROM_NUMBER', '+15551234567')

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Restaurant Reservation System</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                h1 {
                    color: #333;
                }
                .info {
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <h1>Restaurant Reservation System</h1>
            <div class="info">
                <h2>Welcome to our Reservation System</h2>
                <p>This is a voice-enabled reservation system powered by SignalWire Agents.</p>
                <p>To interact with the system, please use the following endpoints:</p>
                <ul>
                    <li><strong>Reservation Agent:</strong> <a href="/reservation">/reservation</a></li>
                </ul>
            </div>
        </body>
    </html>
    """

class ReservationAgent(AgentBase):
    def __init__(self):
        super().__init__(
            name="reservation-agent",
            route="/reservation"
        )
        
        # Add English language support
        self.add_language("English", "en-US", "rime.spore:mistv2")
        
        # Set up the agent's capabilities
        self.set_params({
            "end_of_speech_timeout": 500,
            "silence_timeout": 500,
            "max_speech_timeout": 10000
        })
        
        # Add the agent's prompt
        self.prompt_add_section("System", """
You are a helpful restaurant reservation assistant. You can help customers create, view, update, and cancel reservations.
Always be polite and professional. When creating or updating reservations, verify the date and time are valid.
If a customer wants to make a reservation, ask for their name, party size, preferred date and time, and phone number.
If they want to check their reservation, ask for their phone number.
If they want to update or cancel their reservation, ask for their phone number first.
""")
        
        # Initialize the reservations storage
        self.reservations = {}
    
    def create_reservation(self, params):
        try:
            # Validate date and time
            datetime.strptime(f"{params['date']} {params['time']}", "%Y-%m-%d %H:%M")
            
            # Store the reservation
            self.reservations[params['phone_number']] = {
                'name': params['name'],
                'party_size': params['party_size'],
                'date': params['date'],
                'time': params['time']
            }
            
            result = self.send_reservation_sms(self.reservations[params['phone_number']], params.get('order_items', []))
            return {
                'success': True,
                'message': f"Reservation confirmed for {params['name']} on {params['date']} at {params['time']} for {params['party_size']} people.",
                'sms_result': result
            }
        except ValueError:
            return {
                'success': False,
                'message': "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."
            }
    
    def get_reservation(self, params):
        phone = params['phone_number']
        if phone in self.reservations:
            res = self.reservations[phone]
            return {
                'success': True,
                'message': f"Found your reservation for {res['name']} on {res['date']} at {res['time']} for {res['party_size']} people."
            }
        return {
            'success': False,
            'message': "No reservation found for that phone number."
        }
    
    def update_reservation(self, params):
        phone = params['phone_number']
        if phone not in self.reservations:
            return {
                'success': False,
                'message': "No reservation found for that phone number."
            }
        
        res = self.reservations[phone]
        updates = {k: v for k, v in params.items() if v is not None and k != 'phone_number'}
        
        if updates:
            res.update(updates)
            return {
                'success': True,
                'message': "Reservation updated successfully."
            }
        return {
            'success': False,
            'message': "No updates provided."
        }
    
    def cancel_reservation(self, params):
        phone = params['phone_number']
        if phone in self.reservations:
            del self.reservations[phone]
            return {
                'success': True,
                'message': "Reservation cancelled successfully."
            }
        return {
            'success': False,
            'message': "No reservation found for that phone number."
        }
    
    def move_reservation(self, params):
        phone = params['phone_number']
        if phone not in self.reservations:
            return {
                'success': False,
                'message': "No reservation found for that phone number."
            }
        
        try:
            # Validate new date and time
            datetime.strptime(f"{params['new_date']} {params['new_time']}", "%Y-%m-%d %H:%M")
            
            res = self.reservations[phone]
            res['date'] = params['new_date']
            res['time'] = params['new_time']
            
            return {
                'success': True,
                'message': f"Reservation moved to {params['new_date']} at {params['new_time']}."
            }
        except ValueError:
            return {
                'success': False,
                'message': "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."
            }

    @route('/api/reservations', methods=['GET'])
    def api_list_reservations(self, request):
        """SignalWire route to return all reservations in the same format as the Flask API."""
        reservations = Reservation.query.all()
        return [r.to_dict() for r in reservations]

def send_reservation_sms(reservation, order_items):
    sms_body = f"Reservation confirmed for {reservation['name']} on {reservation['date']} at {reservation['time']}.\n"
    if order_items:
        sms_body += "Pre-ordered items:\n"
        for item in order_items:
            sms_body += f"- {item['name']} x{item['quantity']}\n"
    else:
        sms_body += "No pre-ordered items."
    return SwaigFunctionResult().send_sms(
        to_number=reservation['phone_number'],
        from_number=SIGNALWIRE_FROM_NUMBER,
        body=sms_body
    )

@swaig_function(
    name="create_reservation",
    description="Create a new reservation and optionally pre-order food.",
    parameters=[
        {"name": "name", "type": "string", "description": "Name for the reservation."},
        {"name": "party_size", "type": "integer", "description": "Number of people."},
        {"name": "date", "type": "string", "description": "Reservation date (YYYY-MM-DD)."},
        {"name": "time", "type": "string", "description": "Reservation time (HH:MM)."},
        {"name": "phone_number", "type": "string", "description": "Contact phone number."},
        {"name": "special_requests", "type": "string", "description": "Special requests.", "optional": True},
        {"name": "order_items", "type": "array", "description": "List of food/drink items to pre-order.", "optional": True},
    ]
)
def create_reservation(params):
    # Your reservation creation logic here
    # Should call send_reservation_sms as in previous step
    pass

@swaig_function(
    name="get_reservation",
    description="Get reservation details by phone number.",
    parameters=[
        {"name": "phone_number", "type": "string", "description": "Contact phone number."}
    ]
)
def get_reservation(params):
    # Your get logic here
    pass

@swaig_function(
    name="update_reservation",
    description="Update an existing reservation.",
    parameters=[
        {"name": "phone_number", "type": "string", "description": "Contact phone number."},
        {"name": "name", "type": "string", "optional": True},
        {"name": "party_size", "type": "integer", "optional": True},
        {"name": "date", "type": "string", "optional": True},
        {"name": "time", "type": "string", "optional": True},
        {"name": "special_requests", "type": "string", "optional": True},
        {"name": "order_items", "type": "array", "optional": True},
    ]
)
def update_reservation(params):
    # Your update logic here
    pass

@swaig_function(
    name="cancel_reservation",
    description="Cancel a reservation by phone number.",
    parameters=[
        {"name": "phone_number", "type": "string", "description": "Contact phone number."}
    ]
)
def cancel_reservation(params):
    # Your cancel logic here
    pass

@swaig_function(
    name="list_reservations",
    description="List all reservations.",
    parameters=[]
)
def list_reservations(params):
    # Your list logic here
    pass

# Create and serve the agent
if __name__ == "__main__":
    agent = ReservationAgent()
    agent.serve(host="0.0.0.0", port=int(os.getenv("PORT", 5001))) 